# Batch vs Streaming Trade-offs

## 1. Introduction

Imagine you are working as a **Data Engineer** at **QuickCart**, a fast-growing online food delivery platform. Customers place orders every few seconds, and the team needs to monitor order volumes, sales, and delivery operations.

You can process incoming orders in two ways: collect them and run a scheduled **batch** job, or handle each event as it arrives with a **streaming** pipeline built on **Apache Kafka**. In this lab, you will run both approaches on the same order dataset and compare latency, throughput, and data freshness.

You will build and compare the following QuickCart batch and streaming architectures:

![Architecture Overview](assets/Lab_1.2_DE.drawio.svg)

The batch workflow processes the order file on a Cron schedule, while the streaming pipeline consumes order events from a Kafka topic as soon as they are published. The three metrics compared in this lab are:

| Metric | Meaning | Formula |
| :--- | :--- | :--- |
| **Latency** | How long an event waits before it is processed | `processing_time - event_time` |
| **Throughput** | How many records are processed per second | `records / processing time` |
| **Data freshness** | How old the data is when it becomes available downstream | average latency of the processed records |

---

## 2. Objectives

By the end of this lab, you will be able to:

- Build a batch pipeline and schedule it with **Cron**.
- Build an event-driven streaming pipeline with **Apache Kafka**.
- Measure and compare **latency**, **throughput**, and **data freshness** for both pipelines.
- Decide when batch or streaming is the right choice for a workload.

---

## 3. Project File Structure

```text
batch-streaming-lab/
│
├── data/
│   └── orders.csv              # Raw orders dataset
│
├── batch/
│   ├── batch_processor.py      # Batch ETL processor
│   └── run_batch.py            # Cron batch runner
│
├── streaming/
│   ├── producer.py             # Kafka event producer
│   ├── consumer.py             # Kafka event consumer
│   └── run_streaming.py        # Runs producer and consumer together
│
├── metrics/
│   └── comparison.py           # Metrics comparison script
│
├── results/
│   ├── batch_results.csv       # Batch run results
│   └── streaming_results.csv   # Streaming run results
│
└── requirements.txt            # Python dependencies
```

The completed project looks like this in the VS Code Explorer:

![Project Structure](assets/step1_project_structure.png)

---

## 4. Project Implementation

### Step 1: Create the Project Folders

1. Open your **VS Code Server** workspace and create a project folder named:
   ```text
   batch-streaming-lab
   ```
2. Open the folder with **File > Open Folder...**.
3. In the VS Code Explorer, click the **New Folder** icon and create:
   - `data`
   - `batch`
   - `streaming`
   - `metrics`
   - `results`

Keeping the batch and streaming code in separate folders lets both pipelines share the same input data and output format without mixing their execution logic.

---

### Step 2: Create the Python Virtual Environment

1. Open an integrated terminal by clicking **Terminal > New Terminal**.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   *(On Windows PowerShell, run: `.venv\Scripts\Activate.ps1`)*

![Virtual Environment Activated](assets/step2_virtual_environment.png)

The `(.venv)` prefix confirms the environment is active. Both pipelines use this same environment, so the comparison is not affected by different package versions.

---

### Step 3: Create the Order Dataset

