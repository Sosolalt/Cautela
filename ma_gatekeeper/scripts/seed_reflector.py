"""D18 Reflector pre-seed — automate HANDOFF.md's 4-step manual workflow.

Plan §6.4 + HANDOFF D18: 48 hours before demo recording we deliberately
seed the `cross_reference` prompt with a WEAKER version under tag
`production` and the strong version under tag `candidate`. The Reflector
then has a real signal to find when it runs nightly, and the auto-promotion
beat in the demo is reproducible rather than staged.

Usage:
  # Dry-run (default): print what would be written, no API calls.
  python -m scripts.seed_reflector

  # Real run against a live Phoenix:
  python -m scripts.seed_reflector --commit

The "weak" template is built deterministically from
`agent.prompts.CROSS_REFERENCE_PROMPT` by stripping the four numbered
clause-family instruction blocks (1-4) — i.e. the agent loses its
guidance on what to look for and only sees the generic instruction
preamble + the severity rubric. The Reflector's meta-prompt then has
something concrete to improve.

Disclosure: README ships the line
  "Production prompt was deliberately seeded weaker 48h before demo
   recording so the auto-improvement loop has a real signal; the loop
   logic itself is unchanged."
This script implements that exact disclosure — see PROJECT_LOG.md
"Pre-commitments locked in."
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass

from agent.prompts import CROSS_REFERENCE_PROMPT

_LOG = logging.getLogger(__name__)

PROMPT_NAME = "cross_reference"
TAG_PRODUCTION = "production"
TAG_CANDIDATE = "candidate"

# Matches the four numbered clause-family blocks "1. **change_of_control** ..."
# down to (but not including) the next "N. **..." heading or the trailing
# "For each finding, emit:" section. Anchored on the bold-tag style of the
# real prompt — see agent/prompts.py:81-119.
_CLAUSE_BLOCK_RE = re.compile(
    r"\n\d+\.\s+\*\*[a-z_]+\*\*.*?(?=\n\d+\.\s+\*\*|\nFor each finding,)",
    re.DOTALL,
)


@dataclass(frozen=True)
class SeedPlan:
    """What the script would do, surfaced for dry-run + tests."""

    prompt_name: str
    weak_template: str
    strong_template: str
    weak_tag: str
    strong_tag: str


def make_weak_template(strong: str = CROSS_REFERENCE_PROMPT) -> str:
    """Strip the per-clause-family instruction blocks to produce a degraded
    prompt the Reflector's meta-improver can recover from.

    Surgical: removes only the four numbered "**clause_family**" blocks,
    leaves the preamble, the cited_spans/explanation/severity rubric,
    and any trailing instructions intact. Guarantees the weak template
    is strictly shorter than the strong template (sanity check below).
    """
    weak = _CLAUSE_BLOCK_RE.sub("", strong)
    # Replace the now-orphan "The four clause families that matter most:"
    # opener so the prompt reads coherently.
    weak = weak.replace(
        "The four clause families\nthat matter most:",
        "Identify deal-critical triggers across the document.",
    ).replace(
        "The four clause families that matter most:",
        "Identify deal-critical triggers across the document.",
    )
    if len(weak) >= len(strong):
        raise RuntimeError(
            "weak template did not shrink — the CROSS_REFERENCE_PROMPT format "
            "may have drifted from the regex; rebuild the regex against the "
            "current prompts.py before running the live seed."
        )
    return weak


def build_seed_plan(strong: str = CROSS_REFERENCE_PROMPT) -> SeedPlan:
    """Build the SeedPlan without touching Phoenix — usable in tests."""
    return SeedPlan(
        prompt_name=PROMPT_NAME,
        weak_template=make_weak_template(strong),
        strong_template=strong,
        weak_tag=TAG_PRODUCTION,
        strong_tag=TAG_CANDIDATE,
    )


def apply_seed_plan(plan: SeedPlan, client=None) -> tuple[str | None, str | None]:
    """Upsert both versions into Phoenix; returns (weak_version_id, strong_version_id).

    Reuses `agent.reflector._upsert_prompt` so the Phoenix API shape stays
    in exactly one place. If `client` is None, build a default
    `phoenix.client.Client()` lazily.
    """
    from agent.reflector import _upsert_prompt

    if client is None:
        from phoenix.client import Client  # type: ignore
        client = Client()

    # ORDER MATTERS: upsert STRONG (candidate) FIRST. If the script fails
    # between the two upserts, the system stays on whatever `production`
    # currently is — never on a half-applied state where production is
    # weak but candidate doesn't exist yet (the Reflector experiment
    # would compare weak-prod against nothing).
    strong_id = _upsert_prompt(
        client, name=plan.prompt_name, template=plan.strong_template, tag=plan.strong_tag
    )
    weak_id = _upsert_prompt(
        client, name=plan.prompt_name, template=plan.weak_template, tag=plan.weak_tag
    )
    return weak_id, strong_id


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write to Phoenix. Without this flag the script is dry-run.",
    )
    parser.add_argument(
        "--show-weak",
        action="store_true",
        help="Print the generated weak template in full (dry-run only).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    plan = build_seed_plan()

    print(f"prompt_name : {plan.prompt_name}")
    print(f"weak  -> tag={plan.weak_tag}   ({len(plan.weak_template)} chars)")
    print(f"strong-> tag={plan.strong_tag} ({len(plan.strong_template)} chars)")
    print(
        f"reduction   : {len(plan.strong_template) - len(plan.weak_template)} chars "
        f"({100 * (1 - len(plan.weak_template) / len(plan.strong_template)):.1f}%)"
    )
    if args.show_weak:
        print("\n---- WEAK TEMPLATE ----\n")
        print(plan.weak_template)
        print("\n---- END ----")

    if not args.commit:
        print("\n[dry-run] no Phoenix writes performed. Re-run with --commit.")
        return 0

    weak_id, strong_id = apply_seed_plan(plan)
    print(f"\nweak  upserted: version_id={weak_id}")
    print(f"strong upserted: version_id={strong_id}")
    if weak_id is None or strong_id is None:
        _LOG.error("at least one upsert failed; review Phoenix logs before D19 recording")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
