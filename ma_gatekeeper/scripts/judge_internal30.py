"""D8 inference producer — score the human-validated Internal-30 gold findings
with the live Risk-Judge evaluators and emit the calibration CSV that
`scripts/calibrate.py` consumes (plan §5.4 / §8 step 6).

`calibrate.py` does NOT read `reconciled_gold.jsonl`; it reads a CSV of
judged findings. This script is the missing bridge: for every gold span it
runs the two inline judges (`agent/evaluators.py:run_inline_judges`) to get a
hallucination score `h_score` and a faithfulness score `f_score`, takes
`is_block` from the human-validated gold severity, and groups by the manifest
`set` as the calibration `source`. The output columns are exactly:

    contract_id, source, finding_id, severity, h_score, f_score, is_block

Usage:
  # Default: deterministic MOCK (no Vertex quota burn) — wiring/test only.
  python -m scripts.judge_internal30 --out data/internal30/judged_findings.csv

  # Live judges (opt-in; needs the Vertex env from .env: GOOGLE_GENAI_USE_VERTEXAI=TRUE
  # + GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION, same as the MAUD/CUAD --live runs):
  python -m scripts.judge_internal30 --live --out data/internal30/judged_findings.csv

Then calibrate:
  python -m scripts.calibrate --input data/internal30/judged_findings.csv \\
      --out thresholds.json

The MOCK path emits deterministic scores derived from a hash of the finding id;
it is for exercising the CSV shape and the calibrate pipeline WITHOUT a real
model. Only `--live` produces the real Internal-30 Block-recall number — the
mock must never be reported as the headline.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Protocol

from scripts.build_internal30_gold import REPO, MANIFEST, OUT_DIR, load_contracts

_LOG = logging.getLogger(__name__)

GOLD_PATH = OUT_DIR / "reconciled_gold.jsonl"
# Chars of contract context each side of the span for the hallucination judge.
# Widened from 400 -> 3000 (Phase 14): a ±400 window clipped the supporting
# language for many gold spans into neighbouring clauses, so the hallucination
# judge couldn't see the grounding and scored false `hallucinated`. ~3k chars
# each side gives the model the adjacent clauses / defined terms it needs to
# synthesize, well inside the model context budget for one finding at a time.
CONTEXT_PAD = 3000


class _JudgeFn(Protocol):
    """(context, explanation, clause_text, tag, trigger_language) -> (h, f)."""

    def __call__(
        self, context: str, explanation: str, clause_text: str, tag: str,
        trigger_language: str = "",
    ) -> tuple[float, float]: ...


def make_mock_judge(seed: int = 42) -> _JudgeFn:
    """Deterministic stub — NO model call. Scores are a stable hash of the
    clause text, so the CSV shape and the calibrate pipeline can be exercised
    with zero quota. NEVER report mock numbers as the headline."""

    def _judge(context: str, explanation: str, clause_text: str, tag: str,
               trigger_language: str = "") -> tuple[float, float]:
        digest = hashlib.sha256((tag + "::" + clause_text).encode("utf-8")).digest()
        h = 0.5 + (digest[0] / 255.0) * 0.5  # in [0.5, 1.0]
        f = 0.5 + (digest[1] / 255.0) * 0.5
        return round(h, 4), round(f, 4)

    return _judge


def make_live_judge() -> _JudgeFn:
    """Live judges via `agent.evaluators.run_inline_judges` (Gemini on Vertex).

    The phoenix classifiers are module-level lru_cached, so the LLM client is
    built once and reused across all findings. Import is deferred so the mock
    path (and tests) never require phoenix-evals / Vertex creds."""

    def _judge(context: str, explanation: str, clause_text: str, tag: str,
               trigger_language: str = "") -> tuple[float, float]:
        from agent.evaluators import run_inline_judges

        h_score, _h_label, f_score, _f_label = run_inline_judges(
            context=context,
            explanation=explanation,
            clause_text=clause_text,
            tag=tag,
            trigger_language=trigger_language,
        )
        return float(h_score), float(f_score)

    return _judge


def _source_by_contract() -> dict[str, str]:
    """contract_id -> manifest `set` (the calibration `source` / fold group)."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {d["deal_id"]: d.get("set", "unknown") for d in manifest["deals"]}


def load_gold_findings(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def judge_corpus(judge: _JudgeFn, gold_path: Path = GOLD_PATH) -> list[dict[str, Any]]:
    contracts = load_contracts()
    source_of = _source_by_contract()
    findings = load_gold_findings(gold_path)
    out: list[dict[str, Any]] = []
    for i, g in enumerate(findings):
        cid = g["contract_id"]
        text = contracts[cid]
        start, end = int(g["char_start"]), int(g["char_end"])
        context = text[max(0, start - CONTEXT_PAD) : min(len(text), end + CONTEXT_PAD)]
        h_score, f_score = judge(
            context=context,
            explanation=g.get("explanation", ""),
            clause_text=g["text"],
            tag=g["tag"],
            trigger_language=g.get("trigger_language", ""),
        )
        out.append({
            "contract_id": cid,
            "source": source_of.get(cid, "unknown"),
            "finding_id": g.get("item_id") or f"{cid}#{i:04d}",
            "severity": g["severity"],
            "h_score": h_score,
            "f_score": f_score,
            "is_block": int(g["severity"] == "block"),
        })
        if (i + 1) % 50 == 0:
            _LOG.info("judged %d/%d findings", i + 1, len(findings))
    return out


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["contract_id", "source", "finding_id", "severity", "h_score", "f_score", "is_block"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold", type=Path, default=GOLD_PATH)
    p.add_argument("--out", type=Path, default=OUT_DIR / "judged_findings.csv")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--use-mock", action="store_true", default=True,
                   help="Deterministic stub, zero quota (default).")
    g.add_argument("--live", action="store_true", default=False,
                   help="Live Gemini judges (burns Vertex quota).")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    judge = make_live_judge() if args.live else make_mock_judge(seed=args.seed)
    rows = judge_corpus(judge, args.gold)
    write_csv(rows, args.out)
    n_block = sum(r["is_block"] for r in rows)
    mode = "LIVE" if args.live else "MOCK"
    print(
        f"[{mode}] wrote {len(rows)} judged findings to {args.out}\n"
        f"  is_block=1 : {n_block}\n"
        f"  sources    : {sorted({r['source'] for r in rows})}\n"
        f"  contracts  : {len({r['contract_id'] for r in rows})}\n"
        + ("  (MOCK scores — NOT the headline; re-run with --live for the real number)"
           if not args.live else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