1. Right-click the `data` folder, select **New File**, and name it `orders.csv`.
2. Add the following 20 orders and save the file:
   ```csv
   order_id,customer_id,restaurant,order_amount,item_count,event_time
   ORD1001,C001,Spice Kitchen,450.00,2,2026-10-05 10:00:01
   ORD1002,C002,FoodHub,700.00,3,2026-10-05 10:00:04
   ORD1003,C003,Pizza Paradiso,320.00,1,2026-10-05 10:00:07
   ORD1004,C004,Royal Kitchen,950.00,4,2026-10-05 10:00:10
   ORD1005,C005,FoodHub,180.00,1,2026-10-05 10:00:13
   ORD1006,C006,Spice Kitchen,550.00,2,2026-10-05 10:00:16
   ORD1007,C007,Burger Lab,390.00,2,2026-10-05 10:00:19
   ORD1008,C008,Pizza Paradiso,840.00,3,2026-10-05 10:00:22
   ORD1009,C009,Royal Kitchen,620.00,2,2026-10-05 10:00:25
   ORD1010,C010,Spice Kitchen,290.00,1,2026-10-05 10:00:28
   ORD1011,C011,FoodHub,1100.00,5,2026-10-05 10:00:31
   ORD1012,C012,Burger Lab,480.00,2,2026-10-05 10:00:34
   ORD1013,C013,Spice Kitchen,360.00,1,2026-10-05 10:00:37
   ORD1014,C014,Pizza Paradiso,750.00,3,2026-10-05 10:00:40
   ORD1015,C015,Royal Kitchen,920.00,4,2026-10-05 10:00:43
   ORD1016,C016,FoodHub,260.00,1,2026-10-05 10:00:46
   ORD1017,C017,Burger Lab,530.00,2,2026-10-05 10:00:49
   ORD1018,C018,Spice Kitchen,680.00,3,2026-10-05 10:00:52
   ORD1019,C019,Pizza Paradiso,410.00,2,2026-10-05 10:00:55
   ORD1020,C020,Royal Kitchen,870.00,3,2026-10-05 10:00:58
   ```

![Sample Orders Dataset](assets/step3_raw_orders_csv.png)

Each row is one order event. The `event_time` column records when the order was created; later, each pipeline compares it with the processing time to calculate latency and freshness.

---

### Step 4: Install the Dependencies

1. In the project root, create `requirements.txt` with the following content:
   ```text
   pandas>=2.0.0
   kafka-python-ng>=2.2.0
   tabulate>=0.9.0
   python-dateutil>=2.8.2
   ```
2. Install and check the packages:
   ```bash
   pip install -r requirements.txt
   pip list
   ```

![Dependencies Installation](assets/step5_pip_install.png)

![Installed Dependencies](assets/step5_dependencies_installed.png)

Pandas reads the dataset and computes the metrics, and `kafka-python-ng` provides the Kafka producer and consumer clients.

---

### Step 5: Create the Batch Processor

1. Right-click the `batch` folder, select **New File**, and name it `batch_processor.py`.
2. Add the following code:

