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
import uuid
from typing import AsyncIterator

from collections import defaultdict
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
# the existing handle instead of re-uploading. Files auto-expire at 48h
# on Google's side; we don't proactively delete because the 5-deal demo
# benefits from the cache. Keyed by content sha256 so byte-identical
# re-fetches dedupe even when the cache_key (CIK) wasn't passed.
_files_api_uri_cache: dict[str, str] = {}
_files_api_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
# Polling budget for Files API state transitions (PROCESSING → ACTIVE).
# Typical 2 MB upload settles in <2 s; allow 30 s for a 50 MB PDF.
_FILES_API_POLL_TOTAL_SECONDS = 30.0


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


async def _ensure_files_api_upload(data: bytes, mime_type: str) -> str:
    """Upload `data` to Gemini's Files API and return the file URI.

    Caches by content sha256 so a re-fetch of the same artifact reuses
    the existing handle. Per-hash asyncio.Lock prevents the same race
    the byte cache guards against — two concurrent large uploads of
    the same artifact would otherwise double-charge quota.

    Raises HTTPException(502) on upload failure, (504) on PROCESSING
    timeout, (502) on FAILED state. Callers (route handlers) propagate.
    """
    sha = hashlib.sha256(data).hexdigest()
    cached = _files_api_uri_cache.get(sha)
    if cached is not None:
        return cached
    async with _files_api_locks[sha]:
        cached = _files_api_uri_cache.get(sha)
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
            raise HTTPException(
                status_code=502,
                detail=f"Gemini Files API upload failed: {exc}",
            ) from exc
        _files_api_uri_cache[sha] = uri
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
async def healthz() -> dict:
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

            # When the risk_judge emits findings, route each and stream
            # the lane decision. In production we wire ADK's
            # structured-output / Pydantic binding so we don't json.loads
            # the text body; until that's done, parse-failure must FAIL
            # LOUD (yield an error SSE) so the demo doesn't look clean
            # when it's actually broken (legal reviewer flagged this).
            if author == "risk_judge" and text:
                try:
                    findings_list = json.loads(text)
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
                    # Unified "finding" event carries both the RiskFinding
                    # and its routing decision so the frontend doesn't
                    # have to correlate two parallel streams. Invariant:
                    # decision.finding_id == finding.clause_id (see router).
                    yield _sse({
                        "event": "finding",
                        "finding": finding.model_dump(mode="json"),
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


async def _fetch_filing_pdf(cik: str) -> bytes:
    """Fetch the latest 8-K Exhibit 2.1 for the given CIK via edgartools.

    EdgarTools attachment.download(path) writes to disk and returns a
    path. We pass a temp path and read the bytes back.
    """
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
