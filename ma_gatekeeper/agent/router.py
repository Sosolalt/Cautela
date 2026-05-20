"""Deterministic Python router + Phoenix span annotation writer.

Implements §6.2 of plan.md (independent-gating per evaluator) with the
TWO-annotation pattern recommended by the Arize-track reviewer:
  - one annotation per evaluator (`hallucination`, `clause_faithfulness`)
  - plus a third aggregate `risk_judge_gate` annotation carrying the lane

API verified against arize-phoenix-client docs:
  - canonical resource is `client.spans.add_span_annotation(...)`
    (NOT `client.annotations.*`, which is deprecated as of 1.17).
  - Kwargs: span_id, annotation_name, annotator_kind, label, score,
    explanation, metadata, identifier, sync.
  Reference: https://arize-phoenix.readthedocs.io/projects/client/en/latest/api/spans.html

`judge_and_route` MUST be called inside an active ADK span context, or
get_current_span() returns a NoOp span and the annotation lands on
0000... — the writer logs a warning in that case.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .schemas import GatekeeperDecision, RiskFinding

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Thresholds:
    tau_h: float
    tau_f: float

    @classmethod
    def from_json(cls, path: str) -> "Thresholds":
        import json
        with open(path) as f:
            d = json.load(f)
        return cls(tau_h=float(d["tau_h"]), tau_f=float(d["tau_f"]))


def _format_span_id() -> str:
    try:
        from opentelemetry.trace import format_span_id, get_current_span
        span = get_current_span()
        ctx = span.get_span_context()
        sid = format_span_id(ctx.span_id)
        if sid == "0" * 16:
            _LOG.warning("judge_and_route called outside active span context; "
                         "annotation will not link to a trace.")
        return sid
    except Exception:
        return "0" * 16


def _annotate(span_id: str, *, name: str, label: str,
              score: float, explanation: str) -> None:
    """Write one LLM-kind span annotation via arize-phoenix-client.

    Best-effort; failures are logged but do not break routing.
    """
    try:
        from phoenix.client import Client
        Client().spans.add_span_annotation(
            span_id=span_id,
            annotation_name=name,
            annotator_kind="LLM",
            label=label,
            score=score,
            explanation=explanation,
        )
    except Exception as exc:  # pragma: no cover - best effort
        _LOG.warning("Phoenix annotation %s failed (span=%s): %s",
                     name, span_id, exc)


def judge_and_route(
    finding: RiskFinding,
    *,
    h_score: float,
    h_label: str,
    f_score: float,
    f_label: str,
    thresholds: Thresholds,
) -> GatekeeperDecision:
    """Independent-gating router (plan §6.2).

    Both evaluators must pass their own threshold for the finding to
    auto-clear or hard-block. Otherwise the finding escalates. Averaging
    across the two evaluators is intentionally avoided — they measure
    different failure modes (factuality vs classification fidelity);
    averaging would hide one signal behind the other and could let a
    hallucinated explanation auto-clear via a high faithfulness score.

    Writes THREE Phoenix annotations:
      - annotation_name="hallucination"        score=h_score
      - annotation_name="clause_faithfulness"  score=f_score
      - annotation_name="risk_judge_gate"      label=lane

    This is the canonical Arize pattern — one annotation per evaluator
    so the Phoenix UI's annotation analytics surface groups properly.
    """
    passes_h = h_score >= thresholds.tau_h
    passes_f = f_score >= thresholds.tau_f
    both_pass = passes_h and passes_f

    span_id = _format_span_id()
    _annotate(span_id, name="hallucination", label=h_label,
              score=h_score,
              explanation=f"threshold tau_h={thresholds.tau_h}")
    _annotate(span_id, name="clause_faithfulness", label=f_label,
              score=f_score,
              explanation=f"threshold tau_f={thresholds.tau_f}")

    if both_pass and finding.severity == "info":
        lane = "auto_clear"
    elif both_pass and finding.severity == "block":
        lane = "block"
    else:
        lane = "escalate"

    _annotate(
        span_id, name="risk_judge_gate", label=lane,
        score=(1.0 if lane != "escalate" else 0.0),
        explanation=(
            f"finding={finding.clause_id} tag={finding.tag} "
            f"severity={finding.severity} "
            f"h={h_score:.3f}({h_label}) f={f_score:.3f}({f_label}) "
            f"tau_h={thresholds.tau_h} tau_f={thresholds.tau_f}"
        ),
    )

    return GatekeeperDecision(
        finding_id=finding.clause_id,
        lane=lane,
        threshold_applied=min(thresholds.tau_h, thresholds.tau_f),
    )
