"""Citation-gold eval (GROUNDTRUTH_PLAN T1.1).

Grades TWO surfaces against the SAME deliberately-divergent gold set
(`data/citation_gold_v1.jsonl`, audit trail in `data/CITATION_GOLD_SIGNOFF.md`):

  1. the deterministic `citation_map.json` via `lookup_citation`, and
  2. the internal LLM proposer (`agent.citation_linker._call_linker_llm`),
     under a deterministic MOCK by default or the live model under `--live`.

It emits two HONEST map numbers, never one dressed as "accuracy":

  * `map_recall`   — recall@1: does the map's SINGLE best answer for
                     (tag, gold-provided jurisdiction) equal the gold authority?
  * `map_coverage` — contains-anywhere: does ANY map entry for that tag carry
                     the gold authority? This is *coverage, by construction*
                     (primary-source-verified), NOT earned accuracy.

The gap between the two is the honest `candidates[0]` story (an authority the
map HAS for the tag but does not surface as its first entry, e.g. § 271 vs
§ 251). Case-law rows whose gold short form differs from the map's parallel-cite
long form are rescued by the caption-keyed normaliser and counted under
`n_form_mismatch`. Off-map rows (added to de-circularize the gold) are reported
separately: the map correctly returns None/different for all of them.

GUARDRAILS (anti-overclaim, non-negotiable):
  * The JSON ALWAYS carries `run_mode: "mock"|"live"`. A mock proposer number
    is a deterministic stub — the README renderer tags it "MOCK".
  * `confidence_reliability_bins` is OMITTED entirely under mock (a stub has no
    calibration); under `--live` it is 3 coarse bins with a small-n caveat.
  * `jurisdiction` is GOLD-PROVIDED (a hint in metadata), not agent-extracted.

CLI (mirrors scripts/eval_maud_mcq.py conventions; this is intentionally
right-sized — NOT a clone of the 820-line MAUD eval):

    python -m scripts.eval_citation_gold \\
        --gold data/citation_gold_v1.jsonl --out citation_gold_eval.json
    python -m scripts.eval_citation_gold --live \\
        --gold data/citation_gold_v1.jsonl --out citation_gold_eval.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent.citation_linker import (
    citations_match,
    citations_match_kind,
    lookup_citation,
    map_contains_authority_for_tag,
)

_LOG = logging.getLogger(__name__)

_DEFAULT_GOLD = Path(__file__).resolve().parent.parent / "data" / "citation_gold_v1.jsonl"

# One-sided 95% z. Small-n Wilson LB on proposer recall (the gold is ~40 rows,
# so the point estimate alone would overclaim).
_Z_95_ONE_SIDED = 1.6448536269514722


# ---------------------------------------------------------------------------
# Gold loading
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoldRow:
    clause_text: str
    tag: str
    gold_citation: str
    gold_kind: str
    jurisdiction: str | None
    off_map: bool
    deal_id: str

    @property
    def proposer_input(self) -> tuple[str, str]:
        return self.clause_text, self.tag


def load_gold(path: Path) -> list[GoldRow]:
    """Load `citation_gold_v1.jsonl`. Reads `input.tag` (NOT `row['tag']`) and
    `metadata.jurisdiction` (gold-provided hint) per the v1 schema."""
    if not path.exists():
        raise FileNotFoundError(f"--gold path does not exist: {path}")
    rows: list[GoldRow] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{i + 1} is not valid JSON: {exc}") from exc
        inp = obj.get("input", {})
        out = obj.get("output", {})
        meta = obj.get("metadata", {})
        rows.append(GoldRow(
            clause_text=inp.get("clause_text", ""),
            tag=inp.get("tag", ""),
            gold_citation=out.get("citation", ""),
            gold_kind=out.get("citation_kind", "statute"),
            jurisdiction=meta.get("jurisdiction"),
            off_map=bool(meta.get("off_map", False)),
            deal_id=meta.get("deal_id", f"row-{i}"),
        ))
    if not rows:
        raise ValueError(f"--gold file {path} contains no rows")
    return rows


# ---------------------------------------------------------------------------
# Proposers
# ---------------------------------------------------------------------------

# A proposer maps (clause_text, tag, jurisdiction) -> (citation | None, confidence | None).
Proposer = Callable[[str, str, "str | None"], "tuple[str | None, float | None]"]


def make_mock_proposer() -> Proposer:
    """Deterministic stub: mirrors the map's recall@1 answer for (tag,
    jurisdiction). By construction proposer == map, so proposer_recall equals
    map_recall and agreement is trivially 1.0 — this is a REPRODUCIBILITY stub,
    not a model signal. The README renderer labels every mock number "MOCK".
    Confidence is reported as None so the live-only calibration bins are omitted.
    """

    def _propose(clause_text: str, tag: str, jurisdiction: str | None):
        ref = lookup_citation(tag, jurisdiction_hint=jurisdiction)
        return (ref.citation if ref else None), None

    return _propose


def make_live_proposer(timeout: float = 8.0) -> Proposer:
    """Live proposer backed by `agent.citation_linker._call_linker_llm` (Vertex).

    Burns quota only when invoked; the lazy async call is wrapped per-row.
    Confidence is the model's self-reported `model_confidence` (drives the
    live-only `confidence_reliability_bins`). The proposer does NOT receive the
    jurisdiction hint — it sees only the clause + tag, exactly as in production.
    """
    from agent.citation_linker import _call_linker_llm

    def _propose(clause_text: str, tag: str, jurisdiction: str | None):
        try:
            proposal = asyncio.run(_call_linker_llm(clause_text, tag, timeout=timeout))
        except Exception as exc:  # noqa: BLE001 - non-fatal per-row
            _LOG.warning("live proposer failed (tag=%s): %s", tag, exc)
            return None, None
        return proposal.citation, float(proposal.model_confidence)

    return _propose


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def wilson_lower_bound(k: int, n: int, z: float = _Z_95_ONE_SIDED) -> float:
    """One-sided Wilson lower bound on a binomial proportion (small-n honest)."""
    if n <= 0:
        return 0.0
    phat = k / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2.0 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * n)) / n)
    return max(0.0, (centre - margin) / denom)


@dataclass
class RowResult:
    row: GoldRow
    map_citation: str | None
    map_match_kind: str          # exact | section_normalised | case_form | miss
    map_covers: bool             # contains-anywhere for the tag
    proposer_citation: str | None
    proposer_confidence: float | None
    proposer_hit: bool
    agrees_with_map: bool        # proposer vs map recall@1


def _score_row(row: GoldRow, proposer: Proposer) -> RowResult:
    map_ref = lookup_citation(row.tag, jurisdiction_hint=row.jurisdiction)
    map_cit = map_ref.citation if map_ref else None
    match_kind = citations_match_kind(map_cit, row.gold_citation) if map_cit else "miss"
    covers = map_contains_authority_for_tag(row.tag, row.gold_citation)

    prop_cit, prop_conf = proposer(row.clause_text, row.tag, row.jurisdiction)
    prop_hit = bool(prop_cit) and citations_match(prop_cit, row.gold_citation)
    if prop_cit is None and map_cit is None:
        agrees = True
    elif prop_cit is None or map_cit is None:
        agrees = False
    else:
        agrees = citations_match(prop_cit, map_cit)

    return RowResult(
        row=row,
        map_citation=map_cit,
        map_match_kind=match_kind,
        map_covers=covers,
        proposer_citation=prop_cit,
        proposer_confidence=prop_conf,
        proposer_hit=prop_hit,
        agrees_with_map=agrees,
    )


_HIT_KINDS = frozenset({"exact", "section_normalised", "case_form"})


@dataclass
class EvalSummary:
    run_mode: str
    results: list[RowResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        in_map = [r for r in self.results if not r.row.off_map]
        off_map = [r for r in self.results if r.row.off_map]
        n_in_map = len(in_map)
        n_off_map = len(off_map)

        n_hit = sum(1 for r in in_map if r.map_match_kind in {"exact", "section_normalised"})
        n_form = sum(1 for r in in_map if r.map_match_kind == "case_form")
        n_recall_hit = sum(1 for r in in_map if r.map_match_kind in _HIT_KINDS)
        n_recall_miss_covered = sum(
            1 for r in in_map if r.map_match_kind == "miss" and r.map_covers
        )
        n_in_map_true_miss = sum(
            1 for r in in_map if r.map_match_kind == "miss" and not r.map_covers
        )
        n_covered = sum(1 for r in in_map if r.map_covers)

        # Off-map: a row is "correctly missed" when the map does NOT surface the
        # gold authority for the tag (None or a genuinely different authority).
        n_off_correct = sum(1 for r in off_map if not r.map_covers and r.map_match_kind == "miss")
        n_off_false_hit = n_off_map - n_off_correct

        n_prop_hit = sum(1 for r in in_map if r.proposer_hit)
        n_agree = sum(1 for r in self.results if r.agrees_with_map)

        map_recall = n_recall_hit / n_in_map if n_in_map else 0.0
        map_coverage = n_covered / n_in_map if n_in_map else 0.0
        proposer_recall = n_prop_hit / n_in_map if n_in_map else 0.0
        agreement = n_agree / len(self.results) if self.results else 0.0

        out: dict[str, Any] = {
            "run_mode": self.run_mode,
            "n_total": len(self.results),
            "n_evaluated": len(self.results),
            "n_in_map": n_in_map,
            "n_off_map": n_off_map,
            # --- map: two honest numbers + the gap ---
            "map_recall": map_recall,                 # recall@1
            "map_coverage": map_coverage,             # contains-anywhere (by construction)
            "n_in_map_hit": n_hit,
            "n_form_mismatch": n_form,
            "n_in_map_recall_miss_covered": n_recall_miss_covered,  # the candidates[0] gap
            "n_in_map_true_miss": n_in_map_true_miss,
            # --- off-map: map correctly returns None/different ---
            "n_off_map_correctly_missed": n_off_correct,
            "n_off_map_false_hit": n_off_false_hit,
            # --- proposer (mock or live) ---
            "proposer_recall": proposer_recall,
            "proposer_recall_wilson_lb": wilson_lower_bound(n_prop_hit, n_in_map),
            "proposer_vs_map_agreement": agreement,
            # --- per-tag breakdown ---
            "per_tag": self._per_tag(in_map),
            "gold_provenance": {
                "dataset": "citation-gold-v1",
                "path": "data/citation_gold_v1.jsonl",
                "signoff": "data/CITATION_GOLD_SIGNOFF.md",
                "jurisdiction_hint": "gold-provided (metadata.jurisdiction), NOT agent-extracted",
                "map_score_is": "coverage by construction (map_coverage); map_recall is recall@1, not accuracy",
                "agreement_is_not_accuracy": True,
            },
        }
        if self.run_mode == "live":
            out["confidence_reliability_bins"] = self._confidence_bins(in_map)
        # Mock: OMIT the key entirely (a deterministic stub has no calibration).
        return out

    def _per_tag(self, in_map: list[RowResult]) -> dict[str, dict[str, Any]]:
        by_tag: dict[str, list[RowResult]] = {}
        for r in in_map:
            by_tag.setdefault(r.row.tag, []).append(r)
        out: dict[str, dict[str, Any]] = {}
        for tag, items in sorted(by_tag.items()):
            n = len(items)
            map_hits = sum(1 for r in items if r.map_match_kind in _HIT_KINDS)
            prop_hits = sum(1 for r in items if r.proposer_hit)
            out[tag] = {
                "n": n,
                "map": map_hits / n if n else 0.0,
                "proposer": prop_hits / n if n else 0.0,
            }
        return out

    def _confidence_bins(self, in_map: list[RowResult]) -> dict[str, Any]:
        """3 coarse bins (live only). Per-bin n + an explicit small-n caveat —
        NOT 10 bins; n≈40 cannot support a fine calibration curve."""
        bins = {"low": [], "med": [], "high": []}
        for r in in_map:
            c = r.proposer_confidence
            if c is None:
                continue
            key = "low" if c < 0.5 else ("med" if c < 0.8 else "high")
            bins[key].append(r)
        out: dict[str, Any] = {
            "_caveat": "n≈40, illustrative, ungrounded calibration — 3 coarse bins only",
        }
        for name, items in bins.items():
            n = len(items)
            acc = sum(1 for r in items if r.proposer_hit) / n if n else 0.0
            out[name] = {"n": n, "proposer_accuracy_in_bin": acc}
        return out


def run_eval(rows: list[GoldRow], proposer: Proposer, *, run_mode: str) -> EvalSummary:
    return EvalSummary(run_mode=run_mode,
                       results=[_score_row(r, proposer) for r in rows])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gold", type=Path, default=_DEFAULT_GOLD,
                   help="Path to citation_gold_v1.jsonl.")
    p.add_argument("--out", type=Path, default=Path("citation_gold_eval.json"),
                   help="Where to write the summary JSON.")
    p.add_argument("--live", action="store_true", default=False,
                   help="Use the live LLM proposer (burns Vertex quota). "
                        "Default is a deterministic mock — zero quota, "
                        "reproducible across CI runs.")
    p.add_argument("--proposer-timeout", type=float, default=45.0,
                   help="Per-row LLM timeout (seconds) for the --live proposer. "
                        "Eval must WAIT for the real answer (gemini-3.1-pro "
                        "calls run ~9s+), unlike production's deliberate 8s "
                        "fail-fast guard. Too low => asyncio.TimeoutError on "
                        "every row and a falsely-low proposer recall.")
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)

    rows = load_gold(args.gold)
    run_mode = "live" if args.live else "mock"
    proposer = (make_live_proposer(timeout=args.proposer_timeout)
                if args.live else make_mock_proposer())
    summary = run_eval(rows, proposer, run_mode=run_mode)
    data = summary.to_json()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _LOG.info(
        "citation-gold [%s]: map_recall=%.3f map_coverage=%.3f "
        "proposer_recall=%.3f (n_in_map=%d, off_map=%d/%d correctly missed); wrote %s",
        run_mode, data["map_recall"], data["map_coverage"], data["proposer_recall"],
        data["n_in_map"], data["n_off_map_correctly_missed"], data["n_off_map"], args.out,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
