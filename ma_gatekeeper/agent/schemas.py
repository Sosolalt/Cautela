"""Pydantic schemas for the M&A Due Diligence Gatekeeper.

Mirrors §4.3 of plan.md. Every sub-agent reads/writes one of these models so
the pipeline is JSON-schema-validated end to end.
"""
from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field

Tag = Literal[
    "change_of_control",
    "anti_assignment",
    "mac",
    "accelerated_vesting",
    "exclusivity",
    "ip_assignment",
    "non_compete",
    "none",
]

# Derived tag tuples — DO NOT hand-replicate these elsewhere. Adding a
# new tag means adding it to the `Tag` Literal above and to the
# `frontend/lib/types.ts:Tag` union (sync-guarded by
# `tests/test_tag_sync.py`); both Python tuples below derive
# automatically. See the "Tag sync points" section in README.md.
ALL_TAGS: tuple[Tag, ...] = get_args(Tag)
# CLASSIFIER_TAGS excludes "none" because the parallel ParallelAgent
# fan-out in agents.py spawns one LlmAgent per real clause family;
# "none" is the absence label, not a classifier target.
CLASSIFIER_TAGS: tuple[Tag, ...] = tuple(t for t in ALL_TAGS if t != "none")

Severity = Literal["info", "watch", "block"]
Lane = Literal["auto_clear", "escalate", "block"]


class Clause(BaseModel):
    id: str = Field(..., description='e.g. "sec_4.2_para_b"')
    section_path: list[str] = Field(
        ..., description='["Article IV", "Section 4.2", "(b)"]'
    )
    text: str
    page: int
    char_start: int
    char_end: int
    # Populated by Parser on D4 to enable D15 PDF<->trace sync (plan §7 D4).
    # If None, the frontend degrades to forward-only sync (PDF -> trace).
    pdf_bbox: tuple[float, float, float, float] | None = None


class ClauseTag(BaseModel):
    clause_id: str
    tag: Tag
    confidence: float = Field(..., ge=0.0, le=1.0)


class RiskFinding(BaseModel):
    clause_id: str
    clause_text: str
    tag: Tag
    severity: Severity
    judge_score: float = Field(..., ge=0.0, le=1.0)
    cited_spans: list[str]
    cited_spans_text: str
    explanation: str
    # OTel trace ID (32-char lowercase hex), populated by the server from
    # the active span context — NEVER by the LLM. None when emitted
    # outside an active OTel context (e.g. unit tests, NoOp tracer). The
    # frontend uses this to deep-link into the Phoenix trace view; the
    # name is `trace_id` (not `arize_trace_id`) because it's a W3C OTel
    # concept and Phoenix is just the viewer.
    trace_id: str | None = Field(default=None)
    # ------------------------------------------------------------------
    # PDF-highlight provenance (plan §7 D15 — frontend bbox sync).
    # ------------------------------------------------------------------
    # Populated server-side from the Parser's clause output via
    # clause_id lookup (see `agent/server.py:_stream_findings`). The
    # LLM (Risk Judge) does NOT emit these — any value it hallucinates
    # is discarded and replaced. Mirrors the `trace_id` server-override
    # pattern at `agent/server.py:_stream_findings` (the active-OTel-span
    # override): there is exactly one authoritative source per field, and
    # it is the server, not the model.
    #
    # The server populates `page` and `pdf_bbox` by:
    #   1. Capturing the Parser's `output_key="clauses"` from ADK
    #      session state after the agent run (or via event-stream
    #      interception of `event.author == "parser"`).
    #   2. Building a `dict[clause_id, Clause]` lookup.
    #   3. For each RiskFinding emitted by the Risk Judge, copying
    #      `clause.page` and `clause.pdf_bbox` onto the finding via
    #      `finding.model_copy(update={...})`.
    #   4. When `pdf_bbox is None` AND `mime_type == "application/pdf"`,
    #      falling back to `agent.pdf_bbox.extract_bbox_from_pdf(
    #      pdf_bytes, page, clause.char_start, clause.char_end)`.
    #   5. Failing LOUD via an error SSE if `finding.clause_id` is not
    #      in the Parser's clause output — silent fallthrough would
    #      mask a real linkage bug and the frontend would silently
    #      drop the highlight.
    #
    # Both fields are nullable because:
    #   - HTML exhibits never have pdf_bbox (Parser sets it null;
    #     server-side join keeps it null; pdfplumber fallback skipped).
    #   - Mock / unit-test findings omit them entirely.
    #   - pdfplumber fallback can legitimately return None (char-offset
    #     drift between Gemini and pdfplumber, page out of range, etc.).
    page: int | None = Field(default=None)
    pdf_bbox: tuple[float, float, float, float] | None = Field(default=None)


class GatekeeperDecision(BaseModel):
    finding_id: str
    lane: Lane
    threshold_applied: float
