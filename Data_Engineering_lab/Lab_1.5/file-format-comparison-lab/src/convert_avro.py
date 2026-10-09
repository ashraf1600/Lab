"""
Apache Avro Converter and Reader for QuickCart Order Data.
Encodes canonical order records into row-oriented Avro format using FastAvro and Snappy compression.
"""

import os
import sys
import time
import json
from pathlib import Path
import fastavro
import pyarrow.parquet as pq

# Set up project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def load_avro_schema(schema_path: Path) -> dict:
    """Loads and parses Apache Avro JSON schema contract."""
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_dict = json.load(f)
    return fastavro.schema.parse_schema(schema_dict)

def write_avro(input_raw_path: Path, output_avro_path: Path, schema_path: Path, codec: str = "snappy") -> dict:
    """Reads baseline dataset and serializes records into Apache Avro binary container."""
    print(f"[Avro] Reading baseline data from {input_raw_path.name}...")
    table = pq.read_table(input_raw_path)
    records = table.to_pylist()
    num_rows = len(records)
    
    schema = load_avro_schema(schema_path)
    
    print(f"[Avro] Serializing {num_rows:,} records to {output_avro_path.name} (codec={codec})...")
    start_time = time.perf_counter()
    with open(output_avro_path, "wb") as f:
        fastavro.writer(f, schema, records, codec=codec)
    write_duration = time.perf_counter() - start_time
    
    file_size_bytes = os.path.getsize(output_avro_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    write_throughput = num_rows / write_duration
    
    return {
        "format": "Avro",
        "file_path": str(output_avro_path),
        "codec": codec,
        "num_rows": num_rows,
        "write_seconds": write_duration,
        "write_throughput_rec_sec": write_throughput,
        "file_size_bytes": file_size_bytes,
        "file_size_mb": file_size_mb
    }

def read_avro(avro_path: Path) -> dict:
    """Reads records sequentially from Apache Avro binary container."""
    print(f"[Avro] Deserializing from {avro_path.name} (full row scan)...")
    
    start_time = time.perf_counter()
    with open(avro_path, "rb") as f:
        reader = fastavro.reader(f)
        records = [rec for rec in reader]
    read_duration = time.perf_counter() - start_time
    
    num_rows = len(records)
    read_throughput = num_rows / read_duration
    return {
        "format": "Avro",
        "num_rows": num_rows,
        "read_seconds": read_duration,
        "read_throughput_rec_sec": read_throughput
    }

def main():
    raw_path = PROJECT_ROOT / "data" / "orders_raw.parquet"
    avro_schema_path = PROJECT_ROOT / "schemas" / "order_schema.avsc"
    out_path = PROJECT_ROOT / "data" / "orders.avro"
    
    if not raw_path.exists():
        print(f"Error: Raw dataset not found at {raw_path}. Run generate_data.py first.")
        sys.exit(1)
        
    write_res = write_avro(raw_path, out_path, avro_schema_path, codec="snappy")
    print(f" -> Write Time:       {write_res['write_seconds']:.4f} s ({write_res['write_throughput_rec_sec']:,.0f} records/s)")
    print(f" -> File Size:        {write_res['file_size_mb']:.2f} MB ({write_res['file_size_bytes']:,} bytes)")
    
    read_res = read_avro(out_path)
    print(f" -> Full Read Time:   {read_res['read_seconds']:.4f} s ({read_res['read_throughput_rec_sec']:,.0f} records/s)")

if __name__ == "__main__":
    main()
