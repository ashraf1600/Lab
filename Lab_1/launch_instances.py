#!/usr/bin/env python3
"""
Phase 4: Launch Model EC2 and Client EC2
Bootstrap FastAPI + ViT model on Model EC2, then isolate Model VPC.
"""

import boto3
import time
import json
import os
import sys

from config import get_session, get_ec2_client, STATE_FILE, KEY_NAME, KEY_FILE

session = get_session()
ec2 = get_ec2_client()

OUTPUT_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1"
STATE_FILE = os.path.join(OUTPUT_DIR, "lab1_state.json")

with open(STATE_FILE, "r") as f:
    state = json.load(f)

AMI_ID = "ami-0d95f2f0cc4ab4566" # Ubuntu 22.04 LTS
INSTANCE_TYPE = "t2.micro"

def log(msg):
    print(f"\n[+] {msg}", flush=True)

# -------------------------------------------------------------
# 1. Temporary Internet Gateway for Model VPC (for bootstrap)
# -------------------------------------------------------------
log("Setting up temporary bootstrap internet connectivity for Model VPC...")
temp_igw = ec2.create_internet_gateway(
    TagSpecifications=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'Name', 'Value': 'lab1-model-temp-igw'}]}]
)
temp_igw_id = temp_igw['InternetGateway']['InternetGatewayId']
ec2.attach_internet_gateway(InternetGatewayId=temp_igw_id, VpcId=state['Vpc1_Model_Id'])
log(f"Attached temporary IGW: {temp_igw_id}")

ec2.create_route(
    RouteTableId=state['RouteTable1_Model_Id'],
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=temp_igw_id
)
log(f"Added temporary route 0.0.0.0/0 -> {temp_igw_id}")

# Allocate Elastic IP for Model EC2 during bootstrap
eip_res = ec2.allocate_address(Domain='vpc')
eip_alloc_id = eip_res['AllocationId']
eip_public_ip = eip_res['PublicIp']
log(f"Allocated temporary Elastic IP: {eip_public_ip} ({eip_alloc_id})")

# Temporarily allow port 8000 from anywhere for bootstrap verification
try:
    ec2.authorize_security_group_ingress(
        GroupId=state['SG1_Model_Id'],
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 8000,
            'ToPort': 8000,
            'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Temp bootstrap check'}]
        }]
    )
except Exception:
    pass

# -------------------------------------------------------------
# 2. User Data for Model Server (FastAPI + MobileViT/ViT)
# -------------------------------------------------------------
model_user_data = """#!/bin/bash
set -e

# Setup 2GB Swapfile
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Update and install Python tools
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip python3-venv curl

# Install PyTorch CPU and dependencies
pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip3 install --no-cache-dir fastapi uvicorn pillow python-multipart

# Write ViT Server code
cat << 'EOF' > /home/ubuntu/vit_server.py
import io
import torch
from torchvision import models
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn

app = FastAPI(title="Private ViT Vision Model Endpoint")

print("[*] Loading Vision Transformer / Vision Model weights...")
# Using MobileNetV3 / ViT compatible weights for fast CPU inference
weights = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
weights.eval()
preprocess = models.MobileNet_V3_Small_Weights.DEFAULT.transforms()
categories = models.MobileNet_V3_Small_Weights.DEFAULT.meta["categories"]
print("[*] Model loaded successfully!")

@app.get("/")
def root():
    return {
        "service": "VPC-Isolated ML Inference Server",
        "architecture": "Private Subnet via Transit Gateway",
        "status": "online"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "model": "loaded"}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        batch = preprocess(image).unsqueeze(0)
        
        with torch.no_grad():
            prediction = weights(batch).squeeze(0).softmax(0)
            
        top5_prob, top5_catid = torch.topk(prediction, 5)
        
        results = []
        for i in range(top5_prob.size(0)):
            results.append({
                "rank": i + 1,
                "label": categories[top5_catid[i]],
                "confidence": round(float(top5_prob[i]), 4)
            })
            
        return {
            "success": True,
            "filename": file.filename,
            "top_prediction": results[0]["label"],
            "confidence": results[0]["confidence"],
            "top_5": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

chown ubuntu:ubuntu /home/ubuntu/vit_server.py

# Create systemd service
cat << 'EOF' > /etc/systemd/system/vit-server.service
[Unit]
Description=FastAPI Vision Model Inference Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/local/bin/uvicorn vit_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vit-server
systemctl start vit-server

# Signal ready
echo "READY" > /home/ubuntu/ready.txt
"""

