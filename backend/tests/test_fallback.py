from __future__ import annotations

import pytest

from app.core.fallback import ServiceUnavailableError, with_retry


def test_succeeds_without_retry():
    calls = {"n": 0}

    @with_retry(max_retries=2, backoff_seconds=0)
    def flaky():
        calls["n"] += 1
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 1


def test_retries_then_succeeds():
    calls = {"n": 0}

    @with_retry(max_retries=2, backoff_seconds=0)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 2


def test_exhausts_retries_and_raises_service_unavailable():
    @with_retry(max_retries=2, backoff_seconds=0)
    def always_fails():
        raise RuntimeError("permanent failure")

    with pytest.raises(ServiceUnavailableError):
        always_fails()
