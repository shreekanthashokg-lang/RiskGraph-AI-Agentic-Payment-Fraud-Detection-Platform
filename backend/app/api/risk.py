from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import RiskScore, Transaction
from app.state import app_state

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/summary")
def risk_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(Transaction.id)).scalar() or 0
    level_counts = dict(
        db.query(RiskScore.risk_level, func.count(RiskScore.id)).group_by(RiskScore.risk_level).all()
    )
    high_risk = level_counts.get("HIGH", 0)
    critical = level_counts.get("CRITICAL", 0)
    avg_score = db.query(func.avg(RiskScore.risk_score)).scalar() or 0
    return {
        "total_transactions": total,
        "high_risk_transactions": high_risk,
        "critical_alerts": critical,
        "fraud_rate_estimate": round((high_risk + critical) / total, 4) if total else 0.0,
        "average_risk_score": round(float(avg_score), 2),
        "risk_distribution": {
            "LOW": level_counts.get("LOW", 0), "MEDIUM": level_counts.get("MEDIUM", 0),
            "HIGH": high_risk, "CRITICAL": critical,
        },
        "model_status": "degraded" if app_state.model_degraded else "healthy",
    }


@router.get("/alerts")
def risk_alerts(limit: int = 25, min_level: str = "HIGH", db: Session = Depends(get_db)):
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    floor = order.get(min_level.upper(), 2)
    rows = (
        db.query(RiskScore, Transaction)
        .join(Transaction, Transaction.transaction_id == RiskScore.transaction_id)
        .order_by(RiskScore.created_at.desc())
        .limit(500)
        .all()
    )
    filtered = [(rs, t) for rs, t in rows if order.get(rs.risk_level, 0) >= floor][:limit]
    return [
        {
            "transaction_id": t.transaction_id, "amount": t.amount, "risk_score": rs.risk_score,
            "risk_level": rs.risk_level,
            "top_reason": (rs.contributors[0]["factor"] if rs.contributors else "n/a"),
            "status": t.status, "time": str(t.timestamp),
        }
        for rs, t in filtered
    ]


graph_router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@graph_router.get("/transaction/{transaction_id}")
def graph_for_transaction(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter_by(transaction_id=transaction_id).first()
    if not txn:
        return {"nodes": [], "edges": []}
    return app_state.graph_engine.neighborhood(f"customer:{txn.customer_id}", depth=2)


@graph_router.get("/clusters")
def fraud_clusters(min_size: int = 3):
    clusters = app_state.graph_engine.clusters(min_size=min_size)
    return [c.__dict__ for c in clusters[:50]]


policies_router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@policies_router.get("")
def list_policies():
    seen = {}
    for c in app_state.rag.chunks:
        seen[c.doc_id] = {"doc_id": c.doc_id, "title": c.title, "version": c.version, "category": c.category}
    return list(seen.values())
