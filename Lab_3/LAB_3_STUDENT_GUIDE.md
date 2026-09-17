# Lab 3: Secure Voice Model over IPSec Tunnel

## Introduction

In regulated industries such as healthcare and financial services, voice recordings contain Protected Health Information (PHI) and Personally Identifiable Information (PII). Transmitting audio streams across the public internet without link-layer encapsulation exposes sensitive data to interception, traffic analysis, and regulatory penalties under HIPAA and GDPR.

This lab teaches you to establish a secure site-to-site IPSec VPN tunnel connecting an on-premises hospital infrastructure to an isolated Amazon Virtual Private Cloud (VPC). You will deploy an automated speech recognition service using FastAPI and OpenAI Whisper on an isolated EC2 host with zero public internet exposure. You will configure the strongSwan IPSec daemon, verify tunnel convergence, execute encrypted voice transcription, and confirm cryptographic encapsulation at the packet level using packet capture tools.

![Lab 3 Architecture Diagram](lab_3.webp)



---

## Learning Objectives

By the end of this lab, you will be able to:

1. Configure two isolated VPC topologies with mutually exclusive CIDR allocations simulating on-premises and cloud environments.
2. Provision an AWS Customer Gateway and Virtual Private Gateway to support hardware-based IPsec peering.
3. Configure strongSwan on Linux to establish an IKEv2 security association using AES-256-GCM encryption and SHA2-256 integrity verification.
4. Deploy a private speech-to-text inference endpoint using FastAPI on an isolated compute host with no internet access.
5. Capture and analyze raw network packets with `tcpdump` to prove Encapsulating Security Payload (ESP Protocol 50) encryption.
6. Execute deliberate route tampering and negative penetration tests to validate perimeter security boundaries.

**Prerequisites:** Familiarity with foundational Linux networking commands (`ip`, `tcpdump`), basic CIDR arithmetic, and Python HTTP libraries.

---

## Prologue: The Challenge

You join the engineering infrastructure team at a regional hospital network. Physicians record dictations of clinical consultations, containing patient diagnoses, pharmaceutical dosages, and medical history. The hospital data science team developed an internal speech-to-text pipeline using OpenAI Whisper to generate automated clinical notes.

During an IT compliance audit, auditors identified that internal clinic terminals transmit audio recordings to a cloud-hosted model server over public internet APIs protected only by TLS tokens. The compliance committee cited this architecture as a high-risk vulnerability: application token leakage could expose patient voice files to scraping, and unsegmented public endpoints fail HIPAA transit security requirements.

Your task is to re-architect the voice processing pipeline. You must isolate the Whisper model server within a strictly private AWS subnet that possesses no public IP addresses and no route to an Internet Gateway. You must then establish a Site-to-Site IPSec VPN tunnel connecting the hospital on-premises network directly to the AWS Virtual Private Gateway. Finally, you must prove through raw packet inspection that voice traffic traverses the public internet exclusively inside encrypted ESP payloads.

---

## Environment Setup

> **Region:** All resources are deployed in **`ap-southeast-1` (Singapore)**.

Log in to your workstation and verify the AWS CLI is installed:

```bash
aws --version
aws sts get-caller-identity
```

<details>
<summary>Click to view expected output</summary>

```json
{
    "UserId": "AKIA4JBFBPQS2UBSWKGP",
    "Account": "844038765605",
    "Arn": "arn:aws:iam::844038765605:user/tpnn-poridhi"
}
```
</details>

### Deployed Resource Reference

All resources in this lab have been provisioned in `ap-southeast-1`. Use these identifiers throughout the chapters:

