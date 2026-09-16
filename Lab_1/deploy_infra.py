#!/usr/bin/env python3
"""
Deploy Lab 1: VPC-Isolated ML Inference Endpoint using AWS Transit Gateway
Region: ap-southeast-1 (Singapore)
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
KEY_NAME = "lab1-keypair"
KEY_FILE = os.path.join(OUTPUT_DIR, "lab1-keypair.pem")

state = {}

def log(msg):
    print(f"\n[+] {msg}", flush=True)

# -------------------------------------------------------------
# 1. Key Pair
# -------------------------------------------------------------
log("Step 1: Setting up Key Pair...")
try:
    ec2.delete_key_pair(KeyName=KEY_NAME)
except Exception:
    pass

key_res = ec2.create_key_pair(KeyName=KEY_NAME)
with open(KEY_FILE, "w") as f:
    f.write(key_res['KeyMaterial'])
log(f"Key pair created and saved to {KEY_FILE}")
state['KeyName'] = KEY_NAME

# -------------------------------------------------------------
# 2. VPCs & Subnets
# -------------------------------------------------------------
log("Step 2: Creating VPC 1 (Model VPC: 10.0.0.0/16)...")
vpc1_res = ec2.create_vpc(
    CidrBlock='10.0.0.0/16',
    TagSpecifications=[{
        'ResourceType': 'vpc',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-model-vpc'}]
    }]
)
vpc1_id = vpc1_res['Vpc']['VpcId']
ec2.modify_vpc_attribute(VpcId=vpc1_id, EnableDnsHostnames={'Value': True})
ec2.modify_vpc_attribute(VpcId=vpc1_id, EnableDnsSupport={'Value': True})
state['Vpc1_Model_Id'] = vpc1_id
log(f"Model VPC Created: {vpc1_id}")

log("Step 2b: Creating VPC 2 (Client VPC: 10.1.0.0/16)...")
vpc2_res = ec2.create_vpc(
    CidrBlock='10.1.0.0/16',
    TagSpecifications=[{
        'ResourceType': 'vpc',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-client-vpc'}]
    }]
)
vpc2_id = vpc2_res['Vpc']['VpcId']
ec2.modify_vpc_attribute(VpcId=vpc2_id, EnableDnsHostnames={'Value': True})
ec2.modify_vpc_attribute(VpcId=vpc2_id, EnableDnsSupport={'Value': True})
state['Vpc2_Client_Id'] = vpc2_id
log(f"Client VPC Created: {vpc2_id}")

# Subnets
log("Creating Subnets in ap-southeast-1a...")
sub1_res = ec2.create_subnet(
    VpcId=vpc1_id,
    CidrBlock='10.0.1.0/24',
    AvailabilityZone='ap-southeast-1a',
    TagSpecifications=[{
        'ResourceType': 'subnet',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-model-private-subnet'}]
    }]
)
subnet1_id = sub1_res['Subnet']['SubnetId']
state['Subnet1_Model_Id'] = subnet1_id
log(f"Model Private Subnet Created: {subnet1_id} (10.0.1.0/24)")

sub2_res = ec2.create_subnet(
    VpcId=vpc2_id,
    CidrBlock='10.1.1.0/24',
    AvailabilityZone='ap-southeast-1a',
    TagSpecifications=[{
        'ResourceType': 'subnet',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-client-subnet'}]
    }]
)
subnet2_id = sub2_res['Subnet']['SubnetId']
state['Subnet2_Client_Id'] = subnet2_id
log(f"Client Subnet Created: {subnet2_id} (10.1.1.0/24)")

# Client VPC Internet Gateway (for SSH and testing)
log("Attaching Internet Gateway to Client VPC...")
igw_res = ec2.create_internet_gateway(
    TagSpecifications=[{
        'ResourceType': 'internet-gateway',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-client-igw'}]
    }]
)
igw_id = igw_res['InternetGateway']['InternetGatewayId']
ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc2_id)
state['Client_IGW_Id'] = igw_id
log(f"Client IGW Created & Attached: {igw_id}")

# Route Tables
log("Configuring Route Tables...")
# Model Route Table (Strictly Private - NO IGW)
rt1_res = ec2.create_route_table(
    VpcId=vpc1_id,
    TagSpecifications=[{
        'ResourceType': 'route-table',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-model-rt'}]
    }]
)
rt1_id = rt1_res['RouteTable']['RouteTableId']
ec2.associate_route_table(RouteTableId=rt1_id, SubnetId=subnet1_id)
state['RouteTable1_Model_Id'] = rt1_id
log(f"Model Private Route Table Created: {rt1_id}")

# Client Route Table (with IGW for SSH management)
rt2_res = ec2.create_route_table(
    VpcId=vpc2_id,
    TagSpecifications=[{
        'ResourceType': 'route-table',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-client-rt'}]
    }]
)
rt2_id = rt2_res['RouteTable']['RouteTableId']
ec2.associate_route_table(RouteTableId=rt2_id, SubnetId=subnet2_id)
ec2.create_route(
    RouteTableId=rt2_id,
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=igw_id
)
state['RouteTable2_Client_Id'] = rt2_id
log(f"Client Route Table Created with IGW route: {rt2_id}")

# -------------------------------------------------------------
# 3. AWS Transit Gateway (TGW)
# -------------------------------------------------------------
log("Step 3: Creating AWS Transit Gateway (TGW)...")
tgw_res = ec2.create_transit_gateway(
    Description='Transit Gateway connecting Model VPC and Client VPC',
    Options={
        'AmazonSideAsn': 64512,
        'AutoAcceptSharedAttachments': 'enable',
        'DefaultRouteTableAssociation': 'enable',
        'DefaultRouteTablePropagation': 'enable',
        'DnsSupport': 'enable',
        'VpnEcmpSupport': 'enable'
    },
    TagSpecifications=[{
        'ResourceType': 'transit-gateway',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-tgw'}]
    }]
)
tgw_id = tgw_res['TransitGateway']['TransitGatewayId']
state['TransitGatewayId'] = tgw_id
log(f"Transit Gateway requested: {tgw_id}. Waiting for 'available' state (this takes ~1-2 minutes)...")

while True:
    tgw_status = ec2.describe_transit_gateways(TransitGatewayIds=[tgw_id])['TransitGateways'][0]['State']
    print(f"  TGW Status: {tgw_status}", flush=True)
    if tgw_status == 'available':
        break
    time.sleep(10)

log(f"Transit Gateway is AVAILABLE: {tgw_id}")

# Attach VPC 1 to TGW
log("Attaching Model VPC to Transit Gateway...")
tgw_att1 = ec2.create_transit_gateway_vpc_attachment(
    TransitGatewayId=tgw_id,
    VpcId=vpc1_id,
    SubnetIds=[subnet1_id],
    TagSpecifications=[{
        'ResourceType': 'transit-gateway-attachment',
        'Tags': [{'Key': 'Name', 'Value': 'tgw-attach-model-vpc'}]
    }]
)
att1_id = tgw_att1['TransitGatewayVpcAttachment']['TransitGatewayAttachmentId']
state['TGW_Attachment1_Id'] = att1_id
log(f"Model VPC TGW Attachment requested: {att1_id}")

# Attach VPC 2 to TGW
log("Attaching Client VPC to Transit Gateway...")
tgw_att2 = ec2.create_transit_gateway_vpc_attachment(
    TransitGatewayId=tgw_id,
    VpcId=vpc2_id,
    SubnetIds=[subnet2_id],
    TagSpecifications=[{
        'ResourceType': 'transit-gateway-attachment',
        'Tags': [{'Key': 'Name', 'Value': 'tgw-attach-client-vpc'}]
    }]
)
att2_id = tgw_att2['TransitGatewayVpcAttachment']['TransitGatewayAttachmentId']
state['TGW_Attachment2_Id'] = att2_id
log(f"Client VPC TGW Attachment requested: {att2_id}")

log("Waiting for TGW Attachments to become 'available'...")
while True:
    atts = ec2.describe_transit_gateway_vpc_attachments(TransitGatewayAttachmentIds=[att1_id, att2_id])['TransitGatewayVpcAttachments']
    states = [a['State'] for a in atts]
    print(f"  Attachment states: {states}", flush=True)
    if all(s == 'available' for s in states):
        break
    time.sleep(10)

# Add Cross-VPC Routes to Transit Gateway
log("Updating VPC Route Tables to point cross-VPC traffic to Transit Gateway...")
ec2.create_route(
    RouteTableId=rt1_id,
    DestinationCidrBlock='10.1.0.0/16',
    TransitGatewayId=tgw_id
)
log("  Model Route Table: Added route 10.1.0.0/16 -> TGW")

ec2.create_route(
    RouteTableId=rt2_id,
    DestinationCidrBlock='10.0.0.0/16',
    TransitGatewayId=tgw_id
)
log("  Client Route Table: Added route 10.0.0.0/16 -> TGW")

# -------------------------------------------------------------
# 4. Security Groups
# -------------------------------------------------------------
log("Step 4: Setting up Security Groups...")

# Model SG (VPC 1)
sg1_res = ec2.create_security_group(
    GroupName='lab1-model-sg',
    Description='Security group for private Model Server',
    VpcId=vpc1_id,
    TagSpecifications=[{
        'ResourceType': 'security-group',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-model-sg'}]
    }]
)
sg1_id = sg1_res['GroupId']
state['SG1_Model_Id'] = sg1_id

ec2.authorize_security_group_ingress(
    GroupId=sg1_id,
    IpPermissions=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 8000,
            'ToPort': 8000,
            'IpRanges': [{'CidrIp': '10.1.0.0/16', 'Description': 'FastAPI from Client VPC'}]
        },
        {
            'IpProtocol': 'icmp',
            'FromPort': -1,
            'ToPort': -1,
            'IpRanges': [{'CidrIp': '10.1.0.0/16', 'Description': 'ICMP Ping from Client VPC'}]
        },
        {
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '10.1.0.0/16', 'Description': 'SSH from Client VPC'}]
        }
    ]
)
log(f"Model SG Created: {sg1_id} (Allows port 8000 & ICMP from 10.1.0.0/16)")

# Client SG (VPC 2)
sg2_res = ec2.create_security_group(
    GroupName='lab1-client-sg',
    Description='Security group for Client Tester',
    VpcId=vpc2_id,
    TagSpecifications=[{
        'ResourceType': 'security-group',
        'Tags': [{'Key': 'Name', 'Value': 'lab1-client-sg'}]
    }]
)
sg2_id = sg2_res['GroupId']
state['SG2_Client_Id'] = sg2_id

ec2.authorize_security_group_ingress(
    GroupId=sg2_id,
    IpPermissions=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH from anywhere'}]
        },
        {
            'IpProtocol': 'icmp',
            'FromPort': -1,
            'ToPort': -1,
            'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'ICMP Ping'}]
        }
    ]
)
log(f"Client SG Created: {sg2_id} (Allows SSH port 22)")

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

log("Phase 1 - 4 Infrastructure Deployment SUCCESSFUL!")
print(json.dumps(state, indent=2))
