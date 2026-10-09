# Lab 1.5 — File Format Comparison
## Research, Implementation, Problem Tracking & Screenshot-Guided Documentation

You are working inside my existing lab repository. Your task is to research, implement, test, and document **Lab 1.5: File Format Comparison**.

The lab specification is:

- **Level:** Intermediate
- **Type:** Standalone
- **Objective:** Write the same dataset in Parquet, Avro, and ORC formats, then compare file size, read/write speed, and schema support.

The final lab must be reproducible by a student using **VS Code Server**, following the documentation and screenshots step by step.

## 1. Read the R&D Document First

Before writing code, locate and read the entire file:

`lab_1.5/Lab_1_5_R&D.md`

Read it completely, not just the beginning or a summary.

If the file is missing, inspect the repository and report that fact. Do not silently substitute another lab's R&D document.

Extract the actual requirements, including:
- Learning objectives
- Real-life scenario
- Architecture
- Dataset requirements
- Required technologies and dependencies
- File-format implementation
- Benchmarking methodology
- Expected outputs
- Schema comparison requirements
- Validation criteria
- Student environment constraints

Treat the Lab 1.5 R&D document as the source of truth.

**Do not read `lab_1.4/Lab_1_4_R&D.md` as the primary specification for this task.** This is Lab 1.5. Only consult Lab 1.4 if you need to reuse the established documentation style.

## 2. Inspect the Existing Repository

Before changing anything:
1. Inspect the existing `lab_1.5` directory and relevant repository conventions.
2. Identify reusable setup instructions, documentation templates, and screenshot conventions.
3. Check whether any implementation already exists.
4. Preserve useful existing work.
5. Avoid overwriting unrelated files or other labs.

## 3. Create `problems.md`

Create or update:

`lab_1.5/problems.md`

This file must primarily be a concise list of problems discovered during research, implementation, testing, and documentation.

For each issue, use:

### Problem 1 — Short title
- **Problem:** What is wrong, missing, ambiguous, or risky?
- **Location:** File, step, or component.
- **Impact:** Why does it matter to the lab or student?
- **Status:** Open / Fixed / Accepted limitation.
- **Resolution:** Include only if applicable.

Track issues such as:
- Missing or incompatible dependencies
- Incorrect file paths or commands
- Dataset inconsistencies
- Invalid or unsupported data types
- Schema preservation differences
- Unfair benchmarking methodology
- Memory usage problems
- Missing validation
- Platform-specific setup problems
- Misleading results or assumptions
- Documentation gaps
- Student confusion points
- Screenshot gaps

Keep each issue concise. Do not turn `problems.md` into a long tutorial.

Do not invent problems. Record only issues actually discovered, plus clearly labelled risks or unresolved ambiguities.

If a problem is fixed, keep the record and mark it Fixed with a short resolution.

## 4. Improve the Lab Where Necessary

You may improve code quality, file organization, error handling, benchmarking reliability, reproducibility, explanations, and student instructions.

Do not change the core objective.

Keep the lab focused on comparing **Parquet, Avro, and ORC** using the same logical dataset.

Do not introduce unnecessary technologies or services.

Explain any technical decisions that materially affect the results.

## 5. Implement the Actual Lab

Implement the lab according to the R&D document.

The implementation should include, where required:

- A clearly defined dataset
- A consistent logical schema
- Writing the same dataset to Parquet, Avro, and ORC
- Reading the resulting files
- Validating record counts and values
- Measuring file sizes
- Measuring write time
- Measuring read time
- Comparing schema and data-type support
- Saving benchmark results in a machine-readable format
- Generating a clear final comparison

Use suitable libraries and compatible versions. Document the exact dependencies and installation procedure.

### Benchmarking rules

Make the comparison fair and reproducible:

1. Use the same logical records and equivalent data types for all three formats.
2. Keep the dataset-generation process consistent.
3. Measure write and read operations separately.
4. Use the same hardware and environment for each format.
5. Document dataset size, record count, and relevant settings.
6. Distinguish file size from in-memory data size.
7. Avoid presenting a single noisy timing measurement as definitive.
8. If practical, perform multiple runs and report a sensible summary.
9. Ensure results are actually measured, never fabricated.
10. Explain that compression settings, libraries, data types, and workload can affect results.

Do not claim that one format is universally best. Interpret the measured results in the context of the chosen dataset and workload.

## 6. VS Code Server Is the Required Student Workflow

Students must be able to complete the lab using VS Code Server.

They should use:
- VS Code Explorer to inspect and create files
- The editor to modify code and configuration
- The integrated terminal to execute commands
- The terminal and generated result files to verify outcomes

Do not use `cat` commands in student-facing instructions.

Do not require Jupyter Notebook unless the R&D document explicitly requires it. Prefer normal source files and a terminal-based workflow when appropriate.

Do not assume a particular operating system unless the repository or R&D document specifies one. Document any platform-specific steps clearly.

## 7. Create the Student Documentation

Create or update:

`lab_1.5/Lab_1_5.md`

Follow this structure, adapting it to the R&D requirements:

1. Introduction
2. Real-life storytelling scenario
3. Problem statement
4. Architecture diagram
5. Architecture explanation
6. Project file structure
7. Prerequisites
8. Environment setup
9. Dataset and schema
10. Implementation
11. Validation
12. Benchmarking methodology
13. Results and comparison
14. Interpretation and trade-offs
15. Troubleshooting
16. Conclusion

### Storytelling requirement

Start with one realistic scenario, such as a data engineering team at a delivery platform that needs to choose a storage format for order data.

Keep the same scenario throughout the lab, from the Introduction through the Conclusion.

Do not introduce unrelated scenarios halfway through.

Explain technical concepts in clear, student-friendly language appropriate for an intermediate lab.

## 8. Screenshot-Driven Workflow — Mandatory

**Do not implement the entire lab before asking for screenshots.**

We will create the implementation and documentation progressively.

For every important milestone:

1. Implement the current milestone only.
2. Run the relevant verification.
3. Update the implementation or documentation as needed.
4. Identify the exact VS Code screen that should be captured.
5. Stop and ask me for that screenshot.
6. Wait for me to upload it.
7. Save or copy the uploaded screenshot into the appropriate project `images/` directory.
8. Embed the actual screenshot in `Lab_1_5.md` using a relative path.
9. Add a useful caption and a 3–4 sentence explanation.
10. Continue to the next milestone only after the screenshot has been processed.

Never skip a screenshot checkpoint or pretend that a screenshot was supplied.

Do not ask me to upload all screenshots at once.

## 9. Screenshot Format in `Lab_1_5.md`

Each important implementation step must follow this pattern:

### Step X — Clear Step Name

**What we are doing**

Briefly explain the task.

**Show Image**

Embed the actual screenshot I provide.

Example Markdown:

`![Step 3 — Dataset schema in VS Code](images/step-03-dataset-schema.png)`

*Figure 3: The dataset schema opened in VS Code Server.*

**Explanation**

Write 3–4 meaningful sentences that explain:
- What the screenshot shows
- What was done
- Why this step matters
- What the student should verify or learn

The explanation must accurately describe the actual screenshot and implementation. Do not use generic filler text.

## 10. Screenshot Naming and Quality

Store screenshots under:

`lab_1.5/images/`

Use consistent filenames, for example:

- `step-01-environment.png`
- `step-02-project-structure.png`
- `step-03-dataset-schema.png`
- `step-04-parquet-write.png`
- `step-05-avro-write.png`
- `step-06-orc-write.png`
- `step-07-validation.png`
- `step-08-benchmark-results.png`

Adjust the names to match the actual workflow.

When asking me for a screenshot, specify:
- Which file should be open
- Whether the VS Code Explorer should be visible
- Which terminal/output must be visible
- Which successful result must be readable
- Whether one screenshot is sufficient or multiple views are necessary

