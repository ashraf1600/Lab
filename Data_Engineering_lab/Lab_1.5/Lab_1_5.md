# File Format Comparison (Parquet, Avro, ORC)

## 1. Introduction

Imagine you are a data engineer at **QuickCart**, a fast-growing online food delivery platform, and you are modernizing the storage layer for millions of daily order transactions. Raw JSON and CSV files have inflated storage costs and slowed down analytical queries.

Your task is to build a benchmark that compares **Apache Parquet**, **Apache Avro**, and **Apache ORC** on the same 100,000-order dataset, measuring file size, read/write speed, and schema support.

You will build the following QuickCart file format benchmark:

![Benchmark Architecture](images/Lab_1.5.drawio.svg)

The pipeline synthesizes 100,000 realistic QuickCart orders governed by strict canonical schemas. It encodes the records into Parquet, Avro, and ORC, validates record counts and value parity, runs timed multi-iteration read/write benchmarks, and outputs a structured comparative report.

---

## 2. Objectives

By the end of this lab, you will be able to:

- Write the same dataset as Parquet, Avro, and ORC from one shared schema.
- Verify that all three files hold identical records.
- Benchmark file size, write speed, full-read speed, and column projection.
- Choose the right format for streaming, data lake, and Hive/Trino workloads.

---

## 3. Project File Structure

The project uses the following structure:

