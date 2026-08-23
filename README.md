# AI Payment Risk & Fraud Investigation Agent

**Buildathon target:** Razorpay AI Risk Manager.

This project is a defensive fraud-risk detector + verifier. It combines:
- a public benchmark adapter for the classic ULB/MLG credit-card fraud dataset,
- imbalance-aware model benchmarking,
- threshold selection using a validation set,
- a bounded investigation/policy layer,
- a FastAPI backend,
- a React dashboard,
- an audit log,
- automated tests.

## Important benchmark honesty

The classic public benchmark contains **284,807 transactions and 492 frauds (0.172%)**. Its V1–V28 fields are anonymized/PCA-transformed; only `Time` and `Amount` retain direct meaning. Therefore this project **does not invent device/location/customer fields and claim they came from the benchmark**.

The benchmark path uses:
`Time`, `Amount`, `V1...V28` → engineered `hour`, `amount_log`, and the anonymized V features.

The product demo path separately accepts richer merchant context such as new device/location and customer history. Those are product-side signals, not benchmark claims.

## Data source

Download the original dataset from the official Kaggle dataset page:
https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

Place `creditcard.csv` at:
`data/raw/creditcard.csv`

Do not commit the raw dataset to GitHub.

## One-command benchmark build

### Backend setup
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Train/evaluate
From the repository root:
```bash
python -m backend.ml.pipeline --data data/raw/creditcard.csv
```

This produces:
- `backend/models/final_model.joblib`
- `backend/models/model_metadata.json`
- `backend/reports/metrics.json`
- `backend/reports/confusion_matrix.json`
- `backend/reports/thresholds.csv`
- `backend/reports/evaluation.md`
- `data/processed/benchmark_sample.csv`

The pipeline:
1. validates the raw schema,
2. sorts by `Time`,
3. keeps the final 20% as a chronological holdout test set,
4. uses the first 80% for train/validation,
5. compares Logistic Regression and HistGradientBoosting,
6. tunes a decision threshold on validation data,
7. evaluates once on untouched test data,
8. reports precision, recall, F1, PR-AUC, confusion matrix, and false-positive cost under an explicit illustrative cost assumption.

No SMOTE or oversampling is applied to the held-out test set.

## If you don't have the benchmark yet

The application still runs using a deterministic demo model generated from `backend/ml/demo_model.py`. This is clearly labeled **DEMO ONLY** in the UI. It must not be presented as benchmark performance.

## Run backend
```bash
uvicorn backend.app:app --reload
```

Health:
`GET http://127.0.0.1:8000/health`

## Run frontend
```bash
cd frontend
npm install
npm run dev
```

## API example

`POST /predict/benchmark`
```json
{
  "time": 406.0,
  "amount": 250.50,
  "v": [0.1, -0.2, 0.3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
}
```

`POST /predict/context`
```json
{
  "amount": 48500,
  "hour": 3,
  "customer_avg_amount": 1850,
  "transactions_24h": 7,
  "account_age_days": 18,
  "new_device": true,
  "new_location": true
}
```

## Architecture

```text
                ┌──────────────────────┐
                │ React Risk Dashboard │
                └──────────┬───────────┘
                           │
                           ▼
                     ┌───────────┐
                     │  FastAPI  │
                     └─────┬─────┘
                           │
             ┌─────────────┴──────────────┐
             ▼                            ▼
     ┌────────────────┐          ┌─────────────────┐
     │ Benchmark ML   │          │ Context Rules   │
     │ Risk Scorer    │          │ + Investigation │
     └────────┬───────┘          └────────┬────────┘
              └──────────────┬────────────┘
                             ▼
                    ┌────────────────┐
                    │ Decision Policy│
                    │ Approve/Review │
                    │ /Block         │
                    └───────┬────────┘
                            ▼
                     ┌─────────────┐
                     │ Audit Store │
                     └─────────────┘
```

## Defense-only boundary

The system only identifies risk and recommends defensive actions. It contains no credential theft, bypass, evasion, exploitation, or fraud-enabling workflow.

## Buildathon submission checklist

- [ ] Public repository
- [ ] Benchmark file downloaded from the cited source
- [ ] `python -m backend.ml.pipeline --data data/raw/creditcard.csv`
- [ ] Review `backend/reports/evaluation.md`
- [ ] Review false-positive cost assumption
- [ ] Run tests
- [ ] Run frontend/backend
- [ ] Record 5-minute pitch
- [ ] Include architecture diagram
- [ ] Do not claim synthetic/demo metrics as real benchmark metrics
