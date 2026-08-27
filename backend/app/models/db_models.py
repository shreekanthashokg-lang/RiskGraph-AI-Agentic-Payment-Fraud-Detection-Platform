"""
RiskGraph AI - SQLAlchemy ORM models.

Defaults to SQLite for zero-setup local runs (see app/config.py); the same
models work unmodified against Postgres by changing DATABASE_URL, which is
what docker-compose.yml does for the containerized profile.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid() -> str:
    return uuid.uuid4().hex


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=_uuid)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    merchant_id = Column(String, index=True)
    device_id = Column(String, index=True)
    ip_address = Column(String, index=True)
    beneficiary_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    payment_method = Column(String)
    location = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, default="completed")
    raw_features = Column(JSON)  # snapshot of the feature row used for scoring

    risk_scores = relationship("RiskScore", back_populates="transaction")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(String, primary_key=True, default=_uuid)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), index=True)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    ml_probability = Column(Float)
    graph_risk = Column(Float)
    anomaly_score = Column(Float)
    rule_score = Column(Float)
    historical_risk = Column(Float)
    model_version = Column(String)
    policy_version = Column(String)
    contributors = Column(JSON)
    rule_hits = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="risk_scores")


class FraudCluster(Base):
    __tablename__ = "fraud_clusters"

    id = Column(String, primary_key=True, default=_uuid)
    cluster_id = Column(String, unique=True, index=True)
    cluster_size = Column(Integer)
    risk_score = Column(Float)
    risk_reasons = Column(JSON)
    entities = Column(JSON)
    connected_fraud_cases = Column(Integer)
    detected_at = Column(DateTime, default=datetime.utcnow)


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, unique=True, index=True, default=_uuid)
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), index=True)
    status = Column(String, default="OPEN")  # OPEN, EVIDENCE_GATHERED, RECOMMENDED, CLOSED
    ai_mode = Column(String, default="LIVE")  # LIVE or DEGRADED_AI_MODE
    agent_version = Column(String)
    evidence = Column(JSON)
    inference_summary = Column(Text)
    recommendation = Column(String)
    recommendation_rationale = Column(Text)
    policy_citations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    decisions = relationship("HumanDecision", back_populates="case")


class HumanDecision(Base):
    __tablename__ = "human_decisions"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("investigation_cases.case_id"), index=True)
    decision = Column(String, nullable=False)  # approve, hold, escalate, reject
    analyst = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("InvestigationCase", back_populates="decisions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=_uuid)
    transaction_id = Column(String, index=True)
    event_type = Column(String, nullable=False)
    actor = Column(String, default="system")
    payload = Column(JSON)
    failure_mode = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id = Column(String, primary_key=True, default=_uuid)
    doc_id = Column(String, unique=True, index=True)
    title = Column(String)
    version = Column(String)
    content = Column(Text)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True, default=_uuid)
    version = Column(String, unique=True)
    model_name = Column(String)
    metrics = Column(JSON)
    is_active = Column(Boolean, default=True)
    trained_at = Column(DateTime, default=datetime.utcnow)
