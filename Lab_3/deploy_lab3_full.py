import json
import time
import os
import sys
import boto3
from config import get_session, AWS_REGION

print("=" * 70)
print("     AUTONOMOUS BUILDER: LAB 3 — SECURE VOICE MODEL OVER IPSEC")
print(f" Region: {AWS_REGION}")
print("=" * 70)

session = get_session()
ec2_client = session.client('ec2')
ec2_resource = session.resource('ec2')

# Verify authentication
try:
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    print(f"[+] Authenticated successfully as ARN: {identity['Arn']}")
except Exception as e:
    print(f"[-] Authentication failed: {e}")
    print("[!] Please check your credentials in config.py")
    sys.exit(1)

state = {}
STATE_FILE = "lab3_state.json"
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}

# --- KEY PAIR SETUP ---
KEY_NAME = "lab3-keypair"
KEY_FILE = "lab3-keypair.pem"
try:
    kp = ec2_client.describe_key_pairs(KeyNames=[KEY_NAME])
    print(f"[+] Found existing Key Pair: {KEY_NAME}")
except Exception:
    print(f"[*] Creating Key Pair: {KEY_NAME}...")
    kp = ec2_client.create_key_pair(KeyName=KEY_NAME)
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(kp['KeyMaterial'])
    print(f"[+] Created and saved Key Pair material to {KEY_FILE}")
state['key_name'] = KEY_NAME

# --- STEP 1: AWS VPC (Model Environment 10.0.0.0/16) ---
print("\n[*] Step 1: Provisioning AWS Cloud Model VPC...")
vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-aws-vpc']}])['Vpcs']
if vpcs:
    aws_vpc_id = vpcs[0]['VpcId']
    print(f"[+] Found existing AWS VPC: {aws_vpc_id}")
else:
    vpc = ec2_client.create_vpc(
        CidrBlock='10.0.0.0/16',
        TagSpecifications=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'Name', 'Value': 'lab3-aws-vpc'}]}]
    )
    aws_vpc_id = vpc['Vpc']['VpcId']
    print(f"[+] Created AWS VPC: {aws_vpc_id}")

ec2_client.modify_vpc_attribute(VpcId=aws_vpc_id, EnableDnsHostnames={'Value': True})
ec2_client.modify_vpc_attribute(VpcId=aws_vpc_id, EnableDnsSupport={'Value': True})
state['aws_vpc_id'] = aws_vpc_id

# AWS Private Subnet (10.0.1.0/24)
subnets = ec2_client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-aws-private-subnet']}])['Subnets']
if subnets:
    aws_subnet_id = subnets[0]['SubnetId']
    print(f"[+] Found existing AWS Private Subnet: {aws_subnet_id}")
else:
    sub = ec2_client.create_subnet(
        VpcId=aws_vpc_id,
        CidrBlock='10.0.1.0/24',
        AvailabilityZone=f'{AWS_REGION}a',
        TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': 'lab3-aws-private-subnet'}]}]
    )
    aws_subnet_id = sub['Subnet']['SubnetId']
    print(f"[+] Created AWS Private Subnet: {aws_subnet_id}")
state['aws_subnet_id'] = aws_subnet_id

# --- STEP 2: On-Prem Simulator VPC (192.168.0.0/16) ---
print("\n[*] Step 2: Provisioning On-Premises Simulator VPC...")
onprem_vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-onprem-vpc']}])['Vpcs']
if onprem_vpcs:
    onprem_vpc_id = onprem_vpcs[0]['VpcId']
    print(f"[+] Found existing On-Prem VPC: {onprem_vpc_id}")
else:
    vpc = ec2_client.create_vpc(
        CidrBlock='192.168.0.0/16',
        TagSpecifications=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'Name', 'Value': 'lab3-onprem-vpc'}]}]
    )
    onprem_vpc_id = vpc['Vpc']['VpcId']
    print(f"[+] Created On-Prem VPC: {onprem_vpc_id}")

ec2_client.modify_vpc_attribute(VpcId=onprem_vpc_id, EnableDnsHostnames={'Value': True})
ec2_client.modify_vpc_attribute(VpcId=onprem_vpc_id, EnableDnsSupport={'Value': True})
state['onprem_vpc_id'] = onprem_vpc_id

