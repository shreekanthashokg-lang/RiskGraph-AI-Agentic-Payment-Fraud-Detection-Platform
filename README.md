RiskGraph AI
Agentic Real-Time Payment Risk & Fraud Investigation Platform
Built for Razorpay AI Buildathon 2026
Track 2: AI Risk Manager
Executive Summary

RiskGraph AI is an enterprise-grade fraud detection and investigation platform designed for modern payment ecosystems.

Traditional fraud systems evaluate transactions independently and produce a binary fraud prediction. This approach struggles against organized fraud rings, mule networks, account takeovers, synthetic identities, and coordinated attacks where the risk emerges from the relationships between entities rather than from a single transaction.

RiskGraph AI solves this problem through a multi-layered architecture that combines:

Machine Learning Risk Scoring
Behavioral Anomaly Detection
Graph-Based Fraud Ring Detection
Deterministic Risk Policies
Retrieval-Augmented AI Investigation
Human-in-the-Loop Decision Making

The platform analyzes not only the transaction itself but also the network surrounding it, including:

Shared devices
Shared IP addresses
Shared beneficiaries
Shared accounts
Historical fraud patterns
Velocity spikes
Cross-border anomalies

For high-risk cases, an AI Investigation Agent gathers evidence, retrieves relevant internal policies, generates an explainable risk assessment, and recommends actions while ensuring that final decisions remain under human control.

The Problem

Fraud has evolved beyond isolated suspicious transactions.

Modern payment fraud often operates through interconnected ecosystems of:

Mule accounts
Device farms
Synthetic identities
Organized fraud rings
Account takeover campaigns

Consider the following scenario:

Plain Text
Customer A ─── Device X
Customer B ─── Device X
Customer C ─── Device X
 
Customer A ─── Beneficiary Z
Customer B ─── Beneficiary Z
 
Customer C ─── IP Y
Customer D ─── IP Y

Individually, each transaction may appear legitimate.

Collectively, they reveal a coordinated fraud network.

Most traditional ML systems fail because they:

❌ Analyze transactions independently

❌ Ignore entity relationships

❌ Can't explain decisions clearly

❌ Produce black-box outputs

❌ Lack governance and auditability

❌ Are difficult for risk analysts to investigate

Our Solution

RiskGraph AI introduces a layered risk architecture that separates:

Detection

"What is risky?"

Performed by:

ML Models
Graph Analytics
Rule Engine
Anomaly Detection
Investigation

"Why is it risky?"

Performed by:

AI Investigator Agent
Policy Retrieval System
Evidence Collection Engine
Governance

"What action is allowed?"

Performed by:

Policy Engine
Human Analyst Review
Immutable Audit Trail
Key Innovation
Graph-Aware Fraud Intelligence

Unlike traditional fraud systems that evaluate a transaction in isolation, RiskGraph AI constructs a relationship graph connecting:

Plain Text
Customer
├─ Device
├─ IP Address
├─ Merchant
└─ Beneficiary

This enables the discovery of hidden patterns such as:

Fraud Rings

Multiple customers using the same device.

Mule Networks

Many accounts funneling funds to one beneficiary.

Device Farms

Large numbers of accounts originating from a small set of devices.

Shared-Infrastructure Attacks

Connections through common IP ranges.

Synthetic Identity Clusters

Groups of seemingly unrelated accounts linked through hidden infrastructure.

Technical Architecture
Plain Text
┌─────────────────┐
│ Payment Event │
└────────┬────────┘
│
▼
 
Event Ingestion Layer
│
┌────────────────────┼───────────────────┐
▼ ▼ ▼
 
Feature Engine Graph Builder Policy Engine
│ │ │
▼ ▼ ▼
 
ML Risk Model Graph Risk Score Rule Violations
│ │ │
└──────────────┬─────┴───────────────┬──┘
▼
 
Risk Aggregation Engine
 
▼
 
LOW MEDIUM HIGH CRITICAL
 
▼
 
AI Investigation Agent
 
▼
 
Policy-Grounded Recommendations
 
▼
 
Human Risk Analyst
 
▼
 
Immutable Audit Trail
 
Core Components
1. Machine Learning Layer

Purpose:

Predict fraud probability based on transaction behavior.

Input Signals
transaction amount
customer baseline spending
historical fraud alerts
country mismatch
velocity features
authentication failures
payment channel
Model

Current implementation:

RandomForest (fallback)
XGBoost-ready architecture

Performance on real dataset:

Metric	ScoreROC-AUC	0.982
PR-AUC	0.780
Precision	0.80
Recall	0.73
F1	0.76

The model is calibrated to avoid over-confidence and provide meaningful risk probabilities.

2. Behavioral Anomaly Engine

Purpose:

Detect previously unseen fraud patterns.

Model:

Plain Text
Isolation Forest
 

Detects:

Sudden spending spikes
Velocity anomalies
Geographic anomalies
Unusual transaction timing
Behavioral deviation

Benefit:

Can identify emerging fraud patterns before explicit rules are created.

3. Graph Intelligence Engine

Purpose:

Detect coordinated activity.

