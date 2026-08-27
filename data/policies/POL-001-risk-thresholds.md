---
doc_id: POL-001
title: Risk Score Thresholds and Severity Bands
version: "1.3"
category: risk_thresholds
---

# Risk Score Thresholds and Severity Bands

RiskGraph AI classifies every scored transaction into one of four severity
bands based on the aggregate risk score (0-100), as configured in
`rules.yaml`:

- **LOW (0-30):** Transaction proceeds automatically. No analyst action
  required. Logged to the audit trail for later sampling/QA.
- **MEDIUM (31-60):** Step-up verification is triggered (e.g. OTP
  re-confirmation) or the transaction enters the analyst review queue,
  depending on merchant configuration. Not blocked by default.
- **HIGH (61-85):** Transaction is placed on a temporary hold pending
  review. The AI Investigation Agent is invoked automatically to prepare
  an evidence-backed case for the analyst.
- **CRITICAL (86-100):** Mandatory human review before any funds move.
  The AI Investigation Agent's recommendation is advisory only; a human
  analyst must record an explicit decision (approve/hold/escalate/reject)
  before the transaction can be released.

Thresholds may be changed by risk operations leadership through the
What-If Simulator without a code deployment. Every change is versioned;
the `policy_version` in effect at scoring time is stored with the
transaction's risk score so historical decisions remain auditable.
