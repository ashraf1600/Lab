"""
Apache Parquet Converter and Reader for QuickCart Order Data.
Encodes canonical order records into columnar Parquet format using Snappy compression.
"""

import os
import sys
import time
from pathlib import Path
import pyarrow.parquet as pq

# Set up project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas.order_schema import ORDER_PYARROW_SCHEMA

def write_parquet(input_raw_path: Path, output_parquet_path: Path, compression: str = "snappy") -> dict:
    """Reads raw baseline table and serializes to Apache Parquet."""
    print(f"[Parquet] Reading baseline data from {input_raw_path.name}...")
    table = pq.read_table(input_raw_path, schema=ORDER_PYARROW_SCHEMA)
    
    print(f"[Parquet] Serializing {table.num_rows:,} records to {output_parquet_path.name} (compression={compression})...")
    start_time = time.perf_counter()
    pq.write_table(table, output_parquet_path, compression=compression)
    write_duration = time.perf_counter() - start_time
    
    file_size_bytes = os.path.getsize(output_parquet_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    write_throughput = table.num_rows / write_duration
    
    return {
        "format": "Parquet",
        "file_path": str(output_parquet_path),
        "compression": compression,
        "num_rows": table.num_rows,
        "write_seconds": write_duration,
        "write_throughput_rec_sec": write_throughput,
        "file_size_bytes": file_size_bytes,
        "file_size_mb": file_size_mb
    }

def read_parquet(parquet_path: Path, columns: list = None) -> dict:
    """Deserializes Apache Parquet table from disk, supporting optional column pruning."""
    col_msg = f"columns={columns}" if columns else "full scan (all columns)"
    print(f"[Parquet] Deserializing from {parquet_path.name} ({col_msg})...")
    
    start_time = time.perf_counter()
    table = pq.read_table(parquet_path, columns=columns)
    read_duration = time.perf_counter() - start_time
    
    read_throughput = table.num_rows / read_duration
    return {
        "format": "Parquet",
        "num_rows": table.num_rows,
        "columns_read": len(table.column_names),
        "read_seconds": read_duration,
        "read_throughput_rec_sec": read_throughput
    }

def main():
    raw_path = PROJECT_ROOT / "data" / "orders_raw.parquet"
    out_path = PROJECT_ROOT / "data" / "orders.parquet"
    
    if not raw_path.exists():
        print(f"Error: Raw dataset not found at {raw_path}. Run generate_data.py first.")
        sys.exit(1)
        
    write_res = write_parquet(raw_path, out_path, compression="snappy")
    print(f" -> Write Time:       {write_res['write_seconds']:.4f} s ({write_res['write_throughput_rec_sec']:,.0f} records/s)")
    print(f" -> File Size:        {write_res['file_size_mb']:.2f} MB ({write_res['file_size_bytes']:,} bytes)")
    
    read_res = read_parquet(out_path)
    print(f" -> Full Read Time:   {read_res['read_seconds']:.4f} s ({read_res['read_throughput_rec_sec']:,.0f} records/s)")
    
    # Demonstrate column projection
    proj_res = read_parquet(out_path, columns=["order_id", "order_amount", "payment_method"])
    print(f" -> Projected Read:   {proj_res['read_seconds']:.4f} s ({proj_res['columns_read']} columns)")

if __name__ == "__main__":
    main()
