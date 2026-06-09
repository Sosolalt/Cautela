"""Tests for scripts/verify_structural_reasoning.py (Fix 6).

Defensive priorities, mirroring tests/test_eval_maud_mcq.py:
  - Mock mode must run end-to-end (the CI gate).
  - The matcher must distinguish a structure-conditional verdict from a
    flat / non-differentiated one (the very property the demo beat depends
    on — if this matcher is too lax, a green Day-3 run could mean nothing).
  - Live mode is gated behind `make_live_cross_reference` which raises
    NotImplementedError (PROJECT_LOG Phase 6.6 convention). We pin that
    behavior so a future refactor can't silently no-op `--live`.

DO NOT exercise the live agent here — Vertex quota is not available in CI.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import verify_structural_reasoning as V


# ---------------------------------------------------------------------------
# 1. Fixture loading
# ---------------------------------------------------------------------------


def test_fixtures_load_exactly_two_pairs():
    fixtures = V.load_fixtures()
    assert len(fixtures) == 2, (
        "Fix 6 demo beat depends on EXACTLY two paired fixtures (RTM + "
        "forward merger). Adding a third silently would dilute the matcher."
    )


def test_fixtures_carry_identical_anti_assignment_text():
    """The structural-reasoning premise: SAME clause text, DIFFERENT structure.

    If the two fixtures' anti-assignment text drifts apart, the demo loses
    its punch — the partner critic's "same clause, opposite verdicts"
    framing requires literal text identity.
    """
    fixtures = V.load_fixtures()
    texts = []
    for fx in fixtures:
        clause = next(
            c for c in fx.clauses if c.id == "sec_12_3_anti_assignment"
        )
        texts.append(clause.text)
    assert texts[0] == texts[1], (
        "Anti-assignment clause text drifted between RTM and forward-merger "
        "fixtures; the demo's same-clause-opposite-verdicts framing breaks."
    )


def test_fixtures_have_different_deal_structure():
    fixtures = V.load_fixtures()
    structures = {fx.deal_structure for fx in fixtures}
    assert structures == {
        "reverse_triangular_merger_delaware_law",
        "forward_merger",
    }


def test_fixtures_carry_definition_and_operative_clauses():
    """CrossReference (prompts.py:90+ CROSS_REFERENCE_PROMPT) needs BOTH the
    definition of "Assignment" AND the operative anti-assignment clause to
    do its definition->operative resolution. If a fixture is missing one,
    the agent has nothing to cross-reference."""
    fixtures = V.load_fixtures()
    for fx in fixtures:
        clause_ids = {c.id for c in fx.clauses}
        assert "def_assignment" in clause_ids, fx.fixture_id
        assert "sec_12_3_anti_assignment" in clause_ids, fx.fixture_id
        assert "recital_b_structure" in clause_ids, fx.fixture_id


# ---------------------------------------------------------------------------
# 2. Matcher logic — the load-bearing structural-reasoning gate
# ---------------------------------------------------------------------------


def test_matcher_passes_on_correct_severity_and_keywords():
    verdict = V.VerdictResult(
        fixture_id="rtm_delaware",
        severity="info",
        cited_spans=["def_assignment", "sec_12_3_anti_assignment"],
        explanation=(
            "Reverse triangular merger; Meso Scale v. Roche holds this is "
            "not an assignment by operation of law."
        ),
    )
    passed, _ = verdict.matches_expected(
        "info",
        ["reverse triangular", "Meso Scale", "operation of law"],
    )
    assert passed


def test_matcher_fails_on_severity_mismatch():
    """A non-differentiated agent that just labels both 'block' must FAIL
    the matcher — otherwise Day 3 green means nothing."""
    verdict = V.VerdictResult(
        fixture_id="rtm_delaware",
        severity="block",  # WRONG — RTM should not trigger
        cited_spans=["sec_12_3_anti_assignment"],
        explanation=(
            "Reverse triangular merger; Meso Scale v. Roche operation of law."
        ),
    )
    passed, diag = verdict.matches_expected(
        "info",
        ["reverse triangular", "Meso Scale", "operation of law"],
    )
    assert not passed
    assert "severity mismatch" in diag


def test_matcher_fails_on_missing_structural_reasoning_keywords():
    """If severity is right but the explanation cites no controlling
    precedent and shows no structural reasoning, the matcher must FAIL.
    Otherwise the agent could be guessing severity from clause text alone."""
    verdict = V.VerdictResult(
        fixture_id="forward_merger",
        severity="block",
        cited_spans=["sec_12_3_anti_assignment"],
        explanation="Anti-assignment clause present; flagging as block.",
    )
    passed, diag = verdict.matches_expected(
        "block",
        ["forward merger", "Cincom", "PPG", "operation of law"],
    )
    assert not passed
    assert "rationale missing" in diag


# ---------------------------------------------------------------------------
# 3. Mock agent end-to-end (the CI gate)
# ---------------------------------------------------------------------------


def test_run_verification_mock_end_to_end_passes():
    fixtures = V.load_fixtures()
    agent = V.make_mock_cross_reference()
    report = V.run_verification(fixtures, agent)
    assert report.all_passed, report.failure_messages()
    assert len(report.outcomes) == 2


def test_run_verification_flat_agent_fails_both_fixtures():
    """A flat agent that emits the SAME verdict on both fixtures (no
    structural reasoning) must fail the matcher on at least one fixture.
    This is the property the Day-3 live gate actually tests."""
    fixtures = V.load_fixtures()

    def flat_agent(fixture: V.StructuralFixture) -> V.VerdictResult:
        return V.VerdictResult(
            fixture_id=fixture.fixture_id,
            severity="block",
            cited_spans=["sec_12_3_anti_assignment"],
            explanation="Anti-assignment clause present.",
        )

    report = V.run_verification(fixtures, flat_agent)
    assert not report.all_passed
    # At least one fixture must have failed (the RTM one — severity
    # mismatch — at minimum).
    assert any(not o.passed for o in report.outcomes)


# ---------------------------------------------------------------------------
# 4. CLI surface
# ---------------------------------------------------------------------------


def test_cli_default_is_mock_mode_and_exits_zero():
    """Default invocation (no --live) must exit 0 in CI."""
    rc = V.main([])
    assert rc == 0


def test_cli_live_without_runner_exits_one_with_cut_recommendation(caplog):
    """`--live` without a wired Runner must exit 1 (NOT 2 — exit 2 is a
    fixture/script bug). Mirrors eval_maud_mcq.py:make_live_agent which
    raises NotImplementedError until a Runner is wired (PROJECT_LOG Phase
    6.6 convention)."""
    import logging

    with caplog.at_level(logging.ERROR):
        rc = V.main(["--live"])
    assert rc == 1
    combined = " ".join(rec.getMessage() for rec in caplog.records)
    assert "CUT the structural-reasoning beat" in combined


# ---------------------------------------------------------------------------
# 5. Live-agent contract
# ---------------------------------------------------------------------------


def test_make_live_cross_reference_raises_not_implemented():
    """Pinned so a future refactor can't silently no-op the --live path."""
    with pytest.raises(NotImplementedError, match="Runner wrapper"):
        V.make_live_cross_reference()
