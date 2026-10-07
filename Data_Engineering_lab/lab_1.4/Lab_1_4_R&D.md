# Lab 1.4 — Schema Evolution & Governance

**Level:** Intermediate  
**Type:** Standalone  
**Objective:** Add, remove, and rename fields in a JSON schema and observe breaking vs non-breaking changes between a producer and consumer.

---

## 1. Introduction

### 1.1 Real-Life Scenario

Imagine you are a data engineer at **QuickCart**, an online food delivery platform. Whenever customers place orders, the ordering service emits JSON events to downstream billing, delivery tracking, and analytics services.

As business needs evolve, developers add, remove, or rename event fields. Uncoordinated modifications can break downstream consumers that depend on the original contract. In this lab, you will simulate schema updates to observe **non-breaking** versus **breaking** changes and apply schema-governance rules to prevent production outages.

---

## 2. Lab Objective

By completing this lab, you will:

- Understand JSON schemas and data contracts.
- Create a producer that generates JSON order events.
- Create a consumer that reads and validates order events.
- Establish an initial schema version.
- Add a field and observe a non-breaking change.
- Remove a required field and observe a breaking change.
- Rename a field and observe a breaking change.
- Test producer/consumer compatibility.
- Understand basic schema governance and versioning.

---

## 3. What Is Schema Evolution?

**Schema evolution** means changing the structure of data over time while producers and consumers continue exchanging that data.

Initial event:

```json
{
  "order_id": "ORD001",
  "customer_id": "C001",
  "amount": 650
}
```

Later:

```json
{
  "order_id": "ORD001",
  "customer_id": "C001",
  "amount": 650,
  "payment_method": "card"
}
```

Adding an optional field can be safe because an older consumer may simply ignore it.

However, changing:

```text
amount
```

to:

```text
total_amount
```

can break an older consumer that still expects `amount`.

---

## 4. Breaking vs Non-Breaking Changes

### Non-Breaking

An existing consumer can continue processing the event.

```text
V1:
order_id
customer_id
amount

        ↓ add optional field

V2:
order_id
customer_id
amount
payment_method
```

### Breaking

An existing consumer can no longer process the event correctly.

```text
V1:
amount

        ↓ rename

V2:
total_amount
```

The old consumer still searches for `amount`.

---

# 5. Architecture

```text
                 QUICKCART ORDER EVENT PIPELINE

        ┌──────────────┐
        │ JSON Schema  │
        │    V1        │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │   Producer   │
        │ Create Event │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │  JSON Event  │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │   Consumer   │
        │ Read/Validate│
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Compatibility│
        │    Tests     │
        └──────┬───────┘
               │
       ┌───────┼────────┐
       ▼       ▼        ▼
      Add    Remove    Rename
     Field    Field     Field
       │       │        │
       ▼       ▼        ▼
      Safe*   Break     Break
```

> *Adding a field is non-breaking when it is optional and the compatibility policy permits it.

---

## 6. Project File Structure

```text
schema-evolution-lab/
│
├── schemas/
│   ├── order_v1.json
│   ├── order_v2_add.json
│   ├── order_v2_remove.json
│   └── order_v2_rename.json
│
├── producer/
│   └── producer.py
│
├── consumer/
│   └── consumer.py
│
├── tests/
│   ├── test_add_field.py
│   ├── test_remove_field.py
│   └── test_rename_field.py
│
├── results/
│   └── compatibility_report.json
│
├── requirements.txt
└── README.md
```

---

# 7. Project Implementation

## Step 1 — Verify the Working Environment

Open the project in **VS Code Server** and verify Python and the required JSON/schema libraries.

**Show Image**

> VS Code Server will be the main development environment for the lab. Python will generate JSON events, validate schemas, and run compatibility tests. Keeping all components in one workspace makes the schema versions and test results easy to manage.

---

## Step 2 — Create the Project Structure

Create the folders and files using the VS Code Server file explorer.

**Show Image**

> The project separates schemas, producer code, consumer code, and tests. Multiple schema files allow us to preserve the original version while testing different evolution scenarios. This structure also makes the compatibility experiments easy to follow.

---

# 8. Create the Initial Schema

## Step 3 — Create `order_v1.json`

The initial schema contains:

```text
order_id
customer_id
amount
delivery_address
```

Example:

```json
{
  "type": "object",
  "properties": {
    "order_id": {"type": "string"},
    "customer_id": {"type": "string"},
    "amount": {"type": "number"},
    "delivery_address": {"type": "string"}
  },
  "required": ["order_id", "customer_id", "amount"]
}
```

**Show Image**

> This is the original contract between the QuickCart producer and consumer. The producer must generate events that follow this structure, while the consumer expects these fields. We keep this version unchanged as the baseline for every later compatibility test.

---

## Step 4 — Create the Producer

Create:

```text
producer/producer.py
```

Example event:

```json
{
  "order_id": "ORD001",
  "customer_id": "C001",
  "amount": 650,
  "delivery_address": "Chattogram"
}
```

**Show Image**

> The producer represents the QuickCart service that creates order events. It follows schema version 1 and sends the expected fields to downstream systems. This establishes a working producer-consumer contract before we introduce schema changes.

---

## Step 5 — Create the Consumer

Create:

```text
consumer/consumer.py
```

The consumer should read and use:

```text
order_id
customer_id
amount
```

**Show Image**

> The consumer represents a downstream service that depends on the order event structure. It expects the fields defined in version 1. The initial producer and consumer should work successfully because they follow the same schema contract.

---

## Step 6 — Run the Baseline Test

Run the producer and consumer using schema version 1.

**Show Image**