| Resource | Name | ID / Value |
| :--- | :--- | :--- |
| AWS Cloud VPC | `lab3-aws-vpc` | `vpc-05e9b6390b8b13e40` |
| AWS Private Subnet | `lab3-aws-private-subnet` | `10.0.1.0/24` |
| On-Prem VPC | `lab3-onprem-vpc` | `vpc-001c74c3c1ddef094` |
| On-Prem Subnet | `lab3-onprem-public-subnet` | `192.168.1.0/24` |
| On-Prem Elastic IP | `lab3-onprem-eip` | `52.76.232.237` |
| Customer Gateway | `lab3-customer-gw` | `cgw-0d378d5048c395b77` |
| Virtual Private Gateway | `lab3-vgw` | `vgw-084ba3a31eefa93ff` |
| Site-to-Site VPN | `lab3-ipsec-vpn` | `vpn-0d48f21852888a6a5` |
| VPN Tunnel 1 Outside IP | — | `13.215.168.39` |
| On-Prem Gateway EC2 | `lab3-onprem-gateway` | `i-0d6c4173028c066c5` / `192.168.1.187` |
| Whisper Model EC2 | `lab3-whisper-model` | `i-09655c4e12373e55b` / `10.0.1.50` (no public IP) |
| On-Prem Security Group | `lab3-onprem-sg` | `sg-0f1231755bd59e6ca` |
| Model Security Group | `lab3-aws-model-sg` | `sg-01144f5cd5b476b92` |

---

## Chapter 1: Multi-VPC Architecture and Gateway Allocation

Isolating healthcare workloads requires distinct physical or logical network separation. In this chapter, you establish two distinct VPC networks: one simulating the hospital on-premises perimeter (`192.168.0.0/16`), and one representing the cloud-hosted ML perimeter (`10.0.0.0/16`).

### 1.1 What You Will Build
You will configure:
- **AWS Model VPC (`10.0.0.0/16`)**: Hosting the private inference server.
- **AWS Private Subnet (`10.0.1.0/24`)**: Configured with zero public internet routes.
- **On-Premises Simulator VPC (`192.168.0.0/16`)**: Hosting the strongSwan VPN gateway and test client.
- **On-Premises Public Subnet (`192.168.1.0/24`)**: Equipped with an Internet Gateway to establish the external IPSec tunnel endpoint.
- **Elastic IP Address**: A dedicated static public IP associated with the on-premises gateway.

### 1.2 Think First: Non-Overlapping IP Spaces

Consider a hospital network with subnet `10.0.1.0/24` attempting to peer with an AWS VPC also using `10.0.1.0/24`.

**Question:** What routing problem occurs when the hospital client attempts to query an EC2 instance located at `10.0.1.50`?

<details>
<summary>Click to review</summary>

Routing tables look up routes locally before forwarding to external gateways. If the local network and the remote cloud network share the same CIDR space (`10.0.1.0/24`), the operating system assumes `10.0.1.50` is a local host on the hospital LAN. The packet never routes across the VPN tunnel, causing a total communication failure. Site-to-site VPN networks must maintain non-overlapping address allocations.
</details>

### 1.3 Implementation

Complete the network definition script using Boto3:

```python
# lab3_vpn/setup_networks.py
import boto3

ec2 = boto3.client('ec2', region_name='ap-southeast-1')

# 1. Create AWS Cloud VPC (Model Environment)
aws_vpc = ec2.create_vpc(
    CidrBlock='___',  # Q1: What CIDR block is designated for the AWS VPC?
    TagSpecifications=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'Name', 'Value': 'lab3-aws-vpc'}]}]
)
aws_vpc_id = aws_vpc['Vpc']['VpcId']

# 2. Create AWS Private Subnet
aws_subnet = ec2.create_subnet(
    VpcId=aws_vpc_id,
    CidrBlock='___',  # Q2: What /24 subnet within AWS VPC?
    AvailabilityZone='ap-southeast-1a',
    TagSpecifications=[{'ResourceType': 'subnet', 'Tags': [{'Key': 'Name', 'Value': 'lab3-aws-private-subnet'}]}]
)

# 3. Create On-Premises Simulator VPC
onprem_vpc = ec2.create_vpc(
    CidrBlock='192.168.0.0/16',
    TagSpecifications=[{'ResourceType': 'vpc', 'Tags': [{'Key': 'Name', 'Value': 'lab3-onprem-vpc'}]}]
)
onprem_vpc_id = onprem_vpc['Vpc']['VpcId']

print(f"AWS VPC: {aws_vpc_id}, On-Prem VPC: {onprem_vpc_id}")
```

**Hints:**
- Q1: The AWS environment uses the private RFC 1918 block `10.0.0.0/16`.
- Q2: The designated private subnet is `10.0.1.0/24`.

<details>
<summary>Click to see solution</summary>

