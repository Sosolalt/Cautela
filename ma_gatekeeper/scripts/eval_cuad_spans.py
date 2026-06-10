"""CUAD span-extraction evaluation (plan §5.2 + §12).

Headline numbers for the README three-track eval table:
  - Token-level F1 (per plan §5.2: Jaccard>0.5 match → token-F1).
  - P@R=0.8 + P@R=0.9 (precision at the specified recall across the
    dataset-wide confidence-thresholded ranking; CUAD paper §3 reports
    BOTH operating points).
  - AUPR (area under the precision-recall curve — CUAD paper's primary
    headline metric per §3).

Plan §5.2 explicitly scopes this to "CUAD-Spans for CoC + Anti-Assignment"
(Change-of-Control + Anti-Assignment). Per-clause-type breakdown is
non-negotiable — averaging the two into one number hides per-clause
performance. We report both macro-F1 (per-clause-type mean) and micro-F1
(pooled across clause types).

PROJECT vs PAPER metrics — shipped side-by-side
-----------------------------------------------
- Project Jaccard semantics (plan §5.2): tokens are whitespace-split,
  NFC-normalized, lowercased, **punctuation NOT stripped**, match
  threshold is strictly `> 0.5`. F1 reported per clause type as
  `f1_strict`.
- Paper Jaccard semantics (CUAD paper §3): tokens are
  whitespace-split, NFC-normalized, lowercased, **punctuation stripped**,
  match threshold is `>= 0.5`. F1 reported per clause type as
  `f1_paper`. The CUAD paper reports F1 numbers under this preprocessor.

We compute BOTH so the JSON is comparable to the paper AND defends the
project-pinned strictness invariant (the `f1_strict` test pins document
the punctuation-attached property; see test_jaccard_punctuation_attached
in the test file).

DEFENSIVE INVARIANTS PINNED BY THIS SCRIPT (and locked by
tests/test_eval_cuad_spans.py):

  1. Jaccard token-set normalization:
       tokens = whitespace-split + Unicode-NFC-normalized + lowercased.
       NO stop-word removal (introduces non-determinism).
       NO stemming.
     Adversarial cases (same span with different punctuation) still match
     above 0.5. See test_jaccard_punctuation_robust.

  2. Token-level F1 via Jaccard>0.5 match definition (plan §5.2):
       For each gold span, find the predicted span with maximum Jaccard.
       If max Jaccard > 0.5, the predicted span is "matched"; else unmatched.
       Each predicted span can match at most one gold span (greedy by
       descending Jaccard) to prevent one high-confidence prediction
       "matching" three golds and inflating recall.
       Precision = matched_predicted / total_predicted.
       Recall = matched_gold / total_gold.
       F1 = harmonic mean.

  3. P@R=0.8 sweep semantics:
       - Sort all (prediction, gold-or-noise) pairs across the WHOLE dataset
         by predicted confidence DESCENDING.
       - At each rank k:
           precision = (# matches in top-k) / k
           recall = (# matches in top-k) / (total gold spans across dataset)
       - Smallest k with recall >= 0.8 → P@R=0.8 = precision at that k.
       - If recall never reaches 0.8, DO NOT silently report the precision
         at max recall and call it P@R=0.8. Instead:
           * p_at_r_0_8 = None
           * achieved_recall_max = the actual max recall
           * p_at_achieved_max_recall = precision at that point
           * flag = "recall_0.8_unachieved"
       This is the most load-bearing test in the suite — see
       test_p_at_r_0_8_unachieved_flag_and_null.

  4. Per-clause-type breakdown is required. CoC and Anti-Assignment are
     reported separately AND as macro/micro aggregates.

Usage:
  # Default: deterministic mock — no Vertex quota burn.
  python -m scripts.eval_cuad_spans \\
      --dataset data/cuad --out cuad_spans_eval.json

  # Live agent (opt-in):
  python -m scripts.eval_cuad_spans --live \\
      --dataset data/cuad --out cuad_spans_eval.json
"""
from __future__ import annotations

import argparse
import functools
import json
import logging
import statistics
import sys
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

_LOG = logging.getLogger(__name__)

# CUAD CoC + Anti-Assignment are the two clause types the plan commits to.
# Keep this list authoritative — adding clause types means an explicit
# plan-level decision, not a silent CLI flag flip.
DEFAULT_CLAUSE_TYPES: tuple[str, ...] = ("change_of_control", "anti_assignment")

P_AT_R_TARGET_RECALL = 0.8  # plan §5.2 headline operating point
P_AT_R_TARGET_RECALL_PAPER = 0.9  # CUAD paper §3 also reports P@R=0.9
JACCARD_MATCH_THRESHOLD = 0.5  # plan §5.2: "Jaccard > 0.5 match definition"
JACCARD_MATCH_THRESHOLD_PAPER = 0.5  # paper §3 uses >= 0.5 (see match_spans_paper)


def _flag_recall_unachieved(target_recall: float) -> str:
    """Build the unachieved-recall flag dynamically.

    Hardcoding `"recall_0.8_unachieved"` would mislead callers who pass
    a different `target_recall`. We render the actual target into the
    flag string so a `target_recall=0.9` call surfaces `recall_0.9_unachieved`.
    """
    return f"recall_{target_recall}_unachieved"


# Back-compat alias: tests reference `M.FLAG_RECALL_UNACHIEVED`. This evaluates
# at the default target_recall (0.8). For non-default targets the
# `precision_at_recall` function emits the dynamic flag directly.
FLAG_RECALL_UNACHIEVED = _flag_recall_unachieved(P_AT_R_TARGET_RECALL)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CuadGoldSpan:
    """One human-annotated gold span on a contract."""

    contract_id: str
    clause_type: str
    text: str
    char_start: int
    char_end: int


@dataclass(frozen=True)
class CuadPredictedSpan:
    """One agent-emitted predicted span on a contract."""

    contract_id: str
    clause_type: str
    text: str
    char_start: int
    char_end: int
    confidence: float


@dataclass(frozen=True)
class CuadExample:
    """One contract + its gold spans of a single clause type.

    NOTE: CUAD contracts have gold spans for multiple clause types; this
    eval scopes to (CoC, Anti-Assignment). One CuadExample = one
    (contract, clause_type) pair. Empty `gold_spans` is LEGAL — it means
    "this contract has no spans of this clause type" — and is handled by
    treating any prediction on it as a false positive.
    """

    contract_id: str
    contract_text: str
    clause_type: str
    gold_spans: tuple[CuadGoldSpan, ...]


# ---------------------------------------------------------------------------
# Jaccard — the pinned normalization
# ---------------------------------------------------------------------------


