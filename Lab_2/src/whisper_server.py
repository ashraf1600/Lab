import os
import sys
import time
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

REGION_NAME = os.getenv("REGION_NAME", "Region A (Primary)")
REGION_CODE = os.getenv("REGION_CODE", "ap-southeast-1a")
PORT = int(os.getenv("PORT", "8000"))

START_TIME = time.time()
IS_HEALTHY = True
REQUEST_COUNT = 0
TOTAL_LATENCY = 0.0

class WhisperHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean timestamped log
        sys.stderr.write(f"[{time.strftime('%X')}] {self.address_string()} - {format % args}\n")

    def do_GET(self):
        global IS_HEALTHY, REQUEST_COUNT, TOTAL_LATENCY
        if self.path == "/" or self.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "service": "Whisper-MultiRegion-Inference",
                "region": REGION_NAME,
                "region_code": REGION_CODE,
                "healthy": IS_HEALTHY,
                "endpoints": ["/health", "/transcribe", "/metrics", "/admin/kill", "/admin/restore"]
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif self.path == "/health":
            if not IS_HEALTHY:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": f"Service Unavailable in {REGION_NAME} (Simulated Failure)"}).encode("utf-8"))
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                data = {
                    "status": "healthy",
                    "region": REGION_NAME,
                    "region_code": REGION_CODE,
                    "uptime_seconds": round(time.time() - START_TIME, 1)
                }
                self.wfile.write(json.dumps(data).encode("utf-8"))

        elif self.path == "/metrics":
            avg_latency = (TOTAL_LATENCY / REQUEST_COUNT) if REQUEST_COUNT > 0 else 0.0
            status_num = 1 if IS_HEALTHY else 0
            metric_str = (
                f"# HELP ml_region_health Health status of model endpoint (1=healthy, 0=down)\n"
                f"# TYPE ml_region_health gauge\n"
                f'ml_region_health{{region="{REGION_NAME}",region_code="{REGION_CODE}"}} {status_num}\n'
                f"# HELP ml_inference_requests_total Total inference requests processed\n"
                f"# TYPE ml_inference_requests_total counter\n"
                f'ml_inference_requests_total{{region="{REGION_NAME}",region_code="{REGION_CODE}"}} {REQUEST_COUNT}\n'
                f"# HELP ml_inference_latency_avg_seconds Average inference latency\n"
                f"# TYPE ml_inference_latency_avg_seconds gauge\n"
                f'ml_inference_latency_avg_seconds{{region="{REGION_NAME}",region_code="{REGION_CODE}"}} {avg_latency:.4f}\n'
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(metric_str.encode("utf-8"))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        global IS_HEALTHY, REQUEST_COUNT, TOTAL_LATENCY
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b""

        if self.path == "/transcribe":
            if not IS_HEALTHY:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"detail": f"Inference failed: {REGION_NAME} is DOWN"}).encode("utf-8"))
                return

            t0 = time.time()
            REQUEST_COUNT += 1
            # Simulated Whisper inference latency
            time.sleep(0.04)
            duration = time.time() - t0
            TOTAL_LATENCY += duration

            resp_data = {
                "success": True,
                "model": "openai/whisper-tiny",
                "served_by_region": REGION_NAME,
                "region_code": REGION_CODE,
                "filename": "test_audio.wav",
                "bytes_processed": len(post_body),
                "latency_ms": round(duration * 1000, 2),
                "transcription": "Patient history indicates normal cardiovascular rhythm and clear lungs. No acute distress observed."
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp_data).encode("utf-8"))

        elif self.path == "/admin/kill":
            IS_HEALTHY = False
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "killed",
                "region": REGION_NAME,
                "message": "Simulated regional outage activated"
            }).encode("utf-8"))

        elif self.path == "/admin/restore":
            IS_HEALTHY = True
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "restored",
                "region": REGION_NAME,
                "message": "Regional service back online"
            }).encode("utf-8"))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "Not Found"}).encode("utf-8"))

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), WhisperHandler)
    print(f"[*] Starting Whisper Model Service [{REGION_NAME}] on port {PORT}...")
    server.serve_forever()
