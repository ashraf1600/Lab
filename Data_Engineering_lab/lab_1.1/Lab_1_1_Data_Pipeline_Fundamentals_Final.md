# Data Pipeline Fundamentals

## 1. Introduction

Imagine you have just joined **QuickCart**, a fast-growing online food delivery platform, as a **Junior Data Engineer**. Every evening, partner restaurants upload raw CSV order files, but the data often contains missing IDs, corrupted numbers, negative quantities, and inconsistent text formatting. Manual spreadsheet checks are no longer enough, and analytics dashboards are becoming slow over unindexed CSV data.

Your team lead asks you to build an automated **Extract, Transform, Validate, and Load (ETL)** pipeline. It will read daily order CSV files, clean and validate the records, calculate revenue fields, save trusted data as **Apache Parquet**, and write logs so pipeline failures can be traced.

You will build the following QuickCart order data pipeline:

![Pipeline Architecture](assets/Lab_1-1(DE).drawio.svg)

Raw CSV files are loaded into Pandas, cleaned, validated against business rules, and written to optimized Parquet output. Invalid records trigger structured warning logs, helping downstream analytics and machine learning systems consume reliable data.

---

## 2. Objectives

By the end of this lab, you will be able to:

- Build a Python ETL script that reads a CSV file, transforms it, and writes Parquet.
- Validate records against business rules and quarantine invalid rows.
- Add structured logging so every pipeline stage leaves a trace.
- Use `try/except` error handling to capture pipeline failures with full stack traces.

---

## 3. Project File Structure

The project keeps raw inputs, transformed outputs, business logic, and operational logs in separate folders:

```text
quickcart-data-pipeline/
│
├── data/
│   └── orders.csv              # Raw order data
│
├── src/
│   ├── pipeline.py             # ETL pipeline script
│   └── check_output.py         # Output verification script
│
├── output/
│   ├── orders_clean.parquet    # Cleaned Parquet data
│   └── rejected_orders.csv     # Quarantined invalid rows
│
├── logs/
│   └── pipeline.log            # Pipeline execution logs
│
└── requirements.txt            # Python dependencies
```

---

## 4. Project Implementation

### Step 1: Open VS Code Server and Create Project Folders

1. Open your **VS Code Server** workspace and create a project folder named:
   ```text
   quickcart-data-pipeline
   ```
2. Open the folder with **File > Open Folder...**.
3. In the VS Code Explorer sidebar (left panel), click the **New Folder** icon to create the following directories:
   - `data`
   - `src`
   - `output`
   - `logs`

---

### Step 2: Initialize and Activate Python Virtual Environment

1. Open an integrated terminal by clicking **Terminal > New Terminal**.
2. Create an isolated virtual environment named `.venv`:
   ```bash
   python3 -m venv .venv
   ```
3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

   *(Note: If working locally on Windows PowerShell, run: `.venv\Scripts\Activate.ps1`)*
4. Verify that `(.venv)` appears at the beginning of your terminal prompt.

![Virtual Environment Activated](assets/step2_virtual_environment.png)

The `(.venv)` prefix confirms the virtual environment is active. Every package installed from now on stays inside this project and does not conflict with system-wide Python packages.

---

### Step 3: Create `requirements.txt` and Install Dependencies

1. In the VS Code Explorer, click the **New File** icon in the root directory and name it:
   ```text
   requirements.txt
   ```
2. Open `requirements.txt` in the editor and add the required data engineering libraries:
   ```text
   pandas>=2.0.0
   pyarrow>=14.0.0
   ```
3. Save the file by clicking **File > Save**.
4. In your activated terminal, install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Confirm successful installation:
   ```bash
   pip list
   ```

![Installed Dependencies](assets/step3_dependencies_installed.png)

Pandas handles the data transformations and PyArrow writes the Parquet file. Keeping the dependencies in `requirements.txt` lets anyone recreate the same environment with one command.

