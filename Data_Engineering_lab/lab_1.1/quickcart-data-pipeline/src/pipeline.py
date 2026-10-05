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
