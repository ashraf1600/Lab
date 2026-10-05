# Data Engineering Labs

This repository contains comprehensive hands-on labs and production-grade architectures designed for modern data and ML engineering workflows.

---

## Lab Structure

The data engineering labs are organized modularly into self-contained directories:

```text
Data_Engineering_lab/
├── lab_1.1/
│   ├── quickcart-data-pipeline/                 # Code project (ETL pipeline, DuckDB, Parquet)
│   ├── assets/                                  # Lab architecture & terminal execution screenshots
│   ├── Lab_1_1_Data_Pipeline_Fundamentals_Final.md # Complete end-to-end lab guide
│   ├── Lab_1_R_&D.md                            # R&D lab documentation
│   ├── problem.md                               # Flow & structure review
│   └── image.png
├── lab_1.2/
│   ├── batch-streaming-lab/                     # Code project (Batch vs. Kafka-style streaming)
│   ├── assets/                                  # Architecture diagrams and benchmark screenshots
│   ├── Lab_2_R&D.md                             # Complete end-to-end lab guide
│   └── problems_lab2.md                         # Flow & structure review
├── lab_1.3/
│   ├── train-serve-skew-lab/                    # Code project (Drift simulation & skew detection engine)
│   ├── assets/                                  # Architecture diagrams and distribution plots
│   ├── Lab_1_3_Train_Serve_Skew_Final.md        # Complete end-to-end lab guide
│   ├── Lab_1_3_R&D.md                           # R&D documentation
│   ├── Lab_3_R&D.md                             # Comprehensive R&D documentation
│   └── problems.md                              # Flow & structure review
├── lab_1.4/
│   ├── schema-evolution-lab/                    # Code project (Data contracts, producer/consumer, compatibility matrix)
│   ├── assets/                                  # Architecture SVG & annotated screenshot assets
│   ├── Lab_1_4.md                               # Complete end-to-end student guide
│   ├── Lab_1_4_R&D.md                           # R&D reference document
│   └── problems.md                              # Problem & resolution log
└── README.md
```

---

## Summary of Labs

### [Lab 1.1: Data Pipeline Fundamentals (QuickCart ETL)](./lab_1.1/Lab_1_1_Data_Pipeline_Fundamentals_Final.md)
- **Focus**: Building robust batch ETL data pipelines for e-commerce order ingestion.
- **Key Concepts**: Ingestion validation, null handling, data deduplication, DuckDB transformations, schema validation, and optimized columnar storage with Parquet.
- **Project Folder**: [`lab_1.1/quickcart-data-pipeline`](./lab_1.1/quickcart-data-pipeline/)

### [Lab 1.2: Batch vs. Streaming Processing](./lab_1.2/Lab_2_R&D.md)
- **Focus**: Comparing high-throughput scheduled batch processing against event-driven real-time streaming architectures.
- **Key Concepts**: Latency vs throughput tradeoffs, micro-batching, streaming consumer/producer patterns, operational metrics, and benchmark comparisons.
- **Project Folder**: [`lab_1.2/batch-streaming-lab`](./lab_1.2/batch-streaming-lab/)

### [Lab 1.3: Train-Serve Skew Simulation & Detection](./lab_1.3/Lab_1_3_Train_Serve_Skew_Final.md)
- **Focus**: Identifying, measuring, and alerting on distribution drift and train-serve skew in production ML pipelines.
- **Key Concepts**: Historical baseline vs. online serving drift, logistic regression cancellation prediction, statistical divergence metrics, automated skew thresholding, and visual distribution reporting.
- **Project Folder**: [`lab_1.3/train-serve-skew-lab`](./lab_1.3/train-serve-skew-lab/)

### [Lab 1.4: Schema Evolution & Governance](./lab_1.4/Lab_1_4.md)
- **Focus**: Establishing versioned JSON data contracts and preventing breaking changes across distributed event-driven systems.
- **Key Concepts**: JSON Schema Draft 2020-12, backward compatibility verification, non-breaking optional additions vs breaking removals/renames, automated compatibility matrix gating, and dual-write deprecation patterns.
- **Project Folder**: [`lab_1.4/schema-evolution-lab`](./lab_1.4/schema-evolution-lab/)
