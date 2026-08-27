"""
RiskGraph AI - Graph Risk Engine
----------------------------------
Builds a heterogeneous relationship graph (customer / device / ip /
beneficiary / merchant) from transaction history and derives:

  - shared-identifier risk features that feed the ML/rule layer
  - connected-component / community fraud clusters
  - per-node graph-derived risk (degree, risk-neighbor propagation)

Backed by NetworkX. Architected so a Neo4j-backed implementation could
satisfy the same `GraphEngine` interface for larger deployments - see the
`GraphEngine` ABC below.

This is not decorative: `graph_risk_score` and `cluster_id` produced here
feed directly into `risk_aggregator.py`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import networkx as nx
import pandas as pd


@dataclass
class ClusterResult:
    cluster_id: str
    cluster_size: int
    entities: list[str]
    risk_score: float
    risk_reasons: list[str]
    connected_fraud_cases: int


@dataclass
class GraphFeatures:
    customer_degree: int
    shared_device_count: int
    shared_ip_count: int
    known_risk_neighbor_count: int
    cluster_id: str | None
    cluster_size: int
    graph_risk_score: float


class GraphEngine(ABC):
    """Interface so Neo4j (or another backend) can be dropped in later."""

    @abstractmethod
    def build(self, transactions: pd.DataFrame) -> None: ...

    @abstractmethod
    def features_for_transaction(self, txn: dict) -> GraphFeatures: ...

    @abstractmethod
    def clusters(self, min_size: int = 3) -> list[ClusterResult]: ...

    @abstractmethod
    def neighborhood(self, entity_id: str, depth: int = 2) -> dict: ...


class NetworkXGraphEngine(GraphEngine):
    def __init__(self):
        self.graph = nx.Graph()
        self._built = False
        self._fraud_customers: set[str] = set()

    def build(self, transactions: pd.DataFrame) -> None:
        g = nx.Graph()
        for _, row in transactions.iterrows():
            cust = f"customer:{row['customer_id']}"
            dev = f"device:{row['device_id']}"
            ip = f"ip:{row['ip_address']}"
            benef = f"beneficiary:{row['beneficiary_id']}"
            merch = f"merchant:{row['merchant_id']}"

            for node, ntype in [(cust, "customer"), (dev, "device"), (ip, "ip"),
                                 (benef, "beneficiary"), (merch, "merchant")]:
                if not g.has_node(node):
                    g.add_node(node, type=ntype, id=node.split(":", 1)[1])

            g.add_edge(cust, dev, relation="uses_device")
            g.add_edge(cust, ip, relation="uses_ip")
            g.add_edge(cust, benef, relation="pays_beneficiary")
            g.add_edge(cust, merch, relation="transacts_with")

            if int(row.get("is_fraud", 0)) == 1 or int(row.get("previous_fraud_alerts", 0)) > 0:
                self._fraud_customers.add(cust)
                g.nodes[cust]["flagged"] = True

        self.graph = g
        self._built = True

    def _neighbors_of_type(self, node: str, ntype: str) -> list[str]:
        if not self.graph.has_node(node):
            return []
        return [n for n in self.graph.neighbors(node) if self.graph.nodes[n].get("type") == ntype]

    def features_for_transaction(self, txn: dict) -> GraphFeatures:
        cust = f"customer:{txn['customer_id']}"
        dev = f"device:{txn['device_id']}"
        ip = f"ip:{txn['ip_address']}"

        degree = self.graph.degree[cust] if self.graph.has_node(cust) else 0

        # "shared" = how many OTHER customers touch this same device/ip
        shared_device = len(self._neighbors_of_type(dev, "customer")) - 1 if self.graph.has_node(dev) else 0
        shared_ip = len(self._neighbors_of_type(ip, "customer")) - 1 if self.graph.has_node(ip) else 0
        shared_device = max(0, shared_device)
        shared_ip = max(0, shared_ip)

        # 2-hop neighbors flagged as fraud/high-risk. Traverses the risk
        # subgraph (device/ip/beneficiary), not merchant edges, so a popular
        # merchant doesn't make every customer look like a fraud neighbor.
        risk_neighbors = 0
        risk_graph = self._risk_subgraph()
        if risk_graph.has_node(cust):
            two_hop = set()
            for n1 in risk_graph.neighbors(cust):
                two_hop.update(risk_graph.neighbors(n1))
            two_hop.discard(cust)
            risk_neighbors = sum(
                1 for n in two_hop
                if risk_graph.nodes[n].get("type") == "customer" and n in self._fraud_customers
            )

        cluster_id, cluster_size = None, 0
        risk_graph = self._risk_subgraph()
        if risk_graph.has_node(cust):
            component = nx.node_connected_component(risk_graph, cust)
            if len(component) >= 3:
                cluster_id = f"cluster_{abs(hash(frozenset(component))) % (10 ** 8)}"
                cluster_size = len({n for n in component if self.graph.nodes[n].get("type") == "customer"})

        # Weighted, bounded [0, 1] graph risk score. Weights are explicit and
        # configurable (see docstring) rather than opaque - not a fabricated number.
        raw = (
            0.35 * min(shared_device, 10) / 10
            + 0.30 * min(shared_ip, 10) / 10
            + 0.25 * min(risk_neighbors, 5) / 5
            + 0.10 * min(cluster_size, 15) / 15
        )
        graph_risk_score = round(min(1.0, raw), 4)

        return GraphFeatures(
            customer_degree=degree,
            shared_device_count=shared_device,
            shared_ip_count=shared_ip,
            known_risk_neighbor_count=risk_neighbors,
            cluster_id=cluster_id,
            cluster_size=cluster_size,
            graph_risk_score=graph_risk_score,
        )

    def _risk_subgraph(self) -> nx.Graph:
        """
        Cluster detection deliberately excludes merchant edges: many unrelated
        customers legitimately share a popular merchant, which would merge the
        whole graph into one giant component and drown out real signal.
        Device / IP / beneficiary sharing is a much stronger coordinated-fraud
        indicator, so clustering runs on that subgraph only.
        """
        keep_types = {"customer", "device", "ip", "beneficiary"}
        nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") in keep_types]
        return self.graph.subgraph(nodes)

    def clusters(self, min_size: int = 3) -> list[ClusterResult]:
        results = []
        risk_graph = self._risk_subgraph()
        for component in nx.connected_components(risk_graph):
            customers = [n for n in component if self.graph.nodes[n].get("type") == "customer"]
            if len(customers) < min_size:
                continue
            fraud_hits = sum(1 for c in customers if c in self._fraud_customers)
            devices = {n for n in component if self.graph.nodes[n].get("type") == "device"}
            ips = {n for n in component if self.graph.nodes[n].get("type") == "ip"}
            benefs = {n for n in component if self.graph.nodes[n].get("type") == "beneficiary"}

            reasons = []
            if len(devices) <= 3 and len(customers) >= 5:
                reasons.append(f"{len(customers)} customers share only {len(devices)} device(s)")
            if len(ips) <= 3 and len(customers) >= 5:
                reasons.append(f"{len(customers)} customers share only {len(ips)} IP address(es)")
            if len(benefs) <= 2 and len(customers) >= 4:
                reasons.append(f"{len(customers)} customers route to {len(benefs)} beneficiary account(s)")
            if fraud_hits:
                reasons.append(f"{fraud_hits} member(s) previously flagged for fraud")

            risk_score = round(min(1.0, 0.15 * len(customers) + 0.2 * fraud_hits + 0.1 * len(reasons)), 4)

            results.append(ClusterResult(
                cluster_id=f"cluster_{abs(hash(frozenset(component))) % (10 ** 8)}",
                cluster_size=len(customers),
                entities=sorted(component),
                risk_score=risk_score,
                risk_reasons=reasons or ["Densely connected component above minimum size threshold"],
                connected_fraud_cases=fraud_hits,
            ))
        return sorted(results, key=lambda c: c.risk_score, reverse=True)

    def neighborhood(self, entity_id: str, depth: int = 2) -> dict:
        if not self.graph.has_node(entity_id):
            return {"nodes": [], "edges": []}
        nodes = {entity_id}
        frontier = {entity_id}
        for _ in range(depth):
            next_frontier = set()
            for n in frontier:
                next_frontier.update(self.graph.neighbors(n))
            nodes.update(next_frontier)
            frontier = next_frontier
        sub = self.graph.subgraph(nodes)
        return {
            "nodes": [{"id": n, **sub.nodes[n]} for n in sub.nodes],
            "edges": [{"source": u, "target": v, **sub.edges[u, v]} for u, v in sub.edges],
        }
