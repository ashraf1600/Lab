# Lab 1: VPC-Isolated ML Inference Endpoint using AWS Transit Gateway
## Complete Step-by-Step AWS Management Console Manual Guide

---

## Introduction

This lab guides you through designing, deploying, and validating an enterprise-grade, isolated Machine Learning inference infrastructure on AWS **entirely using the AWS Management Console**. You will construct a private network architecture where a Vision Transformer (ViT) model server resides in a dedicated Virtual Private Cloud (VPC) with zero internet access, reachable only by authorized internal consumer microservices via AWS Transit Gateway. 

This design pattern mitigates common production risks including distributed denial-of-service (DDoS) attacks, unauthorized model intellectual property extraction, and sensitive data exfiltration.

![Architecture Diagram: VPC-Isolated ML Inference Endpoint using AWS Transit Gateway](model-vpc-client-vpc-tgw-animated.svg)

---

## Learning Objectives

By completing this lab entirely through the AWS Management Console, you will be able to:

1. Create two isolated Virtual Private Clouds (VPCs) with non-overlapping CIDR blocks manually in the AWS Console.
2. Implement an AWS Transit Gateway hub-and-spoke topology to route inter-VPC traffic securely across the AWS private global backbone.
3. Configure restrictive VPC route tables and security groups that block all public internet traversal while allowing targeted inter-service communication.
4. Deploy a pre-trained Vision Transformer (ViT) model served with FastAPI on an isolated EC2 host via Console User Data.
5. Validate perimeter security through negative penetration testing and execute latency-benchmarked internal inference queries across the Transit Gateway.
6. Configure an Amazon S3 Gateway Endpoint to enable private model artifact loading without internet exposure.

---

## Prologue: The Challenge

You join the MLOps engineering team at an enterprise processing medical imaging data. Data scientists on your team have trained a high-accuracy Vision Transformer model that classifies diagnostic scans. The intellectual property of the model weights is valued at several million dollars, and incoming patient images contain sensitive Protected Health Information (PHI).

During a recent architecture audit, security compliance identified that internal backend services currently query model servers exposed to the public internet via API tokens. This configuration violates corporate data governance standards: token leakage could expose the endpoint to unauthorized external scraping, and zero-day vulnerabilities in the web framework could grant attackers direct access to the model instance.

Your task is to re-architect the inference platform. You must migrate the model server into a completely private VPC that possesses no Internet Gateway, no public IP addresses, and no NAT gateways. Internal client services living in a separate VPC must be connected to the model server via an AWS Transit Gateway, establishing an isolated, high-throughput channel that cannot be reached from the public internet.

---

## Environment Setup & Console Sign-In

1. Open your web browser and navigate to the AWS Management Console sign-in page:
   ```text
   https://<your-account-id>.signin.aws.amazon.com/console
   ```
2. Enter your **IAM Username** and **Password**, then click **Sign In**.
3. In the top navigation bar (top-right corner), verify that your AWS Region is set to:
   ```text
   Asia Pacific (Singapore) ap-southeast-1
   ```

---

## Chapter 1: Multi-VPC Network Architecture and Isolation

Isolating machine learning workloads begins with establishing explicit network boundaries. Placing model compute resources in the same network space as user-facing applications increases the attack surface. In this chapter, you establish two distinct Virtual Private Clouds with non-overlapping address allocations using the AWS Management Console.

### 1.1 What You Will Build

You will configure:

- **Model VPC (`10.0.0.0/16`)**: Dedicated to ML inference workloads.
- **Model Private Subnet (`10.0.1.0/24`)**: Configured with no route to the public internet.
- **Client VPC (`10.1.0.0/16`)**: Represents internal consuming microservices.
- **Client Subnet (`10.1.1.0/24`)**: Configured with management access for testing.
- **Client Internet Gateway**: Attached to Client VPC to allow SSH access for testing.

### 1.2 Think First: Network Addressing and Isolation

Consider two VPCs configured with the following CIDR blocks:
- VPC A: `10.0.0.0/16`
- VPC B: `10.0.0.0/16`

**Question:** Why is it impossible to route private traffic directly between these two VPCs using Transit Gateway or VPC Peering?

<details>
<summary>Click to review</summary>

Routing requires unambiguous destination addresses. If both VPCs use identical CIDR blocks (`10.0.0.0/16`), routers cannot determine whether an IP such as `10.0.1.50` resides locally or across the gateway. Inter-VPC connections require mutually exclusive, non-overlapping IP address ranges.

</details>

---

### 1.3 Step-by-Step Implementation in AWS Console

#### Step 1: Create Model VPC (`lab1-model-vpc`)
1. In the AWS Console search bar, search for **VPC** and select it to open the VPC Dashboard.
2. In the left navigation menu, click **Your VPCs**.
3. Click the orange **Create VPC** button.
4. Configure the settings:
   - **Resources to create:** Select **VPC only**
   - **Name tag:** `lab1-model-vpc`
   - **IPv4 CIDR block:** `10.0.0.0/16`
   - **IPv6 CIDR block:** No IPv6 CIDR block
   - **Tenancy:** Default
