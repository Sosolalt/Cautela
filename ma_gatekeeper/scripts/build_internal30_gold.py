"""Deterministic grounding + adjudication assembly for the Internal-30 gold set.

This is the *plain-code* half of the human-in-the-loop annotation pipeline
described in `docs/internal30_annotation_cohort.md` and
`docs/internal30_workflow_kickoff_prompt.md`. The LLM cohorts (Pass A / Pass B
specialists + reconcilers, and the adjudication cohort) run as a multi-agent
Workflow and emit *verbatim span text with NO offsets* — because LLMs cannot
count characters. This module does everything that must be deterministic:

  1. `ground`   — turn a cohort's raw spans (verbatim text + metadata) into
                  byte-exact PrelabelSpan rows against the canonical
                  data/edgar/<deal_id>.txt, dropping any span that cannot be
                  located verbatim (NEVER inventing an offset). Writes the
                  Argilla-compatible JSONL that `scripts.annotate` consumes.
  2. `align`    — align Pass A vs Pass B per contract (char-overlap Jaccard
                  >= 0.5), bucket agree / tag-disagreement / solo-A / solo-B,
                  and emit the adjudication work-items (with surrounding
                  contract context) the adjudication cohort reasons over.
  3. `assemble` — fold the adjudication cohort's recommendations back in and
                  write reconciled_gold.jsonl + human_review_packet.md.

GROUNDING ENGINE — why a flexible regex, not str.find:
  The EDGAR .txt files contain U+00A0 (NBSP) **and** U+202F (narrow NBSP),
  curly quotes/dashes, and are hard-wrapped with mid-sentence newlines. LLMs
  habitually "clean" all of these when quoting (collapse whitespace, ASCII-ize
  quotes), so a naive indexOf MISSES real spans. We instead build, from the
  agent's span_text, a regex where every run of whitespace matches `\\s+` and
  every quote/dash matches its ASCII+curly variants, then search the ORIGINAL
  contract. The matched substring is the ORIGINAL .txt text, so the offset
  invariant `contract_text[char_start:char_end] == text` holds by construction
  (verified again through `scripts.annotate._coerce_span`). Mirrors the
  no-fabrication policy of `scripts.eval_cuad_spans._parse_live_spans`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.schemas import CLASSIFIER_TAGS
from scripts.annotate import PrelabelSpan, _coerce_span

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "data" / "edgar" / "manifest.json"
OUT_DIR = REPO / "data" / "internal30"

SEVERITY_ORDER = {"info": 0, "watch": 1, "block": 2}


# ---------------------------------------------------------------------------
# Canonical text loading (with the manifest sha256 gate)
# ---------------------------------------------------------------------------


def load_contracts() -> dict[str, str]:
    """Return {deal_id: contract_text}, hard-failing if any sha256 drifts.

    The manifest pins `text_sha256`; a mismatch means someone re-extracted the
    contract and every offset in the gold set is now wrong. We stop rather than
    silently ground against a different file (master spec §1 invariant 1).
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for deal in manifest["deals"]:
        path = REPO / deal["text_path"]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != deal["text_sha256"]:
            raise SystemExit(
                f"sha256 mismatch for {deal['deal_id']}: {digest} != "
                f"{deal['text_sha256']} — someone re-extracted; refusing to ground."
            )
        out[deal["deal_id"]] = raw.decode("utf-8")
    return out


# ---------------------------------------------------------------------------
# The flexible grounder
# ---------------------------------------------------------------------------

def _char_pattern(ch: str) -> str:
    """Regex fragment matching a single agent-quoted char against the .txt."""
    if ch in "‘’'":
        return "['‘’]"
    if ch in "“”\"":
        return "[\"“”]"
    if ch in "–—-":
        return "[-–—]"
    return re.escape(ch)


def _span_regex(span_text: str) -> re.Pattern[str] | None:
    """Build a whitespace/quote-flexible pattern from the agent's span_text.

    Every maximal run of whitespace in the quote becomes `\\s+` (so NBSP,
    narrow-NBSP, and hard-wrap newlines in the source all match regardless of
    how the agent normalized them). Returns None for an empty/whitespace quote.
    """
    tokens = span_text.split()
    if not tokens:
        return None
    body = r"\s+".join("".join(_char_pattern(c) for c in tok) for tok in tokens)
    return re.compile(body)


