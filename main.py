import boto3
import requests
import os
import sys
from datetime import datetime

def get_public_ip():
    try:
        response = requests.get('https://checkip.amazonaws.com')
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return None

def update_dns(ip, zone_id, record_name):
    client = boto3.client('route53')
    try:
        change_batch = {
            'Comment': 'Updated by Docker DDNS Client',
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': record_name,
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': ip}]
                    }
                }
            ]
        }
        response = client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=change_batch)
        print(f"[{datetime.now()}] DNS update initiated: {response['ChangeInfo']['Status']}")
    except Exception as e:
        print(f"[{datetime.now()}] Error updating DNS: {e}")

if __name__ == "__main__":
    zone_id = os.environ.get('HOSTED_ZONE_ID')
    record_name = os.environ.get('RECORD_NAME')
    
    if not zone_id or not record_name:
        print("Error: HOSTED_ZONE_ID and RECORD_NAME environment variables must be set.")
        sys.exit(1)

    current_ip = get_public_ip()
    if current_ip:
        print(f"[{datetime.now()}] Current Public IP: {current_ip}")
        update_dns(current_ip, zone_id, record_name)
