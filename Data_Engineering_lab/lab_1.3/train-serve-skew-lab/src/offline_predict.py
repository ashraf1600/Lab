"""
Evaluate QuickCart Model Offline on Fixed Test Dataset.

Generates baseline predictions and probabilities on the reserved offline test set,
evaluates offline classification performance metrics, records the reference
prediction distribution, and saves results to results/offline_predictions.csv.
"""

import os
import pickle
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def offline_predict():
    print("=" * 60)
    print(" QuickCart ML Pipeline — Step 3: Offline Model Evaluation")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_path = os.path.join(base_dir, "data", "test.csv")
    model_path = os.path.join(base_dir, "models", "model.pkl")
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, "offline_predictions.csv")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model artifact not found at {model_path}. Run train.py first!")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test dataset not found at {test_path}. Run prepare_data.py first!")

    print(f"[INFO] Loading saved model artifact : {model_path}")
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    print(f"[INFO] Loading offline test dataset : {test_path}")
    test_df = pd.read_csv(test_path)

    feature_cols = ["order_amount", "delivery_time", "customer_orders", "distance"]
    target_col = "cancelled"

    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    print(f"[INFO] Generating predictions for {len(X_test)} offline test orders...")
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    # Offline evaluation metrics
    acc = accuracy_score(y_test, predictions)
    prec = precision_score(y_test, predictions, zero_division=0)
    rec = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)

    # Offline prediction distribution
    total_test = len(predictions)
    pred_0 = (predictions == 0).sum()
    pred_1 = (predictions == 1).sum()
    pct_0 = (pred_0 / total_test) * 100
    pct_1 = (pred_1 / total_test) * 100

    print("\n--- Offline Evaluation Metrics (Baseline) ---")
    print(f"  • Test Accuracy  : {acc * 100:.2f}%")
    print(f"  • Test Precision : {prec * 100:.2f}%")
    print(f"  • Test Recall    : {rec * 100:.2f}%")
    print(f"  • Test F1 Score  : {f1 * 100:.2f}%")

    print("\n--- Baseline Offline Prediction Distribution ---")
    print(f"  • Predicted Class 0 (Fulfilled) : {pred_0:3d} ({pct_0:.1f}%)")
    print(f"  • Predicted Class 1 (Cancelled) : {pred_1:3d} ({pct_1:.1f}%)")
    print(f"  • Average Cancellation Probability: {probabilities.mean():.4f}")

    # Build results DataFrame
    results_df = test_df.copy()
    results_df.rename(columns={"cancelled": "actual_cancelled"}, inplace=True)
    results_df["predicted_class"] = predictions
    results_df["predicted_prob"] = probabilities.round(4)

    results_df.to_csv(out_path, index=False)
    print(f"\n[SUCCESS] Offline predictions saved to: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    offline_predict()
