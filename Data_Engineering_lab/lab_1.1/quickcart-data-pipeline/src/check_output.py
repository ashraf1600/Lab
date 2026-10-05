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
