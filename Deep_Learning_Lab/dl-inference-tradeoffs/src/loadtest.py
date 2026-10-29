"""Send the same 400 test images to the server under three load shapes and measure latency.

  python -m src.loadtest                                # all 6 scenarios (2 modes x 3 patterns)
  python -m src.loadtest --mode online --pattern bursty # just one

steady : 100 images per second, evenly spaced (4 seconds)
bursty : 4 bursts of 100 images, 1 second apart (same average rate as steady)
flood  : all 400 images at the same moment (shows the maximum throughput)
online client: sends every image to POST /predict the moment it arrives.
batch client : collects arriving images and submits them as one job to POST /batch when
               100 images are waiting or the oldest one has waited 100 ms, then fetches the job.
Latency of one image = time from its arrival at the client until its label is back.
"""
import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
import numpy as np

from src.data import load_test_images

URL = "http://localhost:8000"
TOTAL = 400
WARMUP = 20
STEADY_RATE = 100
BURST_SIZE, BURST_GAP_S = 100, 1.0
FLUSH_SIZE, FLUSH_WAIT_S = 100, 0.1  # batch client: submit a job at 100 images or after 100 ms
MODES = ["online", "batch"]
PATTERNS = ["steady", "bursty", "flood"]


def arrival_times(pattern):
    if pattern == "steady":
        return [i / STEADY_RATE for i in range(TOTAL)]
    if pattern == "bursty":
        return [(i // BURST_SIZE) * BURST_GAP_S for i in range(TOTAL)]
    return [0.0] * TOTAL


async def predict_online(client, pixels):
    r = await client.post("/predict", json={"pixels": pixels})
    r.raise_for_status()
    return 1


async def predict_batch(client, items):
    r = await client.post("/batch", json={"items": items})
    r.raise_for_status()
    r = await client.get("/jobs/" + r.json()["job_id"], params={"wait": 60})
    body = r.json()
    if body["status"] != "done":
        raise RuntimeError("job not finished: {}".format(body))
    return body["batch_size"]


async def online_client(client, images, offsets, t0, results):
    async def one(pixels, arrival):
        await asyncio.sleep(max(0.0, arrival - time.perf_counter()))
        batch_size = await predict_online(client, pixels)
        results.append({"sent_s": round(arrival - t0, 4),
                        "latency_ms": round((time.perf_counter() - arrival) * 1000, 3), "batch_size": batch_size})

    await asyncio.gather(*(one(p, t0 + at) for p, at in zip(images, offsets)))


async def batch_client(client, images, offsets, t0, results):
    async def submit(group):
        batch_size = await predict_batch(client, [p for p, _ in group])
        done = time.perf_counter()
        for _, arrival in group:
            results.append({"sent_s": round(arrival - t0, 4), "latency_ms": round((done - arrival) * 1000, 3),
                            "batch_size": batch_size})

    jobs, buffer, i = [], [], 0
    while i < len(images) or buffer:
        now = time.perf_counter()
        while i < len(images) and t0 + offsets[i] <= now:
            buffer.append((images[i], t0 + offsets[i]))
            i += 1
        if buffer and (len(buffer) >= FLUSH_SIZE or now - buffer[0][1] >= FLUSH_WAIT_S or i == len(images)):
            jobs.append(asyncio.create_task(submit(buffer[:FLUSH_SIZE])))
            buffer = buffer[FLUSH_SIZE:]
            continue
        await asyncio.sleep(0.001)
    await asyncio.gather(*jobs)


async def run_scenario(mode, pattern, images):
    limits = httpx.Limits(max_connections=TOTAL, max_keepalive_connections=TOTAL)
    async with httpx.AsyncClient(base_url=URL, limits=limits, timeout=120) as client:
        for p in images[:WARMUP]:
            await predict_online(client, p)  # warm-up requests, not measured
        await predict_batch(client, images[:WARMUP])
        results = []
        t0 = time.perf_counter() + 0.1
        run = online_client if mode == "online" else batch_client
        await run(client, images[WARMUP:], arrival_times(pattern), t0, results)
    lat = np.array([r["latency_ms"] for r in results])
    first_arrival = min(r["sent_s"] for r in results)
    last_done = max(r["sent_s"] + r["latency_ms"] / 1000 for r in results)
    summary = {"mode": mode, "pattern": pattern, "requests": TOTAL,
               "p50_ms": round(float(np.percentile(lat, 50)), 2),
               "p95_ms": round(float(np.percentile(lat, 95)), 2),
               "p99_ms": round(float(np.percentile(lat, 99)), 2),
               "max_ms": round(float(lat.max()), 2),
               "throughput_ips": round(TOTAL / (last_done - first_arrival), 1),
               "mean_batch_size": round(float(np.mean([r["batch_size"] for r in results])), 1)}
    return summary, sorted(results, key=lambda r: r["sent_s"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--pattern", choices=PATTERNS)
    args = parser.parse_args()
    modes = [args.mode] if args.mode else MODES
    patterns = [args.pattern] if args.pattern else PATTERNS

    X, _ = load_test_images(TOTAL + WARMUP)
    images = X.tolist()
    print("{:<7} {:<7} {:>8} {:>8} {:>8} {:>8} {:>12} {:>10}".format(
        "mode", "pattern", "p50_ms", "p95_ms", "p99_ms", "max_ms", "images/s", "avg_batch"))
    summaries, requests = [], {}
    for mode in modes:
        for pattern in patterns:
            s, reqs = asyncio.run(run_scenario(mode, pattern, images))
            summaries.append(s)
            requests["{}_{}".format(mode, pattern)] = reqs
            print("{:<7} {:<7} {:>8.2f} {:>8.2f} {:>8.2f} {:>8.2f} {:>12.1f} {:>10.1f}".format(
                mode, pattern, s["p50_ms"], s["p95_ms"], s["p99_ms"], s["max_ms"], s["throughput_ips"],
                s["mean_batch_size"]))
            time.sleep(1)

    out = Path("outputs/loadtest_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"total": TOTAL, "steady_rate": STEADY_RATE, "burst_size": BURST_SIZE,
                               "summaries": summaries, "requests": requests}, indent=1))
    print("saved -> {}".format(out))


if __name__ == "__main__":
    main()
