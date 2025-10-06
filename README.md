# UniFi DDNS for Route53

A simple, robust Python script to automatically update an AWS Route53 DNS record with the public IP address from a UniFi gateway (like a UDM, USG, or UCG).

## Features

-   Fetches the public IPv4 and IPv6 addresses directly from your UniFi Controller API.
-   Securely updates `A` (IPv4) and `AAAA` (IPv6) records in AWS Route53 using `boto3`.
-   Configuration is managed via a `.env` file for security and portability.
-   Lightweight and designed to be run on a schedule (e.g., via cron).

## Prerequisites

-   Python 3.8+
-   A UniFi Network Application (on a UDM, Cloud Key, etc.).
-   A **local administrator account** on your UniFi Controller. A UI.com SSO account will not work for API access.
-   An AWS account with a pre-existing Hosted Zone in Route53.

## Setup Instructions

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Set up a Python Virtual Environment**
    It's highly recommended to use a virtual environment to isolate project dependencies.
    ```bash
    # Create the virtual environment
    python3 -m venv .venv

    # Activate it (Linux/macOS)
    source .venv/bin/activate

    # Activate it (Windows)
    # .\.venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Copy the example file to create your own local configuration. This file is ignored by Git, so your secrets are safe.
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file with your specific details for UniFi and AWS.

## AWS IAM Permissions

For security, you should create a dedicated IAM user with the minimum required permissions. The script only needs to be able to update record sets within your specific Route53 hosted zone.

Here is a least-privilege IAM policy. **Remember to replace `YOUR_HOSTED_ZONE_ID` with your actual Zone ID from the Route53 console.**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "route53:ChangeResourceRecordSets",
            "Resource": "arn:aws:route53:::hostedzone/YOUR_HOSTED_ZONE_ID"
        }
    ]
}
```

Attach this policy to an IAM user and place that user's `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your `.env` file.

## Usage

Once configured, you can run the script manually from the project's root directory:

```bash
python unifi_ddns/main.py
```

The script will log its progress to the console, indicating a successful login, IP address retrieval, and the result of the Route53 update request.

### Automation

For a true "dynamic DNS" setup, you should run this script automatically on a schedule. A `cron` job is a perfect tool for this.

For example, to run the script every 15 minutes, you could add the following to your crontab:

```cron
*/15 * * * * /path/to/your/project/.venv/bin/python /path/to/your/project/unifi_ddns/main.py >> /var/log/unifi_ddns.log 2>&1
```

Make sure to use the absolute paths to your virtual environment's Python interpreter and the `main.py` script.
