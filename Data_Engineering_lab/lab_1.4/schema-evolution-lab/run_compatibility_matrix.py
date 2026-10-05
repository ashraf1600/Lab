"""
QuickCart Schema Compatibility Matrix & Governance Gate Runner
Executes comprehensive cross-version compatibility tests and generates
the final governance report at results/compatibility_report.json.
"""

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

    # Format Terminal Table with ASCII borders for cross-platform compatibility
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

    # Serialize JSON Report
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
