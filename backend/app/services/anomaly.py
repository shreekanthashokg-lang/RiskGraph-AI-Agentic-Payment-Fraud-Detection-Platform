"""
RiskGraph AI - Anomaly Detection
-----------------------------------
Wraps the trained IsolationForest and adds explainable statistical
deviation features (e.g. "customer baseline Rs.8,500 vs current Rs.46,200,
5.43x deviation") so anomaly output is never a bare opaque score.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class AnomalyResult:
    anomaly_score: float  # normalized 0-1, higher = more anomalous
    is_outlier: bool
    amount_deviation_ratio: float
    velocity_deviation_ratio: float
    explanation: list[str]


class AnomalyDetector:
    def __init__(self, isolation_forest, feature_names: list[str]):
        self.iso = isolation_forest
        self.feature_names = feature_names

    def score(self, feature_row: np.ndarray, txn: dict) -> AnomalyResult:
        row_df = pd.DataFrame([feature_row], columns=self.feature_names)
        raw_score = self.iso.decision_function(row_df)[0]
        # decision_function: higher = more normal. Flip + normalize to 0-1.
        normalized = float(np.clip((0.5 - raw_score) * 2, 0, 1))
        is_outlier = self.iso.predict(row_df)[0] == -1

        baseline = max(float(txn.get("customer_avg_amount", 0)), 1e-6)
        amount = float(txn.get("amount", 0))
        amount_ratio = round(amount / baseline, 2)

        velocity = float(txn.get("velocity_10m", 0))
        velocity_ratio = round(velocity / 2.0, 2)  # 2 tx/10min treated as a normal baseline

        explanation = []
        if amount_ratio >= 2:
            explanation.append(
                f"Customer baseline Rs.{baseline:,.0f}; current amount Rs.{amount:,.0f} "
                f"({amount_ratio}x deviation)"
            )
        if velocity_ratio >= 3:
            explanation.append(f"{int(velocity)} transactions in the last 10 minutes ({velocity_ratio}x normal)")
        if is_outlier and not explanation:
            explanation.append("Flagged as a statistical outlier by the isolation forest model")
        if not explanation:
            explanation.append("No significant deviation from customer baseline detected")

        return AnomalyResult(
            anomaly_score=round(normalized, 4),
            is_outlier=bool(is_outlier),
            amount_deviation_ratio=amount_ratio,
            velocity_deviation_ratio=velocity_ratio,
            explanation=explanation,
        )