```python
# Q1 solution: CidrBlock='10.0.0.0/16'
# Q2 solution: CidrBlock='10.0.1.0/24'
```
</details>

### 1.4 Understanding the Configuration

Match each CIDR block and resource to its operational role:

| Component | Role (A-D) |
| :--- | :--- |
| `10.0.0.0/16` | ___ |
| `192.168.0.0/16` | ___ |
| `lab3-onprem-gateway` | ___ |
| Elastic IP (`52.76.232.237`) | ___ |

**Options:**
- A: Static public WAN identity required for IPSec IKE peer discovery
- B: Private cloud perimeter hosting the machine learning server
- C: On-premises perimeter representing the clinical branch network
- D: Linux host running strongSwan IKEv2 daemon

<details>
<summary>Click to review</summary>

- `10.0.0.0/16`: B
- `192.168.0.0/16`: C
- `lab3-onprem-gateway`: D
- Elastic IP: A
</details>

### 1.5 Test and Verify

Inspect the provisioned subnets across both VPCs:

```bash
aws ec2 describe-subnets --filters "Name=tag:Name,Values=lab3-aws-private-subnet,lab3-onprem-public-subnet"   --query "Subnets[*].[SubnetId,CidrBlock,VpcId,Tags[0].Value]" --output table
```

**Predict:** What CIDR values will appear in the output table?

<details>
<summary>Click to verify</summary>

The table displays `10.0.1.0/24` for `lab3-aws-private-subnet` and `192.168.1.0/24` for `lab3-onprem-public-subnet`.
</details>

#### Visual Verification in AWS Console

Navigate to **AWS Management Console > VPC > Your VPCs**:

![VPCs Console](screenshots/step1_vpcs.png)

Navigate to **AWS Management Console > VPC > Subnets**:

![Subnets Console](screenshots/step1_subnets.png)

Navigate to **AWS Management Console > VPC > Route Tables**:

![Route Tables Console](screenshots/step1b_route_tables.png)

Navigate to **AWS Management Console > EC2 > Instances**:

![On-Prem Gateway EC2](screenshots/step2_onprem_gateway.png)

> **Note:** The on-premises gateway instance possesses Elastic IP `52.76.232.237`, which serves as the public peer for the IPSec tunnel.

### 1.6 Checkpoint

**Self-Assessment:**
- [ ] Both VPCs are created in `ap-southeast-1` with state `available`.
- [ ] AWS VPC uses `10.0.0.0/16` and On-Prem VPC uses `192.168.0.0/16`.
- [ ] On-premises gateway instance has an Elastic IP assigned.

---

## Chapter 2: AWS Site-to-Site IPSec VPN Configuration

Connecting on-premises networks to AWS requires configuring two termination constructs: a Customer Gateway representing the on-premises device, and a Virtual Private Gateway on the AWS VPC side.

### 2.1 What You Will Build
You will configure:
- **Customer Gateway (`lab3-customer-gw`)**: Configured with public IP `52.76.232.237`.
- **Virtual Private Gateway (`lab3-vgw`)**: Attached to `lab3-aws-vpc`.
- **VPC Route Propagation**: Directs traffic destined for `192.168.0.0/16` into `lab3-vgw`.
- **Site-to-Site VPN Connection (`lab3-ipsec-vpn`)**: Configured with static routing and pre-shared authentication keys.

### 2.2 Think First: Route Propagation vs Static Routes

In the AWS VPC route table, you can either manually enter a static route (`192.168.0.0/16 -> vgw-xxxx`) or enable **Route Propagation**.

**Question:** What is the operational advantage of enabling route propagation for a Virtual Private Gateway?

<details>
<summary>Click to review</summary>

Route propagation automatically synchronizes route entries with the Virtual Private Gateway. If VPN routes change or additional prefixes are advertised, AWS updates the VPC route table dynamically without requiring manual administrator intervention.
</details>

### 2.3 Implementation

Complete the AWS VPN provisioning code:

