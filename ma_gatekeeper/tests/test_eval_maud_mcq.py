"""Invariant tests for scripts/eval_maud_mcq.py.

Per Builder B's defensive priorities, each test pins an UNHAPPY-PATH
behavior — happy-path correctness is incidental; the load-bearing
property is "no silent failure mode lands."

Tests cover:
  1. `match_response_to_choice` exact-match semantics — free-form text
     that doesn't match any listed choice returns None and counts as
     wrong (NEVER fuzzy-matched onto a near choice).
  2. Skip semantics for malformed dataset records:
       - empty `choices` -> skipped, reason `no_choices_listed`.
       - gold not in choices -> skipped, reason `gold_answer_not_in_choices`.
       Skipped counts surface in the summary.
  3. Per-category breakdown is required + a single overall hides
     category disparities — pin both the per_category dict shape and the
     macro/micro distinction.
  4. Baselines NEVER hardcoded — `load_baselines(None)` returns None
     (not a fabricated dict), and `comparison_baselines` in the summary
     reflects the input path or None.
  5. Mock agent is deterministic across re-runs given the same seed.
  6. n_unmatched_responses surfaces separately from n_correct (the
     reviewer can tell "agent never refused" from "agent refused often").
  7. `--limit N` returns EXACTLY N examples (round-2 fix: round-1 made
     `--limit 0` return 1).
  8. HF MAUD adapter reconstructs MCQ semantics from the multilabel-binary
     schema (`_coerce_hf_maud_rows`).
  9. Degenerate per-question AUPR (paper-metric path; see module docstring
     for the degeneracy caveat).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import eval_maud_mcq as M


# ---------------------------------------------------------------------------
# 1. match_response_to_choice — exact match only
# ---------------------------------------------------------------------------


def test_match_response_exact_match_returns_choice():
    choices = ("Yes", "No", "Yes, but only for the target")
    assert M.match_response_to_choice("Yes", choices) == "Yes"


def test_match_response_unmatched_returns_none():
    """Free-form text that does NOT equal any listed choice returns None.

    The defensive invariant: a model that says "Yes." (with a trailing
    period) when the only choice is "Yes" is UNMATCHED. We strip outer
    whitespace but NOT punctuation — punctuation is content.
    """
    choices = ("Yes", "No", "Yes, but only for the target")
    assert M.match_response_to_choice("Yes.", choices) is None
    assert M.match_response_to_choice("yes", choices) is None
    assert M.match_response_to_choice("maybe", choices) is None


def test_match_response_strips_outer_whitespace_only():
    """Outer whitespace is stripped (LLM newline noise); inner content is exact."""
    choices = ("Yes, but only for the target",)
    assert (
        M.match_response_to_choice("  Yes, but only for the target\n", choices)
        == "Yes, but only for the target"
    )


def test_match_response_does_not_fuzzy_match_near_choice():
    """The most load-bearing invariant: substrings of a choice MUST NOT
    match. A model returning "Yes" when the only listed choice is
    "Yes, but only for the target" is WRONG. A future "smart match" that
    collapses "Yes" -> "Yes, but only for the target" silently inflates
    accuracy on every yes/no question."""
    choices = ("Yes, but only for the target", "No")
    assert M.match_response_to_choice("Yes", choices) is None


# ---------------------------------------------------------------------------
# 2. Skip semantics — malformed records surface in n_skipped_with_reason
# ---------------------------------------------------------------------------


def _write_jsonl(tmp_path: Path, records: list[dict]) -> Path:
    p = tmp_path / "maud.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec))
            fh.write("\n")
    return p


def _maud_record(
    *,
    example_id: str = "ex_0",
    contract_id: str = "c_0",
    contract_text: str = "the contract",
    category: str = "CoC: Definition",
    question: str = "What is the CoC definition?",
    choices: list[str] | None = None,
    gold_answer: str = "Yes",
) -> dict:
    return {
        "example_id": example_id,
        "contract_id": contract_id,
        "contract_text": contract_text,
        "category": category,
        "question": question,
        "choices": ["Yes", "No"] if choices is None else choices,
        "gold_answer": gold_answer,
    }


def test_load_skips_examples_with_empty_choices(tmp_path):
    """Empty choices list → skipped with reason `no_choices_listed`."""
    records = [
        _maud_record(example_id="a", choices=[]),
        _maud_record(example_id="b"),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    assert len(kept) == 1
    assert kept[0].example_id == "b"
    assert skipped == {M.SKIP_REASON_NO_CHOICES: 1}


def test_load_skips_examples_with_gold_not_in_choices(tmp_path):
    """Gold not in choices → skipped with reason `gold_answer_not_in_choices`.

    This is a real bug pattern in scraped MAUD-style datasets — the
    annotator's reference string drifted from the choices list. Silent
    "score zero" would hide the data bug; skipping with reason makes it
    auditable.
    """
    records = [
        _maud_record(
            example_id="a", choices=["Yes", "No"], gold_answer="Maybe"
        ),
        _maud_record(example_id="b"),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    assert len(kept) == 1
    assert kept[0].example_id == "b"
    assert skipped == {M.SKIP_REASON_GOLD_NOT_IN_CHOICES: 1}


def test_load_skips_both_reasons_simultaneously(tmp_path):
    records = [
        _maud_record(example_id="a", choices=[]),
        _maud_record(example_id="b", choices=["Yes"], gold_answer="No"),
        _maud_record(example_id="c"),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    assert len(kept) == 1
    assert skipped == {
        M.SKIP_REASON_NO_CHOICES: 1,
        M.SKIP_REASON_GOLD_NOT_IN_CHOICES: 1,
    }


def test_run_eval_surfaces_n_skipped_with_reason(tmp_path):
    records = [
        _maud_record(example_id="skip", choices=[]),
        _maud_record(example_id="ok"),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("Yes", 0.5),
        n_total_examples=len(kept) + sum(skipped.values()),
        n_skipped_with_reason=skipped,
    )
    out = summary.to_json()
    assert out["n_total_examples"] == 2
    assert out["n_evaluated"] == 1
    assert out["n_skipped_with_reason"] == {M.SKIP_REASON_NO_CHOICES: 1}


# ---------------------------------------------------------------------------
# 3. Per-category breakdown + macro/micro distinction
# ---------------------------------------------------------------------------


def test_per_category_breakdown_is_keyed_by_category(tmp_path):
    """Per plan §5.2 'Exact-match accuracy per category' — per_category
    dict MUST be keyed by category name and carry per-category n/n_correct.
    """
    records = [
        _maud_record(example_id="a", category="CoC", gold_answer="Yes"),
        _maud_record(example_id="b", category="CoC", gold_answer="No"),
        _maud_record(example_id="c", category="MAC", gold_answer="Yes"),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("Yes", 0.5),  # Agent always answers "Yes".
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
    )
    out = summary.to_json()
    assert set(out["per_category"].keys()) == {"CoC", "MAC"}
    coc = out["per_category"]["CoC"]
    mac = out["per_category"]["MAC"]
    # CoC: agent says "Yes" — golds are "Yes" and "No" → 1/2 = 0.5.
    assert coc["n"] == 2
    assert coc["n_correct"] == 1
    assert coc["accuracy"] == 0.5
    # MAC: 1/1.
    assert mac["n"] == 1
    assert mac["n_correct"] == 1
    assert mac["accuracy"] == 1.0


def test_macro_and_micro_accuracy_both_reported(tmp_path):
    """Macro = per-category mean; micro = pooled. Imbalanced categories
    diverge. Pin both numbers so a category-imbalanced refactor that
    drops one of them is visible.
    """
    records = [
        # Category A: 1 example, agent right.
        _maud_record(example_id="a1", category="A", gold_answer="Yes"),
        # Category B: 3 examples, agent wrong on all (answers "Yes" to "No"x3).
        _maud_record(example_id="b1", category="B", gold_answer="No"),
        _maud_record(example_id="b2", category="B", gold_answer="No"),
        _maud_record(example_id="b3", category="B", gold_answer="No"),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("Yes", 0.5),
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
    )
    # Micro = 1/4 = 0.25; macro = mean(1.0, 0.0) = 0.5. They DIVERGE — the
    # whole point of reporting both. A refactor that quietly returns only
    # micro hides the per-category disaster.
    assert summary.overall_micro_accuracy == pytest.approx(0.25, abs=1e-9)
    assert summary.overall_macro_accuracy == pytest.approx(0.5, abs=1e-9)


# ---------------------------------------------------------------------------
# 4. Baselines never hardcoded
# ---------------------------------------------------------------------------


def test_load_baselines_none_returns_none():
    """Defensive: no path → returns None, NEVER a fabricated dict."""
    assert M.load_baselines(None) is None


def test_load_baselines_reads_provided_json(tmp_path):
    p = tmp_path / "baselines.json"
    p.write_text(json.dumps({"gpt-4": 0.762, "claude-3-opus": 0.781}))
    loaded = M.load_baselines(p)
    assert loaded == {"gpt-4": 0.762, "claude-3-opus": 0.781}


def test_load_baselines_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        M.load_baselines(tmp_path / "nope.json")


def test_load_baselines_rejects_non_dict_json(tmp_path):
    """A list at the top level is a common scrape artifact; we MUST reject
    rather than silently coerce to {0: ...} or similar."""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([0.762, 0.781]))
    with pytest.raises(ValueError, match="must be a JSON object"):
        M.load_baselines(p)


def test_summary_comparison_baselines_none_when_no_path(tmp_path):
    records = [_maud_record()]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("Yes", 0.5),
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
        comparison_baselines=None,
    )
    out = summary.to_json()
    # The defensive contract: comparison_baselines is None, not {} and not
    # a fabricated dict of numbers.
    assert out["comparison_baselines"] is None


def test_summary_comparison_baselines_passes_through(tmp_path):
    records = [_maud_record()]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    baselines = {"gpt-4": 0.762}
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("Yes", 0.5),
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
        comparison_baselines=baselines,
    )
    out = summary.to_json()
    assert out["comparison_baselines"] == {"gpt-4": 0.762}


# ---------------------------------------------------------------------------
# 5. Mock agent determinism
# ---------------------------------------------------------------------------


def test_mock_agent_is_deterministic_across_calls():
    agent = M.make_mock_agent(seed=42)
    a1, c1 = agent("contract text", "question A", ("Yes", "No", "Maybe"))
    a2, c2 = agent("contract text", "question A", ("Yes", "No", "Maybe"))
    assert a1 == a2
    assert c1 == c2


def test_mock_agent_returns_listed_choice():
    agent = M.make_mock_agent(seed=42)
    choices = ("Yes", "No", "Yes, but only for the target")
    answer, _conf = agent("c", "q", choices)
    assert answer in choices


def test_mock_agent_empty_choices_returns_empty():
    """No listed choices → mock returns empty answer + zero confidence."""
    agent = M.make_mock_agent(seed=42)
    answer, conf = agent("c", "q", ())
    assert answer == ""
    assert conf == 0.0


# ---------------------------------------------------------------------------
# 6. n_unmatched_responses surfaces separately
# ---------------------------------------------------------------------------


def test_n_unmatched_responses_separate_from_n_correct(tmp_path):
    """A model that returns free-form text (not in choices) is WRONG, but
    its wrongness is a different shape than "answered confidently with
    the wrong choice." The summary surfaces n_unmatched_responses so
    judges can disambiguate."""
    records = [_maud_record(example_id=f"e{i}") for i in range(3)]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    # Agent always returns "BOGUS" — never matches any choice.
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("BOGUS", 0.5),
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
    )
    out = summary.to_json()
    assert out["n_evaluated"] == 3
    assert out["n_correct"] == 0
    assert out["n_unmatched_responses"] == 3
    # Per-category unmatched count is also surfaced for diagnostic value.
    for cat_metrics in out["per_category"].values():
        assert cat_metrics["n_unmatched"] == cat_metrics["n"]


def test_n_unmatched_responses_zero_when_agent_always_picks(tmp_path):
    records = [_maud_record(example_id=f"e{i}") for i in range(3)]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("Yes", 0.5),
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
    )
    out = summary.to_json()
    assert out["n_unmatched_responses"] == 0


# ---------------------------------------------------------------------------
# 7. End-to-end main() — opt-in --live flag does NOT silently burn quota
# ---------------------------------------------------------------------------


def test_main_default_uses_mock_agent(tmp_path):
    """End-to-end: run main() against a JSONL fixture without --live. The
    script MUST default to mock and write a summary JSON.
    """
    records = [_maud_record(example_id=f"e{i}") for i in range(2)]
    p = _write_jsonl(tmp_path, records)
    out = tmp_path / "out.json"
    rc = M.main(["--dataset", str(p), "--out", str(out)])
    assert rc == 0
    summary = json.loads(out.read_text())
    assert summary["n_evaluated"] == 2
    assert summary["comparison_baselines"] is None


def test_main_returns_2_on_empty_dataset(tmp_path):
    """No usable examples → main() returns 2, NEVER writes a 0/0 summary."""
    p = _write_jsonl(tmp_path, [_maud_record(example_id="a", choices=[])])
    out = tmp_path / "out.json"
    rc = M.main(["--dataset", str(p), "--out", str(out)])
    assert rc == 2
    assert not out.exists()


def test_main_with_baselines_flag_writes_them_through(tmp_path):
    records = [_maud_record()]
    p = _write_jsonl(tmp_path, records)
    baselines_path = tmp_path / "baselines.json"
    baselines_path.write_text(json.dumps({"gpt-4": 0.762}))
    out = tmp_path / "out.json"
    rc = M.main(
        [
            "--dataset",
            str(p),
            "--out",
            str(out),
            "--baselines",
            str(baselines_path),
        ]
    )
    assert rc == 0
    summary = json.loads(out.read_text())
    assert summary["comparison_baselines"] == {"gpt-4": 0.762}


# ---------------------------------------------------------------------------
# 8. --limit semantics (round-2 fix: `--limit 0` must return EXACTLY 0)
# ---------------------------------------------------------------------------


def test_limit_zero_returns_zero_examples(tmp_path):
    """Round-1 bug: `--limit 0` returned 1 example because `kept.append(ex)`
    ran before the limit check. Round-2 contract: `--limit 0` returns 0."""
    records = [_maud_record(example_id=f"e{i}") for i in range(5)]
    p = _write_jsonl(tmp_path, records)
    kept, _skipped = M.load_maud_examples(p, limit=0)
    assert kept == []


def test_limit_one_returns_exactly_one(tmp_path):
    records = [_maud_record(example_id=f"e{i}") for i in range(5)]
    p = _write_jsonl(tmp_path, records)
    kept, _skipped = M.load_maud_examples(p, limit=1)
    assert len(kept) == 1


def test_limit_none_returns_all(tmp_path):
    records = [_maud_record(example_id=f"e{i}") for i in range(5)]
    p = _write_jsonl(tmp_path, records)
    kept, _skipped = M.load_maud_examples(p, limit=None)
    assert len(kept) == 5


# ---------------------------------------------------------------------------
# 9. HF MAUD adapter — multilabel-binary → MCQ reconstruction
# ---------------------------------------------------------------------------


def _hf_maud_row(
    *,
    id: str,
    contract_name: str,
    text: str,
    question: str,
    answer: str,
    label: int,
    category: str = "MAE Definition",
) -> dict:
    """Build a synthetic row matching the actual `theatticusproject/maud`
    HF schema: keys `id, contract_name, text, question, answer, label,
    category` (plus a few we don't consume)."""
    return {
        "id": id,
        "data_type": "main",
        "contract_name": contract_name,
        "text": text,
        "question": question,
        "subquestion": question,
        "answer": answer,
        "label": label,
        "text_type": "agreement",
        "category": category,
    }


def test_hf_maud_adapter_groups_choices_by_contract_and_question():
    """`(contract_name, question)` groups: the `answer` strings across rows
    become the choices list; the row with label==1 is the gold answer."""
    rows = [
        _hf_maud_row(
            id="r1",
            contract_name="C1",
            text="contract C1 text",
            question="Q1",
            answer="Choice A",
            label=0,
        ),
        _hf_maud_row(
            id="r2",
            contract_name="C1",
            text="contract C1 text",
            question="Q1",
            answer="Choice B",
            label=1,
        ),
        _hf_maud_row(
            id="r3",
            contract_name="C1",
            text="contract C1 text",
            question="Q1",
            answer="Choice C",
            label=0,
        ),
    ]
    examples = list(M._coerce_hf_maud_rows(rows))
    assert len(examples) == 1
    ex = examples[0]
    assert ex.contract_id == "C1"
    assert ex.contract_text == "contract C1 text"
    assert ex.question == "Q1"
    assert set(ex.choices) == {"Choice A", "Choice B", "Choice C"}
    # Gold is from the label==1 row.
    assert ex.gold_answer == "Choice B"
    assert ex.example_id == "r2"


def test_hf_maud_adapter_emits_multiple_groups():
    rows = [
        _hf_maud_row(
            id="r1", contract_name="C1", text="C1 text", question="Q1",
            answer="Yes", label=1, category="CatA",
        ),
        _hf_maud_row(
            id="r2", contract_name="C1", text="C1 text", question="Q1",
            answer="No", label=0, category="CatA",
        ),
        _hf_maud_row(
            id="r3", contract_name="C2", text="C2 text", question="Q2",
            answer="Yes", label=0, category="CatB",
        ),
        _hf_maud_row(
            id="r4", contract_name="C2", text="C2 text", question="Q2",
            answer="No", label=1, category="CatB",
        ),
    ]
    examples = list(M._coerce_hf_maud_rows(rows))
    assert len(examples) == 2
    by_id = {ex.example_id: ex for ex in examples}
    assert by_id["r1"].gold_answer == "Yes"
    assert by_id["r1"].category == "CatA"
    assert by_id["r4"].gold_answer == "No"
    assert by_id["r4"].category == "CatB"


def test_hf_maud_adapter_no_positive_label_is_skippable():
    """A group with no label==1 row produces an example whose gold_answer
    is "" — the standard skip path then drops it as
    `gold_answer_not_in_choices`."""
    rows = [
        _hf_maud_row(
            id="r1", contract_name="C1", text="t", question="Q",
            answer="A", label=0,
        ),
        _hf_maud_row(
            id="r2", contract_name="C1", text="t", question="Q",
            answer="B", label=0,
        ),
    ]
    examples = list(M._coerce_hf_maud_rows(rows))
    assert len(examples) == 1
    assert examples[0].gold_answer == ""
    # Gold "" is not in choices → would be skipped by load_maud_examples.
    assert "" not in examples[0].choices


# ---------------------------------------------------------------------------
# 10. Degenerate AUPR (paper-metric path; see module docstring caveat)
# ---------------------------------------------------------------------------


def test_aupr_degenerate_perfect_answer():
    """Agent picks the right choice with confidence 1.0 → degenerate AUPR
    is 1.0 (P(gold)=1.0, P(other)=0)."""
    ex = M.MaudExample(
        example_id="x",
        contract_id="c",
        contract_text="t",
        category="cat",
        question="q",
        choices=("A", "B", "C"),
        gold_answer="A",
    )
    result = M.MaudEvalResult(
        example_id="x",
        category="cat",
        gold_answer="A",
        raw_response="A",
        matched_choice="A",
        is_correct=True,
        confidence=1.0,
    )
    score = M._degenerate_aupr_for_example(result, ex.choices)
    assert score == pytest.approx(1.0, abs=1e-9)


def test_aupr_degenerate_wrong_answer():
    """Agent picks B with confidence 0.9; gold is A → degenerate AUPR is
    low because the only positive prediction (B@0.9) is a non-match and
    every other choice gets score 0."""
    ex = M.MaudExample(
        example_id="x",
        contract_id="c",
        contract_text="t",
        category="cat",
        question="q",
        choices=("A", "B", "C"),
        gold_answer="A",
    )
    result = M.MaudEvalResult(
        example_id="x",
        category="cat",
        gold_answer="A",
        raw_response="B",
        matched_choice="B",
        is_correct=False,
        confidence=0.9,
    )
    score = M._degenerate_aupr_for_example(result, ex.choices)
    # All choices except B get score 0; A (the gold) is tied at 0 with C.
    # AP score is < 1.0 — pin that it's well below 1.0 (the wrong shape).
    assert score < 0.6


def test_aupr_degenerate_unmatched_response_zero():
    """Agent returns BOGUS not in choices → matched_choice=None →
    degenerate AUPR for this example is 0 (no choice carries positive
    probability)."""
    ex = M.MaudExample(
        example_id="x",
        contract_id="c",
        contract_text="t",
        category="cat",
        question="q",
        choices=("A", "B"),
        gold_answer="A",
    )
    result = M.MaudEvalResult(
        example_id="x",
        category="cat",
        gold_answer="A",
        raw_response="BOGUS",
        matched_choice=None,
        is_correct=False,
        confidence=0.7,
    )
    score = M._degenerate_aupr_for_example(result, ex.choices)
    # When all scores are zero AP returns the proportion of positives in y_true.
    # y_true = [1, 0], y_score = [0, 0] → AP = 0.5 (sklearn's degenerate case).
    # We just pin <= 0.5; the load-bearing property is "not 1.0".
    assert score <= 0.5


def test_aupr_degenerate_macro_reported_in_summary(tmp_path):
    """The summary's `aupr_degenerate` field carries the question-mean AUPR.
    With one perfect example (gold matched at confidence 1.0) and one
    wrong, the macro is the mean of the two per-example AUPRs."""
    records = [
        _maud_record(
            example_id="ok", category="C", choices=["A", "B"], gold_answer="A"
        ),
        _maud_record(
            example_id="wrong", category="C", choices=["A", "B"], gold_answer="A"
        ),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    # First agent call returns A@1.0 (perfect); second returns B@1.0 (wrong).
    state = {"i": 0}

    def agent(c, q, ch):
        i = state["i"]
        state["i"] += 1
        return ("A", 1.0) if i == 0 else ("B", 1.0)

    summary = M.run_eval(
        kept,
        agent=agent,
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
    )
    out = summary.to_json()
    # Perfect example → AUPR 1.0. Wrong example → AUPR ≈ 0.5
    # (y_true=[1,0], y_score=[0,1.0]). Mean ≈ 0.75.
    assert "aupr_degenerate" in out
    assert 0.0 < out["aupr_degenerate"] < 1.0


def test_aupr_degenerate_perfect_run_is_one(tmp_path):
    """Every example perfect → aupr_degenerate = 1.0."""
    records = [
        _maud_record(
            example_id=f"e{i}", category="C", choices=["A", "B"], gold_answer="A"
        )
        for i in range(3)
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("A", 1.0),
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
    )
    out = summary.to_json()
    assert out["aupr_degenerate"] == pytest.approx(1.0, abs=1e-9)


def test_per_category_aupr_present(tmp_path):
    """`per_category[cat]["aupr_degenerate"]` is populated for each category."""
    records = [
        _maud_record(
            example_id="a", category="CatA", choices=["A", "B"], gold_answer="A"
        ),
        _maud_record(
            example_id="b", category="CatB", choices=["A", "B"], gold_answer="A"
        ),
    ]
    p = _write_jsonl(tmp_path, records)
    kept, skipped = M.load_maud_examples(p)
    summary = M.run_eval(
        kept,
        agent=lambda c, q, ch: ("A", 1.0),
        n_total_examples=len(kept),
        n_skipped_with_reason=skipped,
    )
    out = summary.to_json()
    for cat in ("CatA", "CatB"):
        assert "aupr_degenerate" in out["per_category"][cat]
        assert out["per_category"][cat]["aupr_degenerate"] == pytest.approx(
            1.0, abs=1e-9
        )
