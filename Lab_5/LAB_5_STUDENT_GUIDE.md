# Lab 5: End-to-End Encrypted ML Pipeline with BGP and IPsec VPN

## Introduction

This lab teaches you how to design, deploy, and validate a secure, end-to-end encrypted hybrid-cloud machine learning architecture on AWS. You will interconnect an air-gapped private Virtual Private Cloud (VPC) hosting an isolated NLP inference service to an on-premises enterprise environment using an IPsec Virtual Private Network (VPN) with dynamic Border Gateway Protocol (BGP) routing. Through hands-on configuration, active retrieval, and chaos testing, you will enforce cryptographic protection for data in transit and data at rest without exposing model workloads to the public internet.

![Lab 5 Architecture](lab5-architecture.svg)

## Learning Objectives

By the end of this lab, you will be able to:

1. Design an air-gapped AWS VPC topology with zero Internet Gateways and zero public IP addresses.
2. Configure hybrid cloud connectivity using an AWS Virtual Private Gateway, Customer Gateway, and Site-to-Site VPN with dynamic BGP routing.
3. Configure IPsec encryption (IKEv2/ESP) and BGP peering on a Linux enterprise edge router.
4. Implement a zero-dependency NLP classification microservice with salted HMAC and stream encryption for data persistence.
5. Execute positive, negative, and chaos tampering experiments to prove traffic isolation and network self-healing.

**Prerequisites:** Proficiency with basic Linux command-line operations, foundational AWS networking concepts (VPC, CIDR, subnets, route tables), and Python programming.

## Prologue: The Challenge

You join the machine learning platform team at a healthcare financial technology enterprise. The organization analyzes patient clinical records and sensitive transactional metadata to detect fraudulent billing claims. Under regulatory frameworks including HIPAA and PCI-DSS, transmitting raw patient text across the public internet or placing model inference clusters in internet-facing subnets is strictly prohibited.

The current system relies on manual batch data transfers over removable media, causing significant processing backlogs and audit compliance risks. Your task is to build a continuous, real-time hybrid cloud pipeline. You must establish an air-gapped model inference environment in AWS, connect it to the on-premises facility through an IPsec tunnel using dynamic BGP route exchanges, and verify that all inferences are securely classified and encrypted at rest in a zero-knowledge audit store.

## Environment Setup

Update your system repositories and install the required networking and Python tools:

```bash
sudo apt update
sudo apt install -y strongswan bird2 curl jq python3 python3-pip
```

Create the working directory structure for the router and model configurations:

```bash
mkdir -p ~/lab5-network/{router,model,scripts}
cd ~/lab5-network
```

Verify that IP forwarding is enabled on your host:

```bash
sudo sysctl -w net.ipv4.ip_forward=1
```

Expected output:
```text
net.ipv4.ip_forward = 1
```

---

## Chapter 1: Cloud and On-Premises Network Foundation

Air-gapped architectures require strict separation of concerns at the network boundary. Placing machine learning models in a subnet without an Internet Gateway guarantees that data cannot be exfiltrated directly to external command-and-control servers. In this chapter, you create the two non-overlapping VPC networks representing the cloud inference zone and the corporate data center.

### 1.1 What You Will Build

You will provision:
- A private cloud VPC (`10.50.0.0/16`) containing one private subnet (`10.50.1.0/24`) with no Internet Gateway.
- A simulated on-premises VPC (`192.168.0.0/16`) containing a public edge subnet (`192.168.1.0/24`) and an Internet Gateway for WAN connectivity.

### 1.2 Think First: Network Containment

Consider an inference host deployed inside a private subnet.

**Question:** If an attacker executes remote code execution inside the model container, how does the absence of an Internet Gateway and NAT Gateway mitigate the severity of the attack?

<details>
<summary>Click to review</summary>

Without an Internet Gateway or NAT Gateway, the host kernel has no default route (`0.0.0.0/0`) to the public internet. Outbound socket connection requests to external IP addresses are immediately dropped at the route table boundary, preventing data exfiltration and reverse shell connections.

</details>

### 1.3 Implementation

Complete the AWS CLI commands to create the isolated cloud VPC and private subnet:

