RiskGraph AI

Agentic Real-Time Payment Risk & Fraud Investigation Platform
 Built for Razorpay AI Buildathon 2026 • Track 2: AI Risk Manager

🚀 Executive Summary

RiskGraph AI is an enterprise-grade fraud detection and investigation platform designed for modern payment ecosystems.

Traditional fraud systems evaluate transactions independently and produce a fraud probability score. While effective against simple fraud patterns, they often fail to detect coordinated attacks involving mule accounts, device farms, synthetic identities, account takeovers, and organized fraud rings.

RISKGRAPH  AI GOES BEYOND TRANSACTION-LEVEL DETECTION. 
IT COMBINES EVERYTHING :

🤖 Machine Learning Risk Scoring
🕸️ Graph-Based Relationship Analysis
📈 Behavioral Anomaly Detection
📋 Deterministic Risk Policies
🧠 AI-Powered Fraud Investigation
✅ Human-in-the-Loop Decision Governance

Rather than asking:

"Is this transaction fraudulent?"

RiskGraph AI asks:

"How risky is this transaction, who is it connected to, what evidence exists, which policies apply, and what action should a risk analyst consider?"

🎯 The Problem

MODERN PAYMENT FRAUD IS RARELY AN ISOLATED EVENT. 

Fraudsters increasingly operate through networks of:

Mule accounts
Shared devices
Proxy infrastructure
Synthetic identities
Coordinated beneficiary networks
Account takeover campaigns

Consider the following example:

Customer A ── Device X
Customer B ── Device X
Customer C ── Device X

Customer A ── Beneficiary Z
Customer B ── Beneficiary Z

Customer C ── IP Y
Customer D ── IP Y


Viewed individually:

✅ Transactions appear normal

Viewed collectively:

🚨 A coordinated fraud network emerges

Most traditional fraud systems struggle because they:

Analyze transactions independently
Ignore relationships between entities
Rely heavily on static rules
Produce black-box decisions
Lack investigation support
Provide limited auditability
💡 Our Solution

RiskGraph AI introduces a layered architecture that separates:

Detection

What is risky?

Performed by:

ML Models
Graph Intelligence
Rule Engine
Anomaly Detection
Investigation

Why is it risky?

PERFORMED BY:

AI Investigation Agent
Policy Search
Evidence Collection Framework
Governance

What actions are allowed?

Performed by:

Deterministic Policy Engine
Human Risk Analyst
Immutable Audit Trail
⭐ Key Innovation
Fraud Detection Through Relationship Intelligence

UNLIKE TRADITIONAL SYSTEMS THAT EVALUATES  a payment in isolation, RiskGraph AI constructs a fraud graph that links:

Customer
 ├── Device
 ├── IP Address
 ├── Beneficiary
 └── Merchant


THIS RELATIONSHIP NETWORK ENABLES DETECTION OF :

Fraud Rings

Many customers sharing the same device.

Mule Networks

Many accounts transferring funds to a common beneficiary.

Device Farms

Hundreds of accounts coming from a few devices.

Shared Infrastructure Attacks

Clusters operating behind common IP ranges.

Synthetic Identity Groups

Apparently unrelated users connected through hidden infrastructure.

🏗 Architecture
                    ┌──────────────────┐
                    │ Payment Event    │
                    └────────┬─────────┘
                             │
                             ▼

                    Event Ingestion API
                          (FastAPI)

                             │

       ┌─────────────────────┴────────────────────┐
       ▼                                          ▼

 Feature Engineering                    Relationship Graph
                                                  (NetworkX)

       ▼                                          ▼

   ML Risk Model                        Graph Risk Engine

(RandomForest/XGBoost)     (Shared Device/IP/Beneficiary Analysis)

       └─────────────────────┬────────────────────┘
                             ▼

                    Anomaly Detection
                     (IsolationForest)

                             ▼

                    Deterministic Rules
                      (Versioned YAML)

                             ▼

                     Risk Aggregator

                             ▼

              Risk Score (0-100) + Severity

                 LOW • MEDIUM • HIGH • CRITICAL

                             ▼

          ┌──────────────────┴─────────────────┐
          ▼                                    ▼

      LOW/MEDIUM                      HIGH/CRITICAL

 Auto Approve / Step-Up          AI Investigation Agent

                                         ▼

                            Evidence Collection
                             Policy Retrieval
                           Recommendation Engine

                                         ▼

                              Human Risk Analyst

                                         ▼

                            Immutable Audit Trail

🔬 Core Components
1. Machine Learning Risk Layer

Purpose:

