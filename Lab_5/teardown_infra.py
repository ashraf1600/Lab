#!/usr/bin/env python3
"""
Infrastructure Teardown for Lab 5
Safely terminates all EC2 instances, VPN connections, gateways, and VPCs.
"""

import boto3
import json
import time
import os

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
REGION = "ap-southeast-1"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION
)
ec2 = session.client("ec2")

def teardown():
    if not os.path.exists("Lab_5/lab5_state.json"):
        print("No state file found.")
        return

    with open("Lab_5/lab5_state.json") as f:
        state = json.load(f)

    # 1. Terminate instances
    inst_ids = []
    if "cloud_inst_id" in state:
        inst_ids.append(state["cloud_inst_id"])
    if "onprem_inst_id" in state:
        inst_ids.append(state["onprem_inst_id"])
    if inst_ids:
        print(f"Terminating instances: {inst_ids}...")
        ec2.terminate_instances(InstanceIds=inst_ids)
        waiter = ec2.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=inst_ids)
        print("Instances terminated.")

    # 2. Delete VPN Connection
    if "vpn_id" in state:
        print(f"Deleting VPN Connection {state['vpn_id']}...")
        try:
            ec2.delete_vpn_connection(VpnConnectionId=state["vpn_id"])
            time.sleep(10)
        except Exception as e:
            print(f"VPN delete note: {e}")

    # 3. Delete CGW
    if "cgw_id" in state:
        print(f"Deleting Customer Gateway {state['cgw_id']}...")
        try:
            ec2.delete_customer_gateway(CustomerGatewayId=state["cgw_id"])
        except Exception as e:
            print(f"CGW delete note: {e}")

    # 4. Detach & Delete VGW
    if "vgw_id" in state and "cloud_vpc_id" in state:
        print(f"Detaching VGW {state['vgw_id']}...")
        try:
            ec2.detach_vpn_gateway(VpcId=state["cloud_vpc_id"], VpnGatewayId=state["vgw_id"])
            time.sleep(10)
            ec2.delete_vpn_gateway(VpnGatewayId=state["vgw_id"])
        except Exception as e:
            print(f"VGW delete note: {e}")

    # 5. Release EIP
    if "eip_alloc_id" in state:
        print(f"Releasing EIP {state['eip_alloc_id']}...")
        try:
            ec2.release_address(AllocationId=state["eip_alloc_id"])
        except Exception as e:
            print(f"EIP release note: {e}")

    # 6. Delete On-Prem IGW & Route Table & Subnet & VPC
    time.sleep(15)
    if "onprem_igw_id" in state and "onprem_vpc_id" in state:
        try:
            ec2.detach_internet_gateway(InternetGatewayId=state["onprem_igw_id"], VpcId=state["onprem_vpc_id"])
            ec2.delete_internet_gateway(InternetGatewayId=state["onprem_igw_id"])
        except Exception as e:
            print(f"IGW note: {e}")

    for sub in [state.get("onprem_subnet_id"), state.get("cloud_subnet_id")]:
        if sub:
            try:
                ec2.delete_subnet(SubnetId=sub)
            except Exception as e:
                print(f"Subnet delete note: {e}")

    for rt in [state.get("onprem_rt_id"), state.get("cloud_rt_id")]:
        if rt:
            try:
                ec2.delete_route_table(RouteTableId=rt)
            except Exception as e:
                print(f"RT delete note: {e}")

    for sg in [state.get("onprem_sg_id"), state.get("cloud_sg_id")]:
        if sg:
            try:
                ec2.delete_security_group(GroupId=sg)
            except Exception as e:
                print(f"SG delete note: {e}")

    for vpc in [state.get("onprem_vpc_id"), state.get("cloud_vpc_id")]:
        if vpc:
            try:
                ec2.delete_vpc(VpcId=vpc)
            except Exception as e:
                print(f"VPC delete note: {e}")

    print("Teardown completed.")

if __name__ == "__main__":
    teardown()