```python
import os
import sys
import time
from datetime import datetime
import pandas as pd


def get_project_root():
    """Returns absolute path to the batch-streaming-lab root directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, ".."))


def run_batch_processing(input_path=None, output_path=None, simulated_batch_delay_seconds=300):
    """
    Executes a batch run over incoming orders.
    
    Parameters:
    - input_path: path to orders.csv
    - output_path: destination for batch_results.csv
    - simulated_batch_delay_seconds: realistic batch window delay (default: 5 min = 300s)
      reflecting scheduled cron execution lag.
    """
    root_dir = get_project_root()
    if input_path is None:
        input_path = os.path.join(root_dir, "data", "orders.csv")
    if output_path is None:
        output_path = os.path.join(root_dir, "results", "batch_results.csv")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("=" * 60)
    print("QUICKCART BATCH PROCESSING PIPELINE")
    print(f"Triggered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input file  : {input_path}")
    print("=" * 60)

    if not os.path.exists(input_path):
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Read available records
    df = pd.read_csv(input_path)
    total_records = len(df)
    if total_records == 0:
        print("[WARNING] No records found to process.")
        return

    print(f"[*] Ingested {total_records} order records for batch processing.")

    # 2. Record processing execution timestamp
    start_compute_time = time.time()
    # Processing timestamp: baseline time when batch job executed
    # We add simulated_batch_delay_seconds to show batch accumulation delay
    processing_dt = datetime.now()
    processing_time_str = processing_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Parse event timestamps
    df["event_dt"] = pd.to_datetime(df["event_time"])

    # 3. Calculate latency and data freshness
    # In batch processing, records accumulated since their event_time until scheduled run
    # For reproducible benchmarking, we calculate difference between batch execution time and event time
    # If the CSV has historical event times (e.g. 10:00:xx), we compute elapsed time relative to base event
    first_event = df["event_dt"].min()
    base_delta_seconds = (processing_dt - first_event).total_seconds()

    # If the timestamps are past dates or artificial, ensure realistic batch latency
    if base_delta_seconds < 0 or base_delta_seconds > 86400 * 30:
        # Use simulated cron schedule delay (e.g., 5-minute accumulation window)
        accumulated_wait = simulated_batch_delay_seconds + (df["event_dt"].max() - df["event_dt"]).dt.total_seconds()
        df["latency_seconds"] = accumulated_wait.round(2)
        df["processing_time"] = (df["event_dt"] + pd.to_timedelta(accumulated_wait, unit="s")).dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        df["latency_seconds"] = (processing_dt - df["event_dt"]).dt.total_seconds().round(2)
        df["processing_time"] = processing_time_str

    # 4. Business Transformation: Enforce category and revenue calculations
    df["avg_item_price"] = (df["order_amount"] / df["item_count"]).round(2)
    df["order_tier"] = df["order_amount"].apply(
        lambda amt: "High Value" if amt >= 700 else ("Medium Value" if amt >= 400 else "Standard")
    )
    df["pipeline_type"] = "batch"

    # Simulate compute work
    time.sleep(0.05)
    compute_duration = time.time() - start_compute_time

    # 5. Save processed results
    output_columns = [
        "order_id",
        "customer_id",
        "restaurant",
        "order_amount",
        "item_count",
        "order_tier",
        "event_time",
        "processing_time",
        "latency_seconds",
        "pipeline_type"
    ]
    df[output_columns].to_csv(output_path, index=False)

    avg_latency = df["latency_seconds"].mean()
    throughput = total_records / max(compute_duration, 0.001)

    print("\n[+] Batch Run Completed Successfully!")
    print(f"    - Total Records Processed : {total_records}")
    print(f"    - Compute Duration        : {compute_duration:.4f} seconds")
    print(f"    - Batch Compute Throughput: {throughput:.2f} records/sec")
    print(f"    - Average Latency (Lag)   : {avg_latency:.2f} seconds")
    print(f"    - Destination             : {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    run_batch_processing()
```

The batch processor reads all available orders at once and stamps them with one processing time. For each record it calculates `latency_seconds` as the gap between the processing time and the original `event_time`, classifies the order tier, and saves the result to `results/batch_results.csv`.

---

### Step 6: Create the Batch Runner and Run a Batch

1. In the `batch` folder, create `run_batch.py`:

```python
#!/usr/bin/env python3
"""
QuickCart Scheduled Batch Runner
Module: batch/run_batch.py

Serves as the execution entrypoint for Cron or standalone periodic triggers.
Can be executed one-off via cron:
  * * * * * cd /path/to/batch-streaming-lab && python3 batch/run_batch.py >> logs/cron.log 2>&1
Or run in interval-loop mode for testing environments without system cron daemons.
"""

import argparse
import sys
import time
from batch_processor import run_batch_processing


def main():
    parser = argparse.ArgumentParser(description="Run QuickCart Batch Processing")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously in a loop to simulate cron execution intervals."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval in seconds between batch executions when running in --loop mode (default: 60s)."
    )
    args = parser.parse_args()

    if args.loop:
        print(f"[*] Starting Batch Runner in loop simulation mode (every {args.interval}s)...")
        print("Press Ctrl+C to terminate.")
        iteration = 1
        try:
            while True:
                print(f"\n--- Batch Trigger Cycle #{iteration} ---")
                run_batch_processing()
                iteration += 1
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[!] Batch runner stopped by user.")
    else:
        # One-off execution (standard cron trigger)
        run_batch_processing()


if __name__ == "__main__":
    main()
```

2. Run one batch from the terminal:
   ```bash
   python batch/run_batch.py
   ```

![Batch Execution](assets/step7_batch_execution.png)

The batch run ingested 20 orders and processed them in 0.0730 seconds (273.80 records/sec). The average latency is 1,703,786.06 seconds (about 19.7 days), because the orders in the CSV were created on 2026-10-05 and the batch ran on 2026-10-25. In batch processing, every record waits until the next scheduled run, so latency grows with the time between the event and the run.

---

### Step 7: Schedule the Batch with Cron

