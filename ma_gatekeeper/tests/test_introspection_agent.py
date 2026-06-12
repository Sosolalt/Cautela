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
from pathlib import Path

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


# ===========================================================================
# MCP toolset process-shutdown registry — catches subprocess leaks that
# bypass the per-call try/finally (SIGTERM, FastAPI lifespan teardown,
# uncaught exception in the executor thread).
# ===========================================================================


def _reset_mcp_registry():
    from agent import reflector
    with reflector._mcp_toolset_registry_lock:
        reflector._mcp_toolset_registry.clear()


def _registry_has(tool) -> bool:
    """True if `tool` is in the registry under any loop binding.
    Registry entries are `(toolset, loop)` tuples per the R4-2 fix —
    cross-loop hazard detection requires tracking the loop reference
    alongside each toolset.
    """
    from agent import reflector
    with reflector._mcp_toolset_registry_lock:
        return any(entry[0] is tool for entry in reflector._mcp_toolset_registry)


def test_make_phoenix_mcp_toolset_registers_in_registry(monkeypatch):
    """Successful toolset construction MUST add the instance to the
    process-wide registry so the shutdown drain can find it later.
    Regression: removing the `_register_toolset(toolset)` line leaves
    the registry empty and the assertion fails.
    """
    import sys
    import types

    from agent import reflector

    _reset_mcp_registry()
    # `make_phoenix_mcp_toolset` now defaults to the node-free
    # `_DirectPhoenixToolset`; opt into the npx MCPToolset path this test
    # stubs so it still exercises the StdioServerParameters registration.
    monkeypatch.setenv("REFLECTOR_USE_NPX_MCP", "1")
    monkeypatch.setenv("PHOENIX_MCP_BASE_URL", "http://phoenix.local")
    monkeypatch.setenv("PHOENIX_MCP_API_KEY", "test-key")

    class _FakeMCPToolset:
        def __init__(self, *, connection_params):
            self.connection_params = connection_params

        async def aclose(self):
            pass

    class _FakeStdioParams:
        def __init__(self, *, command, args):
            self.command = command
            self.args = args

    # After R6-1: `StdioServerParameters` lives in the `mcp` package, not
    # in `google.adk.tools.mcp_tool`. Stub both so the test exercises the
    # new split-import path.
    monkeypatch.setitem(
        sys.modules,
        "google.adk.tools.mcp_tool",
        types.SimpleNamespace(MCPToolset=_FakeMCPToolset),
    )
    monkeypatch.setitem(
        sys.modules, "mcp",
        types.SimpleNamespace(StdioServerParameters=_FakeStdioParams),
    )

    ts = reflector.make_phoenix_mcp_toolset()
    assert ts is not None
    assert _registry_has(ts)


def test_shutdown_all_toolsets_calls_aclose_on_each():
    """`shutdown_all_toolsets()` MUST iterate the registry and call
    `aclose` on every live entry. Regression: empty body or missing
    gather → `closed` list stays empty.
    """
    from agent import reflector

    _reset_mcp_registry()
    closed = []

    class _FakeToolset:
        def __init__(self, tag):
            self.tag = tag

        async def aclose(self):
            closed.append(self.tag)

    a, b = _FakeToolset("a"), _FakeToolset("b")
    reflector._register_toolset(a)
    reflector._register_toolset(b)

    asyncio.run(reflector.shutdown_all_toolsets())
    assert sorted(closed) == ["a", "b"], (
        f"expected aclose on both registered toolsets; got {sorted(closed)}"
    )


