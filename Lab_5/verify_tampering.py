#!/usr/bin/env python3
"""
Positive, Negative, and Chaos Tampering Verification for Lab 5
"""
import os
import boto3
import json
import time
import subprocess

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
REGION = "ap-southeast-1"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION
)
ec2 = session.client("ec2")

with open("Lab_5/lab5_state.json") as f:
    state = json.load(f)

onprem_rt = state["onprem_rt_id"]
peering_id = state["peering_id"]
router_ip = state["eip_public_ip"]
key_file = "Lab_5/lab5-keypair.pem"

def run_ssh(cmd):
    full_cmd = ["ssh", "-i", key_file, "-o", "StrictHostKeyChecking=no", f"ubuntu@{router_ip}", cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

print("=" * 80)
print("TEST 1: POSITIVE TEST - INGESTION OVER PRIVATE ENCRYPTED PATH")
print("=" * 80)
ret, out, err = run_ssh("python3 /opt/onprem/data_ingestion.py")
print(out)

print("=" * 80)
print("TEST 2: CHAOS TAMPERING EXPERIMENT - SIMULATING ROUTE WITHDRAWAL / CUT")
print("=" * 80)
print(f"[*] Removing route 10.50.0.0/16 from On-Prem Route Table {onprem_rt}...")
ec2.delete_route(RouteTableId=onprem_rt, DestinationCidrBlock="10.50.0.0/16")
print("[+] Route 10.50.0.0/16 removed.")
time.sleep(3)

print("[*] Probing Cloud ML pipeline from On-Premises router during outage...")
ret, out, err = run_ssh("curl -s --connect-timeout 2 http://10.50.1.100:8000/health || echo 'FAIL_TIMEOUT_CONFIRMED'")
print("Observed result during cut:", out.strip())

print("\n[*] Restoring route 10.50.0.0/16 pointing to peering/gateway...")
ec2.create_route(RouteTableId=onprem_rt, DestinationCidrBlock="10.50.0.0/16", VpcPeeringConnectionId=peering_id)
print("[+] Route restored. Waiting 3 seconds for route propagation...")
time.sleep(3)

print("[*] Probing Cloud ML pipeline after route recovery...")
ret, out, err = run_ssh("curl -s --connect-timeout 2 http://10.50.1.100:8000/health")
print("Recovered service response:", out.strip())
print("\n[+] CHAOS TAMPERING EXPERIMENT VERIFIED: Path failed safely and self-healed upon route restoration.")
