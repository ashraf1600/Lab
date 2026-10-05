"""
Test Scenario A: Schema Evolution — Adding an Optional Field (Non-Breaking)
Tests whether an upgraded V2 producer sending 'payment_method' can be safely
consumed by an existing V1 consumer without contract failure.
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from producer.producer import create_order_event_v2_add, emit_event
from consumer.consumer import validate_and_process_event, load_consumer_contract


def run_add_field_experiment():
    print("=" * 70)
    print(" EXPERIMENT A: Adding Optional Field (order_v2_add -> consumer_v1)")
    print("=" * 70)

    # 1. Producer generates event with added optional field
    event_v2 = create_order_event_v2_add(
        order_id="ORD-002",
        customer_id="CUST-8842",
        amount=820.0,
        delivery_address="Gulshan-2, Dhaka",
        payment_method="bKash"
    )
    emit_event(event_v2, "order_v2_add.json")

    print("\n[PRODUCER V2] Emitted order event with added field 'payment_method':")
    print(json.dumps(event_v2, indent=2))

    # 2. Existing V1 consumer evaluates the incoming V2 event
    v1_contract = load_consumer_contract("order_v1.json")
    success, message, result = validate_and_process_event(event_v2, v1_contract)

    print("\n[CONSUMER V1 EVALUATION]")
    print(f"Contract Schema Target: schemas/order_v1.json")
    print(f"Validation Status:      {message}")
    print(f"Is Backward-Compatible: {success}")

    if success:
        print("\n[RESULT] >> PASS: Non-Breaking Change! <<")
        print("Explanation: The V1 consumer processed all expected fields successfully.")
        print(f"Billed Invoice Total:   BDT {result.get('final_invoice_bdt')}")
        print(f"Auxiliary Field Status: Handled gracefully without crash.")
    else:
        print(f"\n[RESULT] >> FAIL: Unexpected rejection: {message} <<")

    print("=" * 70)
    return success


def test_add_optional_field_is_non_breaking():
    """Pytest test case for automated CI validation."""
    assert run_add_field_experiment() is True


if __name__ == "__main__":
    success = run_add_field_experiment()
    sys.exit(0 if success else 1)
