from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def sample_transactions() -> pd.DataFrame:
    repo_root = BACKEND_DIR.parent
    csv_path = repo_root / "data" / "sample" / "transactions_demo_small.csv"
    if not csv_path.exists():
        pytest.skip(f"sample dataset not found at {csv_path} - run scripts/generate_synthetic_data.py first")
    return pd.read_csv(csv_path)


@pytest.fixture
def normal_txn() -> dict:
    return {
        "transaction_id": "txn_test_normal",
        "customer_id": "cust_00001",
        "merchant_id": "merch_0001",
        "amount": 1500.0,
        "customer_avg_amount": 1500.0,
        "customer_age_days": 400,
        "customer_transaction_count": 50,
        "device_id": "dev_normal",
        "ip_address": "49.1.1.1",
        "beneficiary_id": "benef_known",
        "location": "Bengaluru",
        "lat": 12.9716,
        "lon": 77.5946,
        "payment_method": "upi",
        "velocity_1m": 0, "velocity_10m": 1, "velocity_1h": 2, "velocity_24h": 4,
        "previous_fraud_alerts": 0,
        "chargeback_history": 0,
        "is_new_beneficiary": 0,
        "is_fraud": 0,
    }


@pytest.fixture
def suspicious_txn(normal_txn) -> dict:
    txn = dict(normal_txn)
    txn.update({
        "transaction_id": "txn_test_suspicious",
        "amount": 25000.0,  # ~16.7x baseline
        "velocity_10m": 12,
        "previous_fraud_alerts": 2,
        "is_new_beneficiary": 1,
        "beneficiary_id": "benef_new",
        "is_fraud": 1,
    })
    return txn
