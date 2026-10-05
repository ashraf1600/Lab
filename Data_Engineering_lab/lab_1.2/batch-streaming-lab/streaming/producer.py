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