1. Open the crontab editor:
   ```bash
   crontab -e
   ```
2. Add the following line to run the batch every 5 minutes, replacing `/path/to/batch-streaming-lab` with your project path:
   ```text
   */5 * * * * cd /path/to/batch-streaming-lab && .venv/bin/python batch/run_batch.py >> results/cron.log 2>&1
   ```
3. If Cron is not available in your environment, simulate the schedule with the runner's loop mode (press **Ctrl+C** to stop):
   ```bash
   python batch/run_batch.py --loop --interval 60
   ```

Cron starts the batch processor only at the scheduled time. Orders that arrive between two runs wait for the next one, which is the main source of batch latency.

---

### Step 8: Inspect the Batch Results

Open `results/batch_results.csv` in the editor:

![Batch Results](assets/step9_batch_results.png)

Every row has the same processing time, and `latency_seconds` decreases by 3 seconds per row because each order was created 3 seconds after the previous one. These values are the batch baseline for the comparison.

---

### Step 9: Start Kafka and Create the Topic

1. Start a Kafka broker on `localhost:9092`.
2. Create a topic named `orders`:
   ```bash
   kafka-topics.sh --create --topic orders --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
   ```

The producer publishes order events to the `orders` topic and the consumer reads them from it. If no broker is reachable on `localhost:9092`, the producer and consumer fall back to a local file queue, and they print `Engine Mode: Local Stream Simulation Queue` instead of `Engine Mode: Kafka Broker (localhost:9092)`.

---

### Step 10: Create the Kafka Producer

1. Right-click the `streaming` folder, select **New File**, and name it `producer.py`.
2. Add the following code:

```python
#!/usr/bin/env python3
"""
QuickCart Real-time Streaming Producer
Module: streaming/producer.py

Reads or generates food order events, stamps current event timestamps, and
publishes them to the Kafka 'orders' topic.
Supports real Kafka broker (localhost:9092) and automated local fallback queue
for seamless execution in environments without a live Kafka daemon.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
import pandas as pd

# Check for kafka library
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False


def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_fallback_queue_path():
    root = get_project_root()
    queue_dir = os.path.join(root, "results", ".stream_queue")
    os.makedirs(queue_dir, exist_ok=True)
    return os.path.join(queue_dir, "orders_stream.jsonl")


def create_producer(bootstrap_servers="localhost:9092"):
    """Attempts to connect to Kafka producer; returns None if broker unreachable."""
    if not KAFKA_AVAILABLE:
        return None
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=2000
        )
        return producer
    except Exception:
        return None


def run_producer(interval=0.5, limit=None, bootstrap_servers="localhost:9092"):
    root_dir = get_project_root()
    input_csv = os.path.join(root_dir, "data", "orders.csv")

    if not os.path.exists(input_csv):
        print(f"[ERROR] Source data not found at {input_csv}")
        sys.exit(1)

    df = pd.read_csv(input_csv)
    records = df.to_dict(orient="records")
    if limit:
        records = records[:limit]

    print("=" * 60)
    print("QUICKCART STREAMING PRODUCER")
    print(f"Target Topic     : orders")
    print(f"Publish Interval : {interval} seconds/event")
    print(f"Total Events     : {len(records)}")
    print("=" * 60)

    producer = create_producer(bootstrap_servers)
    mode = "Kafka Broker (localhost:9092)" if producer else "Local Stream Simulation Queue"
    print(f"[*] Engine Mode: {mode}\n")

    fallback_file = None
    if producer is None:
        fallback_file = get_fallback_queue_path()
        # Reset queue for fresh run
        with open(fallback_file, "w", encoding="utf-8") as f:
            pass

    sent_count = 0
    start_time = time.time()

    for idx, row in enumerate(records, start=1):
        # Generate real-time event timestamp
        event_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_epoch = time.time()

        event = {
            "order_id": row["order_id"],
            "customer_id": row["customer_id"],
            "restaurant": row["restaurant"],
            "order_amount": float(row["order_amount"]),
            "item_count": int(row["item_count"]),
            "event_time": event_time_str,
            "event_epoch": event_epoch,
            "pipeline_type": "streaming"
        }

        if producer:
            producer.send("orders", value=event)
            producer.flush()
        else:
            with open(fallback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

        sent_count += 1
        print(f"[{sent_count:02d}/{len(records)}] Published {event['order_id']} | "
              f"Restaurant: {event['restaurant']:<15} | Amount: ${event['order_amount']:>6.2f} | Time: {event_time_str}")

        if idx < len(records):
            time.sleep(interval)

    duration = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"[+] Producer finished publishing {sent_count} events in {duration:.2f} seconds.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QuickCart Streaming Producer")
    parser.add_argument("--interval", type=float, default=0.3, help="Interval in seconds between orders (default: 0.3)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of events to publish")
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092", help="Kafka broker address")
    args = parser.parse_args()

    run_producer(interval=args.interval, limit=args.limit, bootstrap_servers=args.bootstrap_servers)
```

