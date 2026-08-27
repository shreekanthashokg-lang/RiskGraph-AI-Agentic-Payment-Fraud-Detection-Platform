from __future__ import annotations

from app.services.anomaly import AnomalyResult
from app.services.graph_engine import GraphFeatures
from app.services.risk_aggregator import aggregate_risk
from app.services.rules_engine import RuleEngine

LOW_GRAPH = GraphFeatures(customer_degree=3, shared_device_count=0, shared_ip_count=0,
                           known_risk_neighbor_count=0, cluster_id=None, cluster_size=0, graph_risk_score=0.0)
HIGH_GRAPH = GraphFeatures(customer_degree=30, shared_device_count=15, shared_ip_count=12,
                            known_risk_neighbor_count=8, cluster_id="cluster_x", cluster_size=20, graph_risk_score=0.95)

LOW_ANOMALY = AnomalyResult(anomaly_score=0.05, is_outlier=False, amount_deviation_ratio=1.0,
                             velocity_deviation_ratio=1.0, explanation=["no deviation"])
HIGH_ANOMALY = AnomalyResult(anomaly_score=0.9, is_outlier=True, amount_deviation_ratio=8.0,
                              velocity_deviation_ratio=6.0, explanation=["large deviation"])


def test_low_risk_transaction_scores_low(normal_txn):
    engine = RuleEngine()
    result = aggregate_risk(normal_txn, ml_probability=0.02, graph_features=LOW_GRAPH,
                             anomaly_result=LOW_ANOMALY, rule_engine=engine, model_version="test-v1")
    assert result.risk_level == "LOW"
    assert result.risk_score < 30


def test_high_risk_transaction_scores_high_or_critical(suspicious_txn):
    engine = RuleEngine()
    result = aggregate_risk(suspicious_txn, ml_probability=0.93, graph_features=HIGH_GRAPH,
                             anomaly_result=HIGH_ANOMALY, rule_engine=engine, model_version="test-v1")
    assert result.risk_level in ("HIGH", "CRITICAL")
    assert result.risk_score > 60


def test_contributors_sum_does_not_exceed_100(suspicious_txn):
    engine = RuleEngine()
    result = aggregate_risk(suspicious_txn, ml_probability=0.93, graph_features=HIGH_GRAPH,
                             anomaly_result=HIGH_ANOMALY, rule_engine=engine, model_version="test-v1")
    assert sum(c.contribution_points for c in result.contributors) <= 100.01


def test_contributors_sorted_descending(suspicious_txn):
    engine = RuleEngine()
    result = aggregate_risk(suspicious_txn, ml_probability=0.93, graph_features=HIGH_GRAPH,
                             anomaly_result=HIGH_ANOMALY, rule_engine=engine, model_version="test-v1")
    points = [c.contribution_points for c in result.contributors]
    assert points == sorted(points, reverse=True)


def test_policy_and_model_version_recorded(normal_txn):
    engine = RuleEngine()
    result = aggregate_risk(normal_txn, ml_probability=0.02, graph_features=LOW_GRAPH,
                             anomaly_result=LOW_ANOMALY, rule_engine=engine, model_version="test-v1")
    assert result.policy_version == engine.policy_version
    assert result.model_version == "test-v1"
