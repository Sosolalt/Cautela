"""§11 Build #3 + §12 — Reflector LoopAgent unit tests.

Pins:
  1. HARD GATE — Phoenix MCP `list_traces` is called per iteration.
     A cosmetic re-wrap that skips MCP fails this test.
  2. `should_promote` is reused byte-identically from `agent.reflector`
     (asserted by monkeypatching the symbol and verifying call_args).
  3. When no candidate passes the promotion gate, no auto-PR is staged.
  4. When `REFLECTOR_LOOP_AUTO_PR=0` (default), no `gh pr create`
     subprocess fires.
  5. Span-attribute payload coverage — the events carry
     `loop_iteration_count`, `candidates_proposed`, `promotions_applied`,
     `ci_lower_bound`, `fold5_delta` so the parent trace + the frontend
     can render the CI bar without re-deriving the math.
  6. MCP toolset registry has no leaks after the loop completes
     (entry count before == entry count after).
  7. Early-exit when MCP returns zero traces.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import numpy as np
import pytest

from agent import reflector, reflector_loop


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _FakeToolset:
    """Stand-in for the Phoenix MCP toolset. Exposes `list_traces` so
    the loop body's hard-gate site finds it. Also implements `close`
    so the registry-aware cleanup helper considers it idempotent."""

    def __init__(self, traces_per_call: list[list[dict]] | None = None) -> None:
        # `traces_per_call[i]` is what call number i returns. After the
        # list is exhausted, subsequent calls return [].
        self.traces_per_call = traces_per_call or [[
            {"span_id": "sp-1", "clause_text": "escalation case 1"},
            {"span_id": "sp-2", "clause_text": "escalation case 2"},
        ]]
        self.call_args: list[dict] = []
        self.closed = False

    def list_traces(self, *, project_name: str, lookback_hours: int):
        self.call_args.append({
            "project_name": project_name,
            "lookback_hours": lookback_hours,
        })
        if not self.traces_per_call:
            return []
        return self.traces_per_call.pop(0)

    async def close(self):  # idempotent per `_aclose_one_with_timeout`
        self.closed = True


def _reset_registry():
    with reflector._mcp_toolset_registry_lock:
        reflector._mcp_toolset_registry.clear()


def _drain(gen) -> list:
    """Drive an async generator from a sync test and collect its yields."""
    async def _run():
        out = []
        async for x in gen:
            out.append(x)
        return out

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Hard-gate test #1 — Phoenix MCP `list_traces` is called per iteration.
# ---------------------------------------------------------------------------


def test_loop_body_calls_mcp_list_traces_per_iteration(monkeypatch):
    """HARD GATE (POST_HACKATHON_BACKLOG §11 Build #3): the loop body
    MUST issue an MCP `list_traces` call per iteration. A cosmetic
    re-wrap that skips MCP fails this assertion.

    Configure the experiment + should_promote stubs to deny promotion
    every iteration so the loop runs to `max_iterations` and we can
    count the MCP calls. Default `max_iterations` is 3.
    """
    _reset_registry()
    toolset = _FakeToolset(traces_per_call=[
        [{"span_id": f"sp-{i}", "clause_text": "x"}]
        for i in range(5)
    ])
    # No promotion ever — should_promote returns False
    monkeypatch.setattr(
        reflector_loop, "should_promote",
        lambda **kw: (False, {
            "regression_ci_lb": -0.01, "epsilon_fold5": 0.03,
            "fold5_candidate_mean": 0.5, "fold5_production_mean": 0.5,
            "fold5_non_regression_ok": 1.0, "regression_gate_ok": 0.0,
        }),
    )
    monkeypatch.setattr(
        reflector_loop, "_run_experiment_for_loop",
        lambda *a, **kw: (np.array([0.5]), np.array([0.5])),
    )

    events = _drain(reflector_loop.run_reflector_loop(
        deal_id="microsoft_activision",
        max_iterations=3,
        toolset_factory=lambda: toolset,
        phoenix_client_factory=lambda: object(),
    ))

    # Exactly one MCP call per iteration.
    assert len(toolset.call_args) == 3, (
        f"HARD GATE failed: expected 3 list_traces calls (one per "
        f"iteration); got {len(toolset.call_args)}. The LoopAgent body "
        f"must invoke Phoenix MCP `list_traces` every iteration — "
        f"without that recursion, this build is cosmetic."
    )
    # Each call passes the project_name + lookback_hours kwargs.
    for call in toolset.call_args:
        assert call["project_name"] == "ma-gatekeeper"
        assert call["lookback_hours"] == 24
    # And an `mcp_traces_listed` event is emitted per iteration.
    mcp_events = [e for e in events if e.kind == "mcp_traces_listed"]
    assert len(mcp_events) == 3


# ---------------------------------------------------------------------------
# Hard-gate test #2 — should_promote is reused, not re-implemented.
# ---------------------------------------------------------------------------


def test_promotion_math_reuses_should_promote_via_symbol(monkeypatch):
    """The promotion gate MUST call `reflector.should_promote` (not a
    re-implementation). Pin this by replacing the symbol with a spy.

    Also assert the kwargs come through verbatim — kwarg drift across a
    refactor (`fold5_candidate` vs `fold5_candidate_scores`) silently
    breaks the gate.
    """
    _reset_registry()
    toolset = _FakeToolset()
    spy_calls: list[dict] = []

    def spy_should_promote(**kwargs):
        spy_calls.append({
            k: (v.tolist() if hasattr(v, "tolist") else v)
            for k, v in kwargs.items()
        })
        return False, {
            "regression_ci_lb": 0.0, "epsilon_fold5": 0.03,
            "fold5_candidate_mean": 0.5, "fold5_production_mean": 0.5,
            "fold5_non_regression_ok": 1.0, "regression_gate_ok": 0.0,
        }

    monkeypatch.setattr(reflector_loop, "should_promote", spy_should_promote)
    monkeypatch.setattr(
        reflector_loop, "_run_experiment_for_loop",
        lambda *a, **kw: (np.array([0.5, 0.5]), np.array([0.45, 0.55])),
    )
    _drain(reflector_loop.run_reflector_loop(
        max_iterations=1,
        toolset_factory=lambda: toolset,
        phoenix_client_factory=lambda: object(),
    ))

    assert len(spy_calls) == 1, "should_promote must be called exactly once per iteration"
    kwargs = spy_calls[0]
    # Exact kwarg names — drift catch.
    assert set(kwargs) == {
        "regression_deltas",
        "fold5_candidate_scores",
        "fold5_production_scores",
    }


# ---------------------------------------------------------------------------
# Hard-gate test #3 — no candidate passes → no auto-PR.
# ---------------------------------------------------------------------------


def test_no_promotion_means_no_auto_pr(monkeypatch):
    """When `should_promote` returns False, the loop must NOT call
    `_stage_auto_pr`. The frontend's `auto_promoted` event also must
    NOT appear; the terminal event is `no_promotion`.
    """
    _reset_registry()
    toolset = _FakeToolset()
    stage_calls: list = []
    monkeypatch.setattr(
        reflector_loop, "_stage_auto_pr",
        lambda **kw: (stage_calls.append(kw), (None, ""))[1],
    )
    monkeypatch.setattr(
        reflector_loop, "should_promote",
        lambda **kw: (False, {
            "regression_ci_lb": -0.02, "epsilon_fold5": 0.03,
            "fold5_candidate_mean": 0.5, "fold5_production_mean": 0.52,
            "fold5_non_regression_ok": 0.0, "regression_gate_ok": 0.0,
        }),
    )
    monkeypatch.setattr(
        reflector_loop, "_run_experiment_for_loop",
        lambda *a, **kw: (np.array([0.5]), np.array([0.5])),
    )

    events = _drain(reflector_loop.run_reflector_loop(
        max_iterations=2,
        toolset_factory=lambda: toolset,
        phoenix_client_factory=lambda: object(),
    ))

    assert stage_calls == [], (
        f"_stage_auto_pr must not run when no candidate passes; "
        f"got {len(stage_calls)} call(s)"
    )
    kinds = [e.kind for e in events]
    assert "auto_promoted" not in kinds
    assert kinds[-1] == "no_promotion"


# ---------------------------------------------------------------------------
# Hard-gate test #4 — env flag OFF means no `gh pr create` subprocess.
# ---------------------------------------------------------------------------


def test_auto_pr_env_off_no_gh_subprocess(monkeypatch):
    """`REFLECTOR_LOOP_AUTO_PR` unset (or != "1") must short-circuit
    `_stage_auto_pr` BEFORE subprocess.run is invoked. We assert this
    by patching subprocess.run and confirming it was NOT called.
    """
    monkeypatch.delenv("REFLECTOR_LOOP_AUTO_PR", raising=False)
    subprocess_calls: list = []
    monkeypatch.setattr(
        reflector_loop.subprocess, "run",
        lambda *a, **kw: subprocess_calls.append((a, kw)) or MagicMock(),
    )
    # Drive _stage_auto_pr directly — it's the gate site.
    pr_url, diff = reflector_loop._stage_auto_pr(
        candidate_template="CAND",
        diag={"regression_ci_lb": 0.05},
        deal_id="microsoft_activision",
    )
    assert pr_url is None
    assert "auto-promoted by Reflector LoopAgent" in diff
    assert subprocess_calls == [], (
        f"REFLECTOR_LOOP_AUTO_PR=0 must skip the subprocess; got "
        f"{len(subprocess_calls)} call(s)"
    )


def test_auto_pr_env_on_invokes_gh_subprocess(monkeypatch):
    """Companion: when the env flag is set, subprocess.run IS called
    with the correct argv shape. Pins the gh wiring contract."""
    monkeypatch.setenv("REFLECTOR_LOOP_AUTO_PR", "1")
    subprocess_calls: list = []

    def fake_run(argv, *, capture_output, text, timeout):
        subprocess_calls.append({"argv": argv, "timeout": timeout})
        return MagicMock(
            returncode=0,
            stdout="https://github.com/example/repo/pull/1234\n",
            stderr="",
        )

    monkeypatch.setattr(reflector_loop.subprocess, "run", fake_run)
    pr_url, _diff = reflector_loop._stage_auto_pr(
        candidate_template="CAND",
        diag={"regression_ci_lb": 0.05},
        deal_id="microsoft_activision",
    )
    assert pr_url == "https://github.com/example/repo/pull/1234"
    assert len(subprocess_calls) == 1
    argv = subprocess_calls[0]["argv"]
    assert argv[:3] == ["gh", "pr", "create"]
    # Subprocess timeout MUST be present and bounded — open-ended gh
    # subprocess would hang the demo path on a misconfigured CLI.
    assert subprocess_calls[0]["timeout"] <= 10


# ---------------------------------------------------------------------------
# Hard-gate test #5 — span-attribute coverage on events.
# ---------------------------------------------------------------------------


def test_events_carry_required_payload_fields(monkeypatch):
    """The streamed events must carry the field set the frontend +
    OpenTelemetry parent span depend on:
      - `iteration` (every per-iteration event)
      - `mcp_traces_listed.payload.trace_count`
      - `frozen_fold_check.payload.{ci_lower_bound, fold5_delta,
                                    epsilon_fold5}`
      - `auto_promoted.payload.{ci_lower_bound, fold5_delta,
                                epsilon_fold5, prompt_version}`
    """
    _reset_registry()
    toolset = _FakeToolset()
    # Force promotion on iter 1.
    monkeypatch.setattr(
        reflector_loop, "should_promote",
        lambda **kw: (True, {
            "regression_ci_lb": 0.042, "epsilon_fold5": 0.03,
            "fold5_candidate_mean": 0.71, "fold5_production_mean": 0.69,
            "fold5_non_regression_ok": 1.0, "regression_gate_ok": 1.0,
        }),
    )
    monkeypatch.setattr(
        reflector_loop, "_run_experiment_for_loop",
        lambda *a, **kw: (np.array([0.71, 0.72]), np.array([0.69, 0.68])),
    )
    monkeypatch.delenv("REFLECTOR_LOOP_AUTO_PR", raising=False)

    events = _drain(reflector_loop.run_reflector_loop(
        max_iterations=2,
        toolset_factory=lambda: toolset,
        phoenix_client_factory=lambda: object(),
    ))

    kinds = [e.kind for e in events]
    assert "auto_promoted" in kinds

    # Every per-iteration event must carry iteration >= 1.
    for e in events:
        if e.kind in {
            "iteration_started", "mcp_traces_listed", "candidate_generated",
            "experiment_complete", "frozen_fold_check", "iteration_complete",
            "auto_promoted",
        }:
            if e.iteration is not None:
                assert e.iteration >= 1, f"{e.kind} iteration must be 1-indexed"

    mcp = next(e for e in events if e.kind == "mcp_traces_listed")
    assert "trace_count" in mcp.payload

    ff = next(e for e in events if e.kind == "frozen_fold_check")
    for k in ("ci_lower_bound", "fold5_delta", "epsilon_fold5"):
        assert k in ff.payload, f"frozen_fold_check missing {k}"

    promo = next(e for e in events if e.kind == "auto_promoted")
    for k in ("ci_lower_bound", "fold5_delta", "epsilon_fold5", "prompt_version"):
        assert k in promo.payload, f"auto_promoted missing {k}"

    # Build a `ReflectorLoopReport` and verify it carries the same fields.
    report = reflector_loop.build_report_from_events(events, iteration_count=1)
    assert report.promoted is True
    assert report.candidates_proposed == 1
    assert report.promotions_applied == 1
    assert report.ci_lower_bound == pytest.approx(0.042)


# ---------------------------------------------------------------------------
# Hard-gate test #6 — registry has no leaks after the loop completes.
# ---------------------------------------------------------------------------


def test_mcp_toolset_registry_no_leaks_after_loop(monkeypatch):
    """One toolset constructed per loop run, reused across iterations,
    and explicitly closed + unregistered in the run's finally block.
    Registry size before == size after.
    """
    _reset_registry()
    monkeypatch.setattr(
        reflector_loop, "should_promote",
        lambda **kw: (False, {
            "regression_ci_lb": 0.0, "epsilon_fold5": 0.03,
            "fold5_candidate_mean": 0.5, "fold5_production_mean": 0.5,
            "fold5_non_regression_ok": 1.0, "regression_gate_ok": 0.0,
        }),
    )
    monkeypatch.setattr(
        reflector_loop, "_run_experiment_for_loop",
        lambda *a, **kw: (np.array([0.5]), np.array([0.5])),
    )

    # Make a toolset and register it explicitly so we can prove the
    # post-run unregister works.
    toolset = _FakeToolset()
    reflector._register_toolset(toolset)
    before = len(reflector._mcp_toolset_registry)

    _drain(reflector_loop.run_reflector_loop(
        max_iterations=2,
        toolset_factory=lambda: toolset,
        phoenix_client_factory=lambda: object(),
    ))

    after = len(reflector._mcp_toolset_registry)
    assert after == before - 1, (
        f"registry leak: before={before}, after={after}. "
        f"Expected the loop's finally to drop the toolset entry."
    )
    assert toolset.closed is True


# ---------------------------------------------------------------------------
# Hard-gate test #7 — early-exit when MCP returns zero traces.
# ---------------------------------------------------------------------------


def test_loop_early_exits_when_mcp_returns_zero_traces(monkeypatch):
    """If MCP returns an empty list on iteration 1, the loop should NOT
    advance to candidate generation — there is nothing to learn from.
    The iteration completes with `outcome=no_traces` and the loop
    terminates with `no_promotion`.
    """
    _reset_registry()
    empty_toolset = _FakeToolset(traces_per_call=[[]])
    # If the loop bug-erroneously advances, these stubs would fire —
    # we assert below that they do NOT.
    candidate_calls: list = []
    monkeypatch.setattr(
        reflector_loop, "_generate_candidate_prompt_for_loop",
        lambda traces: (candidate_calls.append(traces), "UNREACHABLE")[1],
    )

    events = _drain(reflector_loop.run_reflector_loop(
        max_iterations=3,
        toolset_factory=lambda: empty_toolset,
        phoenix_client_factory=lambda: object(),
    ))
    # MCP still called (the hard gate fires).
    assert len(empty_toolset.call_args) == 1
    # But no candidate generation — early-exit fired.
    assert candidate_calls == [], (
        f"expected zero candidate-gen calls on empty MCP result; "
        f"got {len(candidate_calls)}"
    )
    kinds = [e.kind for e in events]
    iter_complete = next(e for e in events if e.kind == "iteration_complete")
    assert iter_complete.payload.get("outcome") == "no_traces"
    assert kinds[-1] == "no_promotion"


# ---------------------------------------------------------------------------
# Locked-surface verification — reflector.py top-level symbols intact.
# ---------------------------------------------------------------------------


def test_reflector_locked_surface_unchanged():
    """Defensive: the dispatch spec marks `reflector.py` as MUST NOT
    TOUCH (additive only). Pin the public symbols our loop module
    depends on so a future refactor that renames/removes them fails
    here BEFORE it breaks the loop silently.
    """
    for name in (
        "should_promote",
        "make_phoenix_mcp_toolset",
        "_run_experiment_pairwise",
        "_aclose_one_with_timeout",
        "_unregister_toolset",
        "_register_toolset",
        "_mcp_toolset_registry",
        "_mcp_toolset_registry_lock",
        "_FROZEN_HELD_OUT",
    ):
        assert hasattr(reflector, name), (
            f"reflector.{name} disappeared — reflector_loop depends on it"
        )


def test_should_promote_signature_unchanged():
    """The dispatch spec calls `should_promote` "byte-for-byte". Pin
    the kwarg signature so a future change to the parameter names of
    `reflector.should_promote` fails here (and our test #2 above is the
    behavior counterpart).

    The citation-linkage layer (STATUTE_LAYER.md §3.4) added two OPTIONAL
    keyword-only params with defaults — backward compatible: every existing
    call site that passes only the original three still works unchanged.
    """
    import inspect

    sig = inspect.signature(reflector.should_promote)
    params = list(sig.parameters)
    # The original three remain, in order, as the leading params.
    assert params[:3] == [
        "regression_deltas",
        "fold5_candidate_scores",
        "fold5_production_scores",
    ]
    # The composite citation gate adds exactly these two optional params.
    assert params == [
        "regression_deltas",
        "fold5_candidate_scores",
        "fold5_production_scores",
        "citation_candidate_scores",
        "citation_production_scores",
    ]
    # All params are keyword-only. A regression that makes them positional
    # would break our call-site; the two new ones must also have defaults.
    for name, param in sig.parameters.items():
        assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
            f"{name} must remain keyword-only"
        )
    assert sig.parameters["citation_candidate_scores"].default is None
    assert sig.parameters["citation_production_scores"].default is None