---

### Step 4: Create the Incoming Raw Orders Dataset

1. In the VS Code Explorer, expand the `data/` folder.
2. Right-click on `data` and select **New File**, naming it:
   ```text
   orders.csv
   ```
3. Open `data/orders.csv` and paste the following sample batch of QuickCart restaurant orders:
   ```csv
   order_id,customer_id,restaurant,item,quantity,unit_price,order_date
   1001,C001,FoodHub,Classic Burger,2,250,2026-10-01
   1002,C002,Spice Kitchen,Chicken Biryani,1,320,2026-10-01
   1003,C003,Pizza Paradiso,Margherita Pizza,2,450,2026-10-01
   1004,C004,Royal Kitchen,Mutton Kacchi,1,480,2026-10-01
   1005,C005,Spice Kitchen,Garlic Naan,4,60,2026-10-01
   1006,C006,FoodHub,Crispy Fries,2,120,2026-10-01
   1007,C007,Royal Kitchen,Butter Chicken,1,380,2026-10-01
   1008,C008,Pizza Paradiso,Pasta Alfredo,2,340,2026-10-01
   1009,C009,Wok & Roll,Egg Fried Rice,2,220,2026-10-02
   1010,C010,Green Bowl,Caesar Salad,1,280,2026-10-02
   1011,C011,Wok & Roll,Chicken Chowmein,1,260,2026-10-02
   1012,C012,Cafe Mocha,Iced Caramel Latte,2,210,2026-10-02
   1013,C013,FoodHub,BBQ Wings,3,190,2026-10-02
   1014,C014,Spice Kitchen,Paneer Butter Masala,1,290,2026-10-02
   1015,C015,Green Bowl,Avocado Toast,2,240,2026-10-02
   1016,C016,Cafe Mocha,Chocolate Brownie,2,150,2026-10-02
   1017,C017,Pizza Paradiso,Pepperoni Pizza,1,520,2026-10-03
   1018,C018,Royal Kitchen,Beef Rezala,1,420,2026-10-03
   1019,C019,FoodHub,Smoky Chicken Wrap,2,230,2026-10-03
   1020,C020,Green Bowl,Detox Green Juice,1,160,2026-10-03
   1021,C021,Wok & Roll,Steamed Momos,3,180,2026-10-03
   1022,C022,Cafe Mocha,Cappuccino,2,190,2026-10-03
   1023,C023,Spice Kitchen,Hyderabadi Pulao,2,310,2026-10-03
   1024,C024,Pizza Paradiso,Cheesy Garlic Bread,2,170,2026-10-03
   1025,C025,Royal Kitchen,Gulab Jamun,4,75,2026-10-03
   ```
4. Save the file by clicking **File > Save**.

![Raw Orders Dataset](assets/step4_raw_orders_csv.png)

The CSV holds 25 orders from QuickCart's restaurant partners with order IDs, customer IDs, menu items, quantities, prices, and order dates. This sample batch is used to test the transformation and validation rules.

---

### Step 5: Implement the ETL Pipeline Script

1. In the VS Code Explorer, right-click the `src/` folder and select **New File**. Name it:
   ```text
   pipeline.py
   ```
2. Open `src/pipeline.py` and add the ETL implementation:

