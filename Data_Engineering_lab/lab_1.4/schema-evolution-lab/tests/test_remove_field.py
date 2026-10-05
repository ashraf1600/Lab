"""
Test Scenario B: Schema Evolution — Removing a Required Field (Breaking Change)
Tests what occurs when an upstream service removes the required 'amount' field
while the downstream consumer still expects it.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from producer.producer import create_order_event_v2_remove, emit_event
from consumer.consumer import validate_and_process_event, load_consumer_contract


def run_remove_field_experiment():
    print("=" * 70)
    print(" EXPERIMENT B: Removing Required Field (order_v2_remove -> consumer_v1)")
    print("=" * 70)

    # 1. Producer generates event without 'amount'
    event_v2 = create_order_event_v2_remove(
        order_id="ORD-003",
        customer_id="CUST-5510",
        delivery_address="Dhanmondi, Dhaka"
    )
    emit_event(event_v2, "order_v2_remove.json")

    print("\n[PRODUCER V2] Emitted order event (omitted required field 'amount'):")
    print(json.dumps(event_v2, indent=2))

    # 2. Existing V1 consumer attempts to validate and process
    v1_contract = load_consumer_contract("order_v1.json")
    success, message, result = validate_and_process_event(event_v2, v1_contract)

    print("\n[CONSUMER V1 EVALUATION]")
    print(f"Contract Schema Target: schemas/order_v1.json")
    print(f"Validation Status:      {message}")
    print(f"Is Backward-Compatible: {success}")

    if not success:
        print("\n[RESULT] >> FAIL: Breaking Change Detected! <<")
        print("Root Cause: The incoming payload is missing the mandatory 'amount' field.")
        print("Downstream Impact: Billing Service cannot calculate invoices; pipeline halted.")
    else:
        print("\n[RESULT] >> PASS: Unexpectedly accepted incomplete payload! <<")

    print("=" * 70)
    # Return True if breaking behavior is correctly identified and caught
    return not success


def test_remove_required_field_is_breaking():
    """Pytest test case verifying breaking change is detected."""
    assert run_remove_field_experiment() is True


if __name__ == "__main__":
    is_breaking_caught = run_remove_field_experiment()
    # Exit with code 0 since the expected outcome is successfully detecting the break
    sys.exit(0 if is_breaking_caught else 1)
