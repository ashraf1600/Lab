# Lab 1.5: File Format Comparison — Problem & Resolution Log

This document tracks all technical challenges, platform constraints, benchmarking nuances, and usability issues discovered during the research, implementation, testing, and documentation of **Lab 1.5: File Format Comparison (Parquet, Avro, ORC)**.

---

### Problem 1 — Directory and Path Capitalization Discrepancy
- **Problem:** Existing labs in `Data_Engineering_lab/` use lowercase directory names (`lab_1.1`, `lab_1.2`, `lab_1.3`, `lab_1.4`), whereas the newly scaffolded directory is capitalized as `Lab_1.5/`. Additionally, the prompt refers to both `lab_1.5` and `Lab_1.5`.
- **Location:** `Data_Engineering_lab/Lab_1.5/`
- **Impact:** On Windows the filesystem is case-insensitive, but Linux-based VS Code Server containers and Git enforce strict case sensitivity, which could cause path resolution failures for students.
- **Status:** Fixed
- **Resolution:** Retain the existing directory `Data_Engineering_lab/Lab_1.5/` as the primary workspace container, while documenting clear relative navigation (`cd Data_Engineering_lab/Lab_1.5/file-format-comparison-lab`) so terminal commands succeed reliably on any OS.

---

### Problem 2 — Python Apache ORC Driver Portability on Windows
- **Problem:** Apache ORC support in Python is split between `pyorc` and `pyarrow.orc`. The standalone `pyorc` library relies on C++ bindings (`liborc`) that require Visual Studio C++ build tools on Windows, leading to compilation failures for students installing via pip.
- **Location:** Project dependencies / `requirements.txt`
- **Impact:** Students running VS Code Server on Windows or minimal Linux containers without C++ toolchains cannot install `pyorc`.
- **Status:** Fixed
- **Resolution:** Standardize on `pyarrow.orc` (`pyarrow>=14.0.0`), which bundles precompiled native ORC C++ readers and writers inside the standard cross-platform binary wheel. This eliminates external compiler prerequisites.

---

### Problem 3 — Logical Schema & Data Type Parity Across Formats
- **Problem:** Parquet (columnar), ORC (columnar), and Avro (row-oriented) have distinct type systems. For instance, Avro requires explicit JSON schema specifications with union types for nullable fields (`["null", "string"]`), while PyArrow infers nullability by default. Timestamp precisions also differ (milliseconds vs. microseconds).
- **Location:** `schemas/order_schema.avsc` and `schemas/order_schema.py`
- **Impact:** If data types diverge between formats, file size comparisons and read/write throughput measurements become scientifically invalid.
- **Status:** Fixed
- **Resolution:** Define a canonical schema containing realistic QuickCart business fields (order ID, customer ID, order timestamp, item count, total amount, delivery distance, payment status) and construct exact one-to-one type mappings across PyArrow Schema (Parquet & ORC) and Apache Avro Schema (`.avsc`).

---

### Problem 4 — Confounding Compression Algorithm Defaults
- **Problem:** Each format defaults to a different compression codec: Parquet typically defaults to `snappy`, Apache ORC defaults to `zlib` (or `zstd`), and Apache Avro defaults to uncompressed (`null`). Comparing raw default outputs unfairly skews file size in favor of higher-compression codecs like zlib at the expense of write throughput.
- **Location:** `src/benchmark.py`
- **Impact:** Students might falsely conclude that one format is fundamentally more compact when the difference is solely driven by the compression algorithm.
- **Status:** Fixed
- **Resolution:** Benchmark each format under standardized common compression codec (`snappy`), ensuring a fair comparison across Parquet, Avro, and ORC.

---

### Problem 5 — I/O Benchmark Measurement Noise and Caching
- **Problem:** Measuring execution duration on a single write or read pass produces noisy results caused by OS page caching, disk buffering, and Python module import overhead.
- **Location:** `src/benchmark.py`
- **Impact:** A single benchmark trial can report inconsistent or inverted throughput results between successive executions.
- **Status:** Fixed
- **Resolution:** Implement a multi-iteration benchmark runner that executes a warm-up cycle followed by 5 timed trials per format, computing mean execution times, throughput (records/sec), and compression ratios.

---

### Problem 6 — Pure VS Code Server Workflow Compliance (No `cat` Commands)
- **Problem:** Standard data engineering tutorials frequently instruct users to pipe output or inspect files using terminal `cat` or `head` commands, violating the strict VS Code Server GUI pedagogical standard.
- **Location:** Student guide `Lab_1_5.md`
- **Impact:** Breaks interactive UI immersion and fails the repository's educational standards.
- **Status:** Fixed
- **Resolution:** Direct students to view and inspect schemas, datasets, and benchmark results using the VS Code File Explorer, Editor tabs, and dedicated Python verification CLI scripts.

---

### Problem 7 — FastAvro Snappy Codec Missing Dependency
- **Problem:** When specifying `codec="snappy"` in `fastavro.writer`, FastAvro raises `ValueError: snappy codec is supported but you need to install one of the following libraries: ('cramjam',)` if Snappy decompression bindings are absent.
- **Location:** `src/convert_avro.py` and `requirements.txt`
- **Impact:** Script crashes at runtime when students execute Avro serialization with Snappy compression.
- **Status:** Fixed
- **Resolution:** Added `cramjam>=2.0.0` to `requirements.txt`. Cramjam provides pure Rust precompiled binary wheels for all platforms with zero C++ compilation dependencies.

---

### Problem 8 — Apache ORC C++ Time Zone Database Lookup on Windows
- **Problem:** When writing timestamp columns using `pyarrow.orc.write_table` on Windows, PyArrow's underlying C++ ORC writer fails with `pyarrow.lib.ArrowException: Unknown error: Time zone file /usr/share/zoneinfo/GMT does not exist. Please install IANA time zone database and set TZDIR env.`
- **Location:** `src/convert_orc.py` and `src/benchmark.py`
- **Impact:** Students running on Windows encounter an unhandled crash during ORC serialization.
- **Status:** Fixed
- **Resolution:** Added `tzdata>=2024.1` to `requirements.txt` and dynamically configured `os.environ["TZDIR"] = str(Path(tzdata.__file__).parent / "zoneinfo")` at runtime when `TZDIR` is not set by the operating system.
