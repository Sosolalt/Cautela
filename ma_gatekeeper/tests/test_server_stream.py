"""Tests for the SSE-emission seam in `_stream_findings`.

The cross-cutting bug the original schema review missed: `trace_id`
(formerly `arize_trace_id`) was REQUIRED on `RiskFinding` but had no
server-side producer, so the LLM's hallucinated value flowed onto the
SSE wire and the frontend trace pane loaded broken links.

Tests here pin the contract:
  1. Schema accepts a finding WITHOUT trace_id (proves the field is
     producer-optional, not LLM-required).
  2. Server overrides whatever the LLM produced with the active OTel
     trace_id.
  3. Validation failure emits a loud SSE error event, NOT silent drop —
     honors the legal-reviewer "fail loud" mandate cited in
     `agent/server.py:330-332`.
  4. PDF-highlight provenance (plan §7 D15): the SSE finding event
     now carries `page` + `pdf_bbox` joined from the Parser's clause
     record, with pdfplumber as the offline fallback when the source
     is PDF and the Parser didn't populate the bbox.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import types

import pytest

from agent.schemas import RiskFinding


def test_risk_finding_schema_does_not_require_llm_to_supply_trace_id():
    """The original Issue 3 bug: `arize_trace_id` was a required str
    that no producer populated. New contract: server is sole producer."""
    finding = RiskFinding(
        clause_id="x",
        clause_text="...",
        tag="change_of_control",
        severity="block",
        judge_score=0.9,
        cited_spans=["x"],
        cited_spans_text="...",
        explanation="...",
        # NO trace_id — must validate.
    )
    assert finding.trace_id is None


def test_risk_finding_schema_no_longer_uses_vendor_name():
    """`arize_trace_id` was a vendor-name lie — it's an OTel concept,
    Phoenix is just the viewer. Pin the rename so a refactor doesn't
    silently reintroduce it (which would break the frontend that now
    reads `.trace_id`)."""
    fields = RiskFinding.model_fields
    assert "trace_id" in fields
    assert "arize_trace_id" not in fields


def test_current_trace_id_returns_none_outside_active_span():
    """In the unit-test harness there's no instrumented request, so
    `_current_trace_id` must return None — not an all-zero hex (which
    would Phoenix-404), not raise. Frontend gates on null."""
    from agent.server import _current_trace_id

    result = _current_trace_id()
    # Either None (no OTel installed / NoOp) or a valid 32-char hex
    # (some test runners initialize the SDK globally). Both are correct.
    assert result is None or re.fullmatch(r"^[0-9a-f]{32}$", result)


@pytest.fixture
def ot():
    """Skip the format-specific tests if opentelemetry isn't installed.
    The fallback path (None on import error) is exercised by the
    `_returns_none_outside_active_span` test above."""
    return pytest.importorskip("opentelemetry.trace")


def test_current_trace_id_format_is_lowercase_hex_no_prefix(monkeypatch, ot):
    """If a trace is active, the formatted value MUST be 32 chars,
    lowercase, no `0x` prefix — exactly what Phoenix's URL router
    expects. A `0x`-prefixed or uppercase value would silently 404."""
    import agent.server as srv

    class _FakeCtx:
        trace_id = 0x4f88c63ab2d1e9a5c7b04612d8e3aa11

    class _FakeSpan:
        def get_span_context(self):
            return _FakeCtx()

    # _current_trace_id lazy-imports `from opentelemetry.trace import
    # get_current_span` on every call, so patching the module attribute
    # is what reaches into the helper.
    monkeypatch.setattr(ot, "get_current_span", lambda: _FakeSpan())
    result = srv._current_trace_id()
    assert result is not None
    assert re.fullmatch(r"^[0-9a-f]{32}$", result), result
    assert not result.startswith("0x")
    assert result == result.lower()


def test_current_trace_id_returns_none_on_zero_trace(monkeypatch, ot):
    """A NoOp span carries trace_id=0; the all-zero hex would Phoenix-404
    silently. Return None so the frontend hides the trace tab."""
    import agent.server as srv

    class _FakeCtx:
        trace_id = 0

    class _FakeSpan:
        def get_span_context(self):
            return _FakeCtx()

    monkeypatch.setattr(ot, "get_current_span", lambda: _FakeSpan())
    assert srv._current_trace_id() is None


# ---------------------------------------------------------------------------
# Frame-lockdown middleware (design/TOOLING.md §4 task 4 — Skeptic Round-2)
# ---------------------------------------------------------------------------
# The iframe upside-swap kill-switch fired on 2026-05-24 (TOOLING.md §4.3),
# which means /reflect (and every other surface) must refuse cross-origin
# framing. The middleware was added Day-1 (agent/server.py:_frame_lockdown)
# but never tested — Skeptic Round-2 correctly flagged "set" as a code-read
# claim, not verified behavior. These tests close that loop by asserting
# both headers land on a real response from a real route.

def test_frame_lockdown_sets_x_frame_options_deny_on_healthz():
    """Cheapest possible probe: GET /healthz is unauthenticated and always
    200s. If the middleware is wired, X-Frame-Options: DENY must land on
    the response. If a future refactor strips the middleware, this test
    flips red before the iframe-clickjacking gap reopens."""
    from fastapi.testclient import TestClient
    from agent import server as srv

    with TestClient(srv.app) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "DENY"


def test_frame_lockdown_sets_csp_frame_ancestors_none_on_healthz():
    """The modern half of the same lockdown — CSP frame-ancestors 'none'.
    Older browsers honor X-Frame-Options; modern browsers prefer CSP. Both
    must be present (TOOLING.md §4 task 4)."""
    from fastapi.testclient import TestClient
    from agent import server as srv

    with TestClient(srv.app) as client:
        resp = client.get("/healthz")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp, csp


def test_frame_lockdown_applies_to_reflect_endpoint_regardless_of_status(monkeypatch):
    """The headers must land on /reflect responses *regardless of status*
    — a 401-without-headers would still allow an attacker to frame the
    error-page surface. We simulate a Cloud Run-shaped environment
    (K_SERVICE set + REFLECT_OIDC_AUDIENCE empty) so oidc_dep fail-closes
    with 503 (matches the prod posture per `oidc_dep` lines 462-467);
    headers must still be present."""
    from fastapi.testclient import TestClient
    from agent import server as srv

    # Force the fail-closed path so we hit a real non-200 on /reflect
    # without needing a live Google IDP. Symmetric with how server.py
    # itself checks K_SERVICE — this is the prod posture in test.
    monkeypatch.setenv("K_SERVICE", "ma-gatekeeper-test")
    monkeypatch.setattr(srv, "EXPECTED_OIDC_AUDIENCE", "")

    with TestClient(srv.app) as client:
        resp = client.post("/reflect")
    assert resp.status_code == 503, resp.status_code
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert (
        "frame-ancestors 'none'"
        in resp.headers.get("Content-Security-Policy", "")
    )


# ---------------------------------------------------------------------------
# PDF-highlight provenance — plan §7 D15 (closes post-audit gaps #3 + #4)
# ---------------------------------------------------------------------------
# These tests pin the new contract: the SSE finding event must carry
# `page` + `pdf_bbox` joined from the Parser's clause record. They
# exercise the schema shape, the model_dump JSON projection, and the
# end-to-end `_stream_findings` flow with a mocked Runner.


def test_risk_finding_schema_accepts_page_and_pdf_bbox():
    """Both fields optional; defaults to None so existing producers
    that omit them keep validating (HTML exhibits, unit tests, mocks)."""
    finding = RiskFinding(
        clause_id="x",
        clause_text="...",
        tag="change_of_control",
        severity="block",
        judge_score=0.9,
        cited_spans=["x"],
        cited_spans_text="...",
        explanation="...",
    )
    assert finding.page is None
    assert finding.pdf_bbox is None
    # And accepts populated values.
    populated = RiskFinding(
        clause_id="x", clause_text="...", tag="change_of_control",
        severity="block", judge_score=0.9, cited_spans=["x"],
        cited_spans_text="...", explanation="...",
        page=17, pdf_bbox=(72.0, 144.0, 540.0, 180.0),
    )
    assert populated.page == 17
    assert populated.pdf_bbox == (72.0, 144.0, 540.0, 180.0)


def test_risk_finding_model_dump_serializes_pdf_bbox_as_list():
    """The frontend types `pdf_bbox` as `[number, number, number, number]`
    (a JS tuple is a JSON array). `model_dump(mode="json")` MUST emit
    the Python tuple as a JSON array so the SSE wire shape matches the
    TS type — a regression to a Python-tuple-repr string or a dict
    would silently break the frontend's highlight overlay."""
    finding = RiskFinding(
        clause_id="x", clause_text="...", tag="change_of_control",
        severity="block", judge_score=0.9, cited_spans=["x"],
        cited_spans_text="...", explanation="...",
        page=17, pdf_bbox=(72.0, 144.0, 540.0, 180.0),
    )
    dumped = finding.model_dump(mode="json")
    assert dumped["page"] == 17
    assert dumped["pdf_bbox"] == [72.0, 144.0, 540.0, 180.0]
    # Round-trip through json to confirm it's serializable as-is —
    # this is what `_sse` does in server.py.
    payload = json.dumps({"event": "finding", "finding": dumped})
    parsed = json.loads(payload)
    assert parsed["finding"]["pdf_bbox"] == [72.0, 144.0, 540.0, 180.0]


