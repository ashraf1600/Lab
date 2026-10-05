"""
QuickCart Order Event Producer
Emits JSON order events according to specified schema contract versions.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import jsonschema

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = BASE_DIR / "schemas"
EVENTS_DIR = BASE_DIR / "events"


def load_schema(schema_filename: str) -> Dict[str, Any]:
    """Load JSON schema from the schemas directory."""
    schema_path = SCHEMAS_DIR / schema_filename
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found at: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_order_event_v1(
    order_id: str = "ORD-001",
    customer_id: str = "CUST-8842",
    amount: float = 650.0,
    delivery_address: str = "Chattogram, Bangladesh"
) -> Dict[str, Any]:
    """
    Generate a baseline V1 order event.
    Mandatory: order_id, customer_id, amount.
    Optional: delivery_address.
    """
    event = {
        "order_id": order_id,
        "customer_id": customer_id,
        "amount": amount,
        "delivery_address": delivery_address
    }
    schema = load_schema("order_v1.json")
    jsonschema.validate(instance=event, schema=schema)
    return event


def create_order_event_v2_add(
    order_id: str = "ORD-002",
    customer_id: str = "CUST-8842",
    amount: float = 820.0,
    delivery_address: str = "Gulshan-2, Dhaka",
    payment_method: str = "bKash"
) -> Dict[str, Any]:
    """
    Generate V2 order event with added optional field: payment_method.
    """
    event = {
        "order_id": order_id,
        "customer_id": customer_id,
        "amount": amount,
        "delivery_address": delivery_address,
        "payment_method": payment_method
    }
    # Validate against v2_add if exists, or v1 (which allows additional properties)
    schema_file = "order_v2_add.json" if (SCHEMAS_DIR / "order_v2_add.json").exists() else "order_v1.json"
    schema = load_schema(schema_file)
    jsonschema.validate(instance=event, schema=schema)
    return event


def create_order_event_v2_remove(
    order_id: str = "ORD-003",
    customer_id: str = "CUST-5510",
    delivery_address: str = "Dhanmondi, Dhaka"
) -> Dict[str, Any]:
    """
    Generate V2 order event where required field 'amount' is removed.
    """
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "delivery_address": delivery_address
    }


def create_order_event_v2_rename(
    order_id: str = "ORD-004",
    customer_id: str = "CUST-3319",
    total_amount: float = 1250.0,
    delivery_address: str = "Banani, Dhaka"
) -> Dict[str, Any]:
    """
    Generate V2 order event where 'amount' is renamed to 'total_amount'.
    """
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "total_amount": total_amount,
        "delivery_address": delivery_address
    }


def emit_event(event: Dict[str, Any], filename: str = "order_event.json") -> Path:
    """Persist generated event to the events directory for consumer pickup."""
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVENTS_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2)
    return out_path


if __name__ == "__main__":
    print("=" * 60)
    print(" QuickCart Order Event Producer (Baseline V1)")
    print("=" * 60)
    
    event_v1 = create_order_event_v1()
    saved_path = emit_event(event_v1, "order_v1_live.json")
    
    print("\n[PRODUCER] Successfully generated and validated V1 order event:")
    print(json.dumps(event_v1, indent=2))
    print(f"\n[PRODUCER] Event published to: {saved_path}")
    print("=" * 60)
