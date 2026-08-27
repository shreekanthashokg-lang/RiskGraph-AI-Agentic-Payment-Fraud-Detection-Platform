"""
RiskGraph AI - AI Investigation Agent.

Orchestrates a bounded tool-calling loop against Claude (Anthropic API) to
investigate HIGH/CRITICAL transactions: gather evidence via `AgentToolbox`,
retrieve grounding policy via RAG, and produce a structured recommendation.

Hard boundaries enforced here (see POL-007):
  - The agent NEVER approves/holds/blocks a transaction itself. It returns a
    `recommendation` string from a fixed action set for a human to act on.
  - The agent's `evidence` and `inference_summary` are kept structurally
    separate in the response so the UI can never blur "what the tools
    returned" with "what the agent concluded from it".
  - If the LLM call fails after retries, the agent falls back to a
    deterministic, rule/graph-based investigation summary and marks the
    case `DEGRADED_AI_MODE` - it never blocks transaction scoring.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.agent.tools import TOOL_SCHEMAS, AgentToolbox
from app.config import get_settings
from app.core.fallback import ServiceUnavailableError, with_retry

logger = logging.getLogger("riskgraph.agent")

AGENT_VERSION = "riskgraph-investigator-v1"

SYSTEM_PROMPT = """You are the RiskGraph AI Investigation Agent for a payment risk platform.

Your job is strictly to INVESTIGATE, RETRIEVE EVIDENCE, and RECOMMEND - never to decide.
Rules you must always follow:
1. Only use the provided tools to gather facts. Never invent transaction data, customer
   history, graph connections, or policy content.
2. Always call search_policy at least once before making a recommendation, and cite the
   real doc_id(s) it returns. If no policy result is relevant, say so explicitly instead
   of fabricating a citation.
3. Your final recommendation must be exactly one of: approve, hold, escalate, reject_review.
   You are not authorized to move money or finalize any decision - a human analyst does that.
4. When you write your final answer, clearly separate:
   - EVIDENCE: only facts returned by tools, each attributable to a tool call.
   - INFERENCE: your interpretation of what the evidence suggests. Never phrase inference as
     a confirmed fact.
   - RECOMMENDATION: the single bounded action plus a short rationale.
5. If evidence is insufficient, say so and recommend "escalate" rather than guessing.

When you are done gathering evidence, respond with ONLY a JSON object (no prose, no markdown
fences) matching this shape:
{
  "evidence": [{"source": "<tool_name>", "summary": "<short factual summary>"}],
  "inference_summary": "<your interpretation, clearly hedged where uncertain>",
  "recommendation": "approve|hold|escalate|reject_review",
  "recommendation_rationale": "<short justification tied to evidence and policy>",
  "policy_citations": [{"doc_id": "...", "title": "..."}]
}
"""


@dataclass
class InvestigationOutcome:
    ai_mode: str  # LIVE | DEGRADED_AI_MODE
    evidence: list[dict]
    inference_summary: str
    recommendation: str
    recommendation_rationale: str
    policy_citations: list[dict]
    requires_human_review: bool


def _deterministic_fallback(transaction_id: str, risk_result, rule_hits: list[dict], reason: str) -> InvestigationOutcome:
    """Rule/graph-only investigation used when the LLM is unavailable. See POL-006."""
    evidence = [
        {"source": "risk_aggregator", "summary": f"Aggregate risk score {risk_result.risk_score} ({risk_result.risk_level})"},
        {"source": "rule_engine", "summary": (
            f"{len(rule_hits)} rule(s) triggered: " + ", ".join(h['id'] for h in rule_hits)
        ) if rule_hits else "No deterministic rules triggered"},
    ]
    requires_review = risk_result.risk_level in ("HIGH", "CRITICAL")
    recommendation = "escalate" if requires_review else "approve"
    return InvestigationOutcome(
        ai_mode="DEGRADED_AI_MODE",
        evidence=evidence,
        inference_summary=(
            "AI Investigator unavailable - this is a deterministic fallback summary based only on "
            f"the rule engine and risk aggregator. Reason for degradation: {reason}"
        ),
        recommendation=recommendation,
        recommendation_rationale="Deterministic fallback: escalate any HIGH/CRITICAL score for human review per POL-006.",
        policy_citations=[{"doc_id": "POL-006", "title": "Failure Handling and Degraded Modes"}],
        requires_human_review=True,  # degraded mode always requires a human, out of caution
    )


class Investigator:
    def __init__(self, toolbox: AgentToolbox):
        self.toolbox = toolbox
        self.settings = get_settings()

    def investigate(self, transaction_id: str, risk_result, rule_hits: list[dict]) -> InvestigationOutcome:
        if not self.settings.anthropic_api_key:
            return _deterministic_fallback(
                transaction_id, risk_result, rule_hits,
                reason="ANTHROPIC_API_KEY not configured",
            )
        try:
            return self._run_agent_loop(transaction_id)
        except ServiceUnavailableError as exc:
            logger.error("LLM investigation failed, falling back: %s", exc)
            return _deterministic_fallback(transaction_id, risk_result, rule_hits, reason=str(exc))

    @with_retry(max_retries=2, timeout_seconds=20.0)
    def _run_agent_loop(self, transaction_id: str) -> InvestigationOutcome:
        import anthropic  # imported lazily so the rest of the app works without the SDK installed

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        messages = [{
            "role": "user",
            "content": (
                f"Investigate transaction {transaction_id}. Gather the evidence you need using "
                f"the available tools, then produce your final structured answer."
            ),
        }]

        max_turns = 8
        for _ in range(max_turns):
            response = client.messages.create(
                model=self.settings.llm_model,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    result = self.toolbox.dispatch(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
                messages.append({"role": "user", "content": tool_results})
                continue

            # Final answer turn
            text = "".join(b.text for b in response.content if b.type == "text")
            return self._parse_final_answer(text)

        raise ServiceUnavailableError("agent_loop", detail="exceeded max tool-calling turns without a final answer")

    @staticmethod
    def _parse_final_answer(text: str) -> InvestigationOutcome:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ServiceUnavailableError("agent_parse", detail=f"could not parse agent output: {exc}") from exc

        allowed = {"approve", "hold", "escalate", "reject_review"}
        recommendation = data.get("recommendation") if data.get("recommendation") in allowed else "escalate"

        return InvestigationOutcome(
            ai_mode="LIVE",
            evidence=data.get("evidence", []),
            inference_summary=data.get("inference_summary", ""),
            recommendation=recommendation,
            recommendation_rationale=data.get("recommendation_rationale", ""),
            policy_citations=data.get("policy_citations", []),
            requires_human_review=True,  # AI recommendation is always advisory, per POL-007
        )