def test_aclose_one_with_timeout_enforces_per_toolset_timeout(monkeypatch):
    """A hung `aclose` MUST bail at `_MCP_ACLOSE_TIMEOUT_SECONDS` so
    Cloud Run's SIGTERM→SIGKILL window is respected. Regression:
    removing `asyncio.wait_for` would let this hang for ~10 s and the
    outer guard fires.
    """
    from agent import reflector

    _reset_mcp_registry()
    monkeypatch.setattr(reflector, "_MCP_ACLOSE_TIMEOUT_SECONDS", 0.05)

    class _HangingToolset:
        async def aclose(self):
            await asyncio.sleep(10.0)

    reflector._register_toolset(_HangingToolset())

    async def drive():
        await asyncio.wait_for(
            reflector.shutdown_all_toolsets(), timeout=2.0,
        )

    asyncio.run(drive())  # completes despite the 10 s sleep


def test_shutdown_continues_after_one_toolset_raises():
    """If one toolset's `aclose` raises, subsequent toolsets must still
    close. Pins the per-iteration exception isolation. Uses
    `asyncio.gather(..., return_exceptions=True)` under the hood.
    """
    from agent import reflector

    _reset_mcp_registry()
    closed = []

    class _BoomToolset:
        async def aclose(self):
            raise RuntimeError("simulated MCP transport boom")

    class _GoodToolset:
        async def aclose(self):
            closed.append("good")

    reflector._register_toolset(_BoomToolset())
    reflector._register_toolset(_GoodToolset())

    asyncio.run(reflector.shutdown_all_toolsets())
    assert closed == ["good"], (
        f"shutdown drain must isolate per-toolset failures; got {closed}"
    )


def test_aclose_one_is_idempotent_via_sentinel():
    """Per-call finally + shutdown drain both invoke
    `_aclose_one_with_timeout` on the same toolset. The sentinel
    attribute prevents double-close: aclose body runs exactly once.
    """
    from agent import reflector

    _reset_mcp_registry()
    close_count = {"n": 0}

    class _IdempotentToolset:
        async def aclose(self):
            close_count["n"] += 1

    t = _IdempotentToolset()

    async def run():
        await reflector._aclose_one_with_timeout(t)
        await reflector._aclose_one_with_timeout(t)
        await reflector._aclose_one_with_timeout(t)

    asyncio.run(run())
    assert close_count["n"] == 1, (
        f"sentinel must short-circuit duplicate closes; got {close_count['n']}"
    )


def test_shutdown_handles_empty_registry():
    """Empty drain is a no-op and must not raise. CI may not have
    spawned any toolsets when this runs in isolation.
    """
    from agent import reflector

    _reset_mcp_registry()
    asyncio.run(reflector.shutdown_all_toolsets())  # must not raise