def _normalize_tokens(text: str) -> frozenset[str]:
    """The PROJECT-pinned token-set normalization (plan §5.2 Jaccard).

    - Unicode NFC normalization (so visually-identical text with different
      code-point encodings collapses to the same token set).
    - Lowercased.
    - Whitespace-split (NO punctuation stripping; punctuation attached to
      a token like "consent," remains "consent," — adversarial cases that
      strip punctuation are why we test with .strip() done by the caller
      explicitly, not silently).

    NO stop-word removal (would let "the" / "of" drift the score across
    NLTK versions). NO stemming (would conflate "assigning" and "assign"
    and falsely inflate Jaccard).

    Returns a frozenset (hashable, deduplicates across multi-occurrence
    tokens — Jaccard is set-based by definition).
    """
    nfc = unicodedata.normalize("NFC", text)
    lowered = nfc.lower()
    # `str.split()` with no argument collapses any run of whitespace.
    return frozenset(lowered.split())


# Translation table that strips ASCII punctuation. CUAD paper §3 explicitly
# strips punctuation before tokenisation; we mirror that exactly.
_PAPER_PUNCT_STRIPPER = str.maketrans(
    "", "", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
)


def _normalize_tokens_paper(text: str) -> frozenset[str]:
    """PAPER-pinned token-set normalization (CUAD paper §3).

    Same NFC + lowercase as the project normalizer, then strips ASCII
    punctuation before whitespace-splitting. "consent," and "consent."
    both collapse to "consent". This is intentionally LESS strict than
    the project normalizer so the published paper number is reproducible.
    """
    nfc = unicodedata.normalize("NFC", text)
    lowered = nfc.lower()
    stripped = lowered.translate(_PAPER_PUNCT_STRIPPER)
    return frozenset(stripped.split())


def jaccard(a: str, b: str) -> float:
    """Project Jaccard (plan §5.2 normalization).

    Returns 0.0 when either input normalizes to an empty set — the
    alternative (NaN or 1.0) would silently corrupt downstream max()
    operations.
    """
    sa = _normalize_tokens(a)
    sb = _normalize_tokens(b)
    if not sa and not sb:
        return 0.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return float(inter) / float(union)


def jaccard_paper(a: str, b: str) -> float:
    """Paper Jaccard (CUAD §3 normalization: punctuation stripped).

    Same shape as `jaccard` but uses the paper's tokenizer. Reported
    alongside the project number; never substituted for it.
    """
    sa = _normalize_tokens_paper(a)
    sb = _normalize_tokens_paper(b)
    if not sa and not sb:
        return 0.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return float(inter) / float(union)


# ---------------------------------------------------------------------------
# Matching — greedy by descending Jaccard so each pred matches at most one gold
# ---------------------------------------------------------------------------


@dataclass
class MatchOutcome:
    """One predicted span's matching outcome."""

    pred_idx: int
    matched_gold_idx: int | None  # None when unmatched
    max_jaccard: float


def _match_spans_impl(
    predicted: list[CuadPredictedSpan],
    gold: list[CuadGoldSpan],
    *,
    score_fn: "Any",
    threshold: float,
    strict_inequality: bool,
) -> list[MatchOutcome]:
    """Generic greedy 1-to-1 matcher; shared by `match_spans` and
    `match_spans_paper`.

    `score_fn(text_a, text_b) -> float` computes the similarity score per
    each path's normalization. `strict_inequality=True` means
    `score > threshold` (project semantics); `False` means
    `score >= threshold` (paper semantics).
    """
    if not predicted:
        return []

    triples: list[tuple[float, int, int]] = []
    for pi, p in enumerate(predicted):
        for gi, g in enumerate(gold):
            triples.append((float(score_fn(p.text, g.text)), pi, gi))

    triples.sort(key=lambda t: (-t[0], t[1], t[2]))

    consumed_pred: set[int] = set()
    consumed_gold: set[int] = set()
    pred_match: dict[int, tuple[int, float]] = {}

    for jac, pi, gi in triples:
        if pi in consumed_pred or gi in consumed_gold:
            continue
        # Threshold check: project uses strict `>`, paper uses `>=`.
        is_match = jac > threshold if strict_inequality else jac >= threshold
        if not is_match:
            break  # remaining are all <= current jac, none can match
        consumed_pred.add(pi)
        consumed_gold.add(gi)
        pred_match[pi] = (gi, jac)

    pred_max_jac: dict[int, float] = {}
    for pi in range(len(predicted)):
        max_j = 0.0
        for jac, ppi, _gi in triples:
            if ppi == pi and jac > max_j:
                max_j = jac
        pred_max_jac[pi] = max_j

    outcomes: list[MatchOutcome] = []
    for pi in range(len(predicted)):
        if pi in pred_match:
            gi, jac = pred_match[pi]
            outcomes.append(
                MatchOutcome(pred_idx=pi, matched_gold_idx=gi, max_jaccard=jac)
            )
        else:
            outcomes.append(
                MatchOutcome(
                    pred_idx=pi,
                    matched_gold_idx=None,
                    max_jaccard=pred_max_jac[pi],
                )
            )
    return outcomes


def match_spans(
    predicted: list[CuadPredictedSpan],
    gold: list[CuadGoldSpan],
) -> list[MatchOutcome]:
    """Greedy 1-to-1 matching by descending project-Jaccard.

    For each (pred, gold) cross-pair, compute Jaccard. Sort pairs DESC,
    greedily consume — once a pred or gold is consumed it's locked. A
    pred whose best-available gold scores <= JACCARD_MATCH_THRESHOLD is
    UNMATCHED (counts as a false positive).

    Project semantics: strictly `> 0.5` (plan §5.2) and punctuation
    NOT stripped.

    Returns one MatchOutcome per predicted span (preserving input order).
    """
    return _match_spans_impl(
        predicted,
        gold,
        score_fn=jaccard,
        threshold=JACCARD_MATCH_THRESHOLD,
        strict_inequality=True,
    )


def match_spans_paper(
    predicted: list[CuadPredictedSpan],
    gold: list[CuadGoldSpan],
) -> list[MatchOutcome]:
    """Greedy 1-to-1 matching by descending paper-Jaccard.

    CUAD paper §3 semantics: punctuation stripped, threshold `>= 0.5`.
    Shipped alongside `match_spans` so both numbers are computable.
    """
    return _match_spans_impl(
        predicted,
        gold,
        score_fn=jaccard_paper,
        threshold=JACCARD_MATCH_THRESHOLD_PAPER,
        strict_inequality=False,
    )


# ---------------------------------------------------------------------------
# Per-clause-type F1 + dataset-wide P@R=0.8 sweep
# ---------------------------------------------------------------------------


