"""Phoenix evaluators used by the Risk Judge agent.

Classifiers are cached at module level via @functools.lru_cache so a
single LLM client is reused across findings (Python-reviewer fix —
previously we instantiated a new LLM per call).


Implements Hook 2 of plan §6.1. Verified against arize-phoenix-evals docs:

  - `phoenix.evals.LLM(provider="google", model="...")` — the installed
    phoenix-evals exposes the google-genai adapter as provider "google".
    "vertex"/"vertexai" are NOT valid: they route through litellm (which we
    do not install), and the bare string raises "Unknown provider". The
    "google" adapter routes to Vertex when GOOGLE_GENAI_USE_VERTEXAI=TRUE +
    GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION are set (ADC, no API key).
    Verified 2026-06-09 against the installed SDK. Reference:
    https://arize.com/docs/phoenix/integrations/llm-providers/google-gen-ai/gemini-evals
  - `create_classifier(name=, prompt_template=, choices=, llm=)` returns a
    `ClassificationEvaluator` whose `.evaluate(eval_input: dict)` method
    returns `List[Score]` (one Score per choice's rail). Reference:
    https://arize-phoenix.readthedocs.io/projects/evals/

The Risk Judge runs both classifiers and routes via router.judge_and_route,
which writes TWO separate Phoenix annotations (one per evaluator) so the
analytics UI groups properly (Arize-reviewer guidance).

Routing to Vertex requires GOOGLE_GENAI_USE_VERTEXAI=TRUE plus
GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION (all set in .env.example);
the google-genai client then authenticates via Application Default
Credentials (no API key).
"""
from __future__ import annotations

import functools
import logging
import os
import time

_LOG = logging.getLogger(__name__)

# Model name: as of 2026-05, the publicly-callable Gemini 3 Pro identifier on
# Vertex is "gemini-3.1-pro-preview"; Gemini 2.5 Pro is the fallback if a quota
# bump isn't approved. Override via env.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
# GA Flash model for the LIVE inline judges — see _make_llm(). Mirrors
# agents.GEMINI_FLASH_MODEL (same env var, single source of truth).
GEMINI_FLASH_MODEL = os.environ.get("GEMINI_FLASH_MODEL", "gemini-3.5-flash")

# Sync pacer for the inline judges, which call Vertex (2 calls per finding) via
# phoenix-evals OUTSIDE the ADK graph — so `agents._throttle_before_model`
# doesn't cover them. OFF by default (interval 0): the classifier burst now runs
# on GA `gemini-3.5-flash`, freeing the Pro preview bucket, so pacing shouldn't
# be needed. Shares the same env knob so setting GEMINI_MIN_CALL_INTERVAL_SEC>0
# re-enables pacing on BOTH the pipeline and these judges together.
_GEMINI_MIN_CALL_INTERVAL_SEC = float(
    os.environ.get("GEMINI_MIN_CALL_INTERVAL_SEC", "0")
)
_last_inline_judge_call_at = [0.0]


def _pace_inline_judge_call() -> None:
    """Sleep so consecutive inline-judge Vertex calls are >= the interval apart."""
    if _GEMINI_MIN_CALL_INTERVAL_SEC <= 0:
        return
    wait = _GEMINI_MIN_CALL_INTERVAL_SEC - (time.monotonic() - _last_inline_judge_call_at[0])
    if wait > 0:
        time.sleep(wait)
    _last_inline_judge_call_at[0] = time.monotonic()


# The inline judges run on the SAME tight Vertex preview-quota bucket as the
# heavy ADK stages, but they go through `phoenix.evals.LLM` rather than ADK's
# Gemini wrapper, so they don't inherit `agents._build_model`'s retry_options.
# Without this, a transient 429 on either judge raises straight up through
# `run_inline_judges` into the server's finding loop and aborts the whole
# review AFTER the findings were produced (Phase 15: the exact "0 findings on a
# run that worked" failure, just one stage later). We retry transient errors
# (429 / RESOURCE_EXHAUSTED / 503 / timeout) with exponential backoff so a quota
# blip self-heals; non-transient errors still fail loud.
_TRANSIENT_MARKERS = (
    "429", "resource_exhausted", "resource exhausted", "exhausted",
    "503", "unavailable", "deadline", "timeout", "500",
)


def _evaluate_with_retry(clf, payload: dict, *, attempts: int = 3,
                         base_delay: float = 2.0, max_delay: float = 20.0):
    """Call clf.evaluate(payload), retrying transient Vertex errors w/ backoff."""
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return clf.evaluate(payload)
        except Exception as exc:  # noqa: BLE001 — classify by message, re-raise if not transient
            msg = str(exc).lower()
            is_transient = any(m in msg for m in _TRANSIENT_MARKERS)
            last_exc = exc
            if not is_transient or i == attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2 ** i))
            _LOG.warning("inline-judge transient error (attempt %d/%d), "
                         "backing off %.1fs: %s", i + 1, attempts, delay, exc)
            time.sleep(delay)
    assert last_exc is not None  # unreachable; loop either returns or raises
    raise last_exc