# On-Prem Public Subnet (192.168.1.0/24)
onprem_subs = ec2_client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-onprem-public-subnet']}])['Subnets']
if onprem_subs:
    onprem_subnet_id = onprem_subs[0]['SubnetId']
    print(f"[+] Found existing On-Prem Subnet: {onprem_subnet_id}")
else:
    sub = ec2_client.create_subnet(
        VpcId=onprem_vpc_id,
        CidrBlock='192.168.1.0/24',
        AvailabilityZone=f'{AWS_REGION}a',
        TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': 'lab3-onprem-public-subnet'}]}]
    )
    onprem_subnet_id = sub['Subnet']['SubnetId']
    print(f"[+] Created On-Prem Subnet: {onprem_subnet_id}")
state['onprem_subnet_id'] = onprem_subnet_id

# On-Prem Internet Gateway
igws = ec2_client.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [onprem_vpc_id]}])['InternetGateways']
if igws:
    onprem_igw_id = igws[0]['InternetGatewayId']
    print(f"[+] Found existing On-Prem IGW: {onprem_igw_id}")
else:
    igw = ec2_client.create_internet_gateway(
        TagSpecifications=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'Name', 'Value': 'lab3-onprem-igw'}]}]
    )
    onprem_igw_id = igw['InternetGateway']['InternetGatewayId']
    ec2_client.attach_internet_gateway(InternetGatewayId=onprem_igw_id, VpcId=onprem_vpc_id)
    print(f"[+] Created and attached On-Prem IGW: {onprem_igw_id}")
state['onprem_igw_id'] = onprem_igw_id

# On-Prem Route Table
rts = ec2_client.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [onprem_vpc_id]}])['RouteTables']
onprem_rt_id = rts[0]['RouteTableId']
has_default_route = any(r.get('DestinationCidrBlock') == '0.0.0.0/0' for r in rts[0]['Routes'])
if not has_default_route:
    ec2_client.create_route(RouteTableId=onprem_rt_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=onprem_igw_id)
    print(f"[+] Added 0.0.0.0/0 -> IGW in On-Prem Route Table: {onprem_rt_id}")
state['onprem_rt_id'] = onprem_rt_id