```python
import logging
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "orders.csv"
OUTPUT_FILE = BASE_DIR / "output" / "orders_clean.parquet"
REJECTED_FILE = BASE_DIR / "output" / "rejected_orders.csv"
LOG_FILE = BASE_DIR / "logs" / "pipeline.log"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def extract_data() -> pd.DataFrame:
    logger.info("Starting data extraction")
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found at {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)
    logger.info("Data extraction completed | rows=%d", len(df))
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Starting data transformation")
    df = df.copy()

    df["restaurant"] = df["restaurant"].astype(str).str.strip()
    df["item"] = df["item"].astype(str).str.strip()

    initial_count = len(df)
    df = df.drop_duplicates(subset=["order_id"])
    if len(df) < initial_count:
        logger.info("Duplicates removed | count=%d", initial_count - len(df))

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    df["total_amount"] = df["quantity"] * df["unit_price"]

    logger.info("Data transformation completed")
    return df


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Starting data validation")

    required_columns = ["order_id", "customer_id", "restaurant", "item", "quantity", "unit_price", "order_date"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Schema validation failed. Missing required columns: {missing_columns}")

    invalid_rows = (
        df["order_id"].isna()
        | df["customer_id"].isna()
        | df["quantity"].isna()
        | (df["quantity"] <= 0)
        | df["unit_price"].isna()
        | (df["unit_price"] < 0)
        | df["order_date"].isna()
    )

    valid_df = df[~invalid_rows].copy()
    rejected_df = df[invalid_rows].copy()
    rejected_count = len(rejected_df)

    if rejected_count > 0:
        logger.warning("Invalid records detected | rejected_count=%d", rejected_count)
        rejected_df.to_csv(REJECTED_FILE, index=False)
        logger.info("Rejected records saved for inspection | destination=%s", REJECTED_FILE)

    logger.info("Validation completed | valid=%d | rejected=%d", len(valid_df), rejected_count)
    return valid_df


def load_data(df: pd.DataFrame) -> None:
    logger.info("Starting data loading")
    df.to_parquet(OUTPUT_FILE, index=False)
    logger.info("Data loading completed | destination=%s | rows=%d", OUTPUT_FILE, len(df))


def main():
    try:
        logger.info("========== Pipeline Started ==========")
        df_raw = extract_data()
        df_transformed = transform_data(df_raw)
        df_valid = validate_data(df_transformed)
        load_data(df_valid)
        logger.info("========== Pipeline Completed Successfully ==========")
    except Exception as error:
        logger.exception("Pipeline failed with unexpected error | error=%s", error)
        raise


if __name__ == "__main__":
    main()
```

3. Save the file by clicking **File > Save**.

The pipeline is split into four functions. Extraction loads the raw file, transformation cleans text, removes duplicate orders, and derives `total_amount`, validation moves invalid rows to `output/rejected_orders.csv`, and loading writes the valid rows to Parquet. The `try/except` block in `main()` writes any unhandled error and its stack trace to the log.

---

### Step 6: Execute the Pipeline

1. In your VS Code terminal, execute the pipeline script:
   ```bash
   python src/pipeline.py
   ```
2. The command prints nothing to the terminal because all messages go to the log file.

![Pipeline Execution](assets/step6_pipeline_execution.png)

The pipeline ran end to end. The cleaned data is written to `output/` and the execution trace to `logs/pipeline.log`.

---

### Step 7: Verify the Generated Parquet Output

1. In the VS Code Explorer, right-click `src/` and create a verification script named:
   ```text
   check_output.py
   ```
2. Add the following inspection code:
   ```python
   from pathlib import Path
   import pandas as pd

   BASE_DIR = Path(__file__).resolve().parent.parent
   OUTPUT_FILE = BASE_DIR / "output" / "orders_clean.parquet"

   print("--- Reading Cleaned Parquet Dataset ---")
   df = pd.read_parquet(OUTPUT_FILE)

   print("\nSample Data (First 5 Rows):")
   print(df.head())

   print("\nDataset Schema & Data Types:")
   print(df.info())

   print(f"\nTotal Valid Records Processed: {len(df)}")
   ```
3. Save the file and run it in the terminal:
   ```bash
   python src/check_output.py
   ```

![Parquet Output and Schema](assets/step7_parquet_output.png)

The Parquet file holds all 25 records with typed columns: `order_date` is a datetime and `quantity`, `unit_price`, and `total_amount` are integers. The derived `total_amount` column equals `quantity * unit_price` for every row. The `None` on the last line is the return value of `df.info()`, which prints its own output.

