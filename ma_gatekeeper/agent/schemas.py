"""Pydantic schemas for the M&A Due Diligence Gatekeeper.

Mirrors §4.3 of plan.md. Every sub-agent reads/writes one of these models so
the pipeline is JSON-schema-validated end to end.
"""
from __future__ import annotations

from datetime import date
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


# ---------------------------------------------------------------------------
# Citation-linkage layer (design/STATUTE_LAYER.md).
# ---------------------------------------------------------------------------
# Two-surface split, structurally enforced:
#   - CitationRef         -> the ONLY citation rendered to users. Produced by
#                            the deterministic map lookup in citation_linker.py.
#   - LinkerProposal      -> INTERNAL eval data from the background LLM
#                            proposer. NEVER serialized to the user-facing wire.
# The separation is defended by three guards (see RiskFinding below + the SSE
# wire-output regression test). Citations are pinned to primary sources, not
# generated.


class CitationRef(BaseModel):
    """User-facing citation. Statute OR case-law.

    Only ever emitted by the deterministic lookup (citation_linker.lookup_citation);
    the LLM proposer emits a LinkerProposal instead. Production map content lives in
    data/citation_map.json with each citation primary-source-verified per entry (audit
    trail in data/CITATION_MAP_SIGNOFF.md).
    """

    citation: str = Field(
        ...,
        description='e.g. "8 Del. C. § 251" — case-law cites verified against primary source before commit',
    )
    citation_kind: Literal["statute", "case_law", "regulation"] = "statute"
    jurisdiction: str = Field(..., description='e.g. "Delaware"')
    uri: str | None = Field(default=None)
    rationale: str = Field(..., description="Why this clause maps here (<= 240 chars)")
    verified_date: date = Field(
        ..., description="Map-commit date; CI fails if older than 180 days"
    )
    primary_source: str = Field(
        ...,
        description='e.g. "Cornell LII", "delcode.delaware.gov", "courts.delaware.gov"',
    )


class LinkerProposal(BaseModel):
    """INTERNAL EVAL DATA. NEVER rendered to users.

    Defended by THREE structural guards: a distinct Pydantic class that type
    filters won't accidentally match; the RiskFinding.model_dump override below
    that default-excludes eval-only fields from every public serialization; and
    the SSE wire-output regression test (tests/test_no_eval_leak.py) that asserts
    these field names appear nowhere in bytes leaving the server.
    """

    citation: str
    citation_kind: Literal["statute", "case_law", "regulation"]
    jurisdiction: str
    rationale: str
    model_confidence: float = Field(..., ge=0.0, le=1.0)


class GoverningLaw(BaseModel):
    """Per-CONTRACT governing-law capture (GROUNDTRUTH_PLAN T1.2).

    One per contract, NOT per finding (RiskFinding has no jurisdiction field).
    The cross_reference agent may surface the verbatim governing-law clause; the
    server normalises `verbatim_clause`/`jurisdiction` via
    `citation_linker.normalize_jurisdiction` into the map's five canonical
    jurisdiction values to hint `lookup_citation`. Unknown/ambiguous text leaves
    `jurisdiction` None and the server renders a visible canonical-default label
    rather than silently serving Delaware.
    """

    verbatim_clause: str | None = Field(
        default=None, description="Transcribed governing-law sentence, if found"
    )
    jurisdiction: str | None = Field(
        default=None,
        description="Free text (e.g. 'State of New York'); normalised server-side",
    )


