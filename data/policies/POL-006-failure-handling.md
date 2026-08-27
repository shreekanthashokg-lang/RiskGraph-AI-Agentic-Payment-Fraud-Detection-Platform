---
doc_id: POL-006
title: Failure Handling and Degraded Modes
version: "1.0"
category: failure_handling
---

# Failure Handling and Degraded Modes

RiskGraph AI must never silently fail. Each subsystem has an explicit,
labeled degraded mode:

- **LLM / AI Investigation Agent unavailable:** the system falls back to
  the deterministic risk engine (ML + graph + rules) for scoring. The
  investigation case is marked `DEGRADED_AI_MODE` and a human analyst is
  notified that no AI-authored evidence summary is available; the analyst
  must investigate manually using the raw evidence tools.
- **Graph service unavailable:** cached graph features or the last-known
  graph risk score are used; scoring continues without blocking.
- **ML model unavailable:** the previous stable model version is used; if
  none is available, the rule engine and graph engine alone determine the
  score and the result is marked degraded.
- **RAG / policy retrieval unavailable:** the deterministic policy engine
  (fixed thresholds in rules.yaml) is used, and any AI-generated
  recommendation is marked as lacking policy citation.
- **Database timeout:** requests use bounded retries with backoff; after
  exhausting retries, the caller receives a structured 503 error rather
  than a hang, and the incident is logged.

All degraded-mode activations are written to the audit trail with a
non-null `failure_mode` field.
