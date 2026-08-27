"""
RiskGraph AI - Synthetic Transaction Generator
------------------------------------------------
Generates a reproducible (seeded) synthetic payment transaction dataset
covering normal behaviour and several fraud archetypes:

  - normal transactions
  - unusual amount (baseline deviation)
  - rapid transaction bursts (velocity abuse)
  - shared device across many customers
  - shared IP across many customers
  - new beneficiary + high amount
  - suspicious / mismatched geography
  - account takeover (device+IP change mid-session)
  - coordinated fraud cluster (mule ring: shared device/IP/beneficiary)
  - repeated merchant abuse

No real PII is used. All identifiers are synthetic.

Usage:
    python generate_synthetic_data.py --n-customers 500 --n-transactions 20000 --seed 42
"""
from __future__ import annotations

import argparse
import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

CITIES = [
    ("Bengaluru", 12.9716, 77.5946), ("Mumbai", 19.0760, 72.8777),
    ("Delhi", 28.7041, 77.1025), ("Hyderabad", 17.3850, 78.4867),
    ("Chennai", 13.0827, 80.2707), ("Pune", 18.5204, 73.8567),
    ("Kolkata", 22.5726, 88.3639), ("Ahmedabad", 23.0225, 72.5714),
]
SUSPICIOUS_CITIES = [("Lagos", 6.5244, 3.3792), ("Unknown", 0.0, 0.0)]

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet"]
CURRENCY = "INR"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class EntityPool:
    """Pool of customers/devices/ips/merchants/beneficiaries with realistic reuse."""

    def __init__(self, rng: random.Random, n_customers: int):
        self.rng = rng
        self.customers = [self._make_customer(i) for i in range(n_customers)]
        self.merchants = [_new_id("merch") for _ in range(max(20, n_customers // 15))]
        # A small pool of "mule ring" shared identifiers used to build coordinated clusters
        self.ring_devices = [_new_id("dev") for _ in range(3)]
        self.ring_ips = [f"103.{rng.randint(1,254)}.{rng.randint(1,254)}.{rng.randint(1,254)}" for _ in range(3)]
        self.ring_beneficiary = _new_id("benef")
        self.ring_customers = self.rng.sample(self.customers, k=min(12, len(self.customers)))

    def _make_customer(self, idx: int) -> dict:
        city = self.rng.choice(CITIES)
        return {
            "customer_id": f"cust_{idx:05d}",
            "device_id": _new_id("dev"),
            "ip_address": f"49.{self.rng.randint(1,254)}.{self.rng.randint(1,254)}.{self.rng.randint(1,254)}",
            "home_city": city,
            "avg_amount": round(self.rng.uniform(300, 6000), 2),
            "account_age_days": self.rng.randint(5, 2500),
            "beneficiaries": [_new_id("benef") for _ in range(self.rng.randint(1, 4))],
            "previous_fraud_alerts": 0,
            "chargeback_history": 0,
        }


def _velocity_window_counts(rng: random.Random, burst: bool) -> dict:
    if burst:
        return {
            "velocity_1m": rng.randint(3, 9),
            "velocity_10m": rng.randint(8, 20),
            "velocity_1h": rng.randint(15, 40),
            "velocity_24h": rng.randint(20, 60),
        }
    return {
        "velocity_1m": rng.randint(0, 1),
        "velocity_10m": rng.randint(0, 2),
        "velocity_1h": rng.randint(0, 4),
        "velocity_24h": rng.randint(1, 10),
    }


def generate(n_customers: int, n_transactions: int, seed: int, fraud_rate: float) -> pd.DataFrame:
    rng = random.Random(seed)
    np.random.seed(seed)
    pool = EntityPool(rng, n_customers)

    start_time = datetime(2026, 6, 1)
    rows = []

    n_fraud = int(n_transactions * fraud_rate)
    n_normal = n_transactions - n_fraud

    fraud_types = [
        "unusual_amount", "velocity_burst", "shared_device", "shared_ip",
        "new_beneficiary_high_amount", "suspicious_geo", "account_takeover",
        "coordinated_cluster", "merchant_abuse",
    ]

    def base_row(customer: dict, ts: datetime) -> dict:
        return {
            "transaction_id": _new_id("txn"),
            "customer_id": customer["customer_id"],
            "merchant_id": rng.choice(pool.merchants),
            "amount": round(max(50, np.random.normal(customer["avg_amount"], customer["avg_amount"] * 0.25)), 2),
            "currency": CURRENCY,
            "timestamp": ts.isoformat(),
            "device_id": customer["device_id"],
            "ip_address": customer["ip_address"],
            "location": customer["home_city"][0],
            "lat": customer["home_city"][1],
            "lon": customer["home_city"][2],
            "payment_method": rng.choice(PAYMENT_METHODS),
            "beneficiary_id": rng.choice(customer["beneficiaries"]),
            "transaction_status": "completed",
            "customer_age_days": customer["account_age_days"],
            "customer_avg_amount": customer["avg_amount"],
            "customer_transaction_count": rng.randint(1, 500),
            "previous_fraud_alerts": customer["previous_fraud_alerts"],
            "chargeback_history": customer["chargeback_history"],
            "is_fraud": 0,
            "fraud_type": "none",
            **_velocity_window_counts(rng, burst=False),
        }

    # --- normal transactions ---
    for _ in range(n_normal):
        customer = rng.choice(pool.customers)
        ts = start_time + timedelta(seconds=rng.randint(0, 60 * 60 * 24 * 60))
        rows.append(base_row(customer, ts))

    # --- fraud pattern transactions ---
    for i in range(n_fraud):
        ftype = fraud_types[i % len(fraud_types)]
        ts = start_time + timedelta(seconds=rng.randint(0, 60 * 60 * 24 * 60))

        if ftype == "coordinated_cluster":
            customer = rng.choice(pool.ring_customers)
            row = base_row(customer, ts)
            row["device_id"] = rng.choice(pool.ring_devices)
            row["ip_address"] = rng.choice(pool.ring_ips)
            row["beneficiary_id"] = pool.ring_beneficiary
            row["amount"] = round(rng.uniform(8000, 45000), 2)
            row.update(_velocity_window_counts(rng, burst=True))
            row["previous_fraud_alerts"] = rng.randint(0, 2)
        else:
            customer = rng.choice(pool.customers)
            row = base_row(customer, ts)

            if ftype == "unusual_amount":
                row["amount"] = round(customer["avg_amount"] * rng.uniform(5, 12), 2)
            elif ftype == "velocity_burst":
                row.update(_velocity_window_counts(rng, burst=True))
            elif ftype == "shared_device":
                row["device_id"] = rng.choice(pool.ring_devices)
            elif ftype == "shared_ip":
                row["ip_address"] = rng.choice(pool.ring_ips)
            elif ftype == "new_beneficiary_high_amount":
                row["beneficiary_id"] = _new_id("benef")
                row["amount"] = round(customer["avg_amount"] * rng.uniform(4, 9), 2)
            elif ftype == "suspicious_geo":
                city = rng.choice(SUSPICIOUS_CITIES)
                row["location"], row["lat"], row["lon"] = city
            elif ftype == "account_takeover":
                row["device_id"] = _new_id("dev")
                row["ip_address"] = f"185.{rng.randint(1,254)}.{rng.randint(1,254)}.{rng.randint(1,254)}"
                row["beneficiary_id"] = _new_id("benef")
                row["amount"] = round(customer["avg_amount"] * rng.uniform(3, 8), 2)
            elif ftype == "merchant_abuse":
                row["merchant_id"] = pool.merchants[0]
                row.update(_velocity_window_counts(rng, burst=True))

        row["is_fraud"] = 1
        row["fraud_type"] = ftype
        rows.append(row)

    df = pd.DataFrame(rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df["amount_to_baseline_ratio"] = (df["amount"] / df["customer_avg_amount"]).round(3)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-customers", type=int, default=500)
    ap.add_argument("--n-transactions", type=int, default=20000)
    ap.add_argument("--fraud-rate", type=float, default=0.035, help="Fraction of rows that are fraudulent")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="data/sample/transactions_synthetic.csv")
    ap.add_argument("--out-small", type=str, default="data/sample/transactions_demo_small.csv")
    args = ap.parse_args()

    df = generate(args.n_customers, args.n_transactions, args.seed, args.fraud_rate)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    # Small demo slice for instant local runs (kept in git)
    demo = pd.concat([
        df[df.is_fraud == 0].sample(min(400, (df.is_fraud == 0).sum()), random_state=args.seed),
        df[df.is_fraud == 1].sample(min(100, (df.is_fraud == 1).sum()), random_state=args.seed),
    ]).sample(frac=1.0, random_state=args.seed).reset_index(drop=True)
    demo.to_csv(args.out_small, index=False)

    stats = {
        "rows": len(df),
        "fraud_rows": int(df.is_fraud.sum()),
        "fraud_rate": round(df.is_fraud.mean(), 4),
        "fraud_type_counts": df[df.is_fraud == 1]["fraud_type"].value_counts().to_dict(),
        "seed": args.seed,
    }
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