```python
# lab3_vpn/create_vpn.py
import boto3

ec2 = boto3.client('ec2', region_name='ap-southeast-1')

# 1. Create Customer Gateway
cgw = ec2.create_customer_gateway(
    BgpAsn=65000,
    PublicIp='52.76.232.237',
    Type='___',  # Q1: What VPN type standard?
    TagSpecifications=[{'ResourceType': 'customer-gateway', 'Tags': [{'Key': 'Name', 'Value': 'lab3-customer-gw'}]}]
)
cgw_id = cgw['CustomerGateway']['CustomerGatewayId']

# 2. Create Virtual Private Gateway
vgw = ec2.create_vpn_gateway(
    Type='ipsec.1',
    AmazonSideAsn=64512,
    TagSpecifications=[{'ResourceType': 'vpn-gateway', 'Tags': [{'Key': 'Name', 'Value': 'lab3-vgw'}]}]
)
vgw_id = vgw['VpnGateway']['VpnGatewayId']

# 3. Create Site-to-Site VPN Connection
vpn = ec2.create_vpn_connection(
    Type='ipsec.1',
    CustomerGatewayId=cgw_id,
    VpnGatewayId=vgw_id,
    Options={
        'StaticRoutesOnly': ___,  # Q2: True or False for static prefix routing?
        'TunnelOptions': [{'PreSharedKey': 'HospitalVoiceSecurePsk2026'}]
    },
    TagSpecifications=[{'ResourceType': 'vpn-connection', 'Tags': [{'Key': 'Name', 'Value': 'lab3-ipsec-vpn'}]}]
)
```

**Hints:**
- Q1: AWS uses the industry standard string `'ipsec.1'`.
- Q2: Static route configurations require `'StaticRoutesOnly': True`.

<details>
<summary>Click to see solution</summary>

```python
# Q1 solution: Type='ipsec.1'
# Q2 solution: 'StaticRoutesOnly': True
```
</details>

### 2.4 Understanding the VPN Parameters

Match the cryptographic parameter to its function in the IPSec tunnel:

| Parameter | Function (A-D) |
| :--- | :--- |
| `IKEv2` | ___ |
| `AES-256-GCM` | ___ |
| `Diffie-Hellman Group 14` | ___ |
| `Pre-Shared Key (PSK)` | ___ |

**Options:**
- A: Shared secret string authenticating tunnel endpoints during Phase 1
- B: Symmetric cipher providing voice payload confidentiality and authentication
- C: Key exchange protocol negotiating security parameters and session keys
- D: 2048-bit modular exponentiation group used for secure key derivation

<details>
<summary>Click to review</summary>

- `IKEv2`: C
- `AES-256-GCM`: B
- `Diffie-Hellman Group 14`: D
- `Pre-Shared Key (PSK)`: A
</details>

### 2.5 Test and Verify

Query the Customer Gateway and Virtual Private Gateway status:

```bash
aws ec2 describe-customer-gateways --customer-gateway-ids cgw-0d4d31cd85891bf49   --query "CustomerGateways[0].[CustomerGatewayId,State,IpAddress]" --output text
```

**Predict:** What state will the Customer Gateway report?

<details>
<summary>Click to verify</summary>

The output displays `cgw-0d4d31cd85891bf49 available 52.76.232.237`.
</details>

#### Visual Verification in AWS Console

Navigate to **AWS Management Console > VPC > Customer Gateways**:

![Customer Gateways Console](screenshots/step3_customer_gateway.png)

Navigate to **AWS Management Console > VPC > Virtual Private Gateways**:

![Virtual Private Gateways Console](screenshots/step4_virtual_private_gateway.png)

Navigate to **AWS Management Console > VPC > Site-to-Site VPN Connections**:

![Site to Site VPN Console](screenshots/step5_vpn_connection.png)

Navigate to **AWS Management Console > VPC > Site-to-Site VPN Connections > VPN details > Static routes**:

![VPN Static Routes Console](screenshots/step7b_vpn_static_routes.png)

### 2.6 Checkpoint

**Self-Assessment:**
- [ ] Customer Gateway status is `available`.
- [ ] Virtual Private Gateway state shows `attached` to `lab3-aws-vpc`.
- [ ] Route propagation is enabled on the AWS VPC route table.
- [ ] Tunnel 1 outside IP address is noted.

---

## Chapter 3: Deploying the Private Speech Inference Service

The machine learning inference server processes confidential audio. In this chapter, you deploy FastAPI serving an automated speech recognition pipeline on an EC2 instance in the private subnet (`10.0.1.50`).

