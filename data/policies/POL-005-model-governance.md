---
doc_id: POL-005
title: Model Governance
version: "1.2"
category: model_governance
---

# Model Governance

- Every risk score records the `model_version` that produced it (see
  ModelVersion table). Models are never silently swapped in production;
  a new version must pass the evaluation gates in `ml/train.py`
  (precision, recall, PR-AUC, false-positive rate) before activation.
- The classification threshold is chosen on a held-out validation split to
  maximize F1 subject to a minimum recall floor, and the rationale is
  persisted to `metrics.json` for audit.
- If the production model becomes unavailable, the system falls back to
  the last known-stable model version and marks affected transactions with
  `DEGRADED_AI_MODE` (see POL-006).
- SHAP-based (or equivalent) feature contribution values shown to analysts
  must be computed from the actual model and data for that transaction.
  Fabricated or illustrative "example" contribution numbers must never be
  shown in the production analyst UI.