PREDICT FRAUD PROBABILITY USING TRANSACTION  behaviour and historical activity.

Signals Used
Transaction amount
Customer spending baseline
Geographic mismatch
Authentication failures
Transaction velocity
Historical fraud alerts
Merchant category
Card-country mismatch
Shipping distance
Payment channel
Real Dataset Training

Unlike many hackathon demos built entirely on synthetic data, RiskGraph AI trains on a real fraud dataset containing:

299,695 transactions
6,000 customers
2.21% fraud rate


Feature engineering computes:

velocity_1m
velocity_10m
velocity_1h
velocity_24h
previous_fraud_alerts
is_suspicious_geo

USING ONLY HISTORICAL RECORDS  available before the transaction being scored, preventing target leakage.

Current Performance
Metric	ScoreROC-AUC	0.982
PR-AUC	0.780
Precision	0.80
Recall	0.73
F1 Score	0.76
2. Behavioral Anomaly Detection

Purpose:

Detect previously unseen fraud strategies.

Model:

Isolation Forest


Detects:

Spending spikes
Abnormal velocity
New behavior patterns
Geographic anomalies
Rare transaction combinations

Benefit:

Rules only catch known patterns. Anomaly detection catches emerging patterns.

3. Relationship Graph Engine

Purpose:

Detect coordinated fraud activity.

Nodes:

Customer
Device
IP Address
Merchant
Beneficiary


Edges:

USES_DEVICE
USES_IP
PAYS_TO
PURCHASES_FROM


Example:

Customer_1 ── Device_A
Customer_2 ── Device_A
Customer_3 ── Device_A


The graph engine identifies:

Connected Fraud Clusters
Shared Devices
Shared Infrastructure
Suspicious Beneficiary Networks
Fraud Rings

Output:

graph_risk_score = 0.0 → 1.0

4. Deterministic Rule Engine

Purpose:

Capture expert fraud knowledge in a transparent, auditable form.

Example Rules:

High Amount
IF amount > threshold
THEN increase risk

Beneficiary Risk
IF new_beneficiary = true
THEN increase risk

Country Mismatch
IF card_country != transaction_country
THEN increase risk

Repeat Alerts
IF previous_fraud_alerts > 0
THEN increase risk


Benefits:

✅ Explainable

✅ Version Controlled

✅ Auditable

✅ Easy To Modify

5. Risk Aggregation Engine

Combines:

ML Risk Score
+
Graph Risk Score
+
Anomaly Detection Score
+
Policy Rule Signals


Produces:

Risk Score: 0-100


Risk Tiers:

Score Range	Severity0-25	LOW
26-50	MEDIUM
51-75	HIGH
76-100	CRITICAL
🤖 AI Investigation Agent

The Investigation Agent activates only for:

HIGH
CRITICAL


risk cases.

What The Agent Can Do

✅ Retrieve transaction details

✅ Analyze graph connections

✅ Query policy documents

✅ Gather supporting evidence

✅ Generate investigation summaries

✅ Recommend analyst actions

What The Agent Cannot Do

❌ Move money

❌ Block accounts

❌ Reverse transactions

❌ Override policy

❌ Skip human approval

❌ Execute financial actions

This restriction is enforced by policy:

POL-007: Agent Behavior Policy

📚 Retrieval-Augmented Governance (RAG)

The Investigation Agent does not generate recommendations from memory.

Instead, it searches internal policy documentation.

Examples:

POL-001 Escalation Policy
POL-002 Fraud Ring Investigation
POL-003 Velocity Monitoring
POL-004 Geographic Risk Controls
POL-005 Transaction Hold Procedures
POL-006 Failure Handling
POL-007 Agent Behavior
POL-008 Privacy Requirements


The agent must cite relevant policy sections before making recommendations.

No policy evidence → No recommendation.

This prevents hallucinated compliance decisions.

👨‍💼 Human-in-the-Loop Safety Model

A fundamental design principle:

AI Recommends
Humans Decide

Workflow:

Detect
 ↓

Investigate
 ↓

Recommend
 ↓

Human Review
 ↓

Decision


No High or Critical transaction can be automatically finalized by the AI agent.

The human analyst remains the ultimate decision-maker.

🔍 Explainability & Auditability

Every investigation contains four separate sections:

Evidence

Facts gathered from systems.

Example:

Device Shared By:
8 Customers

Beneficiary Shared By:
17 Transactions

Country Mismatch:
Detected

Inference

Reasoning derived from evidence.

Example:

Pattern resembles coordinated mule activity.

Recommendation

Suggested next step.

Example:

Escalate for manual review.