def test_risk_finding_schema_treats_llm_page_pdf_bbox_as_optional_inputs():
    """Schema accepts `page` + `pdf_bbox` even though the prompt now
    instructs the LLM not to emit them. The server's authoritative
    override (`model_copy(update=...)`) will replace whatever the LLM
    produced — but the validator must not REJECT an LLM that ignored
    the instruction, otherwise the existing fail-loud
    `validate_risk_judge_finding` SSE error would fire on every PDF
    review during the demo. Same defensive posture as `trace_id`."""
    raw = {
        "clause_id": "x", "clause_text": "...", "tag": "change_of_control",
        "severity": "block", "judge_score": 0.9, "cited_spans": ["x"],
        "cited_spans_text": "...", "explanation": "...",
        # LLM ignored the "do not emit" instruction:
        "page": 99, "pdf_bbox": [1.0, 2.0, 3.0, 4.0],
        "trace_id": "deadbeef" * 4,
    }
    finding = RiskFinding.model_validate(raw)
    # Validates; the server's model_copy below will then overwrite.
    assert finding.page == 99
    assert finding.pdf_bbox == (1.0, 2.0, 3.0, 4.0)


# --- end-to-end `_stream_findings` exercise with a mocked Runner ------------
#
# The pattern: stub `google.adk.runners.InMemoryRunner` so the agent
# graph doesn't run; instead, `run_async` yields a pre-canned list of
# Event objects (parser output, then risk_judge output). The SSE bytes
# emitted by `_stream_findings` carry the joined page/pdf_bbox.

