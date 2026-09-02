"""
RiskGraph AI - Rule Engine
----------------------------
Deterministic, configurable, auditable risk rules loaded from
`app/policies/rules.yaml`. Rules are never hard-coded inside Python
functions - business/risk teams edit the YAML, the engine just evaluates it.
Every result carries the `policy_version` so decisions are reproducible.
"""
from __future__ import annotations

import operator
from dataclasses import dataclass
from pathlib import Path

import yaml

OPS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "policies" / "rules.yaml"


@dataclass
class RuleHit:
    rule_id: str
    description: str
    weight: float


@dataclass
class RuleEngineResult:
    policy_version: str
    triggered: list[RuleHit]
    rule_score: float  # normalized 0-100
    max_possible: float


class RuleEngine:
    def __init__(self, policy_path: Path | str = DEFAULT_POLICY_PATH):
        self.policy_path = Path(policy_path)
        self.reload()

    def reload(self) -> None:
        with open(self.policy_path) as f:
            self.policy = yaml.safe_load(f)
        self.policy_version = self.policy["policy_version"]
        self.rules = self.policy["rules"]
        self.thresholds = self.policy["thresholds"]
        self.weights = self.policy["weights"]

    @staticmethod
    def _check(condition: dict, txn: dict) -> bool:
        field_val = txn.get(condition["field"])
        if field_val is None:
            return False
        op = OPS[condition["operator"]]
        return bool(op(field_val, condition["threshold"]))

    def evaluate(self, txn: dict) -> RuleEngineResult:
        hits: list[RuleHit] = []
        for rule in self.rules:
            if not self._check(rule, txn):
                continue
            if "also_requires" in rule and not self._check(rule["also_requires"], txn):
                continue
            hits.append(RuleHit(rule_id=rule["id"], description=rule["description"], weight=rule["weight"]))

        max_possible = sum(r["weight"] for r in self.rules)
        raw = sum(h.weight for h in hits)
        rule_score = round(100 * raw / max_possible, 2) if max_possible else 0.0

        return RuleEngineResult(
            policy_version=self.policy_version,
            triggered=hits,
            rule_score=rule_score,
            max_possible=max_possible,
        )

    def risk_level(self, aggregate_score: float) -> str:
        t = self.thresholds
        if aggregate_score <= t["low_max"]:
            return "LOW"
        if aggregate_score <= t["medium_max"]:
            return "MEDIUM"
        if aggregate_score <= t["high_max"]:
            return "HIGH"
        return "CRITICAL"
