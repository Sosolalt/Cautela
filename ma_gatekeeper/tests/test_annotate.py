"""Unit tests for scripts/annotate.py — pure-Python paths only.

The Gemini call itself is integration-only (gated behind credentials);
tests pass a deterministic stub labeler so we exercise the JSONL
serialization, kappa math, and validation paths without network."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.annotate import (
    PrelabelSpan,
    _coerce_span,
    _kappa_from_pairs,
    cohen_kappa,
    prelabel_corpus,
)
from scripts import annotate as annotate_mod


def _make_span(**overrides) -> PrelabelSpan:
    base = dict(
        contract_id="ABC_8K_Ex21",
        clause_id="sec_4.2_b",
        text="No party may assign...",
        char_start=0,
        char_end=23,
        suggested_tag="anti_assignment",
        suggested_severity="block",
        confidence=0.85,
        trigger_language="No party may assign",
        explanation="bare anti-assignment with no consent carve-out",
    )
    base.update(overrides)
    return PrelabelSpan(**base)


def test_argilla_record_has_required_fields():
    span = _make_span()
    rec = span.to_argilla_record()
    assert rec["fields"]["text"].startswith("No party")
    names = {s["question_name"] for s in rec["suggestions"]}
    assert names == {"tag", "severity", "span"}
    assert rec["metadata"]["contract_id"] == "ABC_8K_Ex21"
    assert rec["metadata"]["clause_id"] == "sec_4.2_b"


def test_span_suggestion_uses_char_offsets():
    span = _make_span(char_start=100, char_end=200)
    rec = span.to_argilla_record()
    span_q = next(s for s in rec["suggestions"] if s["question_name"] == "span")
    assert span_q["value"][0]["start"] == 100
    assert span_q["value"][0]["end"] == 200
    assert span_q["value"][0]["label"] == "anti_assignment"


def test_coerce_span_rejects_unknown_tag():
    with pytest.raises(ValueError, match="out-of-vocab tag"):
        _coerce_span(
            "X",
            {
                "clause_id": "x",
                "text": "y",
                "char_start": 0,
                "char_end": 1,
                "suggested_tag": "bogus_tag",
                "suggested_severity": "info",
                "confidence": 0.5,
            },
        )


def test_coerce_span_rejects_unknown_severity():
    with pytest.raises(ValueError, match="out-of-vocab severity"):
        _coerce_span(
            "X",
            {
                "clause_id": "x",
                "text": "y",
                "char_start": 0,
                "char_end": 1,
                "suggested_tag": "mac",
                "suggested_severity": "CRITICAL",
                "confidence": 0.5,
            },
        )


def test_prelabel_corpus_writes_jsonl(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "c1.txt").write_text("contract one text")
    (in_dir / "c2.txt").write_text("contract two text")

    def stub_labeler(contract_id: str, text: str) -> list[PrelabelSpan]:
        return [_make_span(contract_id=contract_id, clause_id=f"{contract_id}_x")]

    out = tmp_path / "out.jsonl"
    summary = prelabel_corpus(in_dir, out, labeler=stub_labeler)
    assert summary.n_spans == 2
    assert set(summary.ok_contracts) == {"c1", "c2"}
    assert summary.failed_contracts == ()
    lines = out.read_text().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    contract_ids = {r["metadata"]["contract_id"] for r in records}
    assert contract_ids == {"c1", "c2"}


def test_prelabel_corpus_honors_limit(tmp_path: Path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    for i in range(5):
        (in_dir / f"c{i}.txt").write_text(f"contract {i}")

    def stub_labeler(contract_id, text):
        return [_make_span(contract_id=contract_id, clause_id=contract_id)]

    out = tmp_path / "out.jsonl"
    summary = prelabel_corpus(in_dir, out, labeler=stub_labeler, limit=3)
    assert summary.n_spans == 3
    assert len(summary.ok_contracts) == 3


def test_prelabel_corpus_records_failure_per_contract(tmp_path: Path):
    """A failing labeler must not silently drop a contract from the manifest."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "good.txt").write_text("ok contract")
    (in_dir / "bad.txt").write_text("kaboom")

    def labeler(contract_id, text):
        if contract_id == "bad":
            raise RuntimeError("simulated API failure")
        return [_make_span(contract_id=contract_id, clause_id="x")]

    summary = prelabel_corpus(in_dir, tmp_path / "out.jsonl", labeler=labeler)
    assert summary.ok_contracts == ("good",)
    assert summary.failed_contracts == ("bad",)
    assert summary.n_spans == 1


def test_prelabel_corpus_records_empty_per_contract(tmp_path: Path):
    """A contract that yields zero spans is bookkept distinctly from a failure."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "clean.txt").write_text("no clauses here")

    summary = prelabel_corpus(
        in_dir, tmp_path / "out.jsonl", labeler=lambda cid, t: []
    )
    assert summary.empty_contracts == ("clean",)
    assert summary.failed_contracts == ()
    assert summary.n_spans == 0


def test_prelabel_corpus_strict_utf8(tmp_path: Path):
    """Silent character substitution in legal text changes meaning — surface
    the encoding error at ingest time, not at adjudication time."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "bad.txt").write_bytes(b"valid text \xff and invalid byte")
    with pytest.raises(UnicodeDecodeError):
        prelabel_corpus(
            in_dir, tmp_path / "out.jsonl", labeler=lambda cid, t: []
        )


def test_kappa_perfect_agreement_returns_one():
    pairs = [("mac", "mac"), ("change_of_control", "change_of_control")]
    assert _kappa_from_pairs(pairs) == pytest.approx(1.0)


