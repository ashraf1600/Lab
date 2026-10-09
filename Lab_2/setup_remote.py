import os
import subprocess

KEY_FILE = "lab2-keypair.pem"
ROUTER_IP = "18.143.179.97"

def run_ssh(host, cmd):
    ssh_cmd = [
        "ssh", "-i", KEY_FILE,
        "-o", "StrictHostKeyChecking=no",
        f"ubuntu@{host}",
        cmd
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

print("[*] Setting up Whisper on Region A...")
setup_a = """
cat << 'EOF' | sudo tee /etc/systemd/system/whisper.service
[Unit]
Description=Whisper Region A Service
After=network.target

[Service]
Type=simple
User=ubuntu
Environment="REGION_NAME=AWS Region A (Primary Cloud)"
Environment="REGION_CODE=ap-southeast-1a"
Environment="PORT=8000"
ExecStart=/usr/bin/python3 /home/ubuntu/whisper_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable whisper
sudo systemctl restart whisper
"""
cmd = f"ssh -o StrictHostKeyChecking=no ubuntu@10.0.1.100 \"{setup_a}\""
ret, out, err = run_ssh(ROUTER_IP, cmd)
print("Region A output:", out, err)

print("[*] Setting up Whisper on Region B...")
setup_b = """
cat << 'EOF' | sudo tee /etc/systemd/system/whisper.service
[Unit]
Description=Whisper Region B Service
After=network.target

[Service]
Type=simple
User=ubuntu
Environment="REGION_NAME=AWS Region B (Failover / On-Prem)"
Environment="REGION_CODE=ap-southeast-1b"
Environment="PORT=8000"
ExecStart=/usr/bin/python3 /home/ubuntu/whisper_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable whisper
sudo systemctl restart whisper
"""
cmd = f"ssh -o StrictHostKeyChecking=no ubuntu@10.1.1.100 \"{setup_b}\""
ret, out, err = run_ssh(ROUTER_IP, cmd)
print("Region B output:", out, err)

print("[*] Setting up BGP Router Service on Router...")
setup_router = """
cat << 'EOF' | sudo tee /etc/systemd/system/bgp-router.service
[Unit]
Description=BGP Dynamic Route Controller and Inference Gateway
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="REGION_A_IP=10.0.1.100"
Environment="REGION_B_IP=10.1.1.100"
Environment="PORT=8000"
ExecStart=/home/ubuntu/.local/bin/uvicorn bgp_router:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable bgp-router
sudo systemctl restart bgp-router
"""
ret, out, err = run_ssh(ROUTER_IP, setup_router)
print("Router service output:", out, err)

print("[*] Setting up Prometheus configuration...")
setup_prom = """
sudo cp /home/ubuntu/prometheus.yml /etc/prometheus/prometheus.yml
sudo systemctl restart prometheus
sudo systemctl status prometheus --no-pager
"""
ret, out, err = run_ssh(ROUTER_IP, setup_prom)
print("Prometheus output:", out, err)
