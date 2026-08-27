from __future__ import annotations

import pandas as pd

from app.services.feature_engineering import engineer_features
from app.services.rules_engine import RuleEngine


def _engineered(txn: dict) -> dict:
    """Rule engine consumes engineered fields (amount_to_baseline_ratio, etc.) -
    mirrors what app/services/ml_scoring.py does before calling the rule engine."""
    return engineer_features(pd.DataFrame([txn])).iloc[0].to_dict()


def test_normal_transaction_triggers_no_rules(normal_txn):
    engine = RuleEngine()
    result = engine.evaluate(_engineered(normal_txn))
    assert result.triggered == []
    assert result.rule_score == 0.0


def test_suspicious_transaction_triggers_multiple_rules(suspicious_txn):
    engine = RuleEngine()
    result = engine.evaluate(_engineered(suspicious_txn))
    triggered_ids = {h.rule_id for h in result.triggered}
    assert "R001" in triggered_ids  # velocity
    assert "R002" in triggered_ids  # new beneficiary + high amount
    assert "R003" in triggered_ids  # baseline deviation
    assert "R004" in triggered_ids  # prior fraud alerts
    assert result.rule_score > 0


def test_policy_version_present():
    engine = RuleEngine()
    result = engine.evaluate({})
    assert result.policy_version == "rules-v1.2026-08-22"


def test_risk_level_bands():
    engine = RuleEngine()
    assert engine.risk_level(10) == "LOW"
    assert engine.risk_level(45) == "MEDIUM"
    assert engine.risk_level(75) == "HIGH"
    assert engine.risk_level(95) == "CRITICAL"


def test_also_requires_condition_gates_rule(normal_txn):
    # is_new_beneficiary=1 alone should NOT trigger R002 without the amount spike
    engine = RuleEngine()
    txn = dict(normal_txn)
    txn["is_new_beneficiary"] = 1
    result = engine.evaluate(_engineered(txn))
    assert "R002" not in {h.rule_id for h in result.triggered}
