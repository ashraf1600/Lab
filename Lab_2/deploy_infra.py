import os
import sys
import time
import json
import boto3

# Add directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from config import (
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION,
    KEY_NAME, KEY_FILE, STATE_FILE,
    VPC_A_CIDR, SUBNET_A_CIDR, REGION_A_NAME,
    VPC_B_CIDR, SUBNET_B_CIDR, REGION_B_NAME,
    VPC_ROUTER_CIDR, SUBNET_ROUTER_CIDR, REGION_ROUTER_NAME
)

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
ec2_client = session.client('ec2')
ec2_resource = session.resource('ec2')

def create_key_pair():
    print(f"[*] Checking/Creating Key Pair: {KEY_NAME}...")
    try:
        keys = ec2_client.describe_key_pairs(KeyNames=[KEY_NAME])
        print(f"[+] Key pair {KEY_NAME} already exists in AWS.")
    except ec2_client.exceptions.ClientError:
        key_pair = ec2_client.create_key_pair(KeyName=KEY_NAME)
        with open(KEY_FILE, "w") as f:
            f.write(key_pair['KeyMaterial'])
        print(f"[+] Created and saved key pair to {KEY_FILE}")
    return KEY_NAME

def get_latest_ubuntu_ami():
    images = ec2_client.describe_images(
        Owners=['amazon'],
        Filters=[
            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
            {'Name': 'state', 'Values': ['available']}
        ]
    )
    sorted_imgs = sorted(images['Images'], key=lambda x: x['CreationDate'], reverse=True)
    return sorted_imgs[0]['ImageId']

