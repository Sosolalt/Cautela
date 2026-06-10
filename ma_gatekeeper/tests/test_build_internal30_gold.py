"""Tests for scripts/build_internal30_gold.py — the deterministic half of the
Internal-30 annotation pipeline.

The single most load-bearing invariant is the offset invariant: every grounded
span must satisfy `contract_text[char_start:char_end] == text` against the raw
EDGAR .txt, even when the agent "cleaned" the quote (collapsed NBSP/narrow-NBSP
and hard-wrap newlines, ASCII-ized curly quotes). These tests pin that the
flexible regex grounder recovers the ORIGINAL substring (never a guessed
offset), that ungroundable paraphrases are dropped, and that the A↔B aligner
buckets spans the way the master spec §6 prescribes.
"""
from __future__ import annotations

import pytest

from scripts.build_internal30_gold import (
    GoldSpan,
    align_passes,
    char_jaccard,
    derive_clause_id,
    ground_pass,
    ground_span,
)

# A miniature "contract" carrying every adversarial character the real EDGAR
# files contain: U+00A0 (NBSP), U+202F (narrow NBSP), curly quotes, an em dash,
# and a hard-wrap newline mid-sentence.
CONTRACT = (
    "ARTICLE IX\n\n"
    "9.3  Assignment.\n"
    "No Party may “assign” either this Agreement or any of its rights,\n"
    "interests, or obligations hereunder—without the prior written approval "
    "of the other Parties.\n\n"
    "9.4 Notices. Any notice shall be in writing.\n"
)


def test_ground_span_exact_substring():
    quote = "No Party may"
    start, end = ground_span(quote, CONTRACT)
    assert CONTRACT[start:end] == quote


def test_ground_span_recovers_through_cleaned_whitespace_and_quotes():
    # An agent quote that collapsed the newline + NBSP to single spaces and
    # turned the curly quotes/em dash into ASCII. The grounder must still land
    # on the ORIGINAL substring so the offset invariant holds against the .txt.
    agent_quote = (
        'No Party may "assign" either this Agreement or any of its rights, '
        "interests, or obligations hereunder-without the prior written approval "
        "of the other Parties."
    )
    located = ground_span(agent_quote, CONTRACT)
    assert located is not None
    start, end = located
    recovered = CONTRACT[start:end]
    # The stored text is the ORIGINAL .txt substring (curly quotes, em dash,
    # NBSP and newline intact), NOT the agent's cleaned quote.
    assert "“assign”" in recovered
    assert "—" in recovered
    assert " " in recovered
    assert "\n" in recovered


def test_ground_span_drops_paraphrase():
    # Words that are not a verbatim subsequence -> no offset is invented.
    assert ground_span("the parties shall not transfer this contract", CONTRACT) is None
    assert ground_span("", CONTRACT) is None


def test_derive_clause_id_uses_section_number():
    idx = CONTRACT.index("No Party")
    assert derive_clause_id(CONTRACT, idx, "No Party may") == "9.3"
    # A span before any section heading falls back to a stable hash.
    cid = derive_clause_id(CONTRACT, 0, "ARTICLE IX")
    assert cid.startswith("h")


def test_ground_pass_enforces_offset_invariant_and_dedup():
    raw = {
        "deal": [
            {
                "clause_id": "9.3",
                # cleaned quote — still groundable
                "span_text": "No Party may \"assign\" either this Agreement",
                "suggested_tag": "anti_assignment",
                "suggested_severity": "watch",
                "confidence": 0.8,
                "trigger_language": "No Party may",
                "explanation": "non-assignment",
            },
            {
                # exact duplicate offset+tag, lower confidence -> dropped by dedup
                "clause_id": "9.3",
                "span_text": "No Party may “assign” either this Agreement",
                "suggested_tag": "anti_assignment",
                "suggested_severity": "watch",
                "confidence": 0.5,
                "trigger_language": "No Party may",
                "explanation": "dup",
            },
            {
                # ungroundable paraphrase -> dropped, counted
                "clause_id": "x",
                "span_text": "the parties shall not transfer this contract",
                "suggested_tag": "anti_assignment",
                "suggested_severity": "info",
                "confidence": 0.9,
                "trigger_language": "transfer",
                "explanation": "para",
            },
        ]
    }
    spans, reports = ground_pass(raw, {"deal": CONTRACT})
    # one survivor (the higher-confidence of the dup pair); the paraphrase dropped
    assert len(spans) == 1
    span = spans[0]
    assert CONTRACT[span.char_start : span.char_end] == span.text  # invariant
    assert span.confidence == 0.8
    assert span.clause_id == "9.3"
    assert reports[0].dropped == 1
    assert reports[0].grounded == 1


def test_multitag_same_offset_survives_as_distinct_rows():
    raw = {
        "deal": [
            {
                "clause_id": "9.3", "span_text": "No Party may",
                "suggested_tag": "anti_assignment", "suggested_severity": "watch",
                "confidence": 0.8, "trigger_language": "assign", "explanation": "x",
            },
            {
                "clause_id": "9.3", "span_text": "No Party may",
                "suggested_tag": "change_of_control", "suggested_severity": "watch",
                "confidence": 0.7, "trigger_language": "assign", "explanation": "deemed",
            },
        ]
    }
    spans, _ = ground_pass(raw, {"deal": CONTRACT})
    assert {s.suggested_tag for s in spans} == {"anti_assignment", "change_of_control"}


def _gs(start, end, tag, sev="watch", conf=0.8):
    return GoldSpan("deal", "9.3", CONTRACT[start:end], start, end, tag, sev, conf, "", "")


def test_align_buckets_agree_disagree_solo():
    a0 = _gs(40, 80, "anti_assignment")
    b0 = _gs(42, 82, "anti_assignment")  # >0.5 char overlap, same tag -> agree
    a1 = _gs(40, 80, "change_of_control")
    b1 = _gs(42, 82, "mac")  # overlap but different tag -> tag_disagreement
    solo = _gs(120, 160, "exclusivity")  # only in A
    res_agree = align_passes([a0], [b0], {"deal": CONTRACT})
    assert res_agree["counts"]["agree"] == 1
    res_dis = align_passes([a1], [b1], {"deal": CONTRACT})
    assert res_dis["counts"]["tag_disagreement"] == 1
    res_solo = align_passes([solo], [], {"deal": CONTRACT})
    assert res_solo["counts"]["solo_a"] == 1


def test_char_jaccard():
    a = _gs(0, 100, "mac")
    b = _gs(50, 150, "mac")
    assert char_jaccard(a, b) == pytest.approx(50 / 150)
    assert char_jaccard(a, _gs(200, 300, "mac")) == 0.0
