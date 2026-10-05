"""
QuickCart Order Event Consumer
Validates incoming events against baseline V1 schema contract and executes downstream processing.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import jsonschema

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = BASE_DIR / "schemas"
EVENTS_DIR = BASE_DIR / "events"


def load_consumer_contract(schema_filename: str = "order_v1.json") -> Dict[str, Any]:
    """Load the consumer's expected baseline JSON Schema contract."""
    schema_path = SCHEMAS_DIR / schema_filename
    if not schema_path.exists():
        raise FileNotFoundError(f"Consumer contract schema not found at: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_and_process_event(
    event: Dict[str, Any],
    contract_schema: Dict[str, Any] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate incoming event against consumer contract and execute processing logic.
    Returns: (is_success, status_message, processed_details)
    """
    if contract_schema is None:
        contract_schema = load_consumer_contract("order_v1.json")

    # Step 1: Formal Schema Contract Validation
    try:
        jsonschema.validate(instance=event, schema=contract_schema)
    except jsonschema.ValidationError as err:
        return False, f"SCHEMA_CONTRACT_VIOLATION: {err.message} (Path: {list(err.path)})", {}
    except Exception as err:
        return False, f"VALIDATION_ERROR: {str(err)}", {}

    # Step 2: Downstream Application Consumption (Billing & Fulfillment)
    try:
        order_id = event["order_id"]
        customer_id = event["customer_id"]
        amount = event["amount"]
        delivery_address = event.get("delivery_address", "Pickup Station")
        
        # Auxiliary fields ignored or utilized if present
        payment_method = event.get("payment_method", "Standard Cash/Card")

        # Business Logic: Tax (5%) and invoice total
        vat_tax = round(amount * 0.05, 2)
        final_invoice_total = round(amount + vat_tax, 2)

        processed_details = {
            "order_id": order_id,
            "customer_id": customer_id,
            "subtotal_bdt": amount,
            "vat_tax_bdt": vat_tax,
            "final_invoice_bdt": final_invoice_total,
            "delivery_address": delivery_address,
            "payment_method": payment_method,
            "status": "BILLED_AND_DISPATCHED"
        }
        return True, "SUCCESS_PROCESSED", processed_details

    except KeyError as err:
        return False, f"APPLICATION_KEY_ERROR: Missing required field '{err.args[0]}' in payload", {}


def consume_event_from_file(event_filename: str = "order_v1_live.json") -> Tuple[bool, str, Dict[str, Any]]:
    """Read and process an event file from the events directory."""
    event_path = EVENTS_DIR / event_filename
    if not event_path.exists():
        raise FileNotFoundError(f"Event file not found at: {event_path}. Run producer first.")
    
    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)
    
    return validate_and_process_event(event)


if __name__ == "__main__":
    print("=" * 65)
    print(" QuickCart Downstream Order Consumer (V1 Contract)")
    print("=" * 65)
    
    event_file = "order_v1_live.json"
    print(f"\n[CONSUMER] Reading event payload from: events/{event_file}")
    
    success, message, result = consume_event_from_file(event_file)
    
    if success:
        print("\n[CONSUMER] Contract Verification: PASSED (order_v1.json)")
        print("[CONSUMER] Downstream Billing & Fulfillment Processed Successfully:")
        print(json.dumps(result, indent=2))
    else:
        print(f"\n[CONSUMER] Processing FAILED: {message}")
    
    print("=" * 65)
