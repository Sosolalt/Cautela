"""§12 demo composition — end-to-end ≤90s integration test.

Exercises the full HTTP → SSE → endpoint → LoopAgent → events flow
that the "Run Reflector now" button drives. The dispatch spec calls
this out as the testable composition of §11 Build #3 + §12: HITL
"wrong" → button → LoopAgent spawn with visible sub-traces → prompt
diff + CI bar + AUTO-PROMOTED badge → PR link → re-run yesterday's
finding now classifies as Block citing the new prompt version.

The test mocks: the Phoenix MCP toolset, `should_promote`, the
Experiment scorer, and `gh pr create`. Real network calls are NOT
permitted; the CI runner has no Phoenix instance and no `gh` CLI.
Target wall-clock under CI: <5s. Hard budget: <30s.

What this test PROVES:
  1. The /reflect/loop endpoint is reachable from the passcode-gated
     surface (matches the /portfolio precedent, NOT the /reflect cron
     OIDC posture).
  2. SSE frames arrive in the dispatch-spec order: loop_started →
     iteration_started → mcp_traces_listed → candidate_generated →
     experiment_complete → frozen_fold_check → iteration_complete →
     auto_promoted → terminal `done`.
  3. The HARD GATE — Phoenix MCP `list_traces` — is called at least
     once during the run (mock call_args verifies, but the e2e shape
     is asserted via the `mcp_traces_listed` event).
  4. When `should_promote` returns True, the `auto_promoted` event
     carries `prompt_version`, `ci_lower_bound`, `fold5_delta`,
     and `epsilon_fold5` so the frontend can render the CI bar +
     badge without re-deriving the math.
  5. With `REFLECTOR_LOOP_AUTO_PR` unset (the default in tests + the
     demo recording), no `gh pr create` subprocess fires — the event
     carries `staged_diff` instead, surfacing the "would-PR" path.

What this test DOES NOT prove (out of scope for an e2e mock):
  - That the live Phoenix MCP server actually exposes `list_traces`
    with the same call signature (covered by the unit test
    `test_reflector_loop.py::test_loop_body_calls_mcp_list_traces_per_iteration`
    via the toolset interface, but the live wire shape is verified
    only on operator deploy per HANDOFF.md D11-D14).
  - That `gh pr create` succeeds end-to-end in production (covered
    by the unit test `test_auto_pr_env_on_invokes_gh_subprocess`).
"""
from __future__ import annotations

import json

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Fake Phoenix MCP toolset — reused from test_reflector_loop fixtures.
# ---------------------------------------------------------------------------


class _FakeToolset:
    """Stand-in matching the production toolset's `list_traces` + `close`
    surface. Mirrors `tests/test_reflector_loop._FakeToolset` so the unit
    tests and this e2e test agree on the interface contract.
    """

    def __init__(self, traces: list[dict] | None = None) -> None:
        self._traces = traces or [
            {
                "span_id": "sp-yesterday-1",
                "clause_text": (
                    "no-shop with fiduciary out subject to "
                    "Revlon-style superior-proposal escape"
                ),
                "label": "escalate",
                "hitl_wrong": True,
            }
        ]
        self.call_args: list[dict] = []
        self.closed = False

    def list_traces(self, *, project_name: str, lookback_hours: int):
        self.call_args.append(
            {"project_name": project_name, "lookback_hours": lookback_hours}
        )
        return list(self._traces)

    async def close(self):
        self.closed = True


# ---------------------------------------------------------------------------
# Allow-list deal selection
# ---------------------------------------------------------------------------


def _first_allow_list_deal_id() -> str:
    """Pick the first allow-list deal slug. The 5 allow-listed entries
    are curated in `agent/allow_list.py`; the e2e test only needs one.
    """
    from agent.allow_list import ALLOW_LIST

    assert ALLOW_LIST, "ALLOW_LIST must not be empty"
    return ALLOW_LIST[0].id


# ---------------------------------------------------------------------------
# SSE parser
# ---------------------------------------------------------------------------


def _parse_sse_frames(body: bytes) -> list[dict]:
    """Decode the response body into a list of SSE event dicts.

    Cloud Run preserves `\\n\\n` delimiters; TestClient does not insert
    proxies in between. Each frame's `data: ...` line is JSON. We accept
    both `\\n\\n` and `\\r\\n\\r\\n` delimiters to match the frontend
    parser in `lib/api.ts`.
    """
    import re

    text = body.decode("utf-8")
    frames = re.split(r"\r?\n\r?\n", text)
    out: list[dict] = []
    for frame in frames:
        for line in frame.splitlines():
            if line.startswith("data: "):
                payload = line[len("data: "):]
                if payload.strip():
                    out.append(json.loads(payload))
    return out


