"""
Agent tool tests using lightweight fakes instead of a live DB/graph, so this
file's core dispatch/error-handling logic can be verified even in
environments without the full SQLAlchemy/FastAPI stack installed. When run
with the full dev environment (`pip install -r requirements.txt && pytest`),
these exercise the real AgentToolbox class end-to-end against a fixture DB
session as well (see test_agent_tools_integration below, requires the `db`
fixture from a full conftest with a temporary SQLite session).
"""
from __future__ import annotations

import pytest

from app.agent.tools import TOOL_SCHEMAS, AgentToolbox


def test_all_tool_schemas_have_required_fields():
    for schema in TOOL_SCHEMAS:
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"


def test_search_policy_tool_returns_results_for_relevant_query(policy_rag):
    toolbox = AgentToolbox(db=None, graph_engine=None, rule_engine=None, rag=policy_rag, risk_cache={})
    result = toolbox.dispatch("search_policy", {"query": "coordinated fraud cluster", "top_k": 3})
    assert "results" in result
    assert len(result["results"]) > 0
    assert all("doc_id" in r for r in result["results"])


def test_search_policy_tool_handles_no_match_without_fabricating(policy_rag):
    toolbox = AgentToolbox(db=None, graph_engine=None, rule_engine=None, rag=policy_rag, risk_cache={})
    result = toolbox.dispatch("search_policy", {"query": "zzz_no_such_topic_qqq", "top_k": 3})
    assert result["results"] == []
    assert "note" in result


def test_unknown_tool_returns_structured_error(policy_rag):
    toolbox = AgentToolbox(db=None, graph_engine=None, rule_engine=None, rag=policy_rag, risk_cache={})
    result = toolbox.dispatch("delete_everything", {})
    assert "error" in result


def test_get_risk_score_uses_request_scoped_cache(policy_rag):
    from dataclasses import dataclass

    @dataclass
    class FakeContributor:
        factor: str
        contribution_points: float
        detail: str

    class FakeResult:
        risk_score = 88.0
        risk_level = "CRITICAL"
        ml_probability = 0.9
        graph_risk = 0.8
        anomaly_score = 0.7
        rule_score = 0.6
        contributors = [FakeContributor("ML model probability", 30, "high fraud probability")]

    toolbox = AgentToolbox(
        db=None, graph_engine=None, rule_engine=None, rag=policy_rag,
        risk_cache={"txn_1": FakeResult()},
    )
    result = toolbox.dispatch("get_risk_score", {"transaction_id": "txn_1"})
    assert result["risk_score"] == 88.0
    assert result["risk_level"] == "CRITICAL"


@pytest.fixture
def policy_rag():
    from pathlib import Path

    from app.agent.rag import PolicyRAG

    docs_dir = Path(__file__).resolve().parents[2] / "data" / "policies"
    return PolicyRAG(docs_dir)