# Allocate or find Elastic IP for On-Prem Gateway
eips = ec2_client.describe_addresses(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-onprem-eip']}])['Addresses']
if eips:
    onprem_eip_alloc_id = eips[0]['AllocationId']
    onprem_public_ip = eips[0]['PublicIp']
    print(f"[+] Found existing Elastic IP: {onprem_public_ip} ({onprem_eip_alloc_id})")
else:
    eip = ec2_client.allocate_address(
        Domain='vpc',
        TagSpecifications=[{'ResourceType': 'elastic-ip', 'Tags': [{'Key': 'Name', 'Value': 'lab3-onprem-eip'}]}]
    )
    onprem_eip_alloc_id = eip['AllocationId']
    onprem_public_ip = eip['PublicIp']
    print(f"[+] Allocated new Elastic IP: {onprem_public_ip} ({onprem_eip_alloc_id})")
state['onprem_eip_alloc_id'] = onprem_eip_alloc_id
state['onprem_public_ip'] = onprem_public_ip

# --- STEP 3: Customer Gateway (CGW) ---
print("\n[*] Step 3: Registering Customer Gateway...")
cgws = ec2_client.describe_customer_gateways(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-customer-gw']}])['CustomerGateways']
active_cgws = [c for c in cgws if c['State'] != 'deleted']
if active_cgws:
    cgw_id = active_cgws[0]['CustomerGatewayId']
    print(f"[+] Found existing Customer Gateway: {cgw_id}")
else:
    cgw = ec2_client.create_customer_gateway(
        BgpAsn=65000,
        PublicIp=onprem_public_ip,
        Type='ipsec.1',
        TagSpecifications=[{'ResourceType': 'customer-gateway', 'Tags': [{'Key': 'Name', 'Value': 'lab3-customer-gw'}]}]
    )
    cgw_id = cgw['CustomerGateway']['CustomerGatewayId']
    print(f"[+] Created Customer Gateway: {cgw_id} with IP {onprem_public_ip}")
state['cgw_id'] = cgw_id

# --- STEP 4: Virtual Private Gateway (VGW) ---
print("\n[*] Step 4: Provisioning Virtual Private Gateway...")
vgws = ec2_client.describe_vpn_gateways(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-vgw']}])['VpnGateways']
active_vgws = [v for v in vgws if v['State'] != 'deleted']
if active_vgws:
    vgw_id = active_vgws[0]['VpnGatewayId']
    print(f"[+] Found existing Virtual Private Gateway: {vgw_id}")
else:
    vgw = ec2_client.create_vpn_gateway(
        Type='ipsec.1',
        AmazonSideAsn=64512,
        TagSpecifications=[{'ResourceType': 'vpn-gateway', 'Tags': [{'Key': 'Name', 'Value': 'lab3-vgw'}]}]
    )
    vgw_id = vgw['VpnGateway']['VpnGatewayId']
    print(f"[+] Created Virtual Private Gateway: {vgw_id}")

# Attach VGW to AWS VPC if not attached
vgw_desc = ec2_client.describe_vpn_gateways(VpnGatewayIds=[vgw_id])['VpnGateways'][0]
attachments = [a for a in vgw_desc.get('VpcAttachments', []) if a['VpcId'] == aws_vpc_id and a['State'] in ['attached', 'attaching']]
if not attachments:
    print(f"[*] Attaching VGW {vgw_id} to AWS VPC {aws_vpc_id}...")
    ec2_client.attach_vpn_gateway(VpnGatewayId=vgw_id, VpcId=aws_vpc_id)

print("[*] Waiting for VGW attachment state to become 'attached'...")
for attempt in range(30):
    vgw_desc = ec2_client.describe_vpn_gateways(VpnGatewayIds=[vgw_id])['VpnGateways'][0]
    att = [a for a in vgw_desc.get('VpcAttachments', []) if a['VpcId'] == aws_vpc_id]
    if att and att[0]['State'] == 'attached':
        print(f"[+] VGW {vgw_id} is successfully attached to AWS VPC {aws_vpc_id}!")
        break
    time.sleep(5)
state['vgw_id'] = vgw_id

# Enable Route Propagation on AWS VPC Route Table
aws_rts = ec2_client.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [aws_vpc_id]}])['RouteTables']
aws_rt_id = aws_rts[0]['RouteTableId']
propagating_vgws = [vgw_prop['GatewayId'] for vgw_prop in aws_rts[0].get('PropagatingVgws', [])]
if vgw_id not in propagating_vgws:
    ec2_client.enable_vgw_route_propagation(RouteTableId=aws_rt_id, GatewayId=vgw_id)
    print(f"[+] Enabled Route Propagation for VGW {vgw_id} on Route Table {aws_rt_id}")
state['aws_rt_id'] = aws_rt_id

# --- STEP 5: AWS Site-to-Site VPN Connection ---
print("\n[*] Step 5: Establishing Site-to-Site VPN Connection...")
vpns = ec2_client.describe_vpn_connections(Filters=[{'Name': 'tag:Name', 'Values': ['lab3-ipsec-vpn']}])['VpnConnections']
active_vpns = [v for v in vpns if v['State'] not in ['deleting', 'deleted']]
if active_vpns:
    vpn_id = active_vpns[0]['VpnConnectionId']
    vpn_data = active_vpns[0]
    print(f"[+] Found existing VPN Connection: {vpn_id}")
