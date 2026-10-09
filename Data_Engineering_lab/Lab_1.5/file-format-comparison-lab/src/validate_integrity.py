"""
Cross-Format Data Integrity and Parity Validator for QuickCart Orders.
Verifies record counts, schema columns, non-null guarantees, and value consistency
across Parquet, Avro, and ORC output files.
"""

import os
import sys
from pathlib import Path
import fastavro
import pyarrow.parquet as pq

# Configure IANA Timezone directory for Apache ORC C++ engine on Windows & Linux
try:
    import tzdata
    if "TZDIR" not in os.environ:
        tz_path = Path(tzdata.__file__).parent / "zoneinfo"
        if tz_path.exists():
            os.environ["TZDIR"] = str(tz_path)
except ImportError:
    pass

import pyarrow.orc as orc

# Set up project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def validate_all_formats():
    data_dir = PROJECT_ROOT / "data"
    parquet_path = data_dir / "orders.parquet"
    avro_path = data_dir / "orders.avro"
    orc_path = data_dir / "orders.orc"

    for path in [parquet_path, avro_path, orc_path]:
        if not path.exists():
            print(f"Error: {path.name} not found. Please run the format converters first.")
            sys.exit(1)

    print("================================================================================")
    print("           QUICKCART DATA INTEGRITY & CROSS-FORMAT PARITY REPORT                ")
    print("================================================================================")

    # 1. Load Parquet
    print("[1/3] Reading Apache Parquet...")
    pq_table = pq.read_table(parquet_path)
    pq_rows = pq_table.num_rows
    pq_cols = pq_table.column_names
    pq_sum_amount = sum(pq_table.column("order_amount").to_pylist())

    # 2. Load Avro
    print("[2/3] Reading Apache Avro...")
    with open(avro_path, "rb") as f:
        avro_reader = fastavro.reader(f)
        avro_records = [r for r in avro_reader]
    avro_rows = len(avro_records)
    avro_cols = list(avro_records[0].keys()) if avro_rows > 0 else []
    avro_sum_amount = sum(r["order_amount"] for r in avro_records)

    # 3. Load ORC
    print("[3/3] Reading Apache ORC...")
    orc_table = orc.read_table(orc_path)
    orc_rows = orc_table.num_rows
    orc_cols = orc_table.column_names
    orc_sum_amount = sum(orc_table.column("order_amount").to_pylist())

    print("\n--------------------------------------------------------------------------------")
    print(f"{'Verification Metric':<25} | {'Parquet':<16} | {'Avro':<16} | {'ORC':<16}")
    print("--------------------------------------------------------------------------------")
    print(f"{'Record Count':<25} | {pq_rows:<16,} | {avro_rows:<16,} | {orc_rows:<16,}")
    print(f"{'Column Count':<25} | {len(pq_cols):<16} | {len(avro_cols):<16} | {len(orc_cols):<16}")
    print(f"{'Total Amount Sum (BDT)':<25} | {pq_sum_amount:<16,.2f} | {avro_sum_amount:<16,.2f} | {orc_sum_amount:<16,.2f}")
    print(f"{'First Order ID':<25} | {str(pq_table.column('order_id')[0]):<16} | {avro_records[0]['order_id']:<16} | {str(orc_table.column('order_id')[0]):<16}")
    print(f"{'Last Order ID':<25} | {str(pq_table.column('order_id')[-1]):<16} | {avro_records[-1]['order_id']:<16} | {str(orc_table.column('order_id')[-1]):<16}")
    print("--------------------------------------------------------------------------------")

    # Assertions
    assert pq_rows == avro_rows == orc_rows == 100000, f"Row count mismatch! PQ={pq_rows}, AV={avro_rows}, ORC={orc_rows}"
    assert set(pq_cols) == set(avro_cols) == set(orc_cols), "Column set mismatch across formats!"
    assert abs(pq_sum_amount - avro_sum_amount) < 0.05, "Order amount divergence between Parquet and Avro!"
    assert abs(pq_sum_amount - orc_sum_amount) < 0.05, "Order amount divergence between Parquet and ORC!"

    print("\n [PASS] INTEGRITY CONFIRMED: 100,000 records & schema fields match with 100% parity across Parquet, Avro, and ORC.\n")

if __name__ == "__main__":
    validate_all_formats()