def ground_span(span_text: str, contract_text: str, search_from: int = 0) -> tuple[int, int] | None:
    """Locate `span_text` verbatim in `contract_text`; return (start, end) or None.

    Uses the FIRST occurrence at/after `search_from` (the standard grounding
    choice, mirroring `_parse_live_spans`). Returns None — never a guessed
    offset — when the span cannot be located.
    """
    pattern = _span_regex(span_text)
    if pattern is None:
        return None
    match = pattern.search(contract_text, search_from)
    if match is None:
        # Retry from the top in case search_from overshot a real earlier hit.
        match = pattern.search(contract_text)
    return (match.start(), match.end()) if match else None


# ---------------------------------------------------------------------------
# clause_id derivation (deterministic, shared by both passes so kappa aligns)
# ---------------------------------------------------------------------------

_SECTION_HEAD = re.compile(r"(?m)^[ \t  ]*(\d+\.\d+(?:\([a-z0-9]+\))?)")


def derive_clause_id(contract_text: str, char_start: int, span_text: str) -> str:
    """Section number containing char_start, else a stable short hash.

    Computed identically for Pass A and Pass B from the same .txt + offset, so
    two passes that ground the same clause receive the same clause_id — which
    is what lets `scripts.annotate kappa` (keyed on
    (contract_id, clause_id, char_start)) align them.
    """
    heads = list(_SECTION_HEAD.finditer(contract_text, 0, char_start + 1))
    if heads:
        return heads[-1].group(1)
    digest = hashlib.sha1(" ".join(span_text.split()).encode("utf-8")).hexdigest()
    return f"h{digest[:10]}"


# ---------------------------------------------------------------------------
# Grounding a whole cohort pass
# ---------------------------------------------------------------------------


@dataclass
class GroundReport:
    deal_id: str
    grounded: int = 0
    dropped: int = 0
    dropped_examples: list[str] = field(default_factory=list)


def ground_pass(
    raw_by_deal: dict[str, list[dict[str, Any]]],
    contracts: dict[str, str],
) -> tuple[list[PrelabelSpan], list[GroundReport]]:
    """Ground every raw span in a pass into validated PrelabelSpan rows.

    De-dup rule: within a contract, two grounded spans collapse when they share
    (char_start, char_end, suggested_tag); the higher-confidence one wins. A
    multi-tag clause (same offsets, different tag) is preserved as distinct
    rows — master spec §3 says this is intentional and kappa de-dups on
    (clause_id, char_start) so it does not double-count.
    """
    spans: list[PrelabelSpan] = []
    reports: list[GroundReport] = []
    for deal_id, items in raw_by_deal.items():
        contract = contracts[deal_id]
        report = GroundReport(deal_id=deal_id)
        # key -> best raw row, with grounded offsets attached
        best: dict[tuple[int, int, str], tuple[float, dict[str, Any], int, int]] = {}
        for item in items:
            span_text = str(item.get("span_text", "")).strip()
            tag = item.get("suggested_tag")
            if not span_text or tag not in CLASSIFIER_TAGS:
                report.dropped += 1
                if len(report.dropped_examples) < 3:
                    report.dropped_examples.append(f"bad-shape:{span_text[:40]!r}")
                continue
            located = ground_span(span_text, contract)
            if located is None:
                report.dropped += 1
                if len(report.dropped_examples) < 3:
                    report.dropped_examples.append(span_text[:60])
                continue
            cs, ce = located
            conf = float(item.get("confidence", 0.0))
            key = (cs, ce, str(tag))
            if key not in best or conf > best[key][0]:
                best[key] = (conf, item, cs, ce)

        for (cs, ce, tag), (conf, item, _cs, _ce) in best.items():
            text = contract[cs:ce]
            clause_id = item.get("clause_id") or ""
            # Always recompute clause_id deterministically so both passes agree;
            # the agent's clause_id is advisory only.
            clause_id = derive_clause_id(contract, cs, text)
            coerced = _coerce_span(
                deal_id,
                {
                    "clause_id": clause_id,
                    "text": text,
                    "char_start": cs,
                    "char_end": ce,
                    "suggested_tag": tag,
                    "suggested_severity": item.get("suggested_severity"),
                    "confidence": conf,
                    "trigger_language": item.get("trigger_language", ""),
                    "explanation": item.get("explanation", ""),
                },
                contract,  # enforces the offset invariant
            )
            spans.append(coerced)
            report.grounded += 1
        reports.append(report)
    return spans, reports