```bash
# Q1: What CIDR block defines the cloud network?
aws ec2 create-vpc --cidr-block ___ --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=lab5-cloud-vpc}]'

# Q2: Which VPC attribute must be enabled for internal domain name resolution?
aws ec2 modify-vpc-attribute --vpc-id <CLOUD_VPC_ID> --___ '{"Value": true}'

# Q3: What subnet CIDR provides 256 addresses inside 10.50.0.0/16?
aws ec2 create-subnet --vpc-id <CLOUD_VPC_ID> --cidr-block ___ --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=lab5-cloud-private-subnet}]'
```

Hints:
- Q1: The cloud VPC uses a `/16` network prefix starting with `10.50`.
- Q2: The attribute name controls DNS hostnames resolution.
- Q3: The subnet uses a `/24` prefix within the `10.50` block.

<details>
<summary>Click to see solution</summary>

```bash
# Create Cloud VPC
aws ec2 create-vpc --cidr-block 10.50.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=lab5-cloud-vpc}]'

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id <CLOUD_VPC_ID> --enable-dns-hostnames '{"Value": true}'

# Create Cloud Subnet
aws ec2 create-subnet --vpc-id <CLOUD_VPC_ID> --cidr-block 10.50.1.0/24 --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=lab5-cloud-private-subnet}]'
```

</details>

### 1.4 Understanding the Network Layout

Match each network component to its architectural role:

| Component | Role (A-D) |
|---|---|
| `10.50.0.0/16` | ___ |
| `192.168.0.0/16` | ___ |
| `lab5-onprem-igw` | ___ |
| `lab5-cloud-private-subnet` | ___ |

**Options:**
- A: Simulated on-premises corporate network
- B: Air-gapped cloud inference domain
- C: Isolated compute zone with zero internet access
- D: Edge transport gateway for public VPN termination

<details>
<summary>Click to review</summary>

- `10.50.0.0/16`: B
- `192.168.0.0/16`: A
- `lab5-onprem-igw`: D
- `lab5-cloud-private-subnet`: C

</details>

### 1.5 Test and Verify

**Predict:** What route destination will be displayed if you query the cloud private route table?

```bash
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=<CLOUD_VPC_ID>" --query "RouteTables[].Routes"
```

<details>
<summary>Click to verify</summary>

```json
[
    [
        {
            "DestinationCidrBlock": "10.50.0.0/16",
            "GatewayId": "local",
            "Origin": "CreateRouteTable",
            "State": "active"
        }
    ]
]
```
The table contains only the local target route and has no default route (`0.0.0.0/0`).

</details>

### 1.6 Checkpoint

**Self-Assessment:**
- [ ] Cloud VPC (`10.50.0.0/16`) created with DNS hostnames enabled
- [ ] Cloud private subnet (`10.50.1.0/24`) created with zero public IP assignment
- [ ] On-premises VPC (`192.168.0.0/16`) and edge subnet (`192.168.1.0/24`) operational
- [ ] No Internet Gateway attached to `lab5-cloud-vpc`

---

## Chapter 2: Hybrid Connectivity via Site-to-Site VPN and BGP

Static routing across cloud networks requires manual interventions whenever subnets change. Border Gateway Protocol (BGP) dynamically advertises reachable prefixes between autonomous systems and automatically recalculates routes during network changes. In this chapter, you establish an AWS Site-to-Site VPN with BGP route propagation.

### 2.1 What You Will Build

You will provision:
- An AWS Virtual Private Gateway (VGW) attached to the Cloud VPC using Amazon ASN `64512`.
- An AWS Customer Gateway (CGW) referencing the on-premises router public IP with ASN `65000`.
- An AWS Site-to-Site VPN Connection with dynamic routing and VPC route propagation enabled.

### 2.2 Think First: Dynamic Routing Advantages

**Question:** Why is route propagation enabled on the VPC route table when using dynamic BGP with a Virtual Private Gateway?

<details>
<summary>Click to review</summary>

Route propagation allows the Virtual Private Gateway to automatically inject routes advertised by the on-premises router via BGP directly into the VPC route table. When the on-premises network topology changes, routes update dynamically without requiring manual administrator edits.

</details>

### 2.3 Implementation

Complete the configuration to provision the Virtual Private Gateway and enable route propagation:

