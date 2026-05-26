"""LLM-assisted annotation pipeline for the Internal-30 gold set.

Plan §5.2 — Gemini pre-labels spans; the human adjudicates. The output is
Argilla-compatible JSONL that drops straight into an Argilla `SpanQuestion`
dataset on a Hugging Face Space.

Usage:
  # Single-pass pre-labeling (deterministic, temperature=0):
  python -m scripts.annotate prelabel \\
      --input data/edgar/ \\
      --output data/internal30/prelabels.jsonl

  # Independent second pass on the same 10-contract subset for kappa.
  # Uses a non-zero temperature + an integer seed so the B-pass actually
  # diverges from the A-pass — kappa on two temperature=0 runs of the
  # same prompt is meaningless.
  python -m scripts.annotate prelabel \\
      --input data/edgar/ --limit 10 --seed 7 --temperature 0.7 \\
      --output data/internal30/prelabels_b.jsonl

  # Cohen's kappa between two annotation files (matched by
  # (contract_id, clause_id, char_start) to avoid collapsing multiple
  # spans within a single clause):
  python -m scripts.annotate kappa \\
      data/internal30/prelabels.jsonl data/internal30/prelabels_b.jsonl

  # NOTE: --limit picks the first N contracts in *sorted* filename order
  # (not random). Use a deliberate file-naming scheme if you need a
  # representative subset.

HANDOFF D5-D9 — this pipeline turns a 60h hand-annotation budget into the
15-25h adjudication budget plan §5.2 assumes.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, Callable, Protocol

from agent.schemas import CLASSIFIER_TAGS, Severity, Tag

_LOG = logging.getLogger(__name__)

# Derived from `agent.schemas.CLASSIFIER_TAGS`. "none" is omitted because
# we only emit a record when a candidate clause is found; "no clause
# here" is encoded as an empty list per contract. See README "Tag sync
# points" — the previous hand-replicated tuple is exactly what Issue 6
# eliminated.
PRELABEL_TAGS: tuple[Tag, ...] = CLASSIFIER_TAGS


@dataclasses.dataclass(frozen=True)
class PrelabelSpan:
    """One pre-labeled span emitted by the LLM, awaiting human adjudication."""

    contract_id: str
    clause_id: str
    text: str
    char_start: int
    char_end: int
    suggested_tag: Tag
    suggested_severity: Severity
    confidence: float
    trigger_language: str
    explanation: str

    def to_argilla_record(self) -> dict[str, Any]:
        """Argilla SpanQuestion-compatible JSONL record.

        Schema reference: https://docs.argilla.io/latest/how_to_guides/dataset/
        — `fields` holds the visible text, `suggestions` populates the
        annotator's pre-filled answer, `metadata` carries non-editable
        provenance so adjudicators can audit the LLM's reasoning.

        SpanQuestion suggestions carry a `field` reference identifying
        which field the offsets index into — Argilla 2.x silently fails
        to render the highlight if this is missing. Smoke-test one
        record in a live Argilla Space before the 30-contract burn.
        """
        return {
            "fields": {"text": self.text},
            "suggestions": [
                {
                    "question_name": "tag",
                    "value": self.suggested_tag,
                    "score": self.confidence,
                    "agent": "gemini-3-pro",
                },
                {
                    "question_name": "severity",
                    "value": self.suggested_severity,
                    "score": self.confidence,
                    "agent": "gemini-3-pro",
                },
                {
                    "question_name": "span",
                    "field": "text",
                    "value": [
                        {
                            "start": self.char_start,
                            "end": self.char_end,
                            "label": self.suggested_tag,
                        }
                    ],
                    "agent": "gemini-3-pro",
                },
            ],
            "metadata": {
                "contract_id": self.contract_id,
                "clause_id": self.clause_id,
                "trigger_language": self.trigger_language,
                "explanation": self.explanation,
            },
        }


class _LabelerFn(Protocol):
    """Pluggable LLM call — concrete impl is gemini_prelabel below.

    The Protocol lets unit tests pass a deterministic stub so the rest of
    the pipeline can be exercised without network access.
    """

    def __call__(self, contract_id: str, contract_text: str) -> list[PrelabelSpan]: ...


# ---------------------------------------------------------------------------
# Gemini pre-labeling
# ---------------------------------------------------------------------------

# PRELABEL_INSTRUCTION is built once at import-time from PRELABEL_TAGS
# so adding a new clause family to schemas.Tag automatically appears
# in the LLM's instructions — no silent recall hole from a stale prose
# enumeration. See README "Tag sync points".
_PRELABEL_TAG_LIST = ", ".join(PRELABEL_TAGS)
_PRELABEL_TAG_COUNT = len(PRELABEL_TAGS)
PRELABEL_INSTRUCTION = f"""You are an M&A contract pre-labeler. The output of
this step is reviewed by a human adjudicator — you should err on the side
of HIGH RECALL (over-tagging is cheaper to fix than under-tagging in this
pipeline).

