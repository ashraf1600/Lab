"""Call each endpoint once and print what comes back."""
import json

import httpx

from src.data import load_test_images

URL = "http://localhost:8000"


def main():
    X, y = load_test_images(5)
    with httpx.Client(base_url=URL, timeout=30) as client:
        print("GET  /health  ->", json.dumps(client.get("/health").json()))

        r = client.post("/predict", json={"pixels": X[0].tolist()})
        print("POST /predict ->", r.status_code, json.dumps(r.json()), "| true label:", int(y[0]))

        r = client.post("/batch", json={"items": X.tolist()})
        print("POST /batch   ->", r.status_code, json.dumps(r.json()))
        job_id = r.json()["job_id"]
        r = client.get("/jobs/" + job_id, params={"wait": 10})
        print("GET  /jobs/id ->", json.dumps(r.json()), "| true labels:", y.tolist())


if __name__ == "__main__":
    main()