def deploy():
    print("==================================================================")
    print(" Deploying Lab 2: Multi-Region ML Serving with BGP Failover Infra ")
    print("==================================================================")
    
    state = {}
    key_name = create_key_pair()
    state["key_name"] = key_name
    ami_id = get_latest_ubuntu_ami()
    state["ami_id"] = ami_id
    print(f"[*] Using Ubuntu AMI: {ami_id}")

    # 1. Create VPC Region A (Primary)
    print(f"\n[*] Creating VPC Region A ({REGION_A_NAME} - {VPC_A_CIDR})...")
    vpc_a = ec2_resource.create_vpc(CidrBlock=VPC_A_CIDR)
    vpc_a.wait_until_available()
    vpc_a.create_tags(Tags=[{'Key': 'Name', 'Value': REGION_A_NAME}, {'Key': 'Lab', 'Value': 'Lab2'}])
    state["vpc_a_id"] = vpc_a.id
    print(f"[+] VPC Region A Created: {vpc_a.id}")

    # Subnet A
    subnet_a = vpc_a.create_subnet(
        CidrBlock=SUBNET_A_CIDR,
        AvailabilityZone=f"{AWS_REGION}a"
    )
    subnet_a.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-regionA-private-subnet'}])
    state["subnet_a_id"] = subnet_a.id
    print(f"[+] Subnet Region A Created: {subnet_a.id} ({SUBNET_A_CIDR})")

    # 2. Create VPC Region B (Failover)
    print(f"\n[*] Creating VPC Region B ({REGION_B_NAME} - {VPC_B_CIDR})...")
    vpc_b = ec2_resource.create_vpc(CidrBlock=VPC_B_CIDR)
    vpc_b.wait_until_available()
    vpc_b.create_tags(Tags=[{'Key': 'Name', 'Value': REGION_B_NAME}, {'Key': 'Lab', 'Value': 'Lab2'}])
    state["vpc_b_id"] = vpc_b.id
    print(f"[+] VPC Region B Created: {vpc_b.id}")

    # Subnet B
    subnet_b = vpc_b.create_subnet(
        CidrBlock=SUBNET_B_CIDR,
        AvailabilityZone=f"{AWS_REGION}b"
    )
    subnet_b.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-regionB-private-subnet'}])
    state["subnet_b_id"] = subnet_b.id
    print(f"[+] Subnet Region B Created: {subnet_b.id} ({SUBNET_B_CIDR})")

    # 3. Create VPC Router / Edge
    print(f"\n[*] Creating VPC Router ({REGION_ROUTER_NAME} - {VPC_ROUTER_CIDR})...")
    vpc_router = ec2_resource.create_vpc(CidrBlock=VPC_ROUTER_CIDR)
    vpc_router.wait_until_available()
    vpc_router.create_tags(Tags=[{'Key': 'Name', 'Value': REGION_ROUTER_NAME}, {'Key': 'Lab', 'Value': 'Lab2'}])
    state["vpc_router_id"] = vpc_router.id
    print(f"[+] VPC Router Created: {vpc_router.id}")

    # Subnet Router (Public)
    subnet_router = vpc_router.create_subnet(
        CidrBlock=SUBNET_ROUTER_CIDR,
        AvailabilityZone=f"{AWS_REGION}a"
    )
    subnet_router.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-router-public-subnet'}])
    state["subnet_router_id"] = subnet_router.id
    print(f"[+] Subnet Router Created: {subnet_router.id} ({SUBNET_ROUTER_CIDR})")

    # Internet Gateway for Router VPC
    igw = ec2_resource.create_internet_gateway()
    igw.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-router-igw'}])
    vpc_router.attach_internet_gateway(InternetGatewayId=igw.id)
    state["igw_id"] = igw.id
    print(f"[+] Internet Gateway Attached: {igw.id}")

    # 4. VPC Peering Connections
    print("\n[*] Establishing VPC Peering Connections...")
    # Router <-> Region A
    pcx_a = ec2_client.create_vpc_peering_connection(
        VpcId=vpc_router.id,
        PeerVpcId=vpc_a.id,
        TagSpecifications=[{
            'ResourceType': 'vpc-peering-connection',
            'Tags': [{'Key': 'Name', 'Value': 'lab2-peering-router-to-regionA'}]
        }]
    )['VpcPeeringConnection']
    pcx_a_id = pcx_a['VpcPeeringConnectionId']
    ec2_client.accept_vpc_peering_connection(VpcPeeringConnectionId=pcx_a_id)
    state["peering_a_id"] = pcx_a_id
    print(f"[+] Peering Connection Router <-> Region A: {pcx_a_id} (Accepted)")

    # Router <-> Region B
    pcx_b = ec2_client.create_vpc_peering_connection(
        VpcId=vpc_router.id,
        PeerVpcId=vpc_b.id,
        TagSpecifications=[{
            'ResourceType': 'vpc-peering-connection',
            'Tags': [{'Key': 'Name', 'Value': 'lab2-peering-router-to-regionB'}]
        }]
    )['VpcPeeringConnection']
    pcx_b_id = pcx_b['VpcPeeringConnectionId']
    ec2_client.accept_vpc_peering_connection(VpcPeeringConnectionId=pcx_b_id)
    state["peering_b_id"] = pcx_b_id
    print(f"[+] Peering Connection Router <-> Region B: {pcx_b_id} (Accepted)")

    # 5. Route Tables
    print("\n[*] Configuring Route Tables...")
    # Router Route Table
    rt_router = vpc_router.create_route_table()
    rt_router.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-router-rt'}])
    rt_router.associate_with_subnet(SubnetId=subnet_router.id)
    rt_router.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=igw.id)
    rt_router.create_route(DestinationCidrBlock=VPC_A_CIDR, VpcPeeringConnectionId=pcx_a_id)
    rt_router.create_route(DestinationCidrBlock=VPC_B_CIDR, VpcPeeringConnectionId=pcx_b_id)
    state["rt_router_id"] = rt_router.id
    print(f"[+] Router RT configured with IGW + Peering routes to Region A & B")

    # Region A Route Table
    rt_a = vpc_a.create_route_table()
    rt_a.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-regionA-rt'}])
    rt_a.associate_with_subnet(SubnetId=subnet_a.id)
    rt_a.create_route(DestinationCidrBlock=VPC_ROUTER_CIDR, VpcPeeringConnectionId=pcx_a_id)
    state["rt_a_id"] = rt_a.id
    print(f"[+] Region A RT configured with return route to Router VPC")

    # Region B Route Table
    rt_b = vpc_b.create_route_table()
    rt_b.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-regionB-rt'}])
    rt_b.associate_with_subnet(SubnetId=subnet_b.id)
    rt_b.create_route(DestinationCidrBlock=VPC_ROUTER_CIDR, VpcPeeringConnectionId=pcx_b_id)
    state["rt_b_id"] = rt_b.id
    print(f"[+] Region B RT configured with return route to Router VPC")

    # 6. Security Groups
    print("\n[*] Setting up Security Groups...")
    # SG Router
    sg_router = ec2_resource.create_security_group(
        GroupName='lab2-router-sg',
        Description='BGP Gateway, Prometheus, Grafana SG',
        VpcId=vpc_router.id
    )
    sg_router.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-router-sg'}])
    sg_router.authorize_ingress(
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH'}]},
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'BGP VIP Inference API'}]},
            {'IpProtocol': 'tcp', 'FromPort': 9090, 'ToPort': 9090, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Prometheus UI'}]},
            {'IpProtocol': 'tcp', 'FromPort': 3000, 'ToPort': 3000, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Grafana UI'}]},
            {'IpProtocol': 'tcp', 'FromPort': 9000, 'ToPort': 9000, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'MinIO S3 API'}]},
            {'IpProtocol': 'tcp', 'FromPort': 9001, 'ToPort': 9001, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'MinIO Web Console'}]},
            {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Ping'}]}
        ]
    )
    state["sg_router_id"] = sg_router.id
    print(f"[+] Security Group Router created: {sg_router.id}")

    # SG Region A
    sg_a = ec2_resource.create_security_group(
        GroupName='lab2-modelA-sg',
        Description='Model Server Region A Private SG',
        VpcId=vpc_a.id
    )
    sg_a.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-modelA-sg'}])
    sg_a.authorize_ingress(
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': VPC_ROUTER_CIDR, 'Description': 'Whisper API from Router'}]},
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': VPC_ROUTER_CIDR, 'Description': 'SSH from Router'}]},
            {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': VPC_ROUTER_CIDR, 'Description': 'Ping from Router'}]}
        ]
    )
    state["sg_a_id"] = sg_a.id
    print(f"[+] Security Group Region A created: {sg_a.id}")

    # SG Region B
    sg_b = ec2_resource.create_security_group(
        GroupName='lab2-modelB-sg',
        Description='Model Server Region B Private SG',
        VpcId=vpc_b.id
    )
    sg_b.create_tags(Tags=[{'Key': 'Name', 'Value': 'lab2-modelB-sg'}])
    sg_b.authorize_ingress(
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': VPC_ROUTER_CIDR, 'Description': 'Whisper API from Router'}]},
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': VPC_ROUTER_CIDR, 'Description': 'SSH from Router'}]},
            {'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': VPC_ROUTER_CIDR, 'Description': 'Ping from Router'}]}
        ]
    )
    state["sg_b_id"] = sg_b.id
    print(f"[+] Security Group Region B created: {sg_b.id}")

    # 7. User Data Startup Scripts
    with open(os.path.join(BASE_DIR, "src", "whisper_server.py"), "r") as f:
        whisper_code = f.read()
    with open(os.path.join(BASE_DIR, "src", "bgp_router.py"), "r") as f:
        bgp_router_code = f.read()
    with open(os.path.join(BASE_DIR, "monitoring", "prometheus.yml"), "r") as f:
        prom_yaml = f.read()
    with open(os.path.join(BASE_DIR, "monitoring", "grafana_dashboard.json"), "r") as f:
        grafana_json = f.read()

    whisper_user_data_a = f"""#!/bin/bash
cat << 'EOF' > /home/ubuntu/whisper_server.py
{whisper_code}
EOF

cat << 'EOF' > /etc/systemd/system/whisper.service
[Unit]
Description=Whisper Region A Service
After=network.target

[Service]
Type=simple
User=ubuntu
Environment="REGION_NAME=Region-A-Primary-Cloud"
Environment="REGION_CODE=ap-southeast-1a"
Environment="PORT=8000"
ExecStart=/usr/bin/python3 /home/ubuntu/whisper_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

chown -R ubuntu:ubuntu /home/ubuntu
systemctl daemon-reload
systemctl enable whisper
systemctl restart whisper
"""

    whisper_user_data_b = f"""#!/bin/bash
cat << 'EOF' > /home/ubuntu/whisper_server.py
{whisper_code}
EOF

cat << 'EOF' > /etc/systemd/system/whisper.service
[Unit]
Description=Whisper Region B Service
After=network.target

[Service]
Type=simple
User=ubuntu
Environment="REGION_NAME=Region-B-Failover-On-Prem"
Environment="REGION_CODE=ap-southeast-1b"
Environment="PORT=8000"
ExecStart=/usr/bin/python3 /home/ubuntu/whisper_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

chown -R ubuntu:ubuntu /home/ubuntu
systemctl daemon-reload
systemctl enable whisper
systemctl restart whisper
    import gzip
    import base64
    bgp_b64 = base64.b64encode(gzip.compress(bgp_router_code.encode())).decode()
    grafana_b64 = base64.b64encode(gzip.compress(grafana_json.encode())).decode()

    router_user_data = f"""#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip prometheus wget curl gnupg software-properties-common

