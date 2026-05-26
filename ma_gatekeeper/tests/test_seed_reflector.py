"""Tests for scripts/seed_reflector.py.

The Phoenix upsert path is integration-only (gated behind live client);
tests exercise the pure-Python template transformation and SeedPlan
construction — the parts that, if wrong, would corrupt the demo
recording on D19.
"""
from __future__ import annotations

import pytest

from agent.prompts import CROSS_REFERENCE_PROMPT
from scripts.seed_reflector import (
    PROMPT_NAME,
    TAG_CANDIDATE,
    TAG_PRODUCTION,
    apply_seed_plan,
    build_seed_plan,
    make_weak_template,
)


def test_weak_template_is_shorter_than_strong():
    weak = make_weak_template()
    assert len(weak) < len(CROSS_REFERENCE_PROMPT)


def test_weak_template_drops_clause_family_blocks():
    weak = make_weak_template()
    # The four numbered clause families should be gone — the agent loses
    # its concrete guidance on what to look for.
    for needle in (
        "1. **change_of_control**",
        "2. **anti_assignment**",
        "3. **mac**",
        "4. **accelerated_vesting**",
    ):
        assert needle not in weak, f"weak template still contains {needle!r}"


def test_weak_template_keeps_severity_rubric():
    """The severity rubric is generic structural guidance, not clause-family
    advice — it should survive. If the regex over-matched and ate it, the
    agent would lose its ability to even pick a severity label."""
    weak = make_weak_template()
    assert "For each finding, emit:" in weak
    assert '"block"' in weak
    assert '"watch"' in weak
    assert '"info"' in weak


def test_weak_template_keeps_preamble():
    weak = make_weak_template()
    assert "You are an M&A cross-reference resolver." in weak


def test_weak_template_rewrites_orphan_opener():
    """After the 4 numbered blocks are stripped, the "The four clause
    families that matter most:" opener would dangle with nothing under
    it. Verify it was rewritten."""
    weak = make_weak_template()
    assert "four clause families" not in weak.lower()
    assert "Identify deal-critical triggers" in weak


def test_make_weak_template_idempotent_on_already_weak():
    """Running the stripper on an already-stripped template must raise
    (the post-condition `len(weak) < len(strong)` fails) — this is the
    safety net against accidentally running the script twice and silently
    no-op'ing in a way that looks successful."""
    once = make_weak_template()
    with pytest.raises(RuntimeError, match="weak template did not shrink"):
        make_weak_template(once)


def test_build_seed_plan_pairs_tags_correctly():
    """The weak template MUST be tagged `production` (that's the one the
    agent serves to end-users); strong MUST be tagged `candidate` (the
    one the Reflector experiment will promote). Swapping these would
    show the strong prompt in the live demo and the Reflector would
    have nothing to improve."""
    plan = build_seed_plan()
    assert plan.prompt_name == PROMPT_NAME
    assert plan.weak_tag == TAG_PRODUCTION
    assert plan.strong_tag == TAG_CANDIDATE
    assert plan.weak_template != plan.strong_template
    assert plan.strong_template == CROSS_REFERENCE_PROMPT


def test_apply_seed_plan_upserts_strong_first(monkeypatch):
    """If the script fails between upserts we must NOT leave production
    pointing at a weak template with no candidate alongside (the
    Reflector's two-prompt experiment would have nothing to compare).
    Strong-first means a mid-flight failure is recoverable."""
    plan = build_seed_plan()
    order: list[tuple[str, str]] = []

    def fake_upsert(client, *, name, template, tag):
        order.append((tag, template[:30]))
        return f"v_{tag}"

    monkeypatch.setattr("agent.reflector._upsert_prompt", fake_upsert)
    weak_id, strong_id = apply_seed_plan(plan, client=object())
    assert order[0][0] == TAG_CANDIDATE  # strong went up first
    assert order[1][0] == TAG_PRODUCTION
    assert weak_id == f"v_{TAG_PRODUCTION}"
    assert strong_id == f"v_{TAG_CANDIDATE}"


def test_apply_seed_plan_writes_distinct_templates(monkeypatch):
    """Sanity check that we don't accidentally pass the same template
    string under both tags — that would corrupt the demo silently."""
    plan = build_seed_plan()
    written: dict[str, str] = {}

    def fake_upsert(client, *, name, template, tag):
        written[tag] = template
        return f"v_{tag}"

    monkeypatch.setattr("agent.reflector._upsert_prompt", fake_upsert)
    apply_seed_plan(plan, client=object())
    assert written[TAG_PRODUCTION] != written[TAG_CANDIDATE]
    assert len(written[TAG_PRODUCTION]) < len(written[TAG_CANDIDATE])
