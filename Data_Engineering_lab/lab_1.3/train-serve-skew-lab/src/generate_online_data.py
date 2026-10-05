"""
Simulate Production Data Drift for QuickCart Online Serving.

Simulates post-deployment production conditions (e.g. peak holiday rush, rainy weather,
expanded delivery radiuses, and influx of newer customers) where incoming feature
distributions drift significantly from the historical training baseline:
- order_amount  : shifts from ~500 -> ~850
- delivery_time : shifts from ~30  -> ~48 min
- distance      : shifts from ~6.5 -> ~10.5 km
- customer_orders: shifts towards newer accounts (~5 past orders)

Saves incoming production data without ground-truth labels to data/online_data.csv.
"""

import os
import numpy as np
import pandas as pd


def generate_drifted_online_data(num_samples: int = 500, random_seed: int = 101) -> pd.DataFrame:
    np.random.seed(random_seed)

    order_ids = [f"ORD-ONL-{20000 + i}" for i in range(num_samples)]

    # Shifted production feature distributions (Data Drift)
    # 1. order_amount: mean shifts to $850, std ~ $120
    order_amount = np.random.normal(loc=850.0, scale=120.0, size=num_samples)
    order_amount = np.clip(order_amount, 350.0, 1600.0).round(2)

    # 2. delivery_time (minutes): mean shifts to 48.0 min, std ~ 8.0
    delivery_time = np.random.normal(loc=48.0, scale=8.0, size=num_samples)
    delivery_time = np.clip(delivery_time, 25.0, 85.0).round(1)

    # 3. customer_orders: newer customer base, mean ~ 5, poisson
    customer_orders = np.random.poisson(lam=5.0, size=num_samples)
    customer_orders = np.clip(customer_orders, 1, 20)

    # 4. distance (kilometers): mean shifts to 10.5 km, std ~ 3.0
    distance = np.random.normal(loc=10.5, scale=3.0, size=num_samples)
    distance = np.clip(distance, 2.0, 22.0).round(2)

    # Notice: In real online production serving, ground-truth 'cancelled' is unknown at scoring time!
    df = pd.DataFrame(
        {
            "order_id": order_ids,
            "order_amount": order_amount,
            "delivery_time": delivery_time,
            "customer_orders": customer_orders,
            "distance": distance,
        }
    )

    return df


def main():
    print("=" * 60)
    print(" QuickCart ML Pipeline — Step 4: Simulating Production Data Drift")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_path = os.path.join(base_dir, "data", "train.csv")
    online_path = os.path.join(base_dir, "data", "online_data.csv")

    print("[INFO] Generating 500 online production order records with intentional drift...")
    online_df = generate_drifted_online_data(num_samples=500, random_seed=101)
    online_df.to_csv(online_path, index=False)
    print(f"[SUCCESS] Online serving dataset saved to: {online_path}")

    # Inspect and compare feature distributions against training data
    if os.path.exists(train_path):
        train_df = pd.read_csv(train_path)
        features = ["order_amount", "delivery_time", "customer_orders", "distance"]

        print("\n" + "=" * 60)
        print(" FEATURE DISTRIBUTION DRIFT INSPECTION")
        print("=" * 60)
        print(f"{'Feature':<18} | {'Training Mean':<14} | {'Online Mean':<14} | {'Shift Delta':<12}")
        print("-" * 65)

        for feat in features:
            tr_mean = train_df[feat].mean()
            on_mean = online_df[feat].mean()
            delta = on_mean - tr_mean
            pct = (delta / tr_mean) * 100
            print(f"{feat:<18} | {tr_mean:<14.2f} | {on_mean:<14.2f} | {delta:+7.2f} ({pct:+.1f}%)")

        print("=" * 60)
        print("[ANALYSIS] Production data demonstrates significant feature distribution drift!")
        print("=" * 60)
    else:
        print("[WARNING] train.csv not found to print comparison.")


if __name__ == "__main__":
    main()
