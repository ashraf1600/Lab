#!/usr/bin/env python3
"""
Automated Infrastructure Deployment for Lab 5 (Idempotent & Resilient)
Provisions all VPCs, Subnets, Gateways, VPN Connection, and EC2 Hosts in ap-southeast-1.
Saves all resource IDs and state to lab5_state.json.
"""

import boto3
import json
import time
import base64
import os

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

state = {}
if os.path.exists("Lab_5/lab5_state.json"):
    try:
        with open("Lab_5/lab5_state.json") as f:
            state = json.load(f)
    except Exception:
        state = {}

def log(msg):
    print(f"[{time.strftime('%X')}] {msg}")

def wait_for_vgw_attachment(vgw_id, vpc_id):
    log(f"Waiting for VGW {vgw_id} attachment to {vpc_id} to become 'attached'...")
    for _ in range(30):
        res = ec2.describe_vpn_gateways(VpnGatewayIds=[vgw_id])
        attachments = res["VpnGateways"][0].get("VpcAttachments", [])
        for att in attachments:
            if att.get("VpcId") == vpc_id and att.get("State") == "attached":
                log(f"VGW {vgw_id} is now ATTACHED to {vpc_id}!")
                return True
        time.sleep(5)
    raise TimeoutError(f"VGW {vgw_id} did not attach in time.")

