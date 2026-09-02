"""
RiskGraph AI - Agent Tools.

Every tool the AI Investigation Agent can call is defined here as a typed,
schema-validated function with explicit error handling. The agent can only
gather and synthesize evidence through these tools - it has no other way to
touch the system, and none of them move money or unilaterally change a
transaction's status (see POL-007).

Each tool returns a plain dict shaped for direct inclusion in a Claude
tool_result block, and never raises past the boundary - failures are
returned as `{"error": ...}` so the agent can reason about missing evidence
instead of the whole investigation crashing.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


TOOL_SCHEMAS = [
    {
        "name": "get_transaction",
        "description": "Fetch the full record for a transaction by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"transaction_id": {"type": "string"}},
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_customer_history",
        "description": "Fetch recent transaction history and summary stats for a customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_device_history",
        "description": "Fetch all customers and transactions ever seen on a given device_id.",
        "input_schema": {
            "type": "object",
            "properties": {"device_id": {"type": "string"}},
            "required": ["device_id"],
        },
    },
    {
        "name": "get_ip_history",
        "description": "Fetch all customers and transactions ever seen from a given IP address.",
        "input_schema": {
            "type": "object",
            "properties": {"ip_address": {"type": "string"}},
            "required": ["ip_address"],
        },
    },
    {
        "name": "get_graph_connections",
        "description": "Fetch the relationship-graph neighborhood (devices/IPs/beneficiaries/merchants) around a customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "depth": {"type": "integer", "default": 2},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_related_transactions",
        "description": "Fetch other transactions sharing this transaction's device, IP, or beneficiary.",
        "input_schema": {
            "type": "object",
            "properties": {"transaction_id": {"type": "string"}, "limit": {"type": "integer", "default": 20}},
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_previous_risk_cases",
        "description": "Fetch prior investigation cases for a customer, if any.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_risk_score",
        "description": "Fetch the current aggregate risk score and its contributing factors for a transaction.",
        "input_schema": {
            "type": "object",
            "properties": {"transaction_id": {"type": "string"}},
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_model_explanation",
        "description": "Fetch the ML model's feature-level contribution breakdown for a transaction's fraud probability.",
        "input_schema": {
            "type": "object",
            "properties": {"transaction_id": {"type": "string"}},
            "required": ["transaction_id"],
        },
    },
    {
        "name": "search_policy",
        "description": "Search the risk-policy knowledge base for guidance relevant to a query. Always call this before recommending an action.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 3}},
            "required": ["query"],
        },
    },
]


class AgentToolbox:
    """
    Binds tool schemas to real implementations against the current request's
    DB session and in-memory engines (graph/risk cache). Constructed fresh
    per-investigation so nothing leaks across requests.
    """

    def __init__(self, db: Session, graph_engine, rule_engine, rag, risk_cache: dict[str, Any]):
        self.db = db
        self.graph_engine = graph_engine
        self.rule_engine = rule_engine
        self.rag = rag
        self.risk_cache = risk_cache  # transaction_id -> AggregateRiskResult (this request's scoring run)

    def dispatch(self, name: str, tool_input: dict) -> dict:
        handler: Callable[[dict], dict] | None = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return {"error": f"Unknown tool '{name}'"}
        try:
            return handler(tool_input)
        except Exception as exc:  # noqa: BLE001 - tool boundary must not crash the agent loop
            return {"error": f"{name} failed: {exc}"}

    # --- tool implementations -------------------------------------------------

    def _tool_get_transaction(self, args: dict) -> dict:
        from app.models.db_models import Transaction
        txn = self.db.query(Transaction).filter_by(transaction_id=args["transaction_id"]).first()
        if not txn:
            return {"error": "transaction not found"}
        return {
            "transaction_id": txn.transaction_id, "customer_id": txn.customer_id,
            "merchant_id": txn.merchant_id, "amount": txn.amount, "currency": txn.currency,
            "device_id": txn.device_id, "ip_address": txn.ip_address,
            "beneficiary_id": txn.beneficiary_id, "location": txn.location,
            "timestamp": str(txn.timestamp), "status": txn.status,
        }

    def _tool_get_customer_history(self, args: dict) -> dict:
        from app.models.db_models import Transaction
        q = (
            self.db.query(Transaction)
            .filter_by(customer_id=args["customer_id"])
            .order_by(Transaction.timestamp.desc())
            .limit(args.get("limit", 20))
        )
        rows = q.all()
        return {
            "customer_id": args["customer_id"],
            "transaction_count": len(rows),
            "transactions": [
                {"transaction_id": r.transaction_id, "amount": r.amount, "timestamp": str(r.timestamp),
                 "status": r.status} for r in rows
            ],
        }

    def _tool_get_device_history(self, args: dict) -> dict:
        from app.models.db_models import Transaction
        rows = self.db.query(Transaction).filter_by(device_id=args["device_id"]).all()
        customers = sorted({r.customer_id for r in rows})
        return {"device_id": args["device_id"], "distinct_customers": len(customers),
                "customers": customers[:25], "transaction_count": len(rows)}

    def _tool_get_ip_history(self, args: dict) -> dict:
        from app.models.db_models import Transaction
        rows = self.db.query(Transaction).filter_by(ip_address=args["ip_address"]).all()
        customers = sorted({r.customer_id for r in rows})
        return {"ip_address": args["ip_address"], "distinct_customers": len(customers),
                "customers": customers[:25], "transaction_count": len(rows)}

    def _tool_get_graph_connections(self, args: dict) -> dict:
        node_id = f"customer:{args['customer_id']}"
        return self.graph_engine.neighborhood(node_id, depth=args.get("depth", 2))

    def _tool_get_related_transactions(self, args: dict) -> dict:
        from app.models.db_models import Transaction
        txn = self.db.query(Transaction).filter_by(transaction_id=args["transaction_id"]).first()
        if not txn:
            return {"error": "transaction not found"}
        related = (
            self.db.query(Transaction)
            .filter(
                Transaction.transaction_id != txn.transaction_id,
                (Transaction.device_id == txn.device_id)
                | (Transaction.ip_address == txn.ip_address)
                | (Transaction.beneficiary_id == txn.beneficiary_id),
            )
            .limit(args.get("limit", 20))
            .all()
        )
        return {
            "transaction_id": args["transaction_id"],
            "related_count": len(related),
            "related_transactions": [
                {"transaction_id": r.transaction_id, "customer_id": r.customer_id, "amount": r.amount,
                 "shared_via": (
                     "device" if r.device_id == txn.device_id else
                     "ip" if r.ip_address == txn.ip_address else "beneficiary"
                 )} for r in related
            ],
        }

    def _tool_get_previous_risk_cases(self, args: dict) -> dict:
        from app.models.db_models import InvestigationCase, Transaction
        txns = self.db.query(Transaction.transaction_id).filter_by(customer_id=args["customer_id"]).subquery()
        cases = self.db.query(InvestigationCase).filter(InvestigationCase.transaction_id.in_(txns)).all()
        return {
            "customer_id": args["customer_id"],
            "case_count": len(cases),
            "cases": [
                {"case_id": c.case_id, "status": c.status, "recommendation": c.recommendation,
                 "created_at": str(c.created_at)} for c in cases
            ],
        }

    def _tool_get_risk_score(self, args: dict) -> dict:
        cached = self.risk_cache.get(args["transaction_id"])
        if cached:
            return {
                "risk_score": cached.risk_score, "risk_level": cached.risk_level,
                "ml_probability": cached.ml_probability, "graph_risk": cached.graph_risk,
                "anomaly_score": cached.anomaly_score, "rule_score": cached.rule_score,
                "contributors": [asdict(c) for c in cached.contributors],
            }
        from app.models.db_models import RiskScore
        row = (
            self.db.query(RiskScore)
            .filter_by(transaction_id=args["transaction_id"])
            .order_by(RiskScore.created_at.desc())
            .first()
        )
        if not row:
            return {"error": "no risk score on file for this transaction"}
        return {
            "risk_score": row.risk_score, "risk_level": row.risk_level,
            "ml_probability": row.ml_probability, "graph_risk": row.graph_risk,
            "anomaly_score": row.anomaly_score, "rule_score": row.rule_score,
            "contributors": row.contributors,
        }

    def _tool_get_model_explanation(self, args: dict) -> dict:
        result = self._tool_get_risk_score(args)
        if "error" in result:
            return result
        return {"transaction_id": args["transaction_id"], "top_contributors": result.get("contributors", [])[:5]}

    def _tool_search_policy(self, args: dict) -> dict:
        chunks = self.rag.retrieve(args["query"], top_k=args.get("top_k", 3))
        if not chunks:
            return {"results": [], "note": "No matching policy found - do not fabricate a citation."}
        return {
            "results": [
                {"doc_id": c.doc_id, "title": c.title, "version": c.version, "excerpt": c.text[:500]}
                for c in chunks
            ]
        }