5. Click **Create VPC**.
6. After creation, select `lab1-model-vpc`, click **Actions > Edit VPC settings**:
   - Check **Enable DNS hostnames**
   - Check **Enable DNS resolution**
   - Click **Save changes**.

#### Step 2: Create Client VPC (`lab1-client-vpc`)
1. In **Your VPCs**, click **Create VPC** again.
2. Configure the settings:
   - **Resources to create:** Select **VPC only**
   - **Name tag:** `lab1-client-vpc`
   - **IPv4 CIDR block:** `10.1.0.0/16`
   - **Tenancy:** Default
3. Click **Create VPC**.
4. In **Actions > Edit VPC settings**, check both **Enable DNS hostnames** and **Enable DNS resolution**, then click **Save changes**.

#### Step 3: Create Subnets
1. In the left sidebar, click **Subnets**, then click **Create subnet**.
2. **Model Private Subnet:**
   - **VPC ID:** Select `lab1-model-vpc`
   - **Subnet name:** `lab1-model-private-subnet`
   - **Availability Zone:** Select `ap-southeast-1a`
   - **IPv4 subnet CIDR block:** `10.0.1.0/24`
   - Click **Create subnet**.
3. Click **Create subnet** again for **Client Subnet:**
   - **VPC ID:** Select `lab1-client-vpc`
   - **Subnet name:** `lab1-client-subnet`
   - **Availability Zone:** Select `ap-southeast-1a`
   - **IPv4 subnet CIDR block:** `10.1.1.0/24`
   - Click **Create subnet**.

#### Step 4: Attach Internet Gateway to Client VPC
1. In the left sidebar, click **Internet gateways**, then click **Create internet gateway**.
2. **Name tag:** `lab1-client-igw`, then click **Create internet gateway**.
3. Once created, click **Actions > Attach to VPC**.
4. Select `lab1-client-vpc` from the dropdown and click **Attach internet gateway**.

> **Crucial Security Note:** Do **NOT** create or attach an Internet Gateway to `lab1-model-vpc`. The Model VPC must remain strictly isolated with zero internet connectivity.

---

### 1.4 Visual Verification in AWS Console

Navigate to **AWS Management Console > VPC > Virtual Private Clouds**:

![AWS Management Console - Virtual Private Clouds](screenshots/step1_vpcs.png)

Navigate to **AWS Management Console > VPC > Subnets**:

![AWS Management Console - Subnets](screenshots/step2_subnets.png)

### 1.5 Checkpoint

- [x] Both VPCs show `Available` state in `ap-southeast-1`.
- [x] `lab1-model-vpc` has CIDR `10.0.0.0/16`.
- [x] `lab1-client-vpc` has CIDR `10.1.0.0/16`.
- [x] Subnets `10.0.1.0/24` and `10.1.1.0/24` are created in `ap-southeast-1a`.
- [x] Client VPC has an attached Internet Gateway; Model VPC has **NO** Internet Gateway.

---

## Chapter 2: Inter-VPC Connectivity with AWS Transit Gateway

Connecting multiple VPCs through point-to-point VPC Peering requires $\frac{N(N-1)}{2}$ connections as systems grow. AWS Transit Gateway serves as a regional cloud router, simplifying network topologies to a centralized hub-and-spoke model. In this chapter, you establish a Transit Gateway and configure route tables and security groups entirely in the AWS Management Console.

### 2.1 What You Will Build

You will configure:

- An AWS Transit Gateway (`lab1-tgw`, ASN `64512`).
- Two Transit Gateway Attachments (one for Model VPC, one for Client VPC).
- Static route table entries in both VPCs directing traffic destined for the peer VPC to the Transit Gateway.
- Explicit omission of any default route (`0.0.0.0/0`) in the Model VPC route table.
- Restrictive security groups allowing port 8000 only from the Client VPC.

---

### 2.2 Think First: Route Table Evaluation

Examine this route table entry from the Model VPC:

| Destination | Target |
| :--- | :--- |
| `10.0.0.0/16` | `local` |
| `10.1.0.0/16` | `tgw-...` |

**Question:** An application on the model server attempts an HTTP request to `54.239.28.85` (a public internet IP). What will happen to this network packet?

<details>
<summary>Click to review</summary>

The packet will be dropped immediately at the network layer with a `No route to host` or `Network is unreachable` error. The route table only knows how to route destinations in `10.0.0.0/16` and `10.1.0.0/16`. Because no default route (`0.0.0.0/0`) exists, outbound internet packets have no destination path.

</details>

---

### 2.3 Implementation via AWS Management Console

*(Manual step-by-step console guide replacing automated scripts)*

