"""ADK agent topology for the M&A Due Diligence Gatekeeper.

Implements §4.2 of plan.md.

Verified ADK import paths (Arize-reviewer + Python-reviewer):
  - `from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent`
    (NOT `from google.adk import ...` — that re-export is not guaranteed.)
  - `from google.adk.runners import Runner`
  - `from google.genai.types import Content, Part`

Verified Phoenix prompt API:
  - `client.prompts.get(prompt_identifier=..., tag=...)` (NOT `name=`).
  - Returns a `PromptVersion`-like object; the template body is accessed
    via `.template` and is itself an object with `.text` or via `.format(
    variables={...})`. We hedge with a try/except and fall back to
    constants in `prompts.py` if anything in the chain returns None.

Reference: https://arize.com/docs/phoenix/prompt-engineering/quickstart-prompts/quickstart-prompts-python
"""
from __future__ import annotations

import asyncio
import logging
import os

from .prompts import (
    CLASSIFIER_PROMPT,
    CROSS_REFERENCE_PROMPT,
    PARSER_PROMPT,
    PORTFOLIO_ANALYST_PROMPT,
    RISK_JUDGE_PROMPT,
)
# Single source of truth: derive from the schemas.Tag Literal rather
# than re-listing the 7 strings here. See README "Tag sync points".
from .schemas import CLASSIFIER_TAGS  # noqa: F401  re-export for callers

_LOG = logging.getLogger(__name__)

# Resolved once at import. Env override (set by .venv/bin/activate and the
# Cloud Run deploy) wins; the fallback is the Vertex `global`-endpoint model
# this project is allow-listed for. NOTE: gemini-3.1-pro-preview is served
# ONLY from GOOGLE_CLOUD_LOCATION=global — a regional location 404s.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")

# Model for the classifier fan-out. The heavy Pro model is a PREVIEW model on a
# tight, shared per-minute Vertex quota; firing the parallel classifier burst on
# it exhausted that quota (429 RESOURCE_EXHAUSTED → the review died with zero
# findings). `gemini-3.5-flash` is a GA model on its OWN, higher, self-serve
# quota — so the concurrent burst no longer competes with (or exhausts) the Pro
# preview bucket the heavy stages use. It's also faster/cheaper, and per-tag
# clause classification is simple enough that Flash is the right tool. Verified
# callable on the Vertex global endpoint (probed live — the quota dimension list
# is NOT a model-availability list and is actively misleading). Override via env.
GEMINI_FLASH_MODEL = os.environ.get("GEMINI_FLASH_MODEL", "gemini-3.5-flash")

# Optional global Vertex-call throttle, OFF by default (interval 0). Kept as a
# tunable safety valve: with the classifier burst moved to GA `gemini-3.5-flash`
# the preview-quota 429 should not recur, so we fire continuously with no pacing.
# If a residual 429 ever shows on the Pro preview stages (parser / cross_reference
# / risk_judge / inline judges), set GEMINI_MIN_CALL_INTERVAL_SEC>0 (e.g. 5-7) to
# re-enable pacing across the whole graph — no redeploy, just an env update.
GEMINI_MIN_CALL_INTERVAL_SEC = float(
    os.environ.get("GEMINI_MIN_CALL_INTERVAL_SEC", "0")
)
_throttle_lock = asyncio.Lock()
_last_model_call_at = [0.0]


