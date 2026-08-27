---
doc_id: POL-004
title: Coordinated Fraud Cluster Handling
version: "1.0"
category: fraud_clusters
---

# Coordinated Fraud Cluster Handling

A coordinated fraud cluster is a connected group of 3 or more customers
linked through shared devices, IP addresses, or beneficiary accounts, with
at least one of: (a) an above-baseline rate of flagged transactions, (b) a
prior fraud alert among cluster members, or (c) unusually low diversity of
shared identifiers relative to cluster size (e.g. 10 customers sharing 1
device).

When a cluster is detected:
1. All customers in the cluster are surfaced together in the analyst
   dashboard's Fraud Network Visualization.
2. New transactions from any cluster member receive an elevated graph_risk
   component in their aggregate score for as long as the cluster remains
   active (default: 30 days from last cluster activity).
3. Clusters are not, by themselves, sufficient grounds for automatic
   rejection - individual transactions are still scored on their own
   merits and require human review before HIGH/CRITICAL actions.