def _ev(author: str, text: str):
    """Build a fake ADK Event with the minimal shape `_stream_findings`
    consumes: `.author` (str) and `.content.parts[i].text`."""
    return types.SimpleNamespace(
        author=author,
        content=types.SimpleNamespace(
            parts=[types.SimpleNamespace(text=text)]
        ),
        actions=None,
    )


def _make_fake_adk(events: list):
    """Install fake `google.adk.runners.InMemoryRunner` + `google.genai`
    so `_stream_findings` runs without the real ADK install. Returns
    the fake `Runner` class for assertions if needed."""
    # google.adk.runners.InMemoryRunner
    class _FakeSessionService:
        def create_session(self, **kw):
            return None

    class _InMemoryRunner:
        def __init__(self, *, agent, app_name):
            self.agent = agent
            self.app_name = app_name
            self.session_service = _FakeSessionService()

        async def run_async(self, *, user_id, session_id, new_message):
            for e in events:
                yield e

    runners_mod = types.ModuleType("google.adk.runners")
    runners_mod.InMemoryRunner = _InMemoryRunner

    adk_pkg = types.ModuleType("google.adk")
    adk_pkg.runners = runners_mod

    # google.genai.types.Content + Part
    class _Part:
        def __init__(self, **kw):
            self.__dict__.update(kw)

        @classmethod
        def from_bytes(cls, *, data, mime_type):
            return cls(kind="bytes", data=data, mime_type=mime_type)

        @classmethod
        def from_uri(cls, *, file_uri, mime_type):
            return cls(kind="uri", file_uri=file_uri, mime_type=mime_type)

    class _Content:
        def __init__(self, *, role, parts):
            self.role = role
            self.parts = parts

    gtypes_mod = types.ModuleType("google.genai.types")
    gtypes_mod.Part = _Part
    gtypes_mod.Content = _Content
    gtypes_mod.UploadFileConfig = lambda **kw: kw

    genai_pkg = types.ModuleType("google.genai")
    genai_pkg.types = gtypes_mod

    google_pkg = types.ModuleType("google")
    google_pkg.adk = adk_pkg
    google_pkg.genai = genai_pkg

    return google_pkg, adk_pkg, runners_mod, genai_pkg, gtypes_mod, _InMemoryRunner