def write_jsonl(spans: list[PrelabelSpan], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for span in spans:
            fh.write(json.dumps(span.to_argilla_record(), ensure_ascii=False))
            fh.write("\n")


# ---------------------------------------------------------------------------
# Reload grounded spans from JSONL (for align/assemble stages)
# ---------------------------------------------------------------------------


@dataclass
class GoldSpan:
    contract_id: str
    clause_id: str
    text: str
    char_start: int
    char_end: int
    tag: str
    severity: str
    confidence: float
    trigger_language: str
    explanation: str

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.contract_id, self.clause_id, self.char_start)


def load_grounded(path: Path) -> list[GoldSpan]:
    out: list[GoldSpan] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            meta = rec["metadata"]
            sugg = {s["question_name"]: s for s in rec["suggestions"]}
            span_val = sugg["span"]["value"][0]
            out.append(
                GoldSpan(
                    contract_id=meta["contract_id"],
                    clause_id=meta["clause_id"],
                    text=rec["fields"]["text"],
                    char_start=int(span_val["start"]),
                    char_end=int(span_val["end"]),
                    tag=sugg["tag"]["value"],
                    severity=sugg["severity"]["value"],
                    confidence=float(sugg["tag"].get("score", 0.0)),
                    trigger_language=meta.get("trigger_language", ""),
                    explanation=meta.get("explanation", ""),
                )
            )
    return out


# ---------------------------------------------------------------------------
# A <-> B alignment (master spec §6)
# ---------------------------------------------------------------------------


def char_jaccard(a: GoldSpan, b: GoldSpan) -> float:
    inter = max(0, min(a.char_end, b.char_end) - max(a.char_start, b.char_start))
    union = (a.char_end - a.char_start) + (b.char_end - b.char_start) - inter
    return inter / union if union > 0 else 0.0


def align_passes(
    a_spans: list[GoldSpan], b_spans: list[GoldSpan], contracts: dict[str, str]
) -> dict[str, Any]:
    """Greedy char-overlap alignment per contract, bucketed per master spec §6."""
    by_contract: dict[str, dict[str, list[GoldSpan]]] = {}
    for sp in a_spans:
        by_contract.setdefault(sp.contract_id, {"a": [], "b": []})["a"].append(sp)
    for sp in b_spans:
        by_contract.setdefault(sp.contract_id, {"a": [], "b": []})["b"].append(sp)

    items: list[dict[str, Any]] = []
    agree = tag_disagree = solo_a = solo_b = 0

    for cid, pair in by_contract.items():
        contract = contracts[cid]
        a_list = sorted(pair["a"], key=lambda s: s.char_start)
        b_list = sorted(pair["b"], key=lambda s: s.char_start)
        # Build all candidate matches (Jaccard >= 0.5), greedily consume best-first.
        cands: list[tuple[float, int, int]] = []
        for i, sa in enumerate(a_list):
            for j, sb in enumerate(b_list):
                jac = char_jaccard(sa, sb)
                if jac >= 0.5:
                    cands.append((jac, i, j))
        cands.sort(key=lambda t: (-t[0], t[1], t[2]))
        used_a: set[int] = set()
        used_b: set[int] = set()
        for jac, i, j in cands:
            if i in used_a or j in used_b:
                continue
            used_a.add(i)
            used_b.add(j)
            sa, sb = a_list[i], b_list[j]
            sev_gap = abs(SEVERITY_ORDER[sa.severity] - SEVERITY_ORDER[sb.severity])
            same_tag = sa.tag == sb.tag
            if same_tag and sev_gap <= 1:
                bucket = "agree"
                agree += 1
            else:
                bucket = "tag_disagreement"
                tag_disagree += 1
            items.append(
                _make_item(cid, contract, bucket, sa, sb, jac)
            )
        for i, sa in enumerate(a_list):
            if i not in used_a:
                solo_a += 1
                items.append(_make_item(cid, contract, "solo_a", sa, None, 0.0))
        for j, sb in enumerate(b_list):
            if j not in used_b:
                solo_b += 1
                items.append(_make_item(cid, contract, "solo_b", None, sb, 0.0))

    return {
        "counts": {
            "agree": agree,
            "tag_disagreement": tag_disagree,
            "solo_a": solo_a,
            "solo_b": solo_b,
            "total": len(items),
        },
        "items": items,
    }