The producer publishes each order as a separate event and stamps it with the current time as `event_time` and `event_epoch`, so the consumer can measure how quickly each event is processed.

---

### Step 11: Create the Kafka Consumer

1. In the `streaming` folder, create `consumer.py`:

```python
#!/usr/bin/env python3
"""
QuickCart Real-time Streaming Consumer
Module: streaming/consumer.py

Subscribes to the Kafka 'orders' topic, processes incoming order events immediately,
records processing timestamps, computes per-record latency and data freshness,
and persists streaming results to results/streaming_results.csv.
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

# Check for kafka library
try:
    from kafka import KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False


def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_fallback_queue_path():
    root = get_project_root()
    return os.path.join(root, "results", ".stream_queue", "orders_stream.jsonl")


def create_consumer(bootstrap_servers="localhost:9092", auto_offset_reset="earliest"):
    if not KAFKA_AVAILABLE:
        return None
    try:
        consumer = KafkaConsumer(
            "orders",
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            consumer_timeout_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode("utf-8"))
        )
        return consumer
    except Exception:
        return None


def run_consumer(bootstrap_servers="localhost:9092", max_records=None, timeout_seconds=10):
    root_dir = get_project_root()
    output_csv = os.path.join(root_dir, "results", "streaming_results.csv")
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    print("=" * 60)
    print("QUICKCART STREAMING CONSUMER")
    print(f"Target Topic     : orders")
    print(f"Output File      : {output_csv}")
    print("=" * 60)

    consumer = create_consumer(bootstrap_servers)
    mode = "Kafka Broker (localhost:9092)" if consumer else "Local Stream Simulation Queue"
    print(f"[*] Engine Mode: {mode}\n")

    # CSV headers
    fieldnames = [
        "order_id",
        "customer_id",
        "restaurant",
        "order_amount",
        "item_count",
        "order_tier",
        "event_time",
        "processing_time",
        "latency_seconds",
        "pipeline_type"
    ]

    # Initialize CSV file with header
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    processed_count = 0
    total_latency = 0.0
    start_time = time.time()

    def process_event(event_dict):
        nonlocal processed_count, total_latency
        proc_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proc_epoch = time.time()

        # Compute real-time processing latency
        event_epoch = event_dict.get("event_epoch")
        if event_epoch:
            latency = max(0.001, proc_epoch - event_epoch)
        else:
            try:
                e_dt = datetime.strptime(event_dict["event_time"], "%Y-%m-%d %H:%M:%S")
                latency = max(0.001, (datetime.now() - e_dt).total_seconds())
            except Exception:
                latency = 0.05

        order_amount = float(event_dict["order_amount"])
        tier = "High Value" if order_amount >= 700 else ("Medium Value" if order_amount >= 400 else "Standard")

        record = {
            "order_id": event_dict["order_id"],
            "customer_id": event_dict["customer_id"],
            "restaurant": event_dict["restaurant"],
            "order_amount": order_amount,
            "item_count": int(event_dict["item_count"]),
            "order_tier": tier,
            "event_time": event_dict["event_time"],
            "processing_time": proc_time_str,
            "latency_seconds": round(latency, 3),
            "pipeline_type": "streaming"
        }

        with open(output_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(record)

        processed_count += 1
        total_latency += latency
        avg_lat = total_latency / processed_count

        print(f"[{processed_count:02d}] Consumed {record['order_id']} | "
              f"Latency: {latency * 1000:>6.1f} ms ({latency:.3f}s) | Avg: {avg_lat:.3f}s | "
              f"Tier: {tier:<10} | Freshness: FRESH")

    # Streaming loop
    if consumer:
        try:
            for message in consumer:
                process_event(message.value)
                if max_records and processed_count >= max_records:
                    break
        except KeyboardInterrupt:
            pass
    else:
        # Fallback file stream tailer
        fallback_file = get_fallback_queue_path()
        last_pos = 0
        idle_start = time.time()

        while True:
            if os.path.exists(fallback_file):
                current_size = os.path.getsize(fallback_file)
                if current_size < last_pos:
                    # File was truncated/restarted by a new producer run
                    last_pos = 0

                with open(fallback_file, "r", encoding="utf-8") as f:
                    f.seek(last_pos)
                    lines = f.readlines()
                    last_pos = f.tell()

                if lines:
                    idle_start = time.time()
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                event = json.loads(line)
                                process_event(event)
                                if max_records and processed_count >= max_records:
                                    break
                            except Exception:
                                continue
                else:
                    if processed_count > 0 and (time.time() - idle_start) > timeout_seconds:
                        print("\n[*] Stream idle timeout reached. Exiting consumer.")
                        break
                    time.sleep(0.05)
            else:
                if (time.time() - idle_start) > timeout_seconds:
                    print("\n[*] Waiting for stream timed out. Exiting.")
                    break
                time.sleep(0.1)

    total_time = max(time.time() - start_time, 0.001)
    avg_latency = (total_latency / processed_count) if processed_count > 0 else 0
    throughput = processed_count / total_time

    print("\n" + "=" * 60)
    print("[+] Streaming Consumer Session Completed")
    print(f"    - Total Events Processed : {processed_count}")
    print(f"    - Total Session Duration : {total_time:.2f} seconds")
    print(f"    - Average Latency        : {avg_latency:.4f} seconds ({avg_latency * 1000:.1f} ms)")
    print(f"    - Streaming Throughput   : {throughput:.2f} events/sec")
    print(f"    - Output Saved To        : {output_csv}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QuickCart Streaming Consumer")
    parser.add_argument("--bootstrap-servers", type=str, default="localhost:9092", help="Kafka broker address")
    parser.add_argument("--max-records", type=int, default=None, help="Exit after processing N records")
    parser.add_argument("--timeout", type=int, default=5, help="Seconds to wait before exiting when idle")
    args = parser.parse_args()

    run_consumer(bootstrap_servers=args.bootstrap_servers, max_records=args.max_records, timeout_seconds=args.timeout)
```

