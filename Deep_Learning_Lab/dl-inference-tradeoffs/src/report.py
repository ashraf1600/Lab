"""Turn outputs/loadtest_results.json into latency_summary.csv and latency_report.png."""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path("outputs")
COLORS = {"online": "#2563eb", "batch": "#ea580c"}


def main():
    data = json.loads((OUT / "loadtest_results.json").read_text())
    rows = data["summaries"]

    with open(OUT / "latency_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17, 5))
    labels = ["{}\n{}".format(r["mode"], r["pattern"]) for r in rows]
    xs = range(len(rows))
    w = 0.38
    ax1.bar([x - w / 2 for x in xs], [r["p50_ms"] for r in rows], w, label="p50", color="#94a3b8")
    ax1.bar([x + w / 2 for x in xs], [r["p95_ms"] for r in rows], w, label="p95",
            color=[COLORS[r["mode"]] for r in rows])
    ax1.set_yscale("log")
    ax1.set_xticks(list(xs), labels, fontsize=8)
    ax1.set_ylabel("latency per image (ms, log scale)")
    ax1.set_title("p50 vs p95 latency (lower is better)")
    ax1.legend()

    ax2.bar(list(xs), [r["throughput_ips"] for r in rows], color=[COLORS[r["mode"]] for r in rows])
    ax2.set_xticks(list(xs), labels, fontsize=8)
    ax2.set_ylabel("images per second")
    ax2.set_title("throughput (higher is better)")

    for mode in ("online", "batch"):
        reqs = data["requests"].get(mode + "_bursty", [])
        ax3.scatter([r["sent_s"] for r in reqs], [r["latency_ms"] for r in reqs], s=8,
                    color=COLORS[mode], label=mode, alpha=0.7)
    ax3.set_xlabel("time the image was sent (s)")
    ax3.set_ylabel("latency (ms)")
    ax3.set_title("bursty load: latency of every image")
    ax3.legend()

    for ax in (ax1, ax2, ax3):
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "latency_report.png", dpi=120)

    print("{:<7} {:<7} {:>8} {:>8} {:>10} {:>10}".format("mode", "pattern", "p50_ms", "p95_ms", "p95/p50", "images/s"))
    for r in rows:
        print("{:<7} {:<7} {:>8.2f} {:>8.2f} {:>10.1f} {:>10.1f}".format(
            r["mode"], r["pattern"], r["p50_ms"], r["p95_ms"], r["p95_ms"] / r["p50_ms"], r["throughput_ips"]))

    def pick(pattern, key, best):
        cand = [r for r in rows if r["pattern"] == pattern]
        return best(cand, key=lambda r: r[key])["mode"] if cand else "n/a"

    print("lowest p50 under steady load : {}".format(pick("steady", "p50_ms", min)))
    print("lowest p95 under bursty load : {}".format(pick("bursty", "p95_ms", min)))
    print("highest throughput (flood)   : {}".format(pick("flood", "throughput_ips", max)))
    print("saved -> {} and {}".format(OUT / "latency_summary.csv", OUT / "latency_report.png"))


if __name__ == "__main__":
    main()
