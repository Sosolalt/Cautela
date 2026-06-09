"""Reflector self-improvement loop (plan §6.3, statistically-honest).

Single ADK agent process that holds:
  - Phoenix MCP tools via google.adk.tools.mcp_tool.MCPToolset (for the
    "agent inspects its own traces" beat in the demo). The MCPToolset is
    built by `make_phoenix_mcp_toolset()` and mounted on the introspection
    sub-agent at construction time.
  - phoenix.client.Client() for deterministic SDK steps (datasets,
    experiments, prompts).

Verified Phoenix client API (Arize-reviewer + live docs):
  - client.datasets.get_dataset(name=...) returns a Dataset object.
  - client.datasets.append_examples(dataset=Dataset, examples=...)
  - client.prompts.get(prompt_identifier=, tag=)
  - client.prompts.create(name=, version=...)  (NOT upsert)
  - client.prompts.tags.create(prompt_version_id=, name=, description=)
                                                    (NOT add_version_tag)
  - client.experiments.run_experiment(dataset, task, evaluators=None, ...)
    where `dataset` is a Dataset object.

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


def make_phoenix_mcp_toolset():
    """Hook 4 — real MCPToolset wiring around the @arizeai/phoenix-mcp server.

    Mounted on the Reflector's introspection sub-agent so the LLM can call
    `list-traces`, `get-trace`, `get-span-annotations`, etc. directly. The
    deterministic SDK calls (datasets/experiments/prompts) continue to use
    phoenix.client; MCP is for the agent-driven introspection beat in the
    demo.

    Returns an MCPToolset, or None if the MCP integration packages are
    not installed in this environment.
    """
    try:
        # `StdioServerParameters` is exported from the upstream `mcp` package,
        # NOT from `google.adk.tools.mcp_tool` (R6 WebFetch-verified against
        # https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/tools/mcp_tool/__init__.py).
        # Importing it from ADK previously worked only via test-suite
        # stubbing; on a clean install with the real packages it raised
        # ImportError at runtime — silently swallowed by the broad except
        # below, which is exactly the "Hook 4 quietly dead" failure mode
        # Phase 5 was trying to close.
        from google.adk.tools.mcp_tool import MCPToolset
        from mcp import StdioServerParameters
    except Exception as exc:
        _LOG.warning("MCPToolset unavailable: %s", exc)
        return None
    base_url = os.environ.get("PHOENIX_MCP_BASE_URL", "")
    api_key = os.environ.get("PHOENIX_MCP_API_KEY", "")
    if not base_url or not api_key:
        _LOG.info(
            "Phoenix MCP base URL or API key unset; Hook 4 will run in "
            "no-op mode until env is configured."
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


def build_introspection_agent():
    """LlmAgent that calls Phoenix MCP tools to inspect its own traces.

    Invoked at the START of run_reflection_cycle so the chosen failing
    traces include the agent's own recent reasoning. This is the
    "meta-agentic observability" beat the Arize-track judges look for.
    """
    toolset = make_phoenix_mcp_toolset()
    if toolset is None:
        return None
    try:
        from google.adk.agents import LlmAgent
    except Exception:
        return None
    return LlmAgent(
        name="reflector_introspector",
        model=os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview"),
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

    Important (Python-reviewer fix): we filter BEFORE returning. The
    previous version returned every span which polluted `regressions-v1`
    with successes — defeating the whole "regression dataset of failures"
    purpose.
    """
    try:
        spans = client.spans.get_spans_dataframe(project_name=project_name)
        if spans is None or len(spans) == 0:
            return []
        # The annotation name `risk_judge_gate` carries the lane label
        # (router.py writes it). Filter to escalations only; auto_clear
        # and block ARE NOT failures (block is a deliberate hard-stop).
        # The annotation column name from get_spans_dataframe depends on
        # phoenix.client version; try both standard shapes.
        cand_cols = [
            "annotation.risk_judge_gate.label",
            "annotations.risk_judge_gate.label",
            "risk_judge_gate.label",
        ]
        col = next((c for c in cand_cols if c in spans.columns), None)
        if col is None:
            _LOG.warning(
                "risk_judge_gate annotation column not found; columns=%s",
                list(spans.columns)[:30],
            )
            return []
        failing = spans[spans[col] == "escalate"]
        return failing.to_dict(orient="records")
    except Exception as exc:
        _LOG.warning("Failed to pull traces: %s", exc)
        return []


def _append_to_dataset(client, dataset_name: str, examples: Sequence[dict]) -> None:
    assert_writable(dataset_name)
    if not examples:
        return
    try:
        ds = client.datasets.get_dataset(name=dataset_name)
        client.datasets.append_examples(dataset=ds, examples=list(examples))
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
        model=os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview"),
        contents=meta,
    )
    return resp.text or CROSS_REFERENCE_PROMPT


def _upsert_prompt(client, *, name: str, template: str, tag: str) -> str | None:
    """Create a new prompt version under `name`; tag it `tag`. Returns version id.

    Phoenix client API (verified): `client.prompts.create(...)` takes a
    `version` argument that is a `PromptVersion` payload, NOT a top-level
    `template=` kwarg. We build the PromptVersion with the helper, fall
    back to passing the template directly if the SDK version accepts the
    simpler form.
    """
    try:
        version_payload = None
        try:
            from phoenix.client.types import PromptVersion
            version_payload = PromptVersion(template=template,
                                            description=f"auto-{tag}")
        except Exception:
            pass
        if version_payload is not None:
            version = client.prompts.create(name=name, version=version_payload)
        else:
            # Older SDK accepted the flatter form; try as a fallback.
            version = client.prompts.create(name=name, template=template,
                                            prompt_description=f"auto-{tag}")
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


def _evaluate_one_example(client, example, prompt_template: str) -> float:
    """Run the cross_reference agent on one example and score with the
    faithfulness evaluator.

    This replaces the v3-B placeholder task that just returned the
    truncated prompt string. The score is the FAITHFULNESS evaluator's
    score on the agent's output against the example's clause text —
    that's what we expect a "better" prompt to improve.
    """
    from .evaluators import make_faithfulness_classifier

    genai_client = _genai_client()
    clause_text = example.get("clause_text") or example.get("input") or ""
    contents = f"{prompt_template}\n\nCLAUSE:\n{clause_text}"
    try:
        resp = genai_client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview"),
            contents=contents,
        )
        output = (resp.text or "").strip()
    except Exception as exc:
        _LOG.warning("agent call failed in experiment task: %s", exc)
        return 0.0

    try:
        f_clf = make_faithfulness_classifier()
        scored = f_clf.evaluate({"clause_text": clause_text, "tag": output[:200]})
        return float(scored[0].score)
    except Exception as exc:
        _LOG.warning("faithfulness scoring failed: %s", exc)
        return 0.0


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
        ds = client.datasets.get_dataset(name=dataset_name)
    except Exception as exc:
        _LOG.warning("Could not fetch dataset %s: %s", dataset_name, exc)
        return np.array([]), np.array([])

    def make_task(tag: str):
        def task(example):
            prompt = client.prompts.get(prompt_identifier=prompt_name, tag=tag)
            tmpl_obj = getattr(prompt, "template", None) or prompt
            template_text = getattr(tmpl_obj, "text", None) or str(tmpl_obj)
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
            # Phoenix Experiment result exposes per-example runs; the
            # exact attr varies (`.runs`, `.results`, `.examples`). Try a
            # cascade.
            runs = (
                getattr(result, "runs", None)
                or getattr(result, "results", None)
                or getattr(result, "examples", None)
                or []
            )
            for r in runs:
                out = getattr(r, "output", None) or {}
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