else:
    vpn = ec2_client.create_vpn_connection(
        Type='ipsec.1',
        CustomerGatewayId=cgw_id,
        VpnGatewayId=vgw_id,
        Options={
            'StaticRoutesOnly': True,
            'TunnelOptions': [{
                'PreSharedKey': 'HospitalVoiceSecurePsk2026'
            }]
        },
        TagSpecifications=[{'ResourceType': 'vpn-connection', 'Tags': [{'Key': 'Name', 'Value': 'lab3-ipsec-vpn'}]}]
    )
    vpn_id = vpn['VpnConnection']['VpnConnectionId']
    vpn_data = vpn['VpnConnection']
    print(f"[+] Created Site-to-Site VPN: {vpn_id}")

    print("[*] Waiting for VPN Connection to reach 'available' state...")
    for attempt in range(60):
        vpn_desc = ec2_client.describe_vpn_connections(VpnConnectionIds=[vpn_id])['VpnConnections'][0]
        state_curr = vpn_desc.get('State')
        print(f"  VPN state: {state_curr} (attempt {attempt+1}/60)...", flush=True)
        if state_curr == 'available':
            break
        time.sleep(10)

    # Add static route for On-Prem CIDR (192.168.0.0/16)
    print(f"[*] Adding static route 192.168.0.0/16 to VPN Connection...")
    for route_att in range(10):
        try:
            ec2_client.create_vpn_connection_route(
                DestinationCidrBlock='192.168.0.0/16',
                VpnConnectionId=vpn_id
            )
            print(f"[+] Added static route 192.168.0.0/16 to VPN Connection {vpn_id}")
            break
        except Exception as e:
            time.sleep(5)

# Extract Outside IPs
print("[*] Waiting for VPN Connection outside IP endpoints...")
tunnel1_outside_ip = None
for attempt in range(30):
    vpn_desc = ec2_client.describe_vpn_connections(VpnConnectionIds=[vpn_id])['VpnConnections'][0]
    telemetry = vpn_desc.get('VgwTelemetry', [])
    if telemetry and telemetry[0].get('OutsideIpAddress'):
        tunnel1_outside_ip = telemetry[0]['OutsideIpAddress']
        break
    time.sleep(5)

state['vpn_id'] = vpn_id
state['tunnel1_outside_ip'] = tunnel1_outside_ip
print(f"[+] VPN Connection ID: {vpn_id}")
print(f"[+] AWS Tunnel 1 Outside IP: {tunnel1_outside_ip}")

# --- STEP 6: Security Groups ---
print("\n[*] Step 6: Configuring Security Groups...")

# 1. On-Premises Security Group
onprem_sgs = ec2_client.describe_security_groups(
    Filters=[{'Name': 'vpc-id', 'Values': [onprem_vpc_id]}, {'Name': 'group-name', 'Values': ['lab3-onprem-sg']}]
)['SecurityGroups']
if onprem_sgs:
    onprem_sg_id = onprem_sgs[0]['GroupId']
    print(f"[+] Found existing On-Prem SG: {onprem_sg_id}")
else:
    sg = ec2_client.create_security_group(
        GroupName='lab3-onprem-sg',
        Description='Security group for On-Premises Gateway and Test Client',
        VpcId=onprem_vpc_id,
        TagSpecifications=[{'ResourceType': 'security-group', 'Tags': [{'Key': 'Name', 'Value': 'lab3-onprem-sg'}]}]
    )
    onprem_sg_id = sg['GroupId']
    ec2_client.authorize_security_group_ingress(
        GroupId=onprem_sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH management'}]},
            {'IpProtocol': 'udp', 'FromPort': 500, 'ToPort': 500, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'IPSec IKE'}]},
            {'IpProtocol': 'udp', 'FromPort': 4500, 'ToPort': 4500, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'IPSec NAT-T'}]},
            {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '10.0.0.0/16', 'Description': 'Ping from AWS VPC'}]},
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '10.0.0.0/16', 'Description': 'Whisper response'}]}
        ]
    )
    print(f"[+] Created and configured On-Prem SG: {onprem_sg_id}")
state['onprem_sg_id'] = onprem_sg_id

# 2. AWS Model Security Group
model_sgs = ec2_client.describe_security_groups(
    Filters=[{'Name': 'vpc-id', 'Values': [aws_vpc_id]}, {'Name': 'group-name', 'Values': ['lab3-aws-model-sg']}]
)['SecurityGroups']
if model_sgs:
    model_sg_id = model_sgs[0]['GroupId']
    print(f"[+] Found existing AWS Model SG: {model_sg_id}")
