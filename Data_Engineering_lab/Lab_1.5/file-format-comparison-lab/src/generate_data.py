"""
Dataset Generator for QuickCart Order Transactions.
Generates 100,000 synthetic transactional records conforming to
the canonical QuickCart schema and writes to data/orders_raw.parquet.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Set up project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas.order_schema import ORDER_PYARROW_SCHEMA

def generate_orders(num_records: int = 100000, seed: int = 42) -> pa.Table:
    """Generate reproducible synthetic QuickCart order records."""
    np.random.seed(seed)
    print(f"Generating {num_records:,} synthetic QuickCart order records...")

    order_ids = [f"ORD-{i:07d}" for i in range(1, num_records + 1)]
    customer_ids = [f"CUST-{np.random.randint(1, 20000):05d}" for _ in range(num_records)]

    # Timestamps spanning last 30 days up to current epoch ms
    base_epoch_ms = 1717200000000  # 2024-06-01 00:00:00 UTC
    random_offsets = np.random.randint(0, 30 * 24 * 3600 * 1000, size=num_records, dtype=np.int64)
    order_timestamps = base_epoch_ms + random_offsets

    item_counts = np.random.randint(1, 15, size=num_records, dtype=np.int32)
    order_amounts = np.round(np.random.uniform(50.0, 3500.0, size=num_records), 2)
    delivery_distances = np.round(np.random.uniform(0.5, 25.0, size=num_records), 2)

    payment_channels = np.array(["credit_card", "bKash", "cash_on_delivery", "nagad", "debit_card"])
    payment_probs = [0.25, 0.40, 0.20, 0.10, 0.05]
    payment_methods = np.random.choice(payment_channels, size=num_records, p=payment_probs)

    is_cancelled = np.random.choice([False, True], size=num_records, p=[0.95, 0.05])

    # Construct PyArrow Table using canonical schema
    arrays = [
        pa.array(order_ids, type=pa.string()),
        pa.array(customer_ids, type=pa.string()),
        pa.array(order_timestamps, type=pa.timestamp("ms")),
        pa.array(item_counts, type=pa.int32()),
        pa.array(order_amounts, type=pa.float64()),
        pa.array(delivery_distances, type=pa.float64()),
        pa.array(payment_methods, type=pa.string()),
        pa.array(is_cancelled, type=pa.bool_()),
    ]

    table = pa.Table.from_arrays(arrays, schema=ORDER_PYARROW_SCHEMA)
    return table

def main():
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "orders_raw.parquet"

    table = generate_orders(num_records=100000)

    print(f"Writing raw baseline to {output_path}...")
    pq.write_table(table, output_path, compression="snappy")

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print("\nDataset Generation Complete:")
    print(f" - Total Rows:        {table.num_rows:,}")
    print(f" - Total Columns:     {table.num_columns}")
    print(f" - Schema Fields:     {table.schema.names}")
    print(f" - Baseline File:     {output_path.name}")
    print(f" - File Size:         {file_size_mb:.2f} MB")
    print(f" - In-Memory Size:    {table.nbytes / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    main()
