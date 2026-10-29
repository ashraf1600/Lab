"""Turn benchmark files + hourly prices into a compute-planning matrix.

  python -m src.plan
Reads every outputs/bench_<device>.json that exists, so GPU results can be added later.
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    out = Path("outputs")
    prices = json.loads(Path("config/prices.json").read_text())
    rows = []
    for path in sorted(out.glob("bench_*.json")):
        bench = json.loads(path.read_text())
        dev = bench["info"]["device"]
        price = prices[dev]["usd_per_hour"]
        for r in bench["results"]:
            cost = price * r["epoch_time_s"] / 3600
            rows.append({"device": dev, "hardware": bench["info"]["hardware"], "workload": r["workload"],
                         "batch_size": r["batch_size"], "epoch_time_s": r["epoch_time_s"],
                         "throughput_sps": r["throughput_sps"], "peak_memory_mb": r["peak_memory_mb"],
                         "usd_per_hour": price, "usd_per_epoch": cost, "usd_per_1k_epochs": round(cost * 1000, 4)})
    if not rows:
        raise SystemExit("No outputs/bench_*.json found. Run src.benchmark first.")

    with open(out / "compute_plan.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    line = "{:<7} {:<11} {:>5} {:>12} {:>13} {:>10} {:>14}"
    print(line.format("device", "workload", "batch", "epoch_time_s", "throughput/s", "$/hour", "$ per 1k ep"))
    for r in rows:
        print(line.format(r["device"], r["workload"], r["batch_size"], "{:.3f}".format(r["epoch_time_s"]),
                          "{:,.1f}".format(r["throughput_sps"]), "{:.3f}".format(r["usd_per_hour"]),
                          "{:.4f}".format(r["usd_per_1k_epochs"])))

    print()
    print("Recommendation per workload (cheapest $ per epoch among measured devices):")
    for wl in sorted({r["workload"] for r in rows}):
        best = min((r for r in rows if r["workload"] == wl), key=lambda r: r["usd_per_epoch"])
        print("  {:<11} -> {} (batch {}), {:.4f} $ per 1k epochs".format(
            wl, best["device"], best["batch_size"], best["usd_per_1k_epochs"]))

    labels = ["{}\n{} b{}".format(r["device"], r["workload"], r["batch_size"]) for r in rows]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))
    ax1.bar(labels, [r["epoch_time_s"] for r in rows], color="#2563eb")
    ax1.set_title("Epoch time (s, log scale, lower is better)")
    ax2.bar(labels, [r["usd_per_1k_epochs"] for r in rows], color="#16a34a")
    ax2.set_title("Cost per 1,000 epochs (USD, log scale, lower is better)")
    for ax in (ax1, ax2):
        ax.set_yscale("log")
        ax.tick_params(axis="x", labelsize=8, labelrotation=30)
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "compute_plan.png", dpi=150)
    print("saved -> outputs/compute_plan.csv, outputs/compute_plan.png")


if __name__ == "__main__":
    main()
