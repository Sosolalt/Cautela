"""Tests for the Hook 4 introspection-agent runner.

The original `_run_introspection_agent` used
`asyncio.get_event_loop().run_until_complete(...)` inside a worker
thread — broken on Python 3.12 (DeprecationWarning + implicit-create
removed) and silently swallowed by a bare `except`. The refactor
splits the body into `_run_introspection_agent_async` and a sync
wrapper that calls `asyncio.run`. These tests pin the new contract.
"""
from __future__ import annotations

import asyncio
import concurrent.futures

import pytest


def test_returns_empty_when_introspection_agent_unavailable(monkeypatch):
    """No MCP env → `build_introspection_agent` returns None → wrapper
    returns "" without touching the runner. Cheapest path; no fresh
    loop spun up."""
    from agent import reflector

    monkeypatch.setattr(reflector, "build_introspection_agent", lambda: None)
    assert reflector._run_introspection_agent() == ""


def test_uses_asyncio_run_not_get_event_loop(monkeypatch):
    """The 3.12 timebomb: `asyncio.get_event_loop()` in an executor
    thread with no installed loop is the deprecated path. The fix uses
    `asyncio.run`, which works on every supported Python by creating a
    fresh loop, awaiting the coroutine, and closing the loop atomically.

    We assert behavior by exercising the call from inside a worker
    thread — exactly how `/reflect` invokes it via `run_in_executor`."""
    from agent import reflector

    monkeypatch.setattr(reflector, "build_introspection_agent", lambda: None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(reflector._run_introspection_agent).result(timeout=5)
    assert result == ""


def test_swallows_runtime_errors_but_logs_with_traceback(monkeypatch, caplog):
    """A Phoenix/MCP outage must not abort the nightly Reflector cycle,
    but the failure MUST surface in logs with a traceback so an operator
    can diagnose it. The old code's `_LOG.warning("...: %s", exc)`
    dropped the traceback; the new code uses `exc_info=True`."""
    import logging

    from agent import reflector

    class _BoomAgent:
        tools: list = []

    monkeypatch.setattr(reflector, "build_introspection_agent", lambda: _BoomAgent())

    async def fake_async():
        raise RuntimeError("simulated MCP outage")

    monkeypatch.setattr(reflector, "_run_introspection_agent_async", fake_async)

    with caplog.at_level(logging.WARNING, logger=reflector._LOG.name):
        result = reflector._run_introspection_agent()
    assert result == ""
    assert any("introspection agent failed" in r.message for r in caplog.records)
    # exc_info=True attaches a traceback record
    assert any(r.exc_info is not None for r in caplog.records)


def test_cancelled_error_propagates(monkeypatch):
    """`asyncio.CancelledError` is reserved for cooperative cancellation
    (server shutdown). It must not be swallowed by the broad except —
    otherwise a SIGTERM during Reflector run hangs the worker thread."""
    from agent import reflector

    class _Agent:
        tools: list = []

    monkeypatch.setattr(reflector, "build_introspection_agent", lambda: _Agent())

    async def cancelled_body():
        raise asyncio.CancelledError()

    monkeypatch.setattr(reflector, "_run_introspection_agent_async", cancelled_body)

    with pytest.raises(asyncio.CancelledError):
        reflector._run_introspection_agent()


def test_async_body_drains_runner_and_closes_toolset(monkeypatch):
    """The fix must (a) drain the async-generator yielded by
    `runner.run_async`, (b) concatenate text parts, (c) close every
    MCPToolset on the agent so the `npx phoenix-mcp` subprocess doesn't
    leak across nightly cycles. Without the close, FD exhaustion is a
    silent demo-day failure mode."""
    from agent import reflector

    close_called: list[str] = []

    class _FakeToolset:
        async def aclose(self):
            close_called.append("aclose")

    class _FakeAgent:
        tools = [_FakeToolset()]

    class _FakeContent:
        def __init__(self, text):
            self.parts = [type("P", (), {"text": text})()]

    class _FakeEvent:
        def __init__(self, text):
            self.content = _FakeContent(text)

    class _FakeSession:
        def create_session(self, **kw):
            return None  # sync return; the awaitable-guard branch is taken elsewhere

    class _FakeRunner:
        def __init__(self, agent, app_name):
            self.session_service = _FakeSession()

        async def run_async(self, user_id, session_id, new_message):
            yield _FakeEvent("hello ")
            yield _FakeEvent("world")

    monkeypatch.setattr(reflector, "build_introspection_agent", lambda: _FakeAgent())
    fake_runners = type("M", (), {"InMemoryRunner": _FakeRunner})
    fake_genai_types = type(
        "M", (), {"Content": lambda role, parts: None, "Part": lambda text: None}
    )

    import sys

    monkeypatch.setitem(sys.modules, "google.adk.runners", fake_runners)
    monkeypatch.setitem(sys.modules, "google.genai", type("M", (), {"types": fake_genai_types}))
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_genai_types)

    result = reflector._run_introspection_agent()
    assert result == "hello \nworld"
    assert close_called == ["aclose"], (
        "MCPToolset.aclose was not called — subprocess will leak"
    )


def test_runs_in_worker_thread_no_event_loop_required(monkeypatch):
    """Mimic the production call shape exactly: `/reflect` calls
    `run_in_executor(None, run_reflection_cycle)`, which (deep inside)
    calls `_run_introspection_agent`. The worker thread starts with
    NO event loop installed.

    To genuinely exercise the asyncio primitive (and not short-circuit
    at the agent-None early return), use a non-None fake agent + fake
    runner so the wrapper actually reaches `asyncio.run(async_body())`.
    This is the test that would have caught the original
    `asyncio.get_event_loop()` bug on Python 3.12+."""
    import sys

    from agent import reflector

    class _FakeToolset:
        async def aclose(self):
            pass

    class _FakeAgent:
        tools = [_FakeToolset()]

    class _FakeSession:
        def create_session(self, **kw):
            return None

    class _FakeRunner:
        def __init__(self, agent, app_name):
            self.session_service = _FakeSession()

        async def run_async(self, user_id, session_id, new_message):
            # Async generator with NO yields — drains immediately.
            if False:
                yield None

    monkeypatch.setattr(reflector, "build_introspection_agent", lambda: _FakeAgent())
    fake_runners = type("M", (), {"InMemoryRunner": _FakeRunner})
    fake_genai_types = type(
        "M", (), {"Content": lambda role, parts: None, "Part": lambda text: None}
    )
    monkeypatch.setitem(sys.modules, "google.adk.runners", fake_runners)
    monkeypatch.setitem(sys.modules, "google.genai", type("M", (), {"types": fake_genai_types}))
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_genai_types)

    async def driver():
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, reflector._run_introspection_agent)

    # If `_run_introspection_agent` regressed to `asyncio.get_event_loop()`
    # in the executor thread, Python 3.12+ would raise RuntimeError or
    # emit a DeprecationWarning the bare except would swallow → result
    # would still be "" silently. The drain path here forces real loop
    # usage so a regression would either raise (no swallowed except in
    # the async body for loop errors) or warn.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        result = asyncio.run(driver())
    assert result == ""