#### Step 1: Create AWS Transit Gateway
1. In the VPC Console left sidebar, scroll down to **Transit gateways** and click **Transit gateways**.
2. Click the orange **Create transit gateway** button.
3. Configure the parameters:
   - **Name tag:** `lab1-tgw`
   - **Description:** `Transit Gateway connecting Model VPC and Client VPC`
   - **Amazon side Autonomous System Number (ASN):** `64512`
   - **Auto accept shared attachments:** Enable
   - **Default route table association:** Enable
   - **Default route table propagation:** Enable
   - **DNS support:** Enable
4. Click **Create transit gateway**.
5. *Wait ~1 to 2 minutes* until the State changes from `pending` to **`Available`**. (Take note of your Transit Gateway ID, e.g., `tgw-07682c01476b8069e`).

#### Step 2: Create Transit Gateway Attachments
1. In the left sidebar, click **Transit gateway attachments**.
2. Click **Create transit gateway attachment**.
3. **Model VPC Attachment:**
   - **Transit gateway ID:** Select `lab1-tgw`
   - **Attachment type:** `VPC`
   - **Attachment name tag:** `tgw-attach-model-vpc`
   - **VPC ID:** Select `lab1-model-vpc` (`vpc-0462cd78993cb1085`)
   - **Subnet IDs:** Select `lab1-model-private-subnet` (`10.0.1.0/24`)
   - Click **Create transit gateway attachment**.
4. Click **Create transit gateway attachment** again for **Client VPC:**
   - **Transit gateway ID:** Select `lab1-tgw`
   - **Attachment type:** `VPC`
   - **Attachment name tag:** `tgw-attach-client-vpc`
   - **VPC ID:** Select `lab1-client-vpc` (`vpc-07c031c79191b0fd9`)
   - **Subnet IDs:** Select `lab1-client-subnet` (`10.1.1.0/24`)
   - Click **Create transit gateway attachment**.
5. Wait for both attachments to show State: **`Available`**.

#### Step 3: Complete Route Table Configuration in AWS Console
1. In the VPC Console left sidebar, click **Route tables**.
2. **Model VPC Route Table (`lab1-model-rt`):**
   - Click **Create route table**.
   - **Name tag:** `lab1-model-rt`
   - **VPC:** Select `lab1-model-vpc`
   - Click **Create route table**.
   - Go to the **Subnet associations** tab, click **Edit subnet associations**, check `lab1-model-private-subnet`, and click **Save associations**.
   - Go to the **Routes** tab, click **Edit routes** > **Add route**:
     - **Destination:** Type the Client VPC CIDR `10.1.0.0/16` *(Q1)*
     - **Target:** Select **Transit Gateway** -> select your Transit Gateway ID `tgw-07682c01476b8069e` *(Q2)*
     - Click **Save changes**.
     - *(Notice: Do NOT add `0.0.0.0/0`. Keep this route table free of any internet path!)*
3. **Client VPC Route Table (`lab1-client-rt`):**
   - Click **Create route table**.
   - **Name tag:** `lab1-client-rt`
   - **VPC:** Select `lab1-client-vpc`
   - Click **Create route table**.
   - Under **Subnet associations**, click **Edit subnet associations**, check `lab1-client-subnet`, and click **Save associations**.
   - Under **Routes**, click **Edit routes** > **Add route**:
     - **Route 1:** Destination `10.0.0.0/16` -> Target: **Transit Gateway** (`lab1-tgw`).
     - **Route 2:** Destination `0.0.0.0/0` -> Target: **Internet Gateway** (`lab1-client-igw`).
     - Click **Save changes**.

#### Step 4: Configure Security Groups in AWS Console
1. In the VPC Console left sidebar, click **Security groups** under *Security*.
2. **Model Security Group (`lab1-model-sg`):**
   - Click **Create security group**.
   - **Security group name:** `lab1-model-sg`
   - **Description:** `Security group for private Model Server`
   - **VPC:** Select `lab1-model-vpc`
   - Under **Inbound rules**, click **Add rule**:
     - **Type:** Custom TCP
     - **Port range:** `8000`
     - **Source:** Custom -> Enter Client VPC CIDR: `10.1.0.0/16` *(Q3: Restrict inbound port 8000 to only Client VPC!)*
   - Add another rule for ping/diagnostic:
     - **Type:** All ICMP - IPv4, **Source:** Custom -> `10.1.0.0/16`
   - Add an internal SSH rule (optional for admin jump):
     - **Type:** SSH, **Port:** `22`, **Source:** Custom -> `10.1.0.0/16`
   - Click **Create security group**.
3. **Client Security Group (`lab1-client-sg`):**
   - Click **Create security group**.
   - **Security group name:** `lab1-client-sg`
   - **VPC:** Select `lab1-client-vpc`
   - Under **Inbound rules**, click **Add rule**:
     - **Type:** SSH, **Port:** `22`, **Source:** `0.0.0.0/0` (Allows SSH management from your workstation)
     - **Type:** All ICMP - IPv4, **Source:** `0.0.0.0/0`
   - Click **Create security group**.

---

### Key Questions & Solutions for Section 2.3

<details>
<summary>Click to view Question Hints</summary>