> The baseline test confirms that the original schema works correctly. The producer generates a valid event and the consumer successfully reads the expected fields. This successful state becomes our reference point for the schema-evolution experiments.

---

# 9. Schema Evolution — Adding a Field

## Step 7 — Add an Optional Field

Create:

```text
schemas/order_v2_add.json
```

Add:

```text
payment_method
```

Example:

```json
{
  "order_id": "ORD001",
  "customer_id": "C001",
  "amount": 650,
  "delivery_address": "Chattogram",
  "payment_method": "card"
}
```

**Show Image**

> The producer now sends an additional `payment_method` field. Existing consumers that only use the original fields can continue processing the event if the new field is optional. This demonstrates a common non-breaking schema-evolution pattern.

---

## Step 8 — Test the Add-Field Change

Run the new producer event against the existing consumer.

**Show Image**

> The consumer continues reading the fields it already understands and can ignore the additional field. Because no existing required field was removed or renamed, the original consumer can continue operating. This is an example of a potentially non-breaking change.

---

# 10. Schema Evolution — Removing a Field

## Step 9 — Remove the `amount` Field

Create:

```text
schemas/order_v2_remove.json
```

Remove:

```text
amount
```

**Show Image**

> The `amount` field is required by the existing consumer. Removing it changes the event contract in a way that the old consumer cannot handle. This experiment demonstrates why removing required fields from shared schemas can be dangerous.

---

## Step 10 — Test the Removed Field

Run the modified producer with the original consumer.

**Show Image**

> The consumer attempts to read `amount`, but the new event no longer contains it. The validation or processing step should therefore report a compatibility error or fail. This demonstrates a breaking schema change from the perspective of the existing consumer.

---

# 11. Schema Evolution — Renaming a Field

## Step 11 — Rename `amount` to `total_amount`

Create:

```text
schemas/order_v2_rename.json
```

Change:

```text
amount
```

to:

```text
total_amount
```

**Show Image**

> Renaming a field changes the event contract even though the actual value may have the same meaning. The existing consumer still searches for `amount`, while the new producer sends `total_amount`. Therefore, the old consumer can no longer reliably process the new event.

---

## Step 12 — Test the Renamed Field

Run the renamed schema with the old consumer.

**Show Image**

> The old consumer cannot find the field it expects because the producer now uses a different field name. The test should show a validation or processing failure. This demonstrates why field renaming must be handled carefully in shared data contracts.

---

# 12. Compatibility Test Matrix

## Step 13 — Test Producer and Consumer Combinations

| Producer | Consumer | Expected Result |
|---|---|---|
| V1 | V1 | PASS |
| Add Field | V1 | PASS* |
| Remove Field | V1 | FAIL |
| Rename Field | V1 | FAIL |

> *The add-field case is non-breaking when the added field is optional and the compatibility policy allows it.

**Show Image**

> The compatibility matrix summarizes the effect of each schema change. The original producer-consumer pair works normally, while removing or renaming an expected field causes compatibility problems. The add-field case shows how optional additions can allow different versions to coexist.

---

# 13. Schema Governance

## Step 14 — Define Compatibility Rules

For this lab:

```text
Allowed:
✓ Add optional field

Breaking:
✗ Remove required field
✗ Rename required field
✗ Incompatible type change
```

**Show Image**

> Schema governance defines rules for how shared data contracts can change. Without governance, one team may modify an event while another team is still using the old structure. A compatibility policy reduces this risk by identifying safe and unsafe changes before deployment.

---

# 14. Generate the Compatibility Report

## Step 15 — Create the Final Report

Generate:

```text
results/compatibility_report.json
```

The report should contain:

```text
Change
Producer Version
Consumer Version
Result
Breaking / Non-Breaking
Reason
```

Example:

```json
{
  "change": "Add payment_method",
  "result": "PASS",
  "type": "Non-Breaking"
}
```

**Show Image**

> The final report summarizes all schema-evolution tests. It records which changes were accepted and which caused compatibility problems. This simple report represents the foundation of automated schema governance in a real data platform.

---

# 15. Final Comparison

| Schema Change | Example | Result |
|---|---|---|
| Add optional field | `payment_method` | Usually non-breaking |
| Remove required field | Remove `amount` | Breaking |
| Rename field | `amount` → `total_amount` | Breaking |
| Change type | `amount: number` → `amount: string` | Potentially breaking |

---

# 16. Key Concept

The most important idea is:

```text
Producer
   ↓
JSON Schema / Contract
   ↓
Consumer
```

The producer and consumer must agree on the structure of the data.

When the schema evolves:

```text
Old Producer → Old Consumer     ✓
New Producer → Old Consumer     ?
New Producer → New Consumer     ✓
```

The `?` is where compatibility testing becomes important.

---

# 17. Why Schema Governance Matters

Without governance:

```text
Team A
  ↓
Changes JSON
  ↓
Production
  ↓
Team B Consumer
  ↓
ERROR
```

With governance:

```text
Schema Change
      ↓
Compatibility Check
      ↓
PASS / FAIL
      ↓
Safe Deployment
```

Schema governance is therefore important in event-driven systems, APIs, data pipelines, and microservices where producers and consumers evolve independently.

---

# 18. Conclusion

In this lab, we created a versioned JSON order-event contract and used a producer-consumer setup to simulate schema evolution. We tested adding, removing, and renaming fields and observed that optional additions can often remain compatible, while removing or renaming required fields can break existing consumers. The experiments demonstrated why producers and consumers must be coordinated when shared data contracts change. A schema compatibility policy provides a practical way to prevent unsafe changes from reaching production. Therefore, schema evolution and governance are essential for maintaining reliable data pipelines as systems and teams grow.
