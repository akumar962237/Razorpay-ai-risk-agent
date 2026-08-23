# Benchmark Evaluation

- Rows: 284,807
- Fraud cases: 492
- Fraud rate: 0.1727%
- Selected model: `logistic`
- Threshold: `0.950`
- Test precision: **0.4236**
- Test recall: **0.8133**
- Test F1: **0.5571**
- Test PR-AUC: **0.7619**

The final test set was not used for threshold selection. The illustrative cost assigns 1 unit to a false positive and 10 to a false negative; this is a modeling assumption, not a Razorpay business cost estimate.
