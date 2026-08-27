"""
RiskGraph AI - Application State.

Holds the process-wide singletons (trained model artifact, graph engine,
rule engine, RAG index) that are expensive to build and safe to share
read-only across requests. Loaded once at FastAPI startup (see main.py).

Includes the model-unavailable fallback path: if the trained artifact is
missing (e.g. `ml/train.py` hasn't been run yet), the app still starts and
serves a clearly `degraded_mode=True` deterministic score instead of
crashing - see POL-006.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from app.agent.rag import PolicyRAG
from app.config import get_settings
from app.services.anomaly import AnomalyDetector
from app.services.graph_engine import NetworkXGraphEngine
from app.services.rules_engine import RuleEngine

logger = logging.getLogger("riskgraph.state")


class AppState:
    def __init__(self):
        self.settings = get_settings()
        self.model_artifact: dict | None = None
        self.anomaly_detector: AnomalyDetector | None = None
        self.graph_engine = NetworkXGraphEngine()
        self.rule_engine = RuleEngine(self.settings.rules_policy_path)
        self.rag = PolicyRAG(self.settings.policy_docs_dir)
        self.model_degraded = True
        self.model_degraded_reason = "not loaded yet"

    def load_model(self) -> None:
        import joblib

        path = Path(self.settings.model_artifact_path)
        if not path.exists():
            self.model_degraded = True
            self.model_degraded_reason = (
                f"model artifact not found at {path}. Run `python ml/train.py` first."
            )
            logger.warning(self.model_degraded_reason)
            return
        try:
            self.model_artifact = joblib.load(path)
            self.anomaly_detector = AnomalyDetector(
                self.model_artifact["isolation_forest"], self.model_artifact["feature_names"]
            )
            self.model_degraded = False
            self.model_degraded_reason = None
            logger.info("Loaded model artifact version=%s", self.model_artifact.get("model_version"))
        except Exception as exc:  # noqa: BLE001
            self.model_degraded = True
            self.model_degraded_reason = f"failed to load model artifact: {exc}"
            logger.error(self.model_degraded_reason)

    def build_graph(self, transactions: pd.DataFrame) -> None:
        try:
            self.graph_engine.build(transactions)
        except Exception as exc:  # noqa: BLE001 - graph unavailability must not crash startup
            logger.error("graph build failed, continuing with empty graph: %s", exc)


app_state = AppState()