- **Q1:** The cross-VPC route in the Model Route Table needs to direct traffic bound for the Client VPC: `10.1.0.0/16`.
- **Q2:** The target resource receiving cross-VPC traffic is your deployed Transit Gateway ID (`tgw-07682c01476b8069e`).
- **Q3:** The Model Security Group should restrict inbound traffic on port 8000 strictly to the Client VPC CIDR `10.1.0.0/16`, never `0.0.0.0/0`.

</details>

<details>
<summary>Click to see solution</summary>

```text
Q1 Destination CIDR: 10.1.0.0/16
Q2 Target Resource:  tgw-07682c01476b8069e (Transit Gateway)
Q3 Security Group:   Port: 8000, Protocol: TCP, Source: 10.1.0.0/16
```

</details>

---

### 2.4 Understanding the Route Tables

Compare the Model VPC Route Table with the Client VPC Route Table:

| Parameter | Model VPC Route Table (`lab1-model-rt`) | Client VPC Route Table (`lab1-client-rt`) |
| :--- | :--- | :--- |
| **Local CIDR** | `10.0.0.0/16` $\rightarrow$ `local` | `10.1.0.0/16` $\rightarrow$ `local` |
| **Cross-VPC Route** | `10.1.0.0/16` $\rightarrow$ **Transit Gateway** | `10.0.0.0/16` $\rightarrow$ **Transit Gateway** |
| **Internet Route (`0.0.0.0/0`)** | **None** *(Strictly Omitted)* | `0.0.0.0/0` $\rightarrow$ **Internet Gateway** |
| **S3 Access** | `pl-6fa54006` $\rightarrow$ **S3 Gateway Endpoint** | Via Internet Gateway / AWS Public API |
| **Public Accessibility** | **Zero inbound / Zero outbound** | Management SSH inbound allowed |

---

### 2.5 Test and Verify in AWS Console

#### Inspecting the Routes of the Model VPC Route Table
1. Navigate to **AWS Management Console > VPC > Route Tables**.
2. Select `lab1-model-rt` (`rtb-09626f0bf062697a4`).
3. Click the **Routes** tab in the bottom panel.

**Predict:** Will the routes contain an entry where the Target equals an Internet Gateway (`igw-...`)?

<details>
<summary>Click to verify</summary>

**No!** The Model VPC Route Table contains only:
1. `10.0.0.0/16` $\rightarrow$ `local`
2. `10.1.0.0/16` $\rightarrow$ `tgw-07682c01476b8069e` (Transit Gateway)
3. `pl-6fa54006` (S3 Prefix List) $\rightarrow$ `vpce-0d7c425217bff9419` (S3 Gateway Endpoint)

There is **no `0.0.0.0/0` route** and **no Internet Gateway (`igw-...`)**. This proves the subnet is physically cut off from the public internet.

</details>

#### Visual Verification in AWS Console

Navigate to **AWS Management Console > VPC > Transit Gateways**:

![AWS Management Console - Transit Gateways](screenshots/step3_transit_gateways.png)

Navigate to **AWS Management Console > VPC > Transit Gateway Attachments**:

![AWS Management Console - Transit Gateway Attachments](screenshots/step4_tgw_attachments.png)

Navigate to **AWS Management Console > VPC > Route Tables**:

![AWS Management Console - Route Tables](screenshots/step5_route_tables.png)

Navigate to **AWS Management Console > VPC > Security Groups**:

![AWS Management Console - Security Groups](screenshots/step8_security_groups.png)

---

### 2.6 Checkpoint

- [x] Transit Gateway state is `Available`.
- [x] Both VPC attachments show state `Available`.
- [x] Model Route Table targets `10.1.0.0/16` to Transit Gateway.
- [x] Model Route Table contains no route to `0.0.0.0/0`.
- [x] Model Security Group restricts port 8000 strictly to `10.1.0.0/16`.

---

## Chapter 3: Deploying the Vision Transformer Inference Service

A secure network requires an operational workload. In this chapter, you deploy an inference application using FastAPI and a pre-trained Vision Transformer model on the Model Server EC2 instance (`10.0.1.140`). The application loads model weights in memory during boot and exposes endpoints for operational status and image prediction.

### 3.1 What You Will Build

You will implement:

- An operational health check endpoint: `GET /health`.
- An image classification endpoint: `POST /predict`.
- An inference pipeline that transforms uploaded images and extracts top-5 class predictions with confidence scores.

### 3.2 Think First: Health Endpoints vs Readiness Endpoints

**Scenario:** A deployment orchestrator monitors a model server. During server startup, loading model weights takes 45 seconds.

**Question:** If the server returns HTTP 200 on `/health` as soon as Uvicorn starts (before model weights finish loading), what will happen if client requests arrive during those 45 seconds?

<details>
<summary>Click to review</summary>

Client requests arriving during those 45 seconds will fail with HTTP 500 errors, unhandled exceptions, or service crashes because the inference function will attempt to pass input tensors through an uninitialized model object. In production MLOps, a readiness probe must only return HTTP 200 after model weights are loaded and an initial warm-up inference completes successfully.

</details>

