#!/usr/bin/env python3
"""
Client Tester for Lab 1: VPC-Isolated ML Inference Endpoint
Sends a test image to the Model Server's private IP across the Transit Gateway.
"""

import sys
import os
import requests
import json
import time

def test_inference(model_server_ip, image_path):
    url = f"http://{model_server_ip}:8000/predict"
    health_url = f"http://{model_server_ip}:8000/health"
    
    print(f"[*] Testing connection to Model Server at: {model_server_ip} (over Transit Gateway)...")
    
    # Check health
    try:
        t0 = time.time()
        health_resp = requests.get(health_url, timeout=5)
        latency = round((time.time() - t0) * 1000, 2)
        print(f"[+] Health check passed in {latency}ms: {health_resp.json()}")
    except Exception as e:
        print(f"[-] Health check failed: {e}")
        return False
        
    # Send image
    print(f"[*] Sending image '{image_path}' for ViT inference...")
    try:
        with open(image_path, "rb") as f:
            t0 = time.time()
            files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
            resp = requests.post(url, files=files, timeout=30)
            latency = round((time.time() - t0) * 1000, 2)
            
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n{'='*50}")
            print(f"[+] INFERENCE SUCCESSFUL! (Total Latency: {latency}ms)")
            print(f"{'='*50}")
            print(f"  Image File:     {data.get('filename')}")
            print(f"  Top Prediction: {data.get('top_prediction')}")
            print(f"  Confidence:     {round(data.get('confidence', 0) * 100, 2)}%")
            print(f"\nTop 5 Classes:")
            for item in data.get("top_5", []):
                print(f"  {item['rank']}. {item['label']} ({round(item['confidence']*100, 2)}%)")
            print(f"{'='*50}")
            return True
        else:
            print(f"[-] Inference failed with status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[-] Request error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python client_test.py <MODEL_PRIVATE_IP> <IMAGE_PATH>")
        sys.exit(1)
        
    model_ip = sys.argv[1]
    img = sys.argv[2]
    test_inference(model_ip, img)