Policy Citations

Example:

POL-002
POL-007


Every recommendation can therefore be traced, reviewed, and audited.

📊 Example Risk Scoring Results
Legitimate Transaction
Scenario:
Long-standing customer
Small grocery purchase
Card country matches transaction country
3DS authentication passed

ML Fraud Probability: 0.03%
Risk Score: 12/100

Result:
LOW RISK

Suspicious Transaction
Scenario:
New customer
Card issued in Nigeria
Transaction from United States
High velocity activity
AVS failed
CVV failed
3DS failed
8,200 km shipping distance
2 previous fraud alerts

ML Fraud Probability: 86.57%
Risk Score: 61/100

Result:
HIGH RISK


Triggered Rules:

R002
R003
R004
R005
Edge Case Transaction
Scenario:
4× normal customer spend
No other fraud indicators

ML Fraud Probability: 0.22%
Risk Score: 15/100

Result:
LOW RISK


Demonstrates reduced false positives through signal aggregation.

🛡 Failure-Tolerant Design

One of the judging criteria is system resilience.

RiskGraph AI explicitly degrades rather than failing silently.

Failure Scenario	System BehaviorLLM unavailable	Deterministic investigation summary
API key missing	DEGRADED_AI_MODE
Model unavailable	Graph + Rules fallback
Graph engine failure	Default graph features
Empty RAG index	No policy recommendations
Database unavailable	Retry + structured 503

Example:

mv ml/artifacts/model.pkl model.bak


Then:

GET /health


Returns:

{
  "model_status": "degraded"
}


while scoring remains operational.

📈 Business Impact

RiskGraph AI helps payment providers:

Reduce Fraud Losses

Earlier identification of coordinated attacks.

Reduce False Positives

Multiple signals reduce unnecessary alerts.

Increase Analyst Efficiency

Automated evidence gathering and summarization.

Improve Compliance

Policy-grounded recommendations.

Improve Trust

Human oversight remains mandatory.

🔒 Security & Privacy
Environment-based secret management
No hard-coded credentials
Pydantic request validation
Configurable CORS controls
Immutable audit records
Synthetic demo data
No real PII within repository
🧪 Testing Coverage
cd backend
pytest -v --cov=app


Covered Components:

✅ Feature Engineering

✅ Rule Engine

✅ Graph Engine

✅ Anomaly Detection

✅ Risk Aggregation

✅ Policy Retrieval

✅ Agent Tool Dispatch

✅ Retry & Fallback Framework

✅ Citation Validation

⚡ Quick Start
1. Backend Setup
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp ../.env.example ../.env


Add:

ANTHROPIC_API_KEY=<your_key>

2. Train The Model
python ml/train.py \
  --data data/raw/transactions.csv


Generates:

ml/artifacts/model.pkl
ml/artifacts/metrics.json
ml/artifacts/model_metadata.json
reports/classification_report.txt
reports/*.png

3. Start The API
cd backend

uvicorn app.main:app \
  --reload \
  --port 8000


Open:

http://localhost:8000/docs
http://localhost:8000/health

4. Start Frontend
cd frontend

npm install
npm run dev


Open:

http://localhost:5173

🐳 Docker Deployment
cp .env.example .env

docker compose up --build


The stack launches:

Trainer
PostgreSQL
Redis
Backend API
Frontend Dashboard
🗺 Future Roadmap
Version 2
Neo4j Integration
Graph Neural Networks (GNNs)
SHAP Explainability
Kafka Streaming
Real-Time Feature Store
Version 3
Cross-Merchant Fraud Intelligence
Multi-Agent Investigations
Adaptive Policy Learning
Fraud Ring Visualization Studio
Continuous Feedback Training
🏆 Why RiskGraph AI Stands Out
Capability	Traditional Systems	RiskGraph AITransaction ML	✅	✅
Graph Analytics	❌	✅
Fraud Ring Detection	❌	✅
Behavioral Anomalies	Limited	✅
AI Investigation	❌	✅
Policy-Grounded Decisions	❌	✅
Human Oversight	Rare	✅
Audit Trail	Partial	✅
Resilient Degradation	Limited	✅
Final Takeaway

RiskGraph AI is not just a fraud classifier.

It is a complete AI-powered fraud detection, investigation, governance, and decision-support platform that combines machine learning, graph intelligence, anomaly detection, policy-aware AI, and mandatory human oversight.

By separating Detection, Investigation, Governance, and Decision Making into independent layers, RiskGraph AI delivers a system that is explainable, auditable, resilient, compliant, and ready for real-world payment risk operations.
