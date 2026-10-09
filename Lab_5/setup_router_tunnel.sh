#!/bin/bash
set -x

# 1. Enable IP forwarding and disable rp_filter
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -w net.ipv4.conf.all.rp_filter=0
sysctl -w net.ipv4.conf.default.rp_filter=0
sysctl -w net.ipv4.conf.eth0.rp_filter=0

# 2. Setup XFRM interface ipsec0 with if_id 100
ip link del ipsec0 2>/dev/null || true
ip link add ipsec0 type xfrm dev eth0 if_id 100
ip link set ipsec0 up
ip addr add 169.254.10.2/30 remote 169.254.10.1 dev ipsec0
sysctl -w net.ipv4.conf.ipsec0.disable_policy=1
sysctl -w net.ipv4.conf.ipsec0.rp_filter=0

# 3. strongSwan Secrets
cat << 'EOF' > /etc/ipsec.secrets
54.151.194.132 18.141.117.198 : PSK "Lab5_SecretKey_BGP_2026"
EOF

# 4. strongSwan Conf
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
    left=10.0.1.10
    leftid=54.151.194.132
    leftsubnet=0.0.0.0/0
    right=18.141.117.198
    rightsubnet=0.0.0.0/0
    if_id_in=100
    if_id_out=100
EOF

# Restart strongSwan
systemctl restart strongswan-starter || ipsec restart
sleep 3
ipsec status

# 5. Configure BIRD 2
cat << 'EOF' > /etc/bird/bird.conf
log syslog all;
router id 10.0.1.10;

protocol device {
}

protocol direct {
    ipv4;
}

protocol kernel {
    ipv4 {
        export all;
        import all;
    };
}

protocol bgp aws_tunnel1 {
    local 169.254.10.2 as 65000;
    neighbor 169.254.10.1 as 64512;
    hold time 30;
    ipv4 {
        import all;
        export where net = 10.0.0.0/16;
    };
}
EOF

systemctl restart bird
sleep 2

# 6. IPTables NAT
iptables -t nat -C POSTROUTING -o ipsec0 -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -o ipsec0 -j MASQUERADE

# 7. Connectivity Verification
echo "=== PING 169.254.10.1 ==="
ping -c 3 169.254.10.1 || true

echo "=== BIRDC PROTOCOLS ==="
birdc show protocols
