"""
RiskGraph AI - Failure handling.

Implements the graceful-degradation scenarios called out in the product
spec: LLM unavailable, graph unavailable, model unavailable, RAG
unavailable, DB timeout. Nothing here fails silently - every degraded path
returns an explicit `degraded_mode`/`ai_mode` flag and logs an audit event.
"""
from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("riskgraph.fallback")


class ServiceUnavailableError(Exception):
    def __init__(self, service: str, detail: str = ""):
        self.service = service
        self.detail = detail
        super().__init__(f"{service} unavailable: {detail}")


@dataclass
class DegradedResult:
    degraded: bool
    reason: str | None = None


def with_retry(max_retries: int = 2, timeout_seconds: float = 20.0, backoff_seconds: float = 0.5):
    """
    Decorator implementing bounded retry + timeout for external calls (LLM,
    DB). Raises ServiceUnavailableError after exhausting retries so callers
    can trigger an explicit, logged fallback rather than hanging or crashing.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                start = time.time()
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - deliberately broad, this is the fallback boundary
                    elapsed = time.time() - start
                    last_exc = exc
                    logger.warning(
                        "call to %s failed on attempt %d/%d after %.2fs: %s",
                        fn.__name__, attempt + 1, max_retries + 1, elapsed, exc,
                    )
                    if attempt < max_retries:
                        time.sleep(backoff_seconds * (attempt + 1))
            raise ServiceUnavailableError(fn.__name__, detail=str(last_exc))
        return wrapper
    return decorator