def _context(contract: str, start: int, end: int, pad: int = 200) -> str:
    return contract[max(0, start - pad) : min(len(contract), end + pad)]


def _span_payload(sp: GoldSpan | None) -> dict[str, Any] | None:
    if sp is None:
        return None
    return {
        "clause_id": sp.clause_id,
        "char_start": sp.char_start,
        "char_end": sp.char_end,
        "text": sp.text,
        "tag": sp.tag,
        "severity": sp.severity,
        "confidence": round(sp.confidence, 3),
        "trigger_language": sp.trigger_language,
        "explanation": sp.explanation,
    }


_ITEM_SEQ = {"n": 0}


def _make_item(
    cid: str,
    contract: str,
    bucket: str,
    sa: GoldSpan | None,
    sb: GoldSpan | None,
    jaccard: float,
) -> dict[str, Any]:
    _ITEM_SEQ["n"] += 1
    anchor = sa or sb
    assert anchor is not None
    return {
        "item_id": f"{cid}#{_ITEM_SEQ['n']:04d}",
        "contract_id": cid,
        "bucket": bucket,
        "jaccard": round(jaccard, 3),
        "char_start": anchor.char_start,
        "char_end": anchor.char_end,
        "context": _context(contract, anchor.char_start, anchor.char_end),
        "pass_a": _span_payload(sa),
        "pass_b": _span_payload(sb),
    }


# ---------------------------------------------------------------------------
# Assemble reconciled gold + human review packet (master spec §6)
# ---------------------------------------------------------------------------


def assemble(
    alignment: dict[str, Any],
    adjudications: dict[str, dict[str, Any]],
    contracts: dict[str, str],
) -> tuple[list[dict[str, Any]], str]:
    """Fold adjudication recommendations into the reconciled gold + packet.

    `adjudications` maps item_id -> {decision, recommended_tag,
    recommended_severity, rationale, confidence}. AGREE items need no
    adjudication; they go straight to gold. Disagreement/solo items carry the
    adjudicator's recommended resolution and an `agreement` marker.
    """
    items = alignment["items"]
    by_id = {it["item_id"]: it for it in items}
    gold: list[dict[str, Any]] = []

    # ----- reconciled_gold.jsonl -----
    for it in items:
        adj = adjudications.get(it["item_id"], {})
        a, b = it["pass_a"], it["pass_b"]
        if it["bucket"] == "agree":
            base = a or b
            gold.append(
                _gold_row(it, base, base["tag"], base["severity"], "agree", base["confidence"])
            )
            continue
        decision = adj.get("decision", "needs_human")
        if decision == "accept_a" and a:
            src, marker = a, "resolved_A"
        elif decision == "accept_b" and b:
            src, marker = b, "resolved_B"
        elif decision == "accept" and (a or b):  # solo accepted
            src, marker = (a or b), ("resolved_A" if a else "resolved_B")
        elif decision == "reject":
            continue  # adjudicator says neither pass is right; nothing to gold
        else:
            src, marker = (a or b), "needs_human"
        tag = adj.get("recommended_tag") or src["tag"]
        sev = adj.get("recommended_severity") or src["severity"]
        gold.append(_gold_row(it, src, tag, sev, marker, src["confidence"]))

    packet = _build_packet(items, adjudications, contracts)
    return gold, packet


def _gold_row(
    it: dict[str, Any],
    src: dict[str, Any],
    tag: str,
    severity: str,
    agreement: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "contract_id": it["contract_id"],
        "clause_id": src["clause_id"],
        "char_start": src["char_start"],
        "char_end": src["char_end"],
        "text": src["text"],
        "tag": tag,
        "severity": severity,
        "confidence": round(float(confidence), 3),
        "agreement": agreement,
        "trigger_language": src.get("trigger_language", ""),
        "explanation": src.get("explanation", ""),
        "item_id": it["item_id"],
    }


