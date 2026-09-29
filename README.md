# Cloud AI & Enterprise Networking Labs

Production-grade cloud networking architectures for isolated, highly secure machine learning inference and model governance on AWS.

---

## Lab Directory

| Lab | Name | Focus Areas | Guide |
| :--- | :--- | :--- | :--- |
| **Lab 1** | **VPC-Isolated ML Inference Endpoint** | AWS Transit Gateway, Multi-VPC Isolation, Vision Transformer (ViT), Zero Internet Egress | [Lab 1 Student Guide](Lab_1/LAB_1_STUDENT_GUIDE.md) |
| **Lab 2** | **Multi-Region ML Serving with Dynamic BGP Failover** | AWS VPC Peering, BGP Local-Pref, Anycast VIP, Whisper Voice Inference, Prometheus & Grafana | [Lab 2 Student Guide](Lab_2/LAB_2_STUDENT_GUIDE.md) |
| **Lab 3** | **Secure Voice Model over IPsec Tunnel** | Site-to-Site IPsec VPN, StrongSwan, Whisper Voice Inference, Wireshark Packet Sniffing | [Lab 3 Student Guide](Lab_3/LAB_3_STUDENT_GUIDE.md) |
| **Lab 4** | **Private Model Registry via Transit Gateway** | AWS Transit Gateway, S3 Interface Endpoints (AWS PrivateLink), MinIO S3 Model Store, Hugging Face Hub Sync | [Lab 4 Student Guide](Lab_4/LAB_4_STUDENT_GUIDE.md) |
| **Lab 5** | **End-to-End Encrypted ML Pipeline with BGP & IPsec VPN** | AWS Virtual Private Gateway (VGW), Customer Gateway (CGW), Site-to-Site VPN, Dynamic BGP Routing, Air-Gapped NLP Pipeline, Salted HMAC XOR Stream Cipher, Chaos Route Tampering | [Lab 5 Student Guide](Lab_5/LAB_5_STUDENT_GUIDE.md) |

---

## Architectural Principles

1. **Air-Gapped Workload Isolation** — Production ML model servers reside in private subnets with zero Internet Gateways and zero NAT Gateways, eliminating direct attack surfaces and exfiltration vectors.
2. **Dynamic Hybrid Routing** — Border Gateway Protocol (BGP) dynamically exchanges routes across IPsec tunnels and peering links, preventing routing loops and manual configuration errors.
3. **Defense-in-Depth Cryptography** — All network packets are encrypted in transit via IPsec ESP (AES-256 / SHA-256), and inferences are cryptographically encrypted at rest using salted zero-knowledge stores.
4. **Resilient Failover & Chaos Verification** — Empirical chaos engineering tests confirm fail-safe packet drops and autonomous self-healing recovery across hybrid network boundaries.
