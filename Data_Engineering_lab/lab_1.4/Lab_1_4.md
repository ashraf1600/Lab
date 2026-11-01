# Schema Evolution and Governance

## 1. Introduction

Imagine you are a data engineer at **QuickCart**, a fast-growing online food delivery platform. Whenever customers place orders, the Ordering Service emits JSON events containing fields like `order_id`, `customer_id`, and `amount` to downstream billing, analytics, and notification services.

As business needs evolve, developers add, remove, or rename event fields. If an upstream service modifies a shared schema contract without coordination, older downstream consumers can crash from missing required keys or unexpected data types.

You will build the following QuickCart schema evolution and governance pipeline:

![Pipeline Architecture](assets/lab_1.4_DE.drawio.svg)

The Order Service publishes JSON events validated against schema contracts. When schema updates occur (adding, removing, or renaming fields), an automated governance check tests compatibility—allowing safe, backward-compatible updates and blocking breaking changes before they reach production.

---

## 2. Objectives

By the end of this lab, you will be able to:

- Define a versioned JSON Schema data contract for order events.
- Build a producer and a consumer that validate events against the contract.
- Add, remove, and rename fields and observe which changes break the consumer.
- Run a compatibility matrix that blocks breaking changes before release.

---

## 3. Project File Structure

The project uses the following structure:

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
├── events/                      # Emitted event payloads (created by the producer)
├── tests/
│   ├── test_add_field.py        # Scenario A: add field
│   ├── test_remove_field.py     # Scenario B: remove field
│   └── test_rename_field.py     # Scenario C: rename field
├── results/
│   └── compatibility_report.json # Compatibility report
├── requirements.txt             # Python dependencies
├── run_compatibility_matrix.py  # Compatibility matrix runner
└── README.md                    # Lab documentation
```

---

## 4. Project Implementation

### Step 1: Set Up the Project and Environment

1. Open your workspace in **VS Code Server**.
2. Open an integrated terminal by clicking **Terminal > New Terminal**.
3. Create the project folder and move into it:
   ```bash
   mkdir -p schema-evolution-lab && cd schema-evolution-lab
   ```
4. Create an isolated Python virtual environment named `.venv`:
   ```bash
   python3 -m venv .venv
   ```
   *(On Windows PowerShell, run: `python -m venv .venv`)*
5. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
   *(On Windows PowerShell, run: `.venv\Scripts\Activate.ps1`)*
6. In the VS Code Explorer, click the **New File** icon to create `requirements.txt`, open it in the editor, and add:
   ```text
   jsonschema>=4.20.0
   pytest>=7.4.0
   tabulate>=0.9.0
   ```
7. Save the file (**File > Save**) and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

![Dependencies Installation](assets/step1_pip_install.png)

8. Using the VS Code Explorer, create the subdirectories: `schemas`, `producer`, `consumer`, `tests`, and `results`.

![Project Directory Structure](assets/step1_project_structure.png)

The Explorer shows the `schema-evolution-lab` workspace with its `.venv` and subfolders. Keeping schema contracts, runtime scripts, and tests in separate folders makes each experiment easy to follow and repeat.

---

### Step 2: Create the Baseline Schema Contract

1. In the VS Code Explorer, navigate to the `schemas/` directory.
2. Right-click the `schemas/` folder, select **New File**, and name it:
   ```text
   order_v1.json
   ```
3. Open `order_v1.json` in the editor and define QuickCart's initial baseline data contract:
   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "title": "QuickCartOrderEventV1",
     "description": "Baseline Order Event Data Contract for QuickCart Platform",
     "type": "object",
     "properties": {
       "order_id": {
         "type": "string",
         "description": "Unique identifier for the order"
       },
       "customer_id": {
         "type": "string",
         "description": "Unique customer reference ID"
       },
       "amount": {
         "type": "number",
         "minimum": 0,
         "description": "Total order amount in BDT"
       },
       "delivery_address": {
         "type": "string",
         "description": "Delivery destination address"
       }
     },
     "required": [
       "order_id",
       "customer_id",
       "amount"
     ],
     "additionalProperties": true
   }
   ```
