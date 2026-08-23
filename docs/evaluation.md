# Evaluation protocol

## Split

The dataset is sorted by `Time`. The first 64% is training, the next 16% validation, and the final 20% is the held-out test set.

## Metrics

Primary:
- Precision
- Recall
- F1
- PR-AUC

Accuracy is deliberately not used as the headline metric because the fraud class is only 0.172% in the classic benchmark.

## Threshold

Threshold is selected on validation data. The test set is not used for threshold selection.

## False-positive cost

The project reports an illustrative cost:
- false positive = 1 unit
- false negative = 10 units

This is explicitly a modeling assumption and is not presented as a Razorpay business cost estimate.