def test_registry_no_entries_lost_under_many_concurrent_adds():
    """Concurrent `_register_toolset` from many threads must result in
    every entry landing in the set. On CPython today this passes even
    without the lock because the GIL serializes `set.add` at C level;
    the lock is defense for free-threaded CPython (PEP 703) and for the
    snapshot/iteration race in `shutdown_all_toolsets` (see
    `test_registry_lock_present_at_all_load_bearing_sites` which pins
    the lock's structural presence at all three call sites).

    Regression caught: any change that drops entries (e.g., switching
    from `set.add` to "check-then-add" without atomic semantics) would
    fail this. The thread-safety contract proper is pinned structurally
    by the source-inspection test below.
    """
    import threading

    from agent import reflector

    _reset_mcp_registry()
    N_THREADS = 16
    PER_THREAD = 25

    class _T:
        def __init__(self, key):
            self.key = key

    barrier = threading.Barrier(N_THREADS)

    def worker(seed):
        barrier.wait()
        for j in range(PER_THREAD):
            reflector._register_toolset(_T((seed, j)))

    threads = [
        threading.Thread(target=worker, args=(i,)) for i in range(N_THREADS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with reflector._mcp_toolset_registry_lock:
        size = len(reflector._mcp_toolset_registry)
    assert size == N_THREADS * PER_THREAD, (
        f"registry lost entries: expected {N_THREADS * PER_THREAD}, got {size}"
    )


def test_registry_lock_present_at_all_load_bearing_sites():
    """Source-structure test: the lock must wrap `set.add` /
    `set.discard` AND the snapshot iteration in `shutdown_all_toolsets`.
    On CPython today the GIL serializes individual `set` operations and
    `list(set)` atomically at the C level, so a runtime contention test
    cannot reliably catch the lock's removal. The locks are defense for
    free-threaded CPython (PEP 703) and for future readers who shouldn't
    have to relitigate the thread-safety question.

    Closes the R2-G2.7 mutation gap honestly: instead of a contention
    test that CPython refuses to flake (verified — 50 snapshot/drain
    cycles against a writer thread caught zero races), we pin the lock
    placement structurally. A future commit that drops the lock would
    fail this test with a clear failure message.
    """
    import inspect as _inspect

    from agent import reflector

    register_src = _inspect.getsource(reflector._register_toolset)
    assert "with _mcp_toolset_registry_lock:" in register_src, (
        "_register_toolset must hold the lock around `set.add` — "
        "defense for PEP 703 free-threaded CPython"
    )

    unregister_src = _inspect.getsource(reflector._unregister_toolset)
    assert "with _mcp_toolset_registry_lock:" in unregister_src, (
        "_unregister_toolset must hold the lock around `set.discard`"
    )

    shutdown_src = _inspect.getsource(reflector.shutdown_all_toolsets)
    # R2 round-B minor #1: the function has TWO load-bearing `with`
    # blocks — one around the snapshot (`list(_mcp_toolset_registry)`)
    # and one around the post-gather discard loop. Removing EITHER
    # silently regresses thread-safety. We assert both are present by
    # counting occurrences, not by substring presence.
    lock_block_count = shutdown_src.count("with _mcp_toolset_registry_lock:")
    assert lock_block_count >= 2, (
        f"shutdown_all_toolsets must hold the lock at BOTH the snapshot "
        f"site AND the post-gather discard site (2 `with` blocks); "
        f"found {lock_block_count}. Regression: one of the two lock "
        f"blocks was removed."
    )
    # And specifically: the snapshot line must follow the FIRST `with`
    # block (a regression that moved `list(...)` outside the `with`
    # block would silently break PEP-703 safety).
    snapshot_idx = shutdown_src.find("list(_mcp_toolset_registry)")
    first_with_idx = shutdown_src.find("with _mcp_toolset_registry_lock:")
    assert snapshot_idx > first_with_idx, (
        "list(_mcp_toolset_registry) must appear AFTER the first `with "
        "lock:` block opens, not before — otherwise the snapshot reads "
        "the set without the lock held"
    )
    # And the discard loop must follow the SECOND `with` block.
    # `set.discard(` is the discard-loop signature; the snapshot site
    # doesn't call it. Find the second occurrence of the lock-`with`
    # and verify a `discard(` follows it.
    second_with_idx = shutdown_src.find(
        "with _mcp_toolset_registry_lock:", first_with_idx + 1,
    )
    discard_idx = shutdown_src.find("_mcp_toolset_registry.discard")
    assert second_with_idx >= 0 and discard_idx > second_with_idx, (
        "the post-gather discard loop must be inside the second `with "
        "lock:` block — removing this lock would let a concurrent "
        "_register_toolset race the discard"
    )


def test_shutdown_gather_uses_return_exceptions_for_helper_failure(monkeypatch):
    """The R2-G2.4 mutation gap: `_aclose_one_with_timeout` catches
    `Exception` internally, so the gather-level `return_exceptions=True`
    looks redundant when a toolset's `aclose` raises a normal exception.
    The defense matters when the HELPER ITSELF raises (e.g., a coding
    bug, a `BaseException` subclass that escapes the inner except, or
    a `KeyboardInterrupt` during shutdown).

    We simulate this by monkeypatching the helper to raise on the first
    call. Without `return_exceptions=True`, the unhandled exception
    propagates out of `asyncio.gather` and cancels all sibling closes.
    With it, sibling closes still run.
    """
    from agent import reflector

    _reset_mcp_registry()

    closed: list[object] = []
    call_count = {"n": 0}
    real_helper = reflector._aclose_one_with_timeout

    async def fake_helper(tool):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # Simulate a helper-level failure that escapes any internal
            # `except Exception` — e.g., the helper itself has a bug.
            raise RuntimeError("simulated helper-level failure")
        await real_helper(tool)
        closed.append(tool)

    monkeypatch.setattr(reflector, "_aclose_one_with_timeout", fake_helper)

    class _T:
        async def aclose(self):
            pass

    reflector._register_toolset(_T())  # 1st helper call raises
    reflector._register_toolset(_T())  # 2nd must still run
    reflector._register_toolset(_T())  # 3rd must still run

    asyncio.run(reflector.shutdown_all_toolsets())
    assert len(closed) == 2, (
        f"`asyncio.gather(..., return_exceptions=True)` must let sibling "
        f"closes run after a helper-level failure; got {len(closed)} "
        f"successful closes (expected 2). Regression: "
        f"`return_exceptions=True` was removed from the gather call."
    )


def test_shutdown_clears_registry_after_drain():
    """After `shutdown_all_toolsets` runs, the registry is empty so a
    subsequent drain is a clean no-op. Regression: forgetting to
    discard after gather would leave dead references in the set.
    """
    from agent import reflector

    _reset_mcp_registry()

    class _T:
        async def aclose(self):
            pass

    for _ in range(3):
        reflector._register_toolset(_T())

    asyncio.run(reflector.shutdown_all_toolsets())
    with reflector._mcp_toolset_registry_lock:
        assert len(reflector._mcp_toolset_registry) == 0


def test_shutdown_skips_cross_loop_toolsets_with_warning(caplog):
    """R4-2 cross-loop hazard: a toolset constructed under `asyncio.run`
    in a worker thread is bound to THAT loop. Calling its `close()` from
    the main FastAPI loop (where the lifespan post-yield drain runs)
    raises `RuntimeError: ... bound to a different event loop` — which
    the broad `except Exception` in `_aclose_one_with_timeout` would
    swallow into a WARNING, masking the leak.

    Fix: registry stores `(toolset, loop)` tuples; the drain checks loop
    match and skips mismatched entries with a loud warning instead of
    pretending to close them.

    This test verifies the skip behavior: register a toolset under one
    loop sentinel, drain under a different loop, confirm the toolset's
    `close` is NOT called and a warning is logged.
    """
    import logging

    from agent import reflector

    _reset_mcp_registry()
    close_count = {"n": 0}

    class _T:
        async def close(self):
            close_count["n"] += 1

    t = _T()
    # Register with a fake "other loop" sentinel (a plain object stand-in
    # for an event loop the drain will not match).
    fake_other_loop = object()
    with reflector._mcp_toolset_registry_lock:
        reflector._mcp_toolset_registry.add((t, fake_other_loop))

    with caplog.at_level(logging.WARNING, logger="agent.reflector"):
        asyncio.run(reflector.shutdown_all_toolsets())

    assert close_count["n"] == 0, (
        "cross-loop toolset must NOT be closed; the per-loop binding "
        "would raise RuntimeError"
    )
    # Loud warning emitted naming the cross-loop case.
    warning_texts = [r.getMessage() for r in caplog.records]
    assert any("different event loop" in t for t in warning_texts), (
        f"expected cross-loop warning; logs={warning_texts}"
    )
    # Registry was still drained of the skipped entry (we don't want
    # an unkillable toolset hanging in the set forever).
    assert not _registry_has(t)


def test_shutdown_closes_same_loop_toolset_normally():
    """Companion to the cross-loop test: when the toolset's registered
    loop matches the current loop, `close()` IS called. Pins the
    success path of the loop-match check.
    """
    from agent import reflector

    _reset_mcp_registry()
    close_count = {"n": 0}

    class _T:
        async def close(self):
            close_count["n"] += 1

    async def drive():
        # Register from within the same loop that will run the drain.
        reflector._register_toolset(_T())
        await reflector.shutdown_all_toolsets()

    asyncio.run(drive())
    assert close_count["n"] == 1


def test_close_method_preferred_over_aclose():
    """R6-3 fix: ADK's documented MCPToolset cleanup method is `close()`,
    NOT `aclose()`. `_aclose_one_with_timeout` must try `close` FIRST,
    falling back to `aclose` only for forked / older builds that may
    expose the older name. Verifies the precedence order so a future
    refactor doesn't silently regress to the old (wrong) ordering.
    """
    from agent import reflector

    closed_via: list[str] = []

    class _BothMethods:
        async def close(self):
            closed_via.append("close")

        async def aclose(self):
            closed_via.append("aclose")

    t = _BothMethods()
    asyncio.run(reflector._aclose_one_with_timeout(t))
    assert closed_via == ["close"], (
        f"close() must be preferred over aclose(); got {closed_via}. "
        f"Regression: getattr fallback order reverted."
    )


def test_aclose_fallback_when_close_absent():
    """If a forked / older MCPToolset exposes only `aclose`, fall back
    to it. Pins the dual-method compatibility path.
    """
    from agent import reflector

    closed: list[str] = []

    class _OnlyAclose:
        async def aclose(self):
            closed.append("aclose")

    t = _OnlyAclose()
    asyncio.run(reflector._aclose_one_with_timeout(t))
    assert closed == ["aclose"]


def test_mcp_aclose_timeout_env_clamps_to_ceiling(monkeypatch):
    """R5-4 fix: `MCP_ACLOSE_TIMEOUT_SECONDS` is clamped to 8.0 s so an
    operator setting it to 99999 doesn't block FastAPI lifespan past
    Cloud Run's 10 s SIGTERM-to-SIGKILL grace window.

    Also asserts the MODULE-LEVEL invocation passes `ceiling=8.0` —
    catches a regression that removes the kwarg from the actual call
    site even if the helper still supports it.
    """
    import inspect as _inspect

    from agent import reflector

    # Direct invocation of the parser.
    monkeypatch.setenv("MCP_ACLOSE_TIMEOUT_SECONDS", "99999")
    clamped = reflector._parse_env_float(
        "MCP_ACLOSE_TIMEOUT_SECONDS", 5.0, ceiling=8.0,
    )
    assert clamped == 8.0

    monkeypatch.setenv("MCP_ACLOSE_TIMEOUT_SECONDS", "3.0")
    in_range = reflector._parse_env_float(
        "MCP_ACLOSE_TIMEOUT_SECONDS", 5.0, ceiling=8.0,
    )
    assert in_range == 3.0

    # Module-level invocation must include the ceiling. Source-inspect
    # the module so we catch a regression that removes `ceiling=8.0`
    # from the actual `_MCP_ACLOSE_TIMEOUT_SECONDS = _parse_env_float(...)`
    # call site.
    module_src = Path(reflector.__file__).read_text()
    invocation_idx = module_src.find("_MCP_ACLOSE_TIMEOUT_SECONDS = _parse_env_float(")
    assert invocation_idx >= 0, "module-level invocation not found"
    invocation_end = module_src.find(")", invocation_idx)
    invocation = module_src[invocation_idx:invocation_end + 1]
    assert "ceiling=8.0" in invocation, (
        f"module-level _MCP_ACLOSE_TIMEOUT_SECONDS must be parsed with "
        f"ceiling=8.0 to clamp operator footgun; got: {invocation!r}. "
        f"Regression: the ceiling kwarg was dropped from the call site."
    )


def test_mcp_aclose_timeout_env_falls_back_on_garbage(monkeypatch):
    """R5-1 fix: a malformed env value falls back to the default with a
    warning instead of crashing at module import.
    """
    from agent import reflector

    monkeypatch.setenv("MCP_ACLOSE_TIMEOUT_SECONDS", "not-a-float")
    result = reflector._parse_env_float(
        "MCP_ACLOSE_TIMEOUT_SECONDS", 5.0, ceiling=8.0,
    )
    assert result == 5.0  # the documented default


def test_unregister_drops_toolset_from_registry():
    """`_unregister_toolset` must remove the toolset so subsequent
    drains don't redundantly inspect it. The per-call finally relies
    on this to keep the registry bounded across many cycles.
    """
    from agent import reflector

    _reset_mcp_registry()

    class _T:
        async def aclose(self):
            pass

    t = _T()
    reflector._register_toolset(t)
    assert _registry_has(t)

    reflector._unregister_toolset(t)
    assert not _registry_has(t)

    # Unregistering a non-member is a clean no-op (idempotent).
    reflector._unregister_toolset(t)
    reflector._unregister_toolset(_T())  # never-registered, must not raise


# ===========================================================================
# Fix 5 — MCP introspection now DRIVES regression-set growth (not just
# decorative). The LlmAgent's JSON output feeds `_append_to_dataset`;
# the SDK `get_spans_dataframe` path is a documented fallback only.
# ===========================================================================


def test_parse_introspection_output_extracts_fenced_json():
    """The instruction tells the agent to wrap its result in a ```json
    fenced block. The parser must lift the `failing_spans` list out
    cleanly."""
    from agent import reflector

    text = (
        "Here is the result:\n"
        "```json\n"
        '{"failing_spans": ['
        '{"span_id": "abc123", "clause_text": "no MAC carve-out", "label": "escalate"},'
        '{"span_id": "def456", "clause_text": "anti-assignment trigger", "label": "escalate"}'
        "]}\n"
        "```\n"
    )
    spans = reflector._parse_introspection_output(text)
    assert spans is not None
    assert len(spans) == 2
    assert spans[0]["span_id"] == "abc123"
    assert spans[1]["span_id"] == "def456"


def test_parse_introspection_output_handles_raw_json():
    """If the agent skips the fence and emits raw JSON, still parseable."""
    from agent import reflector

    text = '{"failing_spans": [{"span_id": "raw1"}]}'
    spans = reflector._parse_introspection_output(text)
    assert spans == [{"span_id": "raw1"}]


def test_parse_introspection_output_empty_list_is_honored():
    """An explicit empty `failing_spans` list means MCP introspected
    successfully and found no escalations — return `[]`, NOT `None`.
    `None` would trigger the SDK fallback, which we DO NOT want when
    MCP correctly reports zero failures."""
    from agent import reflector

    text = '```json\n{"failing_spans": []}\n```'
    spans = reflector._parse_introspection_output(text)
    assert spans == []  # honored as a real result
    assert spans is not None  # NOT the fallback sentinel


def test_parse_introspection_output_returns_none_on_garbage():
    """Malformed / non-JSON output returns `None` so the cycle falls
    back to the SDK `_failing_traces` path."""
    from agent import reflector

    assert reflector._parse_introspection_output("") is None
    assert reflector._parse_introspection_output(
        "lol the model ignored its instructions"
    ) is None
    assert reflector._parse_introspection_output(
        '{"other_key": [1,2,3]}'  # valid JSON, wrong shape
    ) is None


def test_run_reflection_cycle_uses_mcp_output_to_drive_append(monkeypatch):
    """The core Fix 5 invariant: when MCP introspection returns a
    parseable list of failing spans, THOSE spans (not the SDK dataframe
    query) flow into `_append_to_dataset`.

    Pin this by stubbing the introspection agent to return a known
    JSON payload, asserting the SDK `_failing_traces` is NOT called,
    and asserting `_append_to_dataset` was called with the MCP-derived
    list.
    """
    from agent import reflector

    mcp_payload = (
        '```json\n{"failing_spans": ['
        '{"span_id": "mcp-1", "clause_text": "MCP-discovered escalation"}'
        ']}\n```'
    )

    monkeypatch.setattr(reflector, "_run_introspection_agent", lambda: mcp_payload)

    sdk_called = {"n": 0}

    def _no_sdk(*args, **kwargs):
        sdk_called["n"] += 1
        return [{"span_id": "should-not-appear"}]

    monkeypatch.setattr(reflector, "_failing_traces", _no_sdk)

    appended: dict = {}

    def fake_append(client, name, examples):
        appended["name"] = name
        appended["examples"] = list(examples)

    monkeypatch.setattr(reflector, "_append_to_dataset", fake_append)

    # Stub everything downstream so the cycle short-circuits cleanly.
    monkeypatch.setattr(reflector, "_generate_candidate_prompt", lambda f: "PROMPT")
    monkeypatch.setattr(reflector, "_upsert_prompt", lambda *a, **kw: None)
    monkeypatch.setattr(
        reflector, "_run_experiment_pairwise",
        lambda *a, **kw: (__import__("numpy").array([]), __import__("numpy").array([])),
    )
    monkeypatch.setattr(reflector, "_backstop_run_evals", lambda *a, **kw: None)

    # Stub phoenix.client.Client so the cycle reaches the introspection step.
    import sys
    import types

    fake_phoenix = types.ModuleType("phoenix")
    fake_phoenix_client = types.ModuleType("phoenix.client")
    fake_phoenix_client.Client = lambda: object()
    monkeypatch.setitem(sys.modules, "phoenix", fake_phoenix)
    monkeypatch.setitem(sys.modules, "phoenix.client", fake_phoenix_client)

    reflector.run_reflection_cycle()

    assert sdk_called["n"] == 0, (
        "SDK `_failing_traces` must NOT be called when MCP introspection "
        "produced a parseable failing-spans list — that's the whole point "
        "of Fix 5 (MCP drives the write, SDK is fallback only)."
    )
    assert appended.get("name") == "regressions-v1"
    assert len(appended.get("examples", [])) == 1
    assert appended["examples"][0]["span_id"] == "mcp-1"


def test_run_reflection_cycle_falls_back_to_sdk_when_mcp_unparseable(monkeypatch):
    """Fallback policy contract: when MCP produces garbage / empty
    output (e.g. model outage, env unset), the cycle MUST fall back to
    the deterministic SDK `_failing_traces` path so the nightly
    regression dataset still grows."""
    from agent import reflector

    monkeypatch.setattr(reflector, "_run_introspection_agent", lambda: "")

    sdk_called = {"n": 0}

    def fake_sdk(client, project, hours):
        sdk_called["n"] += 1
        return [{"span_id": "sdk-fallback-1"}]

    monkeypatch.setattr(reflector, "_failing_traces", fake_sdk)

    appended: dict = {}

    def fake_append(client, name, examples):
        appended["name"] = name
        appended["examples"] = list(examples)

    monkeypatch.setattr(reflector, "_append_to_dataset", fake_append)
    monkeypatch.setattr(reflector, "_generate_candidate_prompt", lambda f: "PROMPT")
    monkeypatch.setattr(reflector, "_upsert_prompt", lambda *a, **kw: None)
    monkeypatch.setattr(
        reflector, "_run_experiment_pairwise",
        lambda *a, **kw: (__import__("numpy").array([]), __import__("numpy").array([])),
    )
    monkeypatch.setattr(reflector, "_backstop_run_evals", lambda *a, **kw: None)

    import sys
    import types

    fake_phoenix = types.ModuleType("phoenix")
    fake_phoenix_client = types.ModuleType("phoenix.client")
    fake_phoenix_client.Client = lambda: object()
    monkeypatch.setitem(sys.modules, "phoenix", fake_phoenix)
    monkeypatch.setitem(sys.modules, "phoenix.client", fake_phoenix_client)

    reflector.run_reflection_cycle()

    assert sdk_called["n"] == 1, "SDK fallback must fire on unparseable MCP output"
    assert appended.get("examples") == [{"span_id": "sdk-fallback-1"}]


def test_run_reflection_cycle_honors_empty_mcp_result(monkeypatch):
    """An explicit empty MCP result (`failing_spans: []`) is a SUCCESS,
    not a fallback trigger. The SDK path must NOT run. Append is still
    called (with an empty list — `_append_to_dataset` short-circuits
    on empty per its own contract).
    """
    from agent import reflector

    monkeypatch.setattr(
        reflector, "_run_introspection_agent",
        lambda: '```json\n{"failing_spans": []}\n```',
    )

    sdk_called = {"n": 0}
    monkeypatch.setattr(
        reflector, "_failing_traces",
        lambda *a, **kw: sdk_called.__setitem__("n", sdk_called["n"] + 1) or [],
    )

    appended: dict = {}
    monkeypatch.setattr(
        reflector, "_append_to_dataset",
        lambda c, name, ex: appended.update({"name": name, "examples": list(ex)}),
    )
    monkeypatch.setattr(reflector, "_generate_candidate_prompt", lambda f: "PROMPT")
    monkeypatch.setattr(reflector, "_upsert_prompt", lambda *a, **kw: None)
    monkeypatch.setattr(
        reflector, "_run_experiment_pairwise",
        lambda *a, **kw: (__import__("numpy").array([]), __import__("numpy").array([])),
    )
    monkeypatch.setattr(reflector, "_backstop_run_evals", lambda *a, **kw: None)

    import sys
    import types

    fake_phoenix = types.ModuleType("phoenix")
    fake_phoenix_client = types.ModuleType("phoenix.client")
    fake_phoenix_client.Client = lambda: object()
    monkeypatch.setitem(sys.modules, "phoenix", fake_phoenix)
    monkeypatch.setitem(sys.modules, "phoenix.client", fake_phoenix_client)

    reflector.run_reflection_cycle()

    assert sdk_called["n"] == 0, (
        "empty MCP result is a real answer, not a fallback trigger"
    )
    assert appended["examples"] == []


def test_assert_writable_invariant_survives_rewire():
    """Fix 5 explicit precondition: the allowlist invariant must survive.
    Re-pin here so a future change to the MCP path that somehow widens
    the writable set is caught alongside the rewire test."""
    from agent import reflector

    reflector.assert_writable("regressions-v1")
    with pytest.raises(PermissionError):
        reflector.assert_writable(reflector._FROZEN_HELD_OUT)
    # Pin the allowlist's identity so a regression that widens it (e.g. adds the
    # frozen fold-5 or the frozen citation gold) is caught. The citation-linkage
    # layer added exactly one writable dataset (citation-regressions); the gold
    # set (citation-gold-v1) stays frozen — never writable.
    assert reflector._WRITABLE_DATASETS == frozenset(
        {"regressions-v1", "citation-regressions"}
    )
    assert reflector._FROZEN_HELD_OUT == "internal-30-holdout-fold-5"
    assert reflector._FROZEN_HELD_OUT not in reflector._WRITABLE_DATASETS
    assert "citation-gold-v1" not in reflector._WRITABLE_DATASETS
    with pytest.raises(PermissionError):
        reflector.assert_writable("citation-gold-v1")


def test_append_to_dataset_enforces_allowlist_on_mcp_input():
    """Even if a malicious / buggy MCP output named the frozen fold-5
    as the target dataset, the allowlist gate inside `_append_to_dataset`
    must still raise. This is the Arize-juror invariant: the frozen
    held-out set is code-level tamper-evident regardless of where the
    failing list came from."""
    from agent import reflector

    with pytest.raises(PermissionError):
        reflector._append_to_dataset(
            client=object(),
            dataset_name=reflector._FROZEN_HELD_OUT,
            examples=[{"span_id": "x"}],
        )
