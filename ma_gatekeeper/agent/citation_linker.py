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
CITATION_LINKER_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")

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
    first. Two distinct modes (GROUNDTRUTH_PLAN T1.2 fail-closed contract):

      * jurisdiction_hint is None
          -> return the canonical (candidates[0]) entry. This is the
             "governing law not detected -> Delaware/canonical default" path;
             the SERVER is responsible for rendering the visible default label.

      * jurisdiction_hint is given
          -> prefer an EXACT then a substring jurisdiction match WITHIN that
             hint. If no same-jurisdiction entry exists for the tag, FAIL
             CLOSED and return None (escalate). We NEVER fall through to a
             different jurisdiction's authority — surfacing a Delaware *case*
             on a New York hint, or Cal. § 16600 without a California hint, is
             a wrong-authority error a fail-open lookup would manufacture.

    Returns None when the tag has no map entry at all — the graceful, expected
    outcome for contract-anchored clause types (e.g. accelerated_vesting).
    """
    candidates = [e for e in _load_entries() if e.get("tag") == tag]
    if not candidates:
        return None

    chosen: dict | None
    if jurisdiction_hint:
        hint = jurisdiction_hint.strip().lower()
        chosen = next(
            (e for e in candidates
             if str(e.get("jurisdiction", "")).strip().lower() == hint),
            None,
        )
        if chosen is None:
            # Substring is allowed only WITHIN the hint's jurisdiction family
            # (e.g. "new york" in "New York"); it can never reach a different
            # jurisdiction because the predicate keys on the hint itself.
            chosen = next(
                (e for e in candidates
                 if hint in str(e.get("jurisdiction", "")).lower()),
                None,
            )
        if chosen is None:
            # Fail-closed: a hinted jurisdiction with no same-jurisdiction
            # entry escalates rather than serving another jurisdiction's law.
            return None
    else:
        chosen = candidates[0]

    try:
        # CitationRef ignores the entry's extra "tag" key (pydantic extra=ignore).
        return CitationRef.model_validate(chosen)
    except ValidationError as exc:  # pragma: no cover - defensive
        _LOG.warning("citation map entry for tag=%s failed validation: %s", tag, exc)
        return None


def map_contains_authority_for_tag(tag: str, gold_citation: str) -> bool:
    """Does ANY map entry for `tag` (any jurisdiction) carry `gold_citation`?

    This is the "map-contains-the-authority-anywhere-for-this-tag" probe the
    citation-gold eval reports ALONGSIDE recall@1. The gap between the two is
    the honest `candidates[0]` story: an authority (e.g. § 271, § 2-210) the map
    *has* for the tag but does not surface as its single best lookup answer.
    Uses the same form-aware comparator as the live rail.
    """
    for e in _load_entries():
        if e.get("tag") != tag:
            continue
        if citations_match(str(e.get("citation", "")), gold_citation):
            return True
    return False


# ---------------------------------------------------------------------------
# Section-citation normaliser (used by the comparator + the exact-match rail).
# ---------------------------------------------------------------------------

_SECTION_WORD_RE = re.compile(r"\b(section|sec\.?)\b", re.IGNORECASE)
_SECTION_SPACE_RE = re.compile(r"§\s*")
_WS_RE = re.compile(r"\s+")

# Case-law caption detector: "Party v. Party". The reporter/year/docket tail
# that follows the caption is the part that drifts between long (parallel-cite)
# and short forms, so we key case-law equality on the CAPTION only.
_CASE_CAPTION_RE = re.compile(r"\bv\.?\s", re.IGNORECASE)
# Split the caption off the citation tail at the first comma that precedes a
# digit run (the reporter volume / docket year). Party names in this corpus
# carry no Arabic digits ("AB Stable VIII" uses roman numerals), so this cleanly
# isolates "Akorn, Inc. v. Fresenius Kabi AG" from ", 2018 WL 4719347 (...)".
_CASE_TAIL_SPLIT_RE = re.compile(r",\s*(?=\d)")


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


def _is_case_law(citation: str) -> bool:
    """Heuristic: a citation is case-law iff it carries a 'X v. Y' caption."""
    return bool(_CASE_CAPTION_RE.search(citation or ""))


def normalise_case_citation(citation: str) -> str:
    """Canonical case-law key = the lowercased, whitespace-collapsed CAPTION
    (party names), with the reporter/year/docket tail stripped.

    This is what makes the gold short form `Akorn, Inc. v. Fresenius Kabi AG,
    2018 WL 4719347 (Del. Ch. 2018)` compare EQUAL to the map's parallel-cite
    long form `... (Del. Ch. Oct. 1, 2018), aff'd, 198 A.3d 724 (Del. 2018)` —
    both reduce to `akorn, inc. v. fresenius kabi ag`. Keying on the caption
    (not "first reporter cite") also survives AB Stable, where the map leads
    with the Chancery WL cite and the gold leads with the Supreme-Court reporter.
    """
    s = (citation or "").strip()
    caption = _CASE_TAIL_SPLIT_RE.split(s, maxsplit=1)[0]
    return _WS_RE.sub(" ", caption.lower()).strip().rstrip(",")


def citations_match(a: str, b: str) -> bool:
    """Form-aware citation equality used by BOTH the live comparator and the
    offline gold eval.

      * statute vs statute  -> section-punctuation normalised equality.
      * case-law vs case-law -> caption (party-name) equality, so long-vs-short
        parallel-cite forms of the SAME case are not manufactured into a
        disagreement.
      * statute vs case-law -> never equal.
    """
    a_case, b_case = _is_case_law(a), _is_case_law(b)
    if a_case and b_case:
        return normalise_case_citation(a) == normalise_case_citation(b)
    if a_case != b_case:
        return False
    return _normalise(a) == _normalise(b)


def citations_match_kind(a: str, b: str) -> str:
    """Classify HOW two citations match, for the gold eval's honesty buckets.

    Returns one of:
      * "exact"            — byte-identical (after strip).
      * "section_normalised" — equal only after § / "Section" punctuation
                               canonicalisation (statutes).
      * "case_form"        — same case under caption-only comparison, but the
                             verbatim strings differ (long-vs-short parallel
                             cites). This is the `citation_form_mismatch` bucket.
      * "miss"             — not the same authority.
    """
    a_s, b_s = (a or "").strip(), (b or "").strip()
    if a_s and b_s and a_s == b_s:
        return "exact"
    if _is_case_law(a_s) and _is_case_law(b_s):
        if normalise_case_citation(a_s) == normalise_case_citation(b_s):
            return "case_form"
        return "miss"
    if _is_case_law(a_s) != _is_case_law(b_s):
        return "miss"
    if _normalise(a_s) == _normalise(b_s):
        return "section_normalised"
    return "miss"


# ---------------------------------------------------------------------------
# Governing-law -> jurisdiction normalisation (GROUNDTRUTH_PLAN T1.2).
# ---------------------------------------------------------------------------
# A PINNED keyword table maps contract governing-law language to the map's
# EXACT five jurisdiction values. Unknown / ambiguous text -> None (the server
# then renders a visible "governing law not detected — canonical default"
# rationale rather than guessing). Order matters: the first matching phrase
# wins, and more specific phrases are listed before broader ones.

# The five canonical map jurisdictions — the ONLY strings lookup_citation hints.
MAP_JURISDICTIONS: tuple[str, ...] = (
    "Delaware", "Federal", "New York", "California", "Uniform Commercial Code",
)

_JURISDICTION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("state of delaware", "Delaware"),
    ("laws of delaware", "Delaware"),
    ("delaware", "Delaware"),
    ("state of new york", "New York"),
    ("laws of the state of new york", "New York"),
    ("new york", "New York"),
    ("state of california", "California"),
    ("california", "California"),
    ("uniform commercial code", "Uniform Commercial Code"),
    ("u.c.c.", "Uniform Commercial Code"),
    ("federal law", "Federal"),
    ("united states", "Federal"),
)


def normalize_jurisdiction(text: str | None) -> str | None:
    """Map free contract governing-law language onto one of MAP_JURISDICTIONS.

    Pinned keyword table; first match wins. Returns None for unknown/ambiguous
    input (including None/empty) — callers MUST treat None as "not detected"
    and fail-closed / render a visible default, never as a silent Delaware.
    """
    if not text:
        return None
    hay = text.strip().lower()
    for needle, canonical in _JURISDICTION_KEYWORDS:
        if needle in hay:
            return canonical
    return None


# ---------------------------------------------------------------------------
# Severity-gated case-law (GROUNDTRUTH_PLAN T1.2).
# ---------------------------------------------------------------------------


def _statute_entry_for(tag: str, jurisdiction: str) -> CitationRef | None:
    """First statute-kind map entry for (tag, jurisdiction), or None."""
    for e in _load_entries():
        if e.get("tag") != tag:
            continue
        if str(e.get("jurisdiction", "")) != jurisdiction:
            continue
        if e.get("citation_kind") == "statute":
            try:
                return CitationRef.model_validate(e)
            except ValidationError:  # pragma: no cover - defensive
                return None
    return None


def severity_gated_citation(
    ref: CitationRef | None, *, tag: str, severity: str
) -> CitationRef | None:
    """Apply the severity gate to a *rendered* citation (server-side only).

    Rule: case-law authority is heavy artillery. For a non-`block` (watch/info)
    finding, prefer the statute entry for the SAME tag+jurisdiction IF ONE
    EXISTS; otherwise KEEP the case-law (do NOT blank it). `mac` and
    `exclusivity` have ONLY case-law entries (Akorn/AB Stable; Revlon) — a
    watch-tier finding there keeps the case rather than collapsing to
    "no controlling statute".

    The offline gold eval grades the RAW map (pre-gate); this gate runs only at
    render time, so the script and the Phoenix rail still agree on the raw map.
    """
    if ref is None or ref.citation_kind != "case_law" or severity == "block":
        return ref
    statute = _statute_entry_for(tag, ref.jurisdiction)
    return statute if statute is not None else ref


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
