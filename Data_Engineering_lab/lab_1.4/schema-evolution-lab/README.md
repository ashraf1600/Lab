# QuickCart Schema Evolution & Governance Lab

This directory contains the complete implementation for **Lab 1.4: Schema Evolution & Governance**.

## Project Structure

```text
schema-evolution-lab/
├── schemas/
│   ├── order_v1.json            # Baseline V1 schema
│   ├── order_v2_add.json        # V2: add optional field
│   ├── order_v2_remove.json     # V2: remove required field
│   └── order_v2_rename.json     # V2: rename required field
├── producer/
│   └── producer.py              # Event producer
├── consumer/
│   └── consumer.py              # Event consumer (V1 contract)
├── tests/
│   ├── test_add_field.py        # Test Scenario A (add field)
│   ├── test_remove_field.py     # Test Scenario B (remove field)
│   └── test_rename_field.py     # Test Scenario C (rename field)
├── results/
│   └── compatibility_report.json # Compatibility report
├── requirements.txt             # Python dependencies
└── README.md                    # Lab documentation
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
