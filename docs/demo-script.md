# 5-minute demo

1. Problem (30s): merchants lose money to fraudulent payments and need fast, explainable verification.
2. Benchmark (45s): show the public benchmark's extreme imbalance and explain why PR-AUC/precision/recall matter.
3. Model (60s): show the model comparison and threshold selection report.
4. Live product (120s): submit a suspicious context transaction; show risk score, reasons, decision, and audit trail.
5. Architecture (45s): React → FastAPI → ML/policy → audit store.
6. Honesty (30s): explicitly distinguish benchmark features from product-side context and state the false-positive cost assumption.
7. Close (10s): working defensive detector/verifier, reproducible evaluation, bounded decisions.
