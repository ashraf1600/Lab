"""Combine training metrics and the FLOPs profile into one comparison table and chart.

  python -m src.compare
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

FIT = {
    "cnn": "images / grids",
    "lstm": "ordered signals",
    "transformer": "text / tokens",
}


def main():
    out = Path("outputs")
    profile = json.loads((out / "profile.json").read_text())
    rows = []
    for name in ("cnn", "lstm", "transformer"):
        m = json.loads((out / name / "metrics.json").read_text())
        p = profile["models"][name]
        rows.append({"model": name, "task": m["task"], "params": p["params"],
                     "flops_per_sample": p["flops_per_sample"], "val_accuracy": round(m["val_accuracy"], 4),
                     "train_seconds": m["train_seconds"], "best_fit": FIT[name]})

    with open(out / "comparison.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    row = "{:<12} {:>9} {:>13} {:>8} {:>8}  {}"
    print(row.format("model", "params", "FLOPs/sample", "val_acc", "train_s", "best fit"))
    for r in rows:
        print(row.format(r["model"], "{:,}".format(r["params"]), "{:,}".format(r["flops_per_sample"]),
                         "{:.4f}".format(r["val_accuracy"]), "{:.1f}".format(r["train_seconds"]), r["best_fit"]))

    names = [r["model"] for r in rows]
    xs = list(range(len(names)))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.bar([i - 0.2 for i in xs], [r["params"] for r in rows], width=0.4, label="parameters")
    ax1.bar([i + 0.2 for i in xs], [r["flops_per_sample"] for r in rows], width=0.4, label="FLOPs / sample")
    ax1.set_xticks(xs, names)
    ax1.set_yscale("log")
    ax1.set_title("Model size and compute (one sample)")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    s = profile["seq_scaling"]
    ax2.plot(s["lengths"], s["lstm"], "o-", label="LSTM")
    ax2.plot(s["lengths"], s["transformer"], "s-", label="Transformer")
    ax2.set_xscale("log", base=2)
    ax2.set_yscale("log")
    ax2.set_xlabel("sequence length")
    ax2.set_ylabel("FLOPs / sample")
    ax2.set_title("Compute vs sequence length")
    ax2.legend()
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "architecture_comparison.png", dpi=150)
    print("saved -> outputs/comparison.csv, outputs/architecture_comparison.png")


if __name__ == "__main__":
    main()