def _install_fake_adk(monkeypatch, events: list):
    google_pkg, adk_pkg, runners_mod, genai_pkg, gtypes_mod, runner_cls = (
        _make_fake_adk(events)
    )
    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.adk", adk_pkg)
    monkeypatch.setitem(sys.modules, "google.adk.runners", runners_mod)
    monkeypatch.setitem(sys.modules, "google.genai", genai_pkg)
    monkeypatch.setitem(sys.modules, "google.genai.types", gtypes_mod)
    return runner_cls


def _stub_inline_judges_and_root_agent(monkeypatch):
    """Stub `_load_prompt`-dependent agent construction, the inline-
    judges call, and Thresholds loading so `_stream_findings` doesn't
    reach into Vertex / Phoenix / disk during the test."""
    from agent import server as srv
    from agent.router import Thresholds

    monkeypatch.setattr(
        "agent.agents.build_root_agent", lambda: types.SimpleNamespace(),
    )
    monkeypatch.setattr(
        "agent.evaluators.run_inline_judges",
        lambda **kw: (0.05, "hallucinated", 0.9, "faithful"),
    )
    # Avoid reading thresholds.json from disk in the test sandbox.
    monkeypatch.setattr(
        Thresholds, "from_json",
        classmethod(lambda cls, path: cls(tau_h=0.5, tau_f=0.5)),
    )
    # Router doesn't need stubbing — it's pure-Python over the finding
    # + scores and is exercised by tests/test_router.py.
    return srv


async def _collect_sse(stream):
    out = []
    async for chunk in stream:
        out.append(chunk)
    return out


def _parse_sse_events(chunks: list[bytes]) -> list[dict]:
    """Decode SSE `data: ...\\n\\n` frames into a list of JSON payloads."""
    events = []
    for c in chunks:
        text = c.decode()
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


_PARSER_CLAUSE_JSON = json.dumps([
    {
        "id": "sec_4.2_para_b",
        "section_path": ["Article IV", "Section 4.2", "(b)"],
        "text": "Upon a Change of Control...",
        "page": 17,
        "char_start": 100,
        "char_end": 250,
        "pdf_bbox": [72.0, 144.0, 540.0, 180.0],
    },
])

_RISK_JUDGE_FINDING_BASE = {
    "clause_id": "sec_4.2_para_b",
    "clause_text": "Upon a Change of Control...",
    "tag": "change_of_control",
    "severity": "block",
    "judge_score": 0.92,
    "cited_spans": ["sec_4.2_para_b"],
    "cited_spans_text": "Upon a Change of Control...",
    "explanation": "Consent requirement triggers on direct equity transfer.",
}


