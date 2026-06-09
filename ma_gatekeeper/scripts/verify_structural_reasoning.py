"""Fix 6 — structural-reasoning demo-beat verifier.

Day-3 dry-run gate for the "same anti-assignment clause, opposite verdicts"
demo beat (`docs/demo_script.md` 1:55–2:05 conditional row).

Trust model: fixtures at `tests/fixtures/structural_reasoning_pair.json`
are TRUSTED inputs (repo-committed) and flow into Gemini 3 Pro prompts on
`--live`. Any future fixture edit is a prompt-injection vector and MUST be
reviewed as code, not as test data.

The premise (per the M&A partner critic in FIX_PLAN): the agent must
visibly do CROSS-CLAUSE STRUCTURAL REASONING. Same boilerplate
anti-assignment language in two contracts; one is a reverse triangular
merger under Delaware law (Meso Scale v. Roche controlling — RTM is NOT
assignment by operation of law, so the clause does NOT trigger);
the other is a forward merger under Sixth Circuit precedent
(Cincom v. Novelis + PPG v. Guardian controlling — forward merger DOES
constitute assignment by operation of law, so the clause DOES trigger).

V3 (FIX_PLAN_NOTES.md) confirmed `agents.py:100-105` instantiates
CrossReference as a real `gemini-3-pro-preview` LlmAgent with
`output_key="findings"` and a definition->operative resolution prompt
(`prompts.py:CROSS_REFERENCE_PROMPT`). Whether the agent ACTUALLY produces
structure-conditional verdicts on these paired fixtures is empirically
open — that's exactly what this script tests on the Day-3 dry run.

Cut-criteria (FIX_PLAN, load-bearing): "only ship if V3 + the demo
verifies. **Faking it is worse than skipping.**" If `--live` exits 1,
the recording-day operator MUST cut the structural-reasoning beat from
`docs/demo_script.md` and revert the 10s budget by restoring
Honest-numbers (1:55–2:15, 20s). The conditional block in
`demo_script.md` makes this the default unless this script passes.

Usage:
  # Default: mock mode — validates fixture wiring + expected-verdict
  # matching logic without exercising the live agent. Reproducible,
  # zero-quota; runs in CI.
  python -m scripts.verify_structural_reasoning

  # Live: burns Vertex quota; the actual Day-3 gate. Mirrors
  # `eval_maud_mcq.py:make_live_agent` (PROJECT_LOG Phase 6.6) — raises
  # NotImplementedError unless the Runner wrapper is wired in by the
  # operator. This is the established convention; CI must never silently
  # no-op on `--live`.
  python -m scripts.verify_structural_reasoning --live

Exit codes:
  0  Both fixtures produced structure-conditional verdicts as expected
     (RTM = no-trigger citing Meso Scale; forward = trigger citing
     Cincom / PPG). Demo beat is SHIPPABLE.
  1  Agent failed to differentiate (one or both verdicts mismatched
     the expected structure-conditional outcome). Recommended demo
     decision: CUT the beat per FIX_PLAN cut-criteria.
  2  Fixture wiring / schema error (script bug, not an agent failure).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

_LOG = logging.getLogger(__name__)


# Fixture lives next to the tests it backs. The script reaches across
# package roots because the fixture is the single source of truth for
# both this verifier and `tests/test_verify_structural_reasoning.py`.
_DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "structural_reasoning_pair.json"
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Clause:
    """Mirror of `agent.schemas.Clause` minus pdf_bbox.

    We don't import `agent.schemas` directly to keep this script importable
    in CI environments where the ADK / Pydantic stack is partially
    installed. Fields match `schemas.py:38-49`.
    """

    id: str
    section_path: list[str]
    text: str
    page: int
    char_start: int
    char_end: int


@dataclass(frozen=True)
class StructuralFixture:
    """One mini-contract — the unit the CrossReference agent reasons over."""

    fixture_id: str
    deal_structure: str
    structure_narrative: str
    target_entity: str
    governing_law: str
    expected_severity: str  # "info" | "watch" | "block" — schemas.py:34
    expected_rationale_keywords: list[str]
    clauses: list[Clause]


@dataclass
class VerdictResult:
    """Output of running CrossReference on one fixture.

    Field names mirror what `agents.py:100-105` declares the cross_reference
    agent produces under `output_key="findings"` (which is a list of
    RiskFinding-shaped objects per `schemas.py:58-108`). We collapse the
    list to the single highest-severity finding for the structural-reasoning
    check — the demo beat shows ONE verdict per fixture, not a list.
    """

    fixture_id: str
    severity: str
    cited_spans: list[str]
    explanation: str

    def matches_expected(
        self, expected_severity: str, expected_rationale_keywords: list[str]
    ) -> tuple[bool, str]:
        """Return (passed, diagnostic).

        Passes IFF:
          1. severity == expected_severity (exact label match — the
             schemas.py:34 Severity Literal is closed: info/watch/block).
          2. At least 2 of the expected rationale keywords appear (case-
             insensitive substring) in `explanation`. The "2 of N" floor is
             deliberately loose — the agent may phrase Meso Scale as "Meso
             Scale Diagnostics," cite "VC Parsons" instead of the case
             name, or use "RTM" instead of spelling it out. We want
             structural-reasoning evidence, not exact-string matching.
        """
        if self.severity != expected_severity:
            return False, (
                f"severity mismatch: expected {expected_severity!r}, "
                f"got {self.severity!r}"
            )
        hay = self.explanation.lower()
        hits = [k for k in expected_rationale_keywords if k.lower() in hay]
        if len(hits) < 2:
            return False, (
                f"rationale missing structural-reasoning evidence: "
                f"matched only {hits!r} of {expected_rationale_keywords!r} "
                f"in explanation={self.explanation!r}"
            )
        return True, f"matched severity + keywords {hits!r}"


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------


def load_fixtures(path: Path | str = _DEFAULT_FIXTURE_PATH) -> list[StructuralFixture]:
    """Parse the JSON pair into typed StructuralFixture objects.

    Raises FileNotFoundError / KeyError loudly — silent fallthrough on a
    malformed fixture would mask the very wiring this script exists to
    validate.
    """
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    fixtures: list[StructuralFixture] = []
    for raw in payload["pairs"]:
        clauses = [
            Clause(
                id=c["id"],
                section_path=list(c["section_path"]),
                text=c["text"],
                page=c["page"],
                char_start=c["char_start"],
                char_end=c["char_end"],
            )
            for c in raw["clauses"]
        ]
        fixtures.append(
            StructuralFixture(
                fixture_id=raw["fixture_id"],
                deal_structure=raw["deal_structure"],
                structure_narrative=raw["structure_narrative"],
                target_entity=raw["target_entity"],
                governing_law=raw["governing_law"],
                expected_severity=raw["expected_verdict"]["severity"],
                expected_rationale_keywords=list(
                    raw["expected_verdict"]["rationale_keywords"]
                ),
                clauses=clauses,
            )
        )
    return fixtures


# ---------------------------------------------------------------------------
# Agent contract (mock + live)
# ---------------------------------------------------------------------------


class _CrossReferenceFn(Protocol):
    """Callable contract: (fixture) -> VerdictResult.

    The default impl wraps CrossReference via the ADK Runner; tests pass
    deterministic mocks; CLI `--use-mock` / `--live` choose which path
    runs. Mirrors `eval_maud_mcq.py:_AgentFn` per PROJECT_LOG Phase 6.6.
    """

    def __call__(self, fixture: StructuralFixture) -> VerdictResult: ...


def make_mock_cross_reference() -> _CrossReferenceFn:
    """Deterministic mock keyed on `deal_structure`.

    Returns the EXPECTED structure-conditional verdict for each fixture —
    this is what lets CI verify the wiring (fixture load -> agent call ->
    verdict matching) without burning Vertex quota. It does NOT validate
    that the LIVE agent reasons correctly; that's the `--live` path's job.

    The mock is deliberately NOT random: a randomized mock would mean a
    green CI run says nothing about the wiring's correctness on Day 3.
    """

    def _agent(fixture: StructuralFixture) -> VerdictResult:
        if fixture.deal_structure == "reverse_triangular_merger_delaware_law":
            return VerdictResult(
                fixture_id=fixture.fixture_id,
                severity="info",
                cited_spans=[
                    "def_assignment",
                    "sec_12_3_anti_assignment",
                    "recital_b_structure",
                ],
                explanation=(
                    "Under Meso Scale v. Roche (Del. Ch. 2013), a reverse "
                    "triangular merger is NOT an assignment by operation of "
                    "law because the target survives as the contracting "
                    "entity — only its equity ownership changes. No "
                    "anti-assignment trigger; treat as informational."
                ),
            )
        if fixture.deal_structure == "forward_merger":
            return VerdictResult(
                fixture_id=fixture.fixture_id,
                severity="block",
                cited_spans=[
                    "def_assignment",
                    "sec_12_3_anti_assignment",
                    "recital_b_structure",
                ],
                explanation=(
                    "Under Cincom v. Novelis (6th Cir. 2009) and PPG v. "
                    "Guardian (6th Cir. 1979), a forward merger constitutes "
                    "an assignment by operation of law: the target ceases "
                    "to exist and its contracts vest in the surviving "
                    "entity. The anti-assignment clause triggers — consent "
                    "required."
                ),
            )
        # Unknown structure -> deliberately non-matching verdict so the
        # matcher fails loudly. Helps the test suite verify mismatch paths.
        return VerdictResult(
            fixture_id=fixture.fixture_id,
            severity="watch",
            cited_spans=[],
            explanation="unknown deal_structure; mock declines to reason.",
        )

    return _agent


def make_live_cross_reference() -> _CrossReferenceFn:
    """Wrap the real ADK CrossReference agent on `gemini-3-pro-preview`.

    Implementation note (mirrors `eval_maud_mcq.py:make_live_agent`,
    PROJECT_LOG Phase 6.6): CrossReference is a sub-agent inside the
    SequentialAgent root (`agents.py:114-117`). A standalone invocation
    requires constructing an `LlmAgent` with `CROSS_REFERENCE_PROMPT` plus
    a synthetic classifier-stage input ("classified clauses"), wrapping it
    in an ADK Runner, and parsing the `findings` output_key as a list of
    RiskFinding-shaped objects (`schemas.py:58-108`).

    This Runner wrapper is out of scope for a verification script — the
    operator must wire it before Day 3. We raise loudly so CI never
    silently no-ops on `--live` (same convention as
    `eval_maud_mcq.py:212-226`).
    """
    raise NotImplementedError(
        "Live CrossReference verification requires an ADK Runner wrapper "
        "around the LlmAgent at agents.py:100-105 with CROSS_REFERENCE_PROMPT "
        "from prompts.py:90+. Build one in "
        "scripts/verify_structural_reasoning.py:make_live_cross_reference "
        "before re-enabling --live, OR call run_verification() with a "
        "custom agent callable from a Day-3 driver script."
    )


# ---------------------------------------------------------------------------
# Verification core
# ---------------------------------------------------------------------------


@dataclass
class FixtureOutcome:
    fixture_id: str
    passed: bool
    diagnostic: str
    verdict: VerdictResult


@dataclass
class VerificationReport:
    outcomes: list[FixtureOutcome] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return bool(self.outcomes) and all(o.passed for o in self.outcomes)

    def failure_messages(self) -> list[str]:
        return [
            f"[{o.fixture_id}] {o.diagnostic} | got verdict={o.verdict!r}"
            for o in self.outcomes
            if not o.passed
        ]


def run_verification(
    fixtures: list[StructuralFixture],
    agent: _CrossReferenceFn,
) -> VerificationReport:
    """Run `agent` on each fixture; return per-fixture pass/fail outcomes.

    Pure function — no I/O, no logging side effects — so tests can drive
    it with arbitrary mock agents to validate the matcher logic.
    """
    report = VerificationReport()
    for fx in fixtures:
        verdict = agent(fx)
        passed, diag = verdict.matches_expected(
            fx.expected_severity, fx.expected_rationale_keywords
        )
        report.outcomes.append(
            FixtureOutcome(
                fixture_id=fx.fixture_id,
                passed=passed,
                diagnostic=diag,
                verdict=verdict,
            )
        )
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=_DEFAULT_FIXTURE_PATH,
        help="Path to structural_reasoning_pair.json. Default: the in-repo fixture.",
    )
    # Mutually exclusive: --use-mock (default, safe) vs --live (burns quota).
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--use-mock",
        action="store_true",
        default=True,
        help=(
            "Use the deterministic mock CrossReference. Default. "
            "Validates fixture wiring + matcher; zero Vertex quota."
        ),
    )
    group.add_argument(
        "--live",
        action="store_true",
        default=False,
        help=(
            "Burn Vertex quota with the real CrossReference agent. The "
            "Day-3 gate. Exit 1 = CUT the demo beat per FIX_PLAN cut-criteria."
        ),
    )
    return parser


_CUT_RECOMMENDATION = (
    "RECOMMENDED DEMO DECISION: CUT the structural-reasoning beat from "
    "docs/demo_script.md and revert the 10s budget by restoring Honest-numbers "
    "(1:55–2:15, 20s). Per FIX_PLAN cut-criteria — faking it is worse than "
    "skipping. Lean on Fix 2 (BMS cold open) + Fix 5 (Arize MCP rewire) for "
    "the demo's headline beats."
)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = _build_parser().parse_args(argv)

    try:
        fixtures = load_fixtures(args.fixture)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        _LOG.error("Fixture load failed: %s", exc)
        return 2
    _LOG.info("Loaded %d structural-reasoning fixtures from %s",
              len(fixtures), args.fixture)
    if len(fixtures) != 2:
        _LOG.error(
            "Expected exactly 2 paired fixtures (RTM + forward merger); "
            "got %d. Aborting.",
            len(fixtures),
        )
        return 2

    if args.live:
        try:
            agent = make_live_cross_reference()
        except NotImplementedError as exc:
            _LOG.error("--live not wired: %s", exc)
            _LOG.error(_CUT_RECOMMENDATION)
            return 1
    else:
        agent = make_mock_cross_reference()
        _LOG.info("Running in mock mode (default). Use --live for the Day-3 gate.")

    report = run_verification(fixtures, agent)
    for outcome in report.outcomes:
        if outcome.passed:
            _LOG.info("[%s] PASS — %s", outcome.fixture_id, outcome.diagnostic)
        else:
            _LOG.error(
                "[%s] FAIL — %s | severity=%s | explanation=%r",
                outcome.fixture_id,
                outcome.diagnostic,
                outcome.verdict.severity,
                outcome.verdict.explanation,
            )

    if report.all_passed:
        if args.live:
            _LOG.info(
                "All fixtures produced structure-conditional verdicts on "
                "the LIVE agent. Demo beat is SHIPPABLE."
            )
        else:
            _LOG.info(
                "MOCK MODE — fixture/matcher wiring OK; this is NOT a SHIP "
                "signal. Re-run with --live for the Day-3 gate."
            )
        return 0

    _LOG.error("Structural-reasoning verification FAILED.")
    for msg in report.failure_messages():
        _LOG.error("  %s", msg)
    _LOG.error(_CUT_RECOMMENDATION)
    return 1


if __name__ == "__main__":
    sys.exit(main())
