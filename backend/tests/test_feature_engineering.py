from __future__ import annotations

import pandas as pd

from app.services.feature_engineering import align_columns, engineer_features, to_model_matrix


def test_amount_to_baseline_ratio_computed(normal_txn):
    df = pd.DataFrame([normal_txn])
    out = engineer_features(df.drop(columns=["amount_to_baseline_ratio"], errors="ignore"))
    assert "amount_to_baseline_ratio" in out.columns
    assert out.loc[0, "amount_to_baseline_ratio"] == 1.0


def test_suspicious_geo_flag(normal_txn):
    txn = dict(normal_txn)
    txn["location"] = "Unknown"
    df = pd.DataFrame([txn])
    out = engineer_features(df)
    assert out.loc[0, "is_suspicious_geo"] == 1


def test_domestic_geo_not_flagged(normal_txn):
    df = pd.DataFrame([normal_txn])
    out = engineer_features(df)
    assert out.loc[0, "is_suspicious_geo"] == 0


def test_to_model_matrix_one_hot_encodes_payment_method(normal_txn):
    df = pd.DataFrame([normal_txn])
    matrix = to_model_matrix(df)
    assert any(col.startswith("payment_method_") for col in matrix.columns)
    assert matrix.isna().sum().sum() == 0


def test_align_columns_adds_missing_and_drops_extra():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    aligned = align_columns(df, ["a", "d"])
    assert list(aligned.columns) == ["a", "d"]
    assert aligned.loc[0, "d"] == 0
