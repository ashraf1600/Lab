# QuickCart Schema Evolution & Governance Lab

This directory contains the complete implementation for **Lab 1.4: Schema Evolution & Governance**.

## Project Structure

```text
schema-evolution-lab/
├── schemas/
│   ├── order_v1.json            # Baseline V1 Order Event Schema
│   ├── order_v2_add.json        # V2: Non-breaking optional field addition (payment_method)
│   ├── order_v2_remove.json     # V2: Breaking required field removal (amount)
│   └── order_v2_rename.json     # V2: Breaking field rename (amount -> total_amount)
├── producer/
│   └── producer.py              # Order event producer supporting multiple schema versions
├── consumer/
│   └── consumer.py              # Order event consumer validating against V1 schema contract
├── tests/
│   ├── test_add_field.py        # Validates non-breaking evolution (V2 add -> V1 consumer)
│   ├── test_remove_field.py     # Validates breaking evolution (V2 remove -> V1 consumer)
│   └── test_rename_field.py     # Validates breaking evolution (V2 rename -> V1 consumer)
├── results/
│   └── compatibility_report.json # Automated compatibility evaluation report
├── requirements.txt             # Python dependencies (jsonschema, pytest, tabulate)
└── README.md
```

## Quick Start

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   # On Windows: .venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run baseline test:
   ```bash
   python tests/test_add_field.py
   ```
