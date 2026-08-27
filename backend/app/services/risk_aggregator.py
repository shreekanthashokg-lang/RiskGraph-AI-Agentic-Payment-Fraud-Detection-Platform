"""
RiskGraph AI - Risk Aggregator
---------------------------------
Combines normalized signals from every detection layer into one auditable
risk score (0-100) and a policy-driven risk level. Weights and thresholds
live in `rules.yaml` (see RuleEngine) - nothing here is hard-coded or
arbitrary at runtime; the weights are simply read from config.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.anomaly import AnomalyResult
from app.services.graph_engine import GraphFeatures
from app.services.rules_engine import RuleEngine, RuleEngineResult


@dataclass
class RiskContributor:
    factor: str
    contribution_points: float
    detail: str


@dataclass
class AggregateRiskResult:
    risk_score: float  # 0-100
    risk_level: str
    policy_version: str
    model_version: str
    contributors: list[RiskContributor]
    ml_probability: float
    graph_risk: float
    anomaly_score: float
    rule_score: float
    historical_risk: float
    rule_hits: list[dict]


def _historical_risk(txn: dict) -> float:
    """0-1 normalized signal from prior fraud alerts / chargebacks on the account."""
    alerts = min(int(txn.get("previous_fraud_alerts", 0)), 5)
    chargebacks = min(int(txn.get("chargeback_history", 0)), 5)
    return round(min(1.0, 0.15 * alerts + 0.1 * chargebacks), 4)


def aggregate_risk(
    txn: dict,
    ml_probability: float,
    graph_features: GraphFeatures,
    anomaly_result: AnomalyResult,
    rule_engine: RuleEngine,
    model_version: str,
) -> AggregateRiskResult:
    rule_result: RuleEngineResult = rule_engine.evaluate(txn)
    historical = _historical_risk(txn)

    w = rule_engine.weights
    normalized_rule = rule_result.rule_score / 100.0

    raw_score_0_1 = (
        w["ml_probability"] * ml_probability
        + w["graph_risk"] * graph_features.graph_risk_score
        + w["anomaly_score"] * anomaly_result.anomaly_score
        + w["rule_score"] * normalized_rule
        + w["historical_risk"] * historical
    )
    risk_score = round(min(100.0, raw_score_0_1 * 100), 2)
    risk_level = rule_engine.risk_level(risk_score)

    contributors = [
        RiskContributor(
            factor="ML model probability",
            contribution_points=round(w["ml_probability"] * ml_probability * 100, 2),
            detail=f"Calibrated fraud probability: {ml_probability:.2%}",
        ),
        RiskContributor(
            factor="Graph / relationship risk",
            contribution_points=round(w["graph_risk"] * graph_features.graph_risk_score * 100, 2),
            detail=(
                f"{graph_features.shared_device_count} customers share this device, "
                f"{graph_features.shared_ip_count} share this IP, "
                f"{graph_features.known_risk_neighbor_count} known-risk neighbors"
            ),
        ),
        RiskContributor(
            factor="Behavioural anomaly",
            contribution_points=round(w["anomaly_score"] * anomaly_result.anomaly_score * 100, 2),
            detail="; ".join(anomaly_result.explanation),
        ),
        RiskContributor(
            factor="Rule violations",
            contribution_points=round(w["rule_score"] * normalized_rule * 100, 2),
            detail=(
                ", ".join(f"{h.rule_id}: {h.description}" for h in rule_result.triggered)
                if rule_result.triggered else "No deterministic rules triggered"
            ),
        ),
        RiskContributor(
            factor="Historical risk",
            contribution_points=round(w["historical_risk"] * historical * 100, 2),
            detail=(
                f"{txn.get('previous_fraud_alerts', 0)} prior fraud alert(s), "
                f"{txn.get('chargeback_history', 0)} chargeback(s)"
            ),
        ),
    ]
    contributors.sort(key=lambda c: c.contribution_points, reverse=True)

    return AggregateRiskResult(
        risk_score=risk_score,
        risk_level=risk_level,
        policy_version=rule_result.policy_version,
        model_version=model_version,
        contributors=contributors,
        ml_probability=round(ml_probability, 4),
        graph_risk=graph_features.graph_risk_score,
        anomaly_score=anomaly_result.anomaly_score,
        rule_score=normalized_rule,
        historical_risk=historical,
        rule_hits=[{"id": h.rule_id, "description": h.description, "weight": h.weight} for h in rule_result.triggered],
    )
