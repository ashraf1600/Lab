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