4. Save the file (**File > Save**).

![Baseline Schema Contract](assets/step2_schema_v1.png)

`schemas/order_v1.json` defines the types and rules for QuickCart order events. The red box highlights the `required` array: `order_id`, `customer_id`, and `amount` must be present in every event, while `delivery_address` is optional. `"additionalProperties": true` lets producers add extra fields without breaking the contract. Both the producer and the consumer validate against this file.

---

### Step 3: Implement and Run the Order Event Producer

1. In the VS Code Explorer, expand the `producer/` folder.
2. Create a new file named:
   ```text
   producer.py
   ```
3. Open `producer.py` in the editor and implement the event generation and contract validation logic:
   ```python
   """
   QuickCart Order Event Producer
   Emits JSON order events according to specified schema contract versions.
   """

   import os
   import json
   from pathlib import Path
   from typing import Dict, Any
   import jsonschema

   BASE_DIR = Path(__file__).resolve().parent.parent
   SCHEMAS_DIR = BASE_DIR / "schemas"
   EVENTS_DIR = BASE_DIR / "events"


   def load_schema(schema_filename: str) -> Dict[str, Any]:
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
       event = {
           "order_id": order_id,
           "customer_id": customer_id,
           "amount": amount,
           "delivery_address": delivery_address,
           "payment_method": payment_method
       }
       schema_file = "order_v2_add.json" if (SCHEMAS_DIR / "order_v2_add.json").exists() else "order_v1.json"
       schema = load_schema(schema_file)
       jsonschema.validate(instance=event, schema=schema)
       return event


   def create_order_event_v2_remove(
       order_id: str = "ORD-003",
       customer_id: str = "CUST-5510",
       delivery_address: str = "Dhanmondi, Dhaka"
   ) -> Dict[str, Any]:
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
       return {
           "order_id": order_id,
           "customer_id": customer_id,
           "total_amount": total_amount,
           "delivery_address": delivery_address
       }


   def emit_event(event: Dict[str, Any], filename: str = "order_event.json") -> Path:
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
   ```
4. Save the file (**File > Save**).
5. In your integrated terminal, execute the producer:
   ```bash
   python producer/producer.py
   ```

![Producer Execution Output](assets/step3_producer_v1.png)

The producer builds a baseline order event for customer `CUST-8842` with an amount of 650.0 BDT. Before emitting it, the script validates the event against `schemas/order_v1.json`. The event has the three required fields (`order_id`, `customer_id`, `amount`) plus the optional `delivery_address`. The red box marks the optional field and the output path: the event is saved to `events/order_v1_live.json` for the consumer to read.

---

### Step 4: Implement and Run the Downstream Consumer

1. In the VS Code Explorer, expand the `consumer/` directory.
2. Create a new file named:
   ```text
   consumer.py
   ```
3. Open `consumer.py` in the editor and add the consumer verification and billing calculations:
   ```python
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
       schema_path = SCHEMAS_DIR / schema_filename
       if not schema_path.exists():
           raise FileNotFoundError(f"Consumer contract schema not found at: {schema_path}")
       with open(schema_path, "r", encoding="utf-8") as f:
           return json.load(f)


   def validate_and_process_event(
       event: Dict[str, Any],
       contract_schema: Dict[str, Any] = None
   ) -> Tuple[bool, str, Dict[str, Any]]:
       if contract_schema is None:
           contract_schema = load_consumer_contract("order_v1.json")

       # Contract Schema Validation
       try:
           jsonschema.validate(instance=event, schema=contract_schema)
       except jsonschema.ValidationError as err:
           return False, f"SCHEMA_CONTRACT_VIOLATION: {err.message} (Path: {list(err.path)})", {}
       except Exception as err:
           return False, f"VALIDATION_ERROR: {str(err)}", {}

       # Application Logic: Field Extraction & Invoice Calculation
       try:
           order_id = event["order_id"]
           customer_id = event["customer_id"]
           amount = event["amount"]
           delivery_address = event.get("delivery_address", "Pickup Station")
           payment_method = event.get("payment_method", "Standard Cash/Card")

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
   ```
