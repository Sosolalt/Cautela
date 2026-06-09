"""Citation-linkage layer (design/STATUTE_LAYER.md §2.4).

Three responsibilities, sharply separated:

  1. lookup_citation(tag, jurisdiction_hint) -> CitationRef | None
     SYNCHRONOUS, deterministic, on the user's critical path. Reads the
     hand-curated, primary-source-verified data/citation_map.json. This is the
     ONLY citation ever rendered to users. Returns None for tags with no map
     entry (e.g. accelerated_vesting -> contract-anchored) — by design.

  2. _call_linker_llm(clause_text, tag, timeout) -> LinkerProposal
     ASYNC. An internal LLM proposer. Its output is INTERNAL EVAL DATA only —
     never serialized to the user-facing wire.

  3. _run_llm_proposer_and_annotate(...)
     ASYNC, fire-and-forget. Awaits the proposer, runs a DETERMINISTIC Python
     comparator (static map vs. LLM proposal), and writes a Phoenix span
     annotation via the existing router._annotate helper. Never blocks /review,
     never mutates the user-facing finding.

Citations are pinned to primary sources, not generated.
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import re
from pathlib import Path

from pydantic import ValidationError

from .prompts import CITATION_LINKER_PROMPT
from .router import _annotate
from .schemas import CitationRef, LinkerProposal

_LOG = logging.getLogger(__name__)

# data/citation_map.json lives at the package root (ma_gatekeeper/data), so
# resolve relative to this file rather than the process CWD — robust whether
# the server runs from ma_gatekeeper/ or the repo root or a test sandbox.
_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "citation_map.json"

# The background proposer reuses the system Gemini model id (GEMINI_MODEL is
# already documented in .env.example via the evaluators). Reusing it — rather
# than introducing a new CITATION_LINKER_MODEL var — keeps the env-documentation
# CI gate green and respects the .env-edit prohibition. A cheaper Flash model
# can be swapped in via GEMINI_MODEL.
CITATION_LINKER_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview")

_ANNOTATION_NAME = "citation_linker_agreement"


# ---------------------------------------------------------------------------
# 1. Deterministic map lookup (synchronous cold path).
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _load_entries() -> tuple[dict, ...]:
    """Load + cache citation_map.json entries. Any failure -> empty tuple, so
    lookups degrade to None rather than breaking the review stream."""
    try:
        with open(_MAP_PATH, encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", []) if isinstance(data, dict) else data
        return tuple(e for e in entries if isinstance(e, dict))
    except Exception as exc:  # pragma: no cover - defensive
        _LOG.warning("citation map load failed (%s): lookups return None", exc)
        return ()


def lookup_citation(tag: str, jurisdiction_hint: str | None = None) -> CitationRef | None:
    """Deterministic clause-tag -> controlling-authority lookup.

    Entries are ordered in the map so the canonical authority for each tag is
    first; with no jurisdiction_hint we return that canonical entry. A hint
    prefers an exact (then substring) jurisdiction match. Returns None when the
    tag has no map entry — the graceful, expected outcome for contract-anchored
    clause types.
    """
    candidates = [e for e in _load_entries() if e.get("tag") == tag]
    if not candidates:
        return None

    chosen: dict | None = None
    if jurisdiction_hint:
        hint = jurisdiction_hint.strip().lower()
        chosen = next(
            (e for e in candidates
             if str(e.get("jurisdiction", "")).strip().lower() == hint),
            None,
        )
        if chosen is None:
            chosen = next(
                (e for e in candidates
                 if hint in str(e.get("jurisdiction", "")).lower()),
                None,
            )
    if chosen is None:
        chosen = candidates[0]

    try:
        # CitationRef ignores the entry's extra "tag" key (pydantic extra=ignore).
        return CitationRef.model_validate(chosen)
    except ValidationError as exc:  # pragma: no cover - defensive
        _LOG.warning("citation map entry for tag=%s failed validation: %s", tag, exc)
        return None


# ---------------------------------------------------------------------------
# Section-citation normaliser (used by the comparator + the exact-match rail).
# ---------------------------------------------------------------------------

_SECTION_WORD_RE = re.compile(r"\b(section|sec\.?)\b", re.IGNORECASE)
_SECTION_SPACE_RE = re.compile(r"§\s*")
_WS_RE = re.compile(r"\s+")


def _normalise(citation: str) -> str:
    """Canonicalise section-citation punctuation so equivalent forms compare
    equal: "§ 251(c)" == "§251(c)" == "Section 251(c)". Case-law citations are
    lowercased/whitespace-collapsed and otherwise compared verbatim.
    """
    s = (citation or "").strip().lower()
    s = _SECTION_WORD_RE.sub("§", s)
    s = _SECTION_SPACE_RE.sub("§", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def citations_match(a: str, b: str) -> bool:
    """Deterministic exact/normalised citation equality."""
    return _normalise(a) == _normalise(b)


# ---------------------------------------------------------------------------
# 2. LLM proposer (async, internal eval data only).
# ---------------------------------------------------------------------------

async def _call_linker_llm(clause_text: str, tag: str, timeout: float = 8.0) -> LinkerProposal:
    """Ask Gemini for a single controlling-authority proposal, parsed into a
    LinkerProposal. Raises asyncio.TimeoutError on timeout, json.JSONDecodeError
    on non-JSON output, ValidationError on a schema mismatch — all handled by
    the caller as a `linker_failed` annotation.
    """

    async def _invoke() -> LinkerProposal:
        from google import genai
        from google.genai import types as gtypes

        client = genai.Client()
        prompt = CITATION_LINKER_PROMPT.format(tag=tag, clause_text=clause_text[:4000])
        resp = await client.aio.models.generate_content(
            model=CITATION_LINKER_MODEL,
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        text = getattr(resp, "text", None) or ""
        return LinkerProposal.model_validate(json.loads(text))

    return await asyncio.wait_for(_invoke(), timeout=timeout)


# ---------------------------------------------------------------------------
# 3. Background comparator + annotation (fire-and-forget).
# ---------------------------------------------------------------------------

def _write_annotation(
    span_id: str, *, label: str, score: float, explanation: str, sync: bool = False
) -> None:
    """Write the citation_linker_agreement annotation.

    Normal path reuses router._annotate as-is (async, best-effort). When the
    upstream span force_flush did NOT complete (`sync=True`), write directly
    with sync=True so the annotation isn't lost to a span that may not have
    exported yet — router._annotate exposes no sync kwarg, so this is the only
    place the synchronous variant is issued.
    """
    if not sync:
        _annotate(span_id, name=_ANNOTATION_NAME, label=label,
                  score=score, explanation=explanation)
        return
    try:
        from phoenix.client import Client
        Client().spans.add_span_annotation(
            span_id=span_id,
            annotation_name=_ANNOTATION_NAME,
            annotator_kind="LLM",
            label=label,
            score=score,
            explanation=explanation,
            sync=True,
        )
    except Exception as exc:  # pragma: no cover - best effort
        _LOG.warning("sync citation annotation failed (span=%s): %s", span_id, exc)


async def _run_llm_proposer_and_annotate(
    *,
    clause_text: str,
    tag: str,
    static_ref: CitationRef | None,
    span_id: str,
    flushed: bool = True,
) -> None:
    """Fire-and-forget: run the LLM proposer, compare to the deterministic map,
    write the agreement annotation. Never raises into the event loop.
    """
    sync = not flushed
    try:
        llm_ref = await _call_linker_llm(clause_text, tag, timeout=8.0)
    except Exception as exc:
        # Covers asyncio.TimeoutError, ValidationError, json.JSONDecodeError,
        # and any transport/auth error — all are non-fatal for the user.
        _LOG.warning("citation linker proposer failed (tag=%s): %s", tag, exc)
        _write_annotation(span_id, label="linker_failed", score=0.0,
                          explanation="proposer error", sync=sync)
        return

    if static_ref is None:
        _write_annotation(
            span_id, label="no_static", score=0.0,
            explanation=f"llm={llm_ref.citation} no_map_match", sync=sync,
        )
        return

    agreement = (
        citations_match(static_ref.citation, llm_ref.citation)
        and static_ref.jurisdiction == llm_ref.jurisdiction
    )
    _write_annotation(
        span_id,
        label="agree" if agreement else "disagree",
        score=1.0 if agreement else 0.0,
        explanation=(
            f"static={static_ref.citation} llm={llm_ref.citation} "
            f"conf={llm_ref.model_confidence:.2f}"
        ),
        sync=sync,
    )