# Module-level constant — referenced by the RiskFinding.model_dump override
# below AND by the SSE wire test for symbol parity.
_EVAL_ONLY_FIELDS: frozenset[str] = frozenset(
    {
        "linker_proposal",
        "linker_agreement",
        "linker_confidence",
    }
)


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
    # ------------------------------------------------------------------
    # Citation-linkage layer (design/STATUTE_LAYER.md §2.2).
    # ------------------------------------------------------------------
    # citation_ref is the ONLY one of these four ever serialized to the
    # user-facing wire — it is server-authoritative (set from the
    # deterministic map in server.py:_stream_findings, never by the LLM).
    # The other three carry INTERNAL eval data and are default-excluded
    # from every public serialization by the model_dump* overrides below
    # (Guard #2). They normally stay None in production (the background
    # proposer writes a Phoenix annotation, not these fields); they exist
    # so the structural guard has something to exclude and so eval/test
    # paths can populate them explicitly.
    citation_ref: CitationRef | None = Field(default=None)
    linker_proposal: LinkerProposal | None = Field(default=None)
    linker_agreement: bool | None = Field(default=None)
    linker_confidence: float | None = Field(default=None)

    def model_dump(self, *, exclude=None, **kwargs):
        """Default-exclude eval-only fields from EVERY public serialization.

        Guard #2: rather than relying on each call site to remember
        exclude=_EVAL_ONLY_FIELDS, the model enforces it. Any future public
        surface (REST, logging, metrics, batch export) is structurally
        defended. Eval-only call sites use model_dump_internal() explicitly.
        """
        exclude_set = set(exclude or ())
        exclude_set |= _EVAL_ONLY_FIELDS
        return super().model_dump(exclude=exclude_set, **kwargs)

    def model_dump_json(self, *, exclude=None, **kwargs):
        """Override the JSON path too — Pydantic v2's model_dump_json does NOT
        call model_dump internally (it goes through the core schema directly),
        so overriding model_dump alone would leave a latent leak for any future
        caller that reaches for the JSON path. Belt-and-suspenders.
        """
        exclude_set = set(exclude or ())
        exclude_set |= _EVAL_ONLY_FIELDS
        return super().model_dump_json(exclude=exclude_set, **kwargs)

    def model_dump_internal(self, **kwargs):
        """Eval-only serialization — bypasses the default exclusion. Used ONLY
        by tests + the background-task annotation diagnostic logger. Audited as
        a single grep target: `model_dump_internal`.
        """
        return super().model_dump(**kwargs)


class GatekeeperDecision(BaseModel):
    finding_id: str
    lane: Lane
    threshold_applied: float


# ---------------------------------------------------------------------------
# Portfolio Analyst (Fix 7) — 1M-context cross-deal cluster output.
# ---------------------------------------------------------------------------
# Mirrors the RiskFinding style: explicit field types + docstring on every
# server-overridden field. The Portfolio Analyst is a SEPARATE endpoint
# (`/portfolio`) from the per-contract `/review` pipeline; one Gemini 3 Pro
# call ingests the EX-2.1 of all 30 Internal-30 contracts concatenated via
# Files API and emits a single `PortfolioReport`. NEVER folded into the
# SequentialAgent at agents.py:114-117 — that would burn a 1M-context call
# on every per-contract review.


class PortfolioCluster(BaseModel):
    """One cluster of MAE/MAC carve-out structural language across deals.

    `member_deal_ids` are the deal_id slugs from
    `docs/internal30_deal_bank.md`. `representative_clause_excerpt` is a
    short (<= 400 char) verbatim excerpt the Analyst lifts from one of
    the cluster members; `why_distinct` is a 1-2 sentence explanation of
    what makes this cluster structurally different from the others.
    """

    cluster_id: str = Field(..., description='e.g. "cluster_1_full_carveouts"')
    name: str = Field(..., description="Short human label for the cluster")
    theme: str = Field(
        ..., description="What the carve-out structure is (one sentence)"
    )
    member_deal_ids: list[str] = Field(
        ..., description="deal_id slugs from internal30_deal_bank.md"
    )
    representative_clause_excerpt: str = Field(
        ..., description="Verbatim excerpt from one member (<= 400 chars)"
    )
    why_distinct: str = Field(
        ..., description="1-2 sentence rationale vs other clusters"
    )


class PortfolioOutlier(BaseModel):
    """One deal whose MAE/MAC structure does not fit any cluster."""

    deal_id: str
    why: str = Field(
        ..., description="1-2 sentence rationale for non-membership"
    )