```bash
# Q1: What Amazon-side ASN is commonly used for private BGP peering?
aws ec2 create-vpn-gateway --type ipsec.1 --amazon-side-asn ___ --tag-specifications 'ResourceType=vpn-gateway,Tags=[{Key=Name,Value=lab5-cloud-vgw}]'

# Attach VGW to the Cloud VPC
aws ec2 attach-vpn-gateway --vpn-gateway-id <VGW_ID> --vpc-id <CLOUD_VPC_ID>

# Q2: Which command parameter enables automatic route injection from the VGW?
aws ec2 enable-vgw-route-propagation --route-table-id <CLOUD_RT_ID> --___ <VGW_ID>

# Create the Customer Gateway
aws ec2 create-customer-gateway --type ipsec.1 --public-ip <ONPREM_ROUTER_EIP> --bgp-asn 65000
```

Hints:
- Q1: Private ASN reserved for the AWS side in this lab is 64512.
- Q2: The parameter specifies the gateway ID to propagate from.

<details>
<summary>Click to see solution</summary>

```bash
# Create Virtual Private Gateway
aws ec2 create-vpn-gateway --type ipsec.1 --amazon-side-asn 64512 --tag-specifications 'ResourceType=vpn-gateway,Tags=[{Key=Name,Value=lab5-cloud-vgw}]'

# Attach VGW to Cloud VPC
aws ec2 attach-vpn-gateway --vpn-gateway-id <VGW_ID> --vpc-id <CLOUD_VPC_ID>

# Enable route propagation
aws ec2 enable-vgw-route-propagation --route-table-id <CLOUD_RT_ID> --gateway-id <VGW_ID>

# Create Customer Gateway
aws ec2 create-customer-gateway --type ipsec.1 --public-ip <ONPREM_ROUTER_EIP> --bgp-asn 65000
```

</details>

### 2.4 Understanding BGP and IPsec Parameters

Match each protocol setting to its definition:

| Setting | Definition (A-D) |
|---|---|
| ASN `64512` | ___ |
| ASN `65000` | ___ |
| `169.254.10.0/30` | ___ |
| AES-256 / SHA-256 | ___ |

**Options:**
- A: Link-local inside IP addressing for tunnel endpoints
- B: Private Autonomous System Number for AWS Virtual Private Gateway
- C: Cryptographic cipher suite for IPsec Phase 1 and Phase 2
- D: Private Autonomous System Number for on-premises edge router

<details>
<summary>Click to review</summary>

- ASN `64512`: B
- ASN `65000`: D
- `169.254.10.0/30`: A
- AES-256 / SHA-256`: C

</details>

### 2.5 Test and Verify

**Predict:** What state will the Site-to-Site VPN connection report before the on-premises router establishes Phase 1 IKE?

```bash
aws ec2 describe-vpn-connections --vpn-connection-ids <VPN_ID> --query "VpnConnections[].VgwTelemetry[].Status"
```

<details>
<summary>Click to verify</summary>

```json
[
    "DOWN",
    "DOWN"
]
```
Both tunnel endpoints report `DOWN` until the on-premises StrongSwan service initiates key exchange.

</details>

### 2.6 Checkpoint

**Self-Assessment:**
- [ ] Virtual Private Gateway attached to `lab5-cloud-vpc`
- [ ] Route propagation enabled on `lab5-cloud-private-rt`
- [ ] Customer Gateway configured with public IP and ASN `65000`
- [ ] Site-to-Site VPN connection configured for dynamic routing

---

## Chapter 3: On-Premises BGP VPN Router Configuration

The on-premises gateway terminates the encrypted tunnel and runs the dynamic routing protocol. Standard EC2 instances drop packets if the source or destination IP does not match the instance network interface. In this chapter, you disable source/destination checking and configure StrongSwan and BIRD routing daemons.

### 3.1 What You Will Build

You will configure:
- An EC2 gateway instance with source/destination checks disabled.
- StrongSwan IPsec configuration (`/etc/ipsec.conf`) for route-based VPN over a Virtual Tunnel Interface (VTI).
- BIRD routing daemon (`/etc/bird/bird.conf`) to peer with AWS BGP neighbor `169.254.10.1`.

### 3.2 Think First: Source and Destination Checks

**Question:** Why must you disable source/destination checking on an EC2 instance acting as a VPN router?

<details>
<summary>Click to review</summary>

By default, AWS EC2 verifies that an instance is the direct source or destination of any packet it handles. A router forwards traffic between disparate subnets (`192.168.0.0/16` and `10.50.0.0/16`). If source/destination checking remains enabled, the AWS hypervisor drops forwarded transit packets.

</details>

### 3.3 Implementation

Complete the StrongSwan IPsec tunnel configuration in `/etc/ipsec.conf`:

```ini
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn aws-tunnel-1
    # Q1: Which key exchange protocol version is required for AWS Site-to-Site VPN?
    keyexchange=___
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256!
    authby=secret
    left=%defaultroute
    leftid=<ROUTER_PUBLIC_IP>
    leftsubnet=0.0.0.0/0
    # Q2: Which public IP address represents the AWS VPN endpoint?
    right=___
    rightsubnet=0.0.0.0/0
    auto=start
    mark=100
