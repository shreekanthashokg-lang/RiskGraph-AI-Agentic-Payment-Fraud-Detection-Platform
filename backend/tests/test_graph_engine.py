from __future__ import annotations

from app.services.graph_engine import NetworkXGraphEngine


def test_normal_customer_has_low_graph_risk(sample_transactions):
    engine = NetworkXGraphEngine()
    engine.build(sample_transactions)
    normal_rows = sample_transactions[sample_transactions.fraud_type == "none"]
    if normal_rows.empty:
        return
    txn = normal_rows.iloc[0].to_dict()
    features = engine.features_for_transaction(txn)
    assert features.graph_risk_score < 0.3


def test_coordinated_cluster_member_has_high_graph_risk(sample_transactions):
    engine = NetworkXGraphEngine()
    engine.build(sample_transactions)
    ring_rows = sample_transactions[sample_transactions.fraud_type == "coordinated_cluster"]
    if ring_rows.empty:
        return
    txn = ring_rows.iloc[0].to_dict()
    features = engine.features_for_transaction(txn)
    assert features.graph_risk_score > 0.5
    assert features.cluster_size >= 3


def test_clusters_below_min_size_excluded(sample_transactions):
    engine = NetworkXGraphEngine()
    engine.build(sample_transactions)
    clusters = engine.clusters(min_size=3)
    assert all(c.cluster_size >= 3 for c in clusters)


def test_merchant_sharing_alone_does_not_create_cluster():
    """Regression test: many unrelated customers sharing one popular merchant
    must NOT be treated as a fraud cluster - only device/IP/beneficiary sharing
    counts (see graph_engine._risk_subgraph docstring)."""
    import pandas as pd
    rows = []
    for i in range(20):
        rows.append({
            "customer_id": f"cust_{i}", "device_id": f"dev_{i}", "ip_address": f"1.1.1.{i}",
            "beneficiary_id": f"benef_{i}", "merchant_id": "merch_popular",
            "is_fraud": 0, "previous_fraud_alerts": 0,
        })
    df = pd.DataFrame(rows)
    engine = NetworkXGraphEngine()
    engine.build(df)
    clusters = engine.clusters(min_size=3)
    assert clusters == []
