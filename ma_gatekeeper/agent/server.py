"""FastAPI server for Cloud Run hosting.

Endpoints:
  POST /review          - upload PDF bytes, returns SSE stream of findings
  GET  /allow-list      - return the 5 pre-indexed deals (plan §5.5)
  POST /review-by-deal  - run agent on a deal_id, fetches Ex 2.1 via EdgarTools
  GET  /healthz         - liveness probe
  POST /reflect         - Cloud Scheduler nightly Reflector cycle (OIDC-gated)

Verified ADK invocation pattern (Python + Arize reviewers):
  - `Runner(agent=..., app_name=..., session_service=...)`
  - `runner.run_async(user_id, session_id, new_message=Content(parts=[
      Part.from_bytes(data=..., mime_type="application/pdf")]))`
  - Yields Event objects with `.author`, `.content` (with `.parts`), `.actions`.

Security (DevOps reviewer):
  - DEMO_PASSCODE compared via hmac.compare_digest (timing-safe).
  - Missing passcode FAILS CLOSED (returns 503) — never opens up.
  - Passcode read from header only, not query string (logs would leak).
  - /reflect requires a valid OIDC bearer token (Cloud Scheduler OIDC).
  - CORS middleware so the Next.js frontend on a different origin can call.

Cloud Run:
  - $PORT honored dynamically via the start command (not hard-coded 8080).
  - SSE responses: explicit Cache-Control + X-Accel-Buffering headers.
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import AsyncIterator

from collections import OrderedDict, defaultdict
import hashlib

from fastapi import Depends, FastAPI, File, Header, HTTPException, Path, Request, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .instrumentation import init_tracing

_LOG = logging.getLogger(__name__)


# ALLOW_LIST + AllowListEntry live in agent/allow_list.py so they can be
# unit-tested without the FastAPI / google.adk import surface. Re-export
# here for any caller that imports them from agent.server.
from .allow_list import ALLOW_LIST, AllowListEntry  # noqa: F401


DEMO_PASSCODE = os.environ.get("DEMO_PASSCODE", "")
SEC_USER_AGENT = os.environ.get(
    "SEC_EDGAR_USER_AGENT", "hugo.majerczyk@proton.me MA-Gatekeeper"
)
EXPECTED_OIDC_AUDIENCE = os.environ.get(
    "REFLECT_OIDC_AUDIENCE", ""  # set to the Cloud Run service URL for /reflect
)
# Max PDF upload size in bytes (DevOps reviewer fix: prevent /review from
# being weaponized into a Vertex billing incident or OOM). Override via env
# if a legitimate use case exceeds 50 MB (almost no real Ex 2.1 does).
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))

# Module-level flag: if `set_identity` fails at startup, /review-by-deal
# will 503 fast instead of silently 403-ing against SEC. Fail-fast >
# silent latent failure under demo load.
_sec_ready: bool = False
# CIKs that failed lifespan validation. Populated only when
# VALIDATE_ALLOW_LIST_ON_BOOT=1 (off for local dev / TestClient so the
# test suite doesn't make network calls). /review-by-deal consults this
# set to 503 with a precise per-deal message before attempting the fetch.
_cik_unreachable: set[str] = set()

# Process-wide filing-artifact cache, keyed by CIK. Value is a
# (bytes, mime_type) tuple because EDGAR 8-K Ex 2.1 attachments are
# almost always HTML (.htm), occasionally PDF; the mime travels with
# the bytes so both the agent (Gemini Part.from_bytes) and the
# `/filing/{deal_id}` route serve the truth. 5 deals × ~5 MB = ~25 MB
# resident — well under the Cloud Run 512 MB floor.
#
# Per-key asyncio.Lock prevents thundering-herd: /review-by-deal and
# /filing/{deal_id} fire within ~50 ms of each other on demo open;
# without the lock we'd double-hit SEC and risk the 10 req/s throttle.
_pdf_cache: dict[str, tuple[bytes, str]] = {}
_pdf_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
# Time budget for one EdgarTools fetch (network + Ex 2.1 download).
# Surfaces as 504 instead of an unbounded hang during the demo.
_PDF_FETCH_TIMEOUT_SECONDS = 20.0

# ---------------------------------------------------------------------------
# Gemini Files API bridge
# ---------------------------------------------------------------------------
# Threshold above which we upload to Gemini's Files API (returning a URI
# we reference via Part.from_uri) instead of inlining bytes via
# Part.from_bytes. Inlining a >5 MB PDF causes Gemini to silently
# truncate pages past ~20 — a clean-looking review of a partial
# document is the worst failure mode the legal reviewer flagged. The
# threshold is conservative; the 5-deal demo HTML files are ~2 MB and
# stay on the inline path.
_FILES_API_THRESHOLD_BYTES = int(
    os.environ.get("FILES_API_THRESHOLD_BYTES", str(8 * 1024 * 1024))
)
# Per-key cache of Files-API URIs so a re-click on the same deal reuses
# the existing handle instead of re-uploading. Google auto-expires the
# uploaded file at 48 h server-side; we evict at 36 h via TTL to stay
# well clear of the boundary plus clock skew. Keyed by content sha256
# so byte-identical re-fetches dedupe even when cache_key (CIK) wasn't
# passed. Value: (uri, monotonic_seconds_at_insert) — monotonic, not
# wall-clock, so a host clock jump (NTP correction on Cloud Run cold
# start) can't falsely expire or extend a live entry.
_files_api_uri_cache: "OrderedDict[str, tuple[str, float]]" = OrderedDict()
_files_api_locks: "OrderedDict[str, asyncio.Lock]" = OrderedDict()
# Polling budget for Files API state transitions (PROCESSING → ACTIVE).
# Typical 2 MB upload settles in <2 s; allow 30 s for a 50 MB PDF.
_FILES_API_POLL_TOTAL_SECONDS = 30.0
# TTL for cached Files-API URIs. Google expires server-side at 48 h;
# 36 h gives 12 h margin and still benefits the Reflector's nightly
# "hits warm cache" pattern. Env-overridable for tests and for ops
# that want a tighter window. A non-positive value silently disables
# the cache — logged at module import so misconfigured ops see it.
_FILES_API_URI_TTL_SECONDS = float(
    os.environ.get("FILES_API_URI_TTL_SECONDS", str(36 * 60 * 60))
)
if _FILES_API_URI_TTL_SECONDS <= 0:
    _LOG.warning(
        "FILES_API_URI_TTL_SECONDS=%s is non-positive; cache effectively "
        "disabled and every demo click pays full upload latency.",
        _FILES_API_URI_TTL_SECONDS,
    )
# Hard cap on the URI cache and on the per-sha lock dict. Without this,
# every distinct content-sha allocates a Lock that's never freed even
# after the URI is TTL-evicted (R4-1 bug-hunter finding). On a long-
# lived Cloud Run instance serving freeform /review uploads, the lock
# dict would grow linearly with upload count. 64 entries covers the
# 5-deal demo + nightly Reflector + a comfortable buffer for ad-hoc
# uploads without unbounded growth. Bounded LRU eviction below.
_FILES_API_CACHE_MAX_ENTRIES = int(
    os.environ.get("FILES_API_CACHE_MAX_ENTRIES", "64")
)


def _should_use_files_api(data: bytes, mime_type: str) -> bool:
    """Threshold rule: inline for small artifacts, Files API for large.

    The PDF size check is tighter than the generic byte threshold
    because Gemini's inline-bytes path silently truncates PDFs past
    ~5 MB — the document-vision rendering doesn't scale with the byte
    budget the way plain-text ingestion does.
    """
    if len(data) > _FILES_API_THRESHOLD_BYTES:
        return True
    if mime_type == "application/pdf" and len(data) > 5 * 1024 * 1024:
        return True
    return False


async def _build_gemini_part(data: bytes, mime_type: str):
    """One-function indirection between the inline and Files-API paths.

    Today: returns `Part.from_bytes` for the small/HTML hot path and
    `Part.from_uri` after a Files-API upload for large/PDF cases.
    Adding a third backend (Cloud Storage URI, blob handle, etc.) is
    a one-function swap.
    """
    from google.genai import types as gtypes

    if not _should_use_files_api(data, mime_type):
        return gtypes.Part.from_bytes(data=data, mime_type=mime_type)
    uri = await _ensure_files_api_upload(data, mime_type)
    return gtypes.Part.from_uri(file_uri=uri, mime_type=mime_type)


def _cache_get_live(sha: str) -> str | None:
    """Return a cached URI iff it is still within the TTL window.

    Stale entries are popped in place — both the URI entry AND the
    per-sha lock — so the lock dict cannot leak past the URI cache
    (R4-1 bug-hunter finding). A future read sees a clean miss.

    TTL is measured with `time.monotonic()` so a wall-clock jump
    (NTP correction during a Cloud Run cold start) cannot falsely
    flip a live entry to expired or vice versa.

    LRU bookkeeping: touching the URI cache MUST also touch the lock
    dict, otherwise the two dicts drift in LRU position and the lock
    eviction (in `_get_or_create_files_api_lock`) can evict a sha
    whose URI is hot. The previous version had this drift bug —
    found during Phase-6 honesty-pass mutation testing.
    """
    entry = _files_api_uri_cache.get(sha)
    if entry is None:
        return None
    uri, inserted_at = entry
    if time.monotonic() - inserted_at > _FILES_API_URI_TTL_SECONDS:
        _files_api_uri_cache.pop(sha, None)
        # Drop the corresponding lock too. The next caller will lazily
        # re-create it via `_get_or_create_files_api_lock` if they need
        # to upload fresh. Without this, the lock dict grows linearly
        # with all-time unique uploads.
        _files_api_locks.pop(sha, None)
        return None
    # LRU touch on BOTH dicts so eviction stays consistent.
    _files_api_uri_cache.move_to_end(sha)
    if sha in _files_api_locks:
        _files_api_locks.move_to_end(sha)
    return uri


def _get_or_create_files_api_lock(sha: str) -> asyncio.Lock:
    """Return the asyncio.Lock for `sha`, creating one if absent and
    evicting the LRU entry if we're at cap. Replaces the previous
    `defaultdict(asyncio.Lock)` which had no bound (R4-1).

    Defense-in-depth note: this function and `_cache_put` BOTH carry
    cap-eviction logic. They cover different scenarios:
      - `_cache_put` evicts on upload SUCCESS (the common case).
      - This function evicts on upload-failure retry — when an upload
        raises, `_cache_put` is never called, so the lock entry would
        accumulate without this eviction site. Don't remove either.
    """
    lock = _files_api_locks.get(sha)
    if lock is not None:
        _files_api_locks.move_to_end(sha)
        return lock
    if len(_files_api_locks) >= _FILES_API_CACHE_MAX_ENTRIES:
        # Evict LRU lock + matching URI entry to keep the two dicts
        # in lockstep. A lock held by a concurrent upload would not
        # be at the front (it's actively used → moved-to-end), so
        # popping the LRU is safe.
        evicted_sha, _ = _files_api_locks.popitem(last=False)
        _files_api_uri_cache.pop(evicted_sha, None)
    lock = asyncio.Lock()
    _files_api_locks[sha] = lock
    return lock


def _cache_put(sha: str, uri: str) -> None:
    """Store `(uri, now)` in the URI cache with LRU cap enforcement.
    Called only inside the per-sha lock so dict mutation is safe.
    """
    if (
        sha not in _files_api_uri_cache
        and len(_files_api_uri_cache) >= _FILES_API_CACHE_MAX_ENTRIES
    ):
        evicted_sha, _ = _files_api_uri_cache.popitem(last=False)
        _files_api_locks.pop(evicted_sha, None)
    _files_api_uri_cache[sha] = (uri, time.monotonic())


async def _ensure_files_api_upload(data: bytes, mime_type: str) -> str:
    """Upload `data` to Gemini's Files API and return the file URI.

    Caches by content sha256 so a re-fetch of the same artifact reuses
    the existing handle within the TTL window. Per-hash asyncio.Lock
    prevents the same race the byte cache guards against — two
    concurrent large uploads of the same artifact would otherwise
    double-charge quota.

    Recovery contract for Google's 48 h server-side URI expiry:
      The cache evicts at `_FILES_API_URI_TTL_SECONDS` (default 36 h),
      well before Google's 48 h boundary. A read past the TTL is
      treated as a miss and triggers a fresh upload. This is pure
      time-based eviction — we deliberately do NOT probe-on-hit
      (cost: 50-200 ms per cache hit on the demo critical path) and
      we do NOT depend on knowing the SDK's expired-URI error shape
      (undocumented and varies across `google-genai` versions).

    Raises HTTPException(502) on upload failure, (504) on PROCESSING
    timeout, (502) on FAILED state. Callers (route handlers) propagate.
    """
    sha = hashlib.sha256(data).hexdigest()
    cached = _cache_get_live(sha)
    if cached is not None:
        return cached
    async with _get_or_create_files_api_lock(sha):
        cached = _cache_get_live(sha)
        if cached is not None:
            return cached
        try:
            uri = await asyncio.wait_for(
                _upload_and_wait_active(data, mime_type),
                timeout=_FILES_API_POLL_TOTAL_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail=f"Gemini Files API PROCESSING > "
                       f"{_FILES_API_POLL_TOTAL_SECONDS}s for "
                       f"{len(data)}-byte {mime_type} upload",
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            _LOG.exception(  # R4 minor #4: log traceback for ops visibility.
                "Gemini Files API upload failed for %d-byte %s artifact",
                len(data), mime_type,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Gemini Files API upload failed: {exc}",
            ) from exc
        _cache_put(sha, uri)
        return uri


async def _upload_and_wait_active(data: bytes, mime_type: str) -> str:
    """Upload via the sync `google-genai` Files API on a worker thread,
    then poll for ACTIVE state with exponential backoff (200 ms → 2 s).

    Sync client + worker thread because the `google-genai` SDK doesn't
    expose an async upload primitive as of v1.x. The wrapping
    `asyncio.wait_for` in `_ensure_files_api_upload` bounds total time.
    """
    import io

    from google import genai
    from google.genai import types as gtypes

    loop = asyncio.get_running_loop()

    def _upload_sync():
        client = genai.Client()
        f = client.files.upload(
            file=io.BytesIO(data),
            config=gtypes.UploadFileConfig(
                mime_type=mime_type,
                display_name=f"ma-gatekeeper-{len(data)}b",
            ),
        )
        return client, f

    client, file_obj = await loop.run_in_executor(None, _upload_sync)
    delay = 0.2
    while True:
        state = getattr(file_obj, "state", None)
        # SDK returns either an enum-ish object or a string; coerce.
        state_str = getattr(state, "name", None) or str(state)
        if state_str == "ACTIVE":
            return file_obj.uri
        if state_str == "FAILED":
            raise RuntimeError(
                f"Files API processing FAILED for {file_obj.name!r}"
            )
        await asyncio.sleep(delay)
        delay = min(delay * 2, 2.0)
        file_obj = await loop.run_in_executor(
            None, lambda: client.files.get(name=file_obj.name)
        )


def _current_trace_id() -> str | None:
    """Return the active OTel trace ID as 32-char lowercase hex, or None.

    Captured by FastAPI's auto-instrumentation: the request handler runs
    inside a root span whose trace_id is shared by every child span the
    ADK runner produces. One value per request = one Phoenix deep-link
    per request, which matches the UX.

    Returns None when no real span is active — typically because Phoenix
    wasn't initialized (NoOp tracer, trace_id == 0) or because the test
    suite runs outside the instrumented request boundary. The frontend
    trace pane gates on `traceId == null` and degrades gracefully; we
    never emit the all-zero hex string because Phoenix would 404 on it
    and that's a worse demo signal than no link at all.
    """
    try:
        from opentelemetry.trace import format_trace_id, get_current_span
    except Exception:
        return None
    span = get_current_span()
    ctx = span.get_span_context()
    trace_int = getattr(ctx, "trace_id", 0)
    if not trace_int:
        return None
    return format_trace_id(trace_int)


def _current_span_id() -> str:
    """Active OTel span id as 16-char lowercase hex (all-zero outside a span).

    The citation background task annotates against the span_id (NOT the 32-hex
    trace_id that _current_trace_id returns). Captured at the _stream_findings
    call site BEFORE asyncio.create_task, because OTel context does not
    propagate across create_task. Best-effort: a NoOp span yields the all-zero
    id and the annotation simply won't link — the proposer is fire-and-forget.
    """
    try:
        from opentelemetry.trace import format_span_id, get_current_span
    except Exception:
        return "0" * 16
    span = get_current_span()
    ctx = span.get_span_context()
    return format_span_id(getattr(ctx, "span_id", 0))


def _force_flush_spans(timeout_millis: int = 500) -> bool:
    """Flush the span exporter so a background annotation POST doesn't race the
    parent span's export (Phoenix 404s on an unknown span_id).

    Returns True when flushed — or when there is nothing to flush (no provider,
    or a provider without force_flush, as in dev/test). Returns False only when
    a real provider's force_flush reports incompleteness or raises; the citation
    background task then falls back to sync=True so the annotation isn't lost.
    """
    try:
        from opentelemetry import trace as _ot_trace
    except Exception:
        return True
    provider = _ot_trace.get_tracer_provider()
    force_flush = getattr(provider, "force_flush", None)
    if not callable(force_flush):
        return True
    try:
        result = force_flush(timeout_millis=timeout_millis)
    except Exception as exc:
        _LOG.warning("span force_flush raised: %s", exc)
        return False
    # SDK force_flush returns True on success / False on timeout; some return None.
    return True if result is None else bool(result)


# Strong references to fire-and-forget citation-proposer tasks. asyncio holds
# only weak refs to tasks, so without this the event loop could garbage-collect
# a task before its background annotation POST completes (~seconds later). The
# done-callback discards each task once finished.
_BG_TASKS: set = set()


def _strip_code_fences(raw: str) -> str:
    """Strip a leading/trailing Markdown code fence from a model JSON body.

    Gemini routinely wraps a JSON array in a ```json … ``` fence; a bare
    `json.loads` then raises and the demo streams `n_findings=0` even though
    the risk_judge produced real findings (PROJECT_LOG Phase 14 root cause).
    Ported from `scripts/eval_cuad_spans.py:_parse_live_spans` so both the
    eval and the live server tolerate fenced output identically. Returns the
    input unchanged when there is no fence.
    """
    import re

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    return text


def _canonical_tag(raw_tag: str) -> str | None:
    """Map a Risk-Judge tag label to the canonical `schemas.Tag` enum value.

    The Judge drifts to display labels ("MAC Carve-Out", "Change of Control").
    Strategy: (1) exact match; (2) snake-case normalize and re-match; (3)
    substring heuristics keyed on the distinctive token of each tag family.
    Returns None when nothing matches confidently, so the caller leaves the
    raw value to fail loud rather than guessing wrong.
    """
    from .schemas import ALL_TAGS

    valid = set(ALL_TAGS)
    if raw_tag in valid:
        return raw_tag
    import re
    norm = re.sub(r"[^a-z0-9]+", "_", raw_tag.strip().lower()).strip("_")
    if norm in valid:
        return norm
    # Substring heuristics — order matters (more specific first).
    if "change" in norm and "control" in norm:
        return "change_of_control"
    if "assign" in norm:
        return "ip_assignment" if ("ip" in norm or "intellectual" in norm) else "anti_assignment"
    if "ip" in norm or "intellectual" in norm:
        return "ip_assignment"
    if "mac" in norm or "material_adverse" in norm or "mae" in norm:
        return "mac"
    if "vest" in norm:
        return "accelerated_vesting"
    if "exclus" in norm or "no_shop" in norm or "noshop" in norm or "solicit" in norm:
        return "exclusivity"
    if "compete" in norm:
        return "non_compete"
    if norm in ("none", "na", "n_a", "other"):
        return "none"
    return None


def _canonical_severity(raw_sev: str) -> str | None:
    """Map a Risk-Judge severity to the canonical `schemas.Severity` enum.

    Handles capitalization ("Block") and adjacent scales ("high"/"critical" ->
    block, "medium" -> watch, "low"/"informational" -> info). Returns None when
    unrecognized so the raw value fails loud.
    """
    s = raw_sev.strip().lower()
    if s in ("info", "watch", "block"):
        return s
    if s in ("high", "critical", "severe", "blocker", "blocking"):
        return "block"
    if s in ("medium", "moderate", "med", "escalate", "warn", "warning"):
        return "watch"
    if s in ("low", "informational", "minor", "none", "clear"):
        return "info"
    return None


def _coerce_risk_finding_raw(raw: dict) -> dict:
    """Normalize Risk-Judge output drift to the RiskFinding schema shape.

    The Risk Judge is a free-running LlmAgent; across runs it drifts on the
    *shape* of three fields even when the *content* is correct (observed live
    on microsoft_activision):

      * `judge_score` — emitted on a 1-10 (or 0-100) integer scale instead of
        the schema's 0.0-1.0 float (`ge=0, le=1`). We rescale: >1 and <=10 -> /10;
        >10 -> /100; then clamp to [0, 1].
      * `cited_spans_text` — emitted as a LIST of span strings instead of one
        joined string. We join with a blank line so the inline judges still see
        the full verbatim context.
      * `clause_id` — occasionally null when the Judge couldn't attribute a
        finding to a single clause. We fall back to the first `cited_spans`
        entry so the downstream clause_id->page/pdf_bbox join still has a key.
      * `tag` — emitted as a human-readable label ("MAC Carve-Out", "Change of
        Control", "Assignment", "Vesting Acceleration") instead of the canonical
        `Tag` enum value. We snake-case + substring-map back to the enum.
      * `severity` — emitted capitalized ("Block") or on an adjacent scale
        ("high"/"medium"/"low") instead of the `Severity` enum (info/watch/block).

    This is normalization, NOT silent error-hiding: the alternative is dropping
    every finding to a hard validation error (`n_findings=0` on a run that
    genuinely produced findings — the exact "demo looks clean when it's broken"
    failure the legal reviewer flagged, but inverted). Anything we can't
    confidently coerce is left as-is so `model_validate` still fails loud on it.
    Mutates and returns a shallow copy; the original is untouched.
    """
    if not isinstance(raw, dict):
        return raw
    out = dict(raw)

    tag = out.get("tag")
    if isinstance(tag, str):
        canon = _canonical_tag(tag)
        if canon is not None:
            out["tag"] = canon

    sev = out.get("severity")
    if isinstance(sev, str):
        canon_sev = _canonical_severity(sev)
        if canon_sev is not None:
            out["severity"] = canon_sev

    score = out.get("judge_score")
    if isinstance(score, bool):
        pass  # bool is an int subclass — leave it to fail loud
    elif isinstance(score, (int, float)):
        s = float(score)
        if s > 10:
            s = s / 100.0
        elif s > 1:
            s = s / 10.0
        out["judge_score"] = max(0.0, min(1.0, s))

    spans_text = out.get("cited_spans_text")
    if isinstance(spans_text, list):
        out["cited_spans_text"] = "\n\n".join(
            str(s) for s in spans_text if s is not None
        )

    # `clause_text` (required) is sometimes omitted entirely — the Judge puts
    # the verbatim text only in `cited_spans_text`. Fall back to that so the
    # finding validates (the two carry the same clause prose for these findings).
    if not out.get("clause_text"):
        fallback_text = out.get("cited_spans_text")
        if isinstance(fallback_text, str) and fallback_text.strip():
            out["clause_text"] = fallback_text

    if out.get("clause_id") in (None, ""):
        spans = out.get("cited_spans")
        if isinstance(spans, list) and spans and isinstance(spans[0], str):
            out["clause_id"] = spans[0]

    return out


async def _read_clauses_raw_from_session(runner, user_id: str, session_id: str) -> list:
    """Read the Parser's clause list from ADK session state (output_key='clauses').

    `gemini-3.5-flash` surfaces EMPTY text on the parser's streamed event even
    though ADK still writes the clause JSON to session state — so the cheaper
    event-text intercept (below) indexes 0 clauses and the clause_id->page join
    fails with a noisy (non-fatal) `join_clause_to_finding` error per finding.
    This reads the authoritative session-state value as a fallback. The
    classifiers consume the same `{clauses}` state var, so its clause ids match
    the ids the Risk Judge cites. Returns [] on any failure (best-effort).
    """
    try:
        import inspect
        sess = runner.session_service.get_session(
            app_name="ma-gatekeeper", user_id=user_id, session_id=session_id,
        )
        if inspect.isawaitable(sess):
            sess = await sess
        state = getattr(sess, "state", None) or {}
        raw = state.get("clauses")
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            return json.loads(_strip_code_fences(raw))
    except Exception as exc:  # noqa: BLE001 — best-effort, never fatal
        _LOG.warning("session-state clause read failed: %s", exc)
    return []


def _sniff_mime(raw: bytes) -> str:
    """Detect mime type from magic bytes — authoritative when present.

    EdgarTools Attachment has `is_html()` but no `mime_type` field, and
    EDGAR Ex 2.1 attachments are almost always `.htm` (3/3 in our 2024
    sample). Magic-byte sniffing is robust regardless of what
    EdgarTools claims: `%PDF-` is the PDF spec header; an HTML page
    starts with `<!doctype` or `<html` (after possible whitespace/BOM).
    Default to `text/html` because that's the empirical 2024 majority.
    """
    if raw[:5] == b"%PDF-":
        return "application/pdf"
    head = raw.lstrip(b"\xef\xbb\xbf \t\r\n")[:64].lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html") or head.startswith(b"<?xml"):
        return "text/html"
    # Conservative fallback: serve as HTML so the frontend iframe path
    # (not the PDF viewer path) handles it; mislabeling as PDF would
    # produce a "broken PDF" toast that hides the real content.
    return "text/html"


async def _get_artifact_cached(cik: str) -> tuple[bytes, str]:
    """Return cached `(bytes, mime_type)` for `cik`, fetching once on miss.

    Per-CIK asyncio.Lock + double-checked dict membership pattern: the
    second concurrent caller waits on the lock, then sees the cache
    populated and returns without fetching. Without this lock, the
    "open the demo, both /review-by-deal and /filing fire within
    50 ms" case double-hits SEC.

    Raises HTTPException(504) on timeout, (502) on EdgarTools error.
    Callers (route handlers) already validated deal existence + cik.
    """
    cached = _pdf_cache.get(cik)
    if cached is not None:
        return cached
    async with _pdf_locks[cik]:
        cached = _pdf_cache.get(cik)
        if cached is not None:
            return cached
        try:
            data = await asyncio.wait_for(
                _fetch_filing_pdf(cik), timeout=_PDF_FETCH_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail=f"EdgarTools fetch timed out for cik={cik} "
                       f"(>{_PDF_FETCH_TIMEOUT_SECONDS}s)",
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"EdgarTools fetch failed for cik={cik}: {exc}",
            ) from exc
        mime = _sniff_mime(data)
        artifact = (data, mime)
        _pdf_cache[cik] = artifact
        return artifact


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    init_tracing(project_name=os.environ.get("PHOENIX_PROJECT", "ma-gatekeeper"))
    # SEC requires a User-Agent on every request (10 req/sec limit). Set
    # the identity once at startup so EdgarTools is registered before
    # the first /review-by-deal hit.
    global _sec_ready
    try:
        from edgar import set_identity
        set_identity(SEC_USER_AGENT)
        _sec_ready = True
        _LOG.info("EdgarTools identity set: %s", SEC_USER_AGENT)
    except Exception as exc:
        _sec_ready = False
        _LOG.error(
            "Failed to set EdgarTools identity: %s. /review-by-deal will "
            "return 503 until this is resolved. SEC requires a valid "
            "User-Agent on every request.", exc,
        )
    _LOG.info("Allow-list size=%d", len(ALLOW_LIST))

    # SECURITY: REFLECT_OIDC_AUDIENCE empty on Cloud Run means /reflect
    # accepts unauthenticated calls. Detect Cloud Run via the K_SERVICE
    # env var (set automatically by the runtime) and log a loud ERROR so
    # ops alerting catches it. The per-request 503 in `oidc_dep` is the
    # actual gate; this log is the operator-visibility channel.
    cloud_run_service = os.environ.get("K_SERVICE")
    if cloud_run_service and not EXPECTED_OIDC_AUDIENCE:
        _LOG.error(
            "SECURITY: REFLECT_OIDC_AUDIENCE is empty on Cloud Run "
            "(K_SERVICE=%s). /reflect will return 503 until this is set "
            "to the deployed service URL.",
            cloud_run_service,
        )

    # Best-effort CIK validation on Cloud Run only — env-gated off in
    # local dev so the test suite (lifespan via TestClient) stays
    # offline. We log per-failed CIK but DO NOT crash the container; a
    # single delisted issuer would otherwise turn the morning of the
    # demo into a crashloop and take /review (the freeform upload path,
    # which doesn't need EDGAR at all) down with it.
    global _cik_unreachable
    _cik_unreachable = set()
    if os.environ.get("VALIDATE_ALLOW_LIST_ON_BOOT", "0") == "1" and _sec_ready:
        for entry in ALLOW_LIST:
            if not entry.cik:
                continue
            try:
                from edgar import Company
                co = Company(entry.cik)
                filings = co.get_filings(form="8-K")
                if not filings:
                    raise RuntimeError("no 8-K filings on file")
            except Exception as exc:
                _cik_unreachable.add(entry.cik)
                _LOG.error(
                    "Allow-list entry %s (cik=%s) failed lifespan validation: %s",
                    entry.id, entry.cik, exc,
                )

    yield

    # FastAPI shutdown phase. Drain any MCPToolset that an in-flight
    # `/reflect` worker constructed but didn't finalize before the
    # SIGTERM cascade (uncaught exception in the executor, cancellation
    # mid-cycle, etc.). Composes with `_run_introspection_agent_async`'s
    # per-call try/finally — `_aclose_one_with_timeout` is idempotent
    # via the `_MCP_CLOSED_ATTR` sentinel, so double-close is a no-op.
    try:
        from .reflector import shutdown_all_toolsets
        await shutdown_all_toolsets()
    except Exception as exc:
        _LOG.warning("MCP shutdown drain failed at lifespan exit: %s", exc)


app = FastAPI(title="M&A Gatekeeper", lifespan=lifespan)


# Security baseline: deny framing by default.
# design/PLAN.md §0.4 task 4 + design/TOOLING.md §4 — the iframe upside-swap
# kill-switch has fired (PROJECT_LOG 2026-05-24), so /reflect is no longer a
# candidate for cross-origin embedding. We set both the legacy X-Frame-Options
# header (older browsers) and the modern CSP frame-ancestors directive.
# If iframe is ever resurrected, widen frame-ancestors to the explicit
# marketing origin — never to '*'.
@app.middleware("http")
async def _frame_lockdown(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault(
        "Content-Security-Policy", "frame-ancestors 'none'"
    )
    return response


# CORS so the Next.js frontend on a different origin can call us.
app.add_middleware(
    CORSMiddleware,
    # Strip whitespace from each entry so "a.com, b.com" works as expected
    # (DevOps reviewer flagged the missing strip).
    allow_origins=[
        o.strip() for o in
        os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _check_passcode(passcode: str | None) -> None:
    """Fail-closed timing-safe passcode check.

    The previous version opened access if DEMO_PASSCODE was unset. That
    fails open on a misconfigured deploy; we now require the env var to
    be set and return 503 otherwise. Constant-time compare via hmac.
    """
    if not DEMO_PASSCODE:
        raise HTTPException(status_code=503,
                            detail="server misconfigured (no passcode)")
    if not passcode:
        raise HTTPException(status_code=401, detail="missing passcode")
    if not hmac.compare_digest(passcode, DEMO_PASSCODE):
        raise HTTPException(status_code=401, detail="invalid passcode")


def passcode_dep(x_demo_passcode: str | None = Header(default=None)) -> None:
    """FastAPI dependency reading passcode from header only.

    Query-string passcodes leak via Cloud Run access logs, so we accept
    only the X-Demo-Passcode header.
    """
    _check_passcode(x_demo_passcode)


async def oidc_dep(authorization: str | None = Header(default=None)) -> None:
    """Cloud Scheduler hits /reflect with an OIDC token in Authorization.

    Verify against the expected audience. Behavior when audience is empty:
      - Cloud Run (K_SERVICE set): refuse with 503 — empty audience would
        silently turn off OIDC verification on an internet-reachable
        process. Symmetric with the DEMO_PASSCODE fail-closed path.
      - localhost (K_SERVICE unset): skip — keeps `pytest` + `uvicorn`
        development flow working without forcing a real audience value.
    """
    if not EXPECTED_OIDC_AUDIENCE:
        if os.environ.get("K_SERVICE"):
            raise HTTPException(
                status_code=503,
                detail="server misconfigured (no OIDC audience)",
            )
        return  # localhost dev — Cloud Run IAM would gate in prod
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        from google.auth.transport import requests as gauth_requests
        from google.oauth2 import id_token
        info = id_token.verify_oauth2_token(
            token, gauth_requests.Request(), audience=EXPECTED_OIDC_AUDIENCE
        )
        if info.get("aud") != EXPECTED_OIDC_AUDIENCE:
            raise HTTPException(status_code=401, detail="bad audience")
    except HTTPException:
        # Don't wrap our own 401 — the message above is more specific
        # than "oidc verify failed: 401: bad audience" would be.
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"oidc verify failed: {exc}")


@app.get("/healthz")
@app.get("/health")
@app.get("/livez")
async def healthz() -> dict:
    # NOTE: the bare path `/healthz` is intercepted at the Google edge on this
    # Cloud Run service (returns a GFE HTML 404 that never reaches the
    # container; novel paths reach the app fine). `/health` and `/livez` are
    # un-poisoned aliases so external smoke-tests / liveness probes have a
    # path that actually returns 200. See manual_steps §11.3.
    return {"ok": True}


@app.get("/allow-list", dependencies=[Depends(passcode_dep)])
async def allow_list(include_uncurated: bool = False) -> dict:
    """Return the demo deals dropdown.

    By default hides uncurated entries (cik=='') so the dropdown can't
    surface a deal that would 503. Pass ?include_uncurated=1 for the
    operator console / curation tooling — the test suite uses this to
    monkeypatch a synthetic uncurated entry without faking the whole
    ALLOW_LIST.
    """
    entries = (
        ALLOW_LIST if include_uncurated else [d for d in ALLOW_LIST if d.cik]
    )
    return {"deals": [d.model_dump() for d in entries]}


def _sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


def _governing_law_hint_from_event(text: str) -> str | None:
    """Pure helper (GROUNDTRUTH_PLAN T1.2): derive a normalised jurisdiction
    hint from a cross_reference event payload.

    Tolerant by design — returns None for the CURRENT output (a bare findings
    list) and only extracts a hint from a future envelope shaped
    `{"governing_law": {"verbatim_clause": ..., "jurisdiction": ...}, "findings": [...]}`.
    The returned value is one of the map's five canonical jurisdictions, or None
    when undetected/ambiguous (the caller then renders the canonical default).
    Unit-tested in tests/test_citation_linker.py without the live pipeline.
    """
    from .citation_linker import normalize_jurisdiction
    from .schemas import GoverningLaw

    try:
        obj = json.loads(_strip_code_fences(text))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    gl_raw = obj.get("governing_law")
    if not isinstance(gl_raw, dict):
        return None
    try:
        gl = GoverningLaw.model_validate(gl_raw)
    except Exception:
        return None
    return normalize_jurisdiction(gl.jurisdiction or gl.verbatim_clause)


async def _stream_findings(
    filing_bytes: bytes, mime_type: str = "application/pdf"
) -> AsyncIterator[bytes]:
    """Run the agent and yield SSE events.

    Real ADK invocation pattern (Python-reviewer verified):
      runner.run_async(user_id, session_id, new_message=Content(parts=[Part.from_bytes(...)]))
    Yields Event objects with `.author`, `.content` (Content with `.parts`),
    `.actions`. We surface each as a server-sent event so the Next.js UI
    can populate the findings list live.
    """
    from google.adk.runners import InMemoryRunner
    from google.genai import types as gtypes

    from .agents import build_root_agent
    from .router import Thresholds, judge_and_route

    root = build_root_agent()
    runner = InMemoryRunner(agent=root, app_name="ma-gatekeeper")
    thresholds = Thresholds.from_json(
        os.environ.get("THRESHOLDS_JSON", "thresholds.json")
    )

    session_id = uuid.uuid4().hex
    user_id = "demo-user"
    # Guard for ADK SDK drift: in some 1.x releases InMemorySessionService
    # exposes a sync create_session, in others it's async. Try sync first,
    # await if needed.
    import inspect
    create_session = runner.session_service.create_session
    result = create_session(
        app_name="ma-gatekeeper", user_id=user_id, session_id=session_id,
    )
    if inspect.isawaitable(result):
        await result

    new_message = gtypes.Content(
        role="user",
        parts=[await _build_gemini_part(filing_bytes, mime_type)],
    )

    yield _sse({"event": "start"})

    # Parser output cache for D15 PDF-highlight provenance. The Parser
    # emits a JSON list of Clause records via `output_key="clauses"`;
    # we intercept the event-stream (cheaper + ADK-version-agnostic
    # than reaching into `runner.session_service`) and build a
    # `dict[clause_id -> Clause]` lookup that the Risk-Judge branch
    # below consults to authoritatively populate `page` + `pdf_bbox`
    # on each RiskFinding. Lookup is keyed by `Clause.id` because the
    # Router invariant pins `RiskFinding.clause_id == Clause.id`.
    # Empty dict means "Parser never emitted parseable clauses" — we
    # then leave whatever the Risk Judge produced (which is also
    # likely null) and the frontend degrades gracefully.
    from .schemas import Clause as _Clause
    clauses_by_id: dict[str, _Clause] = {}

    # Per-contract governing-law hint (GROUNDTRUTH_PLAN T1.2). Captured ONCE
    # from the cross_reference event (mirror of clauses_by_id). None until
    # detected; None means lookup_citation renders the canonical/Delaware
    # default with a visible "governing law not detected" label downstream.
    governing_law_hint: str | None = None

    n_emitted = 0
    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=new_message,
        ):
            # ADK Event: .author is agent name; .content has parts.
            author = getattr(event, "author", None)
            content = getattr(event, "content", None)
            parts = getattr(content, "parts", None) or []
            text_chunks = [getattr(p, "text", None) for p in parts]
            text = "\n".join(t for t in text_chunks if t)
            yield _sse({"event": "agent_output", "author": author, "text": text})

            # Intercept the Parser's clauses for the server-side join
            # below. Parse-failure here is NOT fatal: the demo path
            # tolerates a missing lookup (page/pdf_bbox stay null,
            # frontend skips the highlight pin) — failing loud here
            # would mask the actual product surface (the findings)
            # behind an infrastructure error. We log via SSE for
            # operator visibility but keep streaming.
            if author == "parser" and text and not clauses_by_id:
                try:
                    raw_clauses = json.loads(_strip_code_fences(text))
                except Exception as parse_exc:
                    yield _sse({
                        "event": "error",
                        "stage": "parse_parser_output",
                        "message": (
                            f"failed to json.loads parser output for "
                            f"pdf_bbox join: {parse_exc}. PDF-highlight "
                            f"pins will be skipped for this run."
                        ),
                    })
                    raw_clauses = []
                for raw_clause in raw_clauses:
                    try:
                        c = _Clause.model_validate(raw_clause)
                    except Exception:
                        # Per-clause validation failure — skip this
                        # one but keep the rest of the lookup usable.
                        continue
                    clauses_by_id[c.id] = c

            # Governing-law capture (GROUNDTRUTH_PLAN T1.2). Best-effort, once
            # per contract. Tolerant of BOTH the current cross_reference output
            # (a bare findings list -> hint stays None) and a future envelope
            # `{governing_law: {...}, findings: [...]}`. Non-breaking: when no
            # governing_law is present the hint stays None and lookup_citation
            # renders the canonical default exactly as before.
            if author == "cross_reference" and text and governing_law_hint is None:
                governing_law_hint = _governing_law_hint_from_event(text)

            # When the risk_judge emits findings, route each and stream
            # the lane decision. In production we wire ADK's
            # structured-output / Pydantic binding so we don't json.loads
            # the text body; until that's done, parse-failure must FAIL
            # LOUD (yield an error SSE) so the demo doesn't look clean
            # when it's actually broken (legal reviewer flagged this).
            if author == "risk_judge" and text:
                # PDF-pin provenance fallback: if the event-text intercept above
                # indexed no clauses, try the Parser's session-state clause list
                # (output_key="clauses"). Best-effort and SILENT — for HTML
                # exhibits the parser surfaces no server-indexable clause list
                # (and HTML has no pages/pdf_bbox anyway), so this commonly stays
                # empty; the join below then suppresses its per-finding error
                # because there's no index to legitimately check against. When a
                # PDF deal DOES populate state, this recovers page/pdf_bbox.
                if not clauses_by_id:
                    for raw_clause in await _read_clauses_raw_from_session(
                        runner, user_id, session_id
                    ):
                        try:
                            c = _Clause.model_validate(raw_clause)
                        except Exception:
                            continue
                        clauses_by_id[c.id] = c
                try:
                    findings_list = json.loads(_strip_code_fences(text))
                except Exception as parse_exc:
                    yield _sse({
                        "event": "error",
                        "stage": "parse_risk_judge_output",
                        "message": (
                            f"failed to json.loads risk_judge output: "
                            f"{parse_exc}. First 200 chars: {text[:200]!r}"
                        ),
                    })
                    findings_list = []
                from .schemas import RiskFinding
                request_trace_id = _current_trace_id()
                for raw in findings_list:
                    raw = _coerce_risk_finding_raw(raw)
                    try:
                        finding = RiskFinding.model_validate(raw)
                    except Exception as val_exc:
                        # Fail loud — silently dropping a finding because
                        # of validation drift contradicts the "demo
                        # doesn't look clean when it's broken" mandate
                        # the parse-failure branch above already honors.
                        yield _sse({
                            "event": "error",
                            "stage": "validate_risk_judge_finding",
                            "message": (
                                f"RiskFinding.model_validate failed: "
                                f"{val_exc}. Raw (first 200 chars): "
                                f"{str(raw)[:200]!r}"
                            ),
                        })
                        continue
                    # Authoritative server-side override: the LLM cannot
                    # know its own trace_id, so any value it hallucinated
                    # is discarded in favor of the active OTel context.
                    if request_trace_id is not None:
                        finding = finding.model_copy(
                            update={"trace_id": request_trace_id}
                        )

                    # PDF-highlight provenance (plan §7 D15). Server-
                    # side join: REPLACES `page` + `pdf_bbox` with the
                    # authoritative Parser value, regardless of what
                    # (if anything) the Risk Judge emitted. Mirrors the
                    # trace_id override pattern — one source of truth
                    # per field, and it is NOT the model. The LLM's
                    # output for these fields is structurally discarded
                    # below via `model_copy(update=...)` whether the
                    # clause lookup succeeds or fails.
                    clause_record = clauses_by_id.get(finding.clause_id)
                    if clause_record is None:
                        # Only FAIL LOUD when we actually HAVE a clause index to
                        # check against: a miss there means the Risk Judge cited
                        # a clause the Parser didn't emit (a real linkage bug —
                        # hallucinated id or namespace mismatch), and the demo
                        # should NOT look clean when that's broken. But when
                        # `clauses_by_id` is EMPTY there is no index at all —
                        # the normal case for HTML EDGAR exhibits (no pages /
                        # pdf_bbox exist) and for models whose parser output the
                        # server can't index — so the per-finding "miss" is
                        # expected, not a bug. Suppressing the error then keeps
                        # the stream clean (the frontend renders every error SSE
                        # as a red banner); we still null page/pdf_bbox so the
                        # PDF pane can't be misled by a hallucinated value, and
                        # the finding itself still streams (legal reviewer:
                        # better a finding without a pin than no finding).
                        if clauses_by_id:
                            yield _sse({
                                "event": "error",
                                "stage": "join_clause_to_finding",
                                "clause_id": finding.clause_id,
                                "message": (
                                    f"RiskFinding.clause_id={finding.clause_id!r}"
                                    f" not in Parser's clause output "
                                    f"({len(clauses_by_id)} clauses indexed). "
                                    f"page+pdf_bbox will be null for this "
                                    f"finding; PDF highlight pin will not "
                                    f"render."
                                ),
                            })
                        finding = finding.model_copy(update={
                            "page": None, "pdf_bbox": None,
                        })
                    else:
                        page_override = clause_record.page
                        bbox_override = clause_record.pdf_bbox
                        # Offline pdfplumber fallback: if the Parser
                        # didn't populate pdf_bbox AND the source is
                        # PDF, recompute from char offsets. Pure-Python,
                        # in-process, zero quota — see
                        # `agent/pdf_bbox.py` for the limitation note
                        # on Gemini-vs-pdfplumber offset drift and the
                        # 5s per-page timeout.
                        if (
                            bbox_override is None
                            and mime_type == "application/pdf"
                        ):
                            from .pdf_bbox import extract_bbox_from_pdf
                            bbox_override = extract_bbox_from_pdf(
                                filing_bytes,
                                page_override,
                                clause_record.char_start,
                                clause_record.char_end,
                            )
                        finding = finding.model_copy(update={
                            "page": page_override,
                            "pdf_bbox": bbox_override,
                        })
                    # Inline judge call. In a future iteration this moves
                    # inside the Risk Judge sub-agent so it runs INSIDE
                    # the ADK span (span_id linking is then automatic).
                    from .evaluators import run_inline_judges
                    h_score, h_label, f_score, f_label = run_inline_judges(
                        context=finding.cited_spans_text,
                        explanation=finding.explanation,
                        clause_text=finding.clause_text,
                        tag=finding.tag,
                    )
                    decision = judge_and_route(
                        finding,
                        h_score=h_score, h_label=h_label,
                        f_score=f_score, f_label=f_label,
                        thresholds=thresholds,
                    )

                    # ----- Citation-linkage layer (design/STATUTE_LAYER.md §2.1) -----
                    # Synchronous cold path: deterministic map lookup ONLY. This
                    # is the sole citation rendered to users; the LLM proposer
                    # below never reaches user-facing output.
                    #
                    # GROUNDTRUTH_PLAN T1.2: the rendered citation now depends on
                    # (a) the per-contract governing-law hint — fail-closed, so a
                    # NY-governed clause never gets a Delaware case — and (b) the
                    # finding's severity — case-law (heavy artillery) is gated to
                    # the statute for the same tag/jurisdiction on watch/info
                    # findings when a statute exists, else the case is KEPT (not
                    # blanked). The OFFLINE eval grades the RAW map (pre-gate); the
                    # gate is render-only, so the script and the Phoenix rail stay
                    # consistent on the raw map.
                    from .citation_linker import (
                        _run_llm_proposer_and_annotate,
                        lookup_citation,
                        severity_gated_citation,
                    )
                    static_ref = lookup_citation(
                        finding.tag, jurisdiction_hint=governing_law_hint
                    )
                    static_ref = severity_gated_citation(
                        static_ref, tag=finding.tag, severity=finding.severity
                    )
                    finding = finding.model_copy(
                        update={"citation_ref": static_ref}
                    )

                    # Capture the 16-hex span_id BEFORE create_task — OTel context
                    # does not propagate across create_task, and the BG annotation
                    # needs the span_id, not finding.trace_id (the 32-hex trace id).
                    current_span_id_hex = _current_span_id()
                    # Flush the exporter so the BG task's annotation POST (seconds
                    # later) doesn't race the parent span being exported. On a
                    # False/timeout return the BG task writes with sync=True.
                    flushed = _force_flush_spans(timeout_millis=500)
                    _LOG.info(
                        "span force_flush before citation annotation: %s", flushed
                    )
                    # Fire-and-forget: proposer + Python comparator run in the
                    # background and write a Phoenix annotation. NEVER blocks
                    # /review; NEVER mutates the user-facing finding. The strong
                    # ref in _BG_TASKS keeps the loop from GC-ing it mid-flight.
                    _task = asyncio.create_task(
                        _run_llm_proposer_and_annotate(
                            clause_text=finding.clause_text,
                            tag=finding.tag,
                            static_ref=static_ref,
                            span_id=current_span_id_hex,
                            flushed=flushed,
                        )
                    )
                    _BG_TASKS.add(_task)
                    _task.add_done_callback(_BG_TASKS.discard)

                    # Unified "finding" event carries both the RiskFinding
                    # and its routing decision so the frontend doesn't
                    # have to correlate two parallel streams. Invariant:
                    # decision.finding_id == finding.clause_id (see router).
                    # exclude=_EVAL_ONLY_FIELDS is belt-and-suspenders on top of
                    # the RiskFinding.model_dump override (Guard #2) — eval-only
                    # linker_* fields must never reach the wire.
                    from .schemas import _EVAL_ONLY_FIELDS
                    yield _sse({
                        "event": "finding",
                        "finding": finding.model_dump(
                            mode="json", exclude=_EVAL_ONLY_FIELDS
                        ),
                        "decision": decision.model_dump(mode="json"),
                        "h_score": h_score, "f_score": f_score,
                    })
                    n_emitted += 1
    except Exception as exc:
        _LOG.exception("stream failed")
        yield _sse({"event": "error", "stage": "stream_findings", "message": str(exc)})

    yield _sse({"event": "done", "n_findings": n_emitted})


def _sse_response(stream: AsyncIterator[bytes]) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Cloud Run respects this; ensures the front-end proxy
            # doesn't buffer the SSE stream until end-of-response.
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/review", dependencies=[Depends(passcode_dep)])
async def review(request: Request,
                 file: UploadFile = File(...)) -> StreamingResponse:
    # Upload size cap (DevOps reviewer): prevent /review from being
    # weaponized into a Vertex billing incident or OOM. Check the
    # Content-Length header up front, AND read in bounded chunks so a
    # client that lies about Content-Length still can't blow past the cap.
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"upload exceeds MAX_UPLOAD_BYTES={MAX_UPLOAD_BYTES}",
        )
    pdf_bytes = bytearray()
    chunk_size = 1024 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        pdf_bytes.extend(chunk)
        if len(pdf_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"upload exceeds MAX_UPLOAD_BYTES={MAX_UPLOAD_BYTES}",
            )
    # /review's freeform upload path is documented as PDF-only via the
    # browser file picker; trust the caller's claim. If a user uploads
    # an HTML blob with .pdf extension Gemini will simply parse it as
    # plain text.
    return _sse_response(_stream_findings(bytes(pdf_bytes), "application/pdf"))


class ReviewByDealRequest(BaseModel):
    """JSON body for /review-by-deal. Promoted from a query param so the
    frontend can use a single `Content-Type: application/json` shape
    across /review-by-deal and any future structured-input endpoints,
    instead of mixing query-string + body forms."""

    deal_id: str


@app.post("/review-by-deal", dependencies=[Depends(passcode_dep)])
async def review_by_deal(body: ReviewByDealRequest) -> StreamingResponse:
    deal = _resolve_deal_for_pdf(body.deal_id)
    filing_bytes, mime_type = await _get_artifact_cached(deal.cik)
    return _sse_response(_stream_findings(filing_bytes, mime_type))


def _resolve_deal_for_pdf(deal_id: str):
    """Shared lookup + curation/reachability checks used by both
    /review-by-deal and /filing. Raises HTTPException; never returns
    a half-validated entry."""
    if not _sec_ready:
        raise HTTPException(
            status_code=503,
            detail="SEC EdgarTools identity not initialized at startup",
        )
    deal = next((d for d in ALLOW_LIST if d.id == deal_id), None)
    if not deal:
        raise HTTPException(status_code=404, detail=f"unknown deal_id {deal_id}")
    if not deal.cik:
        raise HTTPException(
            status_code=503,
            detail="allow-list deal not yet curated (HANDOFF.md D10)",
        )
    if deal.cik in _cik_unreachable:
        raise HTTPException(
            status_code=503,
            detail=f"deal {deal.id} (cik={deal.cik}) failed lifespan validation",
        )
    return deal


_MIME_EXT = {
    "application/pdf": "pdf",
    "text/html": "html",
}


@app.get("/filing/{deal_id}", dependencies=[Depends(passcode_dep)])
async def filing(
    request: Request,
    deal_id: str = Path(..., pattern=r"^[a-z0-9_]+$"),
) -> Response:
    """Serve the 8-K Ex 2.1 attachment for an allow-list deal.

    Renamed from `/pdf-proxy` after we discovered EDGAR Ex 2.1
    attachments are almost always HTML, not PDF (3/3 sampled 2024
    8-Ks). The response Content-Type now reflects the actual artifact
    so the frontend can branch on it (react-pdf for application/pdf,
    sandboxed iframe for text/html).

    Why this exists: the frontend needs the original filing artifact
    so a viewer pane can render it alongside the agent's findings.
    Serving the same bytes the agent reviewed (via the shared
    `_pdf_cache`) keeps the user's view and the agent's findings
    perfectly aligned — no risk of the agent reviewing v1 of the
    document while the viewer shows v2.

    Response headers:
      Content-Type — actual sniffed mime (pdf or html);
      Content-Disposition inline for in-tab render;
      X-Content-Type-Options: nosniff so a mislabeled artifact can't
        be browser-rendered as a different type than declared;
      Cross-Origin-Resource-Policy: cross-origin so a pdfjs Web Worker
        or HTML iframe can fetch this resource from a different
        eTLD+1 (Vercel frontend, Cloud Run backend);
      Cache-Control immutable since filed 8-K Ex 2.1 doesn't change;
      ETag + 304 short-circuit on a soft reload.

    Passcode-protected: an unauthenticated route on top of a 10 req/s
    SEC identity throttle is a cost amplifier and a reputation risk.
    """
    deal = _resolve_deal_for_pdf(deal_id)
    artifact, mime_type = await _get_artifact_cached(deal.cik)
    etag = f'W/"{hashlib.sha256(artifact).hexdigest()[:16]}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    ext = _MIME_EXT.get(mime_type, "bin")
    return Response(
        content=artifact,
        media_type=mime_type,
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=86400, immutable",
            "Content-Disposition": f'inline; filename="{deal_id}-ex21.{ext}"',
            "X-Content-Type-Options": "nosniff",
            "Cross-Origin-Resource-Policy": "cross-origin",
        },
    )


async def _fetch_ex21_url(url: str) -> bytes:
    """GET a pinned EX-2.1 artifact from the SEC archives.

    SEC requires a descriptive User-Agent and throttles at 10 req/s; the
    per-CIK cache + lock in `_get_artifact_cached` keep us far under that.
    `follow_redirects` because EDGAR occasionally 301s archive paths.
    """
    import httpx

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(
            url,
            headers={"User-Agent": SEC_USER_AGENT},
            timeout=_PDF_FETCH_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.content


async def _fetch_filing_pdf(cik: str) -> bytes:
    """Fetch the merger-agreement Exhibit 2.1 for the given CIK.

    Curated demo deals carry a pinned `ex21_url` (the exact SEC-archive URL
    of the merger 8-K's EX-2.1). We GET it directly — deterministic, and
    immune to two failure modes of latest-filing navigation observed live
    against EDGAR for cik 718877: (1) a CLOSED merger's most recent 8-K is a
    post-close filing with NO EX-2.1 (so `get_filings("8-K")[0]` is wrong),
    and (2) EdgarTools' `attachment.exhibit_number` does not reliably equal
    "2.1" even on the correct filing. Both produced the demo's 502.

    Uncurated entries (no `ex21_url`) fall back to the legacy EdgarTools
    latest-8-K search via `attachment.download`.
    """
    entry = next(
        (e for e in ALLOW_LIST if e.cik == cik and e.ex21_url), None
    )
    if entry is not None:
        return await _fetch_ex21_url(entry.ex21_url)

    loop = asyncio.get_running_loop()

    def _sync() -> bytes:
        import tempfile
        from pathlib import Path
        from edgar import Company

        co = Company(cik)
        filings = co.get_filings(form="8-K")
        if not filings:
            raise RuntimeError(f"No 8-K filings found for CIK {cik}")
        filing = filings[0]  # latest
        attachments = getattr(filing, "attachments", None) or []
        ex2 = next(
            (a for a in attachments
             if "2.1" in (getattr(a, "exhibit_number", "") or "")),
            None,
        )
        if ex2 is None:
            raise RuntimeError(f"No Ex 2.1 attachment on latest 8-K for CIK {cik}")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ex21.pdf"
            ex2.download(str(target))
            return target.read_bytes()

    return await loop.run_in_executor(None, _sync)


@app.post("/reflect", dependencies=[Depends(oidc_dep)])
async def reflect() -> dict:
    """Cloud Scheduler endpoint — OIDC-protected.

    The Reflector loop is genuinely synchronous (Phoenix HTTP under the
    hood), so we offload to a worker thread to avoid blocking the event
    loop for the duration of the nightly cycle.
    """
    from .reflector import run_reflection_cycle
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_reflection_cycle)


# ---------------------------------------------------------------------------
# §11 Build #3 + §12 — Reflector-as-LoopAgent on-demand endpoint.
# ---------------------------------------------------------------------------
# Distinct from `/reflect` (the OIDC-gated nightly cron): `/reflect/loop`
# is the "Run Reflector now" button surface. Passcode-gated (mirrors
# `/portfolio`'s posture), streams SSE events from the LoopAgent body,
# and emits a terminal `auto_promoted` or `no_promotion` event.
#
# The hard-gate contract (Phoenix MCP `list_traces` per iteration) is
# enforced in `reflector_loop._run_one_iteration`; this endpoint is the
# thin SSE adapter.


class ReflectorLoopRequest(BaseModel):
    """JSON body for `/reflect/loop`. `deal_id` is optional — when
    present the loop surfaces it on every event payload so the frontend
    can correlate the running loop with the currently-open deal pane.

    `lookback_hours` defaults to 720 (30 days) so the hard-gate
    `list_traces` call surfaces historic `risk_judge_gate=escalate`
    annotations — the demo's escalations were captured days before the
    "SELF-IMPROVE NOW" click, and a 24h window would miss them and make
    the loop early-exit on "no_traces". Operators can narrow it per call.
    """

    deal_id: str | None = None
    lookback_hours: int = int(os.environ.get("REFLECTOR_LOOP_LOOKBACK_HOURS", "720"))


async def _stream_reflector_loop_events(
    deal_id: str | None,
    lookback_hours: int = 720,
) -> AsyncIterator[bytes]:
    """SSE adapter for `run_reflector_loop`.

    Mirrors the `_stream_findings` shape: yields one `data: <json>\n\n`
    frame per `ReflectorLoopEvent`, then a terminal `done` frame so the
    frontend can close the stream cleanly. Exceptions are surfaced as
    an `error` SSE event before the terminal `done`.
    """
    from .reflector_loop import run_reflector_loop

    n_events = 0
    try:
        async for event in run_reflector_loop(
            deal_id=deal_id, lookback_hours=lookback_hours,
        ):
            n_events += 1
            yield _sse({"event": "reflector_loop", **event.model_dump(mode="json")})
    except Exception as exc:
        _LOG.exception("/reflect/loop stream failed")
        yield _sse({
            "event": "error",
            "stage": "reflector_loop_stream",
            "message": str(exc),
        })
    yield _sse({"event": "done", "n_events": n_events})


@app.post("/reflect/loop", dependencies=[Depends(passcode_dep)])
async def reflect_loop(body: ReflectorLoopRequest) -> StreamingResponse:
    """Trigger one Reflector LoopAgent run on demand.

    Passcode-gated (NOT OIDC) — this is the operator-visible "Run
    Reflector now" button, not the nightly cron. Mirrors the security
    posture of `/portfolio`. The `_frame_lockdown` middleware is global,
    so X-Frame-Options + CSP frame-ancestors apply automatically.
    """
    return _sse_response(
        _stream_reflector_loop_events(body.deal_id, body.lookback_hours)
    )


# ---------------------------------------------------------------------------
# Fix 7 — Portfolio Analyst endpoint (1M-context cross-deal cluster output).
# ---------------------------------------------------------------------------
# One Gemini 3 Pro call against all 30 Internal-30 contracts concatenated.
# Returns a synchronous JSON response (NOT SSE) — the output is one
# structured `PortfolioReport`, not a stream. Mirrors the security
# posture of /review: passcode-gated, fail-closed on missing config.
# Mock-default in dev; PORTFOLIO_LIVE=1 environment flag opts in to the
# live ADK Runner path (mirrors VALIDATE_ALLOW_LIST_ON_BOOT=1).


@app.post("/portfolio", dependencies=[Depends(passcode_dep)])
async def portfolio() -> dict:
    """Run the Portfolio Analyst over the Internal-30 contract set.

    Live vs mock:
      - PORTFOLIO_LIVE unset (default): returns the canonical mock
        fixture deterministically. Quota-free. Reproducible.
      - PORTFOLIO_LIVE=1: invokes `make_live_portfolio()` which is
        wired by the operator on D9 (currently raises
        NotImplementedError). When wired, the live path uploads the 30
        EX-2.1 bytes via the existing `_ensure_files_api_upload` cache
        and runs one Gemini 3 Pro call against the concatenated input.

    `trace_id` is populated server-side from the active OTel span
    context — never by the LLM — mirroring the RiskFinding pattern.
    """
    from .portfolio_analyst import (
        load_sample_contracts,
        make_live_portfolio,
        make_mock_portfolio,
    )

    contracts = load_sample_contracts()

    if os.environ.get("PORTFOLIO_LIVE", "0") == "1":
        agent = make_live_portfolio()  # raises NotImplementedError until wired
    else:
        agent = make_mock_portfolio()

    # The agent call is sync-ish (mock is trivial; live wraps an ADK
    # Runner). Offload to a thread so the event loop stays free.
    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(None, agent, contracts)

    # Server-populated trace_id (mirrors RiskFinding pattern in
    # _stream_findings). The LLM's value, if any, is discarded.
    trace_id = _current_trace_id()
    report = report.model_copy(update={"trace_id": trace_id})

    return report.model_dump(mode="json")