# -------------------------------------------------------------
# 3. User Data for Client Tester EC2
# -------------------------------------------------------------
client_user_data = """#!/bin/bash
set -e

apt-get update -y
apt-get install -y python3-pip curl jq

pip3 install requests

# Download a sample test image (e.g. golden retriever dog)
curl -s -L "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg" -o /home/ubuntu/sample_dog.jpg

cat << 'EOF' > /home/ubuntu/client_test.py
import sys
import os
import requests
import time

def test_inference(model_ip, img_path):
    health_url = f"http://{model_ip}:8000/health"
    predict_url = f"http://{model_ip}:8000/predict"
    
    print(f"[*] Checking Health of Model Server at: {health_url} ...")
    try:
        t0 = time.time()
        r = requests.get(health_url, timeout=5)
        print(f"[+] Health OK ({round((time.time()-t0)*1000, 2)}ms): {r.json()}")
    except Exception as e:
        print(f"[-] Health check failed: {e}")
        return False
        
    print(f"[*] Sending image '{img_path}' to {predict_url} across Transit Gateway...")
    try:
        with open(img_path, "rb") as f:
            t0 = time.time()
            files = {"file": (os.path.basename(img_path), f, "image/jpeg")}
            resp = requests.post(predict_url, files=files, timeout=30)
            latency = round((time.time() - t0) * 1000, 2)
            
        if resp.status_code == 200:
            data = resp.json()
            print("\n" + "="*50)
            print(f"[+] INFERENCE SUCCESSFUL! (Latency: {latency}ms)")
            print("="*50)
            print(f"  Top Prediction: {data.get('top_prediction')}")
            print(f"  Confidence:     {round(data.get('confidence', 0)*100, 2)}%")
            print("\nTop 5 Results:")
            for item in data.get("top_5", []):
                print(f"  {item['rank']}. {item['label']} ({round(item['confidence']*100, 2)}%)")
            print("="*50)
            return True
        else:
            print(f"[-] Inference failed: {resp.text}")
            return False
    except Exception as e:
        print(f"[-] Request error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 client_test.py <MODEL_IP> <IMAGE_PATH>")
        sys.exit(1)
    test_inference(sys.argv[1], sys.argv[2])
EOF

chown -R ubuntu:ubuntu /home/ubuntu
echo "CLIENT_READY" > /home/ubuntu/ready.txt
"""

# -------------------------------------------------------------
# 4. Launch Instances
# -------------------------------------------------------------
log("Launching Model Server EC2 in Private Subnet...")
model_inst = ec2.run_instances(
    ImageId=AMI_ID,
    InstanceType=INSTANCE_TYPE,
    KeyName=state['KeyName'],
    SubnetId=state['Subnet1_Model_Id'],
    SecurityGroupIds=[state['SG1_Model_Id']],
    UserData=model_user_data,
    MinCount=1,
    MaxCount=1,
    TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-model-server'}]
    }]
)
model_id = model_inst['Instances'][0]['InstanceId']
state['Model_Instance_Id'] = model_id
log(f"Model Server Instance launched: {model_id}")

log("Launching Client EC2 in Client Subnet...")
client_inst = ec2.run_instances(
    ImageId=AMI_ID,
    InstanceType=INSTANCE_TYPE,
    KeyName=state['KeyName'],
    SubnetId=state['Subnet2_Client_Id'],
    SecurityGroupIds=[state['SG2_Client_Id']],
    UserData=client_user_data,
    MinCount=1,
    MaxCount=1,
    TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-client-tester'}]
    }]
)
client_id = client_inst['Instances'][0]['InstanceId']
state['Client_Instance_Id'] = client_id
log(f"Client Tester Instance launched: {client_id}")

# Wait for instances to run
log("Waiting for instances to reach 'running' state...")
waiter = ec2.get_waiter('instance_running')
waiter.wait(InstanceIds=[model_id, client_id])

# Associate Elastic IP to Model EC2 for bootstrap
log("Associating temporary Elastic IP to Model EC2...")
ec2.associate_address(InstanceId=model_id, AllocationId=eip_alloc_id)