# Per-call retry on transient Vertex errors. The 15s throttle above REDUCES
# the per-minute-quota 429 rate but does not eliminate it — the classifier
# fan-out is a ParallelAgent (asyncio TaskGroup), so a SINGLE classifier 429
# cancels its siblings and aborts the whole review with zero findings (observed
# live, Phase 15). Wrapping every model in an ADK `Gemini` with `retry_options`
# makes a 429/503 self-heal WITH EXPONENTIAL BACKOFF *inside* the call (ADK
# forwards this to the google-genai client's http_options — see
# google.adk.models.google_llm.Gemini), so a transient quota blip no longer
# kills the run. Belt-and-suspenders with the throttle: throttle lowers the
# blip rate, retry survives the residual blips.
def _build_model(model_name: str):
    """Wrap a model name in an ADK Gemini with transient-error retry+backoff."""
    from google.adk.models.google_llm import Gemini
    from google.genai import types as genai_types

    # Retry is deliberately SHORT: it exists to ride out a brief per-minute
    # quota blip, NOT to wait out a depleted quota. Aggressive backoff (6x90s)
    # turned an occasional 429 into an 18-minute silent stall that the SSE
    # connection idle-reset before any finding streamed (Phase 15). 3 attempts
    # with a 20s ceiling adds at most ~2+4+8s to a stage; if quota is genuinely
    # gone the stage fails fast and loud instead of hanging. The primary defense
    # is now LOW Pro-preview demand (classifiers + inline judges on GA Flash),
    # so these retries should rarely fire at all.
    return Gemini(
        model=model_name,
        retry_options=genai_types.HttpRetryOptions(
            attempts=3,
            initial_delay=2.0,
            max_delay=20.0,
            exp_base=2.0,
            jitter=0.4,
            http_status_codes=[429, 503, 500],
        ),
    )


async def _throttle_before_model(*args, **kwargs):
    """ADK `before_model_callback`: pace Vertex calls under the preview quota.

    Holds a global lock and sleeps so consecutive model-call starts are at
    least GEMINI_MIN_CALL_INTERVAL_SEC apart. Returns None so the call then
    proceeds normally. Signature is (*args, **kwargs) to be robust to ADK
    passing (callback_context, llm_request) positionally or by keyword.
    """
    if GEMINI_MIN_CALL_INTERVAL_SEC <= 0:
        return None
    async with _throttle_lock:
        loop = asyncio.get_event_loop()
        wait = GEMINI_MIN_CALL_INTERVAL_SEC - (loop.time() - _last_model_call_at[0])
        if wait > 0:
            await asyncio.sleep(wait)
        _last_model_call_at[0] = loop.time()
    return None


def _load_prompt(name: str, fallback: str, tag: str = "production") -> str:
    """Load a prompt from Phoenix by name+tag; fall back to local constant.

    Phoenix `client.prompts.get(...)` signature uses `prompt_identifier=`,
    not `name=`. The returned object exposes template content via
    `.template` (which may itself be an object — we coerce to str
    defensively) or via a `.format(variables={})` call. We do not call
    `.format` here because the caller may want to apply `{tag}` later.
    """
    try:
        from phoenix.client import Client
        prompt = Client().prompts.get(prompt_identifier=name, tag=tag)
        tmpl = getattr(prompt, "template", None)
        if tmpl is None:
            return fallback
        text = getattr(tmpl, "text", None) or str(tmpl)
        return text or fallback
    except Exception as exc:
        _LOG.debug("Falling back to local prompt %r: %s", name, exc)
        return fallback


