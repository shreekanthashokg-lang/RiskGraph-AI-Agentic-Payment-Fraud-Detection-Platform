# RiskGraph AI

**Agentic Real-Time Payment Risk & Fraud Investigation Platform.**
Built for the Razorpay AI Buildathon 2026 — Track 2: AI Risk Manager.

RiskGraph AI combines transaction-level ML, behavioural anomaly detection,
a relationship graph, deterministic risk policies, and a grounded AI
investigation agent to detect coordinated fraud, investigate suspicious
transactions, and recommend auditable risk actions **with mandatory HUMAN
oversight**. It is not a chatbot, a generic RAG demo, or a bare classifier —
detection, investigation, policy, and decision-making are architecturally
separate layers, and the AI agent never moves money or finalizes a decision
on its own.

---

## WHY THIS MATTERS

Payment fraud is often a *network*, not an isolated bad transaction: shared
devices, shared IPs, shared beneficiaries, mule accounts. A transaction-level
model alone misses the ring. RiskGraph AI scores both the transaction and
its relationships, then hands HIGH/CRITICAL cases to an AI agent that
gathers real evidence (not fabricated), grounds its recommendation in
versioned policy documents via RAG, and requires a human analyst to make the
final call.

## Architecture

```
 Transaction ──▶ Event Ingestion API (FastAPI)
                        │
        ┌───────────────┼────────────────┐
        ▼                                 ▼
 Feature Engineering              Relationship Graph (NetworkX)
        │                                 │
        ▼                                 ▼
   ML Risk Model                   Graph Risk Engine
 (LogReg baseline,                 (shared device/IP,
  XGBoost + calibration)            cluster detection)
        │                                 │
        └───────────────┬─────────────────┘
                         ▼
                 Anomaly Detection (IsolationForest)
                         │
                         ▼
                 Rule Engine (versioned YAML policy)
                         │
                         ▼
                 Risk Aggregator → risk_score (0–100), LOW/MED/HIGH/CRITICAL
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        LOW / MEDIUM           HIGH / CRITICAL
              │                     │
        auto / step-up      AI Investigation Agent (Claude)
                                    │  (tool calling: get_transaction,
                                    │   get_graph_connections, search_policy…)
                                    ▼
                            RAG over policy docs
                                    │
                                    ▼
                     Evidence / Inference / Recommendation
                     (never auto-applied — human required)
                                    │
                                    ▼
                          Human Risk Analyst Decision
                                    │
                                    ▼
                            Immutable Audit Trail
```

**Hard boundary enforced throughout:** ML + graph + rules decide risk. The
agent investigates and recommends. A policy engine decides what actions are
*permitted*. A human decides for HIGH/CRITICAL. The agent can never move
money or skip that human step (see `data/policies/POL-007-agent-behavior.md`).

## What's real here (read this before the demo)

Everything below was actually run in development, not just written:

- **Synthetic data generator** — produces 9 distinct fraud archetypes,
  verified via `scripts/generate_synthetic_data.py`. Useful for demos and
  for the graph/agent walkthrough, but the shipped model is now trained on
  real data (below), not this generator's output.
