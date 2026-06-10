"""Retry/backoff behavior of the shared eval runner (`scripts/_live_agent.py`).

A batch eval against a Vertex preview model routinely hits 429
RESOURCE_EXHAUSTED; `run_agent` must absorb transient rate limits with
exponential backoff instead of aborting the whole run. These tests drive that
purely offline by monkeypatching `asyncio.run` and `time.sleep` (no Vertex, no
real waiting).
"""
from __future__ import annotations

import pytest

import scripts._live_agent as LA


def _close(coro) -> None:
    # _run_agent_async(...) builds a coroutine that we never await in the fake;
    # close it so Python doesn't warn "coroutine was never awaited".
    try:
        coro.close()
    except Exception:  # pragma: no cover - defensive
        pass


def test_run_agent_retries_then_succeeds_on_429(monkeypatch):
    monkeypatch.setattr(LA.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def fake_run(coro):
        _close(coro)
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "ok"

    monkeypatch.setattr(LA.asyncio, "run", fake_run)
    assert LA.run_agent(object(), "hello") == "ok"
    assert calls["n"] == 3  # two failures absorbed, third succeeded


def test_run_agent_reraises_non_rate_limit(monkeypatch):
    monkeypatch.setattr(LA.time, "sleep", lambda *_: None)

    def fake_run(coro):
        _close(coro)
        raise ValueError("some other error")

    monkeypatch.setattr(LA.asyncio, "run", fake_run)
    with pytest.raises(ValueError):
        LA.run_agent(object(), "hello")


def test_run_agent_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(LA.time, "sleep", lambda *_: None)
    monkeypatch.setattr(LA, "_MAX_RETRIES", 2)
    attempts = {"n": 0}

    def fake_run(coro):
        _close(coro)
        attempts["n"] += 1
        raise RuntimeError("429")

    monkeypatch.setattr(LA.asyncio, "run", fake_run)
    with pytest.raises(RuntimeError, match="429"):
        LA.run_agent(object(), "hello")
    assert attempts["n"] == 3  # initial try + 2 retries


def test_is_rate_limited_matching():
    assert LA._is_rate_limited(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert LA._is_rate_limited(Exception("Resource exhausted"))
    assert not LA._is_rate_limited(ValueError("bad json"))
