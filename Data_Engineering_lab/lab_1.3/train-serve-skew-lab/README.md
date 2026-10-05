# Lab 1.3: Train-Serve Skew Simulation (QuickCart)

This repository implements the production machine learning data engineering lab simulating and detecting **Train-Serve Skew** and **Feature Drift** on the QuickCart food delivery platform.

---

## 1. Project Directory Structure

```text
train-serve-skew-lab/
│
├── data/
│   ├── train.csv               # Historical training dataset (80% split)
│   ├── test.csv                # Reserved offline evaluation dataset (20% split)
│   └── online_data.csv         # Drifted production incoming data
│
├── models/
│   └── model.pkl               # Serialized frozen Scikit-Learn pipeline artifact
│
├── src/
│   ├── prepare_data.py         # Synthesizes historical dataset and splits train/test
│   ├── train.py                # Trains scaler + classifier and exports model.pkl
│   ├── offline_predict.py      # Evaluates baseline offline metrics & predictions
│   ├── generate_online_data.py # Simulates production feature drift (rush hour, radius)
│   ├── online_predict.py       # Scores drifted online data with frozen model
│   └── detect_skew.py          # Quantifies drift, prediction skew, and generates reports
│
├── results/
│   ├── offline_predictions.csv # Baseline offline test predictions & probabilities
│   ├── online_predictions.csv  # Production serving predictions & probabilities
│   ├── skew_report.csv         # Structured feature drift and skew delta report
│   └── skew_distribution.png   # Multi-panel feature distribution visualization
│
├── requirements.txt            # Python dependencies (pandas, scikit-learn, matplotlib)
└── README.md                   # Lab execution documentation
```

---

## 2. Setup & Installation

Create and activate a virtual environment, then install project dependencies:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Linux / macOS / Poridhi Container
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. End-to-End Execution Workflow

### Step 1: Prepare Historical Data & Splits
```bash
python src/prepare_data.py
```
Synthesizes 1,000 historical order records under baseline operational conditions and partitions them into `data/train.csv` (800 rows) and `data/test.csv` (200 rows).

### Step 2: Train & Freeze ML Model Pipeline
```bash
python src/train.py
```
Fits a `StandardScaler` and `LogisticRegression` pipeline on `data/train.csv` and serializes the frozen pipeline artifact to `models/model.pkl`.

### Step 3: Run Offline Baseline Evaluation
```bash
python src/offline_predict.py
```
Scores `data/test.csv`, measures baseline accuracy and cancellation class distribution (~25% cancel rate), and writes predictions to `results/offline_predictions.csv`.

### Step 4: Simulate Production Data Drift
```bash
python src/generate_online_data.py
```
Generates 500 online orders reflecting real-world drift (order amounts shift to $850, delivery delays reach 48 minutes, delivery radius expands to 10.5 km) into `data/online_data.csv`.

### Step 5: Serve Unchanged Model Online
```bash
python src/online_predict.py
```
Infers predictions on `data/online_data.csv` using the frozen `models/model.pkl` without retraining. Saves serving predictions to `results/online_predictions.csv`.

### Step 6: Detect & Quantify Train-Serve Skew
```bash
python src/detect_skew.py
```
Computes feature drift percentages, highlights threshold breaches, analyzes the surge in predicted cancellations, exports `results/skew_report.csv`, outputs ASCII visual bars, and saves `results/skew_distribution.png`.