def test_stream_findings_emits_joined_page_and_pdf_bbox(monkeypatch):
    """End-to-end: Parser emits a clause with page=17 + pdf_bbox; Risk
    Judge emits a finding without those fields; the SSE finding event
    must carry page=17 + pdf_bbox=[72, 144, 540, 180] joined from the
    Parser. Closes post-audit gap #4 (SSE threading)."""
    events = [
        _ev("parser", _PARSER_CLAUSE_JSON),
        _ev("risk_judge", json.dumps([_RISK_JUDGE_FINDING_BASE])),
    ]
    _install_fake_adk(monkeypatch, events)
    srv = _stub_inline_judges_and_root_agent(monkeypatch)

    chunks = asyncio.run(_collect_sse(
        srv._stream_findings(b"%PDF-fake", mime_type="application/pdf")
    ))
    parsed = _parse_sse_events(chunks)
    findings = [e for e in parsed if e.get("event") == "finding"]
    assert len(findings) == 1, parsed
    f = findings[0]["finding"]
    assert f["page"] == 17, f
    assert f["pdf_bbox"] == [72.0, 144.0, 540.0, 180.0], f


def test_stream_findings_overrides_llm_emitted_page_and_pdf_bbox(monkeypatch):
    """If the LLM ignored the 'do not emit' instruction and produced
    bogus page/pdf_bbox values, the server-side join MUST overwrite
    them with the Parser's truth. Same discipline as trace_id —
    one source of truth per field, and it is NOT the model."""
    events = [
        _ev("parser", _PARSER_CLAUSE_JSON),
        _ev("risk_judge", json.dumps([{
            **_RISK_JUDGE_FINDING_BASE,
            "page": 9999,
            "pdf_bbox": [9.0, 9.0, 9.0, 9.0],
        }])),
    ]
    _install_fake_adk(monkeypatch, events)
    srv = _stub_inline_judges_and_root_agent(monkeypatch)

    chunks = asyncio.run(_collect_sse(
        srv._stream_findings(b"%PDF-fake", mime_type="application/pdf")
    ))
    parsed = _parse_sse_events(chunks)
    findings = [e for e in parsed if e.get("event") == "finding"]
    assert len(findings) == 1
    f = findings[0]["finding"]
    assert f["page"] == 17, "Parser page must override LLM-emitted page"
    assert f["pdf_bbox"] == [72.0, 144.0, 540.0, 180.0], (
        "Parser pdf_bbox must override LLM-emitted pdf_bbox"
    )


def test_stream_findings_invokes_pdfplumber_fallback_when_bbox_null_on_pdf(monkeypatch):
    """Parser emitted a clause with `pdf_bbox: null` (Gemini's bbox
    omission gap #3); source is PDF; the server MUST consult the
    pdfplumber fallback via `extract_bbox_from_pdf` and propagate
    its result onto the SSE finding event."""
    parser_clause_no_bbox = json.dumps([{
        "id": "sec_4.2_para_b",
        "section_path": ["Article IV", "Section 4.2", "(b)"],
        "text": "Upon a Change of Control...",
        "page": 17,
        "char_start": 100,
        "char_end": 250,
        "pdf_bbox": None,
    }])
    events = [
        _ev("parser", parser_clause_no_bbox),
        _ev("risk_judge", json.dumps([_RISK_JUDGE_FINDING_BASE])),
    ]
    _install_fake_adk(monkeypatch, events)
    srv = _stub_inline_judges_and_root_agent(monkeypatch)

    # Stub the pdfplumber fallback to return a known bbox without
    # spinning up real pdfplumber. The fallback's own contract is
    # tested in tests/test_pdf_bbox.py.
    fallback_calls = []

    def _fake_extract(pdf_bytes, page, cs, ce):
        fallback_calls.append((len(pdf_bytes), page, cs, ce))
        return (100.0, 200.0, 300.0, 220.0)

    monkeypatch.setattr("agent.pdf_bbox.extract_bbox_from_pdf", _fake_extract)

    chunks = asyncio.run(_collect_sse(
        srv._stream_findings(b"%PDF-fake-bytes-here", mime_type="application/pdf")
    ))
    parsed = _parse_sse_events(chunks)
    findings = [e for e in parsed if e.get("event") == "finding"]
    assert len(findings) == 1
    f = findings[0]["finding"]
    # Page comes from the Parser (still 17), bbox from the fallback.
    assert f["page"] == 17
    assert f["pdf_bbox"] == [100.0, 200.0, 300.0, 220.0]
    assert fallback_calls == [(20, 17, 100, 250)], (
        f"expected exactly one fallback call with (page, char_start, "
        f"char_end) from the Parser; got {fallback_calls}"
    )


