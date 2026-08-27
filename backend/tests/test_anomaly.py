from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

from app.services.anomaly import AnomalyDetector


def _fit_toy_forest():
    rng = np.random.RandomState(0)
    normal = rng.normal(0, 1, size=(200, 3))
    forest = IsolationForest(n_estimators=100, contamination=0.05, random_state=0)
    forest.fit(normal)
    return forest


def test_anomaly_explanation_flags_amount_deviation():
    forest = _fit_toy_forest()
    detector = AnomalyDetector(forest, ["f1", "f2", "f3"])
    txn = {"customer_avg_amount": 1000, "amount": 9000, "velocity_10m": 1}
    result = detector.score(np.array([5.0, 5.0, 5.0]), txn)
    assert result.amount_deviation_ratio == 9.0
    assert any("baseline" in e for e in result.explanation)


def test_anomaly_score_bounded_0_1():
    forest = _fit_toy_forest()
    detector = AnomalyDetector(forest, ["f1", "f2", "f3"])
    txn = {"customer_avg_amount": 1000, "amount": 1000, "velocity_10m": 1}
    result = detector.score(np.array([0.0, 0.0, 0.0]), txn)
    assert 0.0 <= result.anomaly_score <= 1.0


def test_no_deviation_explanation_when_normal():
    forest = _fit_toy_forest()
    detector = AnomalyDetector(forest, ["f1", "f2", "f3"])
    txn = {"customer_avg_amount": 1000, "amount": 1050, "velocity_10m": 1}
    result = detector.score(np.array([0.0, 0.1, -0.1]), txn)
    assert result.amount_deviation_ratio < 2
