# Lab 1.2: Batch vs Streaming Trade-offs (QuickCart)

This repository implements the comparative data engineering lab comparing **Batch Processing (Cron)** and **Real-Time Streaming (Apache Kafka)** for QuickCart food delivery orders.

---

## 1. Project Directory Structure

```text
batch-streaming-lab/
│
├── data/
│   └── orders.csv              # Incoming raw food orders with event timestamps
│
├── batch/
│   ├── batch_processor.py      # Core batch ETL processor (latency, freshness, tiers)
│   └── run_batch.py            # Cron execution runner / interval simulator
│
├── streaming/
│   ├── producer.py             # Kafka producer emitting real-time order events
│   ├── consumer.py             # Kafka consumer measuring millisecond event latency
│   └── run_streaming.py        # End-to-end concurrent producer/consumer runner
│
├── results/
│   ├── batch_results.csv       # Persisted batch run records and latencies
│   └── streaming_results.csv   # Persisted streaming run records and latencies
│
├── metrics/
│   └── comparison.py           # Benchmark script calculating latency, throughput, freshness
│
├── requirements.txt            # Python dependencies
└── README.md                   # Lab documentation and operational guide
```

---

## 2. Setup & Installation

In your terminal (with Python virtual environment activated):

```bash
pip install -r requirements.txt
```

---

## 3. Running Batch Processing (Cron)

### Manual / One-Off Run:
```bash
python batch/batch_processor.py
```

### Scheduled Cron Configuration:
To schedule the batch processor every 5 minutes in Linux crontab:
```bash
crontab -e
```
Add the following line:
```text
*/5 * * * * cd /path/to/batch-streaming-lab && python3 batch/run_batch.py >> logs/cron.log 2>&1
```

---

## 4. Running Streaming Pipeline (Apache Kafka)

### Option A: Standard Multi-Terminal Mode (with Kafka Broker)
1. Start Kafka broker on `localhost:9092` and ensure topic `orders` exists:
   ```bash
   kafka-topics.sh --create --topic orders --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
   ```
2. In **Terminal 1**, start the consumer:
   ```bash
   python streaming/consumer.py
   ```
3. In **Terminal 2**, start the producer:
   ```bash
   python streaming/producer.py --interval 0.2
   ```

### Option B: Single-Terminal Concurrent Test Mode (Works with or without live Kafka)
```bash
python streaming/run_streaming.py
```

---

## 5. Compare Benchmark Metrics

Run the comparative analysis engine:
```bash
python metrics/comparison.py
```

---

## 6. Observed Trade-off Results

| Metric | Batch Pipeline (Cron) | Streaming Pipeline (Kafka) |
| :--- | :--- | :--- |
| **Processing Paradigm** | Periodic accumulation | Continuous per-event |
| **Average Latency** | ~300 – 350 seconds | ~40 milliseconds |
| **Data Freshness** | Stale (minutes old) | Live (sub-second) |
| **Compute Profile** | High-density burst compute | Continuous lightweight throughput |
| **System Complexity** | Low (script + OS cron) | Moderate-High (Kafka cluster, daemons) |
