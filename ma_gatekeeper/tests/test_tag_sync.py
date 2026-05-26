"""Pin the single-source-of-truth for the Tag enum.

Background: Issue 6 caught a 4-way hand-replicated tag list across
`agent/schemas.py`, `agent/agents.py`, `scripts/annotate.py`, and
`frontend/lib/types.ts`. The Python side now derives from
`schemas.Tag` via `typing.get_args`; the TS side stays hand-mirrored
(no codegen for the hackathon) but is cross-checked here so drift
fails CI loudly.

These tests would have caught the original "easy to forget one when
adding a tag" failure mode the cold-onboarding reviewer (E7) flagged.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

from agent.agents import CLASSIFIER_TAGS as AGENTS_CLASSIFIER_TAGS
from agent.schemas import ALL_TAGS, CLASSIFIER_TAGS, Tag
from scripts.annotate import PRELABEL_INSTRUCTION, PRELABEL_TAGS


def test_all_tags_matches_literal():
    """`ALL_TAGS` is what consumers iterate over; it must equal the
    Literal members exactly."""
    assert set(ALL_TAGS) == set(get_args(Tag))


def test_classifier_tags_excludes_none():
    """The classifier ParallelAgent fan-out spawns one LlmAgent per
    real clause family; "none" is the absence label, not a target."""
    assert "none" not in CLASSIFIER_TAGS
    assert set(CLASSIFIER_TAGS) == set(ALL_TAGS) - {"none"}


def test_python_duplicates_are_gone():
    """The previous bug: agents.py and annotate.py each held their own
    7-string tuple. After Issue 6 they re-export the single source —
    these `is` identity checks fail if anyone re-introduces a literal."""
    assert AGENTS_CLASSIFIER_TAGS is CLASSIFIER_TAGS
    assert PRELABEL_TAGS is CLASSIFIER_TAGS


def test_prelabel_instruction_mentions_every_tag():
    """PRELABEL_INSTRUCTION is the prose Gemini sees. If a tag isn't
    mentioned, Gemini won't pre-label it — a silent recall hole on the
    Internal-30 gold set. The instruction is now f-stringed from
    PRELABEL_TAGS so this test is mostly belt-and-braces, but pins the
    invariant in case someone reverts the f-string."""
    for tag in CLASSIFIER_TAGS:
        assert tag in PRELABEL_INSTRUCTION, (
            f"{tag!r} missing from PRELABEL_INSTRUCTION — the LLM will "
            "never produce this tag and the gold set loses recall on it"
        )


def test_cross_reference_prompt_has_four_clause_family_headings():
    """`CROSS_REFERENCE_PROMPT` has 4 numbered `N. **clause_family**`
    blocks — `scripts/seed_reflector.py:_CLAUSE_BLOCK_RE` depends on
    exactly that structure to weaken the prompt for the D18 pre-seed.
    If anyone reformats the prompt and the regex stops matching, the
    D18 demo silently fails. Pin the four headings here so a regression
    fails fast in CI rather than 48h before recording."""
    from agent.prompts import CROSS_REFERENCE_PROMPT

    for n, family in enumerate(
        ("change_of_control", "anti_assignment", "mac", "accelerated_vesting"),
        start=1,
    ):
        heading = f"{n}. **{family}**"
        assert heading in CROSS_REFERENCE_PROMPT, (
            f"missing heading {heading!r} — breaks scripts/seed_reflector.py "
            "regex contract pinned in agent/prompts.py:81-87"
        )


def test_frontend_ts_tag_union_matches_python():
    """The TS Literal union in `frontend/lib/types.ts` is hand-mirrored
    (we don't ship codegen for the hackathon). Drift here means a tag
    exists in Python but the frontend dropdown / type-narrow won't
    accept it (or vice versa). Regex-extract the union members and
    compare to `set(ALL_TAGS)`."""
    # Path is relative to ma_gatekeeper/ (the pytest rootdir).
    ts_path = Path("frontend/lib/types.ts")
    if not ts_path.exists():
        # Frontend has been removed/relocated — skip rather than fail.
        # The user explicitly noted UX is being redone separately.
        import pytest

        pytest.skip(f"{ts_path} not present — frontend may be mid-refactor")
    ts = ts_path.read_text(encoding="utf-8")
    # Match: `export type Tag = "a" | "b" | ... ;`
    union_match = re.search(r"export\s+type\s+Tag\s*=([^;]+);", ts, re.DOTALL)
    assert union_match is not None, (
        "could not find `export type Tag = ... ;` in "
        f"{ts_path} — the regex may need updating after a TS reformat"
    )
    ts_members = set(re.findall(r'"([a-z_]+)"', union_match.group(1)))
    assert ts_members == set(ALL_TAGS), (
        f"TS Tag union drifted from Python:\n"
        f"  Python (ALL_TAGS): {sorted(ALL_TAGS)}\n"
        f"  TS:                {sorted(ts_members)}\n"
        f"Missing in TS:       {sorted(set(ALL_TAGS) - ts_members)}\n"
        f"Extra in TS:         {sorted(ts_members - set(ALL_TAGS))}"
    )