Identify every span in the contract that plausibly matches one of these
{_PRELABEL_TAG_COUNT} tags:

  {_PRELABEL_TAG_LIST}

For each span, emit a JSON object with:

  {{
    "clause_id": "string — derive from section number if visible, else a stable hash",
    "text": "verbatim span text (do NOT paraphrase)",
    "char_start": int,
    "char_end": int,
    "suggested_tag": "<one of the {_PRELABEL_TAG_COUNT} tags above>",
    "suggested_severity": "info|watch|block",
    "confidence": float in [0,1],
    "trigger_language": "the literal phrase that triggered the tag",
    "explanation": "one sentence — why this span matches the tag"
  }}

Severity guidance:
- "block" — bare CoC trigger with no consent, MAC with narrow carve-outs,
  single-trigger acceleration, blanket anti-assignment.
- "watch" — qualified or carve-out-protected versions of the above.
- "info" — boilerplate references (definitions sections, recitals).

Return ONLY a JSON array of these objects. No prose, no markdown fences."""


def make_gemini_labeler(
    *, temperature: float = 0.0, seed: int | None = None
) -> _LabelerFn:
    """Build a Gemini-3-Pro labeler closure with the given sampling params.

    Two-pass kappa workflow: pass A uses temperature=0 (deterministic);
    pass B uses temperature>0 + a fixed seed so the run actually diverges
    and the kappa number reflects real annotator disagreement instead of
    determinism. `temperature=0.0, seed=None` matches the default used
    by `prelabel_corpus(..., labeler=gemini_prelabel)`.
    """
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore

    client = genai.Client()

    def _label(contract_id: str, contract_text: str) -> list[PrelabelSpan]:
        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "response_mime_type": "application/json",
        }
        if seed is not None:
            config_kwargs["seed"] = seed
        response = client.models.generate_content(
            model="gemini-3-pro",
            contents=[
                types.Part.from_text(text=PRELABEL_INSTRUCTION),
                types.Part.from_text(
                    text=f"<contract id={contract_id}>\n{contract_text}\n</contract>"
                ),
            ],
            config=types.GenerateContentConfig(**config_kwargs),
        )
        raw_items = json.loads(response.text)
        return [_coerce_span(contract_id, item, contract_text) for item in raw_items]

    return _label


def gemini_prelabel(contract_id: str, contract_text: str) -> list[PrelabelSpan]:
    """Default deterministic labeler (temperature=0, no seed).

    Imported lazily inside `make_gemini_labeler` so the rest of the module
    stays testable without `google.genai` installed."""
    return make_gemini_labeler()(contract_id, contract_text)


def _coerce_span(
    contract_id: str, item: dict[str, Any], contract_text: str | None = None
) -> PrelabelSpan:
    """Validate a raw LLM dict into a PrelabelSpan; raise on bad shape.

    Defensive against the LLM returning out-of-vocabulary tags or
    severities — we hard-fail rather than silently coerce, because a
    silently-coerced label corrupts the gold set.

    When `contract_text` is provided, enforce the char-offset invariant
    `contract_text[char_start:char_end] == text`. An LLM that returns
    offsets relative to a stripped/normalized version of the contract
    will produce Argilla spans pointing at the wrong tokens; the human
    adjudicator will then "correct" against the wrong substring,
    silently corrupting the gold set.
    """
    tag = item["suggested_tag"]
    if tag not in PRELABEL_TAGS:
        raise ValueError(f"out-of-vocab tag {tag!r} for contract {contract_id}")
    severity = item["suggested_severity"]
    if severity not in ("info", "watch", "block"):
        raise ValueError(f"out-of-vocab severity {severity!r} for contract {contract_id}")
    char_start = int(item["char_start"])
    char_end = int(item["char_end"])
    text = str(item["text"])
    if contract_text is not None:
        slice_ = contract_text[char_start:char_end]
        if slice_ != text:
            raise ValueError(
                f"char-offset invariant violated for {contract_id}/{item.get('clause_id')!r}: "
                f"contract_text[{char_start}:{char_end}]={slice_!r} != text={text!r}"
            )
    return PrelabelSpan(
        contract_id=contract_id,
        clause_id=str(item["clause_id"]),
        text=text,
        char_start=char_start,
        char_end=char_end,
        suggested_tag=tag,
        suggested_severity=severity,
        confidence=float(item["confidence"]),
        trigger_language=str(item.get("trigger_language", "")),
        explanation=str(item.get("explanation", "")),
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def iter_contracts(input_dir: Path) -> Iterator[tuple[str, str]]:
    """Yield (contract_id, text) for every contract file under input_dir.

    Accepts `.txt` (Gemini-pre-extracted) and `.md`. PDFs are out of scope
    here — the live Parser agent handles those at runtime; for annotation
    we work off pre-extracted text so the human adjudicator can read along.
    """
    for path in sorted(input_dir.rglob("*")):
        if path.suffix.lower() in {".txt", ".md"}:
            # Strict decoding: silent character substitution in legal text
            # changes meaning. Let encoding errors surface at ingest time.
            yield path.stem, path.read_text(encoding="utf-8", errors="strict")


@dataclasses.dataclass(frozen=True)
class PrelabelSummary:
    """Per-run manifest. The CLI prints this; an exit code is derived from
    `failed_contracts` so a partial run does not silently pass."""

    n_spans: int
    ok_contracts: tuple[str, ...]
    failed_contracts: tuple[str, ...]
    empty_contracts: tuple[str, ...]


def prelabel_corpus(
    input_dir: Path,
    output_path: Path,
    labeler: _LabelerFn = gemini_prelabel,
    limit: int | None = None,
) -> PrelabelSummary:
    """Pre-label every contract under input_dir, writing one JSONL record per
    span. Returns a summary of which contracts succeeded / failed / emitted
    zero spans.

    Failure semantics: a labeler-level exception (network / API / coerce)
    marks the whole contract failed and is surfaced in the summary —
    silent contract loss in a 15-25h adjudication budget is the
    expensive failure mode this manifest guards against.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_spans = 0
    ok: list[str] = []
    failed: list[str] = []
    empty: list[str] = []
    with output_path.open("w", encoding="utf-8") as fh:
        for i, (contract_id, text) in enumerate(iter_contracts(input_dir)):
            if limit is not None and i >= limit:
                break
            _LOG.info("pre-labeling %s", contract_id)
            try:
                spans = labeler(contract_id, text)
            except Exception:
                _LOG.exception("labeler failed for %s", contract_id)
                failed.append(contract_id)
                continue
            if not spans:
                empty.append(contract_id)
            else:
                ok.append(contract_id)
            for span in spans:
                fh.write(json.dumps(span.to_argilla_record(), ensure_ascii=False))
                fh.write("\n")
                n_spans += 1
    summary = PrelabelSummary(
        n_spans=n_spans,
        ok_contracts=tuple(ok),
        failed_contracts=tuple(failed),
        empty_contracts=tuple(empty),
    )
    _LOG.info(
        "wrote %d spans to %s (ok=%d failed=%d empty=%d)",
        n_spans,
        output_path,
        len(ok),
        len(failed),
        len(empty),
    )
    return summary


