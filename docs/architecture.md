# Architecture

## Data truth boundary

The public benchmark is used only for features actually present in that benchmark. No customer/device/location semantics are fabricated.

## ML path

Raw CSV → schema validation → chronological split → model comparison → validation threshold tuning → refit on train+validation → untouched test evaluation → serialized model.

## Product path

Merchant transaction context → deterministic risk signals → bounded policy → recommendation → audit log.

## Why two paths?

The benchmark is rigorous for ML evaluation but anonymized. The product path demonstrates the richer context a merchant could provide without misrepresenting benchmark fields.
