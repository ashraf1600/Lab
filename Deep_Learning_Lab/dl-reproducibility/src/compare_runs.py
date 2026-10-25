"""Compare runs bit-for-bit against the first run and plot their loss curves.

  python -m src.compare_runs outputs/run_a outputs/run_b outputs/run_c
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt  # noqa: E402


def load_run(run_dir):
    path = Path(run_dir) / "metrics.json"
    if not path.exists():
        raise SystemExit(f"metrics.json not found in {run_dir}. Train that run first.")
    return json.loads(path.read_text())


def compare(ref, other):
    a, b = ref["step_losses_hex"], other["step_losses_hex"]
    n = min(len(a), len(b))
    mismatched = [i for i in range(n) if a[i] != b[i]]
    max_diff = max((abs(float.fromhex(a[i]) - float.fromhex(b[i])) for i in range(n)), default=0.0)
    hash_match = ref["model_sha256"] == other["model_sha256"]
    return {
        "run": other["run_name"],
        "seed": other["seed"],
        "mismatched_steps": len(mismatched),
        "first_mismatch_step": mismatched[0] if mismatched else None,
        "max_abs_loss_diff": max_diff,
        "model_hash_match": hash_match,
        "final_val_accuracy": other["final_val_accuracy"],
        "bit_identical": len(a) == len(b) and not mismatched and hash_match,
    }


def plot(runs, out_path):
    ref = [float.fromhex(h) for h in runs[0]["step_losses_hex"]]
    styles = ["-", "--", ":", "-."]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    for i, run in enumerate(runs):
        vals = [float.fromhex(h) for h in run["step_losses_hex"]]
        label = "{} (seed={}, deterministic={})".format(run["run_name"], run["seed"], run["deterministic"])
        ax1.plot(vals, styles[i % 4], linewidth=3 if i == 0 else 1.5, alpha=0.5 if i == 0 else 1, label=label)
        if i > 0:
            ax2.plot([abs(v - r) for v, r in zip(vals, ref)], styles[i % 4], label="|{} - {}|".format(run["run_name"], runs[0]["run_name"]))
    ax1.set_title("Training loss per step")
    ax1.set_ylabel("loss")
    ax1.legend()
    ax1.grid(alpha=0.3)
    ax2.set_xlabel("training step")
    ax2.set_ylabel("abs diff vs reference")
    ax2.legend()
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)


def main():
    parser = argparse.ArgumentParser(description="Bit-level comparison of training runs")
    parser.add_argument("runs", nargs="+", help="run folders; the first is the reference")
    parser.add_argument("--output-dir", default="outputs/comparison")
    args = parser.parse_args()
    if len(args.runs) < 2:
        raise SystemExit("Give at least two run folders.")

    runs = [load_run(r) for r in args.runs]
    results = [compare(runs[0], other) for other in runs[1:]]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plot(runs, out_dir / "loss_curves.png")
    report = {"reference": runs[0]["run_name"], "reference_sha256": runs[0]["model_sha256"], "comparisons": results}
    (out_dir / "comparison_report.json").write_text(json.dumps(report, indent=2))

    ref = runs[0]
    print("Reference: {} (seed={}, steps={}, val_acc={:.4f})".format(
        ref["run_name"], ref["seed"], len(ref["step_losses_hex"]), ref["final_val_accuracy"]))
    row = "{:<7} {:>11} {:>11} {:>11} {:>13} {:>11} {:>8}  {}"
    print(row.format("run", "seed", "mismatched", "first_diff", "max_abs_diff", "hash_match", "val_acc", "verdict"))
    for r in results:
        first = "-" if r["first_mismatch_step"] is None else r["first_mismatch_step"]
        verdict = "BIT-IDENTICAL" if r["bit_identical"] else "DIFFERENT"
        print(row.format(r["run"], r["seed"], r["mismatched_steps"], first, "{:.3e}".format(r["max_abs_loss_diff"]),
                         str(r["model_hash_match"]), "{:.4f}".format(r["final_val_accuracy"]), verdict))
    print("Saved: {}, {}".format(out_dir / "loss_curves.png", out_dir / "comparison_report.json"))


if __name__ == "__main__":
    main()