4. Save the file (**File > Save**).
5. In your integrated terminal, run the baseline consumer:
   ```bash
   python consumer/consumer.py
   ```

![Consumer Execution Output](assets/step4_consumer_v1.png)

The consumer reads the event created by the producer. The red box shows `Contract Verification: PASSED (order_v1.json)`. The consumer reads the required fields, computes 5% VAT (32.5 BDT), and produces a final invoice of 682.5 BDT with no schema violation or `KeyError`. This is the baseline that the schema changes below are compared against.

---

### Step 5: Add an Optional Field

1. In the VS Code Explorer, open `schemas/` and create:
   ```text
   order_v2_add.json
   ```
2. Add the evolved contract containing the optional `payment_method` attribute:
   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "title": "QuickCartOrderEventV2Add",
     "description": "V2 Schema Evolution: Non-breaking addition of optional payment_method field",
     "type": "object",
     "properties": {
       "order_id": {"type": "string"},
       "customer_id": {"type": "string"},
       "amount": {"type": "number", "minimum": 0},
       "delivery_address": {"type": "string"},
       "payment_method": {
         "type": "string",
         "enum": ["cash_on_delivery", "card", "bKash", "Nagad", "Rocket"],
         "description": "Optional payment method specified by customer"
       }
     },
     "required": ["order_id", "customer_id", "amount"],
     "additionalProperties": true
   }
   ```
3. Save the file (**File > Save**).
4. In the `tests/` folder, create:
   ```text
   test_add_field.py
   ```
5. Implement the compatibility test:
   ```python
   import sys
   import json
   from pathlib import Path

   BASE_DIR = Path(__file__).resolve().parent.parent
   sys.path.insert(0, str(BASE_DIR))

   from producer.producer import create_order_event_v2_add, emit_event
   from consumer.consumer import validate_and_process_event, load_consumer_contract


   def run_add_field_experiment():
       print("=" * 70)
       print(" EXPERIMENT A: Adding Optional Field (order_v2_add -> consumer_v1)")
       print("=" * 70)

       event_v2 = create_order_event_v2_add(
           order_id="ORD-002",
           customer_id="CUST-8842",
           amount=820.0,
           delivery_address="Gulshan-2, Dhaka",
           payment_method="bKash"
       )
       emit_event(event_v2, "order_v2_add.json")

       v1_contract = load_consumer_contract("order_v1.json")
       success, message, result = validate_and_process_event(event_v2, v1_contract)

       print(f"Contract Schema Target: schemas/order_v1.json")
       print(f"Validation Status:      {message}")
       print(f"Is Backward-Compatible: {success}")

       if success:
           print("\n[RESULT] >> PASS: Non-Breaking Change! <<")
           print(f"Billed Invoice Total:   BDT {result.get('final_invoice_bdt')}")
       else:
           print(f"\n[RESULT] >> FAIL: Unexpected rejection: {message} <<")

       print("=" * 70)
       return success


   def test_add_optional_field_is_non_breaking():
       assert run_add_field_experiment() is True


   if __name__ == "__main__":
       sys.exit(0 if run_add_field_experiment() else 1)
   ```
6. Save the file and execute the test:
   ```bash
   python tests/test_add_field.py
   ```

![Scenario A Test Output](assets/step5_add_field_pass.png)

In Experiment A, a V2 producer sends an event with the extra field `payment_method: "bKash"`. The consumer still uses the original `order_v1.json` contract and accepts the event, because all required fields are present and extra fields are allowed. Billing completes normally with a final invoice of BDT 861.0. The red box shows `>> PASS: Non-Breaking Change! <<`: adding an optional field is safe.

---

### Step 6: Remove a Required Field

1. In the VS Code Explorer, open `schemas/` and create:
   ```text
   order_v2_remove.json
   ```
2. Add the schema where `amount` is omitted:
   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "title": "QuickCartOrderEventV2Remove",
     "description": "V2 Schema Evolution: Breaking removal of required 'amount' field",
     "type": "object",
     "properties": {
       "order_id": {"type": "string"},
       "customer_id": {"type": "string"},
       "delivery_address": {"type": "string"}
     },
     "required": ["order_id", "customer_id"],
     "additionalProperties": true
   }
   ```
