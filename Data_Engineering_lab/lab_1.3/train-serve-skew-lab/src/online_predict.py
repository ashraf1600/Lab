"""
Serve Unchanged Model on Drifted Online Production Data.

Loads the frozen model artifact (models/model.pkl) without retraining, executes
inference on the drifted online dataset (data/online_data.csv), and records
the altered online prediction distribution into results/online_predictions.csv.
"""

import os
import pickle
import pandas as pd


def online_predict():
    print("=" * 60)
    print(" QuickCart ML Pipeline — Step 5: Online Production Serving")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    online_path = os.path.join(base_dir, "data", "online_data.csv")
    model_path = os.path.join(base_dir, "models", "model.pkl")
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, "online_predictions.csv")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model artifact not found at {model_path}. Run train.py first!")
    if not os.path.exists(online_path):
        raise FileNotFoundError(
            f"Online dataset not found at {online_path}. Run generate_online_data.py first!"
        )

    print(f"[INFO] Loading frozen model artifact : {model_path}")
    print("[CRITICAL] Model is NOT retrained; serving in production exactly as deployed.")
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    print(f"[INFO] Loading incoming online data  : {online_path}")
    online_df = pd.read_csv(online_path)

    feature_cols = ["order_amount", "delivery_time", "customer_orders", "distance"]
    X_online = online_df[feature_cols]

    print(f"[INFO] Generating online predictions for {len(X_online)} incoming orders...")
    predictions = model.predict(X_online)
    probabilities = model.predict_proba(X_online)[:, 1]

    # Online prediction distribution
    total_online = len(predictions)
    pred_0 = (predictions == 0).sum()
    pred_1 = (predictions == 1).sum()
    pct_0 = (pred_0 / total_online) * 100
    pct_1 = (pred_1 / total_online) * 100

    print("\n--- Online Prediction Distribution (Serving) ---")
    print(f"  • Predicted Class 0 (Fulfilled) : {pred_0:3d} ({pct_0:.1f}%)")
    print(f"  • Predicted Class 1 (Cancelled) : {pred_1:3d} ({pct_1:.1f}%)")
    print(f"  • Average Predicted Cancellation Probability: {probabilities.mean():.4f}")

    # Build results DataFrame
    results_df = online_df.copy()
    results_df["predicted_class"] = predictions
    results_df["predicted_prob"] = probabilities.round(4)

    results_df.to_csv(out_path, index=False)
    print(f"\n[SUCCESS] Online predictions saved to: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    online_predict()
