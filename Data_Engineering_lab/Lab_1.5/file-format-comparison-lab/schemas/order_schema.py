"""
Canonical PyArrow schema contract for QuickCart order transactions.
Maintains exact type and logical parity with schemas/order_schema.avsc.
"""

import pyarrow as pa

ORDER_PYARROW_SCHEMA = pa.schema([
    pa.field("order_id", pa.string(), nullable=False),
    pa.field("customer_id", pa.string(), nullable=False),
    pa.field("order_timestamp", pa.timestamp("ms"), nullable=False),
    pa.field("item_count", pa.int32(), nullable=False),
    pa.field("order_amount", pa.float64(), nullable=False),
    pa.field("delivery_distance_km", pa.float64(), nullable=False),
    pa.field("payment_method", pa.string(), nullable=False),
    pa.field("is_cancelled", pa.bool_(), nullable=False),
])

if __name__ == "__main__":
    print("QuickCart PyArrow Canonical Schema:")
    for field in ORDER_PYARROW_SCHEMA:
        print(f" - {field.name}: {field.type} (nullable={field.nullable})")
