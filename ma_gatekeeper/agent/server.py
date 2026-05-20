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

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .instrumentation import init_tracing

_LOG = logging.getLogger(__name__)


# The 5 pre-indexed deals (plan §5.5). Curate on D10 (HANDOFF.md).
ALLOW_LIST: list[dict] = [
    {"id": "deal_01", "name": "(curated)", "filing": "8-K/Ex 2.1", "cik": ""},
    {"id": "deal_02", "name": "(curated)", "filing": "8-K/Ex 2.1", "cik": ""},
    {"id": "deal_03", "name": "(curated)", "filing": "8-K/Ex 2.1", "cik": ""},
    {"id": "deal_04", "name": "(curated)", "filing": "8-K/Ex 2.1", "cik": ""},
    {"id": "deal_05", "name": "(curated)", "filing": "8-K/Ex 2.1", "cik": ""},
]


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
    yield


app = FastAPI(title="M&A Gatekeeper", lifespan=lifespan)

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

    Verify against the expected audience. In dev (no audience configured)
    we skip — that lets local tests run, but means `--no-allow-unauthenticated`
    is the deployment safety net (HANDOFF.md).
    """
    if not EXPECTED_OIDC_AUDIENCE:
        return  # dev/local — auth is enforced by Cloud Run IAM
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
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"oidc verify failed: {exc}")


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.get("/allow-list", dependencies=[Depends(passcode_dep)])
async def allow_list() -> dict:
    return {"deals": ALLOW_LIST}


def _sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


async def _stream_findings(pdf_bytes: bytes) -> AsyncIterator[bytes]:
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
        parts=[gtypes.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")],
    )

    yield _sse({"event": "start"})

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
                for raw in findings_list:
                    try:
                        finding = RiskFinding.model_validate(raw)
                    except Exception:
                        continue
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
                    yield _sse({
                        "event": "decision",
                        "finding_id": decision.finding_id,
                        "lane": decision.lane,
                        "h_score": h_score, "f_score": f_score,
                    })
    except Exception as exc:
        _LOG.exception("stream failed")
        yield _sse({"event": "error", "message": str(exc)})

    yield _sse({"event": "done"})


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
    return _sse_response(_stream_findings(bytes(pdf_bytes)))


@app.post("/review-by-deal", dependencies=[Depends(passcode_dep)])
async def review_by_deal(deal_id: str) -> StreamingResponse:
    if not _sec_ready:
        raise HTTPException(
            status_code=503,
            detail="SEC EdgarTools identity not initialized at startup; "
                   "see server logs",
        )
    deal = next((d for d in ALLOW_LIST if d["id"] == deal_id), None)
    if not deal:
        raise HTTPException(status_code=404, detail=f"unknown deal_id {deal_id}")
    if not deal.get("cik"):
        raise HTTPException(status_code=503,
                            detail="allow-list deal not yet curated (HANDOFF.md D10)")
    pdf_bytes = await _fetch_filing_pdf(deal["cik"])
    return _sse_response(_stream_findings(pdf_bytes))


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
