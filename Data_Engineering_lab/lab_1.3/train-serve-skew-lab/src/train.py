"""
Train QuickCart Order Cancellation Model on Fixed Historical Dataset.

Builds a reproducible Scikit-Learn classification pipeline with feature scaling
and logistic regression, evaluates offline training performance, and serializes
the trained model artifact to models/model.pkl.
"""

import os
import pickle
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def train_model():
    print("=" * 60)
    print(" QuickCart ML Pipeline — Step 2: Model Training")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_path = os.path.join(base_dir, "data", "train.csv")
    model_dir = os.path.join(base_dir, "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "model.pkl")

    if not os.path.exists(train_path):
        raise FileNotFoundError(
            f"Training dataset not found at {train_path}. Run prepare_data.py first!"
        )

    print(f"[INFO] Loading training dataset: {train_path}")
    train_df = pd.read_csv(train_path)

    feature_cols = ["order_amount", "delivery_time", "customer_orders", "distance"]
    target_col = "cancelled"

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]

    print(f"[INFO] Features ({len(feature_cols)}): {feature_cols}")
    print(f"[INFO] Training samples : {len(X_train)}")

    # Construct ML pipeline with StandardScaler to ensure consistent preprocessing
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(random_state=42, max_iter=1000)),
        ]
    )

    print("[INFO] Fitting Logistic Regression model with feature scaling...")
    pipeline.fit(X_train, y_train)

    # Evaluate on training data
    y_pred = pipeline.predict(X_train)
    acc = accuracy_score(y_train, y_pred)
    prec = precision_score(y_train, y_pred, zero_division=0)
    rec = recall_score(y_train, y_pred, zero_division=0)
    f1 = f1_score(y_train, y_pred, zero_division=0)

    print("\n--- Model Training Baseline Evaluation ---")
    print(f"  • Accuracy  : {acc * 100:.2f}%")
    print(f"  • Precision : {prec * 100:.2f}%")
    print(f"  • Recall    : {rec * 100:.2f}%")
    print(f"  • F1 Score  : {f1 * 100:.2f}%")

    # Display learned feature weights (coefficients)
    coefs = pipeline.named_steps["classifier"].coef_[0]
    print("\n--- Learned Feature Coefficients ---")
    for feat, coef in zip(feature_cols, coefs):
        impact = "increases cancel risk" if coef > 0 else "reduces cancel risk"
        print(f"  • {feat:<18}: {coef:+.4f} ({impact})")

    # Serialize trained pipeline artifact
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)

    print(f"\n[SUCCESS] Model artifact successfully saved to: {model_path}")
    print("=" * 60)


if __name__ == "__main__":
    train_model()