def _build_packet(
    items: list[dict[str, Any]],
    adjudications: dict[str, dict[str, Any]],
    contracts: dict[str, str],
) -> str:
    by_contract: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_contract.setdefault(it["contract_id"], []).append(it)

    lines: list[str] = []
    lines.append("# Internal-30 — Human Review Packet")
    lines.append("")
    lines.append(
        "> Generated by `scripts/build_internal30_gold.py` from two independent "
        "automated annotation passes (A=recall-first, B=precision-first) "
        "adjudicated by a third cohort. **You are the annotator of record** — "
        "the agents only pre-labeled. For each contract: answer the §A decision "
        "cards, skim §B, sample §C. Target ~5–15 min/contract."
    )
    lines.append("")
    # Global summary
    total = len(items)
    n_cards = sum(
        1
        for it in items
        if it["bucket"] in ("tag_disagreement", "solo_a", "solo_b")
        and _needs_full_card(it, adjudications.get(it["item_id"], {}))
    )
    lines.append(
        f"**{len(by_contract)} contracts · {total} aligned spans · "
        f"{n_cards} full decision cards** (the rest are confidently pre-resolved "
        "and only need a skim)."
    )
    lines.append("")

    for cid in sorted(by_contract):
        c_items = by_contract[cid]
        decision_items = [
            it
            for it in c_items
            if it["bucket"] in ("tag_disagreement", "solo_a", "solo_b")
        ]
        full_cards = [
            it for it in decision_items
            if _needs_full_card(it, adjudications.get(it["item_id"], {}))
        ]
        accepted_solos = [it for it in decision_items if it not in full_cards]
        low_conf_agrees = [
            it
            for it in c_items
            if it["bucket"] == "agree" and _mean_conf(it) < 0.7
        ]
        high_conf_agrees = [
            it
            for it in c_items
            if it["bucket"] == "agree" and _mean_conf(it) >= 0.7
        ]
        lines.append(f"\n---\n\n## {cid}")
        lines.append(
            f"_{len(full_cards)} decisions · {len(accepted_solos)} pre-resolved solos · "
            f"{len(low_conf_agrees)} low-conf agrees · {len(high_conf_agrees)} high-conf agrees_"
        )
        if len(full_cards) >= 12:
            lines.append(
                f"\n> ⚠️ {len(full_cards)} genuine decisions — this contract is "
                "genuinely ambiguous and deserves the extra time."
            )

        # §A decisions
        lines.append("\n### §A — Decisions needed")
        if not full_cards:
            lines.append("\n_None — every disagreement was confidently auto-resolved._")
        for it in full_cards:
            lines.append(_decision_card(it, adjudications.get(it["item_id"], {})))

        # §A.2 confidently-accepted solo spans (skim, not full cards)
        lines.append("\n### §A.2 — Adjudicator-accepted solo spans (skim → gold)")
        if not accepted_solos:
            lines.append("\n_None._")
        for it in accepted_solos:
            adj = adjudications.get(it["item_id"], {})
            src = it["pass_a"] or it["pass_b"]
            which = "A" if it["pass_a"] else "B"
            rtag = adj.get("recommended_tag") or src["tag"]
            rsev = adj.get("recommended_severity") or src["severity"]
            lines.append(
                f"- (solo-{which}, adj {adj.get('confidence','?')}) "
                f"`{rtag}`/{rsev} §{src['clause_id']} [{it['char_start']}:{it['char_end']}] — "
                f"{_oneline(src['text'])}"
            )

        # §B low-confidence agrees
        lines.append("\n### §B — Low-confidence agrees (skim)")
        if not low_conf_agrees:
            lines.append("\n_None._")
        for it in low_conf_agrees:
            src = it["pass_a"] or it["pass_b"]
            lines.append(
                f"- `{src['tag']}`/{src['severity']} "
                f"(conf {_mean_conf(it):.2f}) [{it['char_start']}:{it['char_end']}] "
                f"§{src['clause_id']} — {_oneline(src['text'])}"
            )

        # §C high-confidence agrees (collapsed + explicit sample)
        sample_n = min(5, len(high_conf_agrees))
        lines.append("\n### §C — High-confidence agrees (collapsed)")
        lines.append(
            f"\n{len(high_conf_agrees)} spans where both passes agree at high "
            f"confidence. **Spot-check {sample_n} of {len(high_conf_agrees)}** "
            "rather than reading all; they are pre-trusted into gold."
        )
        for it in high_conf_agrees[:sample_n]:
            src = it["pass_a"] or it["pass_b"]
            lines.append(
                f"- (sample) `{src['tag']}`/{src['severity']} "
                f"§{src['clause_id']} [{it['char_start']}:{it['char_end']}] — "
                f"{_oneline(src['text'])}"
            )
    return "\n".join(lines) + "\n"