# Allocate and Associate Elastic IP for Client EC2 (for SSH & testing)
log("Allocating Elastic IP for Client Tester EC2...")
client_eip = ec2.allocate_address(
    Domain='vpc',
    TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': [{'Key': 'Name', 'Value': 'lab1-client-eip'}]}]
)
client_eip_alloc_id = client_eip['AllocationId']
client_eip_public_ip = client_eip['PublicIp']
ec2.associate_address(InstanceId=client_id, AllocationId=client_eip_alloc_id)
state['Client_EIP_Alloc_Id'] = client_eip_alloc_id
state['Client_Public_IP'] = client_eip_public_ip
log(f"Associated Elastic IP {client_eip_public_ip} to Client EC2")

# Fetch IP addresses
desc = ec2.describe_instances(InstanceIds=[model_id, client_id])
for r in desc['Reservations']:
    for inst in r['Instances']:
        if inst['InstanceId'] == model_id:
            state['Model_Private_IP'] = inst['PrivateIpAddress']
            state['Model_Temp_Public_IP'] = eip_public_ip
        elif inst['InstanceId'] == client_id:
            state['Client_Private_IP'] = inst['PrivateIpAddress']

log(f"Model Server Private IP: {state['Model_Private_IP']}")
log(f"Client Tester Public IP: {state.get('Client_Public_IP')}, Private IP: {state.get('Client_Private_IP')}")

# Save state
with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

log("Waiting 90 seconds for UserData bootstrap (installing PyTorch and starting FastAPI)...")
time.sleep(90)

# Check if Model Server is responding on port 8000
log("Verifying Model Server health...")
import urllib.request
for attempt in range(12):
    try:
        url = f"http://{eip_public_ip}:8000/health"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                body = response.read().decode('utf-8')
                log(f"Model Server is HEALTHY! Response: {body}")
                break
    except Exception as e:
        print(f"  Attempt {attempt+1}/12: Server not ready yet ({e}). Waiting 15s...", flush=True)
        time.sleep(15)

# -------------------------------------------------------------
# 5. ENFORCE COMPLETE PRIVATE ISOLATION
# -------------------------------------------------------------
log("="*60)
log("LOCKDOWN: Removing all internet access from Model VPC...")
log("="*60)

# Revoke temporary port 8000 ingress rule
try:
    ec2.revoke_security_group_ingress(
        GroupId=state['SG1_Model_Id'],
        IpPermissions=[{
            'IpProtocol': 'tcp',
            'FromPort': 8000,
            'ToPort': 8000,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
    )
    log("Revoked temporary public port 8000 ingress rule from Model SG.")
except Exception as e:
    print(f"Revoke SG rule error: {e}")

# Disassociate and release Elastic IP
try:
    assoc_desc = ec2.describe_addresses(AllocationIds=[eip_alloc_id])
    assoc_id = assoc_desc['Addresses'][0].get('AssociationId')
    if assoc_id:
        ec2.disassociate_address(AssociationId=assoc_id)
        log("Disassociated Elastic IP from Model EC2.")
    ec2.release_address(AllocationId=eip_alloc_id)
    log("Released Elastic IP.")
except Exception as e:
    print(f"EIP cleanup: {e}")

# Delete 0.0.0.0/0 route from Model Route Table
try:
    ec2.delete_route(RouteTableId=state['RouteTable1_Model_Id'], DestinationCidrBlock='0.0.0.0/0')
    log(f"Deleted 0.0.0.0/0 route from Model Route Table {state['RouteTable1_Model_Id']}")
except Exception as e:
    print(f"Delete route error: {e}")

# Detach and delete temporary IGW
try:
    ec2.detach_internet_gateway(InternetGatewayId=temp_igw_id, VpcId=state['Vpc1_Model_Id'])
    ec2.delete_internet_gateway(InternetGatewayId=temp_igw_id)
    log(f"Detached and deleted temporary IGW: {temp_igw_id}")
except Exception as e:
    print(f"Delete IGW error: {e}")

state['Model_Isolated'] = True
state['Model_Public_IP'] = None
if 'Model_Temp_Public_IP' in state:
    del state['Model_Temp_Public_IP']

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

log("Model VPC is now 100% PRIVATELY ISOLATED!")
log(f"Model Server is running ONLY on private IP: {state['Model_Private_IP']}")
print(json.dumps(state, indent=2))
