"""
Prepare Historical Training and Test Datasets for QuickCart Order Cancellation Model.

Generates a realistic historical dataset reflecting typical operating conditions:
- Moderate order values, fast delivery times, established customers.
- Trains a baseline ground-truth relationship where severe delivery delays
  and high distances drive cancellation risk.
- Splits into 80% train and 20% test partitions.
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def generate_historical_dataset(num_samples: int = 1000, random_seed: int = 42) -> pd.DataFrame:
    np.random.seed(random_seed)

    order_ids = [f"ORD-{10000 + i}" for i in range(num_samples)]

    # Historical feature distributions (normal operating conditions)
    # 1. order_amount: mean ~ $500, std ~ $80
    order_amount = np.random.normal(loc=500.0, scale=80.0, size=num_samples)
    order_amount = np.clip(order_amount, 200.0, 950.0).round(2)

    # 2. delivery_time (minutes): mean ~ 30, std ~ 6
    delivery_time = np.random.normal(loc=30.0, scale=6.0, size=num_samples)
    delivery_time = np.clip(delivery_time, 15.0, 55.0).round(1)

    # 3. customer_orders (loyalty / past orders count): mean ~ 8, poisson
    customer_orders = np.random.poisson(lam=8.0, size=num_samples)
    customer_orders = np.clip(customer_orders, 1, 25)

    # 4. distance (kilometers): mean ~ 6.5 km, std ~ 2.0
    distance = np.random.normal(loc=6.5, scale=2.0, size=num_samples)
    distance = np.clip(distance, 1.0, 15.0).round(2)

    # Latent operational stress score (delays, long transit, high cart value drive cancellation)
    z = (
        -0.85
        + 0.09 * (delivery_time - 30.0)
        + 0.18 * (distance - 6.5)
        + 0.0025 * (order_amount - 500.0)
        - 0.14 * (customer_orders - 8.0)
        + np.random.normal(0, 0.35, size=num_samples)
    )
    cancelled = (z > 0).astype(int)

    df = pd.DataFrame(
        {
            "order_id": order_ids,
            "order_amount": order_amount,
            "delivery_time": delivery_time,
            "customer_orders": customer_orders,
            "distance": distance,
            "cancelled": cancelled,
        }
    )

    return df


def main():
    print("=" * 60)
    print(" QuickCart ML Pipeline — Step 1: Historical Data Preparation")
    print("=" * 60)

    # Set up directory paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    train_path = os.path.join(data_dir, "train.csv")
    test_path = os.path.join(data_dir, "test.csv")

    print("[INFO] Synthesizing historical QuickCart orders (1,000 records)...")
    dataset = generate_historical_dataset(num_samples=1000, random_seed=42)

    train_df, test_df = train_test_split(
        dataset, test_size=0.20, random_state=42, stratify=dataset["cancelled"]
    )

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"[SUCCESS] Saved training dataset : {train_path} ({len(train_df)} rows)")
    print(f"[SUCCESS] Saved test dataset     : {test_path} ({len(test_df)} rows)")

    print("\n--- Training Set Class Distribution ---")
    c0 = (train_df["cancelled"] == 0).sum()
    c1 = (train_df["cancelled"] == 1).sum()
    total = len(train_df)
    print(f"Class 0 (Fulfilled) : {c0} ({c0/total*100:.1f}%)")
    print(f"Class 1 (Cancelled) : {c1} ({c1/total*100:.1f}%)")

    print("\n--- Training Set Feature Means ---")
    features = ["order_amount", "delivery_time", "customer_orders", "distance"]
    for feat in features:
        print(f"  • {feat:<18}: {train_df[feat].mean():.2f}")

    print("=" * 60)


if __name__ == "__main__":
    main()
