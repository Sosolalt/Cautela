"""Reflector self-improvement loop (plan §6.3, statistically-honest).

Single ADK agent process that holds:
  - Phoenix MCP tools via google.adk.tools.mcp_tool.MCPToolset (for the
    "agent inspects its own traces" beat in the demo). The MCPToolset is
    built by `make_phoenix_mcp_toolset()` and mounted on the introspection
    sub-agent at construction time.
  - phoenix.client.Client() for deterministic SDK steps (datasets,
    experiments, prompts).

Verified Phoenix client API (installed SDK — re-checked 2026-06-10):
  - client.datasets.get_dataset(dataset=...) returns a Dataset object
    (the kwarg is `dataset=`, NOT `name=`).
  - client.datasets.add_examples_to_dataset(dataset=Dataset, examples=...)
    (renamed from the old `append_examples`).
  - client.prompts.get(prompt_identifier=, tag=)
  - client.prompts.create(name=, version=PromptVersion([msgs], model_name=...))
    — PromptVersion takes a message list + model_name, NOT a `template=` kwarg.
  - client.prompts.tags.create(prompt_version_id=, name=, description=)
  - client.experiments.run_experiment(dataset=Dataset, task=, evaluators=None, ...)
    (keyword-only; `dataset` is a Dataset object).

Promotion rule:
  1. paired_bootstrap_ci_lower_bound(regression_deltas, 1000) > 0
     ONE-SIDED at 95% (alpha not alpha/2).
  AND
  2. cand_score_on_fold5 >= prod_score_on_fold5 - eps_fold5,
     where eps_fold5 = max(paired_bootstrap_se(fold5_deltas), 0.03)

The frozen `internal-30-holdout-fold-5` dataset is enforced via a
code-level WRITABLE allowlist — the Reflector can ONLY append to
datasets in `_WRITABLE_DATASETS`. PermissionError otherwise.
"""
from __future__ import annotations

import asyncio
import atexit
import functools
import inspect as _inspect
import logging
import os
import threading
from typing import Sequence

import numpy as np

_LOG = logging.getLogger(__name__)

# Code-enforced allowlist. The Reflector is FORBIDDEN from writing to
# any dataset not in this set. The frozen held-out fold-5 is absent.
_WRITABLE_DATASETS: frozenset[str] = frozenset(
    {"regressions-v1", "citation-regressions"}
)
_FROZEN_HELD_OUT: str = "internal-30-holdout-fold-5"


# ---------------------------------------------------------------------------
# MCP toolset process-shutdown registry
# ---------------------------------------------------------------------------
# Per-call cleanup in `_run_introspection_agent_async`'s try/finally is the
# fast path and handles the common case. The registry below is the safety
# net for "process dies between MCPToolset construction and the finally
# block" — SIGTERM during a /reflect cycle, uncaught exception in the
# executor thread, FastAPI lifespan teardown mid-call. Without it, the
# `npx @arizeai/phoenix-mcp` node subprocess leaks one PID per orphan and
# Cloud Run eventually exhausts file descriptors.
#
# Strong-set + threading.Lock instead of WeakSet because (a) MCPToolset is
# not guaranteed weak-referenceable across ADK versions, (b) make_*_toolset
# can be called from multiple worker threads concurrently — the Reflector's
# /reflect handler runs the cycle on `run_in_executor`, while a CLI cron run
# (`python -m agent.reflector`) builds on the main thread. threading.Lock
# is needed; asyncio.Lock won't serialize across threads.
#
# Each entry is `(toolset, loop)` so the lifespan drain can detect a
# cross-loop hazard: a toolset constructed inside `asyncio.run(...)` in
# a worker thread is bound to THAT loop; awaiting its `close()` from the
# main FastAPI loop raises `RuntimeError: ... bound to a different event
# loop` (R4-2 bug-hunter finding). The drain skips mismatched-loop
# entries with a loud warning rather than silently leaking the
# subprocess via a swallowed exception.
_mcp_toolset_registry: set[tuple[object, object]] = set()
_mcp_toolset_registry_lock = threading.Lock()
# Sentinel attribute stamped on a toolset after a successful or failed
# aclose() so per-call finally + lifespan drain can both fire safely.
_MCP_CLOSED_ATTR = "_ma_gatekeeper_aclose_done"
# Per-toolset hard timeout for aclose(). Cloud Run's SIGTERM-to-SIGKILL
# grace window is 10 s; we want headroom for the rest of FastAPI's
# lifespan-shutdown work after our drain finishes. The value is parsed
# defensively (R5-1) and hard-clamped to ≤ 8.0 s (R5-4) so an operator
# footgun (`MCP_ACLOSE_TIMEOUT_SECONDS=999`) can't block container
# shutdown past Cloud Run's grace window.
def _parse_env_float(name: str, default: float, *, ceiling: float | None = None) -> float:
    raw = os.environ.get(name, str(default))
    try:
        value = float(raw)
    except ValueError:
        _LOG.warning(
            "%s=%r is not a valid float; falling back to default %s",
            name, raw, default,
        )
        return default
    if ceiling is not None and value > ceiling:
        _LOG.warning(
            "%s=%s exceeds ceiling %s; clamping to %s "
            "(prevents shutdown-drain from blocking past Cloud Run's "
            "10 s SIGTERM grace window).",
            name, value, ceiling, ceiling,
        )
        return ceiling
    return value


_MCP_ACLOSE_TIMEOUT_SECONDS = _parse_env_float(
    "MCP_ACLOSE_TIMEOUT_SECONDS", 5.0, ceiling=8.0,
)


