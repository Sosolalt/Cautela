"""Invariant tests for scripts/eval_cuad_spans.py.

Per Builder B's defensive priorities, these tests pin UNHAPPY-PATH
behaviors first. The most load-bearing tests are
`test_p_at_r_0_8_unachieved_flag_and_null` (kills the silent "report
precision at max recall as P@R=0.8=1.0" bug pattern) and
`test_p_at_r_tie_grouped_real_threshold_precision` (kills the silent
"report precision at an unachievable rank under tied confidences" bug).

Tests cover:
  1. Jaccard token-set normalization invariants (project + paper variants).
  2. Greedy 1-to-1 matching for both `match_spans` (strict >, project) and
     `match_spans_paper` (>=, punctuation-stripped, paper).
  3. P@R sweep:
       - Achievable + unachievable + tie-grouping (round-2 fix).
       - P@R=0.9 alongside P@R=0.8 (CUAD §3 reports both).
  4. Per-clause-type breakdown is required; CoC + Anti-Assignment never
     averaged into one number.
  5. Macro vs micro F1 reported separately for BOTH project (`f1_strict`)
     and paper (`f1_paper`) variants.
  6. AUPR (CUAD paper §3 primary metric).
  7. Baselines never hardcoded.
  8. `--limit N` (round-2 fix: CUAD's per-record clause-type fan-out
     made `--limit 1` return 2 examples).
  9. CUAD-QA SQuAD adapter (`_squad_rows_to_project_records`).
 10. Dynamic flag string (round-2 fix: was hardcoded "recall_0.8_unachieved").
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import eval_cuad_spans as M


# ---------------------------------------------------------------------------
# 1. Jaccard normalization invariants
# ---------------------------------------------------------------------------


def test_jaccard_identical_text_is_one():
    """Sanity baseline. Identical input must return 1.0 (not 0.999...)."""
    assert M.jaccard("the quick brown fox", "the quick brown fox") == 1.0


def test_jaccard_case_insensitive():
    """Lowercase normalization: "Yes" and "yes" must be equal token-set-wise.

    A future "preserve case for legal terms" refactor that removes
    .lower() would silently halve every match. Pin the contract."""
    assert M.jaccard("Change Of Control", "change of control") == 1.0


def test_jaccard_multi_space_collapses():
    """`str.split()` collapses runs of whitespace. A regex split on
    a single space would yield empty tokens for `"a  b"` → different
    token set. Pin the contract via `str.split()`."""
    assert M.jaccard("a b c", "a  b   c") == 1.0
    assert M.jaccard("a\tb\nc", "a b c") == 1.0


def test_jaccard_nfc_normalization():
    """Unicode NFC: a precomposed 'e-acute' (U+00E9) and a decomposed
    'e + combining acute' (U+0065 + U+0301) must normalize to the same
    string. Otherwise visually-identical spans drift apart in the token
    set and Jaccard quietly drops.

    Strings built via explicit \\u escapes so editor/tooling normalization
    can't accidentally collapse them at file-write time.
    """
    # "résumé" with precomposed é (U+00E9).
    precomposed = "r\u00e9sum\u00e9"
    # "résumé" with decomposed é (e + combining acute U+0301).
    decomposed = "re\u0301sume\u0301"
    # Sanity: they're not byte-identical without NFC.
    assert precomposed != decomposed
    assert M.jaccard(precomposed, decomposed) == 1.0

def test_jaccard_no_stop_word_removal():
    """No NLTK stop-word removal — "the" / "of" must remain in the token
    set so the score is deterministic across NLTK versions and Python
    environments."""
    assert M.jaccard("the contract", "the two contract") == pytest.approx(
        2.0 / 3.0, abs=1e-9
    )


def test_jaccard_no_stemming():
    """No stemming — "assignment" and "assigning" are distinct tokens.
    A Porter-stemmer revert would silently collapse them and inflate
    Jaccard."""
    j = M.jaccard("anti assignment", "anti assigning")
    assert j == pytest.approx(1.0 / 3.0, abs=1e-9)


def test_jaccard_punctuation_attached_to_token():
    """Project-Jaccard adversarial: punctuation is content. "consent,"
    and "consent" are distinct tokens. This is the DEFENSIVE choice
    pinned by plan §5.2.

    The Builder-B spec said: "the same span with different punctuation
    should still match >0.5". The way that holds in practice: the *rest
    of the span* carries the overlap. We pin that here.
    """
    a = "without the prior written consent of the company"
    b = "without the prior written consent, of the company."
    # See test_eval_cuad_spans_builder_b.py: token-set Jaccard = 5/9 ≈ 0.556.
    j = M.jaccard(a, b)
    assert j > 0.5
    assert j == pytest.approx(5.0 / 9.0, abs=1e-9)


def test_jaccard_empty_inputs_return_zero():
    """Both empty → 0.0 (not NaN, not 1.0)."""
    assert M.jaccard("", "") == 0.0
    assert M.jaccard("", "the contract") == 0.0
    assert M.jaccard("the contract", "") == 0.0


def test_jaccard_no_overlap_is_zero():
    assert M.jaccard("foo bar baz", "qux quux quuz") == 0.0


def test_jaccard_paper_strips_punctuation():
    """Paper-Jaccard (CUAD §3): punctuation stripped, so "consent" and
    "consent," collapse to the same token. With the project-Jaccard the
    same pair scores 5/9; with paper-Jaccard it scores 1.0."""
    a = "without the prior written consent of the company"
    b = "without the prior written consent, of the company."
    assert M.jaccard_paper(a, b) == pytest.approx(1.0, abs=1e-9)


def test_jaccard_paper_case_and_nfc_still_apply():
    """Paper-Jaccard still NFC-normalizes and lowercases."""
    assert M.jaccard_paper("Change Of Control", "change of control") == 1.0


# ---------------------------------------------------------------------------
# 2. Greedy matching invariants (project + paper)
# ---------------------------------------------------------------------------


def _pred(text: str, conf: float = 0.9, contract_id: str = "c", ct: str = "coc"):
    return M.CuadPredictedSpan(
        contract_id=contract_id,
        clause_type=ct,
        text=text,
        char_start=0,
        char_end=len(text),
        confidence=conf,
    )


def _gold(text: str, contract_id: str = "c", ct: str = "coc"):
    return M.CuadGoldSpan(
        contract_id=contract_id,
        clause_type=ct,
        text=text,
        char_start=0,
        char_end=len(text),
    )


def test_match_one_pred_consumes_one_gold():
    """One pred matched to its best gold; that gold is consumed and the
    next-best pred cannot also claim it."""
    preds = [_pred("the change of control event"), _pred("change of control")]
    golds = [_gold("the change of control event")]
    outcomes = M.match_spans(preds, golds)
    assert outcomes[0].matched_gold_idx == 0
    assert outcomes[1].matched_gold_idx is None


def test_match_threshold_strictly_above_half():
    """Project: Jaccard > 0.5. A pair scoring exactly 0.5 is UNMATCHED."""
    preds = [_pred("a b")]
    golds = [_gold("a b c d")]
    j = M.jaccard("a b", "a b c d")
    assert j == 0.5
    outcomes = M.match_spans(preds, golds)
    assert outcomes[0].matched_gold_idx is None
    assert outcomes[0].max_jaccard == pytest.approx(0.5, abs=1e-9)


def test_match_above_half_is_matched():
    """Strictly > 0.5 matches. 2/3 = 0.666... case."""
    preds = [_pred("a b")]
    golds = [_gold("a b c")]
    j = M.jaccard("a b", "a b c")
    assert j > 0.5
    outcomes = M.match_spans(preds, golds)
    assert outcomes[0].matched_gold_idx == 0


def test_match_empty_predictions_returns_empty():
    assert M.match_spans([], [_gold("any text")]) == []


def test_match_empty_gold_returns_all_unmatched():
    preds = [_pred("change of control"), _pred("anti assignment")]
    outcomes = M.match_spans(preds, [])
    assert all(o.matched_gold_idx is None for o in outcomes)


def test_match_paper_threshold_inclusive_half():
    """Paper-match uses >= 0.5 → exact 0.5 IS a match (project's strict >
    flips it to non-match). Pin the divergence."""
    preds = [_pred("a b")]
    golds = [_gold("a b c d")]
    j_paper = M.jaccard_paper("a b", "a b c d")
    assert j_paper == 0.5
    out_strict = M.match_spans(preds, golds)
    out_paper = M.match_spans_paper(preds, golds)
    assert out_strict[0].matched_gold_idx is None
    assert out_paper[0].matched_gold_idx == 0


# ---------------------------------------------------------------------------
# 3. P@R=0.8 — the LOAD-BEARING sweep (silent-failure killer)
# ---------------------------------------------------------------------------


def test_p_at_r_0_8_achievable():
    """4 of 5 golds matched at top-4 (under tie-grouping each confidence
    is unique). Recall first hits 0.8 at rank=4. Precision there = 4/4 = 1.0.
    """
    ranked = [
        (0.99, True),
        (0.95, True),
        (0.90, True),
        (0.85, True),
        (0.80, False),
    ]
    result = M.precision_at_recall(ranked, total_gold=5)
    assert result.flag is None
    assert result.p_at_r_0_8 == pytest.approx(1.0, abs=1e-9)
    assert result.rank_at_target == 4
    assert result.achieved_recall_max == pytest.approx(0.8, abs=1e-9)


def test_p_at_r_0_8_unachieved_flag_and_null():
    """THE most load-bearing test in the suite.

    Synthetic case where max recall = 0.6 (3 of 5 golds matched). P@R=0.8
    is UNREACHABLE. The function MUST:
      - return p_at_r_0_8 = None (NOT silently return precision at max recall)
      - set flag = FLAG_RECALL_UNACHIEVED
      - surface achieved_recall_max and p_at_achieved_max_recall
    """
    ranked = [
        (0.95, True),
        (0.90, True),
        (0.85, True),
        (0.80, False),
    ]
    result = M.precision_at_recall(ranked, total_gold=5)
    assert result.p_at_r_0_8 is None, (
        "CRITICAL: silent-failure bug — p_at_r_0_8 must be None when "
        "recall 0.8 is unreachable, not precision at max recall."
    )
    assert result.flag == M.FLAG_RECALL_UNACHIEVED
    assert result.achieved_recall_max == pytest.approx(0.6, abs=1e-9)
    assert result.p_at_achieved_max_recall == pytest.approx(1.0, abs=1e-9)
    assert result.rank_at_target is None


def test_p_at_r_0_8_empty_inputs_flag():
    """Empty ranked list → flag fires (target 0.8 is unreachable with 0 data)."""
    result = M.precision_at_recall([], total_gold=10)
    assert result.p_at_r_0_8 is None
    assert result.flag == M.FLAG_RECALL_UNACHIEVED


def test_p_at_r_0_8_zero_gold_flag():
    """No gold spans → recall is undefined; flag fires."""
    result = M.precision_at_recall([(0.9, False)], total_gold=0)
    assert result.p_at_r_0_8 is None
    assert result.flag == M.FLAG_RECALL_UNACHIEVED


def test_p_at_r_0_8_sort_is_descending_by_confidence():
    """DESC sort: high-confidence predictions admitted first."""
    ranked = [
        (0.10, False),
        (0.99, True),
        (0.95, True),
    ]
    result = M.precision_at_recall(ranked, total_gold=2)
    assert result.flag is None
    assert result.p_at_r_0_8 == pytest.approx(1.0, abs=1e-9)
    assert result.rank_at_target == 2


def test_p_at_r_0_8_exact_target_recall_lands_correctly():
    """Edge: recall hits exactly target_recall at some k. The smallest k
    where recall >= target_recall is the answer (the >= inequality).
    """
    ranked = (
        [(0.99 - 0.01 * i, True) for i in range(8)]
        + [(0.50, False), (0.40, False)]
    )
    result = M.precision_at_recall(ranked, total_gold=10)
    assert result.p_at_r_0_8 == pytest.approx(1.0, abs=1e-9)
    assert result.rank_at_target == 8


def test_p_at_r_tie_grouped_real_threshold_precision():
    """ROUND-2 LOAD-BEARING TEST: tie-grouping returns precision a real
    confidence threshold would actually achieve.

    Counter-example: ranked = [(0.9,T)]*3 + [(0.7,T),(0.7,F),(0.7,F),(0.7,F)],
    total_gold=4. Round-1 per-rank sweep with matches-first tie-break
    reported P=1.0 at rank=4 — but a caller deploying threshold 0.7
    admits ALL 4 ties, yielding P=4/7 ≈ 0.571.

    Tie-grouping reports the honest number.
    """
    ranked = [(0.9, True)] * 3 + [
        (0.7, True),
        (0.7, False),
        (0.7, False),
        (0.7, False),
    ]
    result = M.precision_at_recall(ranked, total_gold=4)
    # Recall 1.0 (4/4) achieved at conf=0.7 with 7 admitted → precision 4/7.
    assert result.p_at_r_0_8 == pytest.approx(4.0 / 7.0, abs=1e-9)
    assert result.rank_at_target == 7
    assert result.flag is None


def test_p_at_r_tie_grouped_recall_target_at_first_group():
    """At conf=0.9 the recall is 3/4=0.75 < 0.8, so it does NOT meet the
    target. Only at conf=0.7 with all 4 admitted does recall hit 1.0.
    The reported precision is from the conf=0.7 group, NOT the conf=0.9
    group."""
    ranked = [(0.9, True)] * 3 + [
        (0.7, True),
        (0.7, False),
    ]
    result = M.precision_at_recall(ranked, total_gold=4)
    # 4 matches / 5 admitted = 0.8.
    assert result.p_at_r_0_8 == pytest.approx(4.0 / 5.0, abs=1e-9)
    assert result.rank_at_target == 5


def test_p_at_r_0_9_separate_operating_point():
    """P@R=0.9 must be a separate, parameterized sweep result."""
    # 9 of 10 golds matched at high confidence, 1 non-match at low.
    ranked = [(0.99 - 0.01 * i, True) for i in range(9)] + [(0.10, False)]
    result_08 = M.precision_at_recall(ranked, total_gold=10, target_recall=0.8)
    result_09 = M.precision_at_recall(ranked, total_gold=10, target_recall=0.9)
    # 8/10 = 0.8 met at rank=8 with precision 1.0.
    assert result_08.p_at_r_0_8 == pytest.approx(1.0, abs=1e-9)
    assert result_08.rank_at_target == 8
    # 9/10 = 0.9 met at rank=9 with precision 1.0.
    assert result_09.p_at_r_0_8 == pytest.approx(1.0, abs=1e-9)
    assert result_09.rank_at_target == 9


def test_p_at_r_dynamic_flag_string():
    """Round-2 fix: flag is built from target_recall, not hardcoded 0.8."""
    result_08 = M.precision_at_recall([], total_gold=5, target_recall=0.8)
    result_09 = M.precision_at_recall([], total_gold=5, target_recall=0.9)
    assert result_08.flag == "recall_0.8_unachieved"
    assert result_09.flag == "recall_0.9_unachieved"


# ---------------------------------------------------------------------------
# 4. Per-clause-type breakdown — CoC vs Anti-Assignment never averaged
# ---------------------------------------------------------------------------


def _fixture_examples_and_preds():
    """2 contracts × 2 clause types (CoC + Anti-Assignment)."""
    examples = [
        M.CuadExample(
            contract_id="c1",
            contract_text="...",
            clause_type="change_of_control",
            gold_spans=(_gold("the change of control event", "c1", "change_of_control"),),
        ),
        M.CuadExample(
            contract_id="c1",
            contract_text="...",
            clause_type="anti_assignment",
            gold_spans=(_gold("without the prior written consent", "c1", "anti_assignment"),),
        ),
        M.CuadExample(
            contract_id="c2",
            contract_text="...",
            clause_type="change_of_control",
            gold_spans=(_gold("any change of control transfer", "c2", "change_of_control"),),
        ),
        M.CuadExample(
            contract_id="c2",
            contract_text="...",
            clause_type="anti_assignment",
            gold_spans=(_gold("no party may assign this agreement", "c2", "anti_assignment"),),
        ),
    ]
    predictions = {
        ("c1", "change_of_control"): [
            _pred("the change of control event", 0.95, "c1", "change_of_control")
        ],
        ("c1", "anti_assignment"): [
            _pred("entirely unrelated boilerplate text", 0.90, "c1", "anti_assignment")
        ],
        ("c2", "change_of_control"): [
            _pred("any change of control transfer", 0.92, "c2", "change_of_control")
        ],
        ("c2", "anti_assignment"): [
            _pred("no party may assign this agreement", 0.88, "c2", "anti_assignment")
        ],
    }
    return examples, predictions


def test_per_clause_type_breakdown_present_and_separate():
    """CoC and Anti-Assignment never averaged into one number."""
    examples, predictions = _fixture_examples_and_preds()
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    assert set(out["per_clause_type"].keys()) == {
        "change_of_control",
        "anti_assignment",
    }
    coc = out["per_clause_type"]["change_of_control"]
    aa = out["per_clause_type"]["anti_assignment"]
    # CoC: 2/2 → precision = recall = F1 = 1.0.
    assert coc["n_matched"] == 2
    assert coc["precision"] == 1.0
    assert coc["recall"] == 1.0
    assert coc["f1"] == 1.0
    # AA: 1 matched of 2 predicted, 1 of 2 gold → precision = recall = F1 = 0.5.
    assert aa["n_matched"] == 1
    assert aa["precision"] == pytest.approx(0.5, abs=1e-9)
    assert aa["recall"] == pytest.approx(0.5, abs=1e-9)
    assert aa["f1"] == pytest.approx(0.5, abs=1e-9)


def test_macro_and_micro_f1_both_reported_and_distinct():
    """Macro = mean(F1_coc, F1_aa) = (1.0 + 0.5) / 2 = 0.75.
    Micro = pooled: 3 matched / 4 predicted = 0.75."""
    examples, predictions = _fixture_examples_and_preds()
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    assert "macro_f1" in out
    assert "micro_f1" in out
    assert out["macro_f1"] == pytest.approx(0.75, abs=1e-9)
    assert out["micro_f1"] == pytest.approx(0.75, abs=1e-9)


def test_macro_and_micro_f1_diverge_when_clause_sizes_imbalanced():
    """Construct an imbalanced case so macro/micro DIVERGE — proves both
    values are computed independently."""
    examples = [
        M.CuadExample(
            contract_id="c1",
            contract_text="...",
            clause_type="change_of_control",
            gold_spans=(_gold("alpha", "c1", "change_of_control"),),
        ),
        M.CuadExample(
            contract_id="c1",
            contract_text="...",
            clause_type="anti_assignment",
            gold_spans=tuple(
                _gold(f"beta_g_{i}", "c1", "anti_assignment") for i in range(5)
            ),
        ),
    ]
    aa_preds = [_pred("beta_g_0", 0.99, "c1", "anti_assignment")]
    aa_preds.extend(
        _pred(f"unrelated_{i}", 0.95, "c1", "anti_assignment") for i in range(4)
    )
    predictions = {
        ("c1", "change_of_control"): [_pred("alpha", 0.99, "c1", "change_of_control")],
        ("c1", "anti_assignment"): aa_preds,
    }
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    macro = out["macro_f1"]
    micro = out["micro_f1"]
    assert macro == pytest.approx(0.6, abs=1e-9)
    assert micro == pytest.approx(2.0 / 6.0, abs=1e-9)
    assert abs(macro - micro) > 0.2


# ---------------------------------------------------------------------------
# 5. Paper-Jaccard side-by-side (`f1_strict` + `f1_paper`)
# ---------------------------------------------------------------------------


def test_f1_strict_and_paper_present_per_clause_type():
    """The summary surfaces BOTH `f1_strict` and `f1_paper` for every
    clause type. The two diverge when punctuation noise pushes a pair
    below the strict > 0.5 line but the paper's punctuation-strip pulls
    it back above (or to) >= 0.5."""
    # CoC: paper match (punctuation-strip pulls jaccard to 1.0) but strict
    # match also holds since the texts share enough tokens.
    # AA: pred="consent," gold="consent" → strict jaccard = 0 (different
    # token sets {consent,} vs {consent}) so it's unmatched under project;
    # paper-jaccard = 1.0 so it's matched.
    examples = [
        M.CuadExample(
            contract_id="c1",
            contract_text="...",
            clause_type="change_of_control",
            gold_spans=(_gold("change of control", "c1", "change_of_control"),),
        ),
        M.CuadExample(
            contract_id="c1",
            contract_text="...",
            clause_type="anti_assignment",
            gold_spans=(_gold("consent", "c1", "anti_assignment"),),
        ),
    ]
    predictions = {
        ("c1", "change_of_control"): [
            _pred("change of control", 0.9, "c1", "change_of_control")
        ],
        ("c1", "anti_assignment"): [
            _pred("consent,", 0.9, "c1", "anti_assignment")
        ],
    }
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    coc = out["per_clause_type"]["change_of_control"]
    aa = out["per_clause_type"]["anti_assignment"]
    # Both metrics shipped:
    assert "f1_strict" in coc and "f1_paper" in coc
    assert "f1_strict" in aa and "f1_paper" in aa
    # CoC: both = 1.0.
    assert coc["f1_strict"] == 1.0
    assert coc["f1_paper"] == 1.0
    # AA: strict = 0 (no match under > 0.5 with attached punctuation,
    # because "consent," and "consent" share zero tokens → jaccard 0).
    # Paper: 1.0 (punctuation stripped).
    assert aa["f1_strict"] == 0.0
    assert aa["f1_paper"] == pytest.approx(1.0, abs=1e-9)
    # Top-level macro_f1 paper differs from project:
    assert out["macro_f1"] == pytest.approx(0.5, abs=1e-9)
    assert out["macro_f1_paper"] == pytest.approx(1.0, abs=1e-9)


def test_micro_f1_paper_present_in_summary():
    """`micro_f1_paper` mirrors `micro_f1` shape."""
    examples, predictions = _fixture_examples_and_preds()
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    assert "micro_f1_paper" in out
    assert isinstance(out["micro_f1_paper"], float)


# ---------------------------------------------------------------------------
# 6. AUPR (CUAD paper §3 primary metric)
# ---------------------------------------------------------------------------


def test_aupr_perfect_ranking_is_one():
    """All matches at top → AUPR = 1.0 (the standard PR-curve identity)."""
    ranked = [(0.99 - 0.01 * i, True) for i in range(5)]
    assert M.compute_aupr(ranked, total_gold=5) == pytest.approx(1.0, abs=1e-9)


def test_aupr_no_matches_is_zero():
    """No positive labels → AUPR returns 0 (sklearn would emit NaN with
    a warning; we guard explicitly)."""
    ranked = [(0.9, False), (0.5, False)]
    assert M.compute_aupr(ranked, total_gold=3) == 0.0


def test_aupr_empty_inputs_zero():
    assert M.compute_aupr([], total_gold=0) == 0.0


def test_aupr_handworked_case():
    """Hand-computed: ranked=[(0.9,T),(0.8,F),(0.7,T)], total_gold=2.

    Sorted DESC by score: rank-1: precision 1/1=1.0, recall 1/2=0.5.
    rank-2: precision 1/2=0.5, recall 1/2=0.5.
    rank-3: precision 2/3, recall 2/2=1.0.
    sklearn `average_precision_score` returns sum over positives of
    (recall_k - recall_{k-1}) * precision_k:
      = (0.5 - 0) * 1.0 + (1.0 - 0.5) * 2/3
      = 0.5 + 0.5 * 0.6667 = 0.5 + 0.333... = 0.8333...
    """
    ranked = [(0.9, True), (0.8, False), (0.7, True)]
    expected = 0.5 * 1.0 + 0.5 * (2.0 / 3.0)
    assert M.compute_aupr(ranked, total_gold=2) == pytest.approx(expected, abs=1e-9)


def test_aupr_overall_in_summary():
    """`aupr_overall` is reported in the summary; per-clause `aupr` too."""
    examples, predictions = _fixture_examples_and_preds()
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    assert "aupr_overall" in out
    for ct in out["clause_types"]:
        assert "aupr" in out["per_clause_type"][ct]


# ---------------------------------------------------------------------------
# 7. P@R sweep inside run_eval — dataset-wide across clause types
# ---------------------------------------------------------------------------


def test_run_eval_p_at_r_dataset_wide_pool():
    """The P@R sweep MUST pool predictions across clause types."""
    examples, predictions = _fixture_examples_and_preds()
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    p = out["p_at_r_0_8"]
    assert p["total_gold"] == 4
    # 3 matches / 4 predictions. Confidences: 0.95, 0.92, 0.90 (unmatched
    # AA pred), 0.88. With tie-grouping the trajectory is:
    #   conf=0.95: matches=1, admit=1, recall=0.25, precision=1.0
    #   conf=0.92: matches=2, admit=2, recall=0.5,  precision=1.0
    #   conf=0.90: matches=2, admit=3, recall=0.5,  precision=0.667
    #   conf=0.88: matches=3, admit=4, recall=0.75, precision=0.75
    # 0.8 NOT reached. Flag fires.
    assert p["p_at_r_0_8"] is None
    assert p["flag"] == M.FLAG_RECALL_UNACHIEVED
    assert p["achieved_recall_max"] == pytest.approx(0.75, abs=1e-9)


def test_run_eval_emits_both_p_at_r_targets():
    """`p_at_r_0_8` and `p_at_r_0_9` both present in summary JSON."""
    examples, predictions = _fixture_examples_and_preds()
    summary = M.run_eval(examples, predictions)
    out = summary.to_json()
    assert "p_at_r_0_8" in out
    assert "p_at_r_0_9" in out
    # 0.9 target is also unreachable on this fixture.
    assert out["p_at_r_0_9"]["flag"] == "recall_0.9_unachieved"


# ---------------------------------------------------------------------------
# 8. Baselines never hardcoded
# ---------------------------------------------------------------------------


def test_load_baselines_none_returns_none():
    assert M.load_baselines(None) is None


def test_load_baselines_passthrough_to_summary():
    examples, predictions = _fixture_examples_and_preds()
    summary = M.run_eval(
        examples, predictions, comparison_baselines={"cuad-paper": 0.74}
    )
    assert summary.to_json()["comparison_baselines"] == {"cuad-paper": 0.74}


def test_load_baselines_rejects_non_dict_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([0.74]))
    with pytest.raises(ValueError, match="must be a JSON object"):
        M.load_baselines(p)


# ---------------------------------------------------------------------------
# 9. End-to-end main()
# ---------------------------------------------------------------------------


def _write_cuad_jsonl(tmp_path: Path, records: list[dict]) -> Path:
    p = tmp_path / "cuad.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec))
            fh.write("\n")
    return p


def test_main_default_uses_mock_agent(tmp_path):
    records = [
        {
            "contract_id": "c1",
            "contract_text": "the contract text...",
            "gold_spans": [
                {
                    "clause_type": "change_of_control",
                    "text": "the change of control event",
                    "char_start": 0,
                    "char_end": 27,
                },
                {
                    "clause_type": "anti_assignment",
                    "text": "without the prior written consent",
                    "char_start": 100,
                    "char_end": 133,
                },
            ],
        }
    ]
    p = _write_cuad_jsonl(tmp_path, records)
    out = tmp_path / "out.json"
    rc = M.main(["--dataset", str(p), "--out", str(out)])
    assert rc == 0
    summary = json.loads(out.read_text())
    assert summary["n_contracts"] == 1
    assert summary["macro_f1"] == 0.0
    assert summary["micro_f1"] == 0.0
    assert summary["p_at_r_0_8"]["flag"] == M.FLAG_RECALL_UNACHIEVED
    assert summary["p_at_r_0_8"]["p_at_r_0_8"] is None


def test_main_returns_2_on_empty_dataset(tmp_path):
    p = _write_cuad_jsonl(tmp_path, [])
    out = tmp_path / "out.json"
    rc = M.main(["--dataset", str(p), "--out", str(out)])
    assert rc == 2
    assert not out.exists()


def test_main_writes_per_clause_type_breakdown(tmp_path):
    records = [
        {
            "contract_id": "c1",
            "contract_text": "the contract text...",
            "gold_spans": [
                {
                    "clause_type": "change_of_control",
                    "text": "the change of control event",
                    "char_start": 0,
                    "char_end": 27,
                }
            ],
        }
    ]
    p = _write_cuad_jsonl(tmp_path, records)
    out = tmp_path / "out.json"
    rc = M.main(["--dataset", str(p), "--out", str(out)])
    assert rc == 0
    summary = json.loads(out.read_text())
    assert set(summary["per_clause_type"].keys()) == {
        "change_of_control",
        "anti_assignment",
    }


# ---------------------------------------------------------------------------
# 10. --limit semantics (round-2 fix: per-record clause-type fan-out
#     should NOT overshoot)
# ---------------------------------------------------------------------------


def test_limit_one_returns_exactly_one_example(tmp_path):
    """Round-1 bug: with default clause_types=(coc, aa), `--limit 1`
    returned 2 examples because the limit check ran AFTER the inner
    clause-type loop appended both. Round-2 contract: EXACTLY 1."""
    records = [
        {
            "contract_id": f"c{i}",
            "contract_text": "...",
            "gold_spans": [],
        }
        for i in range(3)
    ]
    p = _write_cuad_jsonl(tmp_path, records)
    examples = M.load_cuad_examples(p, limit=1)
    assert len(examples) == 1


def test_limit_three_with_two_clause_types(tmp_path):
    """K=2 clause types × any-many records, --limit 3 → EXACTLY 3."""
    records = [
        {
            "contract_id": f"c{i}",
            "contract_text": "...",
            "gold_spans": [],
        }
        for i in range(5)
    ]
    p = _write_cuad_jsonl(tmp_path, records)
    examples = M.load_cuad_examples(p, limit=3)
    assert len(examples) == 3


def test_limit_zero_returns_zero(tmp_path):
    records = [
        {"contract_id": "c1", "contract_text": "...", "gold_spans": []}
    ]
    p = _write_cuad_jsonl(tmp_path, records)
    examples = M.load_cuad_examples(p, limit=0)
    assert examples == []


# ---------------------------------------------------------------------------
# 11. CUAD-QA SQuAD adapter — schema reconstruction
# ---------------------------------------------------------------------------


def _squad_row(*, title: str, context: str, question: str, ans_texts: list[str], ans_starts: list[int]) -> dict:
    """Build a synthetic SQuAD-shaped CUAD-QA row."""
    return {
        "id": f"{title}__{question[:10]}",
        "title": title,
        "context": context,
        "question": question,
        "answers": {"text": list(ans_texts), "answer_start": list(ans_starts)},
    }


def test_squad_adapter_extracts_clause_phrase_from_question():
    """The question template `... 'Change Of Control' ...` resolves to
    the snake_case clause type `change_of_control`."""
    q = "Highlight the parts (if any) of this contract related to 'Change Of Control' that should be reviewed by a lawyer."
    phrase = M._extract_clause_phrase_from_question(q)
    assert phrase == "Change Of Control"
    assert M._normalize_clause_question_name(phrase) == "change_of_control"


def test_squad_adapter_anti_assignment_normalization():
    """'Anti-Assignment' → `anti_assignment`."""
    for phrase in ("Anti-Assignment", "anti-assignment", "Anti Assignment"):
        assert M._normalize_clause_question_name(phrase) == "anti_assignment"


def test_squad_adapter_unknown_clause_returns_none():
    """A clause type outside our default scope returns None (and the
    iterator skips that row)."""
    assert M._normalize_clause_question_name("License Grant") is None


def test_squad_adapter_emits_one_record_per_contract():
    """Multiple SQuAD rows for the same `title` collapse to one
    project-shaped record with gold_spans aggregated across questions."""
    rows = [
        _squad_row(
            title="MERGER-AGREEMENT-X",
            context="full contract text here with the change of control clause",
            question="Highlight ... 'Change Of Control' ... reviewed.",
            ans_texts=["the change of control"],
            ans_starts=[25],
        ),
        _squad_row(
            title="MERGER-AGREEMENT-X",
            context="full contract text here with the change of control clause",
            question="Highlight ... 'Anti-Assignment' ... reviewed.",
            ans_texts=["no party may assign"],
            ans_starts=[55],
        ),
    ]
    records = list(M._squad_rows_to_project_records(rows))
    assert len(records) == 1
    rec = records[0]
    assert rec["contract_id"] == "MERGER-AGREEMENT-X"
    assert rec["contract_text"].startswith("full contract text")
    span_types = sorted(s["clause_type"] for s in rec["gold_spans"])
    assert span_types == ["anti_assignment", "change_of_control"]
    # char_end = char_start + len(text).
    for span in rec["gold_spans"]:
        assert span["char_end"] == span["char_start"] + len(span["text"])


def test_squad_adapter_drops_unscoped_clauses():
    """Out-of-scope clause types (e.g. License Grant) are silently
    dropped — the resulting record contains no spans for them."""
    rows = [
        _squad_row(
            title="X",
            context="...",
            question="Highlight ... 'License Grant' ... reviewed.",
            ans_texts=["the licensee shall"],
            ans_starts=[10],
        ),
        _squad_row(
            title="X",
            context="...",
            question="Highlight ... 'Change Of Control' ... reviewed.",
            ans_texts=["the change"],
            ans_starts=[5],
        ),
    ]
    records = list(M._squad_rows_to_project_records(rows))
    assert len(records) == 1
    span_types = [s["clause_type"] for s in records[0]["gold_spans"]]
    assert span_types == ["change_of_control"]


def test_squad_adapter_handles_empty_answers():
    """A SQuAD row with empty `answers.text` (no annotated span) produces
    a record with zero gold spans for that contract — caller's
    responsibility to handle the empty case via the standard empty-gold
    invariant."""
    rows = [
        _squad_row(
            title="Y",
            context="contract text",
            question="Highlight ... 'Change Of Control' ... reviewed.",
            ans_texts=[],
            ans_starts=[],
        )
    ]
    records = list(M._squad_rows_to_project_records(rows))
    assert len(records) == 1
    assert records[0]["gold_spans"] == []


def test_squad_adapter_drops_rows_without_quoted_phrase():
    """A malformed question with no quoted clause phrase is dropped."""
    rows = [
        _squad_row(
            title="Y",
            context="contract text",
            question="What is this clause? It has no quoted phrase.",
            ans_texts=["foo"],
            ans_starts=[0],
        )
    ]
    records = list(M._squad_rows_to_project_records(rows))
    assert records == []


# ---------------------------------------------------------------------------
# 12. Live-agent immediate raise (round-2: MF-3-2 simplification)
# ---------------------------------------------------------------------------


def test_make_live_agent_returns_callable_without_adk():
    """`make_live_agent` now returns a working agent closure (the live path
    is wired). Construction must stay cheap and ADK-free — the google-adk
    import is deferred into the closure body — so this returns a callable
    without importing google-adk or touching Vertex. `--use-mock` remains
    the CLI default, so CI never invokes the closure (no quota burn)."""
    agent = M.make_live_agent()
    assert callable(agent)


def test_parse_live_spans_grounds_verbatim_and_drops_paraphrase():
    """`_parse_live_spans` grounds verbatim spans to char offsets and DROPS
    spans the model failed to copy verbatim (no fabricated offsets)."""
    contract = "Section 4.2. Upon a Change of Control, consent is required."
    raw = (
        '[{"text": "Change of Control", "confidence": 0.9}, '
        '{"text": "paraphrased not present", "confidence": 0.8}]'
    )
    spans = M._parse_live_spans(raw, contract)
    assert len(spans) == 1
    text, start, end, conf = spans[0]
    assert text == "Change of Control"
    assert contract[start:end] == "Change of Control"
    assert conf == 0.9


def test_parse_live_spans_strips_code_fence_and_tolerates_garbage():
    contract = "the anti-assignment clause forbids transfer"
    fenced = '```json\n[{"text": "anti-assignment", "confidence": 0.5}]\n```'
    spans = M._parse_live_spans(fenced, contract)
    assert len(spans) == 1 and spans[0][0] == "anti-assignment"
    # Malformed JSON / non-list payloads yield [] rather than raising.
    assert M._parse_live_spans("not json at all", contract) == []
    assert M._parse_live_spans('{"text": "x"}', contract) == []