def deploy():
    log("Starting Lab 5 Infrastructure Deployment...")

    # 1. Cloud Private VPC
    cloud_vpc_id = state.get("cloud_vpc_id")
    if not cloud_vpc_id:
        # Check if already tagged in AWS
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag:Name", "Values": ["lab5-cloud-vpc"]}])["Vpcs"]
        if vpcs:
            cloud_vpc_id = vpcs[0]["VpcId"]
        else:
            log("Creating Cloud Private VPC (10.50.0.0/16)...")
            cloud_vpc = ec2.create_vpc(
                CidrBlock="10.50.0.0/16",
                TagSpecifications=[{"ResourceType": "vpc", "Tags": [{"Key": "Name", "Value": "lab5-cloud-vpc"}]}]
            )["Vpc"]
            cloud_vpc_id = cloud_vpc["VpcId"]
        ec2.modify_vpc_attribute(VpcId=cloud_vpc_id, EnableDnsHostnames={"Value": True})
        ec2.modify_vpc_attribute(VpcId=cloud_vpc_id, EnableDnsSupport={"Value": True})
        state["cloud_vpc_id"] = cloud_vpc_id
    log(f"Cloud VPC: {cloud_vpc_id}")

    # Cloud Subnet
    cloud_subnet_id = state.get("cloud_subnet_id")
    if not cloud_subnet_id:
        subnets = ec2.describe_subnets(Filters=[{"Name": "tag:Name", "Values": ["lab5-cloud-private-subnet"]}])["Subnets"]
        if subnets:
            cloud_subnet_id = subnets[0]["SubnetId"]
        else:
            log("Creating Cloud Private Subnet (10.50.1.0/24 in ap-southeast-1a)...")
            cloud_subnet = ec2.create_subnet(
                VpcId=cloud_vpc_id,
                CidrBlock="10.50.1.0/24",
                AvailabilityZone="ap-southeast-1a",
                TagSpecifications=[{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": "lab5-cloud-private-subnet"}]}]
            )["Subnet"]
            cloud_subnet_id = cloud_subnet["SubnetId"]
        state["cloud_subnet_id"] = cloud_subnet_id
    log(f"Cloud Private Subnet: {cloud_subnet_id}")

    # Cloud VGW
    vgw_id = state.get("vgw_id")
    if not vgw_id:
        vgws = ec2.describe_vpn_gateways(Filters=[{"Name": "tag:Name", "Values": ["lab5-cloud-vgw"]}])["VpnGateways"]
        if vgws:
            vgw_id = vgws[0]["VpnGatewayId"]
        else:
            log("Creating AWS Virtual Private Gateway (ASN: 64512)...")
            vgw = ec2.create_vpn_gateway(
                Type="ipsec.1",
                AmazonSideAsn=64512,
                TagSpecifications=[{"ResourceType": "vpn-gateway", "Tags": [{"Key": "Name", "Value": "lab5-cloud-vgw"}]}]
            )["VpnGateway"]
            vgw_id = vgw["VpnGatewayId"]
        state["vgw_id"] = vgw_id
    log(f"VGW: {vgw_id}")

    # Attach VGW to Cloud VPC
    res = ec2.describe_vpn_gateways(VpnGatewayIds=[vgw_id])
    attachments = res["VpnGateways"][0].get("VpcAttachments", [])
    attached = any(a.get("VpcId") == cloud_vpc_id and a.get("State") in ["attaching", "attached"] for a in attachments)
    if not attached:
        log(f"Attaching VGW {vgw_id} to VPC {cloud_vpc_id}...")
        ec2.attach_vpn_gateway(VpcId=cloud_vpc_id, VpnGatewayId=vgw_id)
    wait_for_vgw_attachment(vgw_id, cloud_vpc_id)

    # Cloud Route Table
    cloud_rt_id = state.get("cloud_rt_id")
    if not cloud_rt_id:
        rts = ec2.describe_route_tables(Filters=[{"Name": "tag:Name", "Values": ["lab5-cloud-private-rt"]}])["RouteTables"]
        if rts:
            cloud_rt_id = rts[0]["RouteTableId"]
        else:
            log("Configuring Cloud Private Route Table...")
            cloud_rt = ec2.create_route_table(
                VpcId=cloud_vpc_id,
                TagSpecifications=[{"ResourceType": "route-table", "Tags": [{"Key": "Name", "Value": "lab5-cloud-private-rt"}]}]
            )["RouteTable"]
            cloud_rt_id = cloud_rt["RouteTableId"]
            ec2.associate_route_table(SubnetId=cloud_subnet_id, RouteTableId=cloud_rt_id)
        state["cloud_rt_id"] = cloud_rt_id
    
    # Enable Route Propagation
    try:
        ec2.enable_vgw_route_propagation(GatewayId=vgw_id, RouteTableId=cloud_rt_id)
        log("Route Propagation enabled on Cloud Private RT.")
    except Exception as e:
        log(f"Route propagation note: {e}")

    # Cloud Security Group
    cloud_sg_id = state.get("cloud_sg_id")
    if not cloud_sg_id:
        sgs = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": ["lab5-cloud-ml-sg"]}])["SecurityGroups"]
        if sgs:
            cloud_sg_id = sgs[0]["GroupId"]
        else:
            log("Creating Cloud Security Group (lab5-cloud-ml-sg)...")
            cloud_sg = ec2.create_security_group(
                GroupName="lab5-cloud-ml-sg",
                Description="Security Group for Private Air-Gapped ML Host",
                VpcId=cloud_vpc_id,
                TagSpecifications=[{"ResourceType": "security-group", "Tags": [{"Key": "Name", "Value": "lab5-cloud-ml-sg"}]}]
            )
            cloud_sg_id = cloud_sg["GroupId"]
            ec2.authorize_security_group_ingress(
                GroupId=cloud_sg_id,
                IpPermissions=[
                    {"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "IpRanges": [{"CidrIp": "192.168.0.0/16", "Description": "FastAPI from On-Premises"}]},
                    {"IpProtocol": "icmp", "FromPort": -1, "ToPort": -1, "IpRanges": [{"CidrIp": "192.168.0.0/16", "Description": "Ping from On-Premises"}]},
                    {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "192.168.0.0/16", "Description": "SSH from On-Premises"}]}
                ]
            )
        state["cloud_sg_id"] = cloud_sg_id
    log(f"Cloud SG: {cloud_sg_id}")

    # 2. Simulated On-Premises VPC
    onprem_vpc_id = state.get("onprem_vpc_id")
    if not onprem_vpc_id:
        vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag:Name", "Values": ["lab5-onprem-vpc"]}])["Vpcs"]
        if vpcs:
            onprem_vpc_id = vpcs[0]["VpcId"]
        else:
            log("Creating Simulated On-Premises VPC (192.168.0.0/16)...")
            onprem_vpc = ec2.create_vpc(
                CidrBlock="192.168.0.0/16",
                TagSpecifications=[{"ResourceType": "vpc", "Tags": [{"Key": "Name", "Value": "lab5-onprem-vpc"}]}]
            )["Vpc"]
            onprem_vpc_id = onprem_vpc["VpcId"]
        ec2.modify_vpc_attribute(VpcId=onprem_vpc_id, EnableDnsHostnames={"Value": True})
        ec2.modify_vpc_attribute(VpcId=onprem_vpc_id, EnableDnsSupport={"Value": True})
        state["onprem_vpc_id"] = onprem_vpc_id
    log(f"On-Prem VPC: {onprem_vpc_id}")

    # On-Prem Subnet
    onprem_subnet_id = state.get("onprem_subnet_id")
    if not onprem_subnet_id:
        subnets = ec2.describe_subnets(Filters=[{"Name": "tag:Name", "Values": ["lab5-onprem-public-subnet"]}])["Subnets"]
        if subnets:
            onprem_subnet_id = subnets[0]["SubnetId"]
        else:
            log("Creating On-Prem Public Subnet (192.168.1.0/24 in ap-southeast-1a)...")
            onprem_subnet = ec2.create_subnet(
                VpcId=onprem_vpc_id,
                CidrBlock="192.168.1.0/24",
                AvailabilityZone="ap-southeast-1a",
                TagSpecifications=[{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": "lab5-onprem-public-subnet"}]}]
            )["Subnet"]
            onprem_subnet_id = onprem_subnet["SubnetId"]
        state["onprem_subnet_id"] = onprem_subnet_id
    log(f"On-Prem Subnet: {onprem_subnet_id}")

    # On-Prem IGW
    onprem_igw_id = state.get("onprem_igw_id")
    if not onprem_igw_id:
        igws = ec2.describe_internet_gateways(Filters=[{"Name": "tag:Name", "Values": ["lab5-onprem-igw"]}])["InternetGateways"]
        if igws:
            onprem_igw_id = igws[0]["InternetGatewayId"]
        else:
            log("Creating On-Prem Internet Gateway...")
            onprem_igw = ec2.create_internet_gateway(
                TagSpecifications=[{"ResourceType": "internet-gateway", "Tags": [{"Key": "Name", "Value": "lab5-onprem-igw"}]}]
            )["InternetGateway"]
            onprem_igw_id = onprem_igw["InternetGatewayId"]
            ec2.attach_internet_gateway(InternetGatewayId=onprem_igw_id, VpcId=onprem_vpc_id)
        state["onprem_igw_id"] = onprem_igw_id
    log(f"On-Prem IGW: {onprem_igw_id}")

    # On-Prem Route Table
    onprem_rt_id = state.get("onprem_rt_id")
    if not onprem_rt_id:
        rts = ec2.describe_route_tables(Filters=[{"Name": "tag:Name", "Values": ["lab5-onprem-rt"]}])["RouteTables"]
        if rts:
            onprem_rt_id = rts[0]["RouteTableId"]
        else:
            log("Configuring On-Prem Route Table...")
            onprem_rt = ec2.create_route_table(
                VpcId=onprem_vpc_id,
                TagSpecifications=[{"ResourceType": "route-table", "Tags": [{"Key": "Name", "Value": "lab5-onprem-rt"}]}]
            )["RouteTable"]
            onprem_rt_id = onprem_rt["RouteTableId"]
            ec2.create_route(RouteTableId=onprem_rt_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=onprem_igw_id)
            ec2.associate_route_table(SubnetId=onprem_subnet_id, RouteTableId=onprem_rt_id)
        state["onprem_rt_id"] = onprem_rt_id
    log(f"On-Prem Route Table: {onprem_rt_id}")

    # Allocate Elastic IP for On-Prem Router
    eip_alloc_id = state.get("eip_alloc_id")
    eip_public_ip = state.get("eip_public_ip")
    if not eip_alloc_id:
        eips = ec2.describe_addresses(Filters=[{"Name": "tag:Name", "Values": ["lab5-onprem-router-eip"]}])["Addresses"]
        if eips:
            eip_alloc_id = eips[0]["AllocationId"]
            eip_public_ip = eips[0]["PublicIp"]
        else:
            log("Allocating Elastic IP for On-Prem Router...")
            eip = ec2.allocate_address(
                Domain="vpc",
                TagSpecifications=[{"ResourceType": "elastic-ip", "Tags": [{"Key": "Name", "Value": "lab5-onprem-router-eip"}]}]
            )
            eip_alloc_id = eip["AllocationId"]
            eip_public_ip = eip["PublicIp"]
        state["eip_alloc_id"] = eip_alloc_id
        state["eip_public_ip"] = eip_public_ip
    log(f"Elastic IP: {eip_public_ip} ({eip_alloc_id})")

    # On-Prem Security Group
    onprem_sg_id = state.get("onprem_sg_id")
    if not onprem_sg_id:
        sgs = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": ["lab5-onprem-router-sg"]}])["SecurityGroups"]
        if sgs:
            onprem_sg_id = sgs[0]["GroupId"]
        else:
            log("Creating On-Prem Router Security Group (lab5-onprem-router-sg)...")
            onprem_sg = ec2.create_security_group(
                GroupName="lab5-onprem-router-sg",
                Description="Security Group for On-Prem BGP VPN Router & Dashboard",
                VpcId=onprem_vpc_id,
                TagSpecifications=[{"ResourceType": "security-group", "Tags": [{"Key": "Name", "Value": "lab5-onprem-router-sg"}]}]
            )
            onprem_sg_id = onprem_sg["GroupId"]
            ec2.authorize_security_group_ingress(
                GroupId=onprem_sg_id,
                IpPermissions=[
                    {"IpProtocol": "udp", "FromPort": 500, "ToPort": 500, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "IPsec IKE"}]},
                    {"IpProtocol": "udp", "FromPort": 4500, "ToPort": 4500, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "IPsec NAT-T"}]},
                    {"IpProtocol": "50", "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "IPsec ESP"}]},
                    {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH"}]},
                    {"IpProtocol": "tcp", "FromPort": 8501, "ToPort": 8501, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Dashboard"}]},
                    {"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Local API"}]},
                    {"IpProtocol": "icmp", "FromPort": -1, "ToPort": -1, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Ping"}]}
                ]
            )
        state["onprem_sg_id"] = onprem_sg_id
    log(f"On-Prem SG: {onprem_sg_id}")

    # 3. AWS Customer Gateway
    cgw_id = state.get("cgw_id")
    if not cgw_id:
        cgws = ec2.describe_customer_gateways(Filters=[{"Name": "tag:Name", "Values": ["lab5-onprem-cgw"]}])["CustomerGateways"]
        # Filter available
        cgws = [c for c in cgws if c.get("State") != "deleted"]
        if cgws:
            cgw_id = cgws[0]["CustomerGatewayId"]
        else:
            log(f"Creating Customer Gateway (BGP ASN: 65000, IP: {eip_public_ip})...")
            cgw = ec2.create_customer_gateway(
                BgpAsn=65000,
                PublicIp=eip_public_ip,
                Type="ipsec.1",
                TagSpecifications=[{"ResourceType": "customer-gateway", "Tags": [{"Key": "Name", "Value": "lab5-onprem-cgw"}]}]
            )["CustomerGateway"]
            cgw_id = cgw["CustomerGatewayId"]
        state["cgw_id"] = cgw_id
    log(f"Customer Gateway: {cgw_id}")

    # 4. AWS Site-to-Site VPN Connection with Dynamic BGP
    vpn_id = state.get("vpn_id")
    if not vpn_id:
        vpns = ec2.describe_vpn_connections(Filters=[{"Name": "tag:Name", "Values": ["lab5-bgp-vpn"]}])["VpnConnections"]
        vpns = [v for v in vpns if v.get("State") != "deleted"]
        if vpns:
            vpn_id = vpns[0]["VpnConnectionId"]
        else:
            log("Creating AWS Site-to-Site VPN Connection (lab5-bgp-vpn)...")
            vpn = ec2.create_vpn_connection(
                CustomerGatewayId=cgw_id,
                VpnGatewayId=vgw_id,
                Type="ipsec.1",
                Options={
                    "StaticRoutesOnly": False,
                    "TunnelOptions": [
                        {
                            "TunnelInsideCidr": "169.254.10.0/30",
                            "PreSharedKey": "Lab5_SecretKey_BGP_2026"
                        },
                        {
                            "TunnelInsideCidr": "169.254.11.0/30",
                            "PreSharedKey": "Lab5_SecretKey_BGP_2026"
                        }
                    ]
                },
                TagSpecifications=[{"ResourceType": "vpn-connection", "Tags": [{"Key": "Name", "Value": "lab5-bgp-vpn"}]}]
            )["VpnConnection"]
            vpn_id = vpn["VpnConnectionId"]
        state["vpn_id"] = vpn_id
    log(f"VPN Connection: {vpn_id}")

    # Retrieve VPN configuration details
    log("Fetching VPN outside endpoint IP addresses...")
    vpn_desc = ec2.describe_vpn_connections(VpnConnectionIds=[vpn_id])["VpnConnections"][0]
    tunnels = vpn_desc.get("VgwTelemetry", [])
    outside_ip_1 = tunnels[0].get("OutsideIpAddress") if len(tunnels) > 0 else ""
    outside_ip_2 = tunnels[1].get("OutsideIpAddress") if len(tunnels) > 1 else ""
    state["outside_ip_1"] = outside_ip_1
    state["outside_ip_2"] = outside_ip_2
    log(f"VPN Tunnel 1 Outside IP: {outside_ip_1}")
    log(f"VPN Tunnel 2 Outside IP: {outside_ip_2}")

    # 5. Launch Cloud ML Host (Private IP: 10.50.1.100)
    cloud_inst_id = state.get("cloud_inst_id")
    if not cloud_inst_id:
        insts = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["lab5-cloud-ml-host"]}, {"Name": "instance-state-name", "Values": ["running", "pending"]}])
        existing_insts = [i for r in insts["Reservations"] for i in r["Instances"]]
        if existing_insts:
            cloud_inst_id = existing_insts[0]["InstanceId"]
        else:
            log("Launching Cloud ML Host in Private Subnet (10.50.1.100)...")
            with open("Lab_5/src/model_server.py", "r") as f:
                model_server_code = f.read()

            cloud_userdata_raw = f"""#!/bin/bash
set -ex
mkdir -p /opt/ml-pipeline
cat << 'EOF' > /opt/ml-pipeline/model_server.py
{model_server_code}
EOF
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
            cloud_ud_b64 = base64.b64encode(cloud_userdata_raw.encode('utf-8')).decode('utf-8')
            cloud_inst = ec2.run_instances(
                ImageId=UBUNTU_AMI,
                InstanceType="t2.micro",
                KeyName=KEY_PAIR_NAME,
                MinCount=1,
                MaxCount=1,
                NetworkInterfaces=[{
                    'DeviceIndex': 0,
                    'SubnetId': cloud_subnet_id,
                    'AssociatePublicIpAddress': False,
                    'PrivateIpAddress': '10.50.1.100',
                    'Groups': [cloud_sg_id]
                }],
                UserData=cloud_ud_b64,
                TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "lab5-cloud-ml-host"}]}]
            )["Instances"][0]
            cloud_inst_id = cloud_inst["InstanceId"]
        state["cloud_inst_id"] = cloud_inst_id
    log(f"Cloud ML Host: {cloud_inst_id} (10.50.1.100)")

    # 6. Launch On-Premises Router Host (Private IP: 192.168.1.10)
    onprem_inst_id = state.get("onprem_inst_id")
    if not onprem_inst_id:
        insts = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["lab5-onprem-router"]}, {"Name": "instance-state-name", "Values": ["running", "pending"]}])
        existing_insts = [i for r in insts["Reservations"] for i in r["Instances"]]
        if existing_insts:
            onprem_inst_id = existing_insts[0]["InstanceId"]
        else:
            log("Launching On-Premises Router Host (192.168.1.10)...")
            with open("Lab_5/src/onprem_dashboard.py", "r") as f:
                dashboard_code = f.read()

            onprem_userdata_raw = f"""#!/bin/bash
