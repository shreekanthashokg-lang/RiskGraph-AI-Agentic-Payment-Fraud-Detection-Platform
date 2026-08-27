from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.investigator import AGENT_VERSION, Investigator
from app.agent.tools import AgentToolbox
from app.core.audit import record_event
from app.database import get_db
from app.models.db_models import HumanDecision, InvestigationCase, Transaction
from app.schemas.schemas import DecisionIn, InvestigateRequest, InvestigationReportOut
from app.services.ml_scoring import score_transaction
from app.state import app_state

router = APIRouter(prefix="/api/v1", tags=["investigation"])


@router.post("/transactions/investigate", response_model=InvestigationReportOut)
def investigate(payload: InvestigateRequest, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter_by(transaction_id=payload.transaction_id).first()
    if not txn:
        raise HTTPException(404, "transaction not found")

    txn_dict = {
        "transaction_id": txn.transaction_id, "customer_id": txn.customer_id, "merchant_id": txn.merchant_id,
        "amount": txn.amount, "device_id": txn.device_id, "ip_address": txn.ip_address,
        "beneficiary_id": txn.beneficiary_id, **(txn.raw_features or {}),
    }
    result, degraded, reason = score_transaction(txn_dict, app_state)

    toolbox = AgentToolbox(
        db=db, graph_engine=app_state.graph_engine, rule_engine=app_state.rule_engine,
        rag=app_state.rag, risk_cache={payload.transaction_id: result},
    )
    outcome = Investigator(toolbox).investigate(payload.transaction_id, result, result.rule_hits)

    case = InvestigationCase(
        transaction_id=payload.transaction_id,
        status="RECOMMENDED",
        ai_mode=outcome.ai_mode,
        agent_version=AGENT_VERSION,
        evidence=outcome.evidence,
        inference_summary=outcome.inference_summary,
        recommendation=outcome.recommendation,
        recommendation_rationale=outcome.recommendation_rationale,
        policy_citations=outcome.policy_citations,
    )
    db.add(case)
    record_event(
        db, transaction_id=payload.transaction_id, event_type="INVESTIGATION_COMPLETED",
        payload={"ai_mode": outcome.ai_mode, "recommendation": outcome.recommendation},
        failure_mode="AI_DEGRADED" if outcome.ai_mode == "DEGRADED_AI_MODE" else None,
    )
    db.commit()
    db.refresh(case)

    return InvestigationReportOut(
        case_id=case.case_id, transaction_id=payload.transaction_id, ai_mode=outcome.ai_mode,
        evidence=outcome.evidence, inference_summary=outcome.inference_summary,
        recommendation=outcome.recommendation, recommendation_rationale=outcome.recommendation_rationale,
        policy_citations=outcome.policy_citations, requires_human_review=outcome.requires_human_review,
    )


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(InvestigationCase).filter_by(case_id=case_id).first()
    if not case:
        raise HTTPException(404, "case not found")
    decisions = db.query(HumanDecision).filter_by(case_id=case_id).all()
    return {
        "case_id": case.case_id, "transaction_id": case.transaction_id, "status": case.status,
        "ai_mode": case.ai_mode, "evidence": case.evidence, "inference_summary": case.inference_summary,
        "recommendation": case.recommendation, "recommendation_rationale": case.recommendation_rationale,
        "policy_citations": case.policy_citations,
        "decisions": [{"decision": d.decision, "analyst": d.analyst, "notes": d.notes,
                       "created_at": str(d.created_at)} for d in decisions],
    }


@router.post("/cases/{case_id}/decision")
def record_decision(case_id: str, payload: DecisionIn, db: Session = Depends(get_db)):
    case = db.query(InvestigationCase).filter_by(case_id=case_id).first()
    if not case:
        raise HTTPException(404, "case not found")

    decision = HumanDecision(case_id=case_id, decision=payload.decision, analyst=payload.analyst, notes=payload.notes)
    db.add(decision)
    case.status = "CLOSED"
    record_event(
        db, transaction_id=case.transaction_id, event_type="HUMAN_DECISION",
        payload={"decision": payload.decision, "analyst": payload.analyst}, actor=payload.analyst,
    )
    db.commit()
    return {"case_id": case_id, "status": "CLOSED", "decision": payload.decision}
