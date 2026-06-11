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


@pytest.mark.parametrize("body", [
    '[{"clause_id": "x"}]',                       # bare JSON, no fence
    '```json\n[{"clause_id": "x"}]\n```',         # ```json fenced
    '```\n[{"clause_id": "x"}]\n```',             # bare ``` fenced
    '  ```json\n[{"clause_id": "x"}]\n```  ',     # fenced + surrounding ws
])
def test_strip_code_fences_unwraps_risk_judge_body(body):
    """Regression for PROJECT_LOG Phase 14: Gemini wraps the risk_judge
    findings array in a ```json fence, so a bare json.loads raised and the
    stream emitted n_findings=0 even when real findings existed. The server
    must tolerate fenced and unfenced bodies identically."""
    from agent.server import _strip_code_fences

    parsed = json.loads(_strip_code_fences(body))
    assert parsed == [{"clause_id": "x"}]


def _base_raw_finding(**overrides):
    raw = {
        "clause_id": "sec_9.3",
        "clause_text": "9.3 Assignment. No Party may assign ...",
        "tag": "anti_assignment",
        "severity": "block",
        "judge_score": 0.9,
        "cited_spans": ["sec_9.3"],
        "cited_spans_text": "9.3 Assignment ...",
        "explanation": "Anti-assignment triggers consent on change of control.",
    }
    raw.update(overrides)
    return raw


@pytest.mark.parametrize("score_in,score_out", [
    (8, 0.8),        # 1-10 integer scale
    (9, 0.9),
    (2, 0.2),
    (85, 0.85),      # 0-100 scale
    (0.7, 0.7),      # already 0-1 — untouched
    (12, 0.12),      # >10 -> /100
])
def test_coerce_risk_finding_rescales_judge_score(score_in, score_out):
    """Regression (Phase 15 live run on microsoft_activision): the Risk Judge
    emits judge_score on a 1-10 (sometimes 0-100) scale, which violates the
    RiskFinding `ge=0, le=1` bound and dropped EVERY finding to a validation
    error (n_findings=0 on a run that produced real findings). The server
    rescales+clamps so the finding validates."""
    from agent.server import _coerce_risk_finding_raw

    coerced = _coerce_risk_finding_raw(_base_raw_finding(judge_score=score_in))
    assert coerced["judge_score"] == pytest.approx(score_out)
    RiskFinding.model_validate(coerced)  # must not raise


def test_coerce_risk_finding_joins_cited_spans_text_list():
    """The Risk Judge sometimes emits cited_spans_text as a LIST of span
    strings; the schema wants a single string. Coercion joins them so the
    inline judges still see the full verbatim context."""
    from agent.server import _coerce_risk_finding_raw

    raw = _base_raw_finding(cited_spans_text=["span one.", "span two."])
    coerced = _coerce_risk_finding_raw(raw)
    assert coerced["cited_spans_text"] == "span one.\n\nspan two."
    RiskFinding.model_validate(coerced)


def test_coerce_risk_finding_fills_null_clause_id_from_cited_spans():
    """A null clause_id (Judge couldn't attribute to a single clause) falls
    back to the first cited_spans entry so the clause_id->page join has a key."""
    from agent.server import _coerce_risk_finding_raw

    raw = _base_raw_finding(clause_id=None, cited_spans=["sec_2.1", "sec_2.2"])
    coerced = _coerce_risk_finding_raw(raw)
    assert coerced["clause_id"] == "sec_2.1"
    RiskFinding.model_validate(coerced)


@pytest.mark.parametrize("label,canon", [
    ("MAC Carve-Out", "mac"),
    ("Change of Control", "change_of_control"),
    ("Assignment", "anti_assignment"),
    ("Vesting Acceleration", "accelerated_vesting"),
    ("IP Assignment", "ip_assignment"),
    ("Exclusivity / No-Shop", "exclusivity"),
    ("Non-Compete", "non_compete"),
    ("change_of_control", "change_of_control"),  # already canonical
])
def test_coerce_risk_finding_canonicalizes_tag_label(label, canon):
    """Regression (Phase 15 live run): the Risk Judge emits human-readable tag
    labels ("MAC Carve-Out", "Change of Control") instead of the canonical
    snake_case Tag enum, failing the literal validator and dropping the finding.
    Coercion maps them back to the enum."""
    from agent.server import _coerce_risk_finding_raw

    coerced = _coerce_risk_finding_raw(_base_raw_finding(tag=label))
    assert coerced["tag"] == canon
    RiskFinding.model_validate(coerced)


@pytest.mark.parametrize("label,canon", [
    ("Block", "block"), ("High", "block"), ("medium", "watch"), ("Low", "info"),
])
def test_coerce_risk_finding_canonicalizes_severity(label, canon):
    """The Risk Judge sometimes capitalizes severity or uses a high/medium/low
    scale; coercion maps to the info/watch/block enum."""
    from agent.server import _coerce_risk_finding_raw

    coerced = _coerce_risk_finding_raw(_base_raw_finding(severity=label))
    assert coerced["severity"] == canon
    RiskFinding.model_validate(coerced)


