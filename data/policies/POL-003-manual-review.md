---
doc_id: POL-003
title: Manual Review Requirements
version: "1.0"
category: manual_review
---

# Manual Review Requirements

- A transaction requires manual review whenever: (a) risk_level is HIGH or
  CRITICAL, (b) the customer has more than 2 previous fraud alerts
  regardless of current score, or (c) the transaction is part of a
  detected fraud cluster with connected_fraud_cases > 0.
- Reviewing analysts must record a decision from the fixed action set:
  approve, hold, escalate, reject. Free-text notes are encouraged but do
  not substitute for a decision.
- The AI Investigation Agent's output is clearly labeled as a
  recommendation. It is never auto-applied as the final decision for
  HIGH/CRITICAL cases.
- Analysts should distinguish between Evidence (directly observed facts:
  transaction data, graph connections, prior alerts), Inference (the
  agent's or analyst's interpretation of what the evidence suggests), and
  Recommendation (the proposed action). Inference must never be presented
  as verified fact in the case file.