3. Save the file (**File > Save**).
4. In the `tests/` folder, create:
   ```text
   test_remove_field.py
   ```
5. Implement the test observing contract failure:
   ```python
   import sys
   import json
   from pathlib import Path

   BASE_DIR = Path(__file__).resolve().parent.parent
   sys.path.insert(0, str(BASE_DIR))

   from producer.producer import create_order_event_v2_remove, emit_event
   from consumer.consumer import validate_and_process_event, load_consumer_contract


   def run_remove_field_experiment():
       print("=" * 70)
       print(" EXPERIMENT B: Removing Required Field (order_v2_remove -> consumer_v1)")
       print("=" * 70)

       event_v2 = create_order_event_v2_remove(
           order_id="ORD-003",
           customer_id="CUST-5510",
           delivery_address="Dhanmondi, Dhaka"
       )
       emit_event(event_v2, "order_v2_remove.json")

       v1_contract = load_consumer_contract("order_v1.json")
       success, message, result = validate_and_process_event(event_v2, v1_contract)

       print(f"Contract Schema Target: schemas/order_v1.json")
       print(f"Validation Status:      {message}")
       print(f"Is Backward-Compatible: {success}")

       if not success:
           print("\n[RESULT] >> FAIL: Breaking Change Detected! <<")
           print("Root Cause: The incoming payload is missing the mandatory 'amount' field.")
       else:
           print("\n[RESULT] >> PASS: Unexpectedly accepted incomplete payload! <<")

       print("=" * 70)
       return not success


   def test_remove_required_field_is_breaking():
       assert run_remove_field_experiment() is True


   if __name__ == "__main__":
       sys.exit(0 if run_remove_field_experiment() else 1)
   ```
6. Save the file and run the test in the terminal:
   ```bash
   python tests/test_remove_field.py
   ```

![Scenario B Test Output](assets/step6_remove_field_fail.png)

In Experiment B, the producer sends an event without `amount`. Validation against `schemas/order_v1.json` fails with `SCHEMA_CONTRACT_VIOLATION: 'amount' is a required property`. Billing cannot compute VAT or the invoice without `amount`, so processing stops with `Is Backward-Compatible: False`. The red box shows `>> FAIL: Breaking Change Detected! <<`: removing a required field breaks existing consumers.

---

### Step 7: Rename a Required Field

1. In the VS Code Explorer, open `schemas/` and create:
   ```text
   order_v2_rename.json
   ```