---

### 3.3 Implementation via EC2 Console Launch & User Data

You launch both EC2 instances manually in the AWS Console, injecting the inference and client software through **User data** during launch.

#### Step 1: Create Key Pair
1. Navigate to **AWS Management Console > EC2 > Key pairs**.
2. Click **Create key pair**.
3. Name: `lab1-keypair`, Type: `RSA`, Format: `.pem`.
4. Click **Create key pair** and save the file to your computer.

#### Step 2: Launch Model Server EC2 (`lab1-model-server`)
1. In the EC2 Console, click **Instances > Launch instances**.
2. **Name:** `lab1-model-server`
3. **AMI:** Ubuntu Server 22.04 LTS (HVM)
4. **Instance type:** `t2.micro` (or `t3.micro`)
5. **Key pair:** `lab1-keypair`
6. Under **Network settings**, click **Edit**:
   - **VPC:** Select `lab1-model-vpc`
   - **Subnet:** Select `lab1-model-private-subnet` (`10.0.1.0/24`)
   - **Auto-assign public IP:** Select **Disable** *(Critical for physical isolation)*
   - **Firewall (security groups):** Select existing security group -> `lab1-model-sg`
7. Scroll down, expand **Advanced details**, and locate the **User data** box.
8. Paste the complete bootstrap script below:

```bash
#!/bin/bash
set -e

# Setup 2GB Swapfile (Prevents Out of Memory errors on t2.micro)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Install dependencies
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip python3-venv curl

pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip3 install --no-cache-dir fastapi uvicorn pillow python-multipart

# Create FastAPI Vision Model Inference Script
cat << 'EOF' > /home/ubuntu/vit_server.py
import io
import torch
from torchvision import models
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn

app = FastAPI(title="Private Vision Model Endpoint")

# Load Vision model weights during initialization
print("[*] Loading Vision model weights...")
weights = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
weights.eval()
preprocess = models.MobileNet_V3_Small_Weights.DEFAULT.transforms()
categories = models.MobileNet_V3_Small_Weights.DEFAULT.meta["categories"]
print("[*] Vision Model loaded and ready!")

@app.get("/health")
def health():
    return {"status": "healthy", "model": "loaded"}  # Q1: Confirm model state in response

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")  # Q2: HTTP status for bad request

    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    batch = preprocess(image).unsqueeze(0)
    
    with torch.no_grad():
        prediction = weights(batch).squeeze(0).softmax(0)
        
    top5_prob, top5_catid = torch.topk(prediction, 5)
    results = [
        {
            "rank": i + 1,
            "label": categories[top5_catid[i]],
            "confidence": round(float(top5_prob[i]), 4)
        }
        for i in range(top5_prob.size(0))
    ]
    
    return {
        "success": True,
        "filename": file.filename,
        "top_prediction": results[0]["label"],
        "confidence": results[0]["confidence"],
        "top_5": results
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # Q3: Bind address for internal network interfaces
EOF

chown ubuntu:ubuntu /home/ubuntu/vit_server.py

# Create systemd background daemon
cat << 'EOF' > /etc/systemd/system/vit-server.service
[Unit]
Description=FastAPI Vision Model Inference Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/local/bin/uvicorn vit_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vit-server
systemctl start vit-server
```

9. Click **Launch instance**.

---

### Key Questions & Solutions for Section 3.3

<details>
<summary>Click to view Hints</summary>

- **Q1:** What value confirms model readiness in the `/health` endpoint response? Value confirming model readiness (e.g., `"loaded"`).
- **Q2:** What is the standard HTTP status code for malformed or unsupported client input? Standard client error status code is `400` (Bad Request).
- **Q3:** Which bind address allows the server to accept connections across all network interfaces (private IP)? Binding to `"0.0.0.0"` allows listening across all internal interfaces.

</details>

<details>
<summary>Click to see solution</summary>

```python
# Q1 solution:
return {"status": "healthy", "model": "loaded"}

# Q2 solution:
raise HTTPException(status_code=400, detail="Invalid file type")

# Q3 solution:
uvicorn.run(app, host="0.0.0.0", port=8000)
```

</details>

---

#### Step 3: Launch Client Tester EC2 (`lab1-client-tester`)
1. Click **Launch instances** again.
2. **Name:** `lab1-client-tester`
3. **AMI:** Ubuntu Server 22.04 LTS, **Instance type:** `t2.micro`, **Key pair:** `lab1-keypair`.
4. Under **Network settings**, click **Edit**:
   - **VPC:** Select `lab1-client-vpc`
   - **Subnet:** Select `lab1-client-subnet` (`10.1.1.0/24`)
   - **Auto-assign public IP:** Select **Enable** *(Allows SSH management)*
   - **Security group:** Select `lab1-client-sg`
5. Expand **Advanced details**, and in **User data**, paste:

```bash
#!/bin/bash
set -e

apt-get update -y
apt-get install -y python3-pip curl jq
pip3 install requests

# Download sample dog test image
curl -s -L "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg" -o /home/ubuntu/sample_dog.jpg

cat << 'EOF' > /home/ubuntu/client_test.py
import sys
import os
import requests
import time

def test_inference(model_ip, img_path):
    health_url = f"http://{model_ip}:8000/health"
    predict_url = f"http://{model_ip}:8000/predict"
    
    print(f"[*] Testing connection to Model Server at: {model_ip} (over Transit Gateway)...")
    
    # 1. Verify health over Transit Gateway
    t0 = time.time()
    health_resp = requests.get(health_url, timeout=5)
    health_latency = round((time.time() - t0) * 1000, 2)
    print(f"[+] Health check passed in {health_latency}ms: {health_resp.json()}")
    
    # 2. Send image payload over Transit Gateway
    print(f"[*] Sending image '{img_path}' for ViT inference...")
    with open(img_path, "rb") as f:
        files = {"file": (os.path.basename(img_path), f, "image/jpeg")}
        t1 = time.time()
        resp = requests.post(predict_url, files=files, timeout=30)
        inference_latency = round((time.time() - t1) * 1000, 2)
        
    data = resp.json()
    print("\n" + "="*50)
    print(f"[+] INFERENCE SUCCESSFUL! (Total Latency: {inference_latency}ms)")
    print("="*50)
    print(f"  Image File:     {data.get('filename')}")
    print(f"  Top Prediction: {data.get('top_prediction')}")
    print(f"  Confidence:     {round(data.get('confidence', 0)*100, 2)}%")
    print("\nTop 5 Classes:")
    for item in data.get("top_5", []):
        print(f"  {item['rank']}. {item['label']} ({round(item['confidence']*100, 2)}%)")
    print("="*50)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 client_test.py <MODEL_IP> <IMAGE_PATH>")
        sys.exit(1)
    test_inference(sys.argv[1], sys.argv[2])
EOF

chown -R ubuntu:ubuntu /home/ubuntu
```

6. Click **Launch instance**.

---

### 3.4 Understanding the Inference Pipeline

Trace the sequence of data transformations during one inference request:

1. **Byte Stream Extraction:** `contents = await file.read()` reads raw multipart upload bytes.
2. **Channel Normalization:** `.convert("RGB")` standardizes 1-channel grayscale or 4-channel RGBA images to 3 channels.
3. **Preprocessing:** Resizes image to 224×224 pixels and normalizes tensor values using ImageNet mean and standard deviation.
4. **Batch Dimension Expansion:** `.unsqueeze(0)` transforms shape from `[3, 224, 224]` to `[1, 3, 224, 224]`.
5. **No-Gradient Inference:** `with torch.no_grad():` disables autograd engine to save memory and accelerate computation.
6. **Probability Normalization:** `.softmax(0)` converts raw model logits into normalized probability distribution summing to 1.0.

---

### 3.5 Test and Verify

#### Verify Server Startup on Model Instance:
From the internal host, a local curl returns:
```bash
curl http://127.0.0.1:8000/health
```
**Expected output:**
```json
{"status": "healthy", "model": "loaded"}
```

#### Visual Verification in AWS Console
Navigate to **AWS Management Console > EC2 > Instances**:

![AWS Management Console - EC2 Instances](screenshots/step6_ec2_instances.png)

> **Notice:** `lab1-model-server` has **no public IPv4 address**, confirming physical internet isolation.

#### Model Server Bootstrap & PyTorch Model Weights Verification
During instance bootstrap, PyTorch downloads and caches the Vision model weights (`mobilenet_v3_small-047dcff4.pth`, 9.9 MB), verifies model readiness, and serves the FastAPI inference daemon:

![Terminal Output - Model Weights Bootstrap and Loading](screenshots/step7c_model_bootstrap.png)

#### Model Server FastAPI + ViT Service Daemon Verification
Inspect the running systemd daemon and FastAPI model serving logs:

![Terminal Output - Model Server Systemd Service](screenshots/step7b_model_service.png)

---

### 3.6 Checkpoint

- [x] Uvicorn service is managed by systemd and active (`vit-server.service`).
- [x] `/health` returns HTTP 200 with model state confirmed: `{"status": "healthy", "model": "loaded"}`.
- [x] Server listens on port 8000 across `0.0.0.0`.
- [x] Model Server has no public IP address.

---

## Chapter 4: Internal Verification and Negative Testing

A critical principle of security engineering is that validation must confirm both functional behavior (the intended path works) and boundary enforcement (unauthorized paths fail). In this chapter, you test both directions: executing inference over Transit Gateway from Client VPC, and proving unreachability from the public internet.

### 4.1 What You Will Build

You will execute:
- **Negative Test:** Attempt direct public connection to the model server from outside AWS.
- **Positive Test:** Send an image from Client EC2 across the Transit Gateway to the model server's private IP (`10.0.1.140:8000/predict`).

### 4.2 Think First: Negative Testing

**Question:** Why is testing for failure (negative testing) equally important as testing for success when deploying security-critical ML architecture?

<details>
<summary>Click to review</summary>