```

Hints:
- Q1: Modern IPsec implementations use version 2.
- Q2: The remote address is the outside IP of AWS Tunnel 1 from the downloaded VPN configuration.

<details>
<summary>Click to see solution</summary>

```ini
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn aws-tunnel-1
    keyexchange=ikev2
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256!
    authby=secret
    left=%defaultroute
    leftid=<ROUTER_PUBLIC_IP>
    leftsubnet=0.0.0.0/0
    right=<AWS_TUNNEL_1_OUTSIDE_IP>
    rightsubnet=0.0.0.0/0
    auto=start
    mark=100
```

</details>

Now complete the BIRD dynamic routing block in `/etc/bird/bird.conf`:

```text
protocol bgp aws_tunnel1 {
    # Q1: What local inside tunnel IP and ASN does the on-prem router use?
    local 169.254.10.2 as ___;
    # Q2: What remote neighbor IP and ASN does AWS VGW use?
    neighbor 169.254.10.1 as ___;
    hold time 30;
    ipv4 {
        import all;
        export where net = 192.168.0.0/16;
    };
}
```

Hints:
- Q1: On-premises router uses ASN 65000.
- Q2: AWS Virtual Private Gateway uses ASN 64512.

<details>
<summary>Click to see solution</summary>

```text
protocol bgp aws_tunnel1 {
    local 169.254.10.2 as 65000;
    neighbor 169.254.10.1 as 64512;
    hold time 30;
    ipv4 {
        import all;
        export where net = 192.168.0.0/16;
    };
}
```

</details>

Restart network services:

```bash
sudo ipsec restart
sudo systemctl restart bird
```

### 3.4 Understanding Tunnel Routing

**Scenario:** The IPsec Phase 2 security association is established, but BGP peering remains in an `Active` or `Connect` state.

**Question:** What is the most likely cause of BGP failure when IPsec is up?

<details>
<summary>Click to review</summary>

BGP communicates over TCP port 179. If the security group or local firewall drops TCP 179 on the inside link-local interface (`169.254.10.1`), the TCP three-way handshake cannot complete despite healthy IPsec encapsulation.

</details>

### 3.5 Test and Verify

**Predict:** What command verifies that the BGP peering session has moved to the `Established` state in BIRD?

```bash
sudo birdc show protocols
```

<details>
<summary>Click to verify</summary>

Expected output:
```text
Name         Proto      Table      State  Since         Info
device1      Device     master4    up     10:00:00
kernel1      Kernel     master4    up     10:00:00
aws_tunnel1  BGP        ---        up     10:00:05      Established
```

</details>

### 3.6 Checkpoint

**Self-Assessment:**
- [ ] Source/destination check disabled on the router EC2 instance
- [ ] StrongSwan Phase 1 and Phase 2 security associations established
- [ ] Inside tunnel interface (`vti1`) configured with `169.254.10.2/30`
- [ ] BGP protocol state reports `Established` with AWS ASN `64512`

---

## Chapter 4: Air-Gapped Private ML Pipeline and Encrypted Storage

In regulated environments, model predictions and sensitive input payloads must be cryptographically protected at rest. Plaintext persistence exposes organizations to insider threats and unauthorized storage snapshot inspection. In this chapter, you deploy a zero-dependency NLP classification microservice with encrypted SQLite persistence in the air-gapped Cloud VPC.

### 4.1 What You Will Build

You will deploy on host `10.50.1.100`:
- An air-gapped Python HTTP server running on port `8000`.
- An NLP inference engine classifying text into domain categories (Technical Support, Billing, Account Security, Customer Praise).
- A cryptographic persistence module using PBKDF2 key derivation and HMAC stream encryption to store records in `/opt/ml-pipeline/encrypted_results.db`.

### 4.2 Think First: Cryptographic Zero-Knowledge Storage

**Question:** Why does the model server store both a ciphertext and an HMAC digest for every inference record in the database?

<details>
<summary>Click to review</summary>

Encrypting the payload guarantees confidentiality so that disk theft does not expose plaintext. The HMAC digest provides authenticated encryption (integrity verification), ensuring that any offline tampering or alteration of ciphertext bits is detected and rejected upon decryption.

</details>

### 4.3 Implementation

Complete the cryptographic encryption routine in `/opt/ml-pipeline/model_server.py`:

```python
import hashlib
import hmac
import secrets