def _needs_full_card(it: dict[str, Any], adj: dict[str, Any]) -> bool:
    """A genuine decision needing the human's full attention.

    Full cards: tag/severity disagreements, anything the adjudicator left as
    needs_human or recommended to reject (the human must confirm the drop), and
    any solo the adjudicator only weakly accepted (confidence < 0.7). A solo the
    adjudicator confidently accepted is a skim line, not a decision (§A.2).
    """
    if it["bucket"] == "tag_disagreement":
        return True
    if not adj:
        return True
    if adj.get("decision") in ("needs_human", "reject"):
        return True
    return float(adj.get("confidence", 0.0)) < 0.7


def _mean_conf(it: dict[str, Any]) -> float:
    vals = [s["confidence"] for s in (it["pass_a"], it["pass_b"]) if s]
    return sum(vals) / len(vals) if vals else 0.0


def _oneline(text: str, n: int = 140) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= n else flat[: n - 1] + "…"


def _decision_card(it: dict[str, Any], adj: dict[str, Any]) -> str:
    a, b = it["pass_a"], it["pass_b"]
    rec = adj.get("decision", "needs_human")
    out = [f"\n**{it['item_id']}** · _{it['bucket']}_ · §{(a or b)['clause_id']} "
           f"[{it['char_start']}:{it['char_end']}]"]
    out.append("")
    out.append("> " + _oneline(it["context"], 360))
    out.append("")
    if a:
        out.append(f"- **A** → `{a['tag']}`/{a['severity']} (conf {a['confidence']}): {a['explanation']}")
    else:
        out.append("- **A** → _(no span)_")
    if b:
        out.append(f"- **B** → `{b['tag']}`/{b['severity']} (conf {b['confidence']}): {b['explanation']}")
    else:
        out.append("- **B** → _(no span)_")
    rationale = adj.get("rationale", "")
    rtag = adj.get("recommended_tag", "")
    rsev = adj.get("recommended_severity", "")
    out.append(
        f"- **Adjudicator** → `{rec}`"
        + (f" → `{rtag}`/{rsev}" if rtag else "")
        + (f" (conf {adj['confidence']})" if "confidence" in adj else "")
        + (f": {rationale}" if rationale else "")
    )
    out.append("- **Your call:** ☐ A  ☐ B  ☐ neither  ☐ edit ______")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_ground(args: argparse.Namespace) -> int:
    contracts = load_contracts()
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    summary: dict[str, Any] = {}
    for pass_key, out_path in (("passA", OUT_DIR / "prelabels.jsonl"),
                               ("passB", OUT_DIR / "prelabels_b.jsonl")):
        raw_by_deal = raw.get(pass_key, {})
        spans, reports = ground_pass(raw_by_deal, contracts)
        write_jsonl(spans, out_path)
        summary[pass_key] = {
            "n_spans": len(spans),
            "per_contract": {
                r.deal_id: {"grounded": r.grounded, "dropped": r.dropped}
                for r in reports
            },
            "total_dropped": sum(r.dropped for r in reports),
            "drop_examples": {
                r.deal_id: r.dropped_examples for r in reports if r.dropped_examples
            },
        }
        print(f"{pass_key}: wrote {len(spans)} spans to {out_path} "
              f"(dropped {summary[pass_key]['total_dropped']} ungrounded)")
    (OUT_DIR / "ground_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return 0


def _cmd_align(args: argparse.Namespace) -> int:
    contracts = load_contracts()
    a = load_grounded(OUT_DIR / "prelabels.jsonl")
    b = load_grounded(OUT_DIR / "prelabels_b.jsonl")
    alignment = align_passes(a, b, contracts)
    Path(args.out).write_text(
        json.dumps(alignment, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"alignment: {alignment['counts']} -> {args.out}")
    return 0


def _cmd_adjcards(args: argparse.Namespace) -> int:
    """alignment.json -> per-contract decision cards for the adjudication cohort.

    Only tag_disagreement / solo_a / solo_b items need adjudication; AGREE
    spans go straight to gold. We trim the context to keep the payload lean.
    """
    alignment = json.loads(Path(args.alignment).read_text(encoding="utf-8"))
    by_contract: dict[str, list[dict[str, Any]]] = {}
    for it in alignment["items"]:
        if it["bucket"] not in ("tag_disagreement", "solo_a", "solo_b"):
            continue
        card = {
            "item_id": it["item_id"],
            "bucket": it["bucket"],
            "context": _oneline(it["context"], 700),
            "pass_a": _trim_for_card(it["pass_a"]),
            "pass_b": _trim_for_card(it["pass_b"]),
        }
        by_contract.setdefault(it["contract_id"], []).append(card)
    # Write one card file per contract so each adjudicator agent Reads only
    # its own slice (keeps the workflow args tiny — agents have file access).
    cards_dir = OUT_DIR / "adj_cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for cid, items in sorted(by_contract.items()):
        path = cards_dir / f"{cid}.json"
        path.write_text(
            json.dumps({"contract_id": cid, "items": items}, indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
        index.append({
            "contract_id": cid,
            "cards_path": str(path.relative_to(REPO)),
            "n_items": len(items),
        })
    Path(args.out).write_text(
        json.dumps({"contracts": index}, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    n_items = sum(c["n_items"] for c in index)
    print(f"adjcards: {n_items} decision cards across {len(index)} contracts; "
          f"per-contract files in {cards_dir} ; index -> {args.out}")
    return 0


def _trim_for_card(sp: dict[str, Any] | None) -> dict[str, Any] | None:
    if sp is None:
        return None
    return {
        "tag": sp["tag"],
        "severity": sp["severity"],
        "confidence": sp["confidence"],
        "text": _oneline(sp["text"], 300),
        "explanation": sp["explanation"],
    }


def _cmd_assemble(args: argparse.Namespace) -> int:
    contracts = load_contracts()
    alignment = json.loads(Path(args.alignment).read_text(encoding="utf-8"))
    adj_raw = json.loads(Path(args.adjudications).read_text(encoding="utf-8"))
    # adj_raw may be {"adjudications": [ {item_id, ...} ]} or a dict by id.
    if isinstance(adj_raw, dict) and "adjudications" in adj_raw:
        adj = {a["item_id"]: a for a in adj_raw["adjudications"]}
    elif isinstance(adj_raw, list):
        adj = {a["item_id"]: a for a in adj_raw}
    else:
        adj = adj_raw
    gold, packet = assemble(alignment, adj, contracts)
    gold_path = OUT_DIR / "reconciled_gold.jsonl"
    with gold_path.open("w", encoding="utf-8") as fh:
        for row in gold:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    packet_path = OUT_DIR / "human_review_packet.md"
    packet_path.write_text(packet, encoding="utf-8")
    print(f"assemble: {len(gold)} gold rows -> {gold_path}")
    print(f"assemble: packet -> {packet_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("ground", help="raw cohort JSON -> prelabels[_b].jsonl")
    g.add_argument("--raw", required=True)
    g.set_defaults(fn=_cmd_ground)
    al = sub.add_parser("align", help="prelabels[_b].jsonl -> alignment.json")
    al.add_argument("--out", default=str(OUT_DIR / "alignment.json"))
    al.set_defaults(fn=_cmd_align)
    ac = sub.add_parser("adjcards", help="alignment.json -> adjudication cohort input")
    ac.add_argument("--alignment", default=str(OUT_DIR / "alignment.json"))
    ac.add_argument("--out", default=str(OUT_DIR / "adj_cards.json"))
    ac.set_defaults(fn=_cmd_adjcards)
    asm = sub.add_parser("assemble", help="alignment + adjudications -> gold + packet")
    asm.add_argument("--alignment", default=str(OUT_DIR / "alignment.json"))
    asm.add_argument("--adjudications", required=True)
    asm.set_defaults(fn=_cmd_assemble)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
