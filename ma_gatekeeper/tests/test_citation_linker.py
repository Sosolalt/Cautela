"""Tests for the citation-linkage layer (design/STATUTE_LAYER.md §2.6).

Covers the deterministic map lookup (hit / graceful-None / jurisdiction hint),
the section-citation normaliser, and every background-proposer outcome
(timeout, garbage JSON, agree, disagree, no_static) plus the sync-fallback
annotation path. The LLM proposer is always patched — these never call Vertex.
"""
from __future__ import annotations

import asyncio
import json
import sys
import types
from datetime import date

import pytest

from agent import citation_linker as cl
from agent.schemas import _EVAL_ONLY_FIELDS, CitationRef, LinkerProposal, RiskFinding


def _ref(citation="8 Del. C. § 251", jurisdiction="Delaware",
         kind="statute") -> CitationRef:
    return CitationRef(
        citation=citation,
        citation_kind=kind,
        jurisdiction=jurisdiction,
        rationale="test",
        verified_date=date(2026, 6, 9),
        primary_source="delcode.delaware.gov",
    )


def _proposal(citation="8 Del. C. § 251", jurisdiction="Delaware",
              kind="statute", conf=0.9) -> LinkerProposal:
    return LinkerProposal(
        citation=citation, citation_kind=kind, jurisdiction=jurisdiction,
        rationale="test", model_confidence=conf,
    )


def _capture_annotate(monkeypatch) -> list[dict]:
    """Patch the (async-path) router._annotate imported into citation_linker."""
    calls: list[dict] = []

    def _fake(span_id, *, name, label, score, explanation):
        calls.append({"span_id": span_id, "name": name, "label": label,
                      "score": score, "explanation": explanation})

    monkeypatch.setattr("agent.citation_linker._annotate", _fake)
    return calls


def _patch_llm(monkeypatch, *, returns=None, raises=None):
    async def _fake(clause_text, tag, timeout=8.0):
        if raises is not None:
            raise raises
        return returns

    monkeypatch.setattr("agent.citation_linker._call_linker_llm", _fake)


# ---------------------------------------------------------------------------
# Deterministic map lookup.
# ---------------------------------------------------------------------------

def test_lookup_returns_citation_for_mapped_tag():
    ref = cl.lookup_citation("change_of_control")
    assert ref is not None
    assert ref.citation == "8 Del. C. § 251"
    assert ref.jurisdiction == "Delaware"
    assert ref.citation_kind == "statute"
    assert ref.primary_source  # audit field populated


def test_static_lookup_returns_none_outside_map_coverage():
    """accelerated_vesting is contract-anchored — no statute, no entry. The
    layer degrades to None, never a fabricated citation (spec §2.6)."""
    assert cl.lookup_citation("accelerated_vesting") is None


def test_lookup_unknown_tag_returns_none():
    assert cl.lookup_citation("definitely_not_a_tag") is None


def test_lookup_respects_jurisdiction_hint():
    ny = cl.lookup_citation("change_of_control", jurisdiction_hint="New York")
    assert ny is not None and ny.jurisdiction == "New York"
    assert ny.citation == "N.Y. Bus. Corp. Law § 902"
    # And a federal hint on a federal-statute tag.
    fed = cl.lookup_citation("ip_assignment", jurisdiction_hint="Federal")
    assert fed is not None and fed.jurisdiction == "Federal"


# ---------------------------------------------------------------------------
# Section-citation normaliser.
# ---------------------------------------------------------------------------

def test_normalise_equates_section_punctuation_variants():
    assert cl.citations_match("§ 251(c)", "§251(c)")
    assert cl.citations_match("§ 251(c)", "Section 251(c)")
    assert cl.citations_match("8 Del. C. § 251", "8 Del. C. §251")
    assert not cl.citations_match("8 Del. C. § 251", "8 Del. C. § 271")


# ---------------------------------------------------------------------------
# Background proposer — failure modes + comparator outcomes.
# ---------------------------------------------------------------------------

def test_llm_timeout_emits_failed_annotation(monkeypatch):
    calls = _capture_annotate(monkeypatch)
    _patch_llm(monkeypatch, raises=asyncio.TimeoutError())
    asyncio.run(cl._run_llm_proposer_and_annotate(
        clause_text="...", tag="change_of_control",
        static_ref=_ref(), span_id="a" * 16,
    ))
    assert len(calls) == 1
    assert calls[0]["label"] == "linker_failed"
    assert calls[0]["score"] == 0.0
    assert calls[0]["name"] == "citation_linker_agreement"


def test_garbage_json_emits_failed_annotation_and_does_not_leak(monkeypatch):
    calls = _capture_annotate(monkeypatch)
    _patch_llm(monkeypatch, raises=json.JSONDecodeError("bad", "doc", 0))
    asyncio.run(cl._run_llm_proposer_and_annotate(
        clause_text="...", tag="mac", static_ref=_ref(), span_id="b" * 16,
    ))
    assert calls and calls[0]["label"] == "linker_failed"

    # The finding serialization never carries eval-only fields regardless.
    finding = RiskFinding(
        clause_id="x", clause_text="...", tag="mac", severity="block",
        judge_score=0.9, cited_spans=["x"], cited_spans_text="...",
        explanation="...", linker_agreement=False, linker_confidence=0.0,
    )
    dumped = finding.model_dump(mode="json", exclude=_EVAL_ONLY_FIELDS)
    assert not (_EVAL_ONLY_FIELDS & set(dumped))