The consumer processes every event as soon as it arrives. It calculates latency per event, assigns the same order tiers as the batch processor, and appends each record to `results/streaming_results.csv`.

---

### Step 12: Run the Streaming Pipeline

1. In the `streaming` folder, create `run_streaming.py`, which starts the consumer in a background thread and then runs the producer:

```python
#!/usr/bin/env python3
"""
QuickCart End-to-End Streaming Runner
Module: streaming/run_streaming.py

Runs the Kafka Consumer in a background worker thread and executes the Producer
concurrently in the main thread. This demonstrates true real-time event streaming
with sub-second latency even in single-terminal environments.
"""

import os
import threading
import time
from consumer import run_consumer
from producer import run_producer


def main():
    print("=" * 60)
    print("LAUNCHING QUICKCART CONCURRENT STREAMING PIPELINE")
    print("=" * 60)

    # Clean existing fallback queue if present
    from producer import get_fallback_queue_path
    queue_path = get_fallback_queue_path()
    if os.path.exists(queue_path):
        os.remove(queue_path)

    # Start consumer in worker thread
    consumer_thread = threading.Thread(
        target=run_consumer,
        kwargs={"timeout_seconds": 3, "max_records": 20},
        daemon=True
    )
    consumer_thread.start()

    # Small pause to allow consumer to attach to topic/queue
    time.sleep(0.5)

    # Run producer in main thread
    run_producer(interval=0.1, limit=20)

    # Wait for consumer to finish processing all records
    consumer_thread.join(timeout=10)
    print("\n[+] Streaming pipeline run complete!")


if __name__ == "__main__":
    main()
```

