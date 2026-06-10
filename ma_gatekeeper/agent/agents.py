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

    parser = LlmAgent(
        name="parser",
        model=GEMINI_MODEL,
        instruction=_load_prompt("parser", PARSER_PROMPT),
        output_key="clauses",
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

    classifier = ParallelAgent(
        name="classifier",
        sub_agents=[
            LlmAgent(
                name=f"classify_{t}",
                model="gemini-3-flash",
                instruction=classifier_template.format(tag=t),
                output_key=f"tagged_{t}",
            )
            for t in CLASSIFIER_TAGS
        ],
    )

    cross_reference = LlmAgent(
        name="cross_reference",
        model=GEMINI_MODEL,
        instruction=_load_prompt("cross_reference", CROSS_REFERENCE_PROMPT),
        output_key="findings",
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
        model=GEMINI_MODEL,
        instruction=_load_prompt("risk_judge", RISK_JUDGE_PROMPT),
        output_key="judged_findings",
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
        model=GEMINI_MODEL,
        instruction=_load_prompt("portfolio_analyst", PORTFOLIO_ANALYST_PROMPT),
        output_key="portfolio_report",
    )