- **Real dataset training (Aug 2026 update)** — `ml/train.py` now trains
  on a real, non-synthetic Kaggle-style dataset (`data/raw/transactions.csv`,
  299,695 rows, 6,000 customers, 2.21% real fraud rate). `ml/dataset_adapter.py`
  maps its raw columns onto RiskGraph AI's schema and computes
  `velocity_1m/10m/1h/24h` and `previous_fraud_alerts` for real from the
  dataset's own per-customer timestamps and fraud history (no leakage — each
  value only uses transactions strictly before the one being scored), and
  `is_suspicious_geo` from a real card-country vs. transaction-country
  mismatch signal. Two fields this dataset has no source for
  (`chargeback_history`, `is_new_beneficiary`) are left at 0 rather than
  invented — see the module docstring for the full accounting. **Actual test
  metrics** (RandomForest fallback, since this sandbox has no network to
  install `xgboost`): **ROC-AUC 0.982, PR-AUC 0.780, precision 0.80, recall
  0.73, F1 0.76** at the F1-maximizing threshold (0.389) — see
  `ml/artifacts/metrics.json`, `reports/classification_report.txt`, and the
  plots in both `ml/artifacts/` and `reports/`. Install `xgboost` locally
  (this environment couldn't reach PyPI) and re-run `ml/train.py` for the
  production-candidate boosted model — the pipeline already supports it,
  it just wasn't installed here.
- **Legacy synthetic-data path** — `ml/train.py` still works unmodified
  against `data/sample/transactions_synthetic.csv` if you want the original
  synthetic-data model back; pass that path via `--data`.
- **Graph engine** — tested against the synthetic ring data; correctly
  separates normal customers (graph risk ≈ 0) from coordinated fraud-ring
  members (graph risk = 1.0). One real bug was found and fixed during
  development: shared *merchants* were initially merging the entire customer
  base into a single fake cluster — cluster detection now deliberately
  excludes merchant edges (see the docstring in `graph_engine.py`).
- **Rule engine, anomaly detector, risk aggregator** — exercised together
  end-to-end on real sample transactions; scores are sensible and
  differentiated (normal ≈ 13/LOW, coordinated-cluster member ≈ 85/HIGH).
- **RAG policy retrieval** — TF-IDF over the 8 markdown policy docs in
  `data/policies/`; tested to correctly retrieve the right policy for a
  given query, entirely offline (no embedding API dependency).
- **Backend (FastAPI/SQLAlchemy/Claude agent)** — every file passes
  `python -m py_compile`; the scoring pipeline (`ml_scoring.py`) was
  exercised end-to-end including the degraded-mode fallback path using a
  duck-typed stand-in for application state, since this development
  environment couldn't install FastAPI/SQLAlchemy/anthropic directly.
  **Run `pip install -r backend/requirements.txt` and `pytest` yourself
  before the demo** to get a real, fully-installed pytest run rather than
  taking this on faith.
- **Frontend** — written against the exact backend API contract but not
  built/type-checked in this environment (no network for `npm install`
  here). Run `npm install && npm run build` locally — do this well before
  recording the demo video, not the night before.

## Quickstart (local, no Docker)

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in ANTHROPIC_API_KEY for LIVE agent mode

# 2. Train the model on the real dataset
cd ..
# Place the real dataset at data/raw/transactions.csv (already there if you
# unzipped this project as delivered), then:
python ml/train.py --data data/raw/transactions.csv
# Prints dataset diagnostics (rows, detected schema, engineered columns,
# missing values, class distribution), then trains, evaluates, and saves:
#   ml/artifacts/model.pkl              trained model + scaler + isolation forest
#   ml/artifacts/model_metadata.json    dataset/model/metrics summary
#   ml/artifacts/metrics.json           full metrics
#   ml/artifacts/*.png                  ROC, PR curve, confusion matrix, feature importance
#   reports/classification_report.txt   sklearn classification report
#   reports/metrics.json + *.png        mirrored copies for the reports/ convention
#   data/processed/transactions_processed.csv.gz   the adapted/engineered dataset

# (Optional) train on the original synthetic generator's data instead:
python scripts/generate_synthetic_data.py --n-customers 500 --n-transactions 20000
python ml/train.py --data data/sample/transactions_synthetic.csv

# 3. Run the API
cd backend
uvicorn app.main:app --reload --port 8000
# -> http://localhost:8000/docs for interactive OpenAPI docs
# -> http://localhost:8000/health to check model/graph/RAG status

# 4. Run the frontend (separate terminal)
cd ../frontend
npm install
npm run dev
# -> http://localhost:5173
```

Score a transaction and try THE AGENT:

```bash
curl -X POST http://localhost:8000/api/v1/transactions/score \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn_demo_1","customer_id":"cust_00001","merchant_id":"merch_01",
       "amount":45000,"device_id":"dev_ring","ip_address":"103.1.1.1",
       "beneficiary_id":"benef_ring","customer_avg_amount":2000,"previous_fraud_alerts":1,
       "velocity_10m":9}'

curl -X POST http://localhost:8000/api/v1/transactions/investigate \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn_demo_1"}'
```

Without `ANTHROPIC_API_KEY` set, `/investigate` still works — it returns a
`DEGRADED_AI_MODE` deterministic summary instead of failing (see
`data/policies/POL-006-failure-handling.md`).

### Real-time prediction, verified against the real-data model

Ran directly against the loaded `ml/artifacts/model.pkl` (no fabricated
numbers — this is copy-pasted output from an actual run in this
environment):

```
Low risk    — long-standing FR customer, small grocery purchase, card
              country matches, 3DS present:
              ML probability 0.03%   risk_score 12/100   LOW

High risk   — new customer, card issued in Nigeria used from the US,
              high transaction velocity, AVS/CVV/3DS all failed,
              8,200km shipping distance, 2 prior fraud alerts:
              ML probability 86.57%  risk_score 61/100   HIGH
              (rules R002/R003/R004/R005 all fired — new beneficiary +
              high amount, above-baseline amount, prior fraud, geo mismatch)

Medium/edge — above-average amount (4x customer baseline) but no other
              red flags, matching card/transaction country:
              ML probability 0.22%   risk_score 15/100   LOW
```

To score your own transaction against the trained model, the extra fields
this dataset adds (`country`, `bin_country`, `channel`, `merchant_category`,
`promo_used`, `avs_match`, `cvv_result`, `three_ds_flag`,
`shipping_distance_km`) are all optional on `POST /api/v1/transactions/score`
— omit any of them and they default to values that don't trigger the new
signals (see `backend/app/schemas/schemas.py`).

## Quickstart (DOCKER Compose)

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY
docker compose up --build
```

This runs a one-shot `trainer` job (generates data + trains the model into a
shared volume) before starting Postgres, Redis, the backend, and the
frontend. Re-run `docker compose run trainer` any time to regenerate.

## Repository layout

