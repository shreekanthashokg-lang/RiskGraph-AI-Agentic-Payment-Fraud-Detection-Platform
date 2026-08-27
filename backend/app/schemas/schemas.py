from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TransactionIn(BaseModel):
    transaction_id: str
    customer_id: str
    merchant_id: str
    amount: float
    currency: str = "INR"
    device_id: str
    ip_address: str
    beneficiary_id: str
    payment_method: str = "card"
    location: str = "Bengaluru"
    lat: float = 12.9716
    lon: float = 77.5946
    customer_age_days: int = 100
    customer_avg_amount: float = 2000.0
    customer_transaction_count: int = 10
    velocity_1m: int = 0
    velocity_10m: int = 0
    velocity_1h: int = 0
    velocity_24h: int = 0
    previous_fraud_alerts: int = 0
    chargeback_history: int = 0
    timestamp: Optional[datetime] = None
    # Optional fields available when scoring against the real-data model
    # (ml/artifacts/model.pkl trained on data/raw/transactions.csv - see
    # README "Real dataset training"). Safe to omit: engineer_features()
    # defaults country/bin_country geo-mismatch checks to the lat/lon
    # heuristic and all the flags below to 0/"unknown" when absent, so
    # existing callers that only send the original fields are unaffected.
    country: Optional[str] = None
    bin_country: Optional[str] = None
    channel: Optional[str] = None
    merchant_category: Optional[str] = None
    promo_used: int = 0
    avs_match: int = 1
    cvv_result: int = 1
    three_ds_flag: int = 0
    shipping_distance_km: float = 0.0


class RiskContributorOut(BaseModel):
    factor: str
    contribution_points: float
    detail: str


class RiskScoreOut(BaseModel):
    transaction_id: str
    risk_score: float
    risk_level: str
    ml_probability: float
    graph_risk: float
    anomaly_score: float
    rule_score: float
    historical_risk: float
    model_version: str
    policy_version: str
    contributors: list[RiskContributorOut]
    rule_hits: list[dict[str, Any]]
    degraded_mode: bool = False
    degraded_reason: Optional[str] = None


class ClusterOut(BaseModel):
    cluster_id: str
    cluster_size: int
    entities: list[str]
    risk_score: float
    risk_reasons: list[str]
    connected_fraud_cases: int


class InvestigateRequest(BaseModel):
    transaction_id: str


class EvidenceItem(BaseModel):
    source: str
    summary: str


class InvestigationReportOut(BaseModel):
    case_id: str
    transaction_id: str
    ai_mode: str  # LIVE or DEGRADED_AI_MODE
    evidence: list[EvidenceItem]
    inference_summary: str
    recommendation: str
    recommendation_rationale: str
    policy_citations: list[dict[str, Any]]
    requires_human_review: bool


class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approve|hold|escalate|reject)$")
    analyst: str
    notes: Optional[str] = None


class SimulationRequest(BaseModel):
    high_threshold: float = Field(ge=0, le=100)
    medium_threshold: float = Field(ge=0, le=100)
    low_threshold: float = Field(ge=0, le=100)


class SimulationResult(BaseModel):
    assumptions: str
    total_transactions: int
    fraud_detected: int
    false_positives: int
    flagged_volume: int
    manual_review_volume: int
    estimated_legit_recovered: int
    estimated_fraud_missed: int
    estimated_loss_prevented_inr: float