@dataclass
class ClauseTypeMetrics:
    """Per-clause-type aggregate."""

    clause_type: str
    n_examples: int
    n_predicted: int
    n_gold: int
    n_matched: int
    precision: float
    recall: float
    f1: float


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_clause_type_metrics(
    examples: list[CuadExample],
    predictions: dict[tuple[str, str], list[CuadPredictedSpan]],
    clause_type: str,
) -> tuple[ClauseTypeMetrics, list[tuple[float, bool]]]:
    """Compute per-clause-type PROJECT metrics + ranked (confidence, is_match).

    Project semantics (plan §5.2): strict `> 0.5` Jaccard, punctuation
    attached. Returns:
      - ClauseTypeMetrics (precision, recall, F1 for this clause type).
      - A list of (confidence, is_match) tuples — every predicted span
        across all contracts for this clause type, with `is_match` true
        iff the prediction was matched to a gold by `match_spans`.

    The ranked list is what feeds the dataset-wide P@R sweep below.
    """
    n_predicted = 0
    n_matched = 0
    n_gold = 0
    ranked: list[tuple[float, bool]] = []
    n_examples = 0

    for ex in examples:
        if ex.clause_type != clause_type:
            continue
        n_examples += 1
        preds = predictions.get((ex.contract_id, ex.clause_type), [])
        gold_list = list(ex.gold_spans)
        n_gold += len(gold_list)
        n_predicted += len(preds)
        outcomes = match_spans(preds, gold_list)
        for out in outcomes:
            is_match = out.matched_gold_idx is not None
            ranked.append((preds[out.pred_idx].confidence, is_match))
            if is_match:
                n_matched += 1

    precision = float(n_matched) / n_predicted if n_predicted else 0.0
    # Recall: matched_gold / total_gold (each matched outcome consumes one
    # distinct gold, so n_matched == matched_gold count).
    recall = float(n_matched) / n_gold if n_gold else 0.0
    f1 = _f1(precision, recall)
    return (
        ClauseTypeMetrics(
            clause_type=clause_type,
            n_examples=n_examples,
            n_predicted=n_predicted,
            n_gold=n_gold,
            n_matched=n_matched,
            precision=precision,
            recall=recall,
            f1=f1,
        ),
        ranked,
    )


def compute_clause_type_metrics_paper(
    examples: list[CuadExample],
    predictions: dict[tuple[str, str], list[CuadPredictedSpan]],
    clause_type: str,
) -> ClauseTypeMetrics:
    """Same as `compute_clause_type_metrics` but with PAPER Jaccard semantics.

    CUAD paper §3 semantics: punctuation stripped, threshold `>= 0.5`.
    Used to compute `f1_paper` alongside `f1_strict`.
    """
    n_predicted = 0
    n_matched = 0
    n_gold = 0
    n_examples = 0

    for ex in examples:
        if ex.clause_type != clause_type:
            continue
        n_examples += 1
        preds = predictions.get((ex.contract_id, ex.clause_type), [])
        gold_list = list(ex.gold_spans)
        n_gold += len(gold_list)
        n_predicted += len(preds)
        outcomes = match_spans_paper(preds, gold_list)
        for out in outcomes:
            if out.matched_gold_idx is not None:
                n_matched += 1

    precision = float(n_matched) / n_predicted if n_predicted else 0.0
    recall = float(n_matched) / n_gold if n_gold else 0.0
    f1 = _f1(precision, recall)
    return ClauseTypeMetrics(
        clause_type=clause_type,
        n_examples=n_examples,
        n_predicted=n_predicted,
        n_gold=n_gold,
        n_matched=n_matched,
        precision=precision,
        recall=recall,
        f1=f1,
    )


@dataclass
class PrecisionAtRecallResult:
    """P@R sweep output.

    When the target recall is unachievable across the dataset,
    `p_at_r_0_8` is None and `flag` carries the dynamic
    `recall_{target}_unachieved` string. Callers MUST inspect `flag`
    before using `p_at_r_0_8` — silently returning the precision at
    max recall is the exact bug pattern this dataclass shape prevents.

    NOTE: the field name `p_at_r_0_8` is kept for back-compat with the
    round-1 JSON schema. For non-default targets the field holds the
    precision at the requested target (the name is unfortunate but the
    schema contract is now external).
    """

    target_recall: float
    total_gold: int
    p_at_r_0_8: float | None
    achieved_recall_max: float
    p_at_achieved_max_recall: float
    rank_at_target: int | None
    flag: str | None


def precision_at_recall(
    ranked_pairs: list[tuple[float, bool]],
    total_gold: int,
    *,
    target_recall: float = P_AT_R_TARGET_RECALL,
) -> PrecisionAtRecallResult:
    """Dataset-wide P@R=target sweep with confidence-tie grouping.

    Tie-grouping is the load-bearing fix in round 2: at any real
    confidence threshold a caller would actually deploy, ALL predictions
    at that confidence are admitted together. A per-rank traversal that
    arbitrarily orders ties (matches-first) reports an operating point
    that NO real threshold can achieve. Instead we accumulate by UNIQUE
    confidence level: for each level, add every (match + non-match) at
    that level, then test the recall inequality. Precision at the
    accumulation point is what an honest deployer would see.

    Hand-checked counter-example pinned in `test_p_at_r_tie_grouped_*`:
      ranked = [(0.9,T)]*3 + [(0.7,T),(0.7,F),(0.7,F),(0.7,F)], total_gold=4.
      Per-rank (round-1) reported precision=1.0 at rank=4. Tie-grouped
      (round-2) reports precision=4/7 ≈ 0.571 at conf=0.7 — the precision
      a caller deploying threshold 0.7 actually sees.

    Empty inputs / zero gold: returns p_at_r=None with flag set (the
    target is unreachable with zero data).
    """
    target_flag = _flag_recall_unachieved(target_recall)
    if total_gold == 0 or not ranked_pairs:
        return PrecisionAtRecallResult(
            target_recall=target_recall,
            total_gold=total_gold,
            p_at_r_0_8=None,
            achieved_recall_max=0.0,
            p_at_achieved_max_recall=0.0,
            rank_at_target=None,
            flag=target_flag,
        )

    # Sort DESC by confidence; secondary order within a confidence is
    # irrelevant because we group ties before evaluating the inequality.
    pairs = sorted(ranked_pairs, key=lambda t: -t[0])

    matches_so_far = 0
    admitted_so_far = 0
    best_recall = 0.0
    best_recall_precision = 0.0
    rank_at_target: int | None = None
    p_at_target: float | None = None

    # Walk by unique confidence; admit all pairs at that level before
    # testing the recall target.
    i = 0
    n = len(pairs)
    while i < n:
        j = i
        # Float equality is OK here — pairs come from the same upstream
        # source list; we're not comparing recomputed floats.
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        # Admit the whole tie group.
        for k in range(i, j):
            if pairs[k][1]:
                matches_so_far += 1
            admitted_so_far += 1
        precision = matches_so_far / admitted_so_far if admitted_so_far else 0.0
        recall = matches_so_far / total_gold
        if recall > best_recall:
            best_recall = recall
            best_recall_precision = precision
        # First (smallest-admitted-so-far) confidence level meeting the
        # target recall is the operating point.
        if rank_at_target is None and recall >= target_recall:
            rank_at_target = admitted_so_far
            p_at_target = precision
        i = j

    if rank_at_target is None:
        return PrecisionAtRecallResult(
            target_recall=target_recall,
            total_gold=total_gold,
            p_at_r_0_8=None,
            achieved_recall_max=best_recall,
            p_at_achieved_max_recall=best_recall_precision,
            rank_at_target=None,
            flag=target_flag,
        )
    return PrecisionAtRecallResult(
        target_recall=target_recall,
        total_gold=total_gold,
        p_at_r_0_8=p_at_target,
        achieved_recall_max=best_recall,
        p_at_achieved_max_recall=best_recall_precision,
        rank_at_target=rank_at_target,
        flag=None,
    )


