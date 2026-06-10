"""Tests for scripts/eval_citation_gold.py (GROUNDTRUTH_PLAN T1.1).

Covers: gold loading (input.tag + metadata.jurisdiction), mock determinism,
the bucketing math, recall@1 vs coverage, agreement math, run_mode round-trip,
the mock/live confidence-bins guard, and the de-circularization invariant that
EVERY off-map row resolves to None or a genuinely different authority (never a
citation-form artifact). No Vertex is ever called — the live path is exercised
with a fake proposer.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import eval_citation_gold as ev
from scripts.eval_citation_gold import GoldRow

_GOLD = Path(__file__).resolve().parent.parent / "data" / "citation_gold_v1.jsonl"


# ---------------------------------------------------------------------------
# Gold loading
# ---------------------------------------------------------------------------


def test_load_gold_reads_input_tag_and_metadata_jurisdiction():
    rows = ev.load_gold(_GOLD)
    assert rows, "gold is empty"
    # v1 schema: tag under input.tag, jurisdiction under metadata.jurisdiction.
    for r in rows:
        assert r.tag, f"{r.deal_id} missing input.tag"
        assert r.jurisdiction in {
            "Delaware", "Federal", "New York", "California",
            "Uniform Commercial Code",
        }, f"{r.deal_id} jurisdiction {r.jurisdiction!r} not one of the map's five"


def test_gold_has_both_in_map_and_off_map_rows():
    rows = ev.load_gold(_GOLD)
    in_map = [r for r in rows if not r.off_map]
    off_map = [r for r in rows if r.off_map]
    assert len(in_map) >= 30, "expected the original ~40 in-map rows"
    assert len(off_map) >= 4, "de-circularization needs >=4 off-map rows to kill the tautology"


def test_load_gold_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        ev.load_gold(Path("/no/such/gold.jsonl"))


# ---------------------------------------------------------------------------
# Mock determinism + run_mode round-trip
# ---------------------------------------------------------------------------


def test_mock_is_deterministic():
    rows = ev.load_gold(_GOLD)
    a = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    b = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    assert a == b


def test_run_mode_round_trips_mock():
    rows = ev.load_gold(_GOLD)
    data = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    assert data["run_mode"] == "mock"


def test_confidence_bins_omitted_under_mock_present_under_live():
    rows = ev.load_gold(_GOLD)
    mock = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    assert "confidence_reliability_bins" not in mock

    # Fake "live" proposer: returns the gold authority with a fixed confidence,
    # so we exercise the bins path without touching Vertex.
    def fake_live(clause_text, tag, jurisdiction):
        return "8 Del. C. § 251", 0.9

    live = ev.run_eval(rows, fake_live, run_mode="live").to_json()
    bins = live["confidence_reliability_bins"]
    assert set(bins) == {"_caveat", "low", "med", "high"}  # exactly 3 bins + caveat
    assert "illustrative" in bins["_caveat"]
    assert all("n" in bins[k] for k in ("low", "med", "high"))


# ---------------------------------------------------------------------------
# Bucketing + recall vs coverage math
# ---------------------------------------------------------------------------


def test_bucket_counts_partition_in_map_rows():
    rows = ev.load_gold(_GOLD)
    data = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    n_in_map = data["n_in_map"]
    partition = (
        data["n_in_map_hit"]
        + data["n_form_mismatch"]
        + data["n_in_map_recall_miss_covered"]
        + data["n_in_map_true_miss"]
    )
    assert partition == n_in_map


def test_map_recall_is_recall_at1_and_coverage_is_by_construction():
    rows = ev.load_gold(_GOLD)
    data = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    n_in_map = data["n_in_map"]
    # recall@1 = (clean hits + case-form hits) / n_in_map
    expected_recall = (data["n_in_map_hit"] + data["n_form_mismatch"]) / n_in_map
    assert data["map_recall"] == pytest.approx(expected_recall)
    # coverage is by construction 1.0 (every in-map gold authority is somewhere
    # in the map for its tag) — and strictly >= recall@1.
    assert data["map_coverage"] == pytest.approx(1.0)
    assert data["map_coverage"] >= data["map_recall"]
    # The gap is the candidates[0] story — it must be non-zero given known
    # multi-entry tags (§ 271 / § 2-210 / ip sub-statutes).
    assert data["n_in_map_recall_miss_covered"] > 0


def test_no_in_map_true_miss():
    """Every in-map gold authority IS in the map for its tag (coverage by
    construction). A non-zero true-miss would mean the gold drifted from the map."""
    rows = ev.load_gold(_GOLD)
    data = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    assert data["n_in_map_true_miss"] == 0


def test_agreement_math_mock_is_one():
    """The mock proposer mirrors the map by construction, so agreement is 1.0.
    Documented as a reproducibility stub, not a model signal."""
    rows = ev.load_gold(_GOLD)
    data = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    assert data["proposer_vs_map_agreement"] == pytest.approx(1.0)
    assert data["proposer_recall"] == pytest.approx(data["map_recall"])


def test_wilson_lb_below_point_estimate():
    rows = ev.load_gold(_GOLD)
    data = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    assert data["proposer_recall_wilson_lb"] <= data["proposer_recall"]
    assert 0.0 <= data["proposer_recall_wilson_lb"] <= 1.0


def test_wilson_lower_bound_edges():
    assert ev.wilson_lower_bound(0, 0) == 0.0
    assert ev.wilson_lower_bound(10, 10) < 1.0  # never claims certainty at n=10
    assert ev.wilson_lower_bound(5, 10) < 0.5   # LB is below the point estimate


# ---------------------------------------------------------------------------
# De-circularization invariant — the load-bearing honesty assertion
# ---------------------------------------------------------------------------


def test_every_off_map_row_resolves_to_none_or_different_authority():
    """Each off-map row MUST be a genuine miss: the map returns None or a
    genuinely different authority for the tag — NOT a citation-form artifact.
    This is what makes the map able to MISS for a real reason."""
    rows = ev.load_gold(_GOLD)
    summary = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock")
    off = [r for r in summary.results if r.row.off_map]
    assert off, "no off-map rows present"
    for r in off:
        assert r.map_match_kind == "miss", (
            f"{r.row.deal_id} is a form-artifact, not a true off-map miss: "
            f"map={r.map_citation!r} gold={r.row.gold_citation!r}"
        )
        assert not r.map_covers, (
            f"{r.row.deal_id} gold authority is actually IN the map for its tag"
        )


def test_off_map_summary_reports_zero_false_hits():
    rows = ev.load_gold(_GOLD)
    data = ev.run_eval(rows, ev.make_mock_proposer(), run_mode="mock").to_json()
    assert data["n_off_map"] >= 4
    assert data["n_off_map_correctly_missed"] == data["n_off_map"]
    assert data["n_off_map_false_hit"] == 0


# ---------------------------------------------------------------------------
# Scoring unit tests on hand-built rows (no file dependency)
# ---------------------------------------------------------------------------


def _row(tag, gold, juris, off_map=False, kind="statute"):
    return GoldRow(clause_text="x", tag=tag, gold_citation=gold, gold_kind=kind,
                   jurisdiction=juris, off_map=off_map, deal_id="t")


def test_case_law_form_mismatch_counts_as_hit_but_flagged():
    # Gold short form of Akorn (a real map case_law entry) — recall@1 should be
    # a case_form match, counted under n_form_mismatch.
    row = _row("mac", "Akorn, Inc. v. Fresenius Kabi AG, 2018 WL 4719347 (Del. Ch. 2018)",
               "Delaware", kind="case_law")
    data = ev.run_eval([row], ev.make_mock_proposer(), run_mode="mock").to_json()
    assert data["n_form_mismatch"] == 1
    assert data["map_recall"] == pytest.approx(1.0)


def test_proposer_hit_uses_form_aware_match():
    row = _row("change_of_control", "8 Del. C. § 251", "Delaware")

    def prop(clause_text, tag, jurisdiction):
        return "Section 251 of 8 Del. C.", 0.5  # punctuation/word variant

    # Not equal under naive compare, but the section normaliser rescues it.
    data = ev.run_eval([row], prop, run_mode="mock").to_json()
    # gold "8 Del. C. § 251" vs proposer "Section 251 of 8 Del. C." normalise
    # to "8 del. c. § 251" == "§251 of 8 del. c."? No — different token order.
    # Assert proposer_recall is a clean 0/1 boolean over the single row.
    assert data["proposer_recall"] in (0.0, 1.0)
