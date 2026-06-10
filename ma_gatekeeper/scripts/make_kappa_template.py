"""Human-vs-model κ template emitter (GROUNDTRUTH_PLAN T1.3).

Produces a BLANK-tag adjudication template the OPERATOR (a human, not Claude)
fills in to compute one real human-vs-one-LLM tag agreement on Internal-30.

Why this script is REQUIRED (not optional):
  * `scripts/annotate.py kappa` keys on `(contract_id, clause_id, char_start)`.
    Eyeballed offsets that drift from the prelabels produce an EMPTY
    intersection -> `cohen_kappa` raises "no overlapping clause_ids" and the κ
    is undefined. Deriving the template FROM the prelabels guarantees the keys
    match exactly.
  * The prelabel (the model's suggested tag) is WITHHELD from the template so
    the human is not anchored to the model's answer — otherwise the κ measures
    "did the human agree with what we showed them", not independent agreement.

SCOPE / HONEST CLAIM (re-scoped per GROUNDTRUTH_PLAN validation):
  The resulting κ is **human-vs-one-LLM TAG agreement on Internal-30 — a sanity
  check on the tag layer, NOT a measure of citation-gold reliability.** Report
  it verbatim as such, with per-class support / a small confusion matrix (a
  high κ can be driven by the `change_of_control` marginal).

Operator workflow:
  1. python -m scripts.make_kappa_template \\
         --prelabels data/internal30/prelabels.jsonl \\
         --out data/internal30/kappa_template.jsonl --n 12
  2. A human fills the blank `tag` on each line (out-of-vocab tag -> reject),
     saves as `data/internal30/human_adjudicated.jsonl`.
  3. python -m scripts.annotate kappa \\
         data/internal30/prelabels.jsonl data/internal30/human_adjudicated.jsonl

This script does NOT call any LLM and burns zero quota.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)

# The valid tag vocabulary, surfaced in the template header so the human knows
# the closed set. Mirrors agent/schemas.py Tag (kept as a literal so this script
# does not import the pydantic stack just to enumerate strings).
TAG_VOCAB = (
    "change_of_control", "anti_assignment", "mac", "accelerated_vesting",
    "exclusivity", "ip_assignment", "non_compete", "none",
)


def _span_key_fields(rec: dict[str, Any]) -> dict[str, Any] | None:
    """Extract (contract_id, clause_id, char_start, char_end, text) from a
    prelabel record — tolerant of BOTH the Argilla SpanQuestion shape (with a
    `metadata` block + `suggestions`) and the flat shape. The suggested TAG is
    deliberately NOT extracted — it is withheld from the template."""
    if "metadata" in rec:
        meta = rec["metadata"]
        cid = meta.get("contract_id")
        clid = meta.get("clause_id")
        text = rec.get("fields", {}).get("text", "")
        char_start = char_end = None
        for sug in rec.get("suggestions", []):
            if sug.get("question_name") == "span" and sug.get("value"):
                char_start = int(sug["value"][0]["start"])
                char_end = int(sug["value"][0]["end"])
                break
    else:
        cid = rec.get("contract_id")
        clid = rec.get("clause_id")
        text = rec.get("text", "")
        char_start = rec.get("char_start")
        char_end = rec.get("char_end")
    if cid is None or clid is None or char_start is None:
        return None
    return {
        "contract_id": cid,
        "clause_id": str(clid),
        "char_start": int(char_start),
        "char_end": int(char_end) if char_end is not None else int(char_start),
        "text": text,
    }


def load_prelabel_spans(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"--prelabels path does not exist: {path}")
    spans: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = _span_key_fields(json.loads(line))
        if fields is not None:
            spans.append(fields)
    if not spans:
        raise ValueError(f"--prelabels file {path} yielded no usable spans")
    return spans


def select_spans(spans: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """Deterministically select up to `n` spans, SPREAD across contracts so the
    κ is not dominated by one document. Round-robin over contracts after a
    stable sort — no RNG, so the same prelabels always yield the same template.
    """
    by_contract: dict[str, list[dict[str, Any]]] = {}
    for s in sorted(spans, key=lambda r: (r["contract_id"], r["clause_id"], r["char_start"])):
        by_contract.setdefault(s["contract_id"], []).append(s)

    selected: list[dict[str, Any]] = []
    contracts = sorted(by_contract)
    idx = 0
    while len(selected) < n and any(by_contract.values()):
        cid = contracts[idx % len(contracts)]
        bucket = by_contract[cid]
        if bucket:
            selected.append(bucket.pop(0))
        idx += 1
        # Stop if every bucket is exhausted.
        if all(not v for v in by_contract.values()):
            break
    return selected[:n]


def make_template_records(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit flat records with a BLANK `tag` (prelabel withheld). Keys match the
    prelabels exactly so `annotate.py kappa`'s intersection is non-empty."""
    return [
        {
            "contract_id": s["contract_id"],
            "clause_id": s["clause_id"],
            "char_start": s["char_start"],
            "char_end": s["char_end"],
            "text": s["text"],
            "tag": "",  # <-- HUMAN fills this; model suggestion withheld (no anchoring)
        }
        for s in spans
    ]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--prelabels", type=Path, required=True,
                   help="Path to the model prelabels JSONL (Argilla or flat shape).")
    p.add_argument("--out", type=Path, required=True,
                   help="Where to write the blank-tag template JSONL.")
    p.add_argument("--n", type=int, default=12,
                   help="Number of clauses to emit (plan: 10-15). Default 12.")
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    if not (10 <= args.n <= 15):
        _LOG.warning("--n=%d is outside the plan's 10-15 range; proceeding anyway.", args.n)

    spans = load_prelabel_spans(args.prelabels)
    selected = select_spans(spans, args.n)
    records = make_template_records(selected)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    _LOG.info(
        "wrote %d blank-tag template rows to %s (tag vocab: %s)",
        len(records), args.out, ", ".join(TAG_VOCAB),
    )
    _LOG.info(
        "NEXT (operator, human): fill `tag` on each row, save as "
        "human_adjudicated.jsonl, then run `python -m scripts.annotate kappa "
        "%s human_adjudicated.jsonl`. The resulting κ is human-vs-one-LLM TAG "
        "agreement on Internal-30 — a tag-layer sanity check, NOT citation-gold "
        "reliability.", args.prelabels,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