# ---------------------------------------------------------------------------
# AUPR — CUAD paper's primary headline metric
# ---------------------------------------------------------------------------


def compute_aupr(
    ranked_pairs: list[tuple[float, bool]],
    total_gold: int,
) -> float:
    """Area under the precision-recall curve from confidence-thresholded preds.

    Uses sklearn's `average_precision_score` which implements the standard
    step-wise integral. Returns 0.0 when no positive labels exist (sklearn
    would otherwise emit a runtime warning and return NaN).

    `total_gold` is included in the signature to mirror `precision_at_recall`
    but does not affect AUPR itself — sklearn computes AP only over the
    predicted set; recall against missing gold is handled by the
    `precision_at_recall` machinery instead.
    """
    if not ranked_pairs:
        return 0.0
    y_true = [1 if m else 0 for _, m in ranked_pairs]
    if sum(y_true) == 0:
        return 0.0
    y_score = [float(c) for c, _ in ranked_pairs]
    from sklearn.metrics import average_precision_score  # type: ignore

    return float(average_precision_score(y_true, y_score))


# ---------------------------------------------------------------------------
# Aggregate eval output
# ---------------------------------------------------------------------------


@dataclass
class CuadEvalSummary:
    """Headline summary for the README results table.

    Carries BOTH project (plan §5.2) and paper (CUAD §3) metric variants:
      - `macro_f1` / `micro_f1`: project metric (strict > 0.5,
        punctuation attached).
      - `macro_f1_paper` / `micro_f1_paper`: paper metric (>= 0.5,
        punctuation stripped).
      - `per_clause_type[ct]["f1_strict"]` and `["f1_paper"]` carry the
        per-clause-type variants.
      - `p_at_r_0_8` (existing): P@R=0.8 sweep result (project semantics).
      - `p_at_r_0_9`: P@R=0.9 sweep result (CUAD paper §3 also reports this).
      - `aupr_overall` + per-clause-type `aupr`: area under PR curve
        per CUAD paper §3.
    """

    n_examples: int
    n_contracts: int
    clause_types: tuple[str, ...]
    per_clause_type: dict[str, dict[str, Any]] = field(default_factory=dict)
    macro_f1: float = 0.0
    micro_f1: float = 0.0
    # Paper-metric variants (CUAD §3).
    macro_f1_paper: float = 0.0
    micro_f1_paper: float = 0.0
    p_at_r_0_8: dict[str, Any] = field(default_factory=dict)
    p_at_r_0_9: dict[str, Any] = field(default_factory=dict)
    aupr_overall: float = 0.0
    comparison_baselines: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "n_examples": self.n_examples,
            "n_contracts": self.n_contracts,
            "clause_types": list(self.clause_types),
            "per_clause_type": self.per_clause_type,
            "macro_f1": self.macro_f1,
            "micro_f1": self.micro_f1,
            "macro_f1_paper": self.macro_f1_paper,
            "micro_f1_paper": self.micro_f1_paper,
            "p_at_r_0_8": self.p_at_r_0_8,
            "p_at_r_0_9": self.p_at_r_0_9,
            "aupr_overall": self.aupr_overall,
            "comparison_baselines": self.comparison_baselines,
        }


def _p_at_r_to_json(p_at_r: PrecisionAtRecallResult) -> dict[str, Any]:
    """Render PrecisionAtRecallResult to the JSON-output shape."""
    return {
        "target_recall": p_at_r.target_recall,
        "total_gold": p_at_r.total_gold,
        "p_at_r_0_8": p_at_r.p_at_r_0_8,
        "achieved_recall_max": p_at_r.achieved_recall_max,
        "p_at_achieved_max_recall": p_at_r.p_at_achieved_max_recall,
        "rank_at_target": p_at_r.rank_at_target,
        "flag": p_at_r.flag,
    }


def run_eval(
    examples: list[CuadExample],
    predictions: dict[tuple[str, str], list[CuadPredictedSpan]],
    *,
    clause_types: tuple[str, ...] = DEFAULT_CLAUSE_TYPES,
    comparison_baselines: dict[str, Any] | None = None,
) -> CuadEvalSummary:
    """Run the full CUAD-Spans eval — per-clause-type F1 + dataset-wide P@R + AUPR.

    `predictions` is keyed by (contract_id, clause_type) so each
    (contract, clause_type) example pairs with its corresponding
    predictions. A missing key is treated as "no predictions for this
    pair" — predictions for clause types outside `clause_types` are
    ignored.

    Computes BOTH project metrics (plan §5.2 strict Jaccard) and paper
    metrics (CUAD §3 punctuation-stripped Jaccard) side-by-side.
    """
    per_clause: dict[str, dict[str, Any]] = {}
    all_ranked: list[tuple[float, bool]] = []
    total_gold_all = 0
    total_matched_all = 0
    total_predicted_all = 0
    per_clause_f1s_strict: list[float] = []
    per_clause_f1s_paper: list[float] = []
    total_matched_paper_all = 0
    total_predicted_paper_all = 0
    total_gold_paper_all = 0

    for ct in clause_types:
        # Project metrics (strict Jaccard).
        metrics, ranked = compute_clause_type_metrics(examples, predictions, ct)
        # Paper metrics (punctuation-stripped Jaccard).
        metrics_paper = compute_clause_type_metrics_paper(
            examples, predictions, ct
        )
        # Per-clause-type AUPR (CUAD paper §3).
        clause_aupr = compute_aupr(ranked, metrics.n_gold)
        per_clause[ct] = {
            "n_examples": metrics.n_examples,
            "n_predicted": metrics.n_predicted,
            "n_gold": metrics.n_gold,
            "n_matched": metrics.n_matched,
            "precision": metrics.precision,
            "recall": metrics.recall,
            # Round-1 field; kept for back-compat.
            "f1": metrics.f1,
            # Round-2 explicit labels:
            "f1_strict": metrics.f1,
            "f1_paper": metrics_paper.f1,
            "precision_paper": metrics_paper.precision,
            "recall_paper": metrics_paper.recall,
            "n_matched_paper": metrics_paper.n_matched,
            "aupr": clause_aupr,
        }
        all_ranked.extend(ranked)
        total_gold_all += metrics.n_gold
        total_matched_all += metrics.n_matched
        total_predicted_all += metrics.n_predicted
        per_clause_f1s_strict.append(metrics.f1)
        per_clause_f1s_paper.append(metrics_paper.f1)
        total_matched_paper_all += metrics_paper.n_matched
        total_predicted_paper_all += metrics_paper.n_predicted
        total_gold_paper_all += metrics_paper.n_gold

    macro_f1 = (
        statistics.fmean(per_clause_f1s_strict) if per_clause_f1s_strict else 0.0
    )
    macro_f1_paper = (
        statistics.fmean(per_clause_f1s_paper) if per_clause_f1s_paper else 0.0
    )
    micro_p = (
        float(total_matched_all) / total_predicted_all
        if total_predicted_all
        else 0.0
    )
    micro_r = (
        float(total_matched_all) / total_gold_all if total_gold_all else 0.0
    )
    micro_f1 = _f1(micro_p, micro_r)
    micro_p_paper = (
        float(total_matched_paper_all) / total_predicted_paper_all
        if total_predicted_paper_all
        else 0.0
    )
    micro_r_paper = (
        float(total_matched_paper_all) / total_gold_paper_all
        if total_gold_paper_all
        else 0.0
    )
    micro_f1_paper = _f1(micro_p_paper, micro_r_paper)

    # Dataset-wide sweep at both target recall operating points.
    p_at_r_08 = precision_at_recall(
        all_ranked, total_gold_all, target_recall=P_AT_R_TARGET_RECALL
    )
    p_at_r_09 = precision_at_recall(
        all_ranked,
        total_gold_all,
        target_recall=P_AT_R_TARGET_RECALL_PAPER,
    )
    aupr_overall = compute_aupr(all_ranked, total_gold_all)

    n_contracts = len({ex.contract_id for ex in examples})
    return CuadEvalSummary(
        n_examples=len(examples),
        n_contracts=n_contracts,
        clause_types=tuple(clause_types),
        per_clause_type=per_clause,
        macro_f1=macro_f1,
        micro_f1=micro_f1,
        macro_f1_paper=macro_f1_paper,
        micro_f1_paper=micro_f1_paper,
        p_at_r_0_8=_p_at_r_to_json(p_at_r_08),
        p_at_r_0_9=_p_at_r_to_json(p_at_r_09),
        aupr_overall=aupr_overall,
        comparison_baselines=comparison_baselines,
    )


