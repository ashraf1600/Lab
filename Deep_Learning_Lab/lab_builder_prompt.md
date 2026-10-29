You are an MLOps engineer and technical writer. Build a complete hands-on lab: implement the code, actually run it, capture real terminal screenshots, and write a professional Markdown lab guide that follows the attached "Master Template: Professional Hands-on Lab Documentation" exactly.

## LAB SPEC
- Title: CNN / RNN / Transformer Architecture Tour
- Level: Beginner · Type: Standalone
- Key focus: Implement a toy CNN (image classification), an RNN/LSTM (sequence task) and a Transformer (masked language modelling) in PyTorch. Compare parameter counts, FLOPs and use-case fit for each architecture family.

## HARD RULES
1. Never write the lab or module number anywhere: not in folder names, file names, Docker image tags, code, docstrings, plot titles, the Markdown title or screenshots. Folder: `dl-architecture-tour`. Image tag: `dl-arch:v1`.
2. Never invent output. Every number, table value and screenshot in the guide must come from a command you actually ran. If something fails, fix it and rerun; do not describe results you did not see.
3. Keep the text short. Each section should have only what a beginner needs: short paragraphs, tables where they help, no filler.
4. Student instructions must not use `cat` commands. Students create files with the VS Code Explorer (New File) and paste the code.
5. All code is written and run in the Poridhi VS Code Server, not on the local machine (see EXECUTION ENVIRONMENT).

## EXECUTION ENVIRONMENT (Poridhi VS Code Server)
- Link: <PASTE_PORIDHI_VSCODE_LINK_HERE>  (workspace folder: `/home/poridhian/code`)
- Open this link with your browser tool. Create the project folder `/home/poridhian/code/dl-architecture-tour` there, write every file there and run every command in that VS Code's integrated terminal (Terminal → New Terminal, or F1 → "Terminal: Create New Terminal").
- Do NOT run the lab on the local machine. The local workspace is only used for assembling the final deliverable: the Markdown guide, the screenshots and a copy of the source files.
- First check the environment in the Poridhi terminal: `docker --version`, `docker info --format '{{.ServerVersion}}'`, `nproc`, `free -h`. If Docker is not available or not running, stop and report it.
- After the source files are written in Poridhi, run `sha256sum Dockerfile requirements.txt src/*.py` there. Then copy the same file contents into the local deliverable folder and confirm the hashes match, so the local copy is exactly the code that ran.

## IMPLEMENTATION REQUIREMENTS
- Pinned environment: `Dockerfile` with `FROM python:3.11.9-slim-bookworm`; `requirements.txt` with exact `==` pins and `--extra-index-url https://download.pytorch.org/whl/cpu` + `torch==2.3.1+cpu`, `numpy==1.26.4`, `scikit-learn==1.5.0`, `matplotlib==3.9.0`. Set `PYTHONHASHSEED=42`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` and `MPLCONFIGDIR=/tmp/matplotlib` in the Dockerfile. Add `.dockerignore` (outputs/, docs/, __pycache__, *.md).
- Reuse the seeding helper from the previous lab (`src/reproducibility.py`: set_global_seed, enable_determinism), so every run is reproducible.
- No internet downloads at runtime. Use offline data only:
  - CNN: scikit-learn `load_digits` (8×8 images, bundled with scikit-learn).
  - RNN/LSTM: a synthetic sequence task generated in code with a fixed seed (for example, classify whether a noisy sine-wave sequence trends up or down, or predict the next value).
  - Transformer: masked language modelling on a small text corpus committed to the repo as `data/corpus.txt` (a few hundred short sentences you write yourself), with a simple word-level tokenizer and 15% `[MASK]` tokens.
- Keep all three models small (CPU training under about 1 minute each on a 2-vCPU VM) and of a comparable scale.
- Measure for each model:
  - parameter count: `sum(p.numel() for p in model.parameters())`
  - forward-pass FLOPs for one sample, using the built-in `torch.utils.flop_counter.FlopCounterMode` (no extra dependency)
  - training time and the final metric (accuracy for the CNN and LSTM; masked-token accuracy or loss for the Transformer)
- Suggested structure: `src/models.py`, `src/data.py`, `src/train_cnn.py`, `src/train_rnn.py`, `src/train_transformer.py`, `src/profile_models.py` (params + FLOPs), `src/compare.py`. `compare.py` writes `outputs/comparison.csv`, `outputs/comparison.md` and a bar chart `outputs/params_flops.png` (log scale). Plot titles must not contain lab numbers.
- Run everything through Docker with the outputs folder mounted:
  `docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)/outputs:/app/outputs" dl-arch:v1 python -m src.<module>`
