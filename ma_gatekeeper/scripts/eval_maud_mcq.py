"""MAUD-MCQ accuracy evaluation (plan §5.2 + §12).

Headline number for the README three-track eval table:
"MAUD-MCQ accuracy vs baselines." This script computes the **achieved**
accuracy of the M&A Gatekeeper agent on the MAUD multiple-choice deal-point
benchmark. Baseline numbers (e.g. GPT-4 from the MAUD paper) are NEVER
fabricated by this script — pass a `--baselines path/to/baselines.json` to
include published baselines in the output JSON for side-by-side comparison.

Plan §5.2 specifies "Exact-match accuracy per category." Per-category
breakdown is non-negotiable: a single overall accuracy hides
category-level disasters (e.g. 80% overall masking 30% on the one
category that actually moves the needle for an M&A reviewer).

PROJECT vs PAPER metrics — both reported side-by-side
-----------------------------------------------------
The MAUD paper's headline metric is **AUPR averaged over questions**
(area under the per-question precision-recall curve, treating each
choice as a binary "is this the right answer?" classifier). Our project
metric is **exact-match accuracy per category** (plan §5.2). We ship
BOTH so the JSON is comparable to the paper AND to the plan.

Caveat on the paper-AUPR we compute here: the MAUD paper assumes the
model exposes per-choice probabilities. The current agent interface
returns a single `(answer, confidence)` tuple, so we compute a
DEGENERATE form: `P(chosen_answer) = confidence` and `P(non-chosen) =
0`. A full-fidelity AUPR matching the paper requires the agent to
expose per-choice probabilities, which would be a separate refactor.
The degenerate AUPR is surfaced in JSON under `aupr_degenerate` so
no reader mistakes it for the paper number. See the test names
`test_aupr_degenerate_*` for the pinned semantics.

Semantics pinned by this script (and locked by tests/test_eval_maud_mcq.py):

  1. Each MAUD example is a (contract, question, category, choices, gold_answer)
     tuple. The agent receives (contract, question, choices) and must return
     a string that EXACTLY matches one of the listed choices. Free-form text
     that does not match any choice counts as a wrong answer AND increments
     `n_unmatched_responses` for transparency.

  2. Examples whose `choices` list is empty (i.e. the dataset omitted choices
     for that agreement) are SKIPPED, not silently scored zero. Skipped
     count + reason is surfaced as `n_skipped_with_reason`.

  3. Per-category breakdown keyed by category name; overall accuracy
     reported as the macro mean across categories AND as the micro mean
     across all (non-skipped) examples. The macro/micro distinction is
     surfaced so judges can see both views.

  4. Comparison baselines, when present, must be loaded from a separate
     JSON file via `--baselines`. The script NEVER hardcodes baseline
     numbers — this would let a refactor silently print "vs GPT-4 (76.2%)"
     even after the published number has been retracted.

Usage:
  # Default: mock agent — no Vertex quota burn, reproducible CI runs.
  python -m scripts.eval_maud_mcq \\
      --dataset data/maud --out maud_mcq_eval.json

  # Live agent (burns Vertex quota; explicit opt-in required):
  python -m scripts.eval_maud_mcq --live \\
      --dataset data/maud --out maud_mcq_eval.json

  # With baseline comparison:
  python -m scripts.eval_maud_mcq \\
      --dataset data/maud --out maud_mcq_eval.json \\
      --baselines configs/maud_published_baselines.json

The default `--use-mock` (deterministic random-choice agent seeded by
example index) is what runs in CI and in any accidental local run; the
`--live` flag is the explicit opt-in to burn quota. Mirrors plan §5.2's
"reproducibility first" stance.
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

_LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaudExample:
    """One MAUD multiple-choice example, agreement-scoped.

    Fields mirror the HuggingFace `theatticusproject/maud` schema. `category`
    is the deal-point category (e.g. "MAE Definition: Carve-outs"); `question`
    is the natural-language deal-point question; `choices` is the explicit
    list of answer strings the agent must select EXACTLY one of; `gold_answer`
    is the human-annotated correct choice (which MUST appear in `choices` —
    enforced at load time).
    """

    example_id: str
    contract_id: str
    contract_text: str
    category: str
    question: str
    choices: tuple[str, ...]
    gold_answer: str


@dataclass
class MaudEvalResult:
    """Per-example evaluation outcome."""

    example_id: str
    category: str
    gold_answer: str
    raw_response: str
    matched_choice: str | None  # None when raw_response matched no choice
    is_correct: bool
    confidence: float


@dataclass
class MaudEvalSummary:
    """Aggregate output. Serialized via `to_json()` for the README pipeline.

    Carries BOTH project metrics (exact-match accuracy per plan §5.2) AND
    paper metrics (degenerate per-question AUPR per MAUD paper §4). The
    paper number is explicitly labelled `aupr_degenerate` so no reader
    mistakes it for the full per-choice-probability AUPR the paper reports.
    """

    n_total_examples: int  # before skipping
    n_evaluated: int
    n_correct: int
    n_unmatched_responses: int
    n_skipped_with_reason: dict[str, int] = field(default_factory=dict)
    overall_micro_accuracy: float = 0.0
    overall_macro_accuracy: float = 0.0
    per_category: dict[str, dict[str, float | int]] = field(default_factory=dict)
    # Paper metric: degenerate AUPR (see module docstring for caveat).
    aupr_degenerate: float = 0.0
    comparison_baselines: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "n_total_examples": self.n_total_examples,
            "n_evaluated": self.n_evaluated,
            "n_correct": self.n_correct,
            "n_unmatched_responses": self.n_unmatched_responses,
            "n_skipped_with_reason": dict(self.n_skipped_with_reason),
            "overall_micro_accuracy": self.overall_micro_accuracy,
            "overall_macro_accuracy": self.overall_macro_accuracy,
            "per_category": self.per_category,
            "aupr_degenerate": self.aupr_degenerate,
            "comparison_baselines": self.comparison_baselines,
        }


# ---------------------------------------------------------------------------
# Agent interface — mock-injectable per spec
# ---------------------------------------------------------------------------


class _AgentFn(Protocol):
    """Callable contract: (contract, question, choices) -> (answer, confidence).

    The default impl wraps `build_root_agent()` via the ADK Runner; tests
    pass deterministic mocks; CLI `--use-mock` and `--live` flags choose
    which path runs. Default is `--use-mock` so accidental runs don't burn
    Vertex quota.
    """

    def __call__(
        self,
        contract_text: str,
        question: str,
        choices: tuple[str, ...],
    ) -> tuple[str, float]: ...


def make_mock_agent(seed: int = 42) -> _AgentFn:
    """Deterministic mock — picks a choice by hash(contract + question) mod len.

    Deterministic per (contract, question) so re-running the eval on the
    same dataset yields the same accuracy number. NOT a learned model;
    its only purpose is to keep accidental CI runs reproducible and quota-free.
    Confidence is fixed at 0.5 so downstream code can't accidentally rely
    on a mock's confidence calibration.
    """
    import hashlib

    def _agent(
        contract_text: str, question: str, choices: tuple[str, ...]
    ) -> tuple[str, float]:
        if not choices:
            return "", 0.0
        digest = hashlib.sha256(
            f"{seed}::{contract_text[:64]}::{question}".encode("utf-8")
        ).digest()
        idx = int.from_bytes(digest[:4], "big") % len(choices)
        return choices[idx], 0.5

    return _agent


def _snap_choice(raw: str, choices: tuple[str, ...]) -> tuple[str, float]:
    """Map a model's free-form reply onto one of the listed MCQ choices.

    Honest, no-fabrication policy — three tiers, each with a distinct
    confidence so the degenerate-AUPR path (P(chosen)=confidence) reflects
    how the answer was recovered:
      - exact verbatim match            -> (choice, 1.0)
      - a choice appears as a substring -> (longest such choice, 0.75)
      - no choice recoverable           -> (raw, 0.5) so the eval counts it
        as an unmatched response (incrementing `n_unmatched_responses`)
        rather than silently snapping to a wrong choice.

    The substring tier prefers the LONGEST matching choice so that, when
    one choice is a prefix/substring of another (e.g. "Yes" vs "Yes, with
    carve-outs"), the more specific answer wins instead of the short one.
    """
    answer = raw.strip()
    for choice in choices:
        if choice == answer:
            return choice, 1.0
    substring_hits = [c for c in choices if c and c in answer]
    if substring_hits:
        best = max(substring_hits, key=len)
        return best, 0.75
    return answer, 0.5


def make_live_agent() -> _AgentFn:
    """Live single-question MCQ agent backed by a Vertex `LlmAgent`.

    Per this module's design, MAUD-MCQ is scored by a single LlmAgent
    answering one deal-point question at a time — NOT the 4-stage findings
    pipeline (`agent/agents.py:build_root_agent`), which extracts
    contract-wide RiskFindings and exposes no MCQ surface. The agent is
    instructed to reply with EXACTLY one of the listed choices; recovery of
    a drifted reply is handled transparently by `_snap_choice` so this
    wrapper never papers over a wrong answer.

    Construction is cheap and ADK-free: the google-adk import lives inside
    the returned closure (via `scripts._live_agent.run_single_agent`), so
    importing this module — and constructing the live agent in tests — does
    not require google-adk or Vertex credentials. Quota is only burned when
    the closure is actually invoked, and `--use-mock` remains the default so
    CI never reaches this path.
    """

    def _agent(
        contract_text: str, question: str, choices: tuple[str, ...]
    ) -> tuple[str, float]:
        if not choices:
            return "", 0.0
        # Lazy import: keeps module import (and test construction) ADK-free.
        from scripts._live_agent import run_single_agent

        choices_block = "\n".join(f"- {c}" for c in choices)
        instruction = (
            "You are an expert M&A attorney answering a MAUD deal-point "
            "multiple-choice question about a merger agreement. Read the "
            "agreement, then choose the SINGLE best answer. Reply with "
            "EXACTLY one of the listed choices, copied verbatim, with no "
            "extra words, punctuation, quoting, or explanation."
        )
        user_text = (
            f"=== MERGER AGREEMENT ===\n{contract_text}\n\n"
            f"=== QUESTION ===\n{question}\n\n"
            f"=== CHOICES (reply with exactly one, verbatim) ===\n"
            f"{choices_block}"
        )
        raw = run_single_agent(instruction, user_text, agent_name="maud_mcq")
        return _snap_choice(raw, choices)

    return _agent


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


SKIP_REASON_NO_CHOICES = "no_choices_listed"
SKIP_REASON_GOLD_NOT_IN_CHOICES = "gold_answer_not_in_choices"


def load_maud_examples(
    dataset_path: Path | str,
    *,
    limit: int | None = None,
) -> tuple[list[MaudExample], dict[str, int]]:
    """Load MAUD examples from a HuggingFace `save_to_disk` directory OR a
    plain JSONL file. Returns (kept_examples, skipped_counts_by_reason).

    Skipping rules (silent failures forbidden):
      - `choices` empty: skip with reason `no_choices_listed`.
      - `gold_answer not in choices`: skip with reason
        `gold_answer_not_in_choices` (an inconsistency in the source
        dataset; we surface it rather than silently score zero).

    Accepts JSONL records with keys: example_id, contract_id, contract_text,
    category, question, choices, gold_answer.
    """
    path = Path(dataset_path)
    if path.is_dir():
        examples = list(_iter_hf_examples(path))
    elif path.suffix == ".jsonl":
        examples = list(_iter_jsonl_examples(path))
    else:
        raise FileNotFoundError(
            f"MAUD dataset path {path!r} is neither a HF save_to_disk "
            "directory nor a .jsonl file."
        )

    kept: list[MaudExample] = []
    skipped: dict[str, int] = {}
    for ex in examples:
        # Check the limit BEFORE appending so `--limit 0` returns 0 examples
        # (the prior post-append check made `--limit 0` return 1).
        if limit is not None and len(kept) >= limit:
            break
        if not ex.choices:
            skipped[SKIP_REASON_NO_CHOICES] = (
                skipped.get(SKIP_REASON_NO_CHOICES, 0) + 1
            )
            continue
        if ex.gold_answer not in ex.choices:
            skipped[SKIP_REASON_GOLD_NOT_IN_CHOICES] = (
                skipped.get(SKIP_REASON_GOLD_NOT_IN_CHOICES, 0) + 1
            )
            continue
        kept.append(ex)
    return kept, skipped


def _iter_jsonl_examples(path: Path) -> Iterator[MaudExample]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            yield _coerce_example(rec)


def _iter_hf_examples(path: Path) -> Iterator[MaudExample]:
    """Lazy-imports `datasets`; skipped in tests via JSONL fixtures.

    The HF `theatticusproject/maud` release is stored in multilabel-binary
    form: each row is one `(contract_name, question, candidate_answer)` triple
    with `label in {0,1}` indicating whether that candidate is a gold answer.
    The MCQ semantics our script consumes ((choices, gold_answer)) are
    reconstructed by grouping rows by `(contract_name, question)` and
    collapsing the per-row `answer` strings into the choice list. The
    `label==1` row(s) become the gold answer (one of, in the multilabel
    case where multiple candidates are valid — we take the first such row's
    answer as the singleton gold to keep this script's MCQ contract).
    """
    from datasets import load_from_disk  # type: ignore

    ds = load_from_disk(str(path))
    # MAUD's HF release may expose a single split or a DatasetDict; flatten.
    if hasattr(ds, "items"):
        iters: list[Iterable[dict]] = [split for _, split in ds.items()]
    else:
        iters = [ds]
    rows: list[dict[str, Any]] = []
    for split in iters:
        for rec in split:
            rows.append(dict(rec))
    yield from _coerce_hf_maud_rows(rows)


def _coerce_hf_maud_rows(
    rows: list[dict[str, Any]],
) -> Iterator[MaudExample]:
    """Reconstruct MCQ examples from the HF multilabel-binary schema.

    Expected per-row keys (per WebFetch of `theatticusproject/maud`):
        id, data_type, contract_name, text, question, subquestion,
        answer, label, text_type, category.

    Mapping:
      - `contract_name`  -> `contract_id`
      - `text`           -> `contract_text` (contract excerpt, NOT question)
      - `question`       -> `question`
      - `category`       -> `category`
      - For each `(contract_name, question)` group, the `answer` strings
        across rows form `choices`; the first row with `label == 1` provides
        `gold_answer`. The example_id is the `id` of that gold row (or, if
        no gold row exists in the group, the group is skipped at the
        load_maud_examples layer via the standard skip path because
        `gold_answer not in choices` will surface).

    Defensive: groups with NO label==1 row produce an example whose
    `gold_answer` is the empty string — which is NOT in `choices` (assuming
    no row's answer is empty), so the standard `gold_answer_not_in_choices`
    skip kicks in. This keeps malformed groups auditable rather than silent.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    order: list[tuple[str, str]] = []
    for rec in rows:
        # Strict-key access — missing fields raise loudly rather than coerce.
        contract_name = str(rec["contract_name"])
        question = str(rec["question"])
        key = (contract_name, question)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(rec)

    for key in order:
        group = groups[key]
        contract_name, question = key
        # Build choice list preserving first-seen order; dedupe by string.
        choices: list[str] = []
        seen: set[str] = set()
        for rec in group:
            ans = str(rec["answer"])
            if ans not in seen:
                choices.append(ans)
                seen.add(ans)
        # First label==1 row is the singleton gold (MAUD's multilabel is
        # collapsed to MCQ here; see module docstring).
        gold_answer = ""
        example_id = ""
        for rec in group:
            try:
                label = int(rec["label"])
            except (TypeError, ValueError):
                label = 0
            if label == 1:
                gold_answer = str(rec["answer"])
                example_id = str(rec["id"])
                break
        if not example_id:
            # No positive label — surface as a synthetic id so the skip
            # path's reason counter still attributes it.
            example_id = f"{contract_name}::{question}"
        # Category: take from the first row (MAUD groups share category).
        category = str(group[0].get("category", ""))
        yield MaudExample(
            example_id=example_id,
            contract_id=contract_name,
            contract_text=str(group[0]["text"]),
            category=category,
            question=question,
            choices=tuple(choices),
            gold_answer=gold_answer,
        )


def _coerce_example(rec: dict[str, Any]) -> MaudExample:
    """Defensive coercion: hard-fail on missing fields rather than guessing.

    This is the JSONL-path coercer (strict project schema). The HF-path
    coercer is `_coerce_hf_maud_rows`, which reconstructs MCQ semantics
    from the multilabel-binary schema MAUD actually ships on HF.
    """
    return MaudExample(
        example_id=str(rec["example_id"]),
        contract_id=str(rec["contract_id"]),
        contract_text=str(rec["contract_text"]),
        category=str(rec["category"]),
        question=str(rec["question"]),
        choices=tuple(str(c) for c in rec["choices"]),
        gold_answer=str(rec["gold_answer"]),
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def match_response_to_choice(
    raw_response: str, choices: tuple[str, ...]
) -> str | None:
    """Match the agent's free-form response to one of the listed choices.

    Match is EXACT string equality (after stripping leading/trailing
    whitespace on both sides). NO fuzzy matching, NO casefold — MAUD
    choices are full clauses (e.g. "Yes, but only for the target") and
    fuzzy collapsing two distinct clauses to the same choice would silently
    inflate accuracy.

    Returns the matched choice string, or None if no choice matches.
    """
    cleaned = raw_response.strip()
    for choice in choices:
        if cleaned == choice.strip():
            return choice
    return None


def evaluate_example(
    example: MaudExample, agent: _AgentFn
) -> MaudEvalResult:
    """Run one example through the agent; return scored result."""
    raw_response, confidence = agent(
        example.contract_text, example.question, example.choices
    )
    matched = match_response_to_choice(raw_response, example.choices)
    is_correct = matched is not None and matched == example.gold_answer
    return MaudEvalResult(
        example_id=example.example_id,
        category=example.category,
        gold_answer=example.gold_answer,
        raw_response=raw_response,
        matched_choice=matched,
        is_correct=is_correct,
        confidence=confidence,
    )


def _degenerate_aupr_for_example(
    result: MaudEvalResult, choices: tuple[str, ...]
) -> float:
    """Compute the degenerate per-example AUPR.

    The MAUD paper's headline metric is AUPR computed from per-choice
    probabilities. Our agent interface only returns a single
    `(answer, confidence)` tuple, so we treat the chosen answer as the
    sole positive prediction with `confidence` as its score and assign
    probability 0 to every other choice. For this binary "is this choice
    the right one?" task the resulting AUPR is degenerate but
    well-defined — see module docstring for the caveat.

    Returns sklearn's `average_precision_score` on the constructed
    (y_true, y_score) vectors. When the gold answer is absent from the
    choice list (which `load_maud_examples` would have skipped, but we
    guard anyway), returns 0.0.
    """
    # Lazy-import sklearn so the broader module stays importable without it.
    from sklearn.metrics import average_precision_score  # type: ignore

    if not choices or result.gold_answer not in choices:
        return 0.0
    y_true: list[int] = []
    y_score: list[float] = []
    chosen = result.matched_choice
    for ch in choices:
        y_true.append(1 if ch == result.gold_answer else 0)
        if chosen is not None and ch == chosen:
            y_score.append(float(result.confidence))
        else:
            y_score.append(0.0)
    # `average_precision_score` requires at least one positive class.
    # gold_answer is in choices (guarded above) so the constraint holds.
    return float(average_precision_score(y_true, y_score))


def _degenerate_aupr_macro(
    results: list[MaudEvalResult],
    examples_by_id: dict[str, MaudExample],
) -> tuple[float, dict[str, float]]:
    """Per-question (-example) degenerate AUPR, averaged across questions.

    The MAUD paper averages AUPR across questions. Per-example AUPR is the
    natural granularity here since each example IS a (question, choices)
    pair. We also return the per-category mean for the JSON breakdown.

    Returns (overall_mean_aupr, per_category_mean_aupr_dict).
    """
    per_example_aupr: list[tuple[str, float]] = []
    for r in results:
        ex = examples_by_id.get(r.example_id)
        if ex is None:
            continue
        per_example_aupr.append(
            (r.category, _degenerate_aupr_for_example(r, ex.choices))
        )
    if not per_example_aupr:
        return 0.0, {}
    overall = statistics.fmean(score for _, score in per_example_aupr)
    by_cat: dict[str, list[float]] = {}
    for cat, score in per_example_aupr:
        by_cat.setdefault(cat, []).append(score)
    per_cat_aupr = {cat: statistics.fmean(v) for cat, v in by_cat.items()}
    return overall, per_cat_aupr


def aggregate_results(
    results: list[MaudEvalResult],
    *,
    n_total_examples: int,
    n_skipped_with_reason: dict[str, int],
    comparison_baselines: dict[str, Any] | None = None,
    examples_by_id: dict[str, MaudExample] | None = None,
) -> MaudEvalSummary:
    """Aggregate per-example results into the headline summary.

    Per-category breakdown is non-negotiable (plan §5.2). Reports BOTH
    macro accuracy (per-category mean) AND micro accuracy (pooled across
    all examples) so the judge can see both views. If the two diverge by
    more than a few points the category sizes are unbalanced — caller's
    responsibility to surface that, not this function's job to hide it.

    Also reports degenerate per-question AUPR (paper metric — see module
    docstring for caveat). Pass `examples_by_id` so the AUPR can read each
    example's choice list; if omitted, AUPR is reported as 0.0.
    """
    per_category: dict[str, dict[str, float | int]] = {}
    by_cat: dict[str, list[MaudEvalResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    for cat, items in sorted(by_cat.items()):
        n = len(items)
        n_correct = sum(1 for r in items if r.is_correct)
        n_unmatched = sum(1 for r in items if r.matched_choice is None)
        per_category[cat] = {
            "n": n,
            "n_correct": n_correct,
            "n_unmatched": n_unmatched,
            "accuracy": float(n_correct) / n if n else 0.0,
        }

    n_evaluated = len(results)
    n_correct_total = sum(1 for r in results if r.is_correct)
    n_unmatched = sum(1 for r in results if r.matched_choice is None)
    overall_micro = float(n_correct_total) / n_evaluated if n_evaluated else 0.0
    overall_macro = (
        statistics.fmean(d["accuracy"] for d in per_category.values())
        if per_category
        else 0.0
    )

    # Paper metric: degenerate AUPR per category + overall.
    if examples_by_id:
        aupr_overall, aupr_per_cat = _degenerate_aupr_macro(
            results, examples_by_id
        )
        for cat, score in aupr_per_cat.items():
            if cat in per_category:
                per_category[cat]["aupr_degenerate"] = score
    else:
        aupr_overall = 0.0

    return MaudEvalSummary(
        n_total_examples=n_total_examples,
        n_evaluated=n_evaluated,
        n_correct=n_correct_total,
        n_unmatched_responses=n_unmatched,
        n_skipped_with_reason=dict(n_skipped_with_reason),
        overall_micro_accuracy=overall_micro,
        overall_macro_accuracy=overall_macro,
        per_category=per_category,
        aupr_degenerate=aupr_overall,
        comparison_baselines=comparison_baselines,
    )


def run_eval(
    examples: list[MaudExample],
    agent: _AgentFn,
    *,
    n_total_examples: int | None = None,
    n_skipped_with_reason: dict[str, int] | None = None,
    comparison_baselines: dict[str, Any] | None = None,
) -> MaudEvalSummary:
    """Convenience wrapper: evaluate each example, then aggregate.

    `n_total_examples` defaults to `len(examples)` — pass the pre-skip
    count if you loaded via `load_maud_examples` and want the summary to
    reflect the original size. Same for `n_skipped_with_reason`.
    """
    if n_total_examples is None:
        n_total_examples = len(examples)
    if n_skipped_with_reason is None:
        n_skipped_with_reason = {}
    results = [evaluate_example(ex, agent) for ex in examples]
    examples_by_id = {ex.example_id: ex for ex in examples}
    return aggregate_results(
        results,
        n_total_examples=n_total_examples,
        n_skipped_with_reason=n_skipped_with_reason,
        comparison_baselines=comparison_baselines,
        examples_by_id=examples_by_id,
    )


# ---------------------------------------------------------------------------
# Baselines loading (defensive: NEVER hardcoded)
# ---------------------------------------------------------------------------


def load_baselines(path: Path | str | None) -> dict[str, Any] | None:
    """Load published baseline numbers from JSON for side-by-side comparison.

    Returns None when no path is given — the summary's `comparison_baselines`
    field is then None, NOT a fabricated dict of numbers. This is the
    defensive contract that prevents the script from ever fabricating
    baseline numbers.
    """
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
        help="Path to MAUD dataset (HF save_to_disk dir or .jsonl).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("maud_mcq_eval.json"),
        help="Where to write the summary JSON.",
    )
    parser.add_argument(
        "--baselines",
        type=Path,
        default=None,
        help=(
            "Optional path to a JSON dict of published baseline numbers "
            "(e.g. {'gpt-4': 0.762}). NEVER hardcoded in this script; if "
            "you want comparison numbers in the output, pass this flag."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of (post-skip) examples to evaluate. Default: all.",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Mock agent seed (ignored under --live)."
    )
    # Mutually exclusive: --use-mock (default, safe) vs --live (burns quota).
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--use-mock",
        action="store_true",
        default=True,
        help=(
            "Use a deterministic mock agent. Default. Reproducible across "
            "CI runs, zero Vertex quota burn."
        ),
    )
    group.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Burn Vertex quota with the real agent. Explicit opt-in.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = _build_parser().parse_args(argv)

    examples, skipped = load_maud_examples(args.dataset, limit=args.limit)
    n_total = len(examples) + sum(skipped.values())
    _LOG.info(
        "Loaded %d MAUD examples (kept=%d, skipped=%s)",
        n_total,
        len(examples),
        dict(skipped),
    )
    if not examples:
        _LOG.error("No usable MAUD examples after skipping; aborting.")
        return 2

    if args.live:
        agent = make_live_agent()
    else:
        agent = make_mock_agent(seed=args.seed)

    baselines = load_baselines(args.baselines)
    summary = run_eval(
        examples,
        agent,
        n_total_examples=n_total,
        n_skipped_with_reason=skipped,
        comparison_baselines=baselines,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary.to_json(), indent=2), encoding="utf-8")
    _LOG.info(
        "MAUD-MCQ: %d/%d correct (micro %.4f, macro %.4f); wrote %s",
        summary.n_correct,
        summary.n_evaluated,
        summary.overall_micro_accuracy,
        summary.overall_macro_accuracy,
        args.out,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