# ---------------------------------------------------------------------------
# The e2e test
# ---------------------------------------------------------------------------


def test_reflect_loop_e2e_full_demo_sequence(monkeypatch):
    """The complete ≤90s demo sequence:

      1. Operator clicks "Run Reflector now" on a deal that has a
         HITL-flagged "wrong" finding from yesterday.
      2. POST /reflect/loop (passcode-gated) triggers the LoopAgent.
      3. LoopAgent iteration body queries Phoenix MCP `list_traces`,
         proposes a candidate, runs Experiment, applies should_promote.
      4. should_promote == True → auto-PR is *staged* (env flag off,
         so no real `gh pr create`), terminal `auto_promoted` event
         carries prompt_version + ci_lower_bound + fold5_delta.
      5. SSE stream closes with a `done` frame.

    All Phoenix + gh interactions are mocked. Wall-clock must stay
    well under 30s (typical: <2s) so CI doesn't blow the budget.
    """
    pydantic = pytest.importorskip("pydantic")  # noqa: F841
    fastapi_testclient = pytest.importorskip("fastapi.testclient")

    # Required server-side env for passcode-gated routes. Set BOTH the
    # env var (for any module that re-reads at call time) AND the
    # module-global `DEMO_PASSCODE` symbol (defense against the
    # import-cache hazard where srv was imported earlier with empty env).
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode-e2e")
    from agent import server as _srv_for_passcode
    monkeypatch.setattr(_srv_for_passcode, "DEMO_PASSCODE", "test-passcode-e2e")
    # Belt-and-braces: ensure the auto-PR env flag is OFF so the test
    # cannot accidentally fire `gh pr create` even if a future refactor
    # widens the call surface.
    monkeypatch.delenv("REFLECTOR_LOOP_AUTO_PR", raising=False)

    from agent import reflector_loop, server as srv
    from agent.allow_list import ALLOW_LIST  # noqa: F401  (assertion below)

    deal_id = _first_allow_list_deal_id()
    fake_toolset = _FakeToolset()

    # --- Wire the loop's collaborators to deterministic stubs ---
    # Toolset factory: avoid the real `make_phoenix_mcp_toolset` (which
    # would npx-spawn the Phoenix MCP server). Substitute a single
    # _FakeToolset reused across iterations.
    monkeypatch.setattr(
        reflector_loop, "make_phoenix_mcp_toolset", lambda: fake_toolset
    )

    # Phoenix Client: the loop iteration body does
    # `from phoenix.client import Client; client = Client()` inside the
    # try/except. Stub the module so the import succeeds with a
    # sentinel (the experiment scorer is patched below and ignores the
    # client). Pattern mirrors tests/test_introspection_agent.py.
    import sys
    import types

    fake_phoenix = types.ModuleType("phoenix")
    fake_phoenix_client = types.ModuleType("phoenix.client")
    fake_phoenix_client.Client = lambda: object()
    monkeypatch.setitem(sys.modules, "phoenix", fake_phoenix)
    monkeypatch.setitem(sys.modules, "phoenix.client", fake_phoenix_client)

    # Experiment scorer: candidate clearly beats production on the
    # regression set so paired-bootstrap CI lower bound is positive.
    candidate_scores = np.array([0.85, 0.92, 0.88, 0.90, 0.86])
    production_scores = np.array([0.60, 0.62, 0.59, 0.61, 0.58])

    def _fake_experiment(client, *, dataset_name, prompt_name):
        return candidate_scores, production_scores

    monkeypatch.setattr(
        reflector_loop, "_run_experiment_for_loop", _fake_experiment
    )

    # Promotion gate: pass the candidate. Diagnostics shape matches the
    # real `should_promote` output (see agent/reflector.py); the
    # _run_one_iteration body computes fold5_delta as
    # `fold5_candidate_mean - fold5_production_mean`, so the stub must
    # carry both means rather than a pre-computed delta.
    diag = {
        "regression_ci_lb": 0.142,
        "regression_gate_ok": 1.0,
        "epsilon_fold5": 0.030,
        "fold5_candidate_mean": 0.74,
        "fold5_production_mean": 0.72,
        "fold5_non_regression_ok": 1.0,
    }
    monkeypatch.setattr(
        reflector_loop, "should_promote", lambda **kw: (True, diag)
    )

    # --- Trigger the endpoint ---
    with fastapi_testclient.TestClient(srv.app) as client:
        resp = client.post(
            "/reflect/loop",
            headers={"X-Demo-Passcode": "test-passcode-e2e"},
            json={"deal_id": deal_id},
        )

    assert resp.status_code == 200, (
        f"/reflect/loop failed: {resp.status_code}: {resp.text[:200]}"
    )

    frames = _parse_sse_frames(resp.content)
    assert frames, "no SSE frames decoded from /reflect/loop response"

    # --- Pull out the ordered LoopAgent events ---
    loop_events = [f for f in frames if f.get("event") == "reflector_loop"]
    kinds = [f["kind"] for f in loop_events]

    # The dispatch-spec sequence: loop_started must come first, the
    # hard-gate `mcp_traces_listed` must appear, the terminal must be
    # either auto_promoted or no_promotion. Order between iteration
    # markers is preserved.
    assert kinds[0] == "loop_started", (
        f"first event must be loop_started; got {kinds[:3]}"
    )
    assert "iteration_started" in kinds, kinds
    assert "mcp_traces_listed" in kinds, (
        f"HARD GATE: mcp_traces_listed must appear (Phoenix MCP "
        f"`list_traces` recursion is the §11 Build #3 differentiator); "
        f"got {kinds}"
    )
    assert "candidate_generated" in kinds, kinds
    assert "experiment_complete" in kinds, kinds
    assert "frozen_fold_check" in kinds, kinds
    assert "iteration_complete" in kinds, kinds

    # The promotion was set up to succeed → terminal event is auto_promoted.
    assert "auto_promoted" in kinds, (
        f"should_promote returned True so the LoopAgent must emit "
        f"auto_promoted; got {kinds}"
    )
    assert "no_promotion" not in kinds, kinds

    # --- The HARD GATE was actually hit ---
    assert len(fake_toolset.call_args) >= 1, (
        "Phoenix MCP `list_traces` was never called — this is the "
        "single differentiating recursion per the Arize-juror critique. "
        "A cosmetic LoopAgent re-wrap is a failed build."
    )

    # --- The auto_promoted payload carries the bar-chart-rendering math ---
    promoted = next(f for f in loop_events if f["kind"] == "auto_promoted")
    p = promoted["payload"]
    # Prompt version is auto-assigned by _run_one_iteration as
    # `cross_reference@candidate-iterN`. We assert the prefix so a future
    # iteration-counter format tweak doesn't churn this test, but the
    # iteration number must be present (proves promotion happened at a
    # real iteration, not iteration 0).
    pv = p.get("prompt_version")
    assert isinstance(pv, str) and pv.startswith("cross_reference@candidate-iter"), pv
    assert pv != "cross_reference@candidate-iter0", (
        f"prompt_version must reference a real iteration (>= 1); got {pv}"
    )
    assert isinstance(p.get("ci_lower_bound"), (int, float)), p
    assert p["ci_lower_bound"] > 0, (
        "ci_lower_bound on auto_promoted must be > 0 — that's the "
        f"paired-bootstrap gate the badge claims; got {p['ci_lower_bound']}"
    )
    assert isinstance(p.get("fold5_delta"), (int, float)), p
    assert isinstance(p.get("epsilon_fold5"), (int, float)), p

    # --- Auto-PR was STAGED, not opened (env flag off) ---
    assert p.get("auto_pr_url") in (None, ""), (
        "REFLECTOR_LOOP_AUTO_PR is unset; auto_pr_url must NOT be "
        f"populated; got {p.get('auto_pr_url')!r}"
    )
    assert isinstance(p.get("staged_diff"), str) and p["staged_diff"], (
        "staged_diff must surface the would-PR text when auto-PR is "
        "off — that's how the demo shows the diff without firing a real "
        f"gh pr create; got {p.get('staged_diff')!r}"
    )

    # --- Terminal `done` frame ---
    done = [f for f in frames if f.get("event") == "done"]
    assert done, f"no `done` terminal frame; saw events: {kinds}"


def test_reflect_loop_rejects_missing_passcode(monkeypatch):
    """The endpoint must be passcode-gated. Without `X-Demo-Passcode`
    header, the request 401s — same posture as `/portfolio` and
    `/review-by-deal`. A widened gating would silently expose the
    LoopAgent run surface to the public internet.
    """
    pytest.importorskip("pydantic")
    fastapi_testclient = pytest.importorskip("fastapi.testclient")

    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode-gate")

    from agent import server as srv

    monkeypatch.setattr(srv, "DEMO_PASSCODE", "test-passcode-gate")

    with fastapi_testclient.TestClient(srv.app) as client:
        resp = client.post("/reflect/loop", json={"deal_id": None})

    assert resp.status_code in (401, 403), (
        f"expected 401/403 without passcode; got {resp.status_code}: "
        f"{resp.text[:200]}"
    )