```text
file-format-comparison-lab/
├── data/                       # Storage for Parquet, Avro, and ORC files
├── schemas/                    # Schema contracts
│   ├── order_schema.avsc       # Avro JSON schema
│   └── order_schema.py         # PyArrow schema
├── src/                        # Benchmark scripts
│   ├── generate_data.py        # Order data generator
│   ├── convert_parquet.py      # Parquet writer and reader
│   ├── convert_avro.py         # Avro writer and reader
│   ├── convert_orc.py          # ORC writer and reader
│   ├── validate_integrity.py   # Parity and validation script
│   └── benchmark.py            # Benchmark suite
├── results/                    # Benchmark results directory
│   └── benchmark_report.json   # Benchmark measurements
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 4. Project Implementation

### Step 1: Set Up the Project and Environment

Initialize the lab workspace in VS Code Server, create the modular project folder hierarchy, establish an isolated Python virtual environment, and install all required big data serialization libraries.

1. Open your browser and access your **VS Code Server** environment.
2. In the top menu bar, select **File > Open Folder...**, navigate to or create the project directory:
   ```text
   file-format-comparison-lab
   ```
3. In the VS Code Explorer sidebar (left panel), verify or create the project subdirectories by clicking the **New Folder** icon:
   - `data`
   - `schemas`
   - `src`
   - `results`
4. Open an integrated terminal by clicking **Terminal > New Terminal**.
5. Create an isolated Python virtual environment named `.venv`:
   ```bash
   python3 -m venv .venv
   ```
6. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
   *(On Windows PowerShell, run: `.venv\Scripts\Activate.ps1`)*
7. In the root of `file-format-comparison-lab/`, click the **New File** icon and create:
   ```text
   requirements.txt
   ```
8. Open `requirements.txt` in the editor and add the required data format libraries:
   ```text
   pandas>=2.0.0
   numpy>=1.24.0
   pyarrow>=14.0.0
   fastavro>=1.8.0
   tabulate>=0.9.0
   cramjam>=2.0.0
   tzdata>=2024.1
   ```
9. Save the file (**File > Save**) and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

![Project Structure and Environment](images/step-01-environment.png)

The workspace shows the `.venv` folder next to `file-format-comparison-lab`, and `requirements.txt` lists the libraries for Parquet, Avro, and ORC (`pyarrow`, `fastavro`), Snappy compression for Avro (`cramjam`), and the time zone data that the ORC writer needs (`tzdata`). The `(.venv)` prefix in the terminal confirms the virtual environment is active.

---

### Step 2: Define the Schemas and Generate the Dataset

Establish unambiguous schema contracts across row-oriented and columnar formats, then synthesize 100,000 realistic QuickCart order transactions to serve as the unified benchmark baseline.

1. In the VS Code Explorer, expand the `schemas` folder.
2. Create a new file named `order_schema.avsc` and populate it with the Apache Avro schema definition:
   ```json
   {
     "type": "record",
     "name": "QuickCartOrder",
     "namespace": "com.quickcart.orders",
     "doc": "Canonical data contract for QuickCart order delivery lifecycle events",
     "fields": [
       {"name": "order_id", "type": "string", "doc": "Unique alphanumeric order identifier"},
       {"name": "customer_id", "type": "string", "doc": "Unique customer account identifier"},
       {"name": "order_timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}, "doc": "Order creation epoch timestamp in milliseconds"},
       {"name": "item_count", "type": "int", "doc": "Number of menu items ordered"},
       {"name": "order_amount", "type": "double", "doc": "Total transaction order amount in BDT"},
       {"name": "delivery_distance_km", "type": "double", "doc": "Transit distance from restaurant to customer in kilometers"},
       {"name": "payment_method", "type": "string", "doc": "Payment channel used"},
       {"name": "is_cancelled", "type": "boolean", "doc": "Flag indicating if order was cancelled"}
     ]
   }
   ```
3. Create a second file in `schemas/` named `order_schema.py` to mirror the schema precisely for PyArrow:
   ```python
   import pyarrow as pa

   ORDER_PYARROW_SCHEMA = pa.schema([
       pa.field("order_id", pa.string(), nullable=False),
       pa.field("customer_id", pa.string(), nullable=False),
       pa.field("order_timestamp", pa.timestamp("ms"), nullable=False),
       pa.field("item_count", pa.int32(), nullable=False),
       pa.field("order_amount", pa.float64(), nullable=False),
       pa.field("delivery_distance_km", pa.float64(), nullable=False),
       pa.field("payment_method", pa.string(), nullable=False),
       pa.field("is_cancelled", pa.bool_(), nullable=False),
   ])
   ```
4. In the `src/` directory, create `generate_data.py` and populate it with the synthetic data generator:
   ```python
   import os
   import sys
   from pathlib import Path
   import numpy as np
   import pyarrow as pa
   import pyarrow.parquet as pq

   # Set up project path
   PROJECT_ROOT = Path(__file__).resolve().parent.parent
   sys.path.insert(0, str(PROJECT_ROOT))

   from schemas.order_schema import ORDER_PYARROW_SCHEMA

   def generate_orders(num_records: int = 100000, seed: int = 42) -> pa.Table:
       np.random.seed(seed)
       print(f"Generating {num_records:,} synthetic QuickCart order records...")

       order_ids = [f"ORD-{i:07d}" for i in range(1, num_records + 1)]
       customer_ids = [f"CUST-{np.random.randint(1, 20000):05d}" for _ in range(num_records)]

       # Timestamps spanning last 30 days
       base_epoch_ms = 1717200000000  # 2024-06-01 UTC
       random_offsets = np.random.randint(0, 30 * 24 * 3600 * 1000, size=num_records, dtype=np.int64)
       order_timestamps = base_epoch_ms + random_offsets

       item_counts = np.random.randint(1, 15, size=num_records, dtype=np.int32)
       order_amounts = np.round(np.random.uniform(50.0, 3500.0, size=num_records), 2)
       delivery_distances = np.round(np.random.uniform(0.5, 25.0, size=num_records), 2)

       payment_channels = np.array(["credit_card", "bKash", "cash_on_delivery", "nagad", "debit_card"])
       payment_probs = [0.25, 0.40, 0.20, 0.10, 0.05]
       payment_methods = np.random.choice(payment_channels, size=num_records, p=payment_probs)

       is_cancelled = np.random.choice([False, True], size=num_records, p=[0.95, 0.05])

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

       return pa.Table.from_arrays(arrays, schema=ORDER_PYARROW_SCHEMA)

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
       print(f" - Baseline File:     {output_path.name}")
       print(f" - File Size:         {file_size_mb:.2f} MB")
       print(f" - In-Memory Size:    {table.nbytes / (1024 * 1024):.2f} MB")

   if __name__ == "__main__":
       main()
   ```
5. In the VS Code terminal, execute the dataset generator:
   ```bash
   python src/generate_data.py
   ```
6. Verify in the terminal that 100,000 records are generated and the baseline file `orders_raw.parquet` is created under `data/`.

![Schema Definition and Dataset Generation](images/step-02-dataset-schema.png)

The editor shows the Avro schema `order_schema.avsc` with types for IDs, timestamps, amounts, and flags. The terminal confirms that `generate_data.py` created 100,000 records with 8 columns in `data/orders_raw.parquet` (2.53 MB on disk, 6.68 MB in memory). Every converter reads this one baseline file, so all three formats start from identical data.

---

### Step 3: Write and Read Apache Parquet

Implement the Apache Parquet converter and reader to evaluate columnar data layout, write performance with Snappy compression, full-table scanning speed, and selective column projection.

1. In the VS Code Explorer, expand the `src` folder.
2. Click the **New File** icon and create:
   ```text
   convert_parquet.py
   ```
3. Open `convert_parquet.py` in the editor and implement the Parquet serialization and reading logic:
   ```python
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
       print(f"[Parquet] Reading baseline data from {input_raw_path.name}...")
       table = pq.read_table(input_raw_path, schema=ORDER_PYARROW_SCHEMA)
       
       print(f"[Parquet] Serializing {table.num_rows:,} records to {output_parquet_path.name} (compression={compression})...")
       start_time = time.perf_counter()
       pq.write_table(table, output_parquet_path, compression=compression)
       write_duration = time.perf_counter() - start_time
       
       file_size_bytes = os.path.getsize(output_parquet_path)
       return {
           "format": "Parquet",
           "num_rows": table.num_rows,
           "write_seconds": write_duration,
           "write_throughput_rec_sec": table.num_rows / write_duration,
           "file_size_mb": file_size_bytes / (1024 * 1024),
           "file_size_bytes": file_size_bytes
       }

   def read_parquet(parquet_path: Path, columns: list = None) -> dict:
       col_msg = f"columns={columns}" if columns else "full scan (all columns)"
       print(f"[Parquet] Deserializing from {parquet_path.name} ({col_msg})...")
       
       start_time = time.perf_counter()
       table = pq.read_table(parquet_path, columns=columns)
       read_duration = time.perf_counter() - start_time
       
       return {
           "format": "Parquet",
           "num_rows": table.num_rows,
           "columns_read": len(table.column_names),
           "read_seconds": read_duration,
           "read_throughput_rec_sec": table.num_rows / read_duration
       }

   def main():
       raw_path = PROJECT_ROOT / "data" / "orders_raw.parquet"
       out_path = PROJECT_ROOT / "data" / "orders.parquet"
       
       write_res = write_parquet(raw_path, out_path, compression="snappy")
       print(f" -> Write Time:       {write_res['write_seconds']:.4f} s ({write_res['write_throughput_rec_sec']:,.0f} records/s)")
       print(f" -> File Size:        {write_res['file_size_mb']:.2f} MB ({write_res['file_size_bytes']:,} bytes)")
       
       read_res = read_parquet(out_path)
       print(f" -> Full Read Time:   {read_res['read_seconds']:.4f} s ({read_res['read_throughput_rec_sec']:,.0f} records/s)")
       
       proj_res = read_parquet(out_path, columns=["order_id", "order_amount", "payment_method"])
       print(f" -> Projected Read:   {proj_res['read_seconds']:.4f} s ({proj_res['columns_read']} columns)")

   if __name__ == "__main__":
       main()
   ```
4. Save the file (**File > Save**).
5. In the integrated terminal, execute the Parquet converter:
   ```bash
   python src/convert_parquet.py
   ```
6. Check the terminal output: the write speed, the file size of about 2.53 MB, and how reading only 3 columns is faster than a full scan.

![Parquet Serialization and Projection](images/step-03-parquet-write.png)

Writing 100,000 orders to Parquet took 0.1269 s (787,787 records/s) and produced a 2.53 MB file. A full read took 0.0346 s (2,888,871 records/s), while reading only `order_id`, `order_amount`, and `payment_method` took 0.0185 s. Parquet skips the column chunks that are not requested, which is its main advantage for analytical queries.

---

### Step 4: Write and Read Apache Avro

Implement the Apache Avro serializer and deserializer using `fastavro` and `cramjam` to benchmark row-oriented streaming ingestion, schema-embedded data storage, and sequential row deserialization.

1. In the VS Code Explorer, click the **New File** icon inside `src/` and create:
   ```text
   convert_avro.py
   ```
2. Open `src/convert_avro.py` and implement the complete Avro conversion script:
   ```python
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
       with open(schema_path, "r", encoding="utf-8") as f:
           schema_dict = json.load(f)
       return fastavro.schema.parse_schema(schema_dict)

   def write_avro(input_raw_path: Path, output_avro_path: Path, schema_path: Path, codec: str = "snappy") -> dict:
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
       return {
           "format": "Avro",
           "file_path": str(output_avro_path),
           "codec": codec,
           "num_rows": num_rows,
           "write_seconds": write_duration,
           "write_throughput_rec_sec": num_rows / write_duration,
           "file_size_bytes": file_size_bytes,
           "file_size_mb": file_size_bytes / (1024 * 1024)
       }

   def read_avro(avro_path: Path) -> dict:
       print(f"[Avro] Deserializing from {avro_path.name} (full row scan)...")
       
       start_time = time.perf_counter()
       with open(avro_path, "rb") as f:
           reader = fastavro.reader(f)
           records = [rec for rec in reader]
       read_duration = time.perf_counter() - start_time
       
       num_rows = len(records)
       return {
           "format": "Avro",
           "num_rows": num_rows,
           "read_seconds": read_duration,
           "read_throughput_rec_sec": num_rows / read_duration
       }

   def main():
       raw_path = PROJECT_ROOT / "data" / "orders_raw.parquet"
       avro_schema_path = PROJECT_ROOT / "schemas" / "order_schema.avsc"
       out_path = PROJECT_ROOT / "data" / "orders.avro"
       
       write_res = write_avro(raw_path, out_path, avro_schema_path, codec="snappy")
       print(f" -> Write Time:       {write_res['write_seconds']:.4f} s ({write_res['write_throughput_rec_sec']:,.0f} records/s)")
       print(f" -> File Size:        {write_res['file_size_mb']:.2f} MB ({write_res['file_size_bytes']:,} bytes)")
       
       read_res = read_avro(out_path)
       print(f" -> Full Read Time:   {read_res['read_seconds']:.4f} s ({read_res['read_throughput_rec_sec']:,.0f} records/s)")

   if __name__ == "__main__":
       main()
   ```
3. Save the file (**File > Save**).
4. In the VS Code terminal, execute the Avro converter:
   ```bash
   python src/convert_avro.py
   ```
5. Check that 100,000 records are written to `data/orders.avro` (about 2.80 MB) and read back. Avro is read row by row, so every record is decoded in sequence.

![Avro Serialization and Deserialization](images/step-04-avro-write.png)

Writing 100,000 orders to Avro with Snappy took 0.9709 s (103,002 records/s) and produced a 2.80 MB file. Reading it back took 0.8279 s (120,792 records/s), because each row is turned into a Python dictionary one at a time. That cost is small for single messages, which is why Avro suits Kafka and RPC payloads, while batch analytics favors columnar formats.

---

### Step 5: Write and Read Apache ORC

Implement the Apache ORC converter and reader using PyArrow's native ORC engine to evaluate columnar stripe layout, metadata indexing, write speed, and selective column projection.

1. In the VS Code Explorer, click the **New File** icon inside `src/` and create:
   ```text
   convert_orc.py
   ```
2. Open `src/convert_orc.py` and implement the complete ORC conversion script:
   ```python
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
       print(f"[ORC] Reading baseline data from {input_raw_path.name}...")
       table = pq.read_table(input_raw_path, schema=ORDER_PYARROW_SCHEMA)
       
       print(f"[ORC] Serializing {table.num_rows:,} records to {output_orc_path.name} (compression={compression})...")
       start_time = time.perf_counter()
       orc.write_table(table, output_orc_path, compression=compression)
       write_duration = time.perf_counter() - start_time
       
       file_size_bytes = os.path.getsize(output_orc_path)
       return {
           "format": "ORC",
           "file_path": str(output_orc_path),
           "compression": compression,
           "num_rows": table.num_rows,
           "write_seconds": write_duration,
           "write_throughput_rec_sec": table.num_rows / write_duration,
           "file_size_bytes": file_size_bytes,
           "file_size_mb": file_size_bytes / (1024 * 1024)
       }

   def read_orc(orc_path: Path, columns: list = None) -> dict:
       col_msg = f"columns={columns}" if columns else "full scan (all columns)"
       print(f"[ORC] Deserializing from {orc_path.name} ({col_msg})...")
       
       start_time = time.perf_counter()
       table = orc.read_table(orc_path, columns=columns)
       read_duration = time.perf_counter() - start_time
       
       return {
           "format": "ORC",
           "num_rows": table.num_rows,
           "columns_read": len(table.column_names),
           "read_seconds": read_duration,
           "read_throughput_rec_sec": table.num_rows / read_duration
       }

   def main():
       raw_path = PROJECT_ROOT / "data" / "orders_raw.parquet"
       out_path = PROJECT_ROOT / "data" / "orders.orc"
       
       write_res = write_orc(raw_path, out_path, compression="snappy")
       print(f" -> Write Time:       {write_res['write_seconds']:.4f} s ({write_res['write_throughput_rec_sec']:,.0f} records/s)")
       print(f" -> File Size:        {write_res['file_size_mb']:.2f} MB ({write_res['file_size_bytes']:,} bytes)")
       
       read_res = read_orc(out_path)
       print(f" -> Full Read Time:   {read_res['read_seconds']:.4f} s ({read_res['read_throughput_rec_sec']:,.0f} records/s)")
       
       proj_res = read_orc(out_path, columns=["order_id", "order_amount", "payment_method"])
       print(f" -> Projected Read:   {proj_res['read_seconds']:.4f} s ({proj_res['columns_read']} columns)")

   if __name__ == "__main__":
       main()
   ```
3. Save the file (**File > Save**).
4. In the VS Code terminal, execute the ORC converter:
   ```bash
   python src/convert_orc.py
   ```
5. Check that 100,000 records are written to `data/orders.orc` (about 2.68 MB), and compare the write time and the 3-column read time with Parquet.

![ORC Serialization and Column Projection](images/step-05-orc-write.png)

`convert_orc.py` uses PyArrow's ORC writer and sets `TZDIR` so it can find time zone data. Writing 100,000 orders took 0.1051 s (951,129 records/s) and produced a 2.68 MB file. A full read took 0.0526 s (1,902,721 records/s), and reading 3 columns took 0.0155 s. Like Parquet, ORC stores data by column, so column projection is close to Parquet's speed.

---

### Step 6: Validate Data Integrity Across Formats

Before benchmarking, confirm that the three files hold the same data: the same record count (100,000), the same columns, and the same total order amount.

1. In the VS Code Explorer, click the **New File** icon inside `src/` and create:
   ```text
   validate_integrity.py
   ```
2. Open `src/validate_integrity.py` and implement the complete validation suite:
   ```python
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
   ```
3. Save the file (**File > Save**).
4. In the VS Code terminal, execute the validation script:
   ```bash
   python src/validate_integrity.py
   ```
5. Check that all three formats match and the script prints `[PASS] INTEGRITY CONFIRMED`.

![Integrity and Parity Verification](images/step-06-validation.png)

All three files hold 100,000 records, 8 columns, and the same total order amount of 177,532,403.85 BDT. Because the data is identical, any difference in the benchmark comes from the file format itself, not from lost or changed data.

---

### Step 7: Run the Benchmark Suite

Run each operation once as a warm-up and then 5 timed times, and report the mean write time, full read time, 3-column read time, file size, and compression ratio.

1. In the VS Code Explorer, click the **New File** icon inside `src/` and create:
   ```text
   benchmark.py
   ```
2. Open `src/benchmark.py` and implement the complete benchmarking script:
   ```python
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

       # Load baseline memory table
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

       # 1. PARQUET BENCHMARK
       print("[1/3] Benchmarking Apache Parquet (Snappy)...")
       pq_path = test_files["Parquet"]
       
       pq.write_table(baseline_table, pq_path, compression="snappy")
       _ = pq.read_table(pq_path)

       write_times_pq = []
       for _ in range(iterations):
           t0 = time.perf_counter()
           pq.write_table(baseline_table, pq_path, compression="snappy")
           write_times_pq.append(time.perf_counter() - t0)

       read_times_pq = []
       for _ in range(iterations):
           t0 = time.perf_counter()
           _ = pq.read_table(pq_path)
           read_times_pq.append(time.perf_counter() - t0)

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

       # 2. AVRO BENCHMARK
       print("[2/3] Benchmarking Apache Avro (Snappy)...")
       avro_path = test_files["Avro"]

       with open(avro_path, "wb") as f:
           fastavro.writer(f, avro_schema, avro_records, codec="snappy")
       with open(avro_path, "rb") as f:
           _ = list(fastavro.reader(f))

       write_times_av = []
       for _ in range(iterations):
           t0 = time.perf_counter()
           with open(avro_path, "wb") as f:
               fastavro.writer(f, avro_schema, avro_records, codec="snappy")
           write_times_av.append(time.perf_counter() - t0)

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

       # 3. ORC BENCHMARK
       print("[3/3] Benchmarking Apache ORC (Snappy)...")
       orc_path = test_files["ORC"]

       orc.write_table(baseline_table, orc_path, compression="snappy")
       _ = orc.read_table(orc_path)

       write_times_orc = []
       for _ in range(iterations):
           t0 = time.perf_counter()
           orc.write_table(baseline_table, orc_path, compression="snappy")
           write_times_orc.append(time.perf_counter() - t0)

       read_times_orc = []
       for _ in range(iterations):
           t0 = time.perf_counter()
           _ = orc.read_table(orc_path)
           read_times_orc.append(time.perf_counter() - t0)

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

       # Build Summary Table
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
       print("\n" + tabulate(table_data, headers=headers, tablefmt="github") + "\n")

       # Export JSON
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
   ```
3. Save the file (**File > Save**).
4. In the VS Code terminal, execute the benchmark suite:
   ```bash
   python src/benchmark.py
   ```
5. Inspect the generated comparison table and the exported file `results/benchmark_report.json`.

![Benchmark Results](images/step-07-benchmark-results.png)

Parquet has the fastest full read (5,333,476 records/s) and the smallest file (2.53 MB, 2.64x smaller than in memory). ORC has the fastest write (910,149 records/s) with a 2.68 MB file. Avro writes 98,667 records/s and reads 107,991 records/s with a 2.80 MB file, because every row is decoded one by one. The script also saves these numbers to `results/benchmark_report.json`.

---

## 5. Results

All metrics below are the mean of 5 isolated execution iterations on the 100,000 QuickCart order dataset (6.68 MB in-memory baseline) using Snappy compression across all three formats:

| Benchmark Metric | Apache Parquet | Apache Avro | Apache ORC | Architectural Winner |
| :--- | :--- | :--- | :--- | :--- |
| **Disk File Size (MB)** | **2.53 MB** | 2.80 MB | 2.68 MB | **Apache Parquet** (5.5% smaller than ORC, 9.4% smaller than Avro) |
| **Raw File Size (Bytes)** | **2,656,602** | 2,933,577 | 2,811,133 | **Apache Parquet** |
| **Compression Ratio vs RAM** | **2.64x** | 2.39x | 2.49x | **Apache Parquet** |
| **Mean Write Latency (Sec)** | 0.1151s | 1.0135s | **0.1099s** | **Apache ORC** (Fastest columnar writer) |
| **Write Throughput (Rec/sec)** | 868,519 | 98,667 | **910,149** | **Apache ORC** |
| **Full Read Latency (Sec)** | **0.0187s** | 0.9260s | 0.0349s | **Apache Parquet** (1.8x faster than ORC, 49x faster than Avro) |
| **Full Read Throughput (Rec/sec)**| **5,333,476** | 107,991 | 2,865,364 | **Apache Parquet** |
| **Projected Read (3 Columns)** | 0.0159s | *N/A (Row scan)* | **0.0153s** | **Apache ORC & Parquet** (Near parity, ~15ms) |
| **Projected Throughput (Rec/sec)**| 6,293,623 | *N/A* | **6,553,303** | **Apache ORC** |

---

## 6. Interpretation and Decision Matrix

### Columnar vs. Row-Oriented Layout
- **Parquet & ORC (Columnar):** Store data by column chunks (Parquet Row Groups and ORC Stripes). Because consecutive values in a column share the same data type and often repeat, columnar formats apply run-length encoding (RLE), dictionary encoding, and bit-packing before compression. This explains why Parquet compressed 6.68 MB of in-memory transactional records down to **2.53 MB** (2.64x compression).
- **Avro (Row-Oriented):** Encodes records sequentially as binary structures. Each row's fields are laid out contiguously. While Avro is a compact binary format compared with JSON or CSV, it cannot achieve Parquet's compression density because heterogeneous data types adjacent in memory compress less efficiently than homogeneous column values.

### Query Speed and Column Pruning
- When QuickCart's BI dashboards calculate metrics like *total gross merchandise value (GMV)* by aggregating `order_amount`, Parquet and ORC perform **column projection (pruning)**. The storage engine reads only the byte offsets for `order_amount`, bypassing all customer IDs, timestamps, and delivery distances entirely.
- In our empirical tests, reading 3 out of 8 columns dropped execution time to **0.015s**, sustaining over **6.5 million records/second**. In contrast, Avro must read and deserialize every preceding field of every single row from disk, achieving 107,991 records/second.

### Schema Governance and Evolution
- **Avro:** The gold standard for real-time event streaming architectures (Kafka, Redpanda). Avro schemas are defined in pure JSON contracts (`.avsc`), support centralized Schema Registries, and offer robust backward, forward, and full compatibility modes where new fields with defaults never break existing consumers.
- **Parquet & ORC:** Embed schema metadata directly inside file footers and postscripts. They allow schema evolution during downstream batch reads (e.g., Spark schema merging), but lack real-time schema registry validation for fine-grained per-event messaging.

### QuickCart Architectural Decision Matrix

| Workload Dimension | Recommended Format | Architectural Justification |
| :--- | :--- | :--- |
| **Real-time Order Ingestion (Kafka Streaming)** | **Apache Avro** | Compact serialization overhead, row-level immutability, zero-overhead single-event deserialization, strict Schema Registry governance. |
| **Data Lake Storage & Cloud Analytics (Athena/Snowflake/BigQuery)** | **Apache Parquet** | Superior columnar compression (2.53 MB), 5.3M rec/s vectorization speed, universal engine compatibility across modern cloud lakes. |
| **Enterprise Hive / Trino ACID Workloads** | **Apache ORC** | Lightweight stripe indexes, highest write throughput (910K rec/s), native support for ACID merge operations in Trino and Hive. |

---

## 7. Troubleshooting

### `ValueError: snappy codec is supported but you need to install cramjam`
- **Cause:** `fastavro` delegates Snappy compression to external decompression libraries.
- **Solution:** Add `cramjam>=2.0.0` to `requirements.txt`. Cramjam provides precompiled wheels across Windows and Linux without C++ toolchain prerequisites.

### `pyarrow.lib.ArrowException: Time zone file /usr/share/zoneinfo/GMT does not exist`
- **Cause:** PyArrow's underlying C++ ORC engine looks for IANA timezone files on disk when serializing timestamp columns. On Windows, `/usr/share/zoneinfo` does not exist by default.
- **Solution:** Install Python's standard `tzdata` package and export the environment path before invoking ORC:
  ```python
  import tzdata
  os.environ["TZDIR"] = str(Path(tzdata.__file__).parent / "zoneinfo")
  ```

### Skewed Results from Different Compression Codecs
- **Cause:** Comparing Parquet with Snappy against Avro with uncompressed (`null`) or ORC with Zlib skews file size and throughput in favor of the codec rather than the format architecture.
- **Solution:** Standardize on `snappy` across Parquet, Avro, and ORC to isolate file structure performance from compression algorithm discrepancies.

---

## 8. Conclusion

Evaluating 100,000 QuickCart orders confirms that file formats serve distinct architectural needs. Apache Parquet provides optimal analytical performance, delivering the highest compression (2.53 MB) and scan speeds exceeding 5.3 million records/sec. Apache Avro excels for upstream streaming ingestion through strict schema governance and row-level serialization. Apache ORC offers high-throughput batch writes exceeding 910,000 records/sec with fast column pruning. QuickCart adopts a hybrid architecture: streaming raw events in Avro and compacting analytical partitions into Parquet.