def build_root_agent():
    """Build the SequentialAgent root of the inference pipeline.

    NOTE: this returns the ADK agent graph. The CALLER must wrap it in a
    Runner and invoke via Content/Part — see `server.py:_stream_findings`.
    """
    from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

    # COST DECISION (2026-06-11): the ENTIRE review pipeline now runs on GA
    # `gemini-3.5-flash`, not the Pro preview. The Pro model's large-context
    # pricing dominated the bill — one review pushes the full merger agreement
    # (150K+ tokens) through the parser plus the downstream stages, and at the
    # >200K-context Pro tier that was ~€2-3/review (and the batch evals were
    # ~€70+). Flash drops a review to well under €1 and its per-stage quality is
    # adequate for this structured extract/classify/judge work. The 3 heavy
    # stages (parser/cross_reference/risk_judge) join the classifier fan-out on
    # GEMINI_FLASH_MODEL; only the standalone Portfolio Analyst keeps GEMINI_MODEL
    # (Pro) since it's a separate, low-frequency endpoint. NOTE: this contradicts
    # the prior "Gemini 3.1 Pro on the heavy stages" narrative in README/devpost —
    # update those docs to match (all-Flash review pipeline) before publishing.
    parser = LlmAgent(
        name="parser",
        model=_build_model(GEMINI_FLASH_MODEL),
        instruction=_load_prompt("parser", PARSER_PROMPT),
        output_key="clauses",
        before_model_callback=_throttle_before_model,
    )

    # Per-tag classifier fan-out. We pre-format the template here so each
    # sub-agent gets a literal tag-baked instruction. CLASSIFIER_PROMPT
    # contains {{...}} escaped braces around the JSON example, so
    # str.format(tag=...) only replaces the {tag} placeholder.
    classifier_template = _load_prompt("classifier", CLASSIFIER_PROMPT)
    try:
        # Sanity-check that the template is .format-safe with our keys.
        classifier_template.format(tag="change_of_control")
    except (KeyError, IndexError) as exc:
        _LOG.warning("Phoenix-loaded classifier template is not format-safe "
                     "(%s); reverting to local CLASSIFIER_PROMPT.", exc)
        classifier_template = CLASSIFIER_PROMPT

    # ParallelAgent: the per-tag classifiers fire concurrently (the fast,
    # intended design). The burst that previously 429'd was on PREVIEW-quota
    # models; on GA `gemini-3.5-flash` (its own higher quota) the concurrent
    # fan-out is fine, so we no longer serialize it. Each sub-agent writes its
    # own `tagged_{tag}` key, so cross_reference downstream is order-independent.
    classifier = ParallelAgent(
        name="classifier",
        sub_agents=[
            LlmAgent(
                name=f"classify_{t}",
                model=_build_model(GEMINI_FLASH_MODEL),
                instruction=classifier_template.format(tag=t),
                output_key=f"tagged_{t}",
                before_model_callback=_throttle_before_model,
            )
            for t in CLASSIFIER_TAGS
        ],
    )

    cross_reference = LlmAgent(
        name="cross_reference",
        model=_build_model(GEMINI_FLASH_MODEL),  # cost: Flash for the whole pipeline (see parser note)
        instruction=_load_prompt("cross_reference", CROSS_REFERENCE_PROMPT),
        output_key="findings",
        before_model_callback=_throttle_before_model,
    )
    # GROUNDTRUTH_PLAN T1.2 (governing-law linkage): the server already consumes
    # a per-contract governing-law hint defensively from this agent's event
    # (`server._governing_law_hint_from_event`), tolerating both the current
    # bare findings-list output AND a future `{governing_law, findings}` envelope.
    # Emitting that envelope on camera is the OPERATOR-GATED live "money moment"
    # (it needs a hard-selected DE/NY deal + a live Phoenix `disagree` span) — it
    # is deliberately NOT forced into this production prompt, so the deterministic
    # jurisdiction-hint + fail-closed + severity-gate code can ship and be
    # unit-tested without coupling to a live recording.

    risk_judge = LlmAgent(
        name="risk_judge",
        model=_build_model(GEMINI_FLASH_MODEL),  # cost: Flash for the whole pipeline (see parser note)
        instruction=_load_prompt("risk_judge", RISK_JUDGE_PROMPT),
        output_key="judged_findings",
        before_model_callback=_throttle_before_model,
    )

    return SequentialAgent(
        name="ma_gatekeeper",
        sub_agents=[parser, classifier, cross_reference, risk_judge],
    )


def build_portfolio_analyst():
    """Fix 7 — standalone 1M-context Portfolio Analyst LlmAgent.

    Single `LlmAgent` on `$GEMINI_MODEL` (default gemini-3.1-pro-preview) with
    `PORTFOLIO_ANALYST_PROMPT`. Deliberately NOT added to the
    SequentialAgent above — the Portfolio Analyst runs as a separate
    `/portfolio` endpoint (`server.py`), one inference call per
    portfolio review, not one per per-contract review.

    Mirrors `portfolio_analyst.py:build_portfolio_analyst` (same factory
    re-exported here so the `agents` module remains the canonical entry
    point for ADK topology construction).
    """
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="portfolio_analyst",
        model=_build_model(GEMINI_MODEL),
        instruction=_load_prompt("portfolio_analyst", PORTFOLIO_ANALYST_PROMPT),
        output_key="portfolio_report",
    )