def test_kappa_chance_agreement_returns_zero():
    # Two annotators each evenly split between two labels with no correlation:
    # po = 0.5, pe = 0.5 -> kappa = 0
    pairs = [("a", "a"), ("a", "b"), ("b", "a"), ("b", "b")]
    assert _kappa_from_pairs(pairs) == pytest.approx(0.0)


def test_kappa_disagreement_negative():
    # Systematically opposite annotators: po=0, pe=0.5 -> kappa = -1
    pairs = [("a", "b"), ("b", "a"), ("a", "b"), ("b", "a")]
    assert _kappa_from_pairs(pairs) == pytest.approx(-1.0)


def test_kappa_degenerate_single_label_agrees():
    # Both annotators put everything in one bucket and agree.
    # sklearn raises a warning + NaN here; we return 1.0 by convention so
    # downstream code doesn't NaN-propagate (see _kappa_from_pairs docstring).
    pairs = [("mac", "mac"), ("mac", "mac"), ("mac", "mac")]
    assert _kappa_from_pairs(pairs) == pytest.approx(1.0)


def test_kappa_degenerate_single_label_disagrees():
    pairs = [("mac", "anti_assignment")] * 3
    assert _kappa_from_pairs(pairs) == pytest.approx(0.0)


def test_cohen_kappa_reads_jsonl_files(tmp_path: Path):
    def _write(path: Path, pairs):
        with path.open("w") as fh:
            for cid, clid, tag in pairs:
                rec = _make_span(
                    contract_id=cid, clause_id=clid, suggested_tag=tag
                ).to_argilla_record()
                fh.write(json.dumps(rec) + "\n")

    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write(a, [("C1", "x", "mac"), ("C1", "y", "change_of_control")])
    _write(b, [("C1", "x", "mac"), ("C1", "y", "change_of_control")])
    assert cohen_kappa(a, b) == pytest.approx(1.0)


def test_coerce_span_enforces_char_offset_invariant():
    contract = "The party may not assign this Agreement without consent."
    bad_item = {
        "clause_id": "x",
        "text": "may not assign",
        "char_start": 0,  # wrong — actual offsets are 10-24
        "char_end": 14,
        "suggested_tag": "anti_assignment",
        "suggested_severity": "block",
        "confidence": 0.9,
    }
    with pytest.raises(ValueError, match="char-offset invariant"):
        _coerce_span("C", bad_item, contract)


def test_coerce_span_offsets_match():
    contract = "The party may not assign this Agreement without consent."
    good_item = {
        "clause_id": "x",
        "text": "may not assign",
        "char_start": 10,
        "char_end": 24,
        "suggested_tag": "anti_assignment",
        "suggested_severity": "block",
        "confidence": 0.9,
    }
    span = _coerce_span("C", good_item, contract)
    assert span.char_start == 10
    assert span.char_end == 24
    assert span.suggested_tag == "anti_assignment"


def test_argilla_span_suggestion_has_field_anchor():
    """Argilla 2.x SpanQuestion suggestions silently fail to render the
    highlight if the `field` reference is missing — verify it survives the
    JSONL round-trip."""
    rec = _make_span().to_argilla_record()
    span_q = next(s for s in rec["suggestions"] if s["question_name"] == "span")
    assert span_q["field"] == "text"


def test_block_severity_survives_jsonl_roundtrip(tmp_path: Path):
    """Asymmetric-loss invariant: a 'block' suggestion must NOT be silently
    coerced to 'info' or 'watch' on its way through serialization. A
    block->info swap is the entire safety failure mode of this pipeline."""
    span = _make_span(suggested_severity="block", suggested_tag="change_of_control")
    path = tmp_path / "one.jsonl"
    path.write_text(json.dumps(span.to_argilla_record()) + "\n")
    rec = json.loads(path.read_text().strip())
    sev = next(s for s in rec["suggestions"] if s["question_name"] == "severity")
    assert sev["value"] == "block"
    tag = next(s for s in rec["suggestions"] if s["question_name"] == "tag")
    assert tag["value"] == "change_of_control"


def test_kappa_distinguishes_overlapping_spans_per_clause(tmp_path: Path):
    """Two spans within one clause carry distinct char_starts; the kappa
    key keeps them separate so a disagreement on one span isn't masked
    by agreement on the other."""

    def _write(path: Path, rows):
        with path.open("w") as fh:
            for cid, clid, char_start, tag in rows:
                rec = _make_span(
                    contract_id=cid,
                    clause_id=clid,
                    char_start=char_start,
                    char_end=char_start + 10,
                    suggested_tag=tag,
                ).to_argilla_record()
                fh.write(json.dumps(rec) + "\n")

    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    # Same clause_id, two spans at different offsets; annotators agree on
    # span @100 and disagree on span @500.
    _write(a, [("C1", "sec_4", 100, "mac"), ("C1", "sec_4", 500, "mac")])
    _write(b, [("C1", "sec_4", 100, "mac"), ("C1", "sec_4", 500, "change_of_control")])
    k = cohen_kappa(a, b)
    # If the loader collapsed both spans onto one key the last one wins
    # and kappa would be 0.0 (full disagreement) or 1.0 (full agreement),
    # not the in-between value the separate keying produces.
    assert 0.0 <= k < 1.0


def test_cohen_kappa_raises_on_disjoint_keys(tmp_path: Path):
    def _write(path: Path, cid: str):
        rec = _make_span(contract_id=cid, clause_id="x").to_argilla_record()
        path.write_text(json.dumps(rec) + "\n")

    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write(a, "A")
    _write(b, "B")
    with pytest.raises(ValueError, match="no overlapping"):
        cohen_kappa(a, b)