2. Add the schema where `amount` is renamed to `total_amount`:
   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "title": "QuickCartOrderEventV2Rename",
     "description": "V2 Schema Evolution: Breaking field rename of 'amount' to 'total_amount'",
     "type": "object",
     "properties": {
       "order_id": {"type": "string"},
       "customer_id": {"type": "string"},
       "total_amount": {"type": "number", "minimum": 0},
       "delivery_address": {"type": "string"}
     },
     "required": ["order_id", "customer_id", "total_amount"],
     "additionalProperties": true
   }
   ```
3. Save the file (**File > Save**).
4. In the `tests/` folder, create:
   ```text
   test_rename_field.py
   ```
5. Implement the test verifying field rename failure:
   ```python
   import sys
   import json
   from pathlib import Path

   BASE_DIR = Path(__file__).resolve().parent.parent
   sys.path.insert(0, str(BASE_DIR))

   from producer.producer import create_order_event_v2_rename, emit_event
   from consumer.consumer import validate_and_process_event, load_consumer_contract


   def run_rename_field_experiment():
       print("=" * 70)
       print(" EXPERIMENT C: Renaming Field (order_v2_rename -> consumer_v1)")
       print("=" * 70)

       event_v2 = create_order_event_v2_rename(
           order_id="ORD-004",
           customer_id="CUST-3319",
           total_amount=1250.0,
           delivery_address="Banani, Dhaka"
       )
       emit_event(event_v2, "order_v2_rename.json")

       v1_contract = load_consumer_contract("order_v1.json")
       success, message, result = validate_and_process_event(event_v2, v1_contract)

       print(f"Contract Schema Target: schemas/order_v1.json")
       print(f"Validation Status:      {message}")
       print(f"Is Backward-Compatible: {success}")

       if not success:
           print("\n[RESULT] >> FAIL: Breaking Change Detected! <<")
           print("Root Cause: The incoming payload uses 'total_amount', but consumer expects 'amount'.")
       else:
           print("\n[RESULT] >> PASS: Unexpectedly accepted renamed payload! <<")

       print("=" * 70)
       return not success


   def test_rename_field_is_breaking():
       assert run_rename_field_experiment() is True


   if __name__ == "__main__":
       sys.exit(0 if run_rename_field_experiment() else 1)
   ```
6. Save the file and execute the test:
   ```bash
   python tests/test_rename_field.py
   ```

![Scenario C Test Output](assets/step7_rename_field_fail.png)

In Experiment C, the producer renames `amount` to `total_amount`. The meaning is the same, but the consumer contract requires the key `amount`, so validation fails with `SCHEMA_CONTRACT_VIOLATION: 'amount' is a required property`. The red box shows `>> FAIL: Breaking Change Detected! <<`. A rename is a breaking change unless the producer sends both names for a transition period (dual write).

---

### Step 8: Run the Compatibility Matrix

1. In the VS Code Explorer, open the project root directory `schema-evolution-lab/`.
2. Create a new file named:
   ```text
   run_compatibility_matrix.py
   ```
3. Open `run_compatibility_matrix.py` in the editor and add the complete governance gate implementation:
   ```python
   import sys
   import json
   from pathlib import Path
   from datetime import datetime, timezone
   from tabulate import tabulate

   BASE_DIR = Path(__file__).resolve().parent
   sys.path.insert(0, str(BASE_DIR))

   from producer.producer import (
       create_order_event_v1,
       create_order_event_v2_add,
       create_order_event_v2_remove,
       create_order_event_v2_rename
   )
   from consumer.consumer import validate_and_process_event, load_consumer_contract


   def run_full_compatibility_matrix():
       print("=" * 80)
       print(" QUICKCART SCHEMA GOVERNANCE GATE -- COMPATIBILITY TEST MATRIX")
       print("=" * 80)

       v1_contract = load_consumer_contract("order_v1.json")
       results = []

       # Scenario 1: Baseline V1 -> V1
       event_v1 = create_order_event_v1()
       ok_1, msg_1, res_1 = validate_and_process_event(event_v1, v1_contract)
       results.append({
           "test_id": "TEST-01",
           "change_description": "Baseline Contract (No Change)",
           "producer_version": "V1 (Initial)",
           "consumer_version": "V1 (Expected)",
           "result": "PASS" if ok_1 else "FAIL",
           "classification": "Non-Breaking",
           "reason": "Exact schema contract match across producer and consumer.",
           "invoice_total": res_1.get("final_invoice_bdt", "N/A")
       })

       # Scenario 2: Add Optional Field V2 -> V1
       event_v2_add = create_order_event_v2_add()
       ok_2, msg_2, res_2 = validate_and_process_event(event_v2_add, v1_contract)
       results.append({
           "test_id": "TEST-02",
           "change_description": "Add optional field 'payment_method'",
           "producer_version": "V2 (Add Field)",
           "consumer_version": "V1 (Expected)",
           "result": "PASS" if ok_2 else "FAIL",
           "classification": "Non-Breaking",
           "reason": "V1 contract allows open content; optional property ignored by old consumer.",
           "invoice_total": res_2.get("final_invoice_bdt", "N/A")
       })

       # Scenario 3: Remove Required Field V2 -> V1
       event_v2_remove = create_order_event_v2_remove()
       ok_3, msg_3, res_3 = validate_and_process_event(event_v2_remove, v1_contract)
       results.append({
           "test_id": "TEST-03",
           "change_description": "Remove required field 'amount'",
           "producer_version": "V2 (Remove Field)",
           "consumer_version": "V1 (Expected)",
           "result": "PASS" if ok_3 else "FAIL",
           "classification": "Breaking",
           "reason": "Missing mandatory 'amount' property; violates V1 required array.",
           "invoice_total": "N/A (Halted)"
       })

       # Scenario 4: Rename Required Field V2 -> V1
       event_v2_rename = create_order_event_v2_rename()
       ok_4, msg_4, res_4 = validate_and_process_event(event_v2_rename, v1_contract)
       results.append({
           "test_id": "TEST-04",
           "change_description": "Rename field 'amount' -> 'total_amount'",
           "producer_version": "V2 (Rename Field)",
           "consumer_version": "V1 (Expected)",
           "result": "PASS" if ok_4 else "FAIL",
           "classification": "Breaking",
           "reason": "Consumer cannot locate 'amount'; 'total_amount' not recognized as alias.",
           "invoice_total": "N/A (Halted)"
       })

       table_data = []
       for r in results:
           status_tag = "[PASS]" if r['result'] == "PASS" else "[FAIL]"
           table_data.append([
               r["test_id"],
               r["producer_version"],
               r["consumer_version"],
               r["change_description"],
               status_tag,
               r["classification"]
           ])

       headers = ["Test ID", "Producer", "Consumer", "Evolution Change", "Result", "Type"]
       print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))

       report_data = {
           "lab": "Lab 1.4 -- Schema Evolution & Governance",
           "timestamp_utc": datetime.now(timezone.utc).isoformat(),
           "platform": "QuickCart Distributed Event Pipeline",
           "governance_policy": {
               "allowed_changes": ["Add optional field with default/open content"],
               "breaking_changes": ["Remove required field", "Rename required field", "Incompatible type change"]
           },
           "summary": {
               "total_tests": len(results),
               "passed": sum(1 for r in results if r["result"] == "PASS"),
               "failed_breaking": sum(1 for r in results if r["result"] == "FAIL")
           },
           "test_matrix": results
       }

       results_dir = BASE_DIR / "results"
       results_dir.mkdir(parents=True, exist_ok=True)
       report_file = results_dir / "compatibility_report.json"

       with open(report_file, "w", encoding="utf-8") as f:
           json.dump(report_data, f, indent=2)

       print(f"\n[GOVERNANCE] Compatibility report successfully serialized to:")
       print(f"             {report_file}")
       print(f"\n[SUMMARY] Tests Passed: {report_data['summary']['passed']}/{report_data['summary']['total_tests']} | "
             f"Breaking Outages Prevented: {report_data['summary']['failed_breaking']}")
       print("=" * 80)
       return report_file


   if __name__ == "__main__":
       run_full_compatibility_matrix()
   ```
4. Save the file (**File > Save**).
5. In your integrated terminal, execute the automated runner:
   ```bash
   python run_compatibility_matrix.py
   ```

![Compatibility Matrix Output](assets/step8_compatibility_matrix.png)

The matrix runs all four scenarios in one table. `TEST-01` (baseline) and `TEST-02` (add optional `payment_method`) show `[PASS]`, so they are backward compatible. `TEST-03` (remove `amount`) and `TEST-04` (rename `amount` to `total_amount`) show `[FAIL]`, so they are flagged as breaking before deployment. The red box shows the summary: 2 of 4 tests passed and 2 breaking changes were caught. The full results are saved to `results/compatibility_report.json`.

---

## 5. Conclusion

In this lab, you designed versioned JSON schema contracts and tested schema evolution across QuickCart’s event pipeline. You confirmed that adding optional fields preserves backward compatibility while removing or renaming required fields introduces breaking changes, and established an automated compatibility matrix to govern releases and prevent downstream outages.
