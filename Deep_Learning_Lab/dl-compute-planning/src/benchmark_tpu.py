"""Time the same training step on one TPU chip (PyTorch/XLA) and save outputs/bench_tpu.json.

  python -m src.benchmark_tpu      # on a TPU VM, for example Kaggle "TPU v5e-8"
Uses the same workloads, batch sizes and epoch size as src/benchmark.py.
"""
import json
import os
import statistics
import time
from pathlib import Path

os.environ.setdefault("PJRT_DEVICE", "TPU")

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch_xla  # noqa: E402
import torch_xla.core.xla_model as xm  # noqa: E402

from src.benchmark import BATCH_SIZES, EPOCH_SAMPLES, REPEATS  # noqa: E402
from src.models import WORKLOADS, count_parameters  # noqa: E402


def get_device():
    try:
        return torch_xla.device()  # newer torch_xla
    except AttributeError:
        return xm.xla_device()  # older torch_xla


def run_epoch(model, optimizer, criterion, x, y, batch_size):
    for i in range(0, len(x), batch_size):
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(x[i:i + batch_size]), y[i:i + batch_size])
        loss.backward()
        optimizer.step()
        xm.mark_step()  # XLA is lazy: compile/run the recorded graph for this step now


def peak_memory_mb(device):
    try:
        info = xm.get_memory_info(device)
    except Exception:
        return None
    for key in ("peak_bytes_used", "bytes_used"):
        if key in info:
            return round(info[key] / 2**20, 1)
    if "kb_total" in info and "kb_free" in info:
        return round((info["kb_total"] - info["kb_free"]) / 1024, 1)
    return None


def benchmark(name, batch_size, device):
    model_cls, shape = WORKLOADS[name]
    torch.manual_seed(42)
    model = model_cls().to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
    criterion = nn.CrossEntropyLoss()
    x = torch.randn(EPOCH_SAMPLES, *shape).to(device)
    y = torch.randint(0, 10, (EPOCH_SAMPLES,)).to(device)
    xm.mark_step()

    # Warm-up = one full epoch: XLA compiles a graph the first time it sees each step,
    # and that compile time must not be counted as training time.
    run_epoch(model, optimizer, criterion, x, y, batch_size)
    xm.wait_device_ops()

    times = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        run_epoch(model, optimizer, criterion, x, y, batch_size)
        xm.wait_device_ops()  # wait until the TPU has really finished before reading the clock
        times.append(time.perf_counter() - start)

    epoch_time = statistics.median(times)
    return {"workload": name, "batch_size": batch_size, "params": count_parameters(model),
            "epoch_time_s": round(epoch_time, 3), "throughput_sps": round(EPOCH_SAMPLES / epoch_time, 1),
            "peak_memory_mb": peak_memory_mb(device), "repeat_times_s": [round(t, 3) for t in times]}


def main():
    device = get_device()
    info = {"device": "tpu", "hardware": "TPU " + os.environ.get("TPU_ACCELERATOR_TYPE", "(type unknown)"),
            "torch": torch.__version__, "torch_xla": torch_xla.__version__,
            "epoch_samples": EPOCH_SAMPLES, "repeats": REPEATS}
    print("device=tpu | hardware={} | torch={} | torch_xla={}".format(info["hardware"], info["torch"], info["torch_xla"]))
    print("{:<11} {:>5} {:>9} {:>12} {:>14} {:>12}".format(
        "workload", "batch", "params", "epoch_time_s", "throughput/s", "peak_mem_MB"))

    results = []
    for name in WORKLOADS:
        for bs in BATCH_SIZES:
            r = benchmark(name, bs, device)
            results.append(r)
            mem = "n/a" if r["peak_memory_mb"] is None else "{:.1f}".format(r["peak_memory_mb"])
            print("{:<11} {:>5} {:>9,} {:>12.3f} {:>14,.1f} {:>12}".format(
                name, bs, r["params"], r["epoch_time_s"], r["throughput_sps"], mem))

    out = Path("outputs")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "bench_tpu.json"
    path.write_text(json.dumps({"info": info, "results": results}, indent=2))
    print("saved -> {}".format(path))


if __name__ == "__main__":
    main()
