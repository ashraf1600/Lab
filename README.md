# Cloud AI & Enterprise Networking Labs

Production-grade cloud architectures for isolated, highly secure machine learning inference in AWS.

---

## Lab Directory

| Lab | Name | Focus Areas | Guide |
| :--- | :--- | :--- | :--- |
| **Lab 1** | **VPC-Isolated ML Inference Endpoint** | AWS Transit Gateway, Multi-VPC Isolation, Vision Transformer (ViT) | [Lab 1 Student Guide](file:///Lab_1/LAB_1_STUDENT_GUIDE.md) |
| **Lab 2** | **Private Endpoint Security & Monitoring** | VPC Endpoints, PrivateLink, CloudWatch Metrics | [Lab 2](file:///Lab_2/) |
| **Lab 3** | **Secure Voice Model over IPSec Tunnel** | Site-to-Site IPSec VPN, strongSwan, Whisper Voice Inference, Packet Sniffing | [Lab 3 Student Guide](file:///Lab_3/LAB_3_STUDENT_GUIDE.md) |

---

## Lab 3 Architecture Overview

![Lab 3 Architecture Diagram](Lab_3/lab_3.webp)

- **Isolated AWS VPC (`10.0.0.0/16`)**: Dedicated private subnet (`10.0.1.0/24`) with zero internet gateway, hosting private FastAPI + Whisper voice model endpoint.
- **On-Premises Simulator (`192.168.0.0/16`)**: Gateway host running strongSwan IKEv2 daemon.
- **IPSec Tunnel**: AES-256 encrypted hardware-accelerated Site-to-Site VPN with Virtual Private Gateway (VGW) and Customer Gateway (CGW).
- **Traffic Encapsulation**: ESP Protocol 50 encapsulation shielding patient voice recordings and transcripts.