def test_stream_findings_skips_pdfplumber_fallback_for_html_exhibits(monkeypatch):
    """HTML exhibits never have pdf_bbox; the server must NOT invoke
    the pdfplumber fallback (it would just return None on text/html
    bytes, but the cost is wasted thread spawning + a misleading log
    line). Symmetric with the schema docstring's degradation note."""
    parser_clause_no_bbox = json.dumps([{
        "id": "sec_4.2_para_b",
        "section_path": ["Article IV", "Section 4.2", "(b)"],
        "text": "Upon a Change of Control...",
        "page": 17,
        "char_start": 100,
        "char_end": 250,
        "pdf_bbox": None,
    }])
    events = [
        _ev("parser", parser_clause_no_bbox),
        _ev("risk_judge", json.dumps([_RISK_JUDGE_FINDING_BASE])),
    ]
    _install_fake_adk(monkeypatch, events)
    srv = _stub_inline_judges_and_root_agent(monkeypatch)

    calls = []

    def _fake_extract(*a, **kw):
        calls.append((a, kw))
        return (1.0, 2.0, 3.0, 4.0)

    monkeypatch.setattr("agent.pdf_bbox.extract_bbox_from_pdf", _fake_extract)

    chunks = asyncio.run(_collect_sse(
        srv._stream_findings(b"<html>...</html>", mime_type="text/html")
    ))
    assert calls == [], (
        f"pdfplumber fallback fired on text/html exhibit: {calls}"
    )
    parsed = _parse_sse_events(chunks)
    findings = [e for e in parsed if e.get("event") == "finding"]
    assert len(findings) == 1
    f = findings[0]["finding"]
    # No bbox for HTML — frontend already handles this (renders iframe,
    # not PDF viewer overlay).
    assert f["page"] == 17
    assert f["pdf_bbox"] is None


def test_stream_findings_yields_join_error_when_clause_id_missing(monkeypatch):
    """Risk Judge cites `sec_99` but Parser only emitted `sec_4.2_para_b`.
    The server must yield a `join_clause_to_finding` error SSE alongside
    the finding (fail loud), AND emit the finding with page=null +
    pdf_bbox=null so the frontend can still render the row without a
    pin. Matches the legal-reviewer 'demo doesn't look clean when it's
    broken' mandate."""
    events = [
        _ev("parser", _PARSER_CLAUSE_JSON),
        _ev("risk_judge", json.dumps([{
            **_RISK_JUDGE_FINDING_BASE,
            "clause_id": "sec_99_para_z",
            # LLM tried to invent coordinates — wipe them in the override.
            "page": 42,
            "pdf_bbox": [1.0, 1.0, 1.0, 1.0],
        }])),
    ]
    _install_fake_adk(monkeypatch, events)
    srv = _stub_inline_judges_and_root_agent(monkeypatch)

    chunks = asyncio.run(_collect_sse(
        srv._stream_findings(b"%PDF-fake", mime_type="application/pdf")
    ))
    parsed = _parse_sse_events(chunks)
    errors = [
        e for e in parsed
        if e.get("event") == "error"
        and e.get("stage") == "join_clause_to_finding"
    ]
    assert len(errors) == 1, parsed
    assert errors[0].get("clause_id") == "sec_99_para_z"
    findings = [e for e in parsed if e.get("event") == "finding"]
    assert len(findings) == 1, "finding must still be emitted (no silent drop)"
    f = findings[0]["finding"]
    assert f["page"] is None, "LLM-hallucinated page must be wiped"
    assert f["pdf_bbox"] is None, "LLM-hallucinated bbox must be wiped"
