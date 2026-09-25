#!/usr/bin/env python3
"""
Terminates existing test cloud instance and launches production air-gapped ML host
with gzip-compressed User Data bootstrapping model_server.py and ml-pipeline.service.
"""

import os
import boto3
import json
import gzip
import base64
import time

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
REGION = "ap-southeast-1"
UBUNTU_AMI = "ami-0d95f2f0cc4ab4566"
KEY_PAIR_NAME = "lab5-keypair"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION
)
ec2 = session.client("ec2")

with open("Lab_5/lab5_state.json") as f:
    state = json.load(f)

old_inst_id = state.get("cloud_inst_id")
if old_inst_id:
    print(f"Terminating old test instance {old_inst_id}...")
    ec2.terminate_instances(InstanceIds=[old_inst_id])
    waiter = ec2.get_waiter("instance_terminated")
    waiter.wait(InstanceIds=[old_inst_id])
    print(f"Old instance {old_inst_id} terminated.")

# Read model_server.py
with open("Lab_5/src/model_server.py", "r") as f:
    model_code = f.read()

compressed_b64 = base64.b64encode(gzip.compress(model_code.encode("utf-8"))).decode("utf-8")
print(f"Compressed code size: {len(compressed_b64)} bytes")

cloud_ud = f"""#!/bin/bash
set -ex
mkdir -p /opt/ml-pipeline
echo "{compressed_b64}" | base64 -d | gzip -d > /opt/ml-pipeline/model_server.py
chmod +x /opt/ml-pipeline/model_server.py

cat << 'EOF' > /etc/systemd/system/ml-pipeline.service
[Unit]
Description=Production Air-Gapped NLP Pipeline Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ml-pipeline
ExecStart=/usr/bin/python3 /opt/ml-pipeline/model_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now ml-pipeline.service
"""

cloud_subnet_id = state["cloud_subnet_id"]
cloud_sg_id = state["cloud_sg_id"]

print(f"Launching production lab5-cloud-ml-host in {cloud_subnet_id} (10.50.1.100)...")
inst = ec2.run_instances(
    ImageId=UBUNTU_AMI,
    InstanceType="t2.micro",
    KeyName=KEY_PAIR_NAME,
    MinCount=1,
    MaxCount=1,
    NetworkInterfaces=[{
        "DeviceIndex": 0,
        "SubnetId": cloud_subnet_id,
        "AssociatePublicIpAddress": False,
        "PrivateIpAddress": "10.50.1.100",
        "Groups": [cloud_sg_id]
    }],
    UserData=cloud_ud,
    TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "lab5-cloud-ml-host"}]}]
)["Instances"][0]

new_inst_id = inst["InstanceId"]
state["cloud_inst_id"] = new_inst_id
print(f"Launched new Cloud ML Host: {new_inst_id}")

print("Waiting for instance to be running...")
waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=[new_inst_id])
print("Instance is now running!")

with open("Lab_5/lab5_state.json", "w") as f:
    json.dump(state, f, indent=2)
print("Updated lab5_state.json successfully!")
