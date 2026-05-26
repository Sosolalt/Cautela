"""Tests for the deterministic Router (plan §6.2 v3).

Validates the independent-gating rule:
- Both evaluators must pass their threshold for auto_clear or block lane.
- Either failure -> escalate.
- info severity passing both gates -> auto_clear (not block).
- block severity passing both gates -> block (not auto_clear).

The router lives entirely in Python; the Phoenix annotation write is
best-effort and tested separately via mocks (skipped when Phoenix is
unavailable).
"""
from __future__ import annotations

import pytest

from agent.router import Thresholds, judge_and_route
from agent.schemas import RiskFinding


def _finding(severity: str) -> RiskFinding:
    return RiskFinding(
        clause_id="sec_4.2_para_b",
        clause_text="Upon any change of control...",
        tag="change_of_control",
        severity=severity,  # type: ignore[arg-type]
        judge_score=0.85,
        cited_spans=["sec_1.1_def"],
        cited_spans_text="'Change of Control' means...",
        explanation="The CoC trigger covers indirect equity changes.",
        # trace_id is server-populated; routing logic doesn't read it.
    )


T = Thresholds(tau_h=0.80, tau_f=0.70)


def test_block_passes_both_gates_keeps_block_lane():
    decision = judge_and_route(
        _finding("block"),
        h_score=0.92, h_label="factual",
        f_score=0.85, f_label="faithful",
        thresholds=T,
    )
    assert decision.lane == "block"


def test_info_passes_both_gates_auto_clears():
    decision = judge_and_route(
        _finding("info"),
        h_score=0.92, h_label="factual",
        f_score=0.85, f_label="faithful",
        thresholds=T,
    )
    assert decision.lane == "auto_clear"


def test_hallucination_fail_escalates_even_high_faithfulness():
    """Critical: a hallucinated explanation must NEVER auto-clear or block.

    This is the recall-optimal gating rule. v2 averaged the two scores
    and could have auto-cleared this with (0.55 + 0.95)/2 = 0.75 >= 0.70.
    """
    decision = judge_and_route(
        _finding("block"),
        h_score=0.55, h_label="hallucinated",
        f_score=0.95, f_label="faithful",
        thresholds=T,
    )
    assert decision.lane == "escalate"


def test_faithfulness_fail_escalates_even_high_hallucination_score():
    decision = judge_and_route(
        _finding("block"),
        h_score=0.99, h_label="factual",
        f_score=0.30, f_label="unfaithful",
        thresholds=T,
    )
    assert decision.lane == "escalate"


def test_watch_severity_escalates_when_gates_pass():
    """`watch` is not a "definitely clear" - it always escalates."""
    decision = judge_and_route(
        _finding("watch"),
        h_score=0.95, h_label="factual",
        f_score=0.95, f_label="faithful",
        thresholds=T,
    )
    assert decision.lane == "escalate"


def test_threshold_applied_is_min_of_two():
    decision = judge_and_route(
        _finding("info"),
        h_score=0.99, h_label="factual",
        f_score=0.99, f_label="faithful",
        thresholds=T,
    )
    assert decision.threshold_applied == 0.70  # min(0.80, 0.70)


def test_thresholds_from_json(tmp_path):
    artifact = tmp_path / "t.json"
    artifact.write_text('{"tau_h": 0.81, "tau_f": 0.72}')
    t = Thresholds.from_json(str(artifact))
    assert t.tau_h == 0.81
    assert t.tau_f == 0.72
