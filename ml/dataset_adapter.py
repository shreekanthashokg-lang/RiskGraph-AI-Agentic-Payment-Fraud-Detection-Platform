"""
RiskGraph AI - real dataset adapter.

Maps the real Kaggle-style `transactions.csv` (299,695 rows, columns:
transaction_id, user_id, account_age_days, total_transactions_user,
avg_amount_user, amount, country, bin_country, channel, merchant_category,
promo_used, avs_match, cvv_result, three_ds_flag, transaction_time,
shipping_distance_km, is_fraud) onto the raw column names that
`backend/app/services/feature_engineering.py` expects (customer_id,
customer_age_days, customer_avg_amount, customer_transaction_count, ...),
and computes the velocity / history features for real instead of leaving
them at their zero defaults.

Every derived feature here is computed ONLY from information that would
have been available at transaction time (strictly-prior rows for the same
user), so there is no target leakage:

  * velocity_1m / 10m / 1h / 24h: count of that user's OTHER transactions in
    the trailing window before this transaction's timestamp (computed from
    real `transaction_time` values in the dataset - this is genuine
    behavioural signal, not synthetic).
  * previous_fraud_alerts: running count of that user's own prior
    transactions that were labelled fraud, using only rows strictly earlier
    in time (`shift(1).cumsum()`), never the current row's label.
  * is_suspicious_geo: 1 when the card's issuing country (`bin_country`)
    differs from the transaction country (`country`) - a real geo-mismatch
    signal in this dataset (fraud rate ~11.3% on mismatches vs ~1.4%
    otherwise).
  * chargeback_history: this dataset has no separate chargeback field, so
    it is left at 0 rather than duplicating previous_fraud_alerts under a
    different name - that would double-count the same signal, not add new
    information.
  * is_new_beneficiary: this dataset has no beneficiary/payee concept, left
    at 0 (documented limitation, not fabricated).
  * payment_method: this dataset has no true payment-instrument field. It is
    NOT invented from `channel` (channel = web/app, a different concept).
    Left absent so `to_model_matrix` fills it with the neutral "unknown"
    category; `channel` and `merchant_category` carry the real categorical
    signal instead.

Run standalone to inspect the adapted output:
    python ml/dataset_adapter.py --data data/raw/transactions.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

RAW_TRANSACTIONS_SCHEMA_COLUMNS = {
    "user_id", "account_age_days", "total_transactions_user", "avg_amount_user",
    "transaction_time", "bin_country",
}


def is_raw_transactions_csv(df: pd.DataFrame) -> bool:
    """Detect the real transactions.csv schema vs. an already-engineered sample file."""
    return RAW_TRANSACTIONS_SCHEMA_COLUMNS.issubset(set(df.columns))


def _velocity_counts(group: pd.DataFrame) -> pd.DataFrame:
    """Per-user trailing-window transaction counts, each window excluding the
    current row itself (closed='left') so it only reflects transactions
    strictly before this one - exactly what would be known in real time."""
    g = group.set_index("transaction_time")
    out = pd.DataFrame(index=g.index)
    for label, window in [
        ("velocity_1m", "1min"),
        ("velocity_10m", "10min"),
        ("velocity_1h", "1h"),
        ("velocity_24h", "24h"),
    ]:
        out[label] = g["transaction_id"].rolling(window, closed="left").count().fillna(0.0)
    out["transaction_id"] = g["transaction_id"].values
    return out.reset_index(drop=True)


def adapt_transactions_csv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- rename onto the app's raw schema ---
    df = df.rename(columns={
        "user_id": "customer_id",
        "account_age_days": "customer_age_days",
        "total_transactions_user": "customer_transaction_count",
        "avg_amount_user": "customer_avg_amount",
    })
    df["transaction_time"] = pd.to_datetime(df["transaction_time"], utc=True)

    # --- real velocity features, computed per customer from actual timestamps ---
    df = df.sort_values(["customer_id", "transaction_time"]).reset_index(drop=True)
    vel = (
        df[["customer_id", "transaction_id", "transaction_time"]]
        .groupby("customer_id", group_keys=False)
        .apply(_velocity_counts, include_groups=False)
        .reset_index(drop=True)
    )
    df = df.drop(columns=["transaction_id"]).reset_index(drop=True)
    df = pd.concat([df, vel[["velocity_1m", "velocity_10m", "velocity_1h", "velocity_24h"]]], axis=1)
    df["transaction_id"] = vel["transaction_id"].values

    # --- leakage-safe history feature: prior fraud count for this customer only ---
    df["previous_fraud_alerts"] = (
        df.groupby("customer_id")["is_fraud"].transform(lambda s: s.shift(1).fillna(0).cumsum())
    )
    # No separate chargeback signal in this dataset - left at 0 rather than
    # duplicating previous_fraud_alerts (see module docstring).
    df["chargeback_history"] = 0
    df["is_new_beneficiary"] = 0  # no beneficiary concept in this dataset

    # --- real geo-mismatch signal ---
    df["is_suspicious_geo"] = (df["country"] != df["bin_country"]).astype(int)

    df["timestamp"] = df["transaction_time"]
    return df


def load_and_adapt(path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Load a dataset and adapt it if it matches a known raw schema.
    Returns (adapted_df, report) where report has the diagnostics the
    training CLI prints (rows/cols, detected schema, dropped cols, etc.)."""
    path = Path(path)
    raw = pd.read_csv(path)
    report: dict = {
        "dataset_path": str(path),
        "raw_rows": len(raw),
        "raw_columns": len(raw.columns),
        "raw_column_names": list(raw.columns),
    }

    if is_raw_transactions_csv(raw):
        report["detected_schema"] = "real_transactions_csv (payment-fraud, raw)"
        adapted = adapt_transactions_csv(raw)
        report["engineered_columns_added"] = [
            "velocity_1m", "velocity_10m", "velocity_1h", "velocity_24h",
            "previous_fraud_alerts", "is_suspicious_geo",
        ]
        report["columns_defaulted_zero_no_source_signal"] = [
            "chargeback_history", "is_new_beneficiary",
        ]
        report["columns_intentionally_not_fabricated"] = ["payment_method"]
    else:
        report["detected_schema"] = "already-engineered / sample schema (no adaptation needed)"
        adapted = raw

    report["adapted_rows"] = len(adapted)
    report["adapted_columns"] = len(adapted.columns)
    return adapted, report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    args = ap.parse_args()
    adapted_df, report = load_and_adapt(args.data)
    import json
    print(json.dumps(report, indent=2, default=str))
    print(adapted_df.head(3).to_string())