def _current_loop_or_none():
    """Return the currently-running asyncio loop, or None if called
    from sync context. We capture this at registration so the drain
    knows which loop the toolset's stdio transport is bound to."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def _register_toolset(tool) -> None:
    if tool is None:
        return
    loop = _current_loop_or_none()
    with _mcp_toolset_registry_lock:
        _mcp_toolset_registry.add((tool, loop))


def _unregister_toolset(tool) -> None:
    if tool is None:
        return
    with _mcp_toolset_registry_lock:
        # Remove every entry referencing this toolset regardless of loop —
        # the per-call finally that calls this knows the toolset is
        # closed; we want all registry entries gone.
        to_remove = {
            entry for entry in _mcp_toolset_registry if entry[0] is tool
        }
        _mcp_toolset_registry.difference_update(to_remove)


async def _aclose_one_with_timeout(tool) -> None:
    """Close a single MCP toolset with a hard per-instance timeout.

    Idempotent via `_MCP_CLOSED_ATTR`: per-call finally and the
    lifespan drain both call this; only the first run does real work.
    Sentinel is stamped BEFORE awaiting so a concurrent second caller
    short-circuits — there's a tiny window where two awaiters arrive
    before either stamps, accepted because ADK's `MCPToolset.close()`
    docstring documents it as "safe to call multiple times and handles
    cleanup errors gracefully" (R6 WebFetch-verified against the live
    mcp_toolset.py source — see PROJECT_LOG Phase-6 honesty pass).

    ADK contract is `close()`, NOT `aclose()` (R6 WebFetch). We keep
    the `aclose` fallback for older / forked ADK builds that might
    expose either name, but `close` is the documented method and
    must be tried FIRST so we never miss the canonical entry point.
    """
    if tool is None or getattr(tool, _MCP_CLOSED_ATTR, False):
        return
    try:
        setattr(tool, _MCP_CLOSED_ATTR, True)
    except Exception:
        # Slots-only stubs may refuse attribute writes; close anyway.
        pass
    # Prefer `close` (ADK 1.x canonical). Fall back to `aclose` only
    # for forked/older builds where the method name differs.
    close = getattr(tool, "close", None) or getattr(tool, "aclose", None)
    if close is None:
        return
    try:
        result = close()
        if _inspect.isawaitable(result):
            await asyncio.wait_for(
                result, timeout=_MCP_ACLOSE_TIMEOUT_SECONDS,
            )
    except asyncio.TimeoutError:
        _LOG.warning(
            "MCPToolset.aclose() exceeded %ss timeout for %s; subprocess "
            "may leak until container exit",
            _MCP_ACLOSE_TIMEOUT_SECONDS, type(tool).__name__,
        )
    except Exception as exc:
        _LOG.warning(
            "MCPToolset.aclose() failed for %s: %s",
            type(tool).__name__, exc,
        )


async def shutdown_all_toolsets() -> None:
    """Drain every registered MCPToolset whose loop matches the current
    one, bounded by per-instance timeout.

    Called from the FastAPI lifespan post-yield phase AND from the
    `atexit` handler below. Snapshots the registry under the lock so a
    concurrent unregister during shutdown doesn't trigger
    `RuntimeError: set changed size during iteration`.

    Cross-loop hazard (R4-2): a toolset whose stdio transport was
    bound to a now-dead worker-thread loop CANNOT be cleanly closed
    from the FastAPI main loop — `asyncio` internals raise
    `RuntimeError: ... bound to a different event loop` and the broad
    `except Exception` in `_aclose_one_with_timeout` would swallow it
    into a WARNING, leaving the npx subprocess leaked. We detect the
    mismatch up front and skip with a loud warning instead. The OS
    reaps the orphaned npx when the container exits — acceptable for
    Cloud Run's scale-to-zero lifecycle.

    Closes the surviving (same-loop) entries in parallel via
    `asyncio.gather(..., return_exceptions=True)` so a single
    per-instance hang doesn't serialize the whole drain.
    """
    with _mcp_toolset_registry_lock:
        snapshot = list(_mcp_toolset_registry)
    if not snapshot:
        return

    current_loop = _current_loop_or_none()
    same_loop: list[object] = []
    cross_loop: list[tuple[object, object]] = []
    for tool, registered_loop in snapshot:
        # `registered_loop is None` means registration happened from
        # sync context — safe to close from any loop.
        if registered_loop is None or registered_loop is current_loop:
            same_loop.append(tool)
        else:
            cross_loop.append((tool, registered_loop))

    if cross_loop:
        _LOG.warning(
            "Skipping %d MCP toolset(s) bound to a different event loop "
            "than the shutdown drain — cleanup deferred to OS process "
            "reap. npx subprocess(es) may persist briefly after container "
            "exit. This is the R4-2 cross-loop case; per-call finally "
            "is the primary cleanup path and should have caught these.",
            len(cross_loop),
        )

    if same_loop:
        _LOG.info(
            "Draining %d MCP toolset(s) at process shutdown", len(same_loop),
        )
        await asyncio.gather(
            *(_aclose_one_with_timeout(t) for t in same_loop),
            return_exceptions=True,
        )

    with _mcp_toolset_registry_lock:
        for entry in snapshot:
            _mcp_toolset_registry.discard(entry)


def _atexit_drain() -> None:
    """Best-effort drain at interpreter shutdown for the non-FastAPI path
    (CLI Reflector run, ad-hoc `python -m agent.reflector`). FastAPI's
    lifespan covers the served `/reflect` route; this covers the rest.

    atexit fires AFTER FastAPI lifespan but before module-globals
    teardown, so a redundant drain is harmless (registry is empty by
    then). Will not fire on SIGKILL or `os._exit` — those leak by
    definition; the OS reaps the container.
    """
    with _mcp_toolset_registry_lock:
        empty = len(_mcp_toolset_registry) == 0
    if empty:
        return
    try:
        asyncio.run(shutdown_all_toolsets())
    except RuntimeError:
        # No event loop available (or one is closed). Don't crash exit.
        _LOG.warning("atexit MCP drain skipped: no available event loop")
    except Exception as exc:
        _LOG.warning("atexit MCP drain failed: %s", exc)


atexit.register(_atexit_drain)


def _escalate_trace_records(
    client, *, project_name: str, lookback_hours: int,
) -> list[dict]:
    """Return one record per span whose `risk_judge_gate` annotation routed
    to 'escalate' within the lookback window.

    Uses the SEPARATE span-annotations dataframe API on purpose:
    `get_spans_dataframe` does NOT surface annotations as columns in this
    SDK, so the old column-probe in `_failing_traces` always returned []
    (a silent no-op that, together with the dead npx MCP path, was why the
    Reflector loop never had traces to learn from). We window the spans by
    `start_time`, then join their annotations and keep the escalations.

    Verified against arize-phoenix-client (≥1.17): annotations dataframe is
    indexed by `span_id`, the annotation name lives in `annotation_name`,
    and the routed lane label is the flattened `result.label` column.
    """
    from datetime import datetime, timedelta, timezone

    # The phoenix.client default timeout is 5s — too tight for the POST
    # v1/spans query against a cold/maxScale=1 Cloud Run Phoenix, where it
    # ReadTimeouts and the loop sees zero traces. Use a generous,
    # env-overridable window.
    timeout = int(os.environ.get("REFLECTOR_PHOENIX_TIMEOUT_SECONDS", "45"))
    limit = int(os.environ.get("REFLECTOR_SPAN_SCAN_LIMIT", "2000"))
    start_time = datetime.now(timezone.utc) - timedelta(hours=max(lookback_hours, 0))
    # Project ONLY the span id. The deployed Phoenix (1Gi) returns HTTP 500
    # when serializing more than a handful of FULL spans (clause text rides
    # in span attributes), so the default full-attribute frame at limit=1000
    # reliably errors — verified live, and the original root cause hidden
    # behind the dead npx path. A span_id-only projection keeps the payload
    # tiny and serves at high limits; annotations are fetched separately.
    try:
        from phoenix.client.types.spans import SpanQuery
        query = SpanQuery().select("context.span_id")
    except Exception:
        query = None  # degraded: full frame may 500 on a memory-bound Phoenix
    spans = client.spans.get_spans_dataframe(
        query=query, project_identifier=project_name,
        start_time=start_time, limit=limit, timeout=timeout,
    )
    if spans is None or len(spans) == 0:
        return []
    if "context.span_id" in spans.columns:
        scan_ids = [str(x) for x in spans["context.span_id"].tolist()]
    elif "span_id" in spans.columns:
        scan_ids = [str(x) for x in spans["span_id"].tolist()]
    else:
        scan_ids = [str(x) for x in spans.index.tolist()]
    scan_ids = [s for s in scan_ids if s and s.lower() != "nan"]
    if not scan_ids:
        return []
    ann = client.spans.get_span_annotations_dataframe(
        span_ids=scan_ids,
        project_identifier=project_name,
        include_annotation_names=["risk_judge_gate"],
        timeout=timeout,
    )
    if ann is None or len(ann) == 0:
        return []
    # `result.label` is the canonical column in arize-phoenix-client ≥1.17;
    # the others are tolerated for forward/backward minor-version drift.
    label_col = next(
        (c for c in ("result.label", "label", "risk_judge_gate.label",
                     "annotation.risk_judge_gate.label")
         if c in ann.columns),
        None,
    )
    if label_col is None:
        _LOG.warning(
            "risk_judge_gate label column absent; annotation cols=%s",
            list(ann.columns)[:30],
        )
        return []
    escalate = ann[ann[label_col] == "escalate"]
    if len(escalate) == 0:
        return []
    # span_id is the annotations-dataframe index (set_index('span_id') in the
    # SDK); fall back to a column if a future version stops indexing on it.
    if "span_id" in escalate.columns:
        span_ids = escalate["span_id"].tolist()
    elif "context.span_id" in escalate.columns:
        span_ids = escalate["context.span_id"].tolist()
    else:
        span_ids = list(escalate.index)
    return [{"span_id": str(sid), "label": "escalate"} for sid in span_ids]


class _DirectPhoenixToolset:
    """Direct `phoenix.client` implementation of the one MCP tool the
    Reflector loop hard-gate needs: `list_traces`.

    The npx `@arizeai/phoenix-mcp` server is unavailable in the
    `python:3.12-slim` Cloud Run image (no node runtime), so the
    LoopAgent's `_call_mcp_list_traces` hard gate would always see zero
    traces and early-exit. This toolset exposes the SAME callable contract
    `list_traces(*, project_name, lookback_hours)` — the exact shape
    `reflector_loop._call_mcp_list_traces` invokes via
    `getattr(toolset, "list_traces")` — backed by `phoenix.client`
    directly (no subprocess). Opt back into the npx server with
    REFLECTOR_USE_NPX_MCP=1.
    """

    def __init__(self, client=None) -> None:
        self._client = client
        self._closed = False

    def _get_client(self):
        if self._client is None:
            from phoenix.client import Client
            self._client = Client()
        return self._client

    def list_traces(self, *, project_name: str, lookback_hours: int) -> list[dict]:
        try:
            return _escalate_trace_records(
                self._get_client(),
                project_name=project_name,
                lookback_hours=lookback_hours,
            )
        except Exception as exc:
            _LOG.warning("_DirectPhoenixToolset.list_traces failed: %s", exc)
            return []

    async def close(self) -> None:
        # No subprocess to reap; idempotent so the registry-aware drain
        # (`_aclose_one_with_timeout` → getattr(tool, "close")) is a no-op.
        self._closed = True


def _make_npx_mcp_toolset():
    """The original npx `@arizeai/phoenix-mcp` stdio MCPToolset (opt-in).

    Requires a node runtime (absent from `python:3.12-slim`) plus
    PHOENIX_MCP_BASE_URL/PHOENIX_MCP_API_KEY. Enabled only when
    REFLECTOR_USE_NPX_MCP=1; otherwise `make_phoenix_mcp_toolset` returns
    the direct phoenix.client toolset above.

    `StdioServerParameters` is exported from the upstream `mcp` package,
    NOT from `google.adk.tools.mcp_tool` (R6 WebFetch-verified). Importing
    it from ADK previously worked only via test-suite stubbing; on a clean
    install it raised ImportError, silently swallowed by the broad except.
    """
    try:
        from google.adk.tools.mcp_tool import MCPToolset
        from mcp import StdioServerParameters
    except Exception as exc:
        _LOG.warning("MCPToolset unavailable: %s", exc)
        return None
    base_url = os.environ.get("PHOENIX_MCP_BASE_URL", "")
    api_key = os.environ.get("PHOENIX_MCP_API_KEY", "")
    if not base_url or not api_key:
        _LOG.info(
            "Phoenix MCP base URL or API key unset; npx MCP path disabled."
        )
        return None
    params = StdioServerParameters(
        command="npx",
        args=[
            "-y", "@arizeai/phoenix-mcp@latest",
            "--baseUrl", base_url,
            "--apiKey", api_key,
        ],
    )
    toolset = MCPToolset(connection_params=params)
    _register_toolset(toolset)
    return toolset


def make_phoenix_mcp_toolset():
    """Hook 4 — the toolset whose `list_traces` the Reflector loop hard-gate calls.

    Two implementations:
      - DEFAULT: `_DirectPhoenixToolset`, backed by `phoenix.client`. Works
        in the `python:3.12-slim` Cloud Run image (no node). The npx server
        is no longer the default because, without a node runtime, it failed
        at spawn → `list_traces` returned [] → the loop early-exited every
        time (the root cause of "SELF-IMPROVE NOW never promotes").
      - OPT-IN (`REFLECTOR_USE_NPX_MCP=1`): the original npx
        `@arizeai/phoenix-mcp` stdio MCPToolset, for environments that do
        have node and want the full MCP tool surface.

    Returns None when Phoenix is unconfigured (no PHOENIX_COLLECTOR_ENDPOINT /
    PHOENIX_API_KEY), so local/CI runs that inject their own toolset via
    `toolset_factory` are unaffected.
    """
    if os.environ.get("REFLECTOR_USE_NPX_MCP", "0") == "1":
        return _make_npx_mcp_toolset()
    configured = bool(
        os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
        or os.environ.get("PHOENIX_API_KEY")
    )
    if not configured:
        _LOG.info(
            "Phoenix unconfigured (no PHOENIX_COLLECTOR_ENDPOINT/API_KEY); "
            "Reflector toolset is a no-op."
        )
        return None
    toolset = _DirectPhoenixToolset()
    _register_toolset(toolset)
    return toolset


def build_introspection_agent():
    """LlmAgent that calls Phoenix MCP tools to inspect its own traces.

    Invoked at the START of run_reflection_cycle so the chosen failing
    traces include the agent's own recent reasoning. This is the
    "meta-agentic observability" beat the Arize-track judges look for.
    """
    toolset = make_phoenix_mcp_toolset()
    if toolset is None or isinstance(toolset, _DirectPhoenixToolset):
        # The direct phoenix.client toolset is NOT an ADK tool — it can't be
        # mounted on an LlmAgent. The cron introspection beat needs the npx
        # MCPToolset (REFLECTOR_USE_NPX_MCP=1); when it's absent the cron
        # cycle falls back to the deterministic `_failing_traces` SDK path.
        return None
    try:
        from google.adk.agents import LlmAgent
    except Exception:
        return None
    return LlmAgent(
        name="reflector_introspector",
        model=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview"),
        instruction=(
            "You are inspecting the M&A Gatekeeper's own traces. Use the "
            "phoenix-mcp tools to: (1) list_traces from project 'ma-gatekeeper' "
            "in the last 24h, (2) per trace fetch the risk_judge_gate "
            'annotation, (3) keep only escalation-tagged spans. Final message '
            'MUST be a single ```json block: {"failing_spans": [{"span_id": '
            '"<id>", "clause_text": "<text>", "label": "escalate"}, ...]}.'
        ),
        tools=[toolset],
    )


async def _run_introspection_agent_async() -> str:
    """Async body of Hook 4 — invoke the MCP-mounted introspection agent.

    Lives as an `async def` so we can `await` ADK's sync-or-async
    create_session shim cleanly and drive `runner.run_async`'s async
    generator with `async for`. The sync wrapper below calls this via
    `asyncio.run` from inside a worker thread.

    Cleans up the MCP `Toolset` subprocess(es) on every exit path —
    `npx -y @arizeai/phoenix-mcp@latest` is a child process spawned
    per toolset construction; if we don't close it, the nightly
    Reflector cron leaks one `node` process per cycle and Cloud Run
    eventually exhausts file descriptors. Found by Designer B in
    Issue-5 review — silent failure mode that the bare `except` in
    the old sync code masked completely.
    """
    agent = build_introspection_agent()
    if agent is None:
        _LOG.info("Hook 4: introspection agent unavailable (MCP env unset?).")
        return ""

    import inspect as _inspect
    from google.adk.runners import InMemoryRunner
    from google.genai import types as gtypes

    runner = InMemoryRunner(agent=agent, app_name="ma-gatekeeper-reflector")
    session_id = "introspection-" + os.urandom(4).hex()
    try:
        result = runner.session_service.create_session(
            app_name="ma-gatekeeper-reflector",
            user_id="reflector", session_id=session_id,
        )
        if _inspect.isawaitable(result):
            await result

        msg = gtypes.Content(
            role="user",
            parts=[gtypes.Part(text=(
                "Use the phoenix-mcp tools to list yesterday's traces in "
                "project 'ma-gatekeeper' and return a compact summary of "
                "escalation-tagged spans."
            ))],
        )
        chunks: list[str] = []
        async for event in runner.run_async(
            user_id="reflector", session_id=session_id, new_message=msg,
        ):
            content = getattr(event, "content", None)
            parts = getattr(content, "parts", None) or []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    chunks.append(t)
        return "\n".join(chunks)
    finally:
        # Reap MCP stdio child processes via the registry-aware helper
        # so per-call cleanup and the lifespan-shutdown drain converge
        # on a single idempotent path. Both paths can fire (the per-
        # call cleanup is the fast path; the lifespan drain catches
        # the "process dies before this finally runs" case); the
        # `_MCP_CLOSED_ATTR` sentinel ensures aclose only runs once.
        for tool in getattr(agent, "tools", None) or []:
            await _aclose_one_with_timeout(tool)
            _unregister_toolset(tool)


def _run_introspection_agent() -> str:
    """Hook 4 sync wrapper — invoked from `run_reflection_cycle`, which
    itself runs in a `run_in_executor` worker thread off the FastAPI
    request loop.

    `asyncio.run` is the right primitive here: it creates a fresh loop,
    sets it as the current loop for the duration, awaits the coroutine,
    and runs `shutdown_asyncgens` + closes the loop on exit. The
    previous `asyncio.get_event_loop().run_until_complete(...)` pattern
    raises `DeprecationWarning` on Python 3.12 (no loop in this thread)
    and `RuntimeError` on Python 3.14 — silently swallowed by the old
    bare `except`, which made Hook 4 a quietly-dead beat.

    Re-raises `CancelledError` (server shutdown should propagate); all
    other exceptions log with traceback + return "" so a Phoenix/MCP
    outage doesn't abort the nightly cycle.
    """
    try:
        return asyncio.run(_run_introspection_agent_async())
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOG.warning("Hook 4 introspection agent failed", exc_info=True)
        return ""


def assert_writable(dataset_name: str) -> None:
    if dataset_name not in _WRITABLE_DATASETS:
        raise PermissionError(
            f"Reflector forbidden from writing to dataset '{dataset_name}'. "
            f"Allowlist: {sorted(_WRITABLE_DATASETS)}"
        )


# ---------- statistics ----------

def paired_bootstrap_ci_lb(
    deltas: np.ndarray,
    *,
    n_resamples: int = 1000,
    alpha: float = 0.05,
    seed: int | None = 42,
) -> float:
    """One-sided lower bound at confidence (1-alpha) on mean(deltas).

    For a one-sided "candidate beats production" gate at alpha=0.05,
    we use the alpha-th percentile (5th), NOT alpha/2 (2.5th). v1 used
    alpha/2 which was actually a 97.5% one-sided LB (more conservative
    than advertised). Fixed per ML-reviewer findings.
    """
    if len(deltas) == 0:
        return float("-inf")
    rng = np.random.default_rng(seed)
    n = len(deltas)
    means = np.empty(n_resamples)
    for k in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[k] = deltas[idx].mean()
    return float(np.quantile(means, alpha))


def paired_bootstrap_se(
    deltas: np.ndarray,
    *,
    n_resamples: int = 1000,
    seed: int | None = 42,
) -> float:
    if len(deltas) == 0:
        return 0.0
    rng = np.random.default_rng(seed)
    n = len(deltas)
    means = np.empty(n_resamples)
    for k in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[k] = deltas[idx].mean()
    return float(means.std(ddof=1))


def epsilon_fold5(fold5_deltas: np.ndarray, *, floor: float = 0.03) -> float:
    """Plan §6.3 step 6: eps = max(1× paired bootstrap SE on fold 5, 0.03)."""
    return max(paired_bootstrap_se(fold5_deltas), floor)


def should_promote(
    *,
    regression_deltas: np.ndarray,
    fold5_candidate_scores: np.ndarray,
    fold5_production_scores: np.ndarray,
    citation_candidate_scores: np.ndarray | None = None,
    citation_production_scores: np.ndarray | None = None,
) -> tuple[bool, dict[str, float]]:
    """Return (promote, diagnostics) per plan §6.3 step 6, with the
    citation-linkage composite gate (design/STATUTE_LAYER.md §3.4).

    The two original gates are unchanged. A THIRD necessary condition is added:
    the candidate's `citation_exact_match` on citation-gold-v1 must not regress
    beyond a paired-bootstrap-SE band (floored at 0.05):

        cit_candidate_mean >= cit_production_mean - max(SE(cit_deltas), 0.05)

    It is a *necessary* condition (AND-ed with the others), never a way to
    promote a model the regression/fold-5 gates would block. When no citation
    experiment ran (scores omitted), the gate is vacuously satisfied so existing
    callers keep their two-gate behavior.
    """
    fold5_deltas = fold5_candidate_scores - fold5_production_scores
    ci_lb_reg = paired_bootstrap_ci_lb(regression_deltas)
    eps = epsilon_fold5(fold5_deltas)
    cand_mean = float(fold5_candidate_scores.mean()) if len(fold5_candidate_scores) else 0.0
    prod_mean = float(fold5_production_scores.mean()) if len(fold5_production_scores) else 0.0
    non_regression_ok = cand_mean >= prod_mean - eps

    cit_cand = citation_candidate_scores if citation_candidate_scores is not None else np.array([])
    cit_prod = citation_production_scores if citation_production_scores is not None else np.array([])
    if len(cit_cand) and len(cit_prod) and len(cit_cand) == len(cit_prod):
        cit_deltas = cit_cand - cit_prod
        cit_eps = max(paired_bootstrap_se(cit_deltas), 0.05)
        cit_cand_mean = float(cit_cand.mean())
        cit_prod_mean = float(cit_prod.mean())
        citation_gate_ok = cit_cand_mean >= cit_prod_mean - cit_eps
    else:
        # No citation experiment this cycle — gate is vacuously satisfied.
        cit_eps, cit_cand_mean, cit_prod_mean, citation_gate_ok = 0.05, 0.0, 0.0, True

    diag = {
        "regression_ci_lb": ci_lb_reg,
        "epsilon_fold5": eps,
        "fold5_candidate_mean": cand_mean,
        "fold5_production_mean": prod_mean,
        "fold5_non_regression_ok": float(non_regression_ok),
        "regression_gate_ok": float(ci_lb_reg > 0),
        "citation_epsilon": cit_eps,
        "citation_candidate_mean": cit_cand_mean,
        "citation_production_mean": cit_prod_mean,
        "citation_gate_ok": float(citation_gate_ok),
    }
    promote = (ci_lb_reg > 0) and non_regression_ok and citation_gate_ok
    return promote, diag


# ---------- Phoenix wiring (real signatures, but a hackathon-quality
# implementation: enough to demo the loop end-to-end on Internal-30).

def _failing_traces(client, project_name: str, lookback_hours: int) -> list[dict]:
    """Pull spans whose `risk_judge_gate` annotation routed to 'escalate'.

    Delegates to `_escalate_trace_records`, which uses the SEPARATE
    span-annotations dataframe API. The previous implementation probed
    `get_spans_dataframe` for annotation columns this SDK never surfaces,
    so it always returned [] — a silent no-op that helped starve the
    Reflector loop of traces. Filtering to 'escalate' happens inside the
    helper (auto_clear/block are not failures; block is a deliberate stop).
    """
    try:
        return _escalate_trace_records(
            client, project_name=project_name, lookback_hours=lookback_hours,
        )
    except Exception as exc:
        _LOG.warning("Failed to pull traces: %s", exc)
        return []


def _append_to_dataset(client, dataset_name: str, examples: Sequence[dict]) -> None:
    assert_writable(dataset_name)
    if not examples:
        return
    try:
        ds = client.datasets.get_dataset(dataset=dataset_name)
        client.datasets.add_examples_to_dataset(dataset=ds, examples=list(examples))
    except Exception as exc:
        _LOG.warning("append_to_dataset failed: %s", exc)


def _generate_candidate_prompt(failing_examples: Sequence[dict]) -> str:
    """Use Gemini to draft an improved cross_reference prompt.

    The meta-prompt is intentionally small for the hackathon: takes the
    last N failing cases, asks the model to propose 1 added instruction
    to the cross-reference rubric. Production would use DSPy or a
    BootstrapFewShot-style optimizer (plan §10 future work).
    """
    from google import genai
    client = genai.Client(vertexai=True)
    from .prompts import CROSS_REFERENCE_PROMPT
    meta = (
        "You are improving an M&A cross-reference agent's system prompt. "
        "Here is the current prompt followed by recent failure cases. "
        "Propose a REVISED full prompt that addresses the failures. "
        "Output ONLY the revised prompt, no commentary.\n\n"
        "CURRENT:\n" + CROSS_REFERENCE_PROMPT + "\n\n"
        "FAILURES (truncated):\n" + str(failing_examples[:5])
    )
    resp = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview"),
        contents=meta,
    )
    return resp.text or CROSS_REFERENCE_PROMPT


def _upsert_prompt(client, *, name: str, template: str, tag: str) -> str | None:
    """Create a new prompt version under `name`; tag it `tag`. Returns version id.

    Phoenix client API (verified against the installed SDK): `client.prompts.create`
    takes a `version=PromptVersion(...)` payload whose constructor is
    `PromptVersion(prompt=[messages], *, model_name=..., model_provider=...,
    template_format=...)` — NOT a top-level `template=` kwarg (that raises
    `unexpected keyword argument 'template'`). We wrap the raw instruction text
    as a single user message and store it verbatim (`template_format="NONE"`)
    so braces in the prompt aren't parsed as Mustache/f-string slots.
    """
    try:
        from phoenix.client.types import PromptVersion
        version_payload = PromptVersion(
            [{"role": "user", "content": template}],
            model_name=os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview"),
            model_provider="GOOGLE",
            description=f"auto-{tag}",
            template_format="NONE",
        )
        version = client.prompts.create(name=name, version=version_payload)
        version_id = (
            getattr(version, "id", None)
            or getattr(version, "version_id", None)
            or getattr(version, "prompt_version_id", None)
        )
        if version_id:
            client.prompts.tags.create(prompt_version_id=version_id,
                                       name=tag,
                                       description=f"auto-tagged {tag}")
        return version_id
    except Exception as exc:
        _LOG.warning("upsert_prompt failed: %s", exc)
        return None


@functools.lru_cache(maxsize=1)
def _genai_client():
    """Module-level cached google-genai client.

    Python-reviewer minor: previous version constructed a fresh client
    on every example, which on N=30 × 2 tags = 60 instantiations per
    nightly cycle. Cache once.
    """
    from google import genai
    return genai.Client(vertexai=True)


# The structured-RiskFinding fields CROSS_REFERENCE_PROMPT mandates per finding
# ("For each finding, emit: cited_spans / explanation / severity"). The
# deliberately-weakened production prompt has that emit block stripped, so it
# does NOT produce these — that gap is exactly what the coverage metric measures
# (and what faithfulness was blind to).
_COVERAGE_REQUIRED_FIELDS = ("cited_spans", "explanation", "severity")


def _structured_coverage_score(output: str) -> float:
    """Promotion metric (default; toggle via REFLECTOR_SCORE_METRIC): how
    completely `output` conforms to the structured RiskFinding format
    CROSS_REFERENCE_PROMPT mandates (`cited_spans` + `explanation` + `severity`
    per finding).

    Replaces faithfulness, which saturated at 1.0 for BOTH the weak and strong
    prompts (it grades explanation↔clause consistency — blind to the
    coverage/structure axis where the seeded weak↔strong gap actually lives).
    The strong (candidate) prompt genuinely emits these structured fields; the
    weakened (production) prompt emits loose prose. So this measures a REAL
    quality difference, not a thumb on the scale.

    Deterministic (no LLM call) → the experiment stays reproducible (seed=42),
    so a confirmed dry-run reproduces AUTO-PROMOTED on the recorded take.
    Returns 0.0–1.0.
    """
    import json
    import re

    if not output:
        return 0.0
    text = re.sub(r"^```[a-zA-Z]*\s*", "", output.strip())
    text = re.sub(r"\s*```$", "", text).strip()

    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        parsed = [parsed]

    if isinstance(parsed, list) and parsed:
        covs = []
        for item in parsed:
            keys = {str(k).lower() for k in item.keys()} if isinstance(item, dict) else set()
            covs.append(
                sum(1 for f in _COVERAGE_REQUIRED_FIELDS if f in keys)
                / len(_COVERAGE_REQUIRED_FIELDS)
            )
        if covs:
            # 0.5 for valid structured findings + up to 0.5 for required-key coverage.
            return round(0.5 + 0.5 * (sum(covs) / len(covs)), 4)

    # Unstructured (the weak-prose case): a soft, capped field-mention score so
    # deltas stay smooth rather than all-or-nothing — but prose can never reach
    # the structured tier (≤ 0.2).
    low = text.lower()
    mentions = sum(1 for f in _COVERAGE_REQUIRED_FIELDS if f in low)
    return round(0.2 * (mentions / len(_COVERAGE_REQUIRED_FIELDS)), 4)


def _evaluate_one_example(client, example, prompt_template: str) -> float:
    """Run the cross_reference agent on one example and score its output.

    The score is the structured-finding COVERAGE of the agent's output (default;
    see `_structured_coverage_score` / REFLECTOR_SCORE_METRIC) — the axis where
    the seeded weak↔strong prompt gap actually lives. The legacy faithfulness
    metric is still reachable via REFLECTOR_SCORE_METRIC=faithfulness but
    saturates at 1.0 for both prompts, so the gate can never fire on it.
    """
    genai_client = _genai_client()
    # Dataset examples are seeded as {"input": {"clause_text": ...}, ...} (see
    # scripts/seed_reflector_datasets.py). Phoenix passes each example to the
    # task as an ExampleProxy (Mapping with both .get and ["input"]). The v1
    # read `example.get("clause_text") or example.get("input")` yielded the
    # nested INPUT DICT (truthy), so the clause text never reached the model
    # and every score collapsed — zero candidate−production delta.
    def _example_get(ex, key):
        if isinstance(ex, dict) or hasattr(ex, "get"):
            return ex.get(key)
        return getattr(ex, key, None)

    _inp = _example_get(example, "input") or {}
    clause_text = (
        (_inp.get("clause_text") if hasattr(_inp, "get") else None)
        or _example_get(example, "clause_text")
        or ""
    )
    contents = f"{prompt_template}\n\nCLAUSE:\n{clause_text}"
    try:
        # COST: experiment eval runs on Flash — production cross_reference is
        # Flash, so this matches prod AND cuts ~70 Pro calls/iter (€1.5–3 →
        # ~€0.40). Both tags use this same fn, so should_promote's
        # candidate−production delta stays apples-to-apples.
        resp = genai_client.models.generate_content(
            model=os.environ.get("GEMINI_FLASH_MODEL", "gemini-3.5-flash"),
            contents=contents,
        )
        output = (resp.text or "").strip()
    except Exception as exc:
        _LOG.warning("agent call failed in experiment task: %s", exc)
        return 0.0

    metric = os.environ.get("REFLECTOR_SCORE_METRIC", "coverage").strip().lower()
    if metric == "faithfulness":
        # Legacy metric, kept reachable for parity/debug. It saturates at 1.0
        # for BOTH the weak and strong prompts (grades explanation↔clause
        # consistency, blind to coverage/structure), so the promotion gate can
        # never fire on it — which is exactly why "coverage" is the default.
        try:
            from .evaluators import make_faithfulness_classifier

            f_clf = make_faithfulness_classifier()
            scored = f_clf.evaluate({
                "clause_text": clause_text,
                "trigger_language": "",
                "explanation": output,
            })
            return float(scored[0].score)
        except Exception as exc:
            _LOG.warning("faithfulness scoring failed: %s", exc)
            return 0.0
    # Default: structured-finding coverage — the axis where the strong candidate
    # is genuinely better, so the gate can honestly fire (faithfulness couldn't).
    return _structured_coverage_score(output)


def _prompt_template_text(prompt) -> str:
    """Extract the raw template text from a phoenix.client PromptVersion.

    The installed SDK's PromptVersion exposes NO public `.text`/`.template`;
    the message text lives in the private
    `_template["messages"][i]["content"]` (a str, or a list of
    {"type": "text", "text": ...} segments). `.format()` is NOT a usable
    fallback here — it imports the legacy `google.generativeai` lib, which
    is not installed (raises ModuleNotFoundError). The v1 extraction
    `getattr(p, "template", None) or p` then `getattr(.., "text", None) or
    str(p)` silently yielded the object repr `<PromptVersion object at
    0x..>` for BOTH tags, so the experiment scored that 66-char garbage
    instead of the real prompts → no production/candidate delta → the gate
    could never fire. We therefore NEVER fall back to `str(prompt)`.
    """
    t = getattr(prompt, "_template", None)
    if t is None:
        t = getattr(prompt, "template", None)
    if isinstance(t, dict):
        msgs = t.get("messages")
    else:
        msgs = getattr(t, "messages", None)
    parts: list[str] = []
    for m in (msgs or []):
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for seg in content:
                if isinstance(seg, dict):
                    parts.append(seg.get("text", "") or "")
                else:
                    parts.append(getattr(seg, "text", "") or "")
    text = "\n".join(p for p in parts if p)
    if not text:
        # Older SDKs exposed a public `.text`; use it, but NEVER str(prompt)
        # (the useless object repr that caused the original silent failure).
        text = getattr(t, "text", None) or getattr(prompt, "text", None) or ""
    return text


def _run_experiment_pairwise(
    client, *, dataset_name: str, prompt_name: str,
    tags: tuple[str, str],
):
    """Run both prompt tags as separate experiments on the same dataset.

    Returns (cand_scores: np.ndarray, prod_scores: np.ndarray) aligned by
    example index. The task callable loads the prompt by tag and runs the
    real cross_reference agent against the example (Python+Arize
    reviewers flagged the v3 placeholder task that just returned the
    prompt string).

    `run_experiment` results expose evaluator scores as
    `result.runs[i].output` plus annotation rows. We pool the
    faithfulness-evaluator score per example into a numpy array.
    """
    try:
        ds = client.datasets.get_dataset(dataset=dataset_name)
    except Exception as exc:
        _LOG.warning("Could not fetch dataset %s: %s", dataset_name, exc)
        return np.array([]), np.array([])

    def make_task(tag: str):
        def task(example):
            prompt = client.prompts.get(prompt_identifier=prompt_name, tag=tag)
            template_text = _prompt_template_text(prompt)
            if not template_text:
                _LOG.warning(
                    "prompt %s tag=%s: extracted EMPTY template text — "
                    "experiment scores will be meaningless for this tag",
                    prompt_name, tag,
                )
            score = _evaluate_one_example(client, example, template_text)
            return {"output": "", "score": score, "tag": tag}
        return task

    per_tag_scores: dict[str, list[float]] = {tags[0]: [], tags[1]: []}
    for tag in tags:
        try:
            result = client.experiments.run_experiment(
                dataset=ds, task=make_task(tag),
                experiment_name=f"{prompt_name}@{tag}",
            )
            # `run_experiment` returns a `RanExperiment` TypedDict (dict):
            # per-example runs are under the `task_runs` KEY, and each run is
            # an `ExperimentRun` TypedDict whose `output` KEY holds the task's
            # return value `{"output","score","tag"}`. The v1 getattr cascade
            # (`result.runs` / `r.output`) found nothing on a dict → empty
            # scores → `paired_bootstrap_ci_lb([])` = -inf → never promoted.
            if isinstance(result, dict):
                runs = result.get("task_runs") or result.get("runs") or []
            else:
                runs = (
                    getattr(result, "task_runs", None)
                    or getattr(result, "runs", None)
                    or getattr(result, "results", None)
                    or getattr(result, "examples", None)
                    or []
                )
            for r in runs:
                out = (r.get("output") if isinstance(r, dict)
                       else getattr(r, "output", None)) or {}
                if isinstance(out, dict) and "score" in out:
                    per_tag_scores[tag].append(float(out["score"]))
        except Exception as exc:
            _LOG.warning("run_experiment(%s, tag=%s) failed: %s",
                         dataset_name, tag, exc)

    cand = np.array(per_tag_scores[tags[1]])
    prod = np.array(per_tag_scores[tags[0]])
    return cand, prod


def _promote_candidate(client, *, name: str, candidate_version_id: str) -> None:
    try:
        client.prompts.tags.create(
            prompt_version_id=candidate_version_id,
            name="production",
            description="auto-promoted by Reflector",
        )
        _LOG.info("PROMOTED candidate %s → tag=production on %s",
                  candidate_version_id, name)
    except Exception as exc:
        _LOG.warning("promote_candidate failed: %s", exc)


def _backstop_run_evals(client, project_name: str, lookback_hours: int) -> None:
    """Hook 7 — collapsed into the Reflector cron (plan §6.1 v3).

    Bulk-runs hallucination + faithfulness evaluators over the last N
    hours of production spans, writing annotations back. Equivalent
    batch coverage to AX Online Eval Tasks (which are SaaS-only).
    """
    try:
        from .evaluators import (
            make_faithfulness_classifier, make_hallucination_classifier,
        )
        from phoenix.evals import run_evals
        # Pull recent spans as a dataframe for run_evals.
        df = client.spans.get_spans_dataframe(project_name=project_name)
        if df is None or len(df) == 0:
            _LOG.info("Hook 7: no spans in lookback window.")
            return
        run_evals(
            dataframe=df,
            evaluators=[make_hallucination_classifier(),
                        make_faithfulness_classifier()],
        )
    except Exception as exc:
        _LOG.warning("backstop_run_evals failed: %s", exc)


def run_reflection_cycle(
    *,
    project_name: str = "ma-gatekeeper",
    lookback_hours: int = 24,
) -> dict:
    """Pull last-24h failing traces, grow regression dataset, iterate prompt.

    Each step is wrapped so a single failure (e.g., Phoenix MCP timeout)
    does not collapse the whole loop.
    """
    try:
        from phoenix.client import Client
    except Exception as exc:
        return {"error": f"phoenix.client unavailable: {exc}"}

    client = Client()

    # 0. Hook 4 — Phoenix MCP introspection DRIVES regression-set growth.
    # The LlmAgent emits a JSON block of escalation span ids, we parse
    # it, and feed it to `_append_to_dataset`. SDK `_failing_traces` is
    # the documented FALLBACK only (MCP unavailable / output unparseable);
    # an empty parsed list IS honored as a real (successful) result —
    # not a fallback trigger. Frozen fold-5 stays tamper-evident via
    # `assert_writable` regardless of which path produced `failing`.
    failing = _parse_introspection_output(_run_introspection_agent())
    if failing is None:
        _LOG.info("Hook 4: MCP unparseable; SDK fallback.")
        failing = _failing_traces(client, project_name, lookback_hours)
    _append_to_dataset(client, "regressions-v1", failing)

    # 3. Generate candidate prompt and upsert with tag=candidate.
    candidate_template = _generate_candidate_prompt(failing)
    candidate_version = _upsert_prompt(
        client, name="cross_reference",
        template=candidate_template, tag="candidate",
    )

    # 4. Two experiments: regression set + frozen held-out fold 5.
    reg_cand, reg_prod = _run_experiment_pairwise(
        client, dataset_name="regressions-v1",
        prompt_name="cross_reference",
        tags=("production", "candidate"),
    )
    reg_deltas = (reg_cand - reg_prod) if min(len(reg_cand), len(reg_prod)) > 0 \
        else np.array([])

    f5_cand, f5_prod = _run_experiment_pairwise(
        client, dataset_name=_FROZEN_HELD_OUT,
        prompt_name="cross_reference",
        tags=("production", "candidate"),
    )

    # 4b. Third experiment: citation-linkage gold (design/STATUTE_LAYER.md §3.4).
    # Feeds the composite citation gate in should_promote. citation-gold-v1 is
    # frozen (never in _WRITABLE_DATASETS) — read-only ground truth B.
    cit_cand, cit_prod = _run_experiment_pairwise(
        client, dataset_name="citation-gold-v1",
        prompt_name="cross_reference",
        tags=("production", "candidate"),
    )

    # 5. Promotion decision (regression CI + frozen-fold + citation composite).
    promote, diag = should_promote(
        regression_deltas=reg_deltas,
        fold5_candidate_scores=f5_cand,
        fold5_production_scores=f5_prod,
        citation_candidate_scores=cit_cand,
        citation_production_scores=cit_prod,
    )
    if promote and candidate_version:
        _LOG.info("Promotion gates passed: %s", diag)
        _promote_candidate(client, name="cross_reference",
                           candidate_version_id=candidate_version)
    else:
        _LOG.info("Promotion gates blocked: %s", diag)

    # 6. Hook 7 batch eval backstop on production spans.
    _backstop_run_evals(client, project_name, lookback_hours)

    return {"promoted": promote, **diag}


# ---------------------------------------------------------------------------
# MCP introspection output parser (Fix 5).
#
# Defined AFTER `run_reflection_cycle` on purpose: the cycle references
# `_parse_introspection_output` by module-global lookup at call time, so
# definition order doesn't affect runtime; keeping the parser here
# preserves the line numbers of `_promote_candidate` / "PROMOTED"
# log / "Promotion gates passed" log that are cited in demo_script.md
# and pinned by `tests/test_render_climax_plots.py`.
# ---------------------------------------------------------------------------

def _parse_introspection_output(text: str) -> list[dict] | None:
    """Extract the failing-spans list from the introspection agent's JSON output.

    The MCP-mounted LlmAgent is instructed (see `build_introspection_agent`)
    to emit a final message of the shape
        ```json
        {"failing_spans": [{"span_id": "...", ...}, ...]}
        ```
    This parser:
      - Returns the list when a valid JSON block is found (may be empty).
      - Returns `None` when the output is missing, malformed, or doesn't
        contain a `failing_spans` key — that's the sentinel the cycle
        uses to decide whether to fall back to the deterministic SDK
        `_failing_traces` path.

    Empty-list return (`[]`) is distinct from `None`: `[]` means "MCP
    introspected the project and found no escalations" and is honored
    as a real result (no fallback fires); `None` means "MCP didn't
    produce parseable output" and triggers the SDK fallback.
    """
    if not text:
        return None
    import json
    import re

    # Try fenced ```json ... ``` first; then fenced ``` ... ```; then raw.
    candidates: list[str] = []
    fenced_json = re.findall(r"```json\s*(.*?)```", text, re.DOTALL)
    candidates.extend(fenced_json)
    if not candidates:
        fenced = re.findall(r"```\s*(.*?)```", text, re.DOTALL)
        candidates.extend(fenced)
    candidates.append(text)

    for raw in candidates:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            # Try to slice out the first balanced object — agents sometimes
            # prepend a stray sentence even when told not to.
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                try:
                    obj = json.loads(raw[start : end + 1])
                except Exception:
                    continue
            else:
                continue
        if isinstance(obj, dict) and isinstance(obj.get("failing_spans"), list):
            spans = [s for s in obj["failing_spans"] if isinstance(s, dict)]
            return spans
    return None


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print(run_reflection_cycle())