# ---------------------------------------------------------------------------
# Cohen's kappa across two annotation files
# ---------------------------------------------------------------------------


def _load_clause_tags(path: Path) -> dict[tuple[str, str, int], str]:
    """Read an annotation JSONL and return {(contract_id, clause_id, char_start): tag}.

    Keying on `char_start` keeps multiple spans within the same clause
    distinct — collapsing them would silently drop disagreements between
    annotators and inflate kappa. Accepts both our pre-label JSONL
    (Argilla SpanQuestion shape) and a flat post-adjudication shape
    where each record is {contract_id, clause_id, char_start, tag}.
    """
    out: dict[tuple[str, str, int], str] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "metadata" in rec:
                cid = rec["metadata"]["contract_id"]
                clid = rec["metadata"]["clause_id"]
                tag = _extract_tag(rec)
                char_start = _extract_char_start(rec)
            else:
                cid = rec["contract_id"]
                clid = rec["clause_id"]
                tag = rec["tag"]
                char_start = int(rec.get("char_start", 0))
            out[(cid, clid, char_start)] = tag
    return out


def _extract_char_start(rec: dict[str, Any]) -> int:
    """Pull the first span's char_start out of an Argilla-shape record."""
    for suggestion in rec.get("suggestions", []):
        if suggestion.get("question_name") == "span":
            values = suggestion.get("value", [])
            if values:
                return int(values[0]["start"])
    return 0


