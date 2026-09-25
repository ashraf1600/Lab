#!/usr/bin/env python3
"""
Clean configuration script for StrongSwan, VTI, and FRR on On-Prem Router
"""

import subprocess
import time

HOST = "52.220.40.120"
KEY = "Lab_5/lab5-keypair.pem"

def run_ssh(cmd):
    full_cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", f"ubuntu@{HOST}", cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

IPSEC_CONF = """config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn %default
    keyexchange=ikev2
    ike=aes256-sha256-modp2048,aes128-sha1-modp1024!
    esp=aes256-sha256,aes128-sha1!
    authby=secret
    dpdaction=restart
    dpddelay=10s
    dpdtimeout=30s
    auto=start

conn aws-cloud-vpc
    left=192.168.1.10
    leftid=52.220.40.120
    leftsubnet=192.168.0.0/16
    right=13.215.94.28
    rightsubnet=10.50.0.0/16
"""

IPSEC_SECRETS = """52.220.40.120 13.215.94.28 : PSK "Lab5_SecretKey_BGP_2026"
"""

STRONGSWAN_CONF = """charon {
    load_modular = yes
    plugins {
        include strongswan.d/charon/*.conf
    }
    install_routes = yes
}
include strongswan.d/*.conf
"""

VTI_SETUP = """#!/bin/bash
ip tunnel del vti1 2>/dev/null || true
ip tunnel add vti1 mode vti local 192.168.1.10 remote 13.215.94.28 okey 100
ip link set dev vti1 mtu 1426 up
ip addr add 169.254.10.2/30 dev vti1
sysctl -w net.ipv4.conf.vti1.disable_policy=1
sysctl -w net.ipv4.conf.vti1.rp_filter=0
sysctl -w net.ipv4.conf.all.rp_filter=0
sysctl -w net.ipv4.conf.default.rp_filter=0
sysctl -w net.ipv4.conf.eth0.rp_filter=0
"""

FRR_CONF = """frr version 8.1
frr defaults traditional
hostname onprem-router
service integrated-vtysh-config
!
router bgp 65000
 bgp router-id 192.168.1.10
 no bgp ebgp-requires-policy
 neighbor 169.254.10.1 remote-as 64512
 neighbor 169.254.10.1 description AWS-VGW-Tunnel-1
 neighbor 169.254.10.1 update-source 169.254.10.2
 neighbor 169.254.10.1 ebgp-multihop 2
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
"""

print("[*] Uploading StrongSwan configs...")
run_ssh(f"sudo tee /etc/ipsec.conf << 'EOF'\n{IPSEC_CONF}\nEOF")
run_ssh(f"sudo tee /etc/ipsec.secrets << 'EOF'\n{IPSEC_SECRETS}\nEOF")
run_ssh(f"sudo tee /etc/strongswan.conf << 'EOF'\n{STRONGSWAN_CONF}\nEOF")

print("[*] Cleaning up vti1...")
run_ssh("sudo ip tunnel del vti1 2>/dev/null || true")

print("[*] Restarting StrongSwan...")
run_ssh("sudo ipsec restart")
time.sleep(4)

print("[*] Checking IPsec status...")
ret, out, err = run_ssh("sudo ipsec statusall")
print(out)

