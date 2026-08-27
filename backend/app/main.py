"""
RiskGraph AI - FastAPI application entrypoint.

    uvicorn app.main:app --reload --port 8000

On startup: creates DB tables (SQLite by default, Postgres via
DATABASE_URL), loads the trained model artifact if present, loads
transaction history into the graph engine, and initializes the RAG policy
index. Every step degrades gracefully rather than crashing startup - see
app/state.py and POL-006.
"""
from __future__ import annotations

import logging

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import cases, risk, transactions
from app.api.audit_simulation import audit_router, simulation_router
from app.config import get_settings
from app.core.fallback import ServiceUnavailableError
from app.database import SessionLocal, init_db
from app.models.db_models import Transaction
from app.state import app_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("riskgraph.main")

settings = get_settings()

app = FastAPI(
    title="RiskGraph AI",
    description="Agentic real-time payment risk & fraud investigation platform.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(risk.router)
app.include_router(risk.graph_router)
app.include_router(risk.policies_router)
app.include_router(cases.router)
app.include_router(audit_router)
app.include_router(simulation_router)


@app.exception_handler(ServiceUnavailableError)
def service_unavailable_handler(request: Request, exc: ServiceUnavailableError):
    logger.error("service unavailable: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"error": "service_unavailable", "service": exc.service, "detail": exc.detail},
    )


@app.on_event("startup")
def on_startup():
    init_db()
    app_state.load_model()

    # Seed the graph engine from any transactions already in the DB, or from
    # the small demo CSV if the DB is empty (fresh local run).
    db = SessionLocal()
    try:
        rows = db.query(Transaction).all()
        if rows:
            df = pd.DataFrame([{
                "customer_id": r.customer_id, "device_id": r.device_id, "ip_address": r.ip_address,
                "beneficiary_id": r.beneficiary_id, "merchant_id": r.merchant_id,
                "is_fraud": (r.raw_features or {}).get("is_fraud", 0),
                "previous_fraud_alerts": (r.raw_features or {}).get("previous_fraud_alerts", 0),
            } for r in rows])
            app_state.build_graph(df)
            logger.info("Graph engine built from %d existing transactions.", len(rows))
        else:
            try:
                df = pd.read_csv("data/sample/transactions_demo_small.csv")
                app_state.build_graph(df)
                logger.info("Graph engine built from demo sample dataset (%d rows).", len(df))
            except FileNotFoundError:
                logger.warning("No demo dataset found; graph engine starts empty until transactions are scored.")
    finally:
        db.close()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_status": "degraded" if app_state.model_degraded else "healthy",
        "model_degraded_reason": app_state.model_degraded_reason,
        "rag_available": app_state.rag.available,
        "graph_node_count": app_state.graph_engine.graph.number_of_nodes(),
        "policy_version": app_state.rule_engine.policy_version,
    }


@app.get("/")
def root():
    return {"service": "RiskGraph AI", "docs": "/docs", "health": "/health"}
