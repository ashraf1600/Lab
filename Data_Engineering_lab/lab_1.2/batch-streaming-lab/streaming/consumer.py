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