Positive testing confirms functionality, but it cannot prove security isolation. An engineer could deploy a model server with a public IP and permissive security group; internal services would connect successfully, giving the illusion of a working deployment while the model remains exposed to internet-wide attacks. Negative testing provides empirical proof that unauthorized paths fail.

</details>

---

### 4.3 Implementation: Review Client Test Script

The test script on Client EC2 (`client_test.py`) connects to the private IP over Transit Gateway:

```python
# client/client_test.py
import sys
import os
import requests
import time

def test_inference(model_ip, img_path):
    health_url = f"http://{model_ip}:8000/health"
    predict_url = f"http://{model_ip}:8000/predict"
    
    # 1. Verify health over Transit Gateway
    t0 = time.time()
    health_resp = requests.get(health_url, timeout=5)
    health_latency = round((time.time() - t0) * 1000, 2)
    print(f"Health Check Passed ({health_latency}ms): {health_resp.json()}")
    
    # 2. Send image payload over Transit Gateway
    with open(img_path, "rb") as f:
        files = {"file": (os.path.basename(img_path), f, "image/jpeg")}
        t1 = time.time()
        resp = requests.post(predict_url, files=files, timeout=30)
        inference_latency = round((time.time() - t1) * 1000, 2)
        
    data = resp.json()
    print(f"Top Prediction: {data['top_prediction']} ({round(data['confidence']*100, 2)}%)")
    print(f"Total Inference Round-Trip: {inference_latency}ms")

if __name__ == "__main__":
    test_inference(sys.argv[1], sys.argv[2])
```

---

### 4.4 Test and Verify

#### Step A: Negative Test (External Internet Perimeter)
From your local personal terminal (outside of AWS), attempt to query the model server directly using its private IP:

```bash
curl -m 3 http://10.0.1.140:8000/health
```

**Predict:** What error will curl return?

<details>
<summary>Click to verify</summary>

```text
curl: (28) Connection timed out after 3000 milliseconds
```
*Isolation confirmed: The model server cannot be reached from outside the AWS private network.*

</details>

#### Step B: Positive Test (Internal Transit Gateway)
Log in to Client EC2 (`18.140.26.115`) and run the test client:

```bash
ssh -i lab1-keypair.pem ubuntu@18.140.26.115
python3 /home/ubuntu/client_test.py 10.0.1.140 /home/ubuntu/sample_dog.jpg
```

**Expected output:**
```text
[*] Testing connection to Model Server at: 10.0.1.140 (over Transit Gateway)...
[+] Health check passed in 7.40ms: {'status': 'healthy', 'model': 'loaded'}
[*] Sending image '/home/ubuntu/sample_dog.jpg' for ViT inference...

==================================================
[+] INFERENCE SUCCESSFUL! (Total Latency: 289.44ms)
==================================================
  Image File:     sample_dog.jpg
  Top Prediction: Samoyed
  Confidence:     75.79%

Top 5 Classes:
  1. Samoyed (75.79%)
  2. Arctic fox (6.54%)
  3. Pomeranian (6.52%)
  4. wallaby (1.98%)
  5. Great Pyrenees (1.62%)
==================================================
```

#### Visual Verification of Inference Output

![Terminal Output - Transit Gateway Model Inference](screenshots/step7_live_inference.png)

---

### 4.5 Experiment: Deliberate Route Tampering

To observe how AWS route tables enforce security boundaries:

1. In the AWS Management Console, navigate to **VPC > Route Tables**.
2. Select the Client VPC route table (`lab1-client-rt` / `rtb-0e5e01d167e738858`).
3. Click the **Routes** tab, then click **Edit routes**.
4. Delete the static route for destination `10.0.0.0/16`, then click **Save changes**.
5. Run the client test command again from Client EC2:
   ```bash
   python3 /home/ubuntu/client_test.py 10.0.1.140 /home/ubuntu/sample_dog.jpg
   ```
6. **Observe:** The client hangs and times out. Packets intended for `10.0.1.140` now fall through to the default route (`0.0.0.0/0 -> IGW`) and are discarded by the internet gateway.
7. **Restore the route in AWS Console:** Click **Edit routes** > **Add route** > Destination: `10.0.0.0/16`, Target: Select **Transit Gateway** (`lab1-tgw`), then click **Save changes**.
8. Rerun the client test to confirm connectivity is immediately restored.

---

### 4.6 Checkpoint

- [x] Direct curl from external network times out.
- [x] Internal inference over Transit Gateway succeeds with valid classification (`Samoyed`, 75.79%).
- [x] Cross-VPC round-trip latency is under 100 milliseconds for health checks.

---

## Epilogue: The Complete System

Your deployed infrastructure provides the following architecture:

