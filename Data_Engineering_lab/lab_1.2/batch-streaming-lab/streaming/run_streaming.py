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
