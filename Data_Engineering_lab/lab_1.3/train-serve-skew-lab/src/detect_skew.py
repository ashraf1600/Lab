"""
Detect and Quantify Train-Serve Skew & Feature Drift.

Compares feature distributions between training and online serving data, compares
offline baseline predictions against online predictions, evaluates drift thresholds,
generates results/skew_report.csv, renders ASCII terminal visualizations, and saves
a comparative multi-panel chart to results/skew_distribution.png.
"""

import os
import sys
import pandas as pd
import numpy as np

# Ensure Windows consoles don't crash on UTF-8 characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def render_ascii_bar(label: str, val: float, max_val: float, bar_length: int = 30) -> str:
    filled_len = int(round(bar_length * val / float(max_val))) if max_val > 0 else 0
    # Determine safe character based on terminal encoding
    enc = (sys.stdout.encoding or "").lower()
    char = "█" if "utf" in enc else "#"
    bar = char * filled_len
    return f"{label:<10}: {bar:<{bar_length}} ({val:.1f})"


def detect_skew():
    print("=" * 70)
    print(" QuickCart ML Monitoring — Step 6: Train-Serve Skew Detection")
    print("=" * 70)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_path = os.path.join(base_dir, "data", "train.csv")
    online_path = os.path.join(base_dir, "data", "online_data.csv")
    offline_pred_path = os.path.join(base_dir, "results", "offline_predictions.csv")
    online_pred_path = os.path.join(base_dir, "results", "online_predictions.csv")
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    report_path = os.path.join(results_dir, "skew_report.csv")
    plot_path = os.path.join(results_dir, "skew_distribution.png")

    for p, name in [
        (train_path, "train.csv"),
        (online_path, "online_data.csv"),
        (offline_pred_path, "offline_predictions.csv"),
        (online_pred_path, "online_predictions.csv"),
    ]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing required file: {name} at {p}")

    train_df = pd.read_csv(train_path)
    online_df = pd.read_csv(online_path)
    offline_preds = pd.read_csv(offline_pred_path)
    online_preds = pd.read_csv(online_pred_path)

    features = ["order_amount", "delivery_time", "customer_orders", "distance"]

    # 1. Feature Distribution Skew Analysis
    report_rows = []
    print("\n--- 1. FEATURE DRIFT ANALYSIS ---")
    print(f"{'Feature':<16} | {'Train Mean':<10} | {'Online Mean':<11} | {'Diff':<8} | {'% Drift':<8} | {'Status'}")
    print("-" * 72)

    for feat in features:
        tr_mean = train_df[feat].mean()
        on_mean = online_df[feat].mean()
        diff = on_mean - tr_mean
        pct_drift = (abs(diff) / tr_mean) * 100

        # Heuristic threshold: > 20% shift considered significant drift
        if pct_drift >= 20.0:
            status = "DRIFT DETECTED"
        elif pct_drift >= 10.0:
            status = "MODERATE SHIFT"
        else:
            status = "STABLE"

        print(
            f"{feat:<16} | {tr_mean:<10.2f} | {on_mean:<11.2f} | {diff:+8.2f} | {pct_drift:<7.1f}% | {status}"
        )

        report_rows.append(
            {
                "Feature": feat,
                "Training_Mean": round(tr_mean, 2),
                "Online_Mean": round(on_mean, 2),
                "Difference": round(diff, 2),
                "Percentage_Drift": round(pct_drift, 2),
                "Status": status,
            }
        )

    # 2. Prediction Shift Analysis
    off_total = len(offline_preds)
    on_total = len(online_preds)

    off_c0_pct = (offline_preds["predicted_class"] == 0).sum() / off_total * 100
    off_c1_pct = (offline_preds["predicted_class"] == 1).sum() / off_total * 100
    off_avg_prob = offline_preds["predicted_prob"].mean()

    on_c0_pct = (online_preds["predicted_class"] == 0).sum() / on_total * 100
    on_c1_pct = (online_preds["predicted_class"] == 1).sum() / on_total * 100
    on_avg_prob = online_preds["predicted_prob"].mean()

    c1_delta = on_c1_pct - off_c1_pct
    prob_delta = on_avg_prob - off_avg_prob

    print("\n--- 2. OFFLINE VS ONLINE PREDICTION DISTRIBUTION COMPARISON ---")
    print(f"{'Metric':<32} | {'Offline Baseline':<16} | {'Online Serving':<16} | {'Delta':<10}")
    print("-" * 80)
    print(f"{'Class 0 (Fulfilled) Ratio':<32} | {off_c0_pct:<15.1f}% | {on_c0_pct:<15.1f}% | {on_c0_pct - off_c0_pct:+9.1f}%")
    print(f"{'Class 1 (Cancelled) Ratio':<32} | {off_c1_pct:<15.1f}% | {on_c1_pct:<15.1f}% | {c1_delta:+9.1f}%")
    print(f"{'Mean Cancellation Probability':<32} | {off_avg_prob:<16.4f} | {on_avg_prob:<16.4f} | {prob_delta:+9.4f}")

    # Append prediction metrics to report
    report_rows.append(
        {
            "Feature": "PREDICTION: Class 1 Ratio (%)",
            "Training_Mean": round(off_c1_pct, 2),
            "Online_Mean": round(on_c1_pct, 2),
            "Difference": round(c1_delta, 2),
            "Percentage_Drift": round((abs(c1_delta) / off_c1_pct) * 100, 2),
            "Status": "HIGH SKEW" if abs(c1_delta) > 15 else "STABLE",
        }
    )

    report_df = pd.DataFrame(report_rows)
    report_df.to_csv(report_path, index=False)
    print(f"\n[SUCCESS] Comprehensive Skew Report saved to: {report_path}")

    # 3. Terminal ASCII Visualization (Step 17 requirement)
    print("\n" + "=" * 70)
    print(" STEP 17: ASCII DISTRIBUTION SKEW VISUALIZATION")
    print("=" * 70)
    for feat in ["order_amount", "delivery_time", "distance"]:
        tr_val = train_df[feat].mean()
        on_val = online_df[feat].mean()
        max_val = max(tr_val, on_val) * 1.25

        print(f"\nFeature: {feat.upper().replace('_', ' ')}")
        print("  " + render_ascii_bar("Training", tr_val, max_val, bar_length=30))
        print("  " + render_ascii_bar("Online", on_val, max_val, bar_length=30))

    # 4. Generate Graphical Chart if matplotlib is installed
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle("QuickCart Train-Serve Skew: Training Baseline vs Production Serving", fontsize=14, fontweight="bold")

        plot_features = [
            ("order_amount", "Order Amount ($)", axes[0, 0]),
            ("delivery_time", "Delivery Time (mins)", axes[0, 1]),
            ("distance", "Distance (km)", axes[1, 0]),
            ("customer_orders", "Customer Past Orders", axes[1, 1]),
        ]

        for col, title, ax in plot_features:
            ax.hist(train_df[col], bins=25, alpha=0.6, label="Training (Baseline)", color="#2563eb", density=True)
            ax.hist(online_df[col], bins=25, alpha=0.6, label="Online (Production)", color="#dc2626", density=True)
            ax.set_title(title, fontweight="bold")
            ax.set_xlabel("Value")
            ax.set_ylabel("Density")
            ax.legend(loc="upper right")
            ax.grid(True, linestyle="--", alpha=0.5)

        plt.tight_layout()
        plt.savefig(plot_path, dpi=200)
        plt.close()
        print(f"\n[SUCCESS] Visual distribution plot saved to: {plot_path}")
    except Exception as e:
        print(f"\n[NOTE] Matplotlib visualization skipped: {e}")

    # 5. Final Diagnostic Verdict (Step 18)
    print("\n" + "=" * 70)
    print(" STEP 18: TRAIN-SERVE SKEW DIAGNOSTIC VERDICT")
    print("=" * 70)
    if c1_delta > 15.0:
        print("🚨 SEVERE TRAIN-SERVE SKEW DETECTED!")
        print("  • Cause  : Incoming production features drifted significantly beyond training ranges.")
        print(f"  • Effect : Cancellation prediction frequency surged by +{c1_delta:.1f}%.")
        print("  • Action : Trigger production pipeline alert; collect new production labels and retrain model.")
    else:
        print("✅ No significant train-serve skew detected. Model serving remains aligned with training distribution.")
    print("=" * 70)


if __name__ == "__main__":
    detect_skew()