- Before building, run `python3 -m py_compile src/*.py`.

## TERMINAL TIPS (lessons from the previous lab)
- In the browser terminal, a typed `\n` may not press Enter. Send an explicit Enter/Return key after each command.
- If you create files from the terminal, use one-line `printf '%s\n' 'line1' 'line2' > file` commands, and run `set +H` first so that `!` in code is not history-expanded. Afterwards, check that the files compile.
- Clear the terminal with Ctrl+L (not `clear`) before each command you want to screenshot, so the screenshot starts with the command line.
- If VS Code shows "Restricted Mode", ask the user to click "Trust Folder & Continue". Do not click it yourself.

## SCREENSHOTS
- Terminal output only. Crop to the terminal area. Maximize the terminal panel and use a viewport around 1000×640, so the text is readable.
- Draw red rectangles (2 px) around the lines that prove each step: versions, `params=`, `FLOPs`, final metrics, saved paths, the comparison table.
- Save the screenshots as `docs/images/NN-short-name.png`, numbered in the order they appear.
- Suggested set: 01 Docker check · 02 project files + image · 03 docker build · 04 environment report · 05 CNN training · 06 LSTM training · 07 Transformer training · 08 params/FLOPs profile · 09 comparison table · 10 output files · 11 the `params_flops.png` chart (cropped figure).
- Place each screenshot directly under the command that produced it. Give each one a caption (`*Figure N: …*`) and a specific 3–4 sentence explanation of what the boxes show and why it matters.

## LAB GUIDE (Markdown)
Follow the Master Template sections in order: Introduction (real-world scenario, problem statement, learning outcomes, architecture diagram, walkthrough), Project Structure, Prerequisites, Environment Setup, Project Implementation (Step N — Title, each with Objective, complete code, commands, screenshot, explanation), Verification and Testing, Results and Observations, Troubleshooting, Conclusion (4–5 sentences).
- Scenario: one consistent story used from start to finish. For example, a startup team deciding which architecture family fits three product features (reading form images, forecasting sensor sequences, autocompleting clinical text), and needing evidence on size, compute cost and fit.
- Results: a table built from the actual `comparison.csv` (Architecture | Task | Params | FLOPs/sample | Train time | Metric | Best use-case fit), plus 3–4 short observations, for example how attention's cost grows with sequence length and why CNNs share weights.
- Troubleshooting: only issues relevant to these tools, each with Symptom / Likely cause / Resolution / Verification.
- Use relative image paths only (`docs/images/...`), so the guide renders when opened from the project folder.

## ARCHITECTURE DIAGRAM
Create a clean left-to-right diagram, saved as `docs/images/architecture.svg` (or .png) and embedded in section 1.4:
Project Files → (docker build) → Docker image box containing the data sources (digits / synthetic sequences / corpus.txt), the three model cards (CNN, LSTM, Transformer) and `profile_models.py` + `compare.py` → Host `outputs/` (mounted volume) with metrics, comparison.csv and params_flops.png → a Findings box.
Use accurate labels only, no decorative or misleading icons, no crossing arrows, and no lab number.

## DELIVERABLE
The code runs in Poridhi. The final deliverable is assembled in the local workspace as a self-contained folder `dl-architecture-tour/` containing all source files, `Dockerfile`, `requirements.txt`, `.dockerignore`, `data/`, an empty `outputs/` (with `.gitkeep`), `docs/images/` (all screenshots and the diagram) and `LAB_DL_Architecture_Tour.md`. Finish with a final checklist pass against the Master Template's "Final Review Checklist", and report anything you could not verify.
