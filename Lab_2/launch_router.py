import boto3
import json
import base64
import gzip
import os

s = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")
)
ec2_c = s.client('ec2')
ec2_r = s.resource('ec2')

# Find subnet
subnets = {t['Value']: s['SubnetId'] for s in ec2_c.describe_subnets()['Subnets'] for t in s.get('Tags', []) if t['Key']=='Name'}
subnet_router_id = subnets.get('lab2-router-public-subnet')
print(f"[*] Subnet Router: {subnet_router_id}")

# Find SG
sgs = {g['GroupName']: g['GroupId'] for g in ec2_c.describe_security_groups()['SecurityGroups']}
sg_router_id = sgs.get('lab2-router-sg')
print(f"[*] SG Router: {sg_router_id}")

# Latest AMI
images = ec2_c.describe_images(
    Owners=['amazon'],
    Filters=[
        {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
        {'Name': 'state', 'Values': ['available']}
    ]
)
ami_id = sorted(images['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]['ImageId']

base_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_dir, "src", "bgp_router.py"), "r") as f:
    bgp_code = f.read()
with open(os.path.join(base_dir, "monitoring", "prometheus.yml"), "r") as f:
    prom_yaml = f.read()
with open(os.path.join(base_dir, "monitoring", "grafana_dashboard.json"), "r") as f:
    grafana_json = f.read()

bgp_b64 = base64.b64encode(gzip.compress(bgp_code.encode())).decode()
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

print(f"[*] User Data Size: {len(router_user_data)} bytes (Limit is 16384 bytes)")

print("[*] Launching lab2-bgp-router...")
inst_router = ec2_r.create_instances(
    ImageId=ami_id,
    InstanceType='t2.micro',
    KeyName='lab2-keypair',
    MinCount=1,
    MaxCount=1,
    NetworkInterfaces=[{
        'SubnetId': subnet_router_id,
        'DeviceIndex': 0,
        'AssociatePublicIpAddress': True,
        'PrivateIpAddress': '172.16.1.10',
        'Groups': [sg_router_id]
    }],
    UserData=router_user_data,
    TagSpecifications=[{
        'ResourceType': 'instance',
        'Tags': [{'Key': 'Name', 'Value': 'lab2-bgp-router'}, {'Key': 'Role', 'Value': 'BGP-Gateway-Observability'}]
    }]
)[0]

print(f"[+] Instance ID: {inst_router.id}. Waiting for it to run...")
inst_router.wait_until_running()
inst_router.reload()
print(f"[+] Router is RUNNING!")
print(f"    Public IP:  {inst_router.public_ip_address}")
print(f"    Private IP: {inst_router.private_ip_address}")

# Save state
state_file = os.path.join(base_dir, "lab2_state.json")
state = {}
if os.path.exists(state_file):
    try:
        with open(state_file) as f:
            state = json.load(f)
    except Exception:
        pass

# Populate all current IDs from AWS
vpcs = {t['Value']: v['VpcId'] for v in ec2_c.describe_vpcs()['Vpcs'] for t in v.get('Tags', []) if t['Key']=='Name'}
instances = {t['Value']: i for r in ec2_c.describe_instances()['Reservations'] for i in r['Instances'] for t in i.get('Tags', []) if t['Key']=='Name'}

state["vpc_a_id"] = vpcs.get("lab2-regionA-vpc")
state["vpc_b_id"] = vpcs.get("lab2-regionB-vpc")
state["vpc_router_id"] = vpcs.get("lab2-router-vpc")
state["subnet_a_id"] = subnets.get("lab2-regionA-private-subnet")
state["subnet_b_id"] = subnets.get("lab2-regionB-private-subnet")
state["subnet_router_id"] = subnet_router_id
state["sg_a_id"] = sgs.get("lab2-modelA-sg")
state["sg_b_id"] = sgs.get("lab2-modelB-sg")
state["sg_router_id"] = sg_router_id

if "lab2-regionA-model" in instances:
    ia = instances["lab2-regionA-model"]
    state["inst_a_id"] = ia["InstanceId"]
    state["inst_a_private_ip"] = ia.get("PrivateIpAddress")

if "lab2-regionB-model" in instances:
    ib = instances["lab2-regionB-model"]
    state["inst_b_id"] = ib["InstanceId"]
    state["inst_b_private_ip"] = ib.get("PrivateIpAddress")

state["inst_router_id"] = inst_router.id
state["inst_router_private_ip"] = inst_router.private_ip_address
state["inst_router_public_ip"] = inst_router.public_ip_address

with open(state_file, "w") as f:
    json.dump(state, f, indent=2)

print(f"[+] Successfully updated {state_file}")