# ---------------------------------------------------------------------------
# Agent interface — mock-injectable per spec
# ---------------------------------------------------------------------------


class _AgentFn(Protocol):
    """Callable contract: (contract_text, clause_type) -> list of predicted spans.

    Returns a list of (text, char_start, char_end, confidence) tuples. The
    Runner wrapper around `build_root_agent()` is the default impl; tests
    pass deterministic mocks. CLI `--use-mock` (default) and `--live` flags
    control which path runs.
    """

    def __call__(
        self, contract_text: str, clause_type: str
    ) -> list[tuple[str, int, int, float]]: ...


def make_mock_agent(seed: int = 42) -> _AgentFn:
    """Deterministic mock — emits zero spans regardless of input.

    Useful for shape-only smoke testing. Tests that want non-trivial
    behavior provide their own mock; this default is intentionally
    boring so accidental CI runs don't pretend to have real predictions.
    Returns an empty list so the script reports "0 matches, 0 predictions"
    rather than fabricating outputs.
    """
    del seed  # unused; kept in signature so the CLI seed flag is wireable

    def _agent(
        contract_text: str, clause_type: str
    ) -> list[tuple[str, int, int, float]]:
        return []

    return _agent


# Length-preserving Unicode fold for span grounding (Fix #3). EVERY entry MUST
# be a single code point -> single code point so that char offsets are IDENTICAL
# between the original text and the folded text. Do NOT add multi-char mappings
# (e.g. "…"->"...", ligature "ﬁ"->"fi", or whitespace-run collapse): they shift
# offsets and could ground a span at the wrong position. Tested by
# test_norm_for_match_is_length_preserving.
_MATCH_FOLD: dict[int, str] = {
    0x00A0: " ",  # non-breaking space
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",  # single quotes
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',  # double quotes
    0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-",  # figure/en/em/horiz dashes
}
_MATCH_TABLE = str.maketrans(_MATCH_FOLD)


def _norm_for_match(s: str) -> str:
    """1-codepoint->1-codepoint fold (see `_MATCH_FOLD`); `len()` is invariant.

    Used only to RECOVER a span's char offset when the model emitted a
    typographically-cleaned variant (curly quote / nbsp / dash) of text that
    is genuinely present in the contract. The grounded span text is always the
    ORIGINAL contract substring, never this folded form.
    """
    return s.translate(_MATCH_TABLE)


def _parse_live_spans(
    raw: str, contract_text: str
) -> list[tuple[str, int, int, float]]:
    """Parse a model's JSON span list and ground each span in the contract.

    Expected model output is a JSON array of objects:
        [{"text": "<verbatim span>", "confidence": 0.0..1.0}, ...]

    No-fabrication policy:
      - Markdown code fences (```json ... ```) are stripped before parsing.
      - A span is grounded by an exact `str.find`; if that misses, by a
        length-preserving Unicode fold (`_norm_for_match`) that recovers spans
        the model "cleaned" (curly quotes / nbsp / dashes -> ASCII). A span
        located by neither is DROPPED (counted, never assigned a guessed
        offset) — a fabricated offset would be worse than a miss.
      - The grounded span text is the ORIGINAL contract substring at the found
        offset, so `contract_text[start:end] == text` holds for the caller.
      - Malformed JSON or a non-list payload yields `[]`.
    Offsets use the FIRST occurrence after folding; CUAD scoring is
    Jaccard-over-char-ranges, for which first-occurrence is the standard choice.
    """
    import json
    import re

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []

    folded_contract: str | None = None  # lazily folded; only if a fast-path miss
    n_dropped = 0
    out: list[tuple[str, int, int, float]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        span_text = item.get("text")
        if not isinstance(span_text, str) or not span_text:
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        start = contract_text.find(span_text)
        if start < 0:
            # Fast path missed — try the length-preserving fold so a model that
            # cleaned a curly quote / nbsp / dash still grounds correctly.
            if folded_contract is None:
                folded_contract = _norm_for_match(contract_text)
            start = folded_contract.find(_norm_for_match(span_text))
        # The fold is 1:1, so the matched region width == len(span_text).
        end = start + len(span_text)
        if start < 0 or end > len(contract_text):
            n_dropped += 1
            continue
        # Store the ORIGINAL contract substring (not the model's cleaned text)
        # so the char-offset invariant holds downstream.
        out.append((contract_text[start:end], start, end, confidence))
    if n_dropped:
        _LOG.debug("_parse_live_spans dropped %d ungrounded span(s)", n_dropped)
    return out


_CLAUSE_DEFINITIONS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "cuad_clause_definitions.json"
)


