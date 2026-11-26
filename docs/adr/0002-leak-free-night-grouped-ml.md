# ADR 0002: Leak-Free Night-Grouped ML Validation

- Status: Accepted
- Date: 2026-11-24

## Context
10-min rows from same night are highly correlated. Random splits leak temporal/physical state and inflate metrics.

## Decision
All offline validation uses `GroupKFold` grouped by `night_id`. No same-night rows across train/test. Report baseline and reward improvement.

## Consequences
- Positive: realistic generalization estimate.
- Negative: lower apparent scores than leaky splits.
- Verification: automated leakage assert in `ml/train_dewleaf_policy.py`; CI/data tests.
