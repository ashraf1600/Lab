"""Time the same training step on one device and save epoch time, throughput and peak memory.

  python -m src.benchmark --device cpu
  python -m src.benchmark --device cuda     # on a machine with an NVIDIA GPU
"""
import argparse
import json
import platform
import resource
import statistics
import time
from pathlib import Path

import torch
import torch.nn as nn

from src.models import WORKLOADS, count_parameters

BATCH_SIZES = [32, 128]
EPOCH_SAMPLES = 2048  # one "epoch" = 2,048 synthetic samples
WARMUP_STEPS = 5
REPEATS = 3


def sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize()  # GPU calls are asynchronous: wait before reading the clock


def device_name(device):
    if device.type == "cuda":
        return torch.cuda.get_device_name(0)
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "cpu"


def run_epoch(model, optimizer, criterion, x, y, batch_size):
    for i in range(0, len(x), batch_size):
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(x[i:i + batch_size]), y[i:i + batch_size])
        loss.backward()
        optimizer.step()


def benchmark(name, batch_size, device):
    model_cls, shape = WORKLOADS[name]
    torch.manual_seed(42)
    model = model_cls().to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
    criterion = nn.CrossEntropyLoss()
    # synthetic data created directly on the device, so we time compute only (no disk / data loading)
    x = torch.randn(EPOCH_SAMPLES, *shape, device=device)
    y = torch.randint(0, 10, (EPOCH_SAMPLES,), device=device)

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for _ in range(WARMUP_STEPS):  # first steps are slow (kernel selection, memory allocation)
        run_epoch(model, optimizer, criterion, x[:batch_size], y[:batch_size], batch_size)
    sync(device)

    times = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        run_epoch(model, optimizer, criterion, x, y, batch_size)
        sync(device)
        times.append(time.perf_counter() - start)

    epoch_time = statistics.median(times)
    if device.type == "cuda":
        peak_mb = torch.cuda.max_memory_allocated() / 2**20
    else:
        peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # Linux reports KB
    return {"workload": name, "batch_size": batch_size, "params": count_parameters(model),
            "epoch_time_s": round(epoch_time, 3), "throughput_sps": round(EPOCH_SAMPLES / epoch_time, 1),
            "peak_memory_mb": round(peak_mb, 1), "repeat_times_s": [round(t, 3) for t in times]}


def main():
    p = argparse.ArgumentParser(description="Benchmark a training step on one device")
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--output-dir", default="outputs")
    args = p.parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("No CUDA GPU found. Run this command on a GPU machine (for example Colab or Kaggle).")

    device = torch.device(args.device)
    info = {"device": args.device, "hardware": device_name(device), "torch": torch.__version__,
            "cpu_threads": torch.get_num_threads(), "epoch_samples": EPOCH_SAMPLES, "repeats": REPEATS}
    print("device={} | hardware={} | torch={} | threads={}".format(
        args.device, info["hardware"], info["torch"], info["cpu_threads"]))
    print("{:<11} {:>5} {:>9} {:>12} {:>14} {:>12}".format(
        "workload", "batch", "params", "epoch_time_s", "throughput/s", "peak_mem_MB"))

    results = []
    for name in WORKLOADS:
        for bs in BATCH_SIZES:
            r = benchmark(name, bs, device)
            results.append(r)
            print("{:<11} {:>5} {:>9,} {:>12.3f} {:>14,.1f} {:>12.1f}".format(
                name, bs, r["params"], r["epoch_time_s"], r["throughput_sps"], r["peak_memory_mb"]))

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "bench_{}.json".format(args.device)
    path.write_text(json.dumps({"info": info, "results": results}, indent=2))
    print("saved -> {}".format(path))


if __name__ == "__main__":
    main()