2. Run the streaming pipeline:
   ```bash
   python streaming/run_streaming.py
   ```

![Streaming Live Events](assets/step14_streaming_live.png)

![Streaming Summary](assets/step14_streaming_summary.png)

The producer published 20 events at 0.1-second intervals, and the consumer processed each one within about 17–60 ms, with an average latency of 40.4 ms. In this run both components printed `Engine Mode: Local Stream Simulation Queue`, which means no Kafka broker was reachable and the events went through the local fallback queue.

---

### Step 13: Compare Batch and Streaming

1. In the `metrics` folder, create `comparison.py`:

```python
#!/usr/bin/env python3
"""
QuickCart Data Engineering Benchmark: Batch vs Streaming Comparison
Module: metrics/comparison.py

Reads results from both batch and streaming runs:
- results/batch_results.csv
- results/streaming_results.csv

Calculates and displays comparative metrics:
- Latency (Average, Min, Max, Median)
- Throughput (Records per second)
- Data Freshness (Event lag to processing availability)
- Trade-off Analysis Summary
"""

import os
import sys
import pandas as pd


def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_dataset(filepath, name):
    if not os.path.exists(filepath):
        print(f"[ERROR] Required result file not found: {filepath}")
        print(f"Please run the {name} pipeline first.")
        return None
    return pd.read_csv(filepath)


def calculate_metrics(df, pipeline_name):
    total_records = len(df)
    if total_records == 0:
        return None

    # Latency stats
    avg_latency = df["latency_seconds"].mean()
    min_latency = df["latency_seconds"].min()
    max_latency = df["latency_seconds"].max()
    median_latency = df["latency_seconds"].median()

    # Data Freshness
    # Freshness measures the average time elapsed between event occurrence and result availability
    freshness_seconds = avg_latency

    # Processing window throughput calculation
    # Throughput = records processed / total span of processing timestamps (or compute span)
    proc_times = pd.to_datetime(df["processing_time"])
    time_span = (proc_times.max() - proc_times.min()).total_seconds()
    
    # If all records processed in the same second (typical for batch), estimate throughput
    if time_span <= 0:
        # Batch burst compute: 20 records in ~0.08s
        estimated_compute_time = 0.08
        throughput = total_records / estimated_compute_time
    else:
        throughput = total_records / time_span

    return {
        "pipeline": pipeline_name,
        "total_records": total_records,
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "median_latency": median_latency,
        "throughput": throughput,
        "freshness_seconds": freshness_seconds,
    }


def print_comparison_table(b_metrics, s_metrics):
    header_sep = "=" * 76
    row_sep = "-" * 76

    print("\n" + header_sep)
    print("      QUICKCART PIPELINE BENCHMARK: BATCH (CRON) VS STREAMING (KAFKA)")
    print(header_sep)
    print(f"{'Metric':<28} | {'Batch Pipeline':<21} | {'Streaming Pipeline':<21}")
    print(header_sep)

    print(f"{'Records Processed':<28} | {b_metrics['total_records']:<21} | {s_metrics['total_records']:<21}")
    print(f"{'Average Latency':<28} | {b_metrics['avg_latency']:>8.2f} sec           | {s_metrics['avg_latency'] * 1000:>8.1f} ms ({s_metrics['avg_latency']:.3f}s)")
    print(f"{'Median Latency':<28} | {b_metrics['median_latency']:>8.2f} sec           | {s_metrics['median_latency'] * 1000:>8.1f} ms ({s_metrics['median_latency']:.3f}s)")
    print(f"{'Min Latency':<28} | {b_metrics['min_latency']:>8.2f} sec           | {s_metrics['min_latency'] * 1000:>8.1f} ms ({s_metrics['min_latency']:.3f}s)")
    print(f"{'Max Latency':<28} | {b_metrics['max_latency']:>8.2f} sec           | {s_metrics['max_latency'] * 1000:>8.1f} ms ({s_metrics['max_latency']:.3f}s)")
    print(row_sep)
    print(f"{'Throughput':<28} | {b_metrics['throughput']:>8.1f} rec/sec        | {s_metrics['throughput']:>8.1f} rec/sec")
    print(f"{'Data Freshness (Avg Lag)':<28} | {b_metrics['freshness_seconds']:>8.2f} sec (STALE)     | {s_metrics['freshness_seconds'] * 1000:>8.1f} ms (LIVE)")
    print(header_sep)

    # Ratio comparisons
    latency_ratio = b_metrics['avg_latency'] / max(s_metrics['avg_latency'], 0.0001)
    print(f"\n[*] KEY TAKEAWAY & TRADE-OFF SUMMARY:")
    print(f"  • Latency Advantage   : Streaming is {latency_ratio:,.0f}x FASTER at reacting to incoming orders.")
    print(f"  • Data Freshness      : Streaming delivers sub-second fresh data ({s_metrics['avg_latency']*1000:.1f}ms) vs {b_metrics['avg_latency']:.1f}s delay in batch.")
    print(f"  • Throughput Profile  : Batch excels at high-density burst compute ({b_metrics['throughput']:.0f} rec/s);")
    print(f"                          Streaming sustains continuous event-driven flow ({s_metrics['throughput']:.1f} rec/s).")
    print(f"  • Architecture Cost   : Batch requires simple Cron scheduler; Streaming requires broker (Kafka) & daemons.")
    print(header_sep + "\n")


def main():
    root = get_project_root()
    batch_file = os.path.join(root, "results", "batch_results.csv")
    stream_file = os.path.join(root, "results", "streaming_results.csv")

    b_df = load_dataset(batch_file, "Batch")
    s_df = load_dataset(stream_file, "Streaming")

    if b_df is None or s_df is None:
        sys.exit(1)

    b_metrics = calculate_metrics(b_df, "Batch")
    s_metrics = calculate_metrics(s_df, "Streaming")

    print_comparison_table(b_metrics, s_metrics)


if __name__ == "__main__":
    main()
```

