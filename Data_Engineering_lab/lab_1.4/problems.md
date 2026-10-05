# Lab 1.4: Schema Evolution & Governance — Problems & Resolutions Log

This document tracks all problems, ambiguities, implementation gaps, environment risks, and student confusion points identified during the analysis and implementation of **Lab 1.4: Schema Evolution & Governance**, along with their respective resolutions.

---

## Problem 1 — Undefined Schema Validation Library & Dependencies
- **Problem**: The R&D document references "required JSON/schema libraries" in Step 1, but does not provide an explicit `requirements.txt` or specify which validation library to use.
- **Where**: `lab_1.4/Lab_1_4_R&D.md`, Section 6 & Section 7 (Step 1).
- **Impact**: Students running `pip install -r requirements.txt` would find an empty file or encounter `ModuleNotFoundError: No module named 'jsonschema'` when running validation scripts.
- **Status**: Resolved.
- **Resolution**: Defined `requirements.txt` containing `jsonschema>=4.20.0`, standardizing on Python's official JSON Schema Draft 2020-12 / Draft 7 implementation for industry-standard validation.

---

## Problem 2 — Missing Complete Executable Implementation Code
- **Problem**: The R&D document provides schema snippets and high-level architectural outlines, but omits complete source code for `producer.py`, `consumer.py`, test scripts, and the compatibility reporting engine.
- **Where**: `lab_1.4/Lab_1_4_R&D.md`, Sections 8–14.
- **Impact**: Without robust, production-grade source code, students would have to guess implementation details, resulting in syntax errors, unhandled exceptions, and irreproducible lab runs.
- **Status**: Resolved.
- **Resolution**: Designed clean, modular, and beginner-to-intermediate friendly Python implementations for `producer.py`, `consumer.py`, each test scenario (`test_add_field.py`, `test_remove_field.py`, `test_rename_field.py`), and an automated runner `run_compatibility_matrix.py` that populates `results/compatibility_report.json`.

---

## Problem 3 — Event Hand-off Mechanism Unspecified
- **Problem**: The R&D document shows `Producer -> JSON Event -> Consumer`, but does not define how events are passed between producer and consumer in a standalone local environment.
- **Where**: `lab_1.4/Lab_1_4_R&D.md`, Section 5 & Section 8.
- **Impact**: Without an explicit hand-off mechanism, students cannot inspect the generated JSON events in VS Code Server.
- **Status**: Resolved.
- **Resolution**: Implemented a transparent, file-based exchange in `events/` (`order_event.json`), paired with direct programmatic interfaces in the test suite. This allows students to physically inspect the event payloads in the VS Code editor while running automated compatibility tests.

---

## Problem 4 — Ambiguity Between Schema Contract Violations vs. Runtime KeyErrors
- **Problem**: When a required field (`amount`) is removed or renamed, failure could manifest either as a formal `jsonschema.ValidationError` (schema contract rejection) or a Python runtime `KeyError` (consumer application crash).
- **Where**: `lab_1.4/Lab_1_4_R&D.md`, Sections 10 & 11.
- **Impact**: If not clearly distinguished, students may confuse application logic crashes with schema contract enforcement.
- **Status**: Resolved.
- **Resolution**: Consumer and tests explicitly decouple the two validation layers: (1) **Contract Validation** against the expected JSON Schema (catches missing required properties upfront), and (2) **Payload Consumption** (safe attribute extraction). Both layers report descriptive error diagnostics explaining why breaking changes cause downstream failures.

---

## Problem 5 — Lack of Automated Compatibility Matrix Runner
- **Problem**: The R&D document requires a compatibility matrix table (Step 13) and a JSON report (Step 15), but outlines running tests disjointedly without a unified reporting mechanism.
- **Where**: `lab_1.4/Lab_1_4_R&D.md`, Sections 12 & 14.
- **Impact**: Fragmented execution makes generating `results/compatibility_report.json` prone to omission and manual errors.
- **Status**: Resolved.
- **Resolution**: Created `run_compatibility_matrix.py` in addition to individual test files. It executes all four permutations (V1-to-V1, V2_add-to-V1, V2_remove-to-V1, V2_rename-to-V1), prints an ASCII matrix to the terminal, and serializes the structured JSON report to `results/compatibility_report.json`.

---

## Problem 6 — Missing Rendered Architecture Diagram Asset
- **Problem**: The R&D document only includes an ASCII text diagram for the QuickCart order event pipeline, missing a visual architecture asset for student-facing documentation.
- **Where**: `lab_1.4/Lab_1_4_R&D.md`, Section 5.
- **Impact**: The student guide would lack the visual polish and diagrammatic consistency present in Labs 1.1, 1.2, and 1.3.
- **Status**: Resolved.
- **Resolution**: Created an SVG architecture diagram (`assets/schema_evolution_architecture.svg`) depicting the QuickCart producer, event payload, consumer validation boundary, and breaking vs. non-breaking evolution paths.

---

## Problem 7 — Reliance on `cat` Commands and Terminal File Generation
- **Problem**: Typical lab guides often rely on `cat <<EOF` terminal commands to generate files, which can cause copy-paste quoting issues and bypasses VS Code Server UI features.
- **Where**: Student execution instructions across all steps.
- **Impact**: Violates guideline requirements; causes confusion for beginner/intermediate learners using VS Code Server.
- **Status**: Resolved.
- **Resolution**: All student instructions strictly guide file creation and editing via VS Code Server UI (File > New File, Explorer right-click, saving in editor), using the terminal strictly for execution (`python`, `pip`).

---

## Problem 8 — Windows Terminal Encoding Conflict with Unicode Table Borders
- **Problem**: When executing `tabulate(tablefmt="fancy_grid")` with Unicode box-drawing characters (`+---`, `✓`, `✗`) on Windows terminals configured for code page 1252 (`cp1252`), Python threw an unhandled `UnicodeEncodeError`.
- **Where**: `run_compatibility_matrix.py`, line 103.
- **Impact**: Windows and PowerShell students would experience test runner crashes before the compatibility report was serialized.
- **Status**: Resolved.
- **Resolution**: Standardized on clean ASCII table borders (`tablefmt="grid"`) and plain text status tags (`[PASS]`, `[FAIL]`), ensuring 100% reliable cross-platform execution on Linux VS Code Server, macOS, and Windows.