@functools.lru_cache(maxsize=1)
def _load_clause_definitions() -> dict[str, str]:
    """Load the dataset-derived CUAD `Details:` clause definitions (Fix #1).

    These are the verbatim `Details:` strings from the CUAD-QA question field —
    the canonical CUAD input the published baselines are queried with — pinned
    in `data/cuad_clause_definitions.json` and regenerated by
    `scripts/refresh_cuad_definitions.py`. A missing/unreadable file yields {}
    so the eval degrades to the bare-label prompt rather than crashing.
    """
    try:
        payload = json.loads(_CLAUSE_DEFINITIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    defs = payload.get("definitions", {})
    return {str(k): str(v) for k, v in defs.items()} if isinstance(defs, dict) else {}


# Multi-pass / chunked extraction tunables (Fixes #2 + #4).
_LIVE_MAX_OUTPUT_TOKENS = 8192  # avoid truncating long span lists (cheap recall lever)
_DEDUP_IOU = 0.5  # NMS overlap threshold for de-duplicating predictions
_SWEEP_CONF_DISCOUNT = 0.9  # recall-sweep spans ranked strictly below pass-1


def _build_extract_instruction(clause_type: str, definition: str) -> str:
    """Pass-1 / per-chunk extraction instruction (shared by every pass)."""
    def_block = (
        f"\nThe CUAD definition of this clause type is: {definition}\n"
        if definition
        else "\n"
    )
    return (
        "You are an expert M&A attorney extracting clauses from a "
        "commercial contract. Extract every span of text that is an "
        f"instance of the clause type '{clause_type}'."
        f"{def_block}"
        "Favor RECALL: return EVERY distinct span that plausibly matches — "
        "all occurrences, definitions, and related sub-clauses — even if "
        "similar; a human reviewer prunes false positives downstream.\n"
        "Return ONLY a JSON array. Each element must be an object: "
        '{"text": "<the span copied EXACTLY, character-for-character, '
        'from the contract>", "confidence": <float between 0 and 1>}.\n'
        "Copy each span verbatim so it can be located in the source "
        "text. If no such clause exists, return an empty array []."
    )


def _build_sweep_instruction(
    clause_type: str, definition: str, found: list[str]
) -> str:
    """Fix #4 recall-sweep instruction — coverage, not echo.

    Lists what pass-1 already found and asks ONLY for spans not already
    covered (and not substrings of them), focusing on later/un-quoted
    sections, so the model does genuine coverage work rather than re-emitting.
    """
    def_block = f" (CUAD definition: {definition})" if definition else ""
    already = "\n".join(f"- {t}" for t in found) if found else "(none)"
    return (
        "You are an expert M&A attorney doing a SECOND-PASS recall check on a "
        f"contract for the clause type '{clause_type}'{def_block}.\n"
        "These spans were already found in the first pass:\n"
        f"{already}\n"
        "Find ADDITIONAL spans that were MISSED — especially in later sections "
        "of the contract. A new span must NOT duplicate or be a substring of an "
        "already-found span. If there are none, return [].\n"
        "Return ONLY a JSON array of "
        '{"text": "<verbatim span>", "confidence": <0..1>} objects.'
    )


def _chunk_text(text: str, window: int, overlap: int) -> list[str]:
    """Slice `text` into overlapping windows of `window` chars (Fix #2).

    Returns the whole text as a single chunk when it fits. Raises ValueError on
    a non-advancing config (`overlap >= window`), which would otherwise loop
    forever. The last window reaches the final character exactly once (no
    duplicate trailing chunk).
    """
    if window <= 0:
        raise ValueError(f"window must be positive (got {window})")
    if overlap >= window:
        raise ValueError(f"overlap ({overlap}) must be < window ({window})")
    if not text:
        return []
    if len(text) <= window:
        return [text]
    stride = window - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + window])
        if start + window >= len(text):
            break
        start += stride
    return chunks


def _char_iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Intersection-over-union of two [start, end) char intervals."""
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    if inter == 0:
        return 0.0
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union else 0.0


def _dedup_spans(
    spans: list[tuple[str, int, int, float]],
) -> list[tuple[str, int, int, float]]:
    """Non-max suppression over predicted spans (Fixes #2 + #4).

    Sorts by confidence desc and greedily keeps a span unless it overlaps an
    already-kept span by char-IoU > `_DEDUP_IOU`. The kept span is the original
    higher-confidence one VERBATIM — we never merge/union boundaries (that would
    fabricate a span neither model nor gold emitted and could flip the 0.5
    Jaccard match). This collapses chunk-overlap and sweep duplicates so they
    don't erode precision as a stride artifact; the greedy 1:1 `match_spans`
    already prevents duplicates from inflating recall.
    """
    kept: list[tuple[str, int, int, float]] = []
    # Sort by confidence desc, then by (start, end) for a deterministic winner
    # among equal-confidence overlaps (no reliance on input iteration order).
    for span in sorted(spans, key=lambda s: (-s[3], s[1], s[2])):
        rng = (span[1], span[2])
        if any(_char_iou(rng, (k[1], k[2])) > _DEDUP_IOU for k in kept):
            continue
        kept.append(span)
    return kept


def make_live_agent(
    *,
    chunk_size: int | None = None,
    chunk_overlap: int = 4000,
    recall_sweep: bool = False,
) -> _AgentFn:
    """Live CUAD span-extraction agent backed by a Vertex `LlmAgent`.

    Extraction passes — all OFF by default (each multiplies Vertex calls, and
    the published baselines are single-pass, so multi-pass numbers are NOT
    apples-to-apples and must be disclosed in the README):
      - Fix #1: the canonical CUAD `Details:` definition + a high-recall prompt.
      - Fix #2 (`chunk_size`): split long contracts into overlapping windows and
        extract per window, so the model attends to every section instead of
        losing recall mid-document. Spans ground against the FULL contract.
      - Fix #4 (`recall_sweep`): a second "what was missed" pass whose spans are
        ranked strictly below pass-1 (so the P@R curve stays honest).
    All passes merge through `_dedup_spans` (NMS — no boundary fabrication).

    Construction is cheap and ADK-free (google-adk imports live in the closure),
    so importing this module / constructing the agent in tests needs no Vertex.
    """

    definitions = _load_clause_definitions()

    def _extract(
        contract_text: str, view_text: str, instruction: str
    ) -> list[tuple[str, int, int, float]]:
        # Lazy import keeps module import + test construction ADK-free.
        from scripts._live_agent import run_single_agent

        raw = run_single_agent(
            instruction,
            f"=== CONTRACT ===\n{view_text}",
            agent_name="cuad_spans",
            max_output_tokens=_LIVE_MAX_OUTPUT_TOKENS,
        )
        # Ground every span against the FULL contract, never the window.
        return _parse_live_spans(raw, contract_text)

    def _agent(
        contract_text: str, clause_type: str
    ) -> list[tuple[str, int, int, float]]:
        definition = definitions.get(clause_type, "")
        extract_instruction = _build_extract_instruction(clause_type, definition)

        # --- Pass 1: single call, or per-chunk for long contracts (Fix #2) ---
        if chunk_size and len(contract_text) > chunk_size:
            spans: list[tuple[str, int, int, float]] = []
            for chunk in _chunk_text(contract_text, chunk_size, chunk_overlap):
                spans.extend(_extract(contract_text, chunk, extract_instruction))
        else:
            spans = _extract(contract_text, contract_text, extract_instruction)
        spans = _dedup_spans(spans)

        # --- Pass 2: recall sweep (Fix #4), ranked strictly below pass-1 -----
        if recall_sweep:
            found_texts = [s[0] for s in spans]
            sweep_instruction = _build_sweep_instruction(
                clause_type, definition, found_texts
            )
            sweep = _extract(contract_text, contract_text, sweep_instruction)
            # Echo guard: drop sweep spans that are substrings of a pass-1 span.
            # Conservative echo guard: drop a sweep span contained in a pass-1
            # span (costs a little recall, never precision — sweep spans are
            # low-value by design).
            sweep = [s for s in sweep if not any(s[0] in f for f in found_texts)]
            # Rank sweep spans strictly below EVERY pass-1 span, so they can only
            # raise the achieved-recall ceiling, never game P@R. Scale each into
            # [0, floor) via floor * discount; when floor == 0 (a pass-1 span the
            # model marked 0-confidence) there is no room below, so sweep spans
            # sit at 0 — tied at the very bottom of the ranking, which cannot
            # inflate precision at any higher-recall threshold.
            floor = min((s[3] for s in spans), default=0.5)
            scale = floor * _SWEEP_CONF_DISCOUNT  # in [0, floor)
            sweep = [
                (t, a, b, max(0.0, min(c, 1.0)) * scale)
                for (t, a, b, c) in sweep
            ]
            spans = _dedup_spans(spans + sweep)

        return spans

    return _agent


def predictions_from_agent(
    examples: list[CuadExample], agent: _AgentFn
) -> dict[tuple[str, str], list[CuadPredictedSpan]]:
    """Run the agent over every (contract, clause_type) example.

    Returns the dict shape `run_eval` expects.
    """
    out: dict[tuple[str, str], list[CuadPredictedSpan]] = {}
    for ex in examples:
        raw_spans = agent(ex.contract_text, ex.clause_type)
        out[(ex.contract_id, ex.clause_type)] = [
            CuadPredictedSpan(
                contract_id=ex.contract_id,
                clause_type=ex.clause_type,
                text=text,
                char_start=int(start),
                char_end=int(end),
                confidence=float(conf),
            )
            for (text, start, end, conf) in raw_spans
        ]
    return out


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def load_cuad_examples(
    dataset_path: Path | str,
    *,
    clause_types: tuple[str, ...] = DEFAULT_CLAUSE_TYPES,
    limit: int | None = None,
    split: str | None = "test",
) -> list[CuadExample]:
    """Load CUAD examples from a HuggingFace `save_to_disk` dir OR JSONL.

    Each record yields one CuadExample per clause type the record covers
    (so a contract with both CoC and Anti-Assignment annotations produces
    two examples). The HF path reads the actual `theatticusproject/cuad-qa`
    SQuAD schema and reconstructs project-shaped records via
    `_squad_record_to_project_record`.

    `--limit N` returns AT MOST N examples, counted at the per-example
    grain (i.e. one (contract, clause_type) per increment). The round-1
    version checked the limit only after the inner clause-type loop had
    appended K examples, so `--limit 1` with K=2 clause types returned 2.
    """
    path = Path(dataset_path)
    if path.is_dir():
        records = list(_iter_hf_cuad(path, split=split))
    elif path.suffix == ".jsonl":
        records = list(_iter_jsonl_cuad(path))
    else:
        raise FileNotFoundError(
            f"CUAD dataset path {path!r} is neither a HF save_to_disk dir "
            "nor a .jsonl file."
        )

    examples: list[CuadExample] = []
    limit_hit = False
    for rec in records:
        if limit_hit:
            break
        spans_by_type: dict[str, list[CuadGoldSpan]] = {}
        for s in rec.get("gold_spans", []):
            ct = s["clause_type"]
            spans_by_type.setdefault(ct, []).append(
                CuadGoldSpan(
                    contract_id=str(rec["contract_id"]),
                    clause_type=str(ct),
                    text=str(s["text"]),
                    char_start=int(s["char_start"]),
                    char_end=int(s["char_end"]),
                )
            )
        for ct in clause_types:
            # Check the limit BEFORE appending so `--limit N` returns
            # EXACTLY N examples regardless of the clause-types fan-out.
            if limit is not None and len(examples) >= limit:
                limit_hit = True
                break
            examples.append(
                CuadExample(
                    contract_id=str(rec["contract_id"]),
                    contract_text=str(rec["contract_text"]),
                    clause_type=ct,
                    gold_spans=tuple(spans_by_type.get(ct, [])),
                )
            )
    return examples


def _iter_jsonl_cuad(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


# CUAD paper phrasing → snake_case clause-type keys we use internally.
# These two are the plan-pinned defaults. Extending requires updating
# DEFAULT_CLAUSE_TYPES too; the matcher is intentionally explicit.
_CUAD_QUESTION_TO_CLAUSE_TYPE: dict[str, str] = {
    "change of control": "change_of_control",
    "anti-assignment": "anti_assignment",
    "anti assignment": "anti_assignment",
}


def _normalize_clause_question_name(name: str) -> str | None:
    """Normalize a CUAD question's clause phrase to our snake_case key.

    CUAD-QA questions are templated like:
      "Highlight the parts (if any) of this contract related to
       'Change Of Control' that should be reviewed by a lawyer."
    The quoted phrase varies across CUAD's 41 clause types. We
    normalize the quoted phrase to lowercase and look it up in
    `_CUAD_QUESTION_TO_CLAUSE_TYPE`. Returns None for clause types
    outside our default scope (the CUAD-QA file covers many more
    than CoC + Anti-Assignment; we filter at load time).
    """
    key = name.strip().lower()
    return _CUAD_QUESTION_TO_CLAUSE_TYPE.get(key)


def _extract_clause_phrase_from_question(question: str) -> str | None:
    """Extract the quoted clause phrase from a CUAD-QA question string.

    Looks for the substring between the first pair of straight or curly
    quotes. Returns None on no quote pair (defensive — surfacing the
    None lets the caller skip rather than guess).
    """
    # Try straight quotes first, then curly.
    for left, right in (("'", "'"), ('"', '"'), ("‘", "’"), ("“", "”")):
        if left in question:
            li = question.index(left)
            try:
                ri = question.index(right, li + 1)
            except ValueError:
                continue
            phrase = question[li + 1 : ri].strip()
            if phrase:
                return phrase
    return None


def _extract_definition_from_question(question: str) -> str:
    """Return the CUAD `Details:` clause definition from a question, else "".

    CUAD-QA questions are templated `Highlight ... related to "<label>" that
    should be reviewed by a lawyer. Details: <definition>`. The definition is
    constant per clause type. Returns the text after the first `Details:`
    marker, stripped; "" if the marker is absent (e.g. JSONL fixtures).
    """
    marker = "Details:"
    idx = question.find(marker)
    if idx < 0:
        return ""
    return question[idx + len(marker):].strip()


def _iter_hf_cuad(path: Path, split: str | None = "test") -> Iterator[dict[str, Any]]:
    """Lazy-import `datasets`; bypassed in tests via JSONL fixtures.

    The HF `theatticusproject/cuad-qa` dataset is in SQuAD format with `train`
    and `test` splits. We evaluate the **`test` split ONLY** by default —
    pooling train+test (the prior behavior) silently contaminated the eval with
    training contracts. `split=None` restores the pooled behavior for callers
    that explicitly want it.
    """
    from datasets import load_from_disk  # type: ignore

    ds = load_from_disk(str(path))
    if hasattr(ds, "items"):
        if split is None:
            chosen: dict[str, Iterable[dict]] = dict(ds.items())
        elif split in ds:
            chosen = {split: ds[split]}
        else:
            _LOG.warning(
                "CUAD split %r not found (have %s); falling back to all splits.",
                split,
                list(ds.keys()),
            )
            chosen = dict(ds.items())
    else:
        chosen = {"_single": ds}
    squad_rows: list[dict[str, Any]] = []
    for name, sp in chosen.items():
        for rec in sp:
            row = dict(rec)
            row["_split"] = name
            squad_rows.append(row)
    yield from _squad_rows_to_project_records(squad_rows)


def _squad_rows_to_project_records(
    rows: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Reconstruct project-shaped CUAD records from CUAD-QA SQuAD rows.

    SQuAD row shape (per WebFetch of `theatticusproject/cuad-qa`):
        {
          "id": "<contract>__Document_Name__0",
          "title": "PFIZER-SEAGEN-MERGER-AGREEMENT",
          "context": "<contract text>",
          "question": "Highlight the parts ... 'Change Of Control' ...",
          "answers": {"text": ["..."], "answer_start": [123]}
        }

    We group by `title` (= contract id), parse clause_type from the
    question, and emit one project-shaped record per contract:
        {
          "contract_id": "PFIZER-SEAGEN-MERGER-AGREEMENT",
          "contract_text": "<context>",
          "gold_spans": [
              {"clause_type": "change_of_control", "text": "...",
               "char_start": 123, "char_end": 145}, ...
          ]
        }

    Rows whose question doesn't parse to one of our scoped clause types
    are silently dropped (clean way to filter the 41-clause CUAD-QA
    down to our CoC + Anti-Assignment scope without errors).
    """
    by_contract: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rec in rows:
        title = str(rec["title"])
        context = str(rec["context"])
        question = str(rec["question"])
        phrase = _extract_clause_phrase_from_question(question)
        if phrase is None:
            continue
        clause_type = _normalize_clause_question_name(phrase)
        if clause_type is None:
            continue  # clause type outside our scope
        if title not in by_contract:
            by_contract[title] = {
                "contract_id": title,
                "contract_text": context,
                "gold_spans": [],
            }
            order.append(title)
        answers = rec.get("answers", {}) or {}
        texts = answers.get("text", []) or []
        starts = answers.get("answer_start", []) or []
        for i, ans_text in enumerate(texts):
            try:
                start = int(starts[i])
            except (IndexError, TypeError, ValueError):
                continue
            span_text = str(ans_text)
            by_contract[title]["gold_spans"].append(
                {
                    "clause_type": clause_type,
                    "text": span_text,
                    "char_start": start,
                    "char_end": start + len(span_text),
                }
            )
    for title in order:
        yield by_contract[title]


# ---------------------------------------------------------------------------
# Baselines (defensive: NEVER hardcoded — same contract as MAUD eval)
# ---------------------------------------------------------------------------


def load_baselines(path: Path | str | None) -> dict[str, Any] | None:
    """Load published baseline numbers from JSON. Returns None on no path."""
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"--baselines path {p!r} does not exist")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"--baselines file {p!r} must be a JSON object; got {type(data).__name__}"
        )
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Path to CUAD dataset (HF save_to_disk dir or .jsonl).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("cuad_spans_eval.json"),
    )
    parser.add_argument(
        "--baselines",
        type=Path,
        default=None,
        help="Optional JSON of published baseline numbers. Never hardcoded.",
    )
    parser.add_argument(
        "--clause-types",
        type=str,
        nargs="+",
        default=list(DEFAULT_CLAUSE_TYPES),
        help=(
            "Clause types to evaluate. Default: CoC + Anti-Assignment per "
            "plan §5.2. Adding clause types is a plan-level decision."
        ),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help=(
            "HF dataset split to evaluate (default: test). Pooling train+test "
            "contaminates the eval; pass 'all' only deliberately."
        ),
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help=(
            "Fix #2: extract over overlapping windows of this many chars for "
            "contracts longer than it (recall lever for long docs). OFF by "
            "default. WARNING: multiplies Vertex calls per contract."
        ),
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=4000,
        help="Fix #2: overlap (chars) between windows. SHOULD exceed the longest "
        "gold span so boundary-spanning clauses stay reachable (not enforced; "
        "spans ground against the full contract). Default 4000.",
    )
    parser.add_argument(
        "--recall-sweep",
        action="store_true",
        default=False,
        help=(
            "Fix #4: add a second 'what was missed' pass per example (recall "
            "lever). OFF by default. WARNING: ~2x Vertex calls."
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--use-mock", action="store_true", default=True)
    group.add_argument("--live", action="store_true", default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = _build_parser().parse_args(argv)
    # "all" is the explicit opt-in to the (contaminating) pooled behavior.
    split_arg = None if args.split == "all" else args.split
    examples = load_cuad_examples(
        args.dataset,
        clause_types=tuple(args.clause_types),
        limit=args.limit,
        split=split_arg,
    )
    if not examples:
        _LOG.error("No CUAD examples loaded from %s; aborting.", args.dataset)
        return 2

    if args.live:
        agent = make_live_agent(
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            recall_sweep=args.recall_sweep,
        )
    else:
        agent = make_mock_agent(seed=args.seed)
    predictions = predictions_from_agent(examples, agent)
    baselines = load_baselines(args.baselines)
    summary = run_eval(
        examples,
        predictions,
        clause_types=tuple(args.clause_types),
        comparison_baselines=baselines,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary_json = summary.to_json()
    # Stamp the run config so the number is auditable (split, sample, model path).
    multipass = bool(args.live and (args.chunk_size or args.recall_sweep))
    summary_json["eval_config"] = {
        "split": args.split,
        "limit": args.limit,
        "seed": args.seed,
        "live": args.live,
        "clause_types": list(args.clause_types),
        "definitions_injected": bool(_load_clause_definitions()),
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "recall_sweep": args.recall_sweep,
    }
    if multipass:
        # Honesty gate: multi-pass / chunked extraction is NOT single-pass, so
        # these numbers are not apples-to-apples with the single-pass published
        # CUAD baselines. Carry the disclosure in the artifact itself.
        summary_json["eval_config"]["protocol_note"] = (
            "Multi-pass extraction (chunked windows and/or a second recall "
            "sweep), NOT single-pass. Numbers reflect a higher inference budget "
            "than the single-pass fine-tuned CUAD baselines and are not "
            "apples-to-apples; report alongside the single-pass number and "
            "disclose in the README."
        )
    args.out.write_text(json.dumps(summary_json, indent=2), encoding="utf-8")
    _LOG.info(
        "CUAD-Spans: macro_f1=%.4f micro_f1=%.4f P@R=0.8=%s (flag=%s); wrote %s",
        summary.macro_f1,
        summary.micro_f1,
        summary.p_at_r_0_8["p_at_r_0_8"],
        summary.p_at_r_0_8["flag"],
        args.out,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
