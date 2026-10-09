"""
Comprehensive Benchmark Suite for QuickCart Storage Formats.
Empirically evaluates Parquet, Avro, and ORC across:
  - Serialization (Write) Throughput
  - Full-Scan & Projected (Read) Throughput
  - Disk Space & Compression Efficiency
Exports machine-readable metrics to results/benchmark_report.json.
"""

import os
import sys
import time
import json
import statistics
from pathlib import Path
from tabulate import tabulate

# Configure IANA Timezone directory for Apache ORC C++ engine on Windows & Linux
try:
    import tzdata
    if "TZDIR" not in os.environ:
        tz_path = Path(tzdata.__file__).parent / "zoneinfo"
        if tz_path.exists():
            os.environ["TZDIR"] = str(tz_path)
except ImportError:
    pass

import pyarrow.parquet as pq
import pyarrow.orc as orc
import fastavro

# Set up project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas.order_schema import ORDER_PYARROW_SCHEMA

def run_benchmarks(iterations: int = 5):
    data_dir = PROJECT_ROOT / "data"
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    raw_path = data_dir / "orders_raw.parquet"
    if not raw_path.exists():
        print(f"Error: {raw_path} not found. Run generate_data.py first.")
        sys.exit(1)

    # 1. Load baseline memory table
    baseline_table = pq.read_table(raw_path, schema=ORDER_PYARROW_SCHEMA)
    num_rows = baseline_table.num_rows
    in_memory_bytes = baseline_table.nbytes
    in_memory_mb = in_memory_bytes / (1024 * 1024)

    # Load Avro schema & record dictionaries
    with open(PROJECT_ROOT / "schemas" / "order_schema.avsc", "r", encoding="utf-8") as f:
        avro_schema = fastavro.schema.parse_schema(json.load(f))
    avro_records = baseline_table.to_pylist()

    test_files = {
        "Parquet": data_dir / "orders.parquet",
        "Avro": data_dir / "orders.avro",
        "ORC": data_dir / "orders.orc"
    }

    metrics = {}

    print("================================================================================")
    print(f"       STARTING QUICKCART STORAGE BENCHMARK ({iterations} TIMED ITERATIONS)       ")
    print("================================================================================")
    print(f" Dataset Scale: {num_rows:,} records | In-Memory Table: {in_memory_mb:.2f} MB\n")

    # -------------------------------------------------------------
    # PARQUET BENCHMARK
    # -------------------------------------------------------------
    print("[1/3] Benchmarking Apache Parquet (Snappy)...")
    pq_path = test_files["Parquet"]
    
    # Warmup
    pq.write_table(baseline_table, pq_path, compression="snappy")
    _ = pq.read_table(pq_path)

    # Write iterations
    write_times_pq = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        pq.write_table(baseline_table, pq_path, compression="snappy")
        write_times_pq.append(time.perf_counter() - t0)

    # Full Read iterations
    read_times_pq = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = pq.read_table(pq_path)
        read_times_pq.append(time.perf_counter() - t0)

    # Projected Read (3 columns)
    proj_times_pq = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = pq.read_table(pq_path, columns=["order_id", "order_amount", "payment_method"])
        proj_times_pq.append(time.perf_counter() - t0)

    size_pq = os.path.getsize(pq_path)
    metrics["Parquet"] = {
        "file_size_bytes": size_pq,
        "file_size_mb": round(size_pq / (1024 * 1024), 2),
        "compression_ratio": round(in_memory_bytes / size_pq, 2),
        "mean_write_s": round(statistics.mean(write_times_pq), 4),
        "write_throughput_rec_sec": round(num_rows / statistics.mean(write_times_pq)),
        "mean_read_s": round(statistics.mean(read_times_pq), 4),
        "read_throughput_rec_sec": round(num_rows / statistics.mean(read_times_pq)),
        "mean_projected_read_s": round(statistics.mean(proj_times_pq), 4),
        "projected_throughput_rec_sec": round(num_rows / statistics.mean(proj_times_pq))
    }

    # -------------------------------------------------------------
    # AVRO BENCHMARK
    # -------------------------------------------------------------
    print("[2/3] Benchmarking Apache Avro (Snappy)...")
    avro_path = test_files["Avro"]

    # Warmup
    with open(avro_path, "wb") as f:
        fastavro.writer(f, avro_schema, avro_records, codec="snappy")
    with open(avro_path, "rb") as f:
        _ = list(fastavro.reader(f))

    # Write iterations
    write_times_av = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        with open(avro_path, "wb") as f:
            fastavro.writer(f, avro_schema, avro_records, codec="snappy")
        write_times_av.append(time.perf_counter() - t0)

    # Full Read iterations
    read_times_av = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        with open(avro_path, "rb") as f:
            _ = list(fastavro.reader(f))
        read_times_av.append(time.perf_counter() - t0)

    size_av = os.path.getsize(avro_path)
    metrics["Avro"] = {
        "file_size_bytes": size_av,
        "file_size_mb": round(size_av / (1024 * 1024), 2),
        "compression_ratio": round(in_memory_bytes / size_av, 2),
        "mean_write_s": round(statistics.mean(write_times_av), 4),
        "write_throughput_rec_sec": round(num_rows / statistics.mean(write_times_av)),
        "mean_read_s": round(statistics.mean(read_times_av), 4),
        "read_throughput_rec_sec": round(num_rows / statistics.mean(read_times_av)),
        "mean_projected_read_s": "N/A (Row-Scan)",
        "projected_throughput_rec_sec": "N/A"
    }

    # -------------------------------------------------------------
    # ORC BENCHMARK
    # -------------------------------------------------------------
    print("[3/3] Benchmarking Apache ORC (Snappy)...")
    orc_path = test_files["ORC"]

    # Warmup
    orc.write_table(baseline_table, orc_path, compression="snappy")
    _ = orc.read_table(orc_path)

    # Write iterations
    write_times_orc = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        orc.write_table(baseline_table, orc_path, compression="snappy")
        write_times_orc.append(time.perf_counter() - t0)

    # Full Read iterations
    read_times_orc = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = orc.read_table(orc_path)
        read_times_orc.append(time.perf_counter() - t0)

    # Projected Read (3 columns)
    proj_times_orc = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = orc.read_table(orc_path, columns=["order_id", "order_amount", "payment_method"])
        proj_times_orc.append(time.perf_counter() - t0)

    size_orc = os.path.getsize(orc_path)
    metrics["ORC"] = {
        "file_size_bytes": size_orc,
        "file_size_mb": round(size_orc / (1024 * 1024), 2),
        "compression_ratio": round(in_memory_bytes / size_orc, 2),
        "mean_write_s": round(statistics.mean(write_times_orc), 4),
        "write_throughput_rec_sec": round(num_rows / statistics.mean(write_times_orc)),
        "mean_read_s": round(statistics.mean(read_times_orc), 4),
        "read_throughput_rec_sec": round(num_rows / statistics.mean(read_times_orc)),
        "mean_projected_read_s": round(statistics.mean(proj_times_orc), 4),
        "projected_throughput_rec_sec": round(num_rows / statistics.mean(proj_times_orc))
    }

    # -------------------------------------------------------------
    # BUILD REPORT TABLE
    # -------------------------------------------------------------
    table_data = [
        ["File Size (MB)", f"{metrics['Parquet']['file_size_mb']} MB", f"{metrics['Avro']['file_size_mb']} MB", f"{metrics['ORC']['file_size_mb']} MB"],
        ["File Size (Bytes)", f"{metrics['Parquet']['file_size_bytes']:,}", f"{metrics['Avro']['file_size_bytes']:,}", f"{metrics['ORC']['file_size_bytes']:,}"],
        ["Compression Ratio vs RAM", f"{metrics['Parquet']['compression_ratio']}x", f"{metrics['Avro']['compression_ratio']}x", f"{metrics['ORC']['compression_ratio']}x"],
        ["Write Time (Mean Sec)", f"{metrics['Parquet']['mean_write_s']}s", f"{metrics['Avro']['mean_write_s']}s", f"{metrics['ORC']['mean_write_s']}s"],
        ["Write Speed (Rec/sec)", f"{metrics['Parquet']['write_throughput_rec_sec']:,}", f"{metrics['Avro']['write_throughput_rec_sec']:,}", f"{metrics['ORC']['write_throughput_rec_sec']:,}"],
        ["Full Read Time (Mean Sec)", f"{metrics['Parquet']['mean_read_s']}s", f"{metrics['Avro']['mean_read_s']}s", f"{metrics['ORC']['mean_read_s']}s"],
        ["Full Read Speed (Rec/sec)", f"{metrics['Parquet']['read_throughput_rec_sec']:,}", f"{metrics['Avro']['read_throughput_rec_sec']:,}", f"{metrics['ORC']['read_throughput_rec_sec']:,}"],
        ["Projected Read (3 cols)", f"{metrics['Parquet']['mean_projected_read_s']}s", "N/A", f"{metrics['ORC']['mean_projected_read_s']}s"],
    ]

    headers = ["Metric", "Apache Parquet", "Apache Avro", "Apache ORC"]
    summary_table_str = tabulate(table_data, headers=headers, tablefmt="github")

    print("\n" + summary_table_str + "\n")

    # Save to JSON
    json_output_path = results_dir / "benchmark_report.json"
    full_report = {
        "dataset_records": num_rows,
        "in_memory_mb": round(in_memory_mb, 2),
        "iterations": iterations,
        "compression_codec": "snappy",
        "results": metrics
    }
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    print(f"Report saved to {json_output_path.relative_to(PROJECT_ROOT)}")

if __name__ == "__main__":
    run_benchmarks(iterations=5)
