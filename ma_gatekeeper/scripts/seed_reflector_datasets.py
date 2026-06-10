"""Seed the three Phoenix datasets the Reflector cycle evaluates against.

`run_reflection_cycle` runs pairwise experiments (candidate vs production) over
three datasets that must already exist in Phoenix:

  - `regressions-v1`            (writable; grown nightly from failing traces)
  - `internal-30-holdout-fold-5` (frozen held-out non-regression set)
  - `citation-gold-v1`          (frozen citation ground truth B)

Without them every experiment returns empty deltas and `should_promote` can
never fire. This script builds each dataset from REAL Internal-30 / citation
gold — nothing fabricated:

  - regressions-v1            <- reconciled_gold rows from the `demo_path` contracts
  - internal-30-holdout-fold-5 <- reconciled_gold rows from the `calibration_core` contracts
  - citation-gold-v1          <- data/citation_gold_v1.jsonl

The two reconciled-gold sources are disjoint by contract (demo_path vs
calibration_core), so the regression set and the held-out fold share no
contract. Each example carries `clause_text` as the single input key (exactly
what `agent.reflector._evaluate_one_example` reads).

Usage:
  PHOENIX_COLLECTOR_ENDPOINT=https://phoenix-prod-... \\
      python -m scripts.seed_reflector_datasets [--recreate]

Idempotent: skips a dataset that already exists unless --recreate is passed.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from scripts.build_internal30_gold import MANIFEST, REPO

_LOG = logging.getLogger(__name__)

RECONCILED = REPO / "data" / "internal30" / "reconciled_gold.jsonl"
CITATION = REPO / "data" / "citation_gold_v1.jsonl"

# Deterministic per-dataset caps (sorted by item_id, head N) — keeps the live
# experiment fast/cheap while leaving the regression set large enough for the
# paired-bootstrap CI to have a chance of clearing LB>0.
N_REGRESSIONS = 20
N_FOLD5 = 15
N_CITATION = 20
MAX_CLAUSE_CHARS = 2000


def _set_of_contract() -> dict[str, str]:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {d["deal_id"]: d.get("set", "?") for d in m["deals"]}


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _clip(text: str) -> str:
    text = (text or "").strip()
    return text[:MAX_CLAUSE_CHARS]


def build_reconciled_examples(target_set: str, n: int) -> list[dict]:
    set_of = _set_of_contract()
    rows = [g for g in _load_jsonl(RECONCILED) if set_of.get(g["contract_id"]) == target_set]
    rows.sort(key=lambda g: g.get("item_id") or g.get("clause_id") or "")
    out = []
    for g in rows[:n]:
        ct = _clip(g.get("text", ""))
        if not ct:
            continue
        tag, sev = g.get("tag", ""), g.get("severity", "")
        out.append({
            "input": {"clause_text": ct},
            "output": {"tag": tag, "severity": sev},
            "metadata": {"tag": tag, "severity": sev, "contract_id": g.get("contract_id", "")},
        })
    return out


def build_citation_examples(n: int) -> list[dict]:
    rows = _load_jsonl(CITATION)
    rows.sort(key=lambda r: json.dumps(r.get("input", {}), sort_keys=True))
    out = []
    for r in rows[:n]:
        inp = r.get("input", {})
        if isinstance(inp, str):
            try:
                inp = json.loads(inp.replace("'", '"'))
            except Exception:
                inp = {"clause_text": inp}
        ct = _clip(inp.get("clause_text", ""))
        if not ct:
            continue
        tag = inp.get("tag", "")
        out.append({
            "input": {"clause_text": ct},
            "output": {"tag": tag},
            "metadata": {"tag": tag},
        })
    return out


def _existing_names(client) -> set[str]:
    try:
        return {getattr(d, "name", None) or d.get("name") for d in client.datasets.list()}
    except Exception as exc:
        _LOG.warning("datasets.list failed (assuming none): %s", exc)
        return set()


def seed_one(client, *, name: str, examples: list[dict],
             description: str, existing: set[str], recreate: bool) -> bool:
    if not examples:
        _LOG.error("dataset %s: NO examples built — source data missing?", name)
        return False
    if name in existing and not recreate:
        print(f"  [skip] {name} already exists ({len(examples)} examples available). "
              f"Pass --recreate to add a new version.")
        return True
    client.datasets.create_dataset(
        name=name,
        examples=examples,
        dataset_description=description,
        timeout=120,
    )
    print(f"  [ok]   {name}: {len(examples)} examples")
    return True


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recreate", action="store_true",
                   help="Create a new version even if the dataset already exists.")
    args = p.parse_args(argv)

    from phoenix.client import Client
    client = Client()
    existing = _existing_names(client)

    regressions = build_reconciled_examples("demo_path", N_REGRESSIONS)
    fold5 = build_reconciled_examples("calibration_core", N_FOLD5)
    citation = build_citation_examples(N_CITATION)

    print(f"built: regressions-v1={len(regressions)} fold5={len(fold5)} citation={len(citation)}")
    ok = True
    ok &= seed_one(client, name="regressions-v1", examples=regressions,
                   description="Internal-30 demo_path clauses (writable regression set)",
                   existing=existing, recreate=args.recreate)
    ok &= seed_one(client, name="internal-30-holdout-fold-5", examples=fold5,
                   description="Internal-30 calibration_core clauses (frozen held-out fold)",
                   existing=existing, recreate=args.recreate)
    ok &= seed_one(client, name="citation-gold-v1", examples=citation,
                   description="citation-gold-v1 clauses (frozen citation ground truth B)",
                   existing=existing, recreate=args.recreate)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