set -ex
mkdir -p /opt/onprem
cat << 'EOF' > /opt/onprem/onprem_dashboard.py
{dashboard_code}
EOF
chmod +x /opt/onprem/*.py

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

# Start Dashboard systemd service
cat << 'EOF' > /etc/systemd/system/onprem-dashboard.service
[Unit]
Description=On-Premises Real-Time Telemetry Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/onprem
ExecStart=/usr/bin/python3 /opt/onprem/onprem_dashboard.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now onprem-dashboard.service
"""
            onprem_ud_b64 = base64.b64encode(onprem_userdata_raw.encode('utf-8')).decode('utf-8')
            onprem_inst = ec2.run_instances(
                ImageId=UBUNTU_AMI,
                InstanceType="t2.micro",
                KeyName=KEY_PAIR_NAME,
                MinCount=1,
                MaxCount=1,
                NetworkInterfaces=[{
                    'DeviceIndex': 0,
                    'SubnetId': onprem_subnet_id,
                    'AssociatePublicIpAddress': False,
                    'PrivateIpAddress': '192.168.1.10',
                    'Groups': [onprem_sg_id]
                }],
                UserData=onprem_ud_b64,
                TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "lab5-onprem-router"}]}]
            )["Instances"][0]
            onprem_inst_id = onprem_inst["InstanceId"]

            log("Waiting for On-Prem instance to be running before associating EIP...")
            waiter = ec2.get_waiter("instance_running")
            waiter.wait(InstanceIds=[onprem_inst_id])

            ec2.associate_address(AllocationId=eip_alloc_id, InstanceId=onprem_inst_id)
            log(f"Elastic IP {eip_public_ip} associated with {onprem_inst_id}!")

            ec2.modify_instance_attribute(InstanceId=onprem_inst_id, SourceDestCheck={"Value": False})
            log("Source/Dest check disabled on On-Prem Router.")

        state["onprem_inst_id"] = onprem_inst_id
    log(f"On-Prem Router: {onprem_inst_id} (192.168.1.10, EIP: {eip_public_ip})")

    # Save complete State
    with open("Lab_5/lab5_state.json", "w") as f:
        json.dump(state, f, indent=2)
    log("All infrastructure is active! State saved to Lab_5/lab5_state.json.")

if __name__ == "__main__":
    deploy()