| Component | AWS Identifier | Network Address | Security State |
| :--- | :--- | :--- | :--- |
| **Model VPC** | `vpc-0462cd78993cb1085` | `10.0.0.0/16` | Strictly Private (Zero IGW) |
| **Model Subnet** | `subnet-0400ac68366782cbf` | `10.0.1.0/24` | Route only to `local`, `TGW`, and `S3 Endpoint` |
| **Model Host** | `i-071b7ebda080e21ef` | `10.0.1.140` (Private) | No Public IP assigned |
| **Model Service** | FastAPI + ViT Daemon | Port 8000 (TCP) | Accepts traffic only from `10.1.0.0/16` |
| **Client VPC** | `vpc-07c031c79191b0fd9` | `10.1.0.0/16` | Public management enabled |
| **Transit Gateway** | `tgw-07682c01476b8069e` | ASN `64512` | High-throughput regional hub |
| **S3 VPC Endpoint** | `vpce-0d7c425217bff9419` | Gateway Endpoint | Private access to AWS S3 without IGW |

---

## Complete Verification Sequence

To verify the operational integrity of the entire system:

1. **Verify Model VPC route table contains no internet route:**
   - In AWS Console > VPC > Route Tables > Select `lab1-model-rt` > Ensure no `0.0.0.0/0` route exists.
2. **Confirm external internet timeout (must time out):**
   ```bash
   curl -m 3 http://10.0.1.140:8000/health || echo "Perimeter isolation confirmed"
   ```
3. **Execute inference from Client VPC over Transit Gateway:**
   ```bash
   ssh -i lab1-keypair.pem ubuntu@18.140.26.115 \
     "python3 /home/ubuntu/client_test.py 10.0.1.140 /home/ubuntu/sample_dog.jpg"
   ```

---

## The Principles

1. **Network isolation precedes application security** — Application firewalls and API keys fail if the transport layer is open to unauthorized networks. Isolate the network first.
2. **Omission is the strongest firewall** — If a subnet has no default route (`0.0.0.0/0`) and no Internet Gateway, external hosts cannot initiate connections to it regardless of software bugs.
3. **Hub-and-spoke scales predictably** — Centralizing inter-VPC traffic through AWS Transit Gateway maintains consistent security policy enforcement without the combinatorial complexity of VPC peering meshes.
4. **Negative testing validates security claims** — Never assume an endpoint is private until you have attempted and failed to reach it from an untrusted network.

---

## Troubleshooting Guide (AWS Management Console)

### Issue 1: Connection timed out when querying model from Client EC2

#### Cause 1: Model Security Group does not permit port 8000 from Client CIDR
- **Console Fix:**
  1. Open **VPC > Security groups** in the AWS Console.
  2. Select `lab1-model-sg`.
  3. Click the **Inbound rules** tab, then click **Edit inbound rules**.
  4. Ensure a rule exists with:
     - **Type:** `Custom TCP`
     - **Port range:** `8000`
     - **Source:** Custom -> `10.1.0.0/16`
  5. Click **Save rules**.

#### Cause 2: Route table in Client VPC missing entry for 10.0.0.0/16
- **Console Fix:**
  1. Open **VPC > Route tables** in the AWS Console.
  2. Select `lab1-client-rt`.
  3. Click the **Routes** tab, then click **Edit routes**.
  4. Click **Add route**:
     - **Destination:** `10.0.0.0/16`
     - **Target:** Transit Gateway -> Select `lab1-tgw`
  5. Click **Save changes**.

---

### Issue 2: PyTorch model fails to load with Out of Memory (OOM)

#### Cause: Instance type memory limits
`t2.micro` instances possess 1 GB RAM; downloading and initializing deep learning weights in PyTorch requires supplementary virtual memory.

- **Fix:** Ensure swap space is allocated. On the Model Server, run:
  ```bash
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```
  *(This is already included automatically in the EC2 User Data script provided in Chapter 3).*

---

## Next Steps

### 1. S3 Gateway Endpoints for Private Model Weight Updates
Configure an S3 Gateway Endpoint in the Model VPC to allow private loading of new model weights directly from Amazon S3 without internet access:

1. In the VPC Console, click **Endpoints** in the left sidebar.
2. Click **Create endpoint**.
3. **Name tag:** `lab1-s3-endpoint`
4. **Service category:** AWS services
5. **Services:** Search for `s3` and select `com.amazonaws.ap-southeast-1.s3` (Type: **Gateway**).
6. **VPC:** Select `lab1-model-vpc`.
7. **Route tables:** Check `lab1-model-rt`.
8. **Policy:** Full access.
9. Click **Create endpoint**.

Navigate to **AWS Management Console > VPC > Endpoints**:

![AWS Management Console - S3 VPC Gateway Endpoint](screenshots/step9_vpc_endpoints.png)

### 2. Internal Load Balancing
Deploy an Internal Application Load Balancer (ALB) in front of a multi-AZ auto-scaling group of model servers.

### 3. Mutual TLS (mTLS)
Implement TLS certificates on the internal FastAPI endpoints to ensure data in transit across the Transit Gateway is encrypted.

---

## Additional Resources

- [AWS Transit Gateway Documentation](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)
- [AWS VPC Routing Documentation](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [PyTorch Torchvision Models](https://pytorch.org/vision/stable/models.html)