# Install Grafana
mkdir -p /etc/apt/keyrings/
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | tee /etc/apt/sources.list.d/grafana.list
apt-get update -y
apt-get install -y grafana

# Python dependencies
pip3 install fastapi uvicorn httpx requests prometheus_client

# BGP Router application (decompressed)
echo "{bgp_b64}" | base64 -d | gzip -d > /home/ubuntu/bgp_router.py

# Prometheus Configuration
cat << 'EOF' > /etc/prometheus/prometheus.yml
{prom_yaml}
EOF
systemctl restart prometheus
systemctl enable prometheus

# Grafana Provisioning
mkdir -p /etc/grafana/provisioning/datasources
cat << 'EOF' > /etc/grafana/provisioning/datasources/prometheus.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
EOF

mkdir -p /etc/grafana/provisioning/dashboards
mkdir -p /var/lib/grafana/dashboards
cat << 'EOF' > /etc/grafana/provisioning/dashboards/dashboard.yaml
apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

echo "{grafana_b64}" | base64 -d | gzip -d > /var/lib/grafana/dashboards/lab2_dashboard.json

chown -R grafana:grafana /etc/grafana /var/lib/grafana
systemctl restart grafana-server
systemctl enable grafana-server

# MinIO S3-Compatible Object Store
wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio
chmod +x /usr/local/bin/minio
mkdir -p /data/minio/models

