"""
Feature engineering for RiskGraph AI.

Transforms raw transaction rows into the numeric feature vector consumed by
the ML risk model. Kept dependency-light (pandas/numpy only) so it can be
imported by both the training pipeline (ml/train.py) and the online
inference service (backend/app/services/ml_scoring.py) without drift.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

NUMERIC_FEATURES = [
    "amount",
    "amount_to_baseline_ratio",
    "customer_age_days",
    "customer_transaction_count",
    "velocity_1m",
    "velocity_10m",
    "velocity_1h",
    "velocity_24h",
    "previous_fraud_alerts",
    "chargeback_history",
    "is_new_beneficiary",
    "is_suspicious_geo",
    # Card/checkout signals present in the real transactions.csv training set
    # (Aug 2026 update). Default to 0 for older callers/datasets that don't
    # have them so the pipeline stays backward compatible - see
    # dataset_adapter.py for how they're populated from real columns.
    "promo_used",
    "avs_match",
    "cvv_result",
    "three_ds_flag",
    "shipping_distance_km",
]

# Candidate categorical columns. Not every dataset has every one of these -
# engineer_features() fills any that are missing with "unknown" so
# training/serving always produce the same one-hot column set for whichever
# categoricals *are* available, rather than silently dropping signal or
# crashing on an unfamiliar schema.
CATEGORICAL_FEATURES = ["payment_method", "channel", "merchant_category"]

TARGET_COL = "is_fraud"


def _is_suspicious_geo(row: pd.Series) -> int:
    # Prefer a real card/geo mismatch signal when available (bin_country vs
    # country - the classic "card issued in one country, used in another"
    # fraud tell). Falls back to the lat/lon home-bounding-box heuristic used
    # by the original demo data when bin_country isn't present.
    if "bin_country" in row.index and pd.notna(row.get("bin_country")) and pd.notna(row.get("country")):
        return int(row.get("country") != row.get("bin_country"))
    lat, lon = row.get("lat", 20.0), row.get("lon", 78.0)
    if row.get("location") in ("Unknown", "Lagos"):
        return 1
    in_india_box = (6.0 <= lat <= 36.0) and (68.0 <= lon <= 98.0)
    return 0 if in_india_box else 1


def engineer_features(df: pd.DataFrame, known_beneficiaries: dict[str, set] | None = None) -> pd.DataFrame:
    """
    Add derived columns needed by the model. `known_beneficiaries` maps
    customer_id -> set of beneficiary_ids seen before this transaction; when
    not supplied (e.g. single-row online scoring) callers should pass the
    customer's historical beneficiary set explicitly per row via
    `is_new_beneficiary` already being present.
    """
    out = df.copy()

    if "amount_to_baseline_ratio" not in out.columns:
        out["amount_to_baseline_ratio"] = (out["amount"] / out["customer_avg_amount"].replace(0, np.nan)).fillna(1.0)

    if "is_new_beneficiary" not in out.columns:
        if known_beneficiaries is not None:
            def _check(row):
                seen = known_beneficiaries.get(row["customer_id"], set())
                return int(row["beneficiary_id"] not in seen)
            out["is_new_beneficiary"] = out.apply(_check, axis=1)
        else:
            out["is_new_beneficiary"] = 0

    if "is_suspicious_geo" not in out.columns:
        out["is_suspicious_geo"] = out.apply(_is_suspicious_geo, axis=1)

    for col in NUMERIC_FEATURES:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    return out


def to_model_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode categoricals and return the final numeric matrix, column-aligned."""
    feat = engineer_features(df)
    for col in CATEGORICAL_FEATURES:
        if col not in feat.columns:
            feat[col] = "unknown"
        feat[col] = feat[col].fillna("unknown").astype(str)
    dummies = pd.get_dummies(feat[CATEGORICAL_FEATURES], prefix=CATEGORICAL_FEATURES)
    matrix = pd.concat([feat[NUMERIC_FEATURES], dummies], axis=1)
    return matrix


def align_columns(matrix: pd.DataFrame, expected_columns: Iterable[str]) -> pd.DataFrame:
    """Ensure inference-time feature matrix has exactly the training-time columns."""
    expected_columns = list(expected_columns)
    for col in expected_columns:
        if col not in matrix.columns:
            matrix[col] = 0
    return matrix[expected_columns]