def test_coerce_risk_finding_handles_all_drift_modes_at_once():
    """The live failure: a single finding drifting on tag + severity +
    judge_score + cited_spans_text simultaneously must still validate."""
    from agent.server import _coerce_risk_finding_raw

    raw = _base_raw_finding(
        tag="MAC Carve-Out", severity="Block", judge_score=8,
        cited_spans_text=['"Company Material Adverse Effect" means ...'],
    )
    f = RiskFinding.model_validate(_coerce_risk_finding_raw(raw))
    assert f.tag == "mac" and f.severity == "block" and f.judge_score == pytest.approx(0.8)
    assert isinstance(f.cited_spans_text, str)


def test_coerce_risk_finding_fills_missing_clause_text_from_cited_spans_text():
    """Regression (Phase 15 live run #4): the Risk Judge omits the required
    `clause_text` field entirely, putting the clause prose only in
    `cited_spans_text`. Coercion backfills clause_text from it so the finding
    validates."""
    from agent.server import _coerce_risk_finding_raw

    raw = _base_raw_finding(cited_spans_text="9.3 Assignment. No Party may assign ...")
    del raw["clause_text"]
    coerced = _coerce_risk_finding_raw(raw)
    assert coerced["clause_text"] == "9.3 Assignment. No Party may assign ..."
    RiskFinding.model_validate(coerced)


def test_coerce_risk_finding_missing_clause_text_and_no_source_fails_loud():
    """If clause_text is missing AND there is no cited_spans_text to backfill
    from, the finding still fails loud (no fabrication)."""
    from agent.server import _coerce_risk_finding_raw

    raw = _base_raw_finding()
    del raw["clause_text"]
    del raw["cited_spans_text"]
    coerced = _coerce_risk_finding_raw(raw)
    with pytest.raises(Exception):
        RiskFinding.model_validate(coerced)


def test_coerce_risk_finding_leaves_unknown_tag_to_fail_loud():
    """A tag that maps to nothing confidently is left raw so validation fails
    loud (coercion is normalization, not a catch-all guess)."""
    from agent.server import _coerce_risk_finding_raw

    coerced = _coerce_risk_finding_raw(_base_raw_finding(tag="Frobnicator Clause"))
    assert coerced["tag"] == "Frobnicator Clause"
    with pytest.raises(Exception):
        RiskFinding.model_validate(coerced)


def test_coerce_risk_finding_leaves_uncoercible_to_fail_loud():
    """Coercion is normalization, not error-hiding: a genuinely bad field it
    can't confidently fix (here, a non-numeric judge_score) is left untouched
    so model_validate still fails loud."""
    from agent.server import _coerce_risk_finding_raw

    raw = _base_raw_finding(judge_score="very high")
    coerced = _coerce_risk_finding_raw(raw)
    assert coerced["judge_score"] == "very high"
    with pytest.raises(Exception):
        RiskFinding.model_validate(coerced)


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


# ---------------------------------------------------------------------------
# GROUNDTRUTH_PLAN T1.2 — governing-law capture helper (pure, no live pipeline)
# ---------------------------------------------------------------------------


def test_governing_law_hint_from_bare_findings_list_is_none():
    """Current cross_reference output (a bare findings list) yields no hint —
    the wiring is non-breaking: lookup then renders the canonical default."""
    from agent.server import _governing_law_hint_from_event
    text = json.dumps([{"clause_id": "c1", "tag": "mac"}])
    assert _governing_law_hint_from_event(text) is None


def test_governing_law_hint_from_envelope_new_york():
    from agent.server import _governing_law_hint_from_event
    text = json.dumps({
        "governing_law": {
            "verbatim_clause": "This Agreement shall be governed by the laws of the State of New York.",
            "jurisdiction": "State of New York",
        },
        "findings": [],
    })
    assert _governing_law_hint_from_event(text) == "New York"


def test_governing_law_hint_falls_back_to_verbatim_clause():
    from agent.server import _governing_law_hint_from_event
    text = json.dumps({
        "governing_law": {
            "verbatim_clause": "Governed by the laws of the State of Delaware.",
            "jurisdiction": None,
        },
        "findings": [],
    })
    assert _governing_law_hint_from_event(text) == "Delaware"


def test_governing_law_hint_unknown_jurisdiction_is_none():
    from agent.server import _governing_law_hint_from_event
    text = json.dumps({
        "governing_law": {"verbatim_clause": "laws of England and Wales", "jurisdiction": "England"},
        "findings": [],
    })
    assert _governing_law_hint_from_event(text) is None


def test_governing_law_hint_handles_garbage():
    from agent.server import _governing_law_hint_from_event
    assert _governing_law_hint_from_event("not json {{{") is None
    assert _governing_law_hint_from_event(json.dumps({"findings": []})) is None
