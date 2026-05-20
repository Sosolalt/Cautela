"""Pydantic schemas for the M&A Due Diligence Gatekeeper.

Mirrors §4.3 of plan.md. Every sub-agent reads/writes one of these models so
the pipeline is JSON-schema-validated end to end.
"""
from __future__ import annotations

from typing import Literal

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
    arize_trace_id: str


class GatekeeperDecision(BaseModel):
    finding_id: str
    lane: Lane
    threshold_applied: float