### 3.1 What You Will Build
You will implement:
- An EC2 model host deployed with no public IPv4 address.
- A restrictive security group admitting TCP port 8000 only from `192.168.0.0/16`.
- A FastAPI application with `/health` and `/transcribe` endpoints.

### 3.2 Think First: Network Binding Addresses

**Scenario:** A developer starts the FastAPI server with `uvicorn.run(app, host="127.0.0.1", port=8000)`.

**Question:** Why will incoming inference requests sent across the VPN tunnel from `192.168.1.187` fail to connect?

<details>
<summary>Click to review</summary>

Binding to `127.0.0.1` binds the application exclusively to the local loopback interface. The server will reject packets arriving from external network adapters (`eth0`). The server must bind to `0.0.0.0` to listen on all network interfaces.
</details>

### 3.3 Implementation

Complete the Whisper server application:

```python
# src/whisper_server.py
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn
import time

app = FastAPI(title="Private Medical Voice Service")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "whisper-ipsec", "mode": "private"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    # Validate audio MIME format
    if not file.filename.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
        raise HTTPException(status_code=___, detail="Unsupported audio format")  # Q1: Status code for client error?
    
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty payload")

    # Simulate inference latency
    time.sleep(0.08)
    
    return {
        "success": True,
        "filename": file.filename,
        "transcription": "Patient history indicates acute bronchitis. Prescribed amoxicillin 500mg.",
        "security": "Transmitted over IPSec ESP encrypted tunnel (HIPAA Compliant)",
        "bytes_processed": len(contents)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="___", port=8000)  # Q2: Bind address for all network interfaces?
```

**Hints:**
- Q1: HTTP 400 Bad Request indicates malformed or unsupported client input.
- Q2: `"0.0.0.0"` instructs the socket to bind across all attached adapters.

<details>
<summary>Click to see solution</summary>

```python
# Q1 solution: status_code=400
# Q2 solution: host="0.0.0.0"
```
</details>

### 3.4 Understanding the Security Posture

Compare the security perimeter of the model server against standard public API endpoints:

| Property | Standard Public API | Private IPSec Endpoint |
| :--- | :--- | :--- |
| Public IP Address | Assigned (`54.x.x.x`) | **None (Isolated)** |
| Inbound Traffic Source | Internet (`0.0.0.0/0`) | **Restricted (`192.168.0.0/16`)** |
| Transport Layer | Public WAN via TLS | **Encapsulating Security Payload (ESP)** |
| DDoS Vulnerability | High | **Zero external surface** |

### 3.5 Test and Verify

Verify that the model server is running and reachable locally:

```bash
curl http://127.0.0.1:8000/health
```

Expected output:
```json
{"status": "healthy", "service": "whisper-ipsec", "mode": "private"}
```

#### Visual Verification in AWS Console

Navigate to **AWS Management Console > EC2 > Network & Security > Security Groups**:

![Security Groups Console](screenshots/step2b_security_groups.png)

Navigate to **AWS Management Console > EC2 > Instances**:

![Private Model Server Instance](screenshots/step6_ec2_instances.png)

> **Notice:** `lab3-whisper-model` has **no public IPv4 address**, confirming zero internet exposure.

### 3.6 Checkpoint

**Self-Assessment:**
- [ ] Model server is launched in `lab3-aws-private-subnet`.
- [ ] Public IPv4 address is empty.
- [ ] Security group permits port 8000 only from `192.168.0.0/16`.

---

## Chapter 4: strongSwan Gateway Configuration and Tunnel Convergence

With cloud resources provisioned, you now configure the on-premises Linux gateway using **strongSwan** to negotiate the IPSec tunnel with AWS.

### 4.1 What You Will Build
You will configure:
- Linux kernel IPv4 forwarding (`net.ipv4.ip_forward = 1`).
- strongSwan connection profile (`/etc/ipsec.conf`).
- Pre-shared authentication key credentials (`/etc/ipsec.secrets`).
- Verification of tunnel state in the AWS Management Console.

### 4.2 Think First: The Role of Dead Peer Detection (DPD)

Examine this setting from `/etc/ipsec.conf`:
```text
dpddelay=10s
dpdtimeout=30s
dpdaction=restart
```

**Question:** What happens if the physical WAN connection drops for 45 seconds without Dead Peer Detection?

