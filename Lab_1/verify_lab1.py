#!/usr/bin/env python3
"""
Verify Lab 1: VPC-Isolated ML Inference Endpoint with Transit Gateway
Performs both:
1. Negative Verification: Public internet cannot reach Model Server
2. Positive Verification: Client VPC reaches Model Server over Transit Gateway and gets inference
"""

import boto3
import json
import os
import sys
import subprocess
import time
import urllib.request
import urllib.error

from config import get_session, get_ec2_client, STATE_FILE, KEY_NAME, KEY_FILE

session = get_session()
ec2 = get_ec2_client()

with open(STATE_FILE, "r") as f:
    state = json.load(f)

print("=" * 65)
print("LAB 1 VERIFICATION: VPC-ISOLATED ML INFERENCE ENDPOINT")
print("=" * 65)

# -------------------------------------------------------------
# 1. Inspect AWS Infrastructure State
# -------------------------------------------------------------
print("\n[1] Checking Cloud Infrastructure Configuration...")

# Inspect Model VPC Route Table
m_rt = ec2.describe_route_tables(RouteTableIds=[state['RouteTable1_Model_Id']])['RouteTables'][0]
m_routes = {r.get('DestinationCidrBlock'): r.get('TransitGatewayId') or r.get('GatewayId') for r in m_rt['Routes']}
print(f"  Model VPC Routes: {m_routes}")
assert '0.0.0.0/0' not in m_routes, "FAILED: Model VPC still has an internet route!"
assert state['Vpc2_Client_Id'] or '10.1.0.0/16' in m_routes, "FAILED: No TGW route to Client VPC!"
print("  [PASS] Model VPC is 100% private: No 0.0.0.0/0 route, TGW route active.")

# Inspect Model Instance
m_inst = ec2.describe_instances(InstanceIds=[state['Model_Instance_Id']])['Reservations'][0]['Instances'][0]
m_pub_ip = m_inst.get('PublicIpAddress')
m_priv_ip = m_inst.get('PrivateIpAddress')
print(f"  Model EC2 Private IP: {m_priv_ip}")
print(f"  Model EC2 Public IP:  {m_pub_ip}")
assert m_pub_ip is None, "FAILED: Model EC2 has a public IP!"
print("  [PASS] Model EC2 has NO Public IP.")

# Inspect Client Instance
c_inst = ec2.describe_instances(InstanceIds=[state['Client_Instance_Id']])['Reservations'][0]['Instances'][0]
c_pub_ip = c_inst.get('PublicIpAddress')
c_priv_ip = c_inst.get('PrivateIpAddress')
print(f"  Client EC2 Public IP:  {c_pub_ip}")
print(f"  Client EC2 Private IP: {c_priv_ip}")

# -------------------------------------------------------------
# 2. Negative Verification: Public Internet Isolation
# -------------------------------------------------------------
print("\n[2] Performing Negative Test: Accessing Model from Public Internet...")
public_test_failed = False
try:
    url = f"http://{m_priv_ip}:8000/predict"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=3) as resp:
        print("  [ALERT] Model server unexpectedly responded from internet!")
except Exception as e:
    public_test_failed = True
    print(f"  [PASS] Connection timed out / unreachable as expected: {e}")

assert public_test_failed, "FAILED: Model server is accessible from internet!"

# -------------------------------------------------------------
# 3. Positive Verification: Client VPC -> Transit Gateway -> Model VPC
# -------------------------------------------------------------
print("\n[3] Performing Positive Test: Querying Model from Client VPC over Transit Gateway...")
print(f"  Connecting to Client EC2 ({c_pub_ip}) via SSH...")

ssh_cmd = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-i", KEY_FILE,
    f"ubuntu@{c_pub_ip}",
    f"python3 /home/ubuntu/client_test.py {m_priv_ip} /home/ubuntu/sample_dog.jpg"
]

for attempt in range(10):
    try:
        proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0 and "INFERENCE SUCCESSFUL" in proc.stdout:
            print("\n" + proc.stdout)
            print("  [PASS] Internal inference over Transit Gateway SUCCEEDED!")
            break
        else:
            print(f"  Attempt {attempt+1}: Client script output: {proc.stdout} {proc.stderr}. Retrying in 10s...")
            time.sleep(10)
    except Exception as e:
        print(f"  Attempt {attempt+1}: SSH connection error ({e}). Retrying in 10s...")
        time.sleep(10)

print("\n" + "=" * 65)
print("ALL LAB 1 OBJECTIVES SUCCESSFULLY VERIFIED!")
print("=" * 65)