class PortfolioReport(BaseModel):
    """Output of the Portfolio Analyst agent — one Gemini 3 Pro call.

    Mutually-exclusive invariant (enforced in `tests/
    test_portfolio_analyst.py`): no deal_id appears in both
    `clusters[*].member_deal_ids` and `outliers[*].deal_id`. The mock
    fixture is the canonical example; the live agent prompt enforces the
    same in plain-English instruction.
    """

    clusters: list[PortfolioCluster]
    outliers: list[PortfolioOutlier]
    # OTel trace ID — populated server-side from the active span context
    # in `server.py:/portfolio`. Mirrors `RiskFinding.trace_id`.
    trace_id: str | None = Field(default=None)


# ---------------------------------------------------------------------------
# §11 Build #3 / §12 — Reflector-as-ADK-LoopAgent (`/reflect/loop`).
# ---------------------------------------------------------------------------
# These schemas mirror the per-event SSE wire and the terminal summary
# emitted by `agent/reflector_loop.py:run_reflector_loop`. The loop body
# runs N iterations, each emitting a sequence of events that the frontend
# streams into a step-by-step status panel:
#
#   loop_started → iteration_started → mcp_traces_listed →
#   candidate_generated → experiment_complete → frozen_fold_check →
#   iteration_complete → (auto_promoted | no_promotion)
#
# `kind` is the event family; `payload` carries event-specific data. We
# deliberately keep `payload` a free-form dict (not a discriminated union)
# because the hackathon timeline doesn't justify 8 sibling Pydantic
# classes — the TS mirror in `frontend/lib/types.ts` documents the per-
# kind payload shape and the frontend component does the dispatch. If a
# field is load-bearing across the cohort (e.g. trace_id, iteration)
# it is promoted to a top-level field on `ReflectorLoopEvent`.


ReflectorLoopEventKind = Literal[
    "loop_started",
    "iteration_started",
    "mcp_traces_listed",
    "candidate_generated",
    "experiment_complete",
    "frozen_fold_check",
    "iteration_complete",
    "auto_promoted",
    "no_promotion",
    "error",
]


class ReflectorLoopEvent(BaseModel):
    """One event in the `/reflect/loop` SSE stream.

    `kind` — see `ReflectorLoopEventKind` for the closed set.
    `iteration` — 1-indexed LoopAgent iteration; None for terminal events.
    `trace_id` — OTel trace id of the parent loop span; server-populated.
    `payload` — kind-specific data (e.g. {"ci_lower_bound": 0.042}).
    """

    kind: ReflectorLoopEventKind
    iteration: int | None = Field(default=None, ge=0)
    trace_id: str | None = Field(default=None)
    payload: dict = Field(default_factory=dict)


class ReflectorLoopReport(BaseModel):
    """Terminal summary of one `run_reflector_loop` invocation.

    `promoted` is True iff at least one iteration's candidate passed the
    `should_promote` gate (paired-bootstrap CI lower bound > 0 AND
    frozen-fold non-regression within ε). `auto_pr_url` is populated only
    when `REFLECTOR_LOOP_AUTO_PR=1` and a real `gh pr create` succeeded;
    otherwise the staged diff is returned in `staged_diff` for the
    "would-PR" path.

    `ci_lower_bound` and `fold5_delta` are mirrored from the winning
    iteration's `should_promote` diagnostics so the frontend can render
    the CI bar and frozen-fold delta without re-deriving them.
    """

    promoted: bool
    iteration_count: int = Field(..., ge=0)
    candidates_proposed: int = Field(..., ge=0)
    promotions_applied: int = Field(..., ge=0)
    ci_lower_bound: float | None = Field(default=None)
    fold5_delta: float | None = Field(default=None)
    epsilon_fold5: float | None = Field(default=None)
    promoted_prompt_version: str | None = Field(default=None)
    auto_pr_url: str | None = Field(default=None)
    staged_diff: str | None = Field(default=None)
    trace_id: str | None = Field(default=None)