Request screenshots only when they help students reproduce or verify the lab. Avoid screenshots for trivial actions.

## 11. Screenshot Checkpoint Interaction

After completing and verifying a milestone, give me a concise instruction like:

**Step 1 is complete. Take Screenshot 1 now.**

Capture the VS Code Server window showing:
- The relevant project files in Explorer
- The appropriate source file or terminal
- The verified output

Make sure all important text is readable.

Upload the screenshot here.

**STOP. Do not proceed to Step 2 until I provide the screenshot.**

After I upload it:
- Confirm what the screenshot demonstrates.
- Save it in the project's `images/` directory.
- Embed it into `Lab_1_5.md`.
- Add the caption and 3–4 sentence explanation.
- Verify the image path.
- Then proceed to the next implementation milestone and request the next screenshot.

## 12. Suggested Implementation Milestones

Adapt these to the R&D document. Do not blindly follow them if the actual requirements differ.

- Milestone 1: Inspect R&D requirements, repository, and environment
- Milestone 2: Create the project structure and dependency files
- Milestone 3: Define and validate the common dataset/schema
- Milestone 4: Implement Parquet writing and reading
- Milestone 5: Implement Avro writing and reading
- Milestone 6: Implement ORC writing and reading
- Milestone 7: Validate record counts, values, and schema behavior
- Milestone 8: Benchmark file sizes and read/write times
- Milestone 9: Generate the final comparison report
- Milestone 10: Verify the complete student workflow and documentation

For each milestone, take only the screenshots that genuinely help a student follow the lab.

## 13. Do Not Fabricate Results

Never invent:
- Benchmark timings
- File sizes
- Successful installation output
- Test results
- Dataset record counts
- Schema behavior
- File paths
- Dependency versions
- Screenshot contents

If something fails:
1. Diagnose it.
2. Record it in `problems.md`.
3. Fix it if appropriate.
4. Rerun the relevant test.
5. Document only verified results.

Clearly label illustrative examples as examples, not actual benchmark results.

## 14. Final Validation

Before declaring the lab complete, verify:

- The R&D document's requirements are satisfied.
- A fresh setup is documented.
- All required dependencies are listed.
- All three formats can be written and read.
- The same logical dataset is used for all formats.
- Record counts and values are validated.
- Benchmark measurements are actually generated.
- Schema support is compared accurately.
- Results are saved and reproducible.
- All documented commands correspond to the implementation.
- No `cat` commands appear in student instructions.
- All requested screenshots are embedded.
- All image paths work.
- `problems.md` reflects discovered and resolved issues.
- The conclusion uses the observed results and remains within 4–5 sentences.

## 15. Final Deliverables

The main deliverables are:

- `lab_1.5/Lab_1_5_R&D.md` — existing source specification, preserved
- `lab_1.5/Lab_1_5.md` — final student-facing tutorial
- `lab_1.5/problems.md` — concise problem log
- The runnable implementation files
- Dataset and schema files, as appropriate
- Benchmark results and comparison report
- `lab_1.5/images/` — actual screenshots provided during the workflow

At the end, summarize:
- What was implemented
- What was improved
- Problems discovered and fixed
- Actual benchmark outcomes
- Screenshots embedded
- Any remaining limitations

## 16. Start Now

Perform these actions in order:

1. Inspect the repository.
2. Read the entire `lab_1.5/Lab_1_5_R&D.md`.
3. Summarize the actual requirements and identify ambiguities.
4. Create or update `lab_1.5/problems.md` with issues discovered so far.
5. Choose the first implementation milestone.
6. Implement and verify only that milestone.
7. Update the documentation for that milestone.
8. Tell me exactly what to capture for Screenshot 1.
9. Stop and wait for my screenshot.

**Do not rush ahead. The objective is a working lab and a verified, screenshot-guided tutorial that another student can reproduce entirely through VS Code Server.**