#!/usr/bin/env python3
"""
On-Premises Real-Time Ingestion & Model Telemetry Dashboard
Hosts an interactive web application on port 8501 for sending encrypted text payloads
to the AWS air-gapped ML inference host over the BGP Site-to-Site VPN tunnel.
"""

import http.server
import socketserver
import json
import urllib.request
import urllib.error
import time
import os
import subprocess
from urllib.parse import urlparse, parse_qs

PORT = 8501
CLOUD_ML_ENDPOINT = os.environ.get("CLOUD_ML_ENDPOINT", "http://10.50.1.100:8000")

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lab 5: On-Premises BGP VPN & Secure ML Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(22, 30, 49, 0.7);
      --border: rgba(255, 255, 255, 0.08);
      --primary: #38bdf8;
      --accent: #818cf8;
      --success: #34d399;
      --warning: #fbbf24;
      --danger: #f87171;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: radial-gradient(circle at 50% 0%, #172554 0%, #0b0f19 80%);
      color: var(--text);
      font-family: 'Inter', sans-serif;
      min-height: 100vh;
      padding: 24px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    .title h1 {
      font-size: 24px;
      font-weight: 700;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 4px;
    }
    .title p { color: var(--text-muted); font-size: 14px; }
    .badge-vpn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(52, 211, 153, 0.1);
      border: 1px solid rgba(52, 211, 153, 0.3);
      border-radius: 9999px;
      color: var(--success);
      font-size: 13px;
      font-weight: 600;
    }
    .pulse {
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--success);
      animation: pulse-dot 1.5s infinite;
    }
    @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
    }
    .card-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--primary);
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 20px;
    }
    .stat-box {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      text-align: center;
    }
    .stat-label { font-size: 11px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px; }
    .stat-val { font-size: 20px; font-weight: 700; color: #fff; }
    
    textarea {
      width: 100%;
      height: 120px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      color: #fff;
      font-family: inherit;
      font-size: 14px;
      resize: vertical;
      margin-bottom: 12px;
    }
    textarea:focus { outline: none; border-color: var(--primary); }
    
    .btn-row { display: flex; gap: 10px; flex-wrap: wrap; }
    button {
      padding: 10px 18px;
      background: linear-gradient(135deg, #0284c7, #2563eb);
      color: #fff;
      border: none;
      border-radius: 6px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
    }
    button:hover { opacity: 0.9; transform: translateY(-1px); }
    button.secondary {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
    }
    button.secondary:hover { background: rgba(255, 255, 255, 0.15); }
    
    pre {
      background: #050811;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
      font-family: 'Fira Code', monospace;
      font-size: 12px;
      color: #cbd5e1;
      max-height: 300px;
      overflow-y: auto;
    }
    .pill {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary);
    }
    .table-container { overflow-x: auto; max-height: 280px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }
    th { color: var(--text-muted); font-weight: 500; }
  </style>
</head>
<body>
  <div class="header">
    <div class="title">
      <h1>Lab 5: On-Premises Control & Telemetry Dashboard</h1>
      <p>Secure Enterprise Data Ingestion &bull; Dynamic BGP Routing &bull; Air-Gapped Cloud ML</p>
    </div>
    <div class="badge-vpn">
      <div class="pulse"></div>
      BGP VPN IPsec: CONNECTED (AS 65000 &harr; AS 64512)
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-box">
      <div class="stat-label">On-Prem Subnet</div>
      <div class="stat-val" style="font-size: 16px; color: var(--primary)">192.168.1.0/24</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Cloud Inference Host</div>
      <div class="stat-val" style="font-size: 16px; color: var(--accent)">10.50.1.100:8000</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Average Latency</div>
      <div class="stat-val" id="avg-lat">2.8 ms</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Tunnel Encryption</div>
      <div class="stat-val" style="font-size: 16px; color: var(--success)">AES-256-GCM</div>
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Data Ingestion -->
    <div class="card">
      <div class="card-title">
        <span>&bull;</span> Live Text Data Ingestion (To AWS Private Subnet)
      </div>
      <textarea id="inputText" placeholder="Enter sensitive enterprise text here (e.g., customer complaints, technical errors, security incidents)...">Our production database server timed out after connection pool exhaustion during peak traffic. Error code DB_504.</textarea>
      <div class="btn-row">
        <button onclick="sendInference()">Send Over BGP Tunnel</button>
        <button class="secondary" onclick="loadSample(1)">Sample: Tech Issue</button>
        <button class="secondary" onclick="loadSample(2)">Sample: Security Alert</button>
        <button class="secondary" onclick="loadSample(3)">Sample: Billing Support</button>
      </div>
    </div>

    <!-- Panel 2: Live Inference Result -->
    <div class="card">
      <div class="card-title">
        <span>&bull;</span> Real-Time Cloud Response (Decrypted for On-Prem Client)
      </div>
      <pre id="jsonResult">// Waiting for inference payload transmission...</pre>
    </div>
  </div>

  <!-- Panel 3: Encrypted Audit DB from Private Cloud -->
  <div class="card">
    <div class="card-title" style="justify-content: space-between;">
      <span>&bull; Cloud Encrypted Results DB (Verified via BGP Route)</span>
      <button class="secondary" style="padding: 4px 10px; font-size: 11px;" onclick="fetchAuditLog()">Refresh Audit Records</button>
    </div>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Topic Classified</th>
            <th>Sentiment</th>
            <th>Confidence</th>
            <th>Encrypted Ciphertext at Rest (AES/HMAC)</th>
            <th>Latency</th>
          </tr>
        </thead>
        <tbody id="auditRows">
          <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Loading audit records...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <script>
    const samples = {
      1: "Production API gateway reported HTTP 504 gateway timeout on customer checkout endpoint. Database connection pool degraded.",
      2: "Security alert: Multiple failed login attempts and unauthorized token refresh detected from external IP range. Please lock credential.",
      3: "Customer inquired about annual subscription renewal discount and requested a breakdown of invoice tax charges."
    };

    function loadSample(id) {
      document.getElementById('inputText').value = samples[id];
    }

    async function sendInference() {
      const text = document.getElementById('inputText').value;
      const resBox = document.getElementById('jsonResult');
      resBox.textContent = "// Encapsulating payload in IPsec ESP and routing over BGP...\n";

      try {
        const res = await fetch('/api/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text })
        });
        const data = await res.json();
        resBox.textContent = JSON.stringify(data, null, 2);
        if (data.network_provenance && data.network_provenance.latency_ms) {
          document.getElementById('avg-lat').textContent = data.network_provenance.latency_ms + ' ms';
        }
        fetchAuditLog();
      } catch (err) {
        resBox.textContent = "// Error transmitting packet: " + err.message;
      }
    }

    async function fetchAuditLog() {
      try {
        const res = await fetch('/api/records');
        const data = await res.json();
        const tbody = document.getElementById('auditRows');
        tbody.innerHTML = '';
        if (!data.records || data.records.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No records yet</td></tr>';
          return;
        }
        data.records.forEach(r => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>#${r.id}</td>
            <td>${r.timestamp}</td>
            <td><span class="pill">${r.topic}</span></td>
            <td>${r.sentiment}</td>
            <td>${(r.confidence * 100).toFixed(1)}%</td>
            <td style="font-family: monospace; color: #a5b4fc;">${r.encrypted_preview}</td>
            <td>${r.latency_ms} ms</td>
          `;
          tbody.appendChild(tr);
        });
      } catch (err) {
        console.error(err);
      }
    }

    // Auto-fetch audit log on load
    fetchAuditLog();
  </script>
</body>
</html>
"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def _send_response(self, code, content_type, content):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._send_response(200, "text/html", HTML_DASHBOARD.encode('utf-8'))
        elif parsed.path == "/api/records":
            target_url = f"{CLOUD_ML_ENDPOINT}/records"
            try:
                req = urllib.request.Request(target_url, headers={'User-Agent': 'OnPrem-Dashboard/1.0'})
                with urllib.request.urlopen(req, timeout=4) as response:
                    body = response.read()
                    self._send_response(200, "application/json", body)
            except Exception as e:
                err_data = json.dumps({"records": [], "error": str(e)}).encode('utf-8')
                self._send_response(502, "application/json", err_data)
        elif parsed.path == "/api/status":
            target_url = f"{CLOUD_ML_ENDPOINT}/health"
            try:
                req = urllib.request.Request(target_url)
                with urllib.request.urlopen(req, timeout=3) as response:
                    body = response.read()
                    self._send_response(200, "application/json", body)
            except Exception as e:
                err_data = json.dumps({"status": "OFFLINE", "error": str(e)}).encode('utf-8')
                self._send_response(502, "application/json", err_data)
        else:
            self._send_response(404, "text/plain", b"Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/predict":
            length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(length)
            target_url = f"{CLOUD_ML_ENDPOINT}/predict"
            try:
                req = urllib.request.Request(target_url, data=post_body, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    body = response.read()
                    self._send_response(200, "application/json", body)
            except Exception as e:
                err_data = json.dumps({"status": "FAILED", "error": f"Failed reaching cloud ML host over VPN: {str(e)}"}).encode('utf-8')
                self._send_response(502, "application/json", err_data)
        else:
            self._send_response(404, "text/plain", b"Not Found")

def run():
    server = socketserver.ThreadingTCPServer(('0.0.0.0', PORT), DashboardHandler)
    server.allow_reuse_address = True
    print(f"[*] On-Premises Interactive Dashboard running on http://0.0.0.0:{PORT} (Target: {CLOUD_ML_ENDPOINT})...")
    server.serve_forever()

if __name__ == "__main__":
    run()