```
riskgraph-ai/
├── backend/app/
│   ├── main.py                  FastAPI app, startup wiring, /health
│   ├── state.py                 process-wide singletons (model, graph, RAG)
│   ├── config.py                env-var configuration (no hard-coded secrets)
│   ├── api/                     transactions, risk, graph, cases, audit, simulation
│   ├── models/db_models.py      SQLAlchemy ORM (SQLite locally, Postgres in Docker)
│   ├── schemas/schemas.py       Pydantic request/response contracts
│   ├── services/                feature engineering, ML scoring, graph engine,
│   │                            anomaly detection, rule engine, risk aggregator
│   ├── agent/                   Claude tool-calling investigator, tools, RAG
│   ├── core/                    retry/timeout/fallback, immutable audit trail
│   ├── policies/rules.yaml      versioned deterministic risk rules & thresholds
│   └── tests/                   pytest suite (see "Testing" below)
├── ml/train.py                  training pipeline → ml/artifacts/{model.pkl,metrics.json,*.png}
├── scripts/
│   ├── generate_synthetic_data.py   seeded synthetic transaction generator
│   └── download_dataset.sh          optional IEEE-CIS / PaySim setup (see licensing notes inside)
├── data/
│   ├── sample/                  small + full synthetic CSVs (committed, run instantly)
│   ├── policies/                8 markdown policy docs (RAG knowledge base)
│   └── raw/                     git-ignored — public datasets go here if you use them
├── frontend/src/
│   ├── pages/                   Dashboard, TransactionDetail, FraudNetwork, Simulator, Policies
│   ├── lib/api.ts                typed client matching the backend contract
│   └── components/
├── docker-compose.yml            postgres, redis, trainer, backend, frontend
└── .github/workflows/ci.yml      lint, train (smoke test), pytest, frontend build
```

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest -v --cov=app
```

Covers: feature engineering, rule engine (including the `also_requires`
gating logic), graph engine (including the merchant-sharing regression
test), anomaly explainability, risk aggregation, RAG retrieval and
citation dedup, the retry/fallback decorator, and agent tool dispatch
(schema validation, unknown-tool handling, no-fabricated-citation
behavior). Full DB-integration and live-LLM agent tests need
`ANTHROPIC_API_KEY` and a real DB session — see `tests/test_agent_tools.py`
docstring for what runs with fakes vs. what needs the full stack.

## Failure handling (demo this — it's a scored criterion)

Every subsystem degrades explicitly instead of failing silently:

| Failure | Behavior |
|---|---|
| `ANTHROPIC_API_KEY` unset / LLM call fails after retries | Agent falls back to a deterministic rule/graph summary, case marked `DEGRADED_AI_MODE`, still requires human review |
| Model artifact missing/corrupt | `/health` reports `model_status: degraded`; scoring continues using graph + rules only, `degraded_mode: true` on the response |
| Graph build fails | Falls back to a zero-risk `GraphFeatures` default rather than crashing scoring |
| RAG index empty/unavailable | `search_policy` tool returns `{"results": [], "note": "..."}`—agent is instructed never to fabricate a citation |
| DB unreachable | Bounded retry + backoff (`core/fallback.py`), then a structured 503, not a hang |

Try it: delete/rename `ml/artifacts/model.pkl` and hit `/health` — you'll see
`degraded` with a specific reason, and scoring still works.

## Security & Privacy

- No secrets in git — everything sensitive comes from `.env` / environment
  variables (see `.env.example`).
- Local/demo data is 100% synthetic; no real PII. See
  `data/policies/POL-008-privacy.md`.
- CORS is explicitly configured (`CORS_ALLOW_ORIGINS`), inputs are
  Pydantic-validated at every API boundary, and the audit trail has no
  update/delete endpoint from the app layer.
- This scaffold does not ship end-user authentication — the API/DB layer is
  structured to add it (role column on the analyst who records a decision,
  a natural place for an auth dependency in FastAPI) but wiring a real
  identity provider was out of scope for the timeline.

## Known Gaps / what I'd do with more time

- SHAP is referenced in the docs as the intended explainability method;
  the current scaffold uses model `feature_importances_` /
  `contribution_points` from the risk aggregator instead, because adding
  full SHAP value computation to the live scoring path needs more latency
  budget than a buildathon demo affords. Swapping it in is a contained
  change inside `services/anomaly.py` / a new `explainability.py`.
- Neo4j is not implemented — `GraphEngine` is an explicit ABC so a
  Neo4j-backed implementation can be dropped in without touching callers.
- The What-If Simulator's fraud-detected/missed figures only apply to
  transactions with a known ground-truth label (the synthetic dataset);
  this is disclosed in the `assumptions` field of every simulation
  response rather than silently averaged over unlabeled live traffic.
- No authentication/authorization middleware is wired up yet (see Security
  section above).

## License / DATASET attribution

This repo's code has no dataset bundled beyond the synthetic generator's
output (which is original, seeded, and committed for zero-setup local runs).
`scripts/download_dataset.sh` documents how to optionally pull IEEE-CIS
Fraud Detection and PaySim from Kaggle under their respective licenses — see
the comments in that script before using either dataset.