def _make_llm(model: str = GEMINI_MODEL):
    """Return a phoenix.evals.LLM bound to Gemini, routed to Vertex.

    provider="google" — the google-genai adapter. It routes to Vertex AI
    (ADC, no API key) when GOOGLE_GENAI_USE_VERTEXAI=TRUE +
    GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION are set; otherwise it
    falls back to the Gemini Developer API and demands GOOGLE_API_KEY.
    "vertex"/"vertexai" are NOT valid here (they require litellm, which is
    not installed). Verified 2026-06-09 against the installed SDK.

    `model` defaults to the heavy Pro model but the LIVE inline judges pass
    GEMINI_FLASH_MODEL: they fire ~2 calls per finding (~10/review), which on
    the tight Pro PREVIEW quota dominated demand and caused the review to stall
    in 429-retry backoff (Phase 15). Moving them to the GA Flash model — its own
    higher, separate quota — leaves only the 3 heavy reasoning stages on the Pro
    bucket. Grading hallucination/faithfulness is well within Flash's ability.
    """
    from phoenix.evals import LLM
    return LLM(provider="google", model=model)


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
            "You are validating whether a finding's explanation is grounded in a "
            "contract excerpt. Adopt a CHARITABLE reading: the explanation was "
            "written by a senior M&A lawyer, and your default should be that it is "
            "grounded unless it plainly conflicts with the text.\n\n"
            "The CONTEXT below is a window of the contract surrounding the cited "
            "clause; it may span several adjacent clauses, definitions, and "
            "cross-references. Read and SYNTHESIZE the ENTIRE context before "
            "deciding — supporting language is frequently in a neighbouring clause "
            "or a defined term, not only in the single sentence the finding "
            "quotes.\n\n"
            "Treat all of the following as GROUNDED expert work-product, NOT "
            "hallucination, even when not printed verbatim in the context:\n"
            "  - standard legal-doctrine labels (Revlon, Omnicare, AB Stable, "
            "fiduciary-out, no-shop, MAC, etc.);\n"
            "  - market-customary framing and benchmark ranges (e.g. a termination "
            "fee being 'within customary range');\n"
            "  - risk-direction and materiality judgments ('raises/lowers pricing "
            "risk', 'watch not block') that follow reasonably from the clause;\n"
            "  - the natural downstream consequences of the clause (e.g. which "
            "provisions a change-of-control trigger fires);\n"
            "  - deal-size ratios and arithmetic derived from figures in the "
            "agreement.\n\n"
            "Judge ONLY the OPERATIVE claim — what the explanation says the cited "
            "clause itself SAYS or DOES. Reply 'factual' whenever that operative "
            "claim is consistent with the context. Reply 'hallucinated' ONLY when "
            "the explanation DIRECTLY CONTRADICTS the clause or fabricates clause "
            "content that is simply not there (e.g. claims a carve-out exists that "
            "the text does not contain). When in doubt, choose 'factual'.\n\n"
            "Context:\n{context}\n\nExplanation:\n{explanation}\n\n"
            "Reply with exactly one of: factual, hallucinated."
        ),
        choices={"factual": 1.0, "hallucinated": 0.0},
        llm=_make_llm(GEMINI_FLASH_MODEL),  # live inline judge → GA Flash quota
    )


@functools.lru_cache(maxsize=1)
def make_faithfulness_classifier():
    """Classifier that scores whether the finding's *explanation* is supported by
    the clause text and the trigger language the finding relies on.

    This aligns the judge's task with the actual logical structure of the
    agent's reasoning (explanation grounded in clause + trigger) rather than the
    v1 task of matching a single-word `tag` against the whole clause — too
    granular, and blind to the nuance the explanation carries.

    Same call shape as hallucination — `.evaluate({...})` returns List[Score].
    """
    from phoenix.evals import create_classifier
    return create_classifier(
        name="clause_faithfulness",
        prompt_template=(
            "Evaluate whether the finding's EXPLANATION is supported by the clause "
            "text and the trigger language quoted from it. Adopt a CHARITABLE "
            "reading: the explanation is senior M&A work-product, so default to "
            "'faithful' unless it clearly conflicts with the clause.\n\n"
            "The trigger language is the operative words inside the clause that the "
            "finding hangs its reasoning on. If the trigger language is empty, "
            "evaluate the explanation against the clause text alone.\n\n"
            "Expert framing — doctrine labels, market-customary ranges, "
            "risk-direction and materiality judgments, and the natural downstream "
            "consequences of the clause — all COUNT as supported; do not downgrade "
            "the score merely because such commentary extends beyond the literal "
            "words.\n\n"
            "Clause text:\n{clause_text}\n\n"
            "Trigger language:\n{trigger_language}\n\n"
            "Finding explanation:\n{explanation}\n\n"
            "Reply 'faithful' when the explanation is consistent with the clause "
            "and trigger language (this is the expected case for valid findings). "
            "Reply 'partial' ONLY when the explanation materially OVERSTATES what "
            "the clause supports. Reply 'unfaithful' ONLY when the explanation "
            "directly contradicts the clause and trigger language. When in doubt, "
            "choose 'faithful'.\n"
            "Reply with exactly one of: faithful, partial, unfaithful."
        ),
        choices={"faithful": 1.0, "partial": 0.5, "unfaithful": 0.0},
        llm=_make_llm(GEMINI_FLASH_MODEL),  # live inline judge → GA Flash quota
    )