<details>
<summary>Click to review</summary>

Without DPD, both endpoints remain in an assumed-established state with stale Security Associations. Traffic continues sending into a black hole. With DPD enabled, the gateway recognizes the peer is unresponsive after 30 seconds, flushes the stale SA, and renegotiates IKE immediately upon link recovery.
</details>

### 4.3 Implementation

Complete the strongSwan configuration files on `lab3-onprem-gateway`:

```bash
# /etc/ipsec.conf
config setup
    charondebug="ike 1, knl 1, cfg 0"
    uniqueids=no

conn %default
    keyexchange=___                    # Q1: What key exchange protocol version?
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256-modp2048!
    keyingtries=%forever
    dpddelay=10s
    dpdtimeout=30s
    dpdaction=restart
    auto=start

conn aws-tunnel-1
    left=%defaultroute
    leftid=52.76.232.237
    leftsubnet=___                     # Q2: What is the local on-prem subnet?
    right=13.215.107.114                      # AWS Tunnel 1 Outside IP
    rightid=13.215.107.114
    rightsubnet=___                    # Q3: What is the target AWS VPC subnet?
    authby=secret
```

**Hints:**
- Q1: Modern secure IPSec tunnels standard uses `ikev2`.
- Q2: The local on-premises network is `192.168.0.0/16`.
- Q3: The destination cloud VPC network is `10.0.0.0/16`.

<details>
<summary>Click to see solution</summary>

```text
# Q1 solution: keyexchange=ikev2
# Q2 solution: leftsubnet=192.168.0.0/16
# Q3 solution: rightsubnet=10.0.0.0/16
```
</details>

Configure `/etc/ipsec.secrets`:
```text
52.76.232.237 13.215.107.114 : PSK "HospitalVoiceSecurePsk2026"
```

### 4.4 Test and Verify

Start the strongSwan daemon and inspect association status:

```bash
sudo ipsec restart
sudo ipsec up aws-tunnel-1
sudo ipsec status
```

**Predict:** What string in `ipsec status` confirms that the cryptographic security association is active?

<details>
<summary>Click to verify</summary>

The output displays `ESTABLISHED` and shows `INSTALLED, TUNNEL, reqid 1, ESP in UDP`.
</details>

Expected output:
```text
Security Associations (1 up, 0 connecting):
aws-tunnel-1[1]: ESTABLISHED 12 seconds ago, 192.168.1.187[52.76.232.237]...13.215.107.114[13.215.107.114]
aws-tunnel-1{1}:  INSTALLED, TUNNEL, reqid 1, ESP in UDP SPIs: c0de1234_i 5678abcd_o
aws-tunnel-1{1}:   192.168.0.0/16 === 10.0.0.0/16
```

#### Visual Verification in AWS Console

Navigate to **AWS Management Console > VPC > Site-to-Site VPN Connections > Tunnel Details**:

![VPN Tunnel Details Console](screenshots/step7_vpn_tunnel_up.png)

> **Confirmation:** Tunnel 1 status transitions from `DOWN` to **`UP`** with `1 IPsec ISAKMP SA` active.

### 4.5 Checkpoint

**Self-Assessment:**
- [ ] Kernel parameter `net.ipv4.ip_forward` is set to 1.
- [ ] strongSwan reports Security Association status `ESTABLISHED`.
- [ ] AWS Console Tunnel 1 Status displays `UP`.

---

## Chapter 5: Packet Analysis and Security Boundary Verification

Security assertions must be verified through empirical measurement. In this chapter, you inspect network packets during inference and perform negative penetration tests against the model perimeter.

### 5.1 What You Will Build
You will execute:
- **Packet Capture Analysis:** Use `tcpdump` on the physical interface to prove ESP Protocol 50 encapsulation.
- **Encrypted Voice Inference:** Transmit audio across the tunnel and extract transcriptions.
- **Negative External Probe:** Prove that untrusted external clients cannot reach the model server.

### 5.2 Think First: Plaintext vs Encapsulating Security Payload

Consider an adversary operating a rogue packet sniffer on the internet transit path between the hospital and AWS.

**Question:** If the adversary captures packets transmitted via ESP (Protocol 50), what information can they read?

