"""Tests for scripts/make_kappa_template.py (GROUNDTRUTH_PLAN T1.3).

The load-bearing property: the emitted template's `(contract_id, clause_id,
char_start)` keys MUST match the prelabels exactly, so `annotate.py kappa`'s
intersection is non-empty (the bug the script exists to prevent). Also: the
prelabel TAG is withheld (no anchoring), selection is deterministic and spread
across contracts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import annotate
from scripts import make_kappa_template as M


def _prelabel_record(cid: str, clid: str, start: int, end: int, tag: str) -> dict:
    """Argilla SpanQuestion-shaped prelabel record (what annotate.py emits)."""
    return {
        "fields": {"text": f"clause {clid} text"},
        "suggestions": [
            {"question_name": "tag", "value": tag, "agent": "gemini-3-pro"},
            {"question_name": "span", "field": "text",
             "value": [{"start": start, "end": end, "label": tag}]},
        ],
        "metadata": {"contract_id": cid, "clause_id": clid,
                     "trigger_language": "x", "explanation": "y"},
    }


def _write_prelabels(tmp_path: Path) -> Path:
    rows = []
    for c in range(4):  # 4 contracts
        for s in range(5):  # 5 spans each -> 20 total
            rows.append(_prelabel_record(
                f"contract-{c}", f"clause-{c}-{s}", start=s * 100, end=s * 100 + 40,
                tag="change_of_control" if s == 0 else "mac",
            ))
    p = tmp_path / "prelabels.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return p


def test_template_keys_match_prelabels_for_nonempty_kappa_intersection(tmp_path: Path):
    prelabels = _write_prelabels(tmp_path)
    spans = M.load_prelabel_spans(prelabels)
    template = M.make_template_records(M.select_spans(spans, 12))
    out = tmp_path / "template.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in template), encoding="utf-8")

    # The actual guard: annotate.py's loader keys both files identically, so the
    # intersection is non-empty (this is the "no overlapping clause_ids" bug).
    pre_keys = set(annotate._load_clause_tags(prelabels))
    tmpl_keys = set(annotate._load_clause_tags(out))
    assert tmpl_keys, "template produced no keys"
    assert tmpl_keys <= pre_keys, "template keys drifted from the prelabels"
    assert len(tmpl_keys & pre_keys) == len(tmpl_keys)


def test_prelabel_tag_is_withheld(tmp_path: Path):
    prelabels = _write_prelabels(tmp_path)
    spans = M.load_prelabel_spans(prelabels)
    template = M.make_template_records(M.select_spans(spans, 12))
    for rec in template:
        assert rec["tag"] == "", "the model's suggested tag must be withheld (no anchoring)"


def test_selection_is_deterministic(tmp_path: Path):
    prelabels = _write_prelabels(tmp_path)
    spans = M.load_prelabel_spans(prelabels)
    a = M.make_template_records(M.select_spans(spans, 12))
    b = M.make_template_records(M.select_spans(M.load_prelabel_spans(prelabels), 12))
    assert a == b


def test_selection_spread_across_contracts(tmp_path: Path):
    prelabels = _write_prelabels(tmp_path)
    spans = M.load_prelabel_spans(prelabels)
    selected = M.select_spans(spans, 8)
    contracts = {s["contract_id"] for s in selected}
    # Round-robin must touch all 4 contracts before doubling up.
    assert len(contracts) == 4


def test_selection_caps_at_n(tmp_path: Path):
    prelabels = _write_prelabels(tmp_path)
    spans = M.load_prelabel_spans(prelabels)
    assert len(M.select_spans(spans, 12)) == 12
    # n larger than the pool returns the whole pool, not an error.
    assert len(M.select_spans(spans, 999)) == 20


def test_load_prelabels_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        M.load_prelabel_spans(tmp_path / "nope.jsonl")


def test_filled_template_computes_a_real_kappa(tmp_path: Path):
    """End-to-end: fill the template with tags and confirm annotate.kappa runs
    on the non-empty intersection (no ValueError)."""
    prelabels = _write_prelabels(tmp_path)
    spans = M.load_prelabel_spans(prelabels)
    template = M.make_template_records(M.select_spans(spans, 12))
    # Simulate the human filling tags (here: agree on half, differ on half).
    for i, rec in enumerate(template):
        rec["tag"] = "change_of_control" if i % 2 == 0 else "anti_assignment"
    human = tmp_path / "human_adjudicated.jsonl"
    human.write_text("\n".join(json.dumps(r) for r in template), encoding="utf-8")

    k = annotate.cohen_kappa(prelabels, human)
    assert isinstance(k, float)
    assert -1.0 <= k <= 1.0