def run_inline_judges(*, context: str, explanation: str,
                     clause_text: str, tag: str = "",
                     trigger_language: str = ""
                     ) -> tuple[float, str, float, str]:
    """Run both inline judges and return (h_score, h_label, f_score, f_label).

    This is the function the Risk Judge agent calls per finding. It exists
    so router.judge_and_route gets genuinely independent scores rather
    than the v1 stub that aliased h to f.

    `tag` is retained for backward compatibility with the agent call site but
    is no longer consumed by the faithfulness judge: faithfulness now grades the
    `explanation` against `clause_text` + `trigger_language` (the operative words
    the finding relies on), which matches the agent's reasoning structure. When
    `trigger_language` is unavailable (e.g. the production Finding schema doesn't
    carry it), the judge falls back to grading the explanation against the clause
    text alone.
    """
    h_clf = make_hallucination_classifier()
    f_clf = make_faithfulness_classifier()

    _pace_inline_judge_call()
    h_scores = _evaluate_with_retry(
        h_clf, {"context": context, "explanation": explanation}
    )
    _pace_inline_judge_call()
    f_scores = _evaluate_with_retry(f_clf, {
        "clause_text": clause_text,
        "trigger_language": trigger_language,
        "explanation": explanation,
    })

    h = h_scores[0]
    f = f_scores[0]
    return float(h.score), str(h.label), float(f.score), str(f.label)


# ---------------------------------------------------------------------------
# Citation-linkage evaluators (design/STATUTE_LAYER.md §3.3).
# ---------------------------------------------------------------------------
# Two complementary axes graded against the citation-gold-v1 dataset:
#   - citation_validity   : LLM — "is this even a real, well-formed provision?"
#   - citation_exact_match : DETERMINISTIC regex — "is it the RIGHT one?"
# citation_faithfulness was cut (Wave-2 scope) as the weakest/most circular axis.


@functools.lru_cache(maxsize=1)
def make_citation_validity_classifier():
    """LLM classifier: is a citation a real, correctly-formed legal authority?

    Rails: valid_citation / invalid_citation / malformed. Same call shape as the
    other classifiers — `.evaluate({"citation": ...})` returns List[Score].
    """
    from phoenix.evals import create_classifier
    return create_classifier(
        name="citation_validity",
        prompt_template=(
            "Determine whether the following legal citation refers to a real, "
            "correctly-formatted statutory provision or judicial decision.\n"
            "Citation:\n{citation}\n\n"
            "Reply with exactly one of: valid_citation, invalid_citation, malformed."
        ),
        choices={"valid_citation": 1.0, "invalid_citation": 0.0, "malformed": 0.0},
        llm=_make_llm(),
    )


def _citation_score(score: float, label: str, explanation: str):
    """A Phoenix-Score-shaped result (.score/.label/.explanation). Uses the real
    phoenix.evals.Score when available, else a lightweight stand-in so the
    deterministic rail works without the phoenix install (and in tests)."""
    try:
        from phoenix.evals import Score
        return Score(score=score, label=label, explanation=explanation,
                     name="citation_exact_match")
    except Exception:
        from types import SimpleNamespace
        return SimpleNamespace(score=score, label=label, explanation=explanation,
                               name="citation_exact_match")


def make_citation_exact_match_classifier():
    """DETERMINISTIC comparator surfaced in the create_classifier `.evaluate(
    dict) -> List[Score]` shape for Phoenix UI uniformity — **NOT an LLM judge**
    (no Gemini call; see README §6.1 Hook 10).

    Compares a candidate citation to the gold/expected citation using the same
    section-normaliser the live comparator uses. Rails: exact / normalised_match
    / miss. Accepts `expected` (gold) under several common keys and the
    candidate under `citation`/`output`/`candidate`.
    """
    from .citation_linker import _normalise

    class _CitationExactMatchClassifier:
        name = "citation_exact_match"
        rails = ("exact", "normalised_match", "miss")

        def evaluate(self, eval_input: dict):
            expected = str(
                eval_input.get("expected")
                or eval_input.get("gold_citation")
                or eval_input.get("reference")
                or ""
            ).strip()
            candidate = str(
                eval_input.get("citation")
                or eval_input.get("output")
                or eval_input.get("candidate")
                or ""
            ).strip()
            if expected and candidate and expected == candidate:
                label, score = "exact", 1.0
            elif expected and candidate and _normalise(expected) == _normalise(candidate):
                label, score = "normalised_match", 1.0
            else:
                label, score = "miss", 0.0
            return [_citation_score(
                score, label, f"expected={expected!r} candidate={candidate!r}"
            )]

    return _CitationExactMatchClassifier()
