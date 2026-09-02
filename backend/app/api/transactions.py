db_dependency = Depends(get_db)
from __future__ import annotations

from datetime import datetime, timezone


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.database import get_db
from app.models.db_models import RiskScore, Transaction
from app.schemas.schemas import RiskScoreOut, TransactionIn
from app.services.ml_scoring import score_transaction
from app.state import app_state




router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

@router.get("")
def list_transactions(limit: int = 50, db: Session = db_dependency):
    rows = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(limit).all()
    return [
        {"transaction_id": r.transaction_id, "customer_id": r.customer_id, "amount": r.amount,
         "timestamp": str(r.timestamp), "status": r.status} for r in rows
    ]


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, db: Session = db_dependency):
    txn = db.query(Transaction).filter_by(transaction_id=transaction_id).first()
    if not txn:
        raise HTTPException(404, "transaction not found")
    latest_score = (
        db.query(RiskScore)
        .filter_by(transaction_id=transaction_id)
        .order_by(RiskScore.created_at.desc())
        .first()
    )
    return {
        "transaction_id": txn.transaction_id, "customer_id": txn.customer_id, "amount": txn.amount,
        "currency": txn.currency, "device_id": txn.device_id, "ip_address": txn.ip_address,
        "beneficiary_id": txn.beneficiary_id, "timestamp": str(txn.timestamp), "status": txn.status,
        "latest_risk_score": latest_score.risk_score if latest_score else None,
        "latest_risk_level": latest_score.risk_level if latest_score else None,
    }


@router.post("/score", response_model=RiskScoreOut)
def score(payload: TransactionIn, db: Session = db_dependency):
    txn_dict = payload.model_dump()
    txn_dict["timestamp"] = (payload.timestamp or datetime.now(timezone.utc)).isoformat()


    existing = db.query(Transaction).filter_by(transaction_id=payload.transaction_id).first()
    if not existing:
        db.add(Transaction(
            transaction_id=payload.transaction_id, customer_id=payload.customer_id,
            merchant_id=payload.merchant_id, device_id=payload.device_id, ip_address=payload.ip_address,
            beneficiary_id=payload.beneficiary_id, amount=payload.amount, currency=payload.currency,
            payment_method=payload.payment_method, location=payload.location, lat=payload.lat, lon=payload.lon,
           timestamp=payload.timestamp or datetime.now(timezone.utc), raw_features=txn_dict,

        ))
        db.commit()

    result, degraded, reason = score_transaction(txn_dict, app_state)

    db.add(RiskScore(
        transaction_id=payload.transaction_id, risk_score=result.risk_score, risk_level=result.risk_level,
        ml_probability=result.ml_probability, graph_risk=result.graph_risk, anomaly_score=result.anomaly_score,
        rule_score=result.rule_score, historical_risk=result.historical_risk,
        model_version=result.model_version, policy_version=result.policy_version,
        contributors=[c.__dict__ for c in result.contributors], rule_hits=result.rule_hits,
    ))
    record_event(
        db, transaction_id=payload.transaction_id, event_type="RISK_SCORED",
        payload={"risk_score": result.risk_score, "risk_level": result.risk_level,
                 "model_version": result.model_version, "policy_version": result.policy_version},
        failure_mode=reason if degraded else None,
    )
    db.commit()

    return RiskScoreOut(
        transaction_id=payload.transaction_id, risk_score=result.risk_score, risk_level=result.risk_level,
        ml_probability=result.ml_probability, graph_risk=result.graph_risk, anomaly_score=result.anomaly_score,
        rule_score=result.rule_score, historical_risk=result.historical_risk,
        model_version=result.model_version, policy_version=result.policy_version,
        contributors=[c.__dict__ for c in result.contributors], rule_hits=result.rule_hits,
        degraded_mode=degraded, degraded_reason=reason,
    )