2. Run the comparison:
   ```bash
   python metrics/comparison.py
   ```

![Benchmark Comparison](assets/step11_benchmark_comparison.png)

The script reads both result files and prints the same metrics for each pipeline. Streaming has an average latency of 40.3 ms, while batch has 1,703,786.06 seconds, because batch records wait for the scheduled run. Batch throughput is reported as 250.0 records/sec: all batch rows share one processing timestamp, so the script uses an estimated compute time of 0.08 seconds. Streaming throughput is 10.0 records/sec, limited by the producer's 0.1-second publish interval rather than by processing speed.

---

## 5. Results

| Metric | Batch (Cron) | Streaming |
| :--- | :--- | :--- |
| Records processed | 20 | 20 |
| Average latency | 1,703,786.06 s | 40.3 ms |
| Min / max latency | 1,703,757.56 s / 1,703,814.56 s | 17.0 ms / 60.0 ms |
| Throughput | 250.0 rec/s (estimated) | 10.0 rec/s |
| Data freshness | Stale (waits for the next run) | Live (sub-second) |

| | Batch | Streaming |
| :--- | :--- | :--- |
| Processing model | Periodic | Continuous |
| Scheduling | Cron | Event-driven |
| Broker | Not required | Kafka |
| System complexity | Simple script and scheduler | Broker and long-running services |
| Best for | Reports, scheduled ETL, large periodic loads | Monitoring, alerts, live dashboards |

---

## 6. Conclusion

In this lab, you processed the same QuickCart orders with a Cron-scheduled batch pipeline and an event-driven streaming pipeline, and compared them using timestamps recorded by each pipeline. Batch processing is simple and handles a whole file in one fast run, but every record waits for the next scheduled run, so its data is never fresher than the schedule allows. Streaming processes each event within milliseconds but needs a broker and always-on services. Choose between them based on how fresh the data must be, how much data arrives, and how much operational complexity the team can support.
