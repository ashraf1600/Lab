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
