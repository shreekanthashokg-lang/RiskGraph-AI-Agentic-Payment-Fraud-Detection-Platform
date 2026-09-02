"""
RiskGraph AI - Online scoring service.

Wraps the full detection pipeline (feature engineering -> ML -> graph ->
anomaly -> rules -> aggregation) for a single incoming transaction, with
explicit degraded-mode handling at every stage per POL-006.
"""
from __future__ import annotations

import logging

import pandas as pd

from app.services.anomaly import AnomalyResult
from app.services.feature_engineering import (
    align_columns,
    engineer_features,
    to_model_matrix,
)
from app.services.graph_engine import GraphFeatures
from app.services.risk_aggregator import AggregateRiskResult, aggregate_risk
from app.state import AppState

logger = logging.getLogger("riskgraph.scoring")


def score_transaction(txn: dict, state: AppState) -> tuple[AggregateRiskResult, bool, str | None]:
    """
    Returns (result, degraded, degraded_reason). `degraded=True` means one or
    more sub-systems fell back to a safe default rather than the full
    pipeline - the score is still returned (never blocked), but the caller
    should surface the degraded flag to the analyst/audit trail.
    """
    degraded = False
    reasons: list[str] = []

    row_df = pd.DataFrame([txn])

    # Feature engineering runs first and unconditionally: the rule engine,
    # graph engine and ML model all depend on derived fields (e.g.
    # amount_to_baseline_ratio, is_new_beneficiary, is_suspicious_geo) being
    # present on the txn dict, not just in the ML feature matrix.
    engineered_df = engineer_features(row_df)
    txn = {**txn, **engineered_df.iloc[0].to_dict()}

    # --- ML scoring (with model-unavailable fallback) ---
    if state.model_degraded or state.model_artifact is None:
        ml_probability = 0.0
        degraded = True
        reasons.append(f"ML model unavailable ({state.model_degraded_reason}); score omits ML signal")
        feature_row = None
    else:
        X = to_model_matrix(engineered_df)
        X = align_columns(X, state.model_artifact["feature_names"])
        try:
            ml_probability = float(state.model_artifact["model"].predict_proba(X)[:, 1][0])
            feature_row = X.values[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("ML scoring failed, falling back: %s", exc)
            ml_probability = 0.0
            degraded = True
            reasons.append(f"ML scoring raised an error at inference time: {exc}")
            feature_row = None

    # --- Graph scoring (with graph-unavailable fallback) ---
    try:
        graph_features = state.graph_engine.features_for_transaction(txn)
    except Exception as exc:  # noqa: BLE001
        logger.error("graph scoring failed, using last-known-safe default: %s", exc)
        degraded = True
        reasons.append(f"Graph engine unavailable: {exc}")
        graph_features = GraphFeatures(0, 0, 0, 0, None, 0, 0.0)

    # --- Anomaly scoring ---
    if feature_row is not None and state.anomaly_detector is not None:
        try:
            anomaly_result = state.anomaly_detector.score(feature_row, txn)
        except Exception as exc:  # noqa: BLE001
            logger.error("anomaly scoring failed: %s", exc)
            degraded = True
            reasons.append(f"Anomaly detector unavailable: {exc}")
            anomaly_result = AnomalyResult(0.0, False, 1.0, 1.0, ["Anomaly detection unavailable"])
    else:
        anomaly_result = AnomalyResult(0.0, False, 1.0, 1.0, ["Anomaly detection unavailable (no model loaded)"])

    # --- Rule engine (deterministic - always available) ---
    result = aggregate_risk(
        txn=txn,
        ml_probability=ml_probability,
        graph_features=graph_features,
        anomaly_result=anomaly_result,
        rule_engine=state.rule_engine,
        model_version=(state.model_artifact or {}).get("model_version", "unavailable"),
    )

    return result, degraded, "; ".join(reasons) if reasons else None