---

### Step 8: Inspect the Execution Log

1. In the VS Code Explorer, expand the `logs/` directory.
2. Click on `pipeline.log` to open it in the editor.
3. Review the execution trace:
   ```text
   2026-10-04 14:30:41,843 | INFO | ========== Pipeline Started ==========
   2026-10-04 14:30:41,843 | INFO | Starting data extraction
   2026-10-04 14:30:41,859 | INFO | Data extraction completed | rows=25
   2026-10-04 14:30:41,859 | INFO | Starting data transformation
   2026-10-04 14:30:41,887 | INFO | Data transformation completed
   2026-10-04 14:30:41,887 | INFO | Starting data validation
   2026-10-04 14:30:41,897 | INFO | Validation completed | valid=25 | rejected=0
   2026-10-04 14:30:41,897 | INFO | Starting data loading
   2026-10-04 14:30:42,256 | INFO | Data loading completed | destination=... | rows=25
   2026-10-04 14:30:42,256 | INFO | ========== Pipeline Completed Successfully ==========
   ```

![Structured Logs](assets/step8_structured_logs.png)

The log keeps a timestamped record of every ETL stage: 25 rows extracted, 25 valid, 0 rejected, and 25 loaded. Because every line uses the same `time | level | message` format, monitoring tools can parse it and raise alerts, for example when a batch is smaller than expected.

---

### Step 9: Test Data Quality Validation and Record Rejection

1. In the VS Code Explorer, open `data/orders.csv`.
2. Edit line 4 (order `1003`) by changing the quantity from `2` to `-2` (simulating a corrupted cancellation entry):
   ```csv
   1003,C003,Pizza Paradiso,Margherita Pizza,-2,450,2026-10-01
   ```
3. Save the file by clicking **File > Save**.
4. Re-run the pipeline in your terminal:
   ```bash
   python src/pipeline.py
   ```
5. Re-open `logs/pipeline.log` and check the data quality warning:
   ```text
   WARNING | Invalid records detected | rejected_count=1
   INFO | Validation completed | valid=24 | rejected=1
   ```

![Validation Warning](assets/step9_validation_warning.png)

The pipeline flags the negative quantity, so the bad order never reaches the analytics data. The invalid row is saved to `output/rejected_orders.csv` and the remaining 24 valid records are written to Parquet. The warning line records how many rows were rejected.

---

### Step 10: Test Pipeline Crash and Error Handling

1. In the VS Code Explorer, right-click `data/orders.csv`, select **Rename**, and change the filename to:
   ```text
   orders_missing.csv
   ```
2. Run the pipeline in the terminal:
   ```bash
   python src/pipeline.py
   ```
3. Open `logs/pipeline.log` and scroll to the bottom. The `try/except` block captured the `FileNotFoundError` together with the full stack trace:
   ```text
   ERROR | Pipeline failed with unexpected error | error=Input file not found...
   Traceback (most recent call last):
   ...
   FileNotFoundError: Input file not found at .../data/orders.csv
   ```
4. In the Explorer, right-click `data/orders_missing.csv`, select **Rename**, and restore the name to `orders.csv`.
5. Restore the original quantity `2` for order `1003` in `data/orders.csv`, save, and re-run `python src/pipeline.py` to leave the lab in a clean state.

![Error Handling Stack Trace](assets/step10_pipeline_error.png)

This test simulates a missing upstream file. The pipeline does not fail silently: it writes the exception and its traceback to the log and then stops with a non-zero exit code, so the team can see exactly what went wrong.

---

## 5. Conclusion

QuickCart's daily restaurant orders are now ingested, cleaned, validated, and stored as efficient Parquet datasets. With modular ETL stages, structured logging, and exception handling, the pipeline delivers reliable data to dashboards and future ML workflows. In the next lab, we will extend this batch pipeline into real-time event streaming with Apache Kafka.