Graph nodes include:

Plain Text
Customer
Device
IP
Merchant
Beneficiary

Graph edges represent:

Plain Text
USES_DEVICE
USES_IP
PAYS_TO
PURCHASES_FROM

Example:

Plain Text
Cust001 ── DeviceA
Cust002 ── DeviceA
Cust003 ── DeviceA

Graph Engine automatically identifies:

Connected Components
Fraud Clusters
Shared Infrastructure
Account Networks

Output:

Python
graph_risk_score = 0.0 -> 1.0
4. Deterministic Rule Engine

Purpose:

Capture domain knowledge and regulatory requirements.

Examples:

High-Risk Amount
YAML
IF amount > threshold
THEN add risk points
Country Mismatch
YAML
IF transaction_country != card_country
THEN add risk points
Prior Fraud History
YAML
IF previous_fraud_alerts > 0
THEN add risk points

Benefits:

Explainable
Auditable
Versioned
Easy to modify
5. Risk Aggregator

Combines:

Plain Text
ML Score
+
Graph Score
+
Anomaly Score
+
Rule Violations

Output:

Plain Text
Risk Score: 0-100

Levels:

Score	Risk0-25	Low
26-50	Medium
51-75	High
76-100	Critical
AI Investigation Agent

The Investigation Agent only activates for:

Plain Text
High Risk
Critical Risk

The agent does NOT make final decisions.

The agent:

✅ Retrieves transaction details

✅ Analyzes graph relationships

✅ Retrieves applicable policies

✅ Builds evidence package

✅ Produces explainable recommendation

The agent cannot:

❌ Release payments

❌ Block accounts

❌ Move money

❌ Override policy

❌ Skip human review

Retrieval-Augmented Governance (RAG)

The AI Investigator uses internal policy documents.

Example policies:

Plain Text
POL-001 Transaction Escalation
POL-002 Fraud Ring Investigation
POL-003 Velocity Abuse
POL-004 High-Risk Geography
POL-007 Agent Behavior
POL-008 Privacy Requirements

The agent must cite retrieved policies before making recommendations.

No policy retrieval = no recommendation.

This prevents hallucinated compliance decisions.

Human-in-the-Loop Safety Model

A fundamental principle of RiskGraph AI:

AI Recommends
Humans Decide

Workflow:

Plain Text
Detect
↓
Investigate
↓
Recommend
↓
Human Review
↓
Decision

This satisfies key governance requirements for:

Financial institutions
Fintech platforms
Regulatory audit
Risk management teams
Explainability

Every risk decision includes:

Evidence

Facts retrieved from systems.

Example:

Plain Text
Shared Device:
8 customers
 
Shared Beneficiary:
17 transactions
 
Country Mismatch:
Detected
Inference

Reasoning derived from evidence.

Example:

Plain Text
Activity resembles mule-account behavior.
Recommendation

Suggested action.

Example:

Plain Text
Escalate for manual review.
Policy Citation
Plain Text
POL-003
POL-007

This produces a complete audit trail for investigation and compliance purposes.

Failure-Tolerant Architecture

Production systems must degrade gracefully.

RiskGraph AI explicitly supports:

LLM Failure

Fallback:

Plain Text
Deterministic Investigation Summary
Model Failure

Fallback:

Plain Text
Rules + Graph Scoring
Graph Failure

Fallback:

Plain Text
Default Graph Features
RAG Failure

Fallback:

Plain Text
No Policy Evidence
No Recommendation
Database Failure

Fallback:

Plain Text
Structured Retry
Graceful 503
Business Impact

RiskGraph AI helps organizations:

Reduce Fraud Losses

Detect coordinated attacks earlier.

Reduce False Positives

Combine multiple signals before escalation.

Improve Analyst Productivity

Auto-generate investigation summaries.

Improve Compliance

Provide auditable, explainable decisions.

Improve Trust

Human approval remains mandatory.

Why RiskGraph AI Is Different
Capability	Traditional Fraud Systems	RiskGraph AIML Fraud Detection	✅	✅
Network Analysis	❌	✅
Fraud Ring Detection	❌	✅
Explainable Decisions	Partial	✅
Policy-Aware AI	❌	✅
Human-in-the-Loop Governance	Rare	✅
Failure Degradation	Limited	✅
Auditable Recommendations	Limited	✅
Future Roadmap
v2
Neo4j Graph Database
Graph Neural Networks
SHAP Explainability
Real-Time Stream Processing
Adaptive Fraud Policies
v3
Cross-Merchant Fraud Intelligence
Multi-Agent Investigation Framework
Fraud Ring Visualization Studio
Continuous Learning Feedback Loops
Final Takeaway

RiskGraph AI is not just a fraud classifier.

It is a complete risk intelligence platform that combines supervised machine learning, graph analytics, anomaly detection, deterministic governance, retrieval-augmented investigation, and human oversight to detect, explain, and manage fraud in modern payment ecosystems.

By separating detection, investigation, policy, and decision-making into independent layers, the system remains explainable, auditable, resilient, and safe for deployment in regulated financial environments.
