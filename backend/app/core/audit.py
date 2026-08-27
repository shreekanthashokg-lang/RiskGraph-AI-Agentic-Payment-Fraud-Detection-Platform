"""
RiskGraph AI - Audit Trail.

Every risk decision, investigation, and human override is written here.
Records are append-only from the application layer: there is no update/
delete endpoint for audit_events, so the normal frontend workflow cannot
edit history (DB-level immutability/retention policies are a deployment
concern - see README "Security & Privacy").
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.db_models import AuditEvent


def record_event(
    db: Session,
    transaction_id: str,
    event_type: str,
    payload: dict[str, Any],
    actor: str = "system",
    failure_mode: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        transaction_id=transaction_id,
        event_type=event_type,
        actor=actor,
        payload=payload,
        failure_mode=failure_mode,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_audit_trail(db: Session, transaction_id: str) -> list[AuditEvent]:
    return (
        db.query(AuditEvent)
        .filter(AuditEvent.transaction_id == transaction_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