def encrypt_payload(plaintext: str, key: bytes) -> str:
    # Q1: Generate a random 16-byte salt
    salt = secrets.token_bytes(___)
    
    # Derive symmetric key using PBKDF2
    derived_key = hashlib.pbkdf2_hmac('sha256', key, salt, 10000, dklen=32)
    pt_bytes = plaintext.encode('utf-8')
    
    # Generate keystream and perform XOR stream encryption
    keystream = b''
    counter = 0
    while len(keystream) < len(pt_bytes):
        keystream += hmac.new(derived_key, counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        counter += 1
    keystream = keystream[:len(pt_bytes)]
    ciphertext = bytes([p ^ k for p, k in zip(pt_bytes, keystream)])
    
    # Q2: Compute authentication tag across ciphertext
    mac = hmac.new(derived_key, ___, hashlib.sha256).digest()
    return f"{salt.hex()}:{ciphertext.hex()}:{mac.hex()}"
```

Hints:
- Q1: Standard salt length for PBKDF2 is 16 bytes.
- Q2: The HMAC authenticates the generated `ciphertext`.

<details>
<summary>Click to see solution</summary>

```python
import hashlib
import hmac
import secrets

def encrypt_payload(plaintext: str, key: bytes) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac('sha256', key, salt, 10000, dklen=32)
    pt_bytes = plaintext.encode('utf-8')
    
    keystream = b''
    counter = 0
    while len(keystream) < len(pt_bytes):
        keystream += hmac.new(derived_key, counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        counter += 1
    keystream = keystream[:len(pt_bytes)]
    ciphertext = bytes([p ^ k for p, k in zip(pt_bytes, keystream)])
    
    mac = hmac.new(derived_key, ciphertext, hashlib.sha256).digest()
    return f"{salt.hex()}:{ciphertext.hex()}:{mac.hex()}"
```

</details>

Start the model service:

```bash
python3 /opt/ml-pipeline/model_server.py &
```

### 4.4 Understanding the Pipeline Schema

Match each database column to its security or inference function:

| Column | Function (A-D) |
|---|---|
| `text_hash` | ___ |
| `ciphertext` | ___ |
| `confidence` | ___ |
| `latency_ms` | ___ |

**Options:**
- A: Model prediction probability score
- B: SHA-256 fingerprint for deduplication without storing plaintext
- C: Salted, authenticated encrypted payload representation
- D: Execution duration measurement for performance auditing

<details>
<summary>Click to review</summary>

- `text_hash`: B
- `ciphertext`: C
- `confidence`: A
- `latency_ms`: D

</details>

### 4.5 Test and Verify

**Predict:** What response structure will the health endpoint return when queried locally on port 8000?

```bash
curl -s http://127.0.0.1:8000/health
```

<details>
<summary>Click to verify</summary>

```json
{
    "service": "AWS Air-Gapped NLP Pipeline",
    "status": "HEALTHY",
    "port": 8000
}
```

</details>

### 4.6 Checkpoint

**Self-Assessment:**
- [ ] Model server daemon listening on `10.50.1.100:8000`
- [ ] SQLite database initialized at `/opt/ml-pipeline/encrypted_results.db`
- [ ] Inference requests correctly derive topics and sentiment scores
- [ ] Plaintext payloads are stored exclusively as salted ciphertexts

---

## Chapter 5: Ingestion Telemetry and Security Verification

Enterprise security controls require empirical validation through positive, negative, and chaos testing. You must mathematically prove that inference requests cross the private IPsec tunnel, that internet access is blocked, and that the architecture exhibits fail-safe self-healing. In this chapter, you run the end-to-end ingestion pipeline and execute chaos route tampering.

### 5.1 What You Will Build

You will operate:
- An ingestion client sending clinical and financial payloads from the on-premises router.
- An interactive web telemetry dashboard (`http://<ROUTER_PUBLIC_IP>:8501`) displaying live predictions.
- A three-stage security test suite:
  1. Positive validation: Cross-VPC private latency and throughput verification.
  2. Negative validation: Direct public internet blocking proof.
  3. Chaos tampering: Route withdrawal and automatic self-healing recovery.

### 5.2 Think First: Chaos Engineering

**Question:** During route tampering, why must the client receive a connection timeout rather than an unencrypted redirection?

<details>
<summary>Click to review</summary>

A fail-safe security posture dictates that if the encrypted path becomes unavailable, traffic must be dropped immediately. If the network allowed fallback to a default route, sensitive unencrypted data could leak across public transit providers.

</details>

### 5.3 Implementation

From the on-premises router, transmit test payloads across the VPN tunnel to the air-gapped ML host:

```bash
python3 /opt/onprem/data_ingestion.py
```

Expected output:
```text
[INGEST] Sending payload 1/5 -> http://10.50.1.100:8000/predict
[RESPONSE] 200 OK | Topic: Technical Support | Latency: 14.8ms | Encrypted: True
[INGEST] Sending payload 2/5 -> http://10.50.1.100:8000/predict
[RESPONSE] 200 OK | Topic: Account Security   | Latency: 16.2ms | Encrypted: True
```

### 5.4 Test and Verify: Positive, Negative, and Chaos Suite

#### Test 1: Positive Test (Private Verification)
Run an inference request directly from the on-premises router terminal:

```bash
curl -X POST http://10.50.1.100:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Unauthorized login attempt detected from unknown IP address"}'
```

<details>
<summary>Click to verify</summary>

```json
{
    "status": "SUCCESS",
    "topic": "Account Security",
    "confidence": 0.985,
    "encryption": "AES-256-HMAC ENCRYPTED IN DATABASE",
    "latency_ms": 15.4
}
```

</details>

#### Test 2: Negative Test (Public Internet Isolation)

**Predict:** What happens when you attempt to query the private ML host directly from your local workstation over the public internet?

```bash
curl --connect-timeout 3 http://10.50.1.100:8000/health
```

<details>
<summary>Click to verify</summary>

```text
curl: (28) Failed to connect to 10.50.1.100 port 8000: Connection timed out
```
The connection times out because RFC 1918 private IP addresses are non-routable over the public internet and `lab5-cloud-vpc` has no Internet Gateway.

</details>

### 5.5 Experiment: Chaos Route Tampering and Self-Healing

Verify that the system drops traffic safely when routes are manipulated, and self-heals when connectivity is restored.

1. **Simulate Route Failure:** In the AWS Console, remove the propagated route to `192.168.0.0/16` or temporarily shut down BIRD on the on-premises router:
   ```bash
   sudo systemctl stop bird
   ```

2. **Observe Fail-Safe Behavior:** Run a curl request from the on-premises host:
   ```bash
   curl -s --connect-timeout 2 http://10.50.1.100:8000/health || echo "FAIL_SAFE_TIMEOUT_CONFIRMED"
   ```
   **Observe:** The request terminates with `FAIL_SAFE_TIMEOUT_CONFIRMED`. Traffic does not leak to the internet.

3. **Restore Routing:** Restart the BIRD routing service:
   ```bash
   sudo systemctl start bird
   ```

4. **Verify Autonomous Self-Healing:** Check the health endpoint within 5 seconds:
   ```bash
   curl -s --connect-timeout 2 http://10.50.1.100:8000/health
   ```
   **Observe:** BGP peering re-establishes and the endpoint immediately responds with `{"service": "AWS Air-Gapped NLP Pipeline", "status": "HEALTHY"}`.

### 5.6 Checkpoint

**Self-Assessment:**
- [ ] Batch ingestion successfully transmitted all 5 payloads across the VPN
- [ ] Telemetry dashboard accessible on port 8501
- [ ] Direct public internet requests to `10.50.1.100` time out
- [ ] Chaos route withdrawal confirms fail-safe packet drops
- [ ] Service recovers automatically upon route restoration

---

## Epilogue: The Complete System

Your hybrid cloud machine learning infrastructure provides the following verified endpoints and components:

| Component | Network Endpoint | Purpose | Security Control |
|---|---|---|---|
| Cloud ML Inference | `http://10.50.1.100:8000/predict` | NLP multi-class prediction | Air-gapped VPC, SG restricted |
| Cloud Health Check | `http://10.50.1.100:8000/health` | Service liveness probing | Private routing only |
| On-Prem Router | `52.220.40.120` (EIP) | IPsec edge gateway | UDP 500/4500, IKEv2 / ESP |
| BGP Peering Session | `169.254.10.1` ↔ `169.254.10.2` | Dynamic route advertisement | TCP 179 over IPsec VTI |
| Web Dashboard | `http://<ROUTER_EIP>:8501` | Operational telemetry | Restrict to corporate CIDR |
| SQLite Audit Store | `/opt/ml-pipeline/encrypted_results.db` | Zero-knowledge record audit | Salted PBKDF2 HMAC XOR |

Verify complete end-to-end functionality using this sequence:

```bash
# 1. Verify BGP peering state
sudo birdc show protocols aws_tunnel1

# 2. Check kernel route to cloud subnet
ip route get 10.50.1.100

# 3. Query ML health endpoint
curl -s http://10.50.1.100:8000/health

# 4. Transmit classification payload
curl -s -X POST http://10.50.1.100:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Production database connection timeout reported on billing cluster"}'

# 5. Inspect encrypted audit records on the cloud host
ssh -i lab5-keypair.pem ubuntu@10.50.1.100 "sqlite3 /opt/ml-pipeline/encrypted_results.db 'SELECT id, text_hash, topic, ciphertext FROM inference_audit_log ORDER BY id DESC LIMIT 1;'"
```

---

## The Principles

1. **Enforce air gaps at the route table** — True network isolation requires zero internet default gateways, not just security group rules.
2. **Prefer dynamic BGP over static routes** — Route propagation automates failover and eliminates configuration drift across hybrid networks.
3. **Apply defense-in-depth cryptography** — Encrypt in transit with IPsec ESP and at rest using authenticated ciphers to prevent plaintext leakage.
4. **Validate fail-safe behavior with chaos testing** — Ensure that network disruptions cause clean timeouts rather than unencrypted routing leaks.
5. **Decouple edge ingestion from backend inference** — Terminate public traffic at an edge gateway to shield model servers from direct visibility.

---

## Troubleshooting

### Error: IPsec Phase 1 negotiation failure (IKE SA not established)

**Cause:** Pre-shared key mismatch, security group dropping UDP 500/4500, or incorrect remote gateway IP.

**Solution:**
Check the StrongSwan daemon logs and verify that UDP ports 500 and 4500 are allowed:
```bash
sudo ipsec statusall
sudo journalctl -u strongswan -n 50 --no-pager
```

### Error: BGP state remains stuck in Connect or Active

**Cause:** TCP port 179 is blocked or the inside tunnel interface IP addresses (`169.254.10.0/30`) are misconfigured.

**Solution:**
Verify IP assignment on the VTI interface and test connectivity to the AWS neighbor:
```bash
ip addr show vti1
ping -c 3 169.254.10.1
sudo birdc show protocols all aws_tunnel1
```

### Error: Packets sent to 10.50.1.100 are dropped by EC2

**Cause:** Source/destination checking remains enabled on the on-premises router instance.

**Solution:**
Disable source/destination checking via the AWS CLI:
```bash
aws ec2 modify-instance-attribute --instance-id <ROUTER_INSTANCE_ID> --no-source-dest-check
```

### Error: Model server reports SQLite database locked

**Cause:** Concurrent multi-threaded writes without WAL (Write-Ahead Logging) mode enabled.

**Solution:**
Enable WAL mode on the SQLite database:
```bash
sqlite3 /opt/ml-pipeline/encrypted_results.db "PRAGMA journal_mode=WAL;"
```

---

## Next Steps

- Implement dual-tunnel redundancy with BGP multipath routing (ECMP) across both AWS VPN tunnel endpoints.
- Configure AWS CloudWatch alarms on the Virtual Private Gateway `TunnelState` metric.
- Transition the symmetric SQLite stream cipher to AWS KMS Envelope Encryption using a VPC Endpoint for KMS.
- Implement rate-limiting and JWT token authentication on the edge gateway using an Envoy reverse proxy.

---

## Additional Resources

- [AWS Site-to-Site VPN Documentation](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPC_VPN.html)
- [AWS Virtual Private Gateway Route Propagation](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html#route-propagation)
- [StrongSwan IPsec Documentation](https://docs.strongswan.org/docs/5.9/index.html)
- [BIRD Internet Routing Daemon Guide](https://bird.network.cz/?get_doc)
- [RFC 4271: A Border Gateway Protocol 4 (BGP-4)](https://datatracker.ietf.org/doc/html/rfc4271)