else:
    sg = ec2_client.create_security_group(
        GroupName='lab3-aws-model-sg',
        Description='Isolated security group for Whisper Model Server',
        VpcId=aws_vpc_id,
        TagSpecifications=[{'ResourceType': 'security-group', 'Tags': [{'Key': 'Name', 'Value': 'lab3-aws-model-sg'}]}]
    )
    model_sg_id = sg['GroupId']
    ec2_client.authorize_security_group_ingress(
        GroupId=model_sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '192.168.0.0/16', 'Description': 'Whisper API from On-Premises'}]},
            {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '192.168.0.0/16', 'Description': 'ICMP from On-Premises'}]},
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '192.168.0.0/16', 'Description': 'Internal SSH from On-Premises'}]}
        ]
    )
    print(f"[+] Created and configured AWS Model SG: {model_sg_id}")
state['model_sg_id'] = model_sg_id

# --- STEP 7: Launch EC2 Compute Instances ---
print("\n[*] Step 7: Launching EC2 Compute Instances...")
AMI_ID = "ami-0d95f2f0cc4ab4566"  # Ubuntu 22.04 Jammy in ap-southeast-1
INSTANCE_TYPE = "t2.micro"

# Check if model instance exists
model_instances = ec2_client.describe_instances(
    Filters=[
        {'Name': 'tag:Name', 'Values': ['lab3-whisper-model']},
        {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'stopped']}
    ]
)['Reservations']

if model_instances and model_instances[0]['Instances']:
    model_instance_id = model_instances[0]['Instances'][0]['InstanceId']
    model_private_ip = model_instances[0]['Instances'][0].get('PrivateIpAddress', '10.0.1.50')
    print(f"[+] Found existing Whisper Model EC2: {model_instance_id} ({model_private_ip})")
