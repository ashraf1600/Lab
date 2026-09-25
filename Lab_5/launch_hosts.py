#!/usr/bin/env python3
"""
Dedicated host launcher and state recorder for Lab 5
"""
import os
import boto3
import json
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

# Ensure cloud instance ID is saved
state["cloud_inst_id"] = "i-0e0285e32a603dc28"

outside_ip_1 = "13.215.94.28"
eip_public_ip = state["eip_public_ip"]
eip_alloc_id = state["eip_alloc_id"]
onprem_subnet_id = state["onprem_subnet_id"]
onprem_sg_id = state["onprem_sg_id"]

onprem_ud = f"""#!/bin/bash
set -ex
mkdir -p /opt/onprem

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

# Install StrongSwan and FRR
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y strongswan strongswan-pki libcharon-extra-plugins frr

# Write StrongSwan IPsec Config
cat << 'EOF' > /etc/ipsec.secrets
{eip_public_ip} {outside_ip_1} : PSK "Lab5_SecretKey_BGP_2026"
EOF

cat << 'EOF' > /etc/ipsec.conf
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn %default
    keyexchange=ikev2
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256!
    authby=secret
    dpdaction=restart
    dpddelay=10s
    dpdtimeout=30s
    auto=start

conn aws-tunnel-1
    left=192.168.1.10
    leftid={eip_public_ip}
    leftsubnet=0.0.0.0/0
    leftupdown=/etc/ipsec.d/vti1.sh
    right={outside_ip_1}
    rightsubnet=0.0.0.0/0
    mark=100
EOF

# VTI script for StrongSwan
cat << 'EOF' > /etc/ipsec.d/vti1.sh
#!/bin/bash
case "$PLUTO_VERB" in
    up-client)
        ip tunnel add vti1 mode vti local 192.168.1.10 remote {outside_ip_1} okey 100 ikey 100 || true
        ip link set vti1 up
        ip addr add 169.254.10.2/30 remote 169.254.10.1 dev vti1 || true
        sysctl -w net.ipv4.conf.vti1.disable_policy=1
        ;;
    down-client)
        ip tunnel del vti1 || true
        ;;
esac
EOF
chmod +x /etc/ipsec.d/vti1.sh

# Configure FRR (BGP)
cat << 'EOF' > /etc/frr/daemons
zebra=yes
bgpd=yes
EOF

cat << 'EOF' > /etc/frr/frr.conf
frr version 8.1
frr defaults traditional
hostname onprem-router
service integrated-vtysh-config
!
router bgp 65000
 bgp router-id 192.168.1.10
 neighbor 169.254.10.1 remote-as 64512
 neighbor 169.254.10.1 description AWS-VGW-Tunnel-1
 neighbor 169.254.10.1 timers 10 30
 !
 address-family ipv4 unicast
  network 192.168.0.0/16
  neighbor 169.254.10.1 activate
  neighbor 169.254.10.1 soft-reconfiguration inbound
 exit-address-family
!
line vty
!
EOF

systemctl restart strongswan-starter || ipsec restart
systemctl restart frr
"""

print(f"Launching on-prem router with UserData size: {len(onprem_ud)} bytes...")

inst = ec2.run_instances(
    ImageId=UBUNTU_AMI,
    InstanceType="t2.micro",
    KeyName=KEY_PAIR_NAME,
    MinCount=1,
    MaxCount=1,
    NetworkInterfaces=[{
        "DeviceIndex": 0,
        "SubnetId": onprem_subnet_id,
        "AssociatePublicIpAddress": False,
        "PrivateIpAddress": "192.168.1.10",
        "Groups": [onprem_sg_id]
    }],
    UserData=onprem_ud,
    TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "lab5-onprem-router"}]}]
)["Instances"][0]

inst_id = inst["InstanceId"]
state["onprem_inst_id"] = inst_id
print("Launched On-Prem Router:", inst_id)

print("Waiting for On-Prem instance to be running...")
waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=[inst_id])

ec2.associate_address(AllocationId=eip_alloc_id, InstanceId=inst_id)
print(f"Associated EIP {eip_public_ip}!")

ec2.modify_instance_attribute(InstanceId=inst_id, SourceDestCheck={"Value": False})
print("Disabled SourceDestCheck.")

with open("Lab_5/lab5_state.json", "w") as f:
    json.dump(state, f, indent=2)
print("State saved successfully!")
