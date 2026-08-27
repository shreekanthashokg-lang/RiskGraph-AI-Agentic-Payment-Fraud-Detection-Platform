from __future__ import annotations

from pathlib import Path

from app.agent.rag import PolicyRAG

DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "policies"


def test_rag_loads_all_policy_docs():
    rag = PolicyRAG(DOCS_DIR)
    assert rag.available
    doc_ids = {c.doc_id for c in rag.chunks}
    assert "POL-004" in doc_ids
    assert "POL-006" in doc_ids


def test_retrieve_returns_relevant_cluster_policy():
    rag = PolicyRAG(DOCS_DIR)
    results = rag.retrieve("coordinated fraud cluster shared device", top_k=3)
    assert any(c.doc_id == "POL-004" for c in results)


def test_retrieve_returns_relevant_failure_policy():
    rag = PolicyRAG(DOCS_DIR)
    results = rag.retrieve("LLM unavailable degraded mode fallback", top_k=3)
    assert any(c.doc_id == "POL-006" for c in results)


def test_citations_deduplicated_by_doc_id():
    rag = PolicyRAG(DOCS_DIR)
    results = rag.retrieve("risk threshold escalation review", top_k=6)
    citations = rag.as_citations(results)
    ids = [c["doc_id"] for c in citations]
    assert len(ids) == len(set(ids))


def test_empty_docs_dir_degrades_gracefully(tmp_path):
    rag = PolicyRAG(tmp_path)
    assert rag.available is False
    assert rag.retrieve("anything") == []
