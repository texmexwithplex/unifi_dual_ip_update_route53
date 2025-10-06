import requests
import urllib3
import sys
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Dict, Any

# Suppress the InsecureRequestWarning for the self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def str_to_bool(value: Optional[str]) -> bool:
    """Converts a string to a boolean, defaulting to False if None or invalid."""
    return value is not None and value.lower() in ('true', '1', 't', 'y', 'yes')

def unifi_login(session: requests.Session, base_url: str, username: str, password: str, verify_ssl: bool) -> bool:
    """Logs into the UniFi Controller and establishes a session."""
    login_url = f"{base_url}/api/auth/login"
    login_payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/json"}

    try:
        print(f"Attempting login to: {login_url}")
        response = session.post(
            login_url,
            headers=headers,
            json=login_payload,
            verify=verify_ssl,
            timeout=10
        )

        if response.status_code == 401:
            print("🔴 Login Failed: Status 401 Unauthorized.")
            print("  --> The user and password were rejected by the UniFi Controller.")
            print("  --> Re-verify the account is LOCAL-ONLY with correct permissions.")
            return False

        response.raise_for_status()
        print("🟢 Login Successful. Session cookie established.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"🚨 An HTTP request error occurred during login: {e}")
        return False

def get_gateway_info(session: requests.Session, base_url: str, site_id: str, verify_ssl: bool) -> Optional[Dict[str, Any]]:
    """Retrieves device list and returns information for the gateway."""
    devices_url = f"{base_url}/proxy/network/api/s/{site_id}/stat/device"
    try:
        print(f"Attempting to retrieve device list from: {devices_url}")
        response = session.get(devices_url, verify=verify_ssl, timeout=10)
        response.raise_for_status()
        print("🟢 Device list retrieval successful.")

        devices_data = response.json().get('data', [])
        for device in devices_data:
            if device.get('type') in ['ugw', 'udm', 'ucg']: # UniFi gateway types
                return device
        return None

    except requests.exceptions.RequestException as e:
        print(f"🚨 An HTTP request error occurred while getting devices: {e}")
        return None
    except requests.exceptions.JSONDecodeError:
        print("🚨 Failed to decode JSON from device list response.")
        return None

def update_route53_records(zone_id: str, record_name: str, ipv4: Optional[str], ipv6: Optional[str], region: str):
    """Updates A and AAAA records in AWS Route53."""
    if not any([ipv4, ipv6]):
        print("🟡 No IP addresses provided to update Route53. Skipping.")
        return

    try:
        client = boto3.client("route53", region_name=region)
        print(f"Attempting to update Route53 record: {record_name} in Zone: {zone_id}")

        changes = []
        if ipv4:
            changes.append({
                'Action': 'UPSERT',
                'ResourceRecordSet': {'Name': record_name, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ipv4}]}
            })
        if ipv6:
            changes.append({
                'Action': 'UPSERT',
                'ResourceRecordSet': {'Name': record_name, 'Type': 'AAAA', 'TTL': 300, 'ResourceRecords': [{'Value': ipv6}]}
            })

        response = client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={'Comment': 'Automated DDNS update', 'Changes': changes}
        )
        
        change_id = response.get('ChangeInfo', {}).get('Id', 'N/A')
        print(f"🟢 Route53 update request successful. Change ID: {change_id}")

    except NoCredentialsError:
        print("🚨 AWS credentials not found. Ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set.")
    except ClientError as e:
        print(f"🚨 An AWS client error occurred: {e.response['Error']['Message']}")

def main():
    """Main execution function."""
    # 1. Load Configuration from .env file
    load_dotenv()
    
    unifi_ip = os.getenv("UNIFI_IP")
    unifi_port = os.getenv("UNIFI_PORT", "443")
    api_user = os.getenv("UNIFI_USER")
    api_pass = os.getenv("UNIFI_PASS")
    site_id = os.getenv("UNIFI_SITE_ID", "default")
    verify_ssl = str_to_bool(os.getenv("UNIFI_VERIFY_SSL"))
    
    # Load Route53 configuration
    route53_zone_id = os.getenv("ROUTE53_ZONE_ID")
    route53_record_name = os.getenv("ROUTE53_RECORD_NAME")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    # Validate required variables
    if not all([unifi_ip, api_user, api_pass, route53_zone_id, route53_record_name]):
        print("🚨 Error: Missing required environment variables. Check UNIFI_* and ROUTE53_* variables.")
        sys.exit(1)

    base_url = f"https://{unifi_ip}:{unifi_port}"

    # 2. Create a session and login
    with requests.Session() as session:
        if not unifi_login(session, base_url, api_user, api_pass, verify_ssl):
            sys.exit(1) # Exit if login fails

        # 3. Get gateway device information
        gateway_device = get_gateway_info(session, base_url, site_id, verify_ssl)

        if not gateway_device:
            print("🔴 Could not find a gateway device in the device list.")
            sys.exit(1)

        # 4. Extract and print IP information
        print(f"\nFound Gateway: {gateway_device.get('name', 'N/A')} ({gateway_device.get('model', 'N/A')})")
        wan_info = gateway_device.get('wan1', {})
        ipv4 = wan_info.get('ip')
        
        # The 'ipv6' key holds a list; we only want the first one.
        ipv6_list = wan_info.get('ipv6')
        ipv6 = ipv6_list[0] if isinstance(ipv6_list, list) and ipv6_list else None
        
        print(f"  Public IPv4: {ipv4 or 'Not found'}")
        print(f"  Public IPv6: {ipv6 or 'Not found'}")
        
        # 5. Update Route53 records
        update_route53_records(route53_zone_id, route53_record_name, ipv4, ipv6, aws_region)

if __name__ == "__main__":
    main()