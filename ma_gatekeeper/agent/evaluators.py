"""Phoenix evaluators used by the Risk Judge agent.

Classifiers are cached at module level via @functools.lru_cache so a
single LLM client is reused across findings (Python-reviewer fix —
previously we instantiated a new LLM per call).


Implements Hook 2 of plan §6.1. Verified against arize-phoenix-evals docs:

  - `phoenix.evals.LLM(provider="vertex", model="...")` — provider FIRST,
    not `provider="vertexai"`. Reference:
    https://arize.com/docs/phoenix/integrations/llm-providers/google-gen-ai/gemini-evals
  - `create_classifier(name=, prompt_template=, choices=, llm=)` returns a
    `ClassificationEvaluator` whose `.evaluate(eval_input: dict)` method
    returns `List[Score]` (one Score per choice's rail). Reference:
    https://arize-phoenix.readthedocs.io/projects/evals/

The Risk Judge runs both classifiers and routes via router.judge_and_route,
which writes TWO separate Phoenix annotations (one per evaluator) so the
analytics UI groups properly (Arize-reviewer guidance).

Vertex provider requires `CLOUD_ML_PROJECT_ID` and `CLOUD_ML_REGION`
environment variables (set in .env.example).
"""
from __future__ import annotations

import functools
import os

# Model name: as of 2026-05, the publicly-callable Gemini 3 Pro identifier on
# Vertex is "gemini-3-pro-preview"; Gemini 2.5 Pro is the fallback if a quota
# bump isn't approved. Override via env.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview")


def _make_llm():
    """Return a phoenix.evals.LLM bound to Gemini on Vertex.

    `provider="vertex"` (NOT "vertexai"). Reads CLOUD_ML_PROJECT_ID and
    CLOUD_ML_REGION from environment per the Vertex provider contract.
    """
    from phoenix.evals import LLM
    return LLM(provider="vertex", model=GEMINI_MODEL)


@functools.lru_cache(maxsize=1)
def make_hallucination_classifier():
    """Classifier that scores whether an explanation is grounded in context.

    Call shape (verified against Phoenix Evals 3.x):
        clf = make_hallucination_classifier()
        scores = clf.evaluate({"context": ctx, "explanation": exp})
        # scores is List[Score]; take scores[0]
        score, label, explanation = scores[0].score, scores[0].label, scores[0].explanation
    """
    from phoenix.evals import create_classifier
    return create_classifier(
        name="hallucination",
        prompt_template=(
            "Given the cited context, determine whether the explanation "
            "contains information not supported by the context.\n"
            "Context:\n{context}\n\nExplanation:\n{explanation}\n\n"
            "Reply with exactly one of: factual, hallucinated."
        ),
        choices={"factual": 1.0, "hallucinated": 0.0},
        llm=_make_llm(),
    )


@functools.lru_cache(maxsize=1)
def make_faithfulness_classifier():
    """Classifier that scores whether the agent's tag matches the clause text.

    Same call shape as hallucination — `.evaluate({...})` returns List[Score].
    """
    from phoenix.evals import create_classifier
    return create_classifier(
        name="clause_faithfulness",
        prompt_template=(
            "Does the agent's classification of this clause match the "
            "literal language of the clause?\n"
            "Clause:\n{clause_text}\n\nClassification: {tag}\n\n"
            "Reply with exactly one of: faithful, partial, unfaithful."
        ),
        choices={"faithful": 1.0, "partial": 0.5, "unfaithful": 0.0},
        llm=_make_llm(),
    )


def run_inline_judges(*, context: str, explanation: str,
                     clause_text: str, tag: str
                     ) -> tuple[float, str, float, str]:
    """Run both inline judges and return (h_score, h_label, f_score, f_label).

    This is the function the Risk Judge agent calls per finding. It exists
    so router.judge_and_route gets genuinely independent scores rather
    than the v1 stub that aliased h to f.
    """
    h_clf = make_hallucination_classifier()
    f_clf = make_faithfulness_classifier()

    h_scores = h_clf.evaluate({"context": context, "explanation": explanation})
    f_scores = f_clf.evaluate({"clause_text": clause_text, "tag": tag})

    h = h_scores[0]
    f = f_scores[0]
    return float(h.score), str(h.label), float(f.score), str(f.label)