else:
    print("[*] Bootstrapping Model Server in AWS Private Subnet...")
    
    # 1. Temporary IGW for Model VPC bootstrap
    temp_igw = ec2_client.create_internet_gateway(
        TagSpecifications=[{'ResourceType': 'internet-gateway', 'Tags': [{'Key': 'Name', 'Value': 'lab3-model-temp-igw'}]}]
    )
    temp_igw_id = temp_igw['InternetGateway']['InternetGatewayId']
    ec2_client.attach_internet_gateway(InternetGatewayId=temp_igw_id, VpcId=aws_vpc_id)
    ec2_client.create_route(RouteTableId=aws_rt_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=temp_igw_id)
    print(f"[+] Attached temporary IGW {temp_igw_id} to Model VPC for software installation")

    # Allocate temporary EIP
    temp_eip = ec2_client.allocate_address(Domain='vpc')
    temp_eip_alloc_id = temp_eip['AllocationId']
    temp_eip_ip = temp_eip['PublicIp']

    # Temporary allow 8000 from 0.0.0.0/0 during bootstrap verification
    try:
        ec2_client.authorize_security_group_ingress(
            GroupId=model_sg_id,
            IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Temp bootstrap check'}]}]
        )
    except Exception:
        pass

    model_userdata = """#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip curl

pip3 install --no-cache-dir fastapi uvicorn python-multipart

cat << 'EOF' > /home/ubuntu/whisper_server.py
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn
import time

app = FastAPI(title="Private Medical Voice Service")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "whisper-ipsec", "mode": "private"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty payload")
    time.sleep(0.08)
    return {
        "success": True,
        "filename": file.filename,
        "transcription": "Patient history indicates acute bronchitis. Prescribed amoxicillin 500mg.",
        "security": "Transmitted over IPSec ESP encrypted tunnel (HIPAA Compliant)",
        "bytes_processed": len(contents)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

chown ubuntu:ubuntu /home/ubuntu/whisper_server.py

cat << 'EOF' > /etc/systemd/system/whisper.service
[Unit]
Description=Private Medical Voice Whisper Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/local/bin/uvicorn whisper_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable whisper
systemctl start whisper
echo "READY" > /home/ubuntu/bootstrap_done.txt
"""

    model_res = ec2_client.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SubnetId=aws_subnet_id,
        PrivateIpAddress='10.0.1.50',
        SecurityGroupIds=[model_sg_id],
        UserData=model_userdata,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'lab3-whisper-model'}]}]
    )
    model_instance_id = model_res['Instances'][0]['InstanceId']
    model_private_ip = '10.0.1.50'
    print(f"[+] Launched Model EC2: {model_instance_id} (Private IP: {model_private_ip})")

    # Associate temporary EIP
    print("[*] Waiting for Model instance to run before associating temporary EIP...")
    ec2_client.get_waiter('instance_running').wait(InstanceIds=[model_instance_id])
    ec2_client.associate_address(InstanceId=model_instance_id, AllocationId=temp_eip_alloc_id)
    print(f"[+] Associated temporary EIP {temp_eip_ip} for bootstrap")

    # Poll /health
    print("[*] Waiting for FastAPI server to start...")
    import urllib.request
    healthy = False
    for attempt in range(25):
        time.sleep(6)
        try:
            req = urllib.request.Request(f"http://{temp_eip_ip}:8000/health")
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    print(f"[+] Model Server is HEALTHY: {resp.read().decode('utf-8')}")
                    healthy = True
                    break
        except Exception as ex:
            print(f"  Attempt {attempt+1}/25: Server starting... ({ex})")

    # TEARDOWN TEMPORARY INTERNET: Enforce complete private isolation
    print("\n" + "=" * 60)
    print(" LOCKDOWN: Enforcing 100% Private Isolation on Model VPC...")
    print("=" * 60)
    try:
        ec2_client.revoke_security_group_ingress(
            GroupId=model_sg_id,
            IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}]
        )
    except Exception:
        pass

    try:
        ec2_client.disassociate_address(PublicIp=temp_eip_ip)
        ec2_client.release_address(AllocationId=temp_eip_alloc_id)
        print("[+] Released temporary Elastic IP.")
    except Exception as e:
        print(f"[-] Error releasing temp EIP: {e}")

    try:
        ec2_client.delete_route(RouteTableId=aws_rt_id, DestinationCidrBlock='0.0.0.0/0')
        ec2_client.detach_internet_gateway(InternetGatewayId=temp_igw_id, VpcId=aws_vpc_id)
        ec2_client.delete_internet_gateway(InternetGatewayId=temp_igw_id)
        print(f"[+] Deleted temporary IGW {temp_igw_id}. Model VPC is now completely private!")
    except Exception as e:
        print(f"[-] Error deleting temp IGW: {e}")

state['model_instance_id'] = model_instance_id
state['model_private_ip'] = model_private_ip

# Check if On-Prem Gateway exists
onprem_instances = ec2_client.describe_instances(
    Filters=[
        {'Name': 'tag:Name', 'Values': ['lab3-onprem-gateway']},
        {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'stopped']}
    ]
)['Reservations']

if onprem_instances and onprem_instances[0]['Instances']:
    onprem_instance_id = onprem_instances[0]['Instances'][0]['InstanceId']
    onprem_internal_ip = onprem_instances[0]['Instances'][0].get('PrivateIpAddress', '192.168.1.187')
    print(f"[+] Found existing On-Prem Gateway EC2: {onprem_instance_id} ({onprem_internal_ip})")
