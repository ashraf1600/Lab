#!/usr/bin/env python3
"""
On-Premises High-Throughput Batch Ingestion Client
Simulates an enterprise on-premise application transmitting sensitive customer
and operations data through the dynamic BGP IPsec VPN tunnel into the private ML VPC.
"""

import sys
import time
import json
import urllib.request
import urllib.error

ENDPOINT = sys.argv[1] if len(sys.argv) > 1 else "http://10.50.1.100:8000/predict"

SAMPLES = [
    {
        "id": "BATCH-001",
        "text": "Critical payment failure: Credit card processing API returned token expired on customer checkout order #98231."
    },
    {
        "id": "BATCH-002",
        "text": "The latest software update is fantastic! Response times are three times faster and the UI feels completely seamless."
    },
    {
        "id": "BATCH-003",
        "text": "Urgent security alert: Detected suspicious multiple password resets and brute-force authentication attacks on admin portal."
    },
    {
        "id": "BATCH-004",
        "text": "Database read replica latency is spiking above 800ms causing web requests to hang and throw internal server errors."
    },
    {
        "id": "BATCH-005",
        "text": "Requesting an updated tax invoice and refund statement for our quarterly corporate subscription renewal."
    }
]

def run_batch():
    print("=" * 80)
    print("🚀 LAB 5: ON-PREMISES DATA INGESTION CLIENT")
    print(f"Target Private ML Endpoint: {ENDPOINT}")
    print(f"Transit Route: On-Prem Gateway (192.168.1.10) -> BGP Tunnel -> AWS VGW -> 10.50.1.100:8000")
    print("=" * 80)

    success_count = 0
    total_latency = 0.0

    for idx, item in enumerate(SAMPLES, 1):
        print(f"\n[Payload {idx}/{len(SAMPLES)}] {item['id']}")
        print(f"Raw Input: \"{item['text'][:70]}...\"")
        
        req_body = json.dumps({"text": item["text"], "batch_id": item["id"]}).encode('utf-8')
        req = urllib.request.Request(ENDPOINT, data=req_body, headers={'Content-Type': 'application/json'})
        
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                roundtrip_ms = round((time.time() - t0) * 1000, 2)
                resp_data = json.loads(resp.read().decode('utf-8'))
                
                pipeline = resp_data.get("pipeline", {})
                nlp = pipeline.get("step_2_nlp_model", {})
                db = pipeline.get("step_3_encrypted_db", {})
                
                print(f"  Status:         SUCCESS ({resp.status} OK)")
                print(f"  Round-Trip RTT: {roundtrip_ms} ms")
                print(f"  Predicted Topic:{nlp.get('topic')} (Confidence: {nlp.get('topic_confidence')})")
                print(f"  Sentiment:      {nlp.get('sentiment')} ({nlp.get('sentiment_confidence')})")
                print(f"  Encrypted at Rest in DB: Record #{db.get('record_id')} ({db.get('encryption_status')})")
                print(f"  SHA-256 Hash:   {db.get('sha256_hash')}")
                
                success_count += 1
                total_latency += roundtrip_ms
        except Exception as e:
            print(f"  [ERROR] Transmission failed: {e}")
            
        time.sleep(0.5)

    print("\n" + "=" * 80)
    print(f"BATCH SUMMARY: {success_count}/{len(SAMPLES)} payloads successfully transmitted and processed.")
    if success_count > 0:
        print(f"Average Round-Trip Latency over BGP VPN: {round(total_latency / success_count, 2)} ms")
    print("=" * 80)

if __name__ == "__main__":
    run_batch()