def test_agreement_path_writes_agree(monkeypatch):
    calls = _capture_annotate(monkeypatch)
    # LLM agrees with the static map (same citation modulo punctuation + juris).
    _patch_llm(monkeypatch, returns=_proposal(citation="§ 251", conf=0.95))
    asyncio.run(cl._run_llm_proposer_and_annotate(
        clause_text="...", tag="change_of_control",
        static_ref=_ref(citation="Section 251"), span_id="c" * 16,
    ))
    assert calls and calls[0]["label"] == "agree"
    assert calls[0]["score"] == 1.0


def test_disagreement_path_writes_disagree(monkeypatch):
    calls = _capture_annotate(monkeypatch)
    _patch_llm(monkeypatch, returns=_proposal(citation="8 Del. C. § 271"))
    asyncio.run(cl._run_llm_proposer_and_annotate(
        clause_text="...", tag="change_of_control",
        static_ref=_ref(citation="8 Del. C. § 251"), span_id="d" * 16,
    ))
    assert calls and calls[0]["label"] == "disagree"
    assert calls[0]["score"] == 0.0


def test_no_static_path_writes_no_static(monkeypatch):
    calls = _capture_annotate(monkeypatch)
    _patch_llm(monkeypatch, returns=_proposal(citation="anything"))
    asyncio.run(cl._run_llm_proposer_and_annotate(
        clause_text="...", tag="accelerated_vesting",
        static_ref=None, span_id="e" * 16,
    ))
    assert calls and calls[0]["label"] == "no_static"


def test_sync_fallback_used_when_flush_incomplete(monkeypatch):
    """When force_flush did not complete (flushed=False), the annotation is
    written with sync=True via the Phoenix client directly — NOT via the async
    router._annotate path (hard constraint: don't lose the annotation to a
    span that may not have exported)."""
    # Fake phoenix.client capturing the sync kwarg.
    captured: list[dict] = []

    class _Spans:
        def add_span_annotation(self, **kw):
            captured.append(kw)

    class _Client:
        def __init__(self, *a, **k):
            self.spans = _Spans()

    mod = types.ModuleType("phoenix.client")
    mod.Client = _Client
    monkeypatch.setitem(sys.modules, "phoenix", types.ModuleType("phoenix"))
    monkeypatch.setitem(sys.modules, "phoenix.client", mod)

    # The async path must NOT be taken when sync.
    async_calls = _capture_annotate(monkeypatch)
    _patch_llm(monkeypatch, raises=asyncio.TimeoutError())

    asyncio.run(cl._run_llm_proposer_and_annotate(
        clause_text="...", tag="change_of_control",
        static_ref=_ref(), span_id="f" * 16, flushed=False,
    ))

    assert async_calls == [], "async _annotate must not run on the sync path"
    assert len(captured) == 1
    assert captured[0]["sync"] is True
    assert captured[0]["annotation_name"] == "citation_linker_agreement"
    assert captured[0]["label"] == "linker_failed"


# ---------------------------------------------------------------------------
# T1.2 — case-law normalisation (caption-keyed).
# ---------------------------------------------------------------------------

def test_case_law_long_vs_short_form_match():
    long = ("Akorn, Inc. v. Fresenius Kabi AG, 2018 WL 4719347 "
            "(Del. Ch. Oct. 1, 2018), aff'd, 198 A.3d 724 (Del. 2018)")
    short = "Akorn, Inc. v. Fresenius Kabi AG, 2018 WL 4719347 (Del. Ch. 2018)"
    assert cl.citations_match(long, short)
    assert cl.citations_match_kind(long, short) == "case_form"
    # AB Stable: map leads with the Chancery WL cite, gold with the Supreme
    # Court reporter — caption keying matches them regardless.
    ab_long = ("AB Stable VIII LLC v. MAPS Hotels & Resorts One LLC, "
               "2020 WL 7024929 (Del. Ch. Nov. 30, 2020), aff'd, 268 A.3d 198 (Del. 2021)")
    ab_short = "AB Stable VIII LLC v. MAPS Hotels & Resorts One LLC, 268 A.3d 198 (Del. 2021)"
    assert cl.citations_match(ab_long, ab_short)


def test_case_law_different_parties_do_not_match():
    a = "Akorn, Inc. v. Fresenius Kabi AG, 2018 WL 4719347 (Del. Ch. 2018)"
    b = "Revlon, Inc. v. MacAndrews & Forbes Holdings, Inc., 506 A.2d 173 (Del. 1986)"
    assert not cl.citations_match(a, b)
    assert cl.citations_match_kind(a, b) == "miss"