<details>
<summary>Click to review</summary>

The adversary can only observe the outer IP headers: the source IP (`52.76.232.237`), destination IP (`13.215.107.114`), and protocol number 50. The inner payload (HTTP request method, URL path, headers, and audio bytes) is encrypted with AES-256 and appears as random binary ciphertext.
</details>

### 5.3 Implementation

Execute the verification sequence using two terminal sessions on `lab3-onprem-gateway`.

**Terminal 1 (Packet Sniffer):**
```bash
sudo tcpdump -i eth0 -nn "proto 50 or port 500 or port 4500"
```

**Terminal 2 (Inference Client):**
```bash
curl -X POST "http://10.0.1.50:8000/transcribe"   -F "file=@sample_patient_voice.wav"
```

### 5.4 Test and Verify

**Terminal 2 Output (Transcription Success):**
```json
{
  "success": true,
  "filename": "sample_patient_voice.wav",
  "transcription": "Patient history indicates acute bronchitis. Prescribed amoxicillin 500mg.",
  "security": "Transmitted over IPSec ESP encrypted tunnel (HIPAA Compliant)",
  "bytes_processed": 145280
}
```

**Terminal 1 Output (Cryptographic Proof):**
```text
12:20:10.104212 IP 52.76.232.237 > 13.215.107.114: ESP(spi=0xc0de1234,seq=42), length 1420
12:20:10.104289 IP 52.76.232.237 > 13.215.107.114: ESP(spi=0xc0de1234,seq=43), length 1420
12:20:10.189401 IP 13.215.107.114 > 52.76.232.237: ESP(spi=0x5678abcd,seq=28), length 380
```

#### Visual Verification of Inference and Packet Capture

![Terminal Proof of Inference and Packet Capture](screenshots/step8_live_inference_tcpdump.png)

#### Negative Internet Penetration Test
From your external workstation (outside the hospital network), attempt to reach the model server:

```bash
curl -m 3 http://10.0.1.50:8000/health
```

Expected output:
```text
curl: (28) Connection timed out after 3000 milliseconds
```

![External Connection Timeout](screenshots/step9_negative_test.png)

### 5.5 Experiment: Deliberate Pre-Shared Key Mismatch

To observe how IPSec enforces cryptographic integrity:

1. On `lab3-onprem-gateway`, edit `/etc/ipsec.secrets` and alter the pre-shared key to an invalid string:
   ```text
   52.76.232.237 13.215.107.114 : PSK "CorruptedKey123"
   ```
2. Restart the daemon: `sudo ipsec restart`.
3. Observe the output of `sudo ipsec status`:
   ```text
   Security Associations (0 up, 1 connecting):
   aws-tunnel-1[1]: CONNECTING, ...
   ```
4. Check `/var/log/auth.log` or `journalctl -u strongswan`:
   Notice the authentication error: `parsed INFORMATIONAL_V1 request ... payload malformed / AUTHENTICATION_FAILED`.
5. Restore the correct key in `/etc/ipsec.secrets`, restart the service, and verify the tunnel returns to `ESTABLISHED`.

### 5.6 Checkpoint

**Self-Assessment:**
- [ ] `tcpdump` confirms voice transmission generates ESP Protocol 50 packets.
- [ ] No plaintext HTTP headers appear on the public interface.
- [ ] Direct curl from external internet times out.
- [ ] Key mismatch causes immediate failure of Phase 1 IKE negotiation.

---

## Epilogue: The Complete System

Your deployed architecture provides the following production components:

| Component | AWS Identifier | Resource ID | Network Address | Operational Role |
| :--- | :--- | :--- | :--- | :--- |
| AWS Model VPC | `lab3-aws-vpc` | `vpc-05e9b6390b8b13e40` | `10.0.0.0/16` | Isolated cloud inference network |
| Private Model Subnet | `lab3-aws-private-subnet` | `subnet-08034bc6e769063ed` | `10.0.1.0/24` | Zero internet access subnet |
| Model Server Host | `lab3-whisper-model` | `i-09655c4e12373e55b` | `10.0.1.50` (Private only) | Whisper transcription daemon |
| On-Prem VPC | `lab3-onprem-vpc` | `vpc-001c74c3c1ddef094` | `192.168.0.0/16` | Simulated hospital perimeter |
| On-Prem Gateway EC2 | `lab3-onprem-gateway` | `i-0d6c4173028c066c5` | `192.168.1.187` / EIP `52.76.232.237` | strongSwan IKEv2 tunnel peer |
| Customer Gateway | `lab3-customer-gw` | `cgw-0d378d5048c395b77` | `52.76.232.237` | On-prem router registration in AWS |
| Virtual Private Gateway | `lab3-vgw` | `vgw-084ba3a31eefa93ff` | ASN `64512` | AWS VPC VPN termination |
| Site-to-Site VPN | `lab3-ipsec-vpn` | `vpn-0d48f21852888a6a5` | Tunnel 1: `13.215.168.39` | AES-256 / IKEv2 encrypted transit |

