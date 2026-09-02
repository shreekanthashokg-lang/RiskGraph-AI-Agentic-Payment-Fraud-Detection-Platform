from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.audit import get_audit_trail
from app.database import get_db
from app.models.db_models import RiskScore, Transaction
from app.schemas.schemas import SimulationRequest, SimulationResult

# Define reusable dependency once
db_dependency = Depends(get_db)

audit_router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@audit_router.get("/{transaction_id}")
def audit_for_transaction(transaction_id: str, db: Session = db_dependency):
    events = get_audit_trail(db, transaction_id)
    return [
        {"event_type": e.event_type, "actor": e.actor, "payload": e.payload,
         "failure_mode": e.failure_mode, "created_at": str(e.created_at)}
        for e in events
    ]


simulation_router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


@simulation_router.post("", response_model=SimulationResult)
def simulate(payload: SimulationRequest, db: Session = db_dependency):
    """
    Recomputes historical decisions under hypothetical thresholds. All
    financial figures are explicitly labeled ESTIMATES derived from actual
    historical scores in the database - not invented numbers - and the
    calculation is shown via `assumptions`.
    """
    rows = (
        db.query(RiskScore, Transaction)
        .join(Transaction, Transaction.transaction_id == RiskScore.transaction_id)
        .all()
    )
    total = len(rows)
    if total == 0:
        return SimulationResult(
            assumptions="No historical scored transactions available yet - score some transactions first.",
            total_transactions=0, fraud_detected=0, false_positives=0, flagged_volume=0,
            manual_review_volume=0, estimated_legit_recovered=0, estimated_fraud_missed=0,
            estimated_loss_prevented_inr=0.0,
        )

    def level_for(score: float) -> str:
        if score <= payload.low_threshold:
            return "LOW"
        if score <= payload.medium_threshold:
            return "MEDIUM"
        if score <= payload.high_threshold:
            return "HIGH"
        return "CRITICAL"

    flagged = 0
    manual_review = 0
    labeled_total = 0
    fraud_detected = 0
    false_positives = 0
    fraud_missed = 0
    loss_prevented = 0.0

    for rs, txn in rows:
        new_level = level_for(rs.risk_score)
        if new_level in ("HIGH", "CRITICAL"):
            flagged += 1
        if new_level in ("MEDIUM", "HIGH", "CRITICAL"):
            manual_review += 1

        label = (txn.raw_features or {}).get("is_fraud")
        if label is None:
            continue
        labeled_total += 1
        is_fraud = int(label) == 1
        would_block = new_level in ("HIGH", "CRITICAL")
        if is_fraud and would_block:
            fraud_detected += 1
            loss_prevented += txn.amount
        elif is_fraud and not would_block:
            fraud_missed += 1
        elif not is_fraud and would_block:
            false_positives += 1

    legit_recovered = max(0, total - flagged - fraud_missed)

    assumptions = (
        f"Recomputed risk_level for all {total} historically scored transactions using the proposed "
        f"thresholds (LOW<={payload.low_threshold}, MEDIUM<={payload.medium_threshold}, "
        f"HIGH<={payload.high_threshold}, else CRITICAL). Fraud-detected/missed/false-positive counts "
        f"and loss-prevented are computed only over the {labeled_total} transactions with a known "
        f"ground-truth label (synthetic demo data); unlabeled live transactions are excluded from those "
        f"three figures and only counted in flagged/manual-review volume. These are ESTIMATES, not guarantees."
    )

    return SimulationResult(
        assumptions=assumptions,
        total_transactions=total,
        fraud_detected=fraud_detected,
        false_positives=false_positives,
        flagged_volume=flagged,
        manual_review_volume=manual_review,
        estimated_legit_recovered=legit_recovered,
        estimated_fraud_missed=fraud_missed,
        estimated_loss_prevented_inr=round(loss_prevented, 2),
    )