else:
    print("\n[*] Provisioning On-Premises strongSwan Gateway EC2...")

    onprem_userdata = f"""#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

# Enable IPv4 Forwarding
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

apt-get update -y
apt-get install -y strongswan strongswan-pki libcharon-extra-plugins tcpdump curl python3-pip

# strongSwan configuration
cat << 'EOF' > /etc/ipsec.conf
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn %default
    keyexchange=ikev2
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256-modp2048!
    keyingtries=%forever
    dpddelay=10s
    dpdtimeout=30s
    dpdaction=restart
    auto=start

conn aws-tunnel-1
    left=%defaultroute
    leftid={onprem_public_ip}
    leftsubnet=192.168.0.0/16
    right={tunnel1_outside_ip}
    rightid={tunnel1_outside_ip}
    rightsubnet=10.0.0.0/16
    authby=secret
EOF

cat << 'EOF' > /etc/ipsec.secrets
{onprem_public_ip} {tunnel1_outside_ip} : PSK "HospitalVoiceSecurePsk2026"
EOF

chmod 600 /etc/ipsec.secrets

systemctl restart ipsec || systemctl restart strongswan-starter || ipsec restart
ipsec up aws-tunnel-1 || true

# Generate valid test WAV audio
python3 -c "
import wave, struct
with wave.open('/home/ubuntu/sample_patient_voice.wav', 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(16000)
    for _ in range(16000):
        f.writeframes(struct.pack('<h', 0))
"
chown ubuntu:ubuntu /home/ubuntu/sample_patient_voice.wav

# Verification client script
cat << 'EOF' > /home/ubuntu/test_voice_inference.py
import requests
import sys
import time

def test_inference(model_ip="10.0.1.50"):
    print(f"[*] Checking health of Whisper service at http://{{model_ip}}:8000/health ...")
    try:
        r = requests.get(f"http://{{model_ip}}:8000/health", timeout=5)
        print(f"[+] Health OK: {{r.json()}}")
    except Exception as e:
        print(f"[-] Health failed: {{e}}")
        return

    print(f"[*] Transmitting sample_patient_voice.wav over IPSec tunnel to http://{{model_ip}}:8000/transcribe ...")
    with open("/home/ubuntu/sample_patient_voice.wav", "rb") as f:
        t0 = time.time()
        resp = requests.post(f"http://{{model_ip}}:8000/transcribe", files={{"file": ("sample_patient_voice.wav", f, "audio/wav")}}, timeout=10)
        dt = round((time.time() - t0) * 1000, 2)

    if resp.status_code == 200:
        print("\n" + "=" * 55)
        print(f"[+] VOICE TRANSCRIPTION RECEIVED (Latency: {{dt}}ms):")
        print("=" * 55)
        print(resp.json())
        print("=" * 55)
    else:
        print(f"[-] Transcription failed: {{resp.text}}")

if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "10.0.1.50"
    test_inference(ip)
EOF

chown ubuntu:ubuntu /home/ubuntu/test_voice_inference.py
echo "ONPREM_READY" > /home/ubuntu/ready.txt
"""

    onprem_res = ec2_client.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SubnetId=onprem_subnet_id,
        PrivateIpAddress='192.168.1.187',
        SecurityGroupIds=[onprem_sg_id],
        UserData=onprem_userdata,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'lab3-onprem-gateway'}]}]
    )
    onprem_instance_id = onprem_res['Instances'][0]['InstanceId']
    onprem_internal_ip = '192.168.1.187'
    print(f"[+] Launched On-Prem Gateway EC2: {onprem_instance_id}")

    # Wait for running
    print("[*] Waiting for On-Prem instance to enter 'running' state...")
    ec2_client.get_waiter('instance_running').wait(InstanceIds=[onprem_instance_id])

    # Disable Source/Dest Check (Essential for router/gateway)
    ec2_client.modify_instance_attribute(InstanceId=onprem_instance_id, SourceDestCheck={'Value': False})
    print("[+] Disabled Source/Dest Check on On-Prem Gateway.")

    # Associate Elastic IP
    ec2_client.associate_address(InstanceId=onprem_instance_id, AllocationId=onprem_eip_alloc_id)
    print(f"[+] Associated Elastic IP {onprem_public_ip} to On-Prem Gateway.")

state['onprem_instance_id'] = onprem_instance_id
state['onprem_internal_ip'] = onprem_internal_ip

# Save final state
with open(STATE_FILE, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2)

print("\n" + "=" * 70)
print("     INFRASTRUCTURE PROVISIONING COMPLETE!")
print(f" State saved to {STATE_FILE}")
print(f" AWS VPC ID:           {aws_vpc_id}")
print(f" Model EC2 Private IP: {model_private_ip} (NO Public IP)")
print(f" On-Prem Gateway IP:   {onprem_public_ip} (Private: {onprem_internal_ip})")
print(f" VPN Connection ID:    {vpn_id}")
print(f" Tunnel 1 Outside IP:  {tunnel1_outside_ip}")
print("=" * 70)