### Complete Verification Sequence

Execute the complete end-to-end verification sequence:

```bash
# 1. Verify IPSec tunnel association
sudo ipsec status | grep "ESTABLISHED"

# 2. Verify model health over encrypted tunnel
curl http://10.0.1.50:8000/health

# 3. Transcribe sample audio over encrypted tunnel
curl -X POST "http://10.0.1.50:8000/transcribe" -F "file=@patient_voice.wav"

# 4. Confirm external internet isolation (must time out)
curl -m 3 http://10.0.1.50:8000/health || echo "Perimeter isolation confirmed"
```

---

## The Principles

1. **Link-layer encryption precedes application authorization** — Application firewalls and tokens fail if data in transit is readable across public networks. Protect the channel first.
2. **Encapsulating Security Payload conceals traffic metadata** — ESP encryption shields not only the payload data but also transport protocol headers, concealing operational patterns from external observers.
3. **Absence of routes provides deterministic isolation** — Omitting public IP addresses and default routes (`0.0.0.0/0`) eliminates external attack vectors regardless of software vulnerabilities.
4. **Negative testing validates security assertions** — Never assume a service is private until you have attempted and failed to reach it from an untrusted public network.

---

## Troubleshooting

### Error: strongSwan tunnel remains in `CONNECTING` state

**Cause 1:** On-premises security group blocks UDP port 500 or 4500.  
**Solution:**
```bash
# Add UDP 500 (IKE) and 4500 (NAT-T) to the on-prem security group
aws ec2 authorize-security-group-ingress --group-id sg-0f1231755bd59e6ca --protocol udp --port 500 --cidr 0.0.0.0/0 --region ap-southeast-1
aws ec2 authorize-security-group-ingress --group-id sg-0f1231755bd59e6ca --protocol udp --port 4500 --cidr 0.0.0.0/0 --region ap-southeast-1
```

**Cause 2:** Pre-shared key mismatch between `/etc/ipsec.secrets` and AWS VPN configuration.  
**Solution:** Verify that the PSK in `/etc/ipsec.secrets` matches the value configured in AWS Tunnel 1 Options.

---

### Error: Packet reaches model server, but response never returns to on-premises client

**Cause:** Route propagation is disabled on the AWS VPC route table. AWS does not know how to return packets to `192.168.0.0/16`.  
**Solution:**
```bash
# Enable VGW route propagation on the AWS VPC route table
aws ec2 enable-vgw-route-propagation --route-table-id rtb-0ac04a2a49b7018ce --gateway-id vgw-084ba3a31eefa93ff --region ap-southeast-1
```

---

## Next Steps

1. **Redundant Dual-Tunnel Failover:** Configure strongSwan to establish both Tunnel 1 and Tunnel 2 with BGP dynamic routing for automated failover.
2. **Mutual TLS over IPSec:** Implement mTLS certificates on FastAPI to establish defense-in-depth security inside the VPN tunnel.
3. **Audio Stream Chunking:** Modify the Whisper inference server to accept streaming chunked audio over WebSockets across the IPSec tunnel.

---

## Additional Resources

- [AWS Site-to-Site VPN Documentation](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPC_VPN.html)
- [strongSwan IKEv2 Configuration Reference](https://docs.strongswan.org/docs/5.9/config/IKEv2.html)
- [FastAPI Request Files Documentation](https://fastapi.tiangolo.com/tutorial/request-files/)
- [OpenAI Whisper Speech Recognition Repository](https://github.com/openai/whisper)
