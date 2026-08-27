---
doc_id: POL-002
title: Escalation Policy for High and Critical Cases
version: "1.1"
category: escalation
---

# Escalation Policy for High and Critical Cases

1. Any transaction scored HIGH or CRITICAL automatically opens an
   Investigation Case and invokes the AI Investigation Agent.
2. The agent must retrieve: transaction detail, customer history, device/IP
   history, graph relationships, prior risk cases, and applicable policy
   documents before producing a recommendation.
3. CRITICAL cases additionally require a second analyst sign-off if the
   transaction amount exceeds Rs.100,000, per the four-eyes principle.
4. If a coordinated fraud cluster (see POL-004) is implicated, all other
   open transactions sharing the same cluster_id must be surfaced to the
   analyst in the same review session rather than handled independently.
5. Analysts may escalate any case regardless of score if they judge it
   warranted; escalation is never blocked by the automated score.
