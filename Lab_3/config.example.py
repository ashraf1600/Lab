import os
import boto3

# Paste your AWS credentials here or configure environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "YOUR_ACCESS_KEY_HERE")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "YOUR_SECRET_KEY_HERE")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", None)  # Leave None if standard IAM user
AWS_REGION = "ap-southeast-1"

def get_session():
    if AWS_SESSION_TOKEN:
        return boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN,
            region_name=AWS_REGION
        )
    return boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