cat << 'EOF' > /etc/systemd/system/minio.service
[Unit]
Description=MinIO S3 Compatible Object Storage
After=network.target

[Service]
Type=simple
User=root
Environment="MINIO_ROOT_USER=minioadmin"
Environment="MINIO_ROOT_PASSWORD=minioadmin"
ExecStart=/usr/local/bin/minio server /data/minio --console-address ":9001" --address ":9000"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable minio
systemctl start minio

# BGP Router Service
cat << 'EOF' > /etc/systemd/system/bgp-router.service
[Unit]
Description=BGP Dynamic Route Controller and Inference Gateway
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="REGION_A_IP=10.0.1.100"
Environment="REGION_B_IP=10.1.1.100"
Environment="PORT=8000"
ExecStart=/usr/bin/python3 -m uvicorn bgp_router:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

chown -R ubuntu:ubuntu /home/ubuntu
systemctl daemon-reload
systemctl enable bgp-router
systemctl restart bgp-router
"""

    # 8. Launch EC2 Instances
    print("\n[*] Launching EC2 Instances...")

    # Region A Model Server (Private IP 10.0.1.100)
    print(" -> Launching lab2-regionA-model in Region A Subnet (10.0.1.100)...")
    inst_a = ec2_resource.create_instances(
        ImageId=ami_id,
        InstanceType='t2.micro',
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{
            'SubnetId': subnet_a.id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': False,
            'PrivateIpAddress': '10.0.1.100',
            'Groups': [sg_a.id]
        }],
        UserData=whisper_user_data_a,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'lab2-regionA-model'}, {'Key': 'Role', 'Value': 'Primary-Model'}]
        }]
    )[0]
    state["inst_a_id"] = inst_a.id

    # Region B Model Server (Private IP 10.1.1.100)
    print(" -> Launching lab2-regionB-model in Region B Subnet (10.1.1.100)...")
    inst_b = ec2_resource.create_instances(
        ImageId=ami_id,
        InstanceType='t2.micro',
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{
            'SubnetId': subnet_b.id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': False,
            'PrivateIpAddress': '10.1.1.100',
            'Groups': [sg_b.id]
        }],
        UserData=whisper_user_data_b,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'lab2-regionB-model'}, {'Key': 'Role', 'Value': 'Failover-Model'}]
        }]
    )[0]
    state["inst_b_id"] = inst_b.id

    # BGP Gateway / Router (Public Subnet)
    print(" -> Launching lab2-bgp-router in Router Subnet (Public)...")
    inst_router = ec2_resource.create_instances(
        ImageId=ami_id,
        InstanceType='t2.micro',
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[{
            'SubnetId': subnet_router.id,
            'DeviceIndex': 0,
            'AssociatePublicIpAddress': True,
            'PrivateIpAddress': '172.16.1.10',
            'Groups': [sg_router.id]
        }],
        UserData=router_user_data,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'lab2-bgp-router'}, {'Key': 'Role', 'Value': 'BGP-Gateway-Observability'}]
        }]
    )[0]
    state["inst_router_id"] = inst_router.id

    print("\n[*] Waiting for EC2 instances to become RUNNING...")
    inst_a.wait_until_running()
    inst_b.wait_until_running()
    inst_router.wait_until_running()

    inst_a.reload()
    inst_b.reload()
    inst_router.reload()

    state["inst_a_private_ip"] = inst_a.private_ip_address
    state["inst_b_private_ip"] = inst_b.private_ip_address
    state["inst_router_private_ip"] = inst_router.private_ip_address
    state["inst_router_public_ip"] = inst_router.public_ip_address

    print(f"\n[+] Region A Model Instance : {inst_a.id} (Private: {inst_a.private_ip_address})")
    print(f"[+] Region B Model Instance : {inst_b.id} (Private: {inst_b.private_ip_address})")
    print(f"[+] BGP Router / Gateway   : {inst_router.id} (Private: {inst_router.private_ip_address}, Public: {inst_router.public_ip_address})")

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"\n[OK] Deployment successfully completed and saved to {STATE_FILE}!")

if __name__ == "__main__":
    deploy()
