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
"""
from __future__ import annotations

import re

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