def test_statute_vs_case_never_match():
    assert not cl.citations_match("8 Del. C. § 251",
                                  "Revlon, Inc. v. MacAndrews & Forbes Holdings, Inc.")


# ---------------------------------------------------------------------------
# T1.2 — fail-closed jurisdiction lookup.
# ---------------------------------------------------------------------------

def test_lookup_fail_closed_returns_none_for_unmatched_jurisdiction():
    # non_compete exists ONLY for California; a New York hint must NOT fall
    # through to Cal. § 16600.
    assert cl.lookup_citation("non_compete", jurisdiction_hint="New York") is None
    # anti_assignment exists only under the UCC; a Delaware hint fails closed.
    assert cl.lookup_citation("anti_assignment", jurisdiction_hint="Delaware") is None


def test_lookup_california_required_for_section_16600():
    assert cl.lookup_citation("non_compete", jurisdiction_hint="California").citation \
        == "Cal. Bus. & Prof. Code § 16600"


def test_lookup_no_hint_returns_canonical_default():
    # No hint -> canonical (Delaware default) entry, NOT a fail-closed None.
    ref = cl.lookup_citation("change_of_control")
    assert ref is not None and ref.citation == "8 Del. C. § 251"


def test_lookup_ny_hint_selects_902_not_delaware():
    ref = cl.lookup_citation("change_of_control", jurisdiction_hint="New York")
    assert ref is not None
    assert ref.citation == "N.Y. Bus. Corp. Law § 902"
    assert ref.jurisdiction == "New York"


def test_map_contains_authority_for_tag():
    # § 271 is in the map for change_of_control (just not recall@1).
    assert cl.map_contains_authority_for_tag("change_of_control", "8 Del. C. § 271")
    # § 262 (appraisal) is NOT in the map for that tag.
    assert not cl.map_contains_authority_for_tag("change_of_control", "8 Del. C. § 262")


# ---------------------------------------------------------------------------
# T1.2 — normalize_jurisdiction pinned table.
# ---------------------------------------------------------------------------

def test_normalize_jurisdiction_table():
    assert cl.normalize_jurisdiction("governed by the laws of the State of New York") == "New York"
    assert cl.normalize_jurisdiction("the State of Delaware") == "Delaware"
    assert cl.normalize_jurisdiction("State of California") == "California"
    assert cl.normalize_jurisdiction("the Uniform Commercial Code") == "Uniform Commercial Code"
    assert cl.normalize_jurisdiction("federal law of the United States") == "Federal"
    # Unknown / ambiguous / empty -> None (caller must NOT silently default).
    assert cl.normalize_jurisdiction("the laws of England and Wales") is None
    assert cl.normalize_jurisdiction("") is None
    assert cl.normalize_jurisdiction(None) is None


def test_normalize_jurisdiction_only_returns_map_values():
    for text in ("Delaware", "New York", "California", "U.C.C.", "United States"):
        out = cl.normalize_jurisdiction(text)
        assert out is None or out in cl.MAP_JURISDICTIONS


# ---------------------------------------------------------------------------
# T1.2 — severity-gated case-law.
# ---------------------------------------------------------------------------

def test_severity_gate_block_keeps_case_law():
    akorn = cl.lookup_citation("mac")  # canonical mac entry is Akorn (case_law)
    assert akorn.citation_kind == "case_law"
    out = cl.severity_gated_citation(akorn, tag="mac", severity="block")
    assert out is akorn  # block findings keep the full case-law artillery


def test_severity_gate_watch_keeps_case_when_no_statute_fallback():
    # mac and exclusivity have ONLY case-law entries — a watch finding must KEEP
    # the case, NOT blank it to "no controlling statute".
    akorn = cl.lookup_citation("mac")
    out = cl.severity_gated_citation(akorn, tag="mac", severity="watch")
    assert out is not None and out.citation_kind == "case_law"
    revlon = cl.lookup_citation("exclusivity")
    out2 = cl.severity_gated_citation(revlon, tag="exclusivity", severity="info")
    assert out2 is not None and out2.citation_kind == "case_law"


def test_severity_gate_watch_drops_to_statute_when_one_exists():
    # change_of_control has a Delaware CASE (Trados) AND statutes (§ 251). If a
    # watch finding somehow resolved to the case, the gate drops to the statute.
    from agent.schemas import CitationRef
    from datetime import date
    trados = CitationRef(
        citation="In re Trados Inc. S'holder Litig., 73 A.3d 17 (Del. Ch. 2013)",
        citation_kind="case_law", jurisdiction="Delaware", rationale="x",
        verified_date=date(2026, 6, 9), primary_source="courts.delaware.gov",
    )
    out = cl.severity_gated_citation(trados, tag="change_of_control", severity="watch")
    assert out is not None and out.citation_kind == "statute"
    assert out.citation == "8 Del. C. § 251"


def test_severity_gate_none_passthrough():
    assert cl.severity_gated_citation(None, tag="mac", severity="watch") is None
