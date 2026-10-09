"""
Apache ORC Converter and Reader for QuickCart Order Data.
Encodes canonical order records into columnar ORC format using PyArrow ORC engine.
"""

import os
import sys
import time
from pathlib import Path

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
import pyarrow.parquet as pq

# Set up project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas.order_schema import ORDER_PYARROW_SCHEMA

def write_orc(input_raw_path: Path, output_orc_path: Path, compression: str = "snappy") -> dict:
    """Reads raw baseline table and serializes to Apache ORC columnar format."""
    print(f"[ORC] Reading baseline data from {input_raw_path.name}...")
    table = pq.read_table(input_raw_path, schema=ORDER_PYARROW_SCHEMA)
    
    print(f"[ORC] Serializing {table.num_rows:,} records to {output_orc_path.name} (compression={compression})...")
    start_time = time.perf_counter()
    orc.write_table(table, output_orc_path, compression=compression)
    write_duration = time.perf_counter() - start_time
    
    file_size_bytes = os.path.getsize(output_orc_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    write_throughput = table.num_rows / write_duration
    
    return {
        "format": "ORC",
        "file_path": str(output_orc_path),
        "compression": compression,
        "num_rows": table.num_rows,
        "write_seconds": write_duration,
        "write_throughput_rec_sec": write_throughput,
        "file_size_bytes": file_size_bytes,
        "file_size_mb": file_size_mb
    }

def read_orc(orc_path: Path, columns: list = None) -> dict:
    """Deserializes Apache ORC table from disk with optional stripe column projection."""
    col_msg = f"columns={columns}" if columns else "full scan (all columns)"
    print(f"[ORC] Deserializing from {orc_path.name} ({col_msg})...")
    
    start_time = time.perf_counter()
    table = orc.read_table(orc_path, columns=columns)
    read_duration = time.perf_counter() - start_time
    
    read_throughput = table.num_rows / read_duration
    return {
        "format": "ORC",
        "num_rows": table.num_rows,
        "columns_read": len(table.column_names),
        "read_seconds": read_duration,
        "read_throughput_rec_sec": read_throughput
    }

def main():
    raw_path = PROJECT_ROOT / "data" / "orders_raw.parquet"
    out_path = PROJECT_ROOT / "data" / "orders.orc"
    
    if not raw_path.exists():
        print(f"Error: Raw dataset not found at {raw_path}. Run generate_data.py first.")
        sys.exit(1)
        
    write_res = write_orc(raw_path, out_path, compression="snappy")
    print(f" -> Write Time:       {write_res['write_seconds']:.4f} s ({write_res['write_throughput_rec_sec']:,.0f} records/s)")
    print(f" -> File Size:        {write_res['file_size_mb']:.2f} MB ({write_res['file_size_bytes']:,} bytes)")
    
    read_res = read_orc(out_path)
    print(f" -> Full Read Time:   {read_res['read_seconds']:.4f} s ({read_res['read_throughput_rec_sec']:,.0f} records/s)")
    
    # Demonstrate column projection
    proj_res = read_orc(out_path, columns=["order_id", "order_amount", "payment_method"])
    print(f" -> Projected Read:   {proj_res['read_seconds']:.4f} s ({proj_res['columns_read']} columns)")

if __name__ == "__main__":
    main()