def _extract_tag(rec: dict[str, Any]) -> str:
    """Prefer adjudicated `responses` over `suggestions` (the human wins)."""
    for response in rec.get("responses", []):
        if response.get("question_name") == "tag":
            return response["value"]
    for suggestion in rec.get("suggestions", []):
        if suggestion.get("question_name") == "tag":
            return suggestion["value"]
    raise ValueError(f"no tag in record: {rec!r}")


def cohen_kappa(file_a: Path, file_b: Path) -> float:
    """Cohen's kappa between two annotation files on the intersection of
    their (contract_id, clause_id) keys.

    Plan §5.2: a 10-contract double-annotated subset for kappa reporting.
    Computed by hand (no sklearn dep) — the formula is small and the
    dependency surface stays minimal."""
    tags_a = _load_clause_tags(file_a)
    tags_b = _load_clause_tags(file_b)
    keys = sorted(set(tags_a) & set(tags_b))
    if not keys:
        raise ValueError(f"no overlapping clause_ids between {file_a} and {file_b}")
    pairs = [(tags_a[k], tags_b[k]) for k in keys]
    return _kappa_from_pairs(pairs)


def _kappa_from_pairs(pairs: Iterable[tuple[str, str]]) -> float:
    """Cohen's kappa from a list of (annotator_a, annotator_b) label tuples.

    kappa = (po - pe) / (1 - pe), where po is observed agreement and pe is
    expected agreement under independence of the marginals.
    """
    pairs = list(pairs)
    n = len(pairs)
    if n == 0:
        raise ValueError("empty pairs")
    labels = sorted({label for pair in pairs for label in pair})
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    pe = 0.0
    for label in labels:
        p_a = sum(1 for a, _ in pairs if a == label) / n
        p_b = sum(1 for _, b in pairs if b == label) / n
        pe += p_a * p_b
    if pe >= 1.0:
        # Degenerate: both annotators put everything in one bucket. By
        # convention we return 1.0 if they agree, 0.0 otherwise (sklearn
        # raises a warning + returns NaN here; we prefer a defined value
        # so downstream code doesn't NaN-propagate).
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pre = sub.add_parser("prelabel", help="LLM pre-labeling pass")
    p_pre.add_argument("--input", type=Path, required=True)
    p_pre.add_argument("--output", type=Path, required=True)
    p_pre.add_argument("--limit", type=int, default=None)
    p_pre.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Gemini sampling seed (only meaningful with --temperature>0).",
    )
    p_pre.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Gemini sampling temperature. Use >0 for the B-pass of the kappa workflow.",
    )

    p_kappa = sub.add_parser("kappa", help="Cohen's kappa between two annotation files")
    p_kappa.add_argument("file_a", type=Path)
    p_kappa.add_argument("file_b", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_parser().parse_args(argv)
    if args.cmd == "prelabel":
        labeler = make_gemini_labeler(temperature=args.temperature, seed=args.seed)
        summary = prelabel_corpus(args.input, args.output, labeler=labeler, limit=args.limit)
        print(
            f"wrote {summary.n_spans} pre-labeled spans to {args.output}\n"
            f"  ok      : {len(summary.ok_contracts)}\n"
            f"  empty   : {len(summary.empty_contracts)} {list(summary.empty_contracts)}\n"
            f"  failed  : {len(summary.failed_contracts)} {list(summary.failed_contracts)}"
        )
        # Non-zero exit if any contract failed — silent contract loss is
        # the failure mode this manifest+exit-code combination prevents.
        return 1 if summary.failed_contracts else 0
    if args.cmd == "kappa":
        k = cohen_kappa(args.file_a, args.file_b)
        print(f"Cohen's kappa: {k:.4f}")
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
