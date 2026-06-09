"""README results-table generator (plan §5.2, §12; HANDOFF L308).

Produces the canonical three-track results table — **Internal-30**,
**MAUD-MCQ**, **CUAD-Spans** — from the JSON artifacts written by
`scripts/calibrate.py`, `scripts/eval_maud_mcq.py`, and
`scripts/eval_cuad_spans.py`.

Design commitments (per plan §5.2 + PROJECT_LOG L89–96):
  * Each track is reported with its OWN metric. MCQ accuracy and CUAD
    token-F1 are NEVER averaged into a single "score".
  * The cluster bootstrap 95% LB (one-sided) on Internal-30 Block-recall
    is the load-bearing headline number and is published unmodified,
    even if below 0.95 (plan §0 + §5.4 v3). It treats CONTRACTS as the
    IID unit; the Wilson row remains as an exploratory per-finding-IID
    cross-check (over-tight as a cluster-corrected estimate).
  * `aupr_degenerate` on MAUD ALWAYS carries the "degenerate (single
    confidence, not per-choice probs)" caveat in the Notes column so a
    reader does not mistake it for the paper's full AUPR.
  * P@R rows surface their `flag` (e.g. FALLBACK_TO_MAX) so a fallback
    number is never silently reported as if it were achieved.
  * Dropped headline folds (calibration could not hit Block-recall=1.0)
    are surfaced as their own row — NEVER hidden.

CLI:
    python -m scripts.build_readme_table \
        --calibrate path/to/thresholds.json \
        --maud path/to/maud_mcq_eval.json \
        --cuad path/to/cuad_spans_eval.json \
        [--out path.md] \
        [--update-readme path/to/README.md]

All three input paths are optional. A missing path renders a
"Not yet available" row so partial runs are still valid intermediate
artifacts (per plan §7).
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Iterable

_LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — markers + caveats
# ---------------------------------------------------------------------------

BEGIN_MARKER = "<!-- BEGIN_RESULTS_TABLE -->"
END_MARKER = "<!-- END_RESULTS_TABLE -->"

# Forced caveat applied to MAUD `aupr_degenerate` rows. Sourced from
# `scripts/eval_maud_mcq.py` module docstring + plan §5.2.
DEGENERATE_CAVEAT = "degenerate (single confidence, not per-choice probs)"

# Pre-commitment paragraph (verbatim phrasing from `README.md` cluster-bootstrap headline row
# + plan §5.4 v3) — appended below the table whenever the Internal-30
# row is present.
CLUSTER_BOOTSTRAP_PRECOMMIT_CAPTION = (
    "_Pre-commitment (plan §0 + §5.4 v3): the cluster-bootstrap 95% LB on "
    "Block recall is the load-bearing headline number and is published "
    "unmodified regardless of whether it clears 0.95. With ~6–10 Block "
    "findings per fold, the 95% CI for a proportion near 1.0 spans roughly "
    "±0.10–0.15; the LB clearing 0.95 is **arithmetically tight, not a "
    "guarantee**. The Wilson row is retained as an exploratory per-finding-"
    "IID cross-check only._"
)


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------


def load_track_jsons(
    *,
    calibrate_path: Path | None,
    maud_path: Path | None,
    cuad_path: Path | None,
) -> dict[str, dict[str, Any] | None]:
    """Load the three optional JSON inputs.

    A `None` value in the returned dict means "track not yet available"
    and will render as a placeholder row. Malformed JSON or a missing
    file at a provided path raises — silent-fallback there would mask a
    pipeline bug.
    """
    out: dict[str, dict[str, Any] | None] = {
        "internal30": None,
        "maud": None,
        "cuad": None,
    }
    if calibrate_path is not None:
        out["internal30"] = _load_one(calibrate_path, "calibrate")
    if maud_path is not None:
        out["maud"] = _load_one(maud_path, "maud")
    if cuad_path is not None:
        out["cuad"] = _load_one(cuad_path, "cuad")
    return out


def _load_one(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"--{label} path does not exist: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"--{label} JSON is malformed at {path}: {exc.msg} "
            f"(line {exc.lineno} col {exc.colno})"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"--{label} JSON at {path} must be an object at the top level, "
            f"got {type(data).__name__}"
        )
    return data


# ---------------------------------------------------------------------------
# Row builders — one per track
# ---------------------------------------------------------------------------

Row = tuple[str, str, str, str]  # (track, metric, value, notes)

_NOT_AVAILABLE = "_Not yet available_"


def _fmt3(x: Any) -> str:
    """Format a numeric to 3 decimals via f-string (no double-rounding)."""
    if x is None:
        return "—"
    try:
        return f"{float(x):.3f}"
    except (TypeError, ValueError):
        return str(x)


def _fmt_pct1(x: Any) -> str:
    """Format a fraction in [0, 1] as a 1-decimal percentage."""
    if x is None:
        return "—"
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(x)


def _build_internal30_rows(data: dict[str, Any] | None) -> list[Row]:
    track = "Internal-30"
    if data is None:
        return [(track, "Block-recall (4-fold CV)", _NOT_AVAILABLE,
                 "Run `scripts/calibrate.py` to populate.")]

    rows: list[Row] = []
    rows.append((
        track,
        "Block recall (point estimate)",
        _fmt3(data.get("point_block_recall")),
        f"Pooled across {len(data.get('headline_folds_present') or [])} "
        f"headline fold(s); frozen fold "
        f"{data.get('frozen_fold', '?')} excluded.",
    ))
    # Headline row: cluster bootstrap (cluster-correct). Comes BEFORE
    # the Wilson row so the headline is visually the load-bearing number.
    rows.append((
        track,
        "Block recall (cluster bootstrap 95% LB, one-sided)",
        _fmt3(data.get("cluster_bootstrap_one_sided_95_lb_block_recall")),
        "Load-bearing number per plan §0 + §5.4 v3 — published unmodified. "
        "Cluster bootstrap over contracts (1000 resamples) — findings "
        "within a contract are correlated, so contracts are the IID unit.",
    ))
    # Backwards-compat key fallback: the V2 gate (FIX_PLAN_NOTES) renamed
    # the Wilson key from `wilson_one_sided_95_lb_block_recall` to
    # `wilson_one_sided_95_lb_block_recall_exploratory_iid`. Read both so
    # an older thresholds.json artifact still renders cleanly for one
    # release cycle. First non-None wins.
    wilson_value = None
    for candidate in (
        "wilson_one_sided_95_lb_block_recall_exploratory_iid",
        "wilson_one_sided_95_lb_block_recall",
    ):
        v = data.get(candidate)
        if v is not None:
            wilson_value = v
            break
    rows.append((
        track,
        "Block recall (Wilson 95% LB — exploratory, per-finding IID)",
        _fmt3(wilson_value),
        "Exploratory cross-check only — assumes findings are IID Bernoulli "
        "trials, which they are not (findings within a contract are "
        "correlated). Over-tight as a cluster-corrected estimate; the "
        "cluster bootstrap row above is the headline.",
    ))
    # `dict.get(key, default)` only returns `default` when the key is
    # ABSENT — an explicit `null` in the JSON would render as the literal
    # string "None". Coerce both shapes (missing-key and explicit-null)
    # to the em-dash placeholder.
    n_contracts = data.get("effective_n_contracts")
    rows.append((
        track,
        "Effective N (contracts)",
        str(n_contracts) if n_contracts is not None else "—",
        "Per plan §5.2 v3 — fold 5 (Reflector frozen set) excluded.",
    ))

    # Deployed thresholds row — formatted defensively so a missing key
    # doesn't crash the table.
    tau_h = data.get("deployed_tau_h")
    tau_f = data.get("deployed_tau_f")
    if tau_h is not None and tau_f is not None:
        thresh_value = f"τ_h={float(tau_h):.2f}, τ_f={float(tau_f):.2f}"
    else:
        thresh_value = "—"
    rows.append((
        track,
        "Deployed thresholds",
        thresh_value,
        "Median across headline folds; written to router config.",
    ))

    # Dropped folds — NEVER hidden when non-empty.
    dropped = data.get("dropped_headline_folds") or []
    if dropped:
        rows.append((
            track,
            "Dropped folds",
            ", ".join(str(f) for f in dropped),
            "Calibration could not hit Block-recall=1.0 on these folds; "
            "disclosed per honesty-guard.",
        ))
    return rows


def _build_maud_rows(data: dict[str, Any] | None) -> list[Row]:
    track = "MAUD-MCQ"
    if data is None:
        return [(track, "Exact-match accuracy", _NOT_AVAILABLE,
                 "Run `scripts/eval_maud_mcq.py` to populate.")]

    rows: list[Row] = []
    rows.append((
        track,
        "Exact-match accuracy (macro)",
        _fmt_pct1(data.get("overall_macro_accuracy")),
        "Per-category mean (plan §5.2).",
    ))
    rows.append((
        track,
        "Exact-match accuracy (micro)",
        _fmt_pct1(data.get("overall_micro_accuracy")),
        "Pooled over all evaluated questions.",
    ))

    aupr = data.get("aupr_degenerate")
    rows.append((
        track,
        "Degenerate per-question AUPR (paper-comparable, see caveat)",
        _fmt3(aupr),
        DEGENERATE_CAVEAT,
    ))

    # Same explicit-null guard as above — `dict.get(key, "—")` would
    # let a JSON-`null` slip through as the literal string "None".
    _n_eval = data.get("n_evaluated")
    _n_total = data.get("n_total_examples")
    n_eval = str(_n_eval) if _n_eval is not None else "—"
    n_total = str(_n_total) if _n_total is not None else "—"
    rows.append((
        track,
        "N evaluated / N total",
        f"{n_eval} / {n_total}",
        "Skipped rows tallied in `n_skipped_with_reason`.",
    ))

    # Comparison baselines — surfaced ONLY if provided. Per plan §5.2
    # line 203 MAUD baselines are exact-match-accuracy comparisons (NOT
    # AUPR comparisons), so the DEGENERATE_CAVEAT belongs only on the
    # `aupr_degenerate` row above, not on every "vs X" row. Attaching
    # the AUPR caveat to an accuracy comparison would mislabel the
    # metric's nature and dilute the honesty signal by crying wolf.
    baselines = data.get("comparison_baselines")
    if baselines:  # truthy = non-null AND non-empty dict
        # Source-of-truth contract leaves the shape of
        # `comparison_baselines` open ("dict[str, Any] | None"). We
        # interpret it as {baseline_name: value-or-dict}; if the value
        # is itself a dict we render its 'value' key (or repr it),
        # otherwise we render it directly.
        # AMBIGUITY (1/1): `comparison_baselines` value-shape is open;
        # we render scalars verbatim and nested dicts by their 'value'
        # field if present, else as a compact JSON repr.
        for name, value in baselines.items():
            rendered, extra_note = _render_baseline_value(value)
            note = "Baseline as published; exact-match accuracy"
            if extra_note:
                note = f"{extra_note}; {note}"
            rows.append((track, f"vs {name}", rendered, note))
    return rows


def _render_baseline_value(value: Any) -> tuple[str, str]:
    """Render a baseline value defensively. Returns (rendered, extra_note)."""
    if isinstance(value, (int, float)):
        return _fmt3(value), ""
    if isinstance(value, dict):
        if "value" in value:
            return _fmt3(value["value"]), ""
        # Fall back to compact JSON — surface to reviewer.
        return json.dumps(value, sort_keys=True), "nested baseline shape"
    if value is None:
        return "—", ""
    return str(value), ""


def _build_cuad_rows(data: dict[str, Any] | None) -> list[Row]:
    track = "CUAD-Spans"
    if data is None:
        return [(track, "Token-F1 + P@R", _NOT_AVAILABLE,
                 "Run `scripts/eval_cuad_spans.py` to populate.")]

    rows: list[Row] = []
    rows.append((
        track,
        "Token-F1 (project, macro, strict >0.5)",
        _fmt3(data.get("macro_f1")),
        "Plan §5.2 strict-Jaccard variant; CoC + Anti-Assignment only.",
    ))
    rows.append((
        track,
        "Token-F1 (paper-comparable, macro, ≥0.5 + punct-strip)",
        _fmt3(data.get("macro_f1_paper")),
        "CUAD §3 paper variant (≥0.5 Jaccard, punctuation-stripped).",
    ))
    rows.append((
        track,
        "AUPR (overall)",
        _fmt3(data.get("aupr_overall")),
        "CUAD paper primary metric (§3).",
    ))

    # P@R rows — honesty-guard surfaces the flag explicitly.
    p08 = data.get("p_at_r_0_8") or {}
    rows.append(_p_at_r_row(track, p08, "P@R=0.8"))
    p09 = data.get("p_at_r_0_9") or {}
    rows.append(_p_at_r_row(track, p09, "P@R=0.9"))

    # Comparison baselines — plan §5.2 line 204 commits CUAD-Spans to
    # "Compared to CUAD published baselines". The eval JSON exposes
    # `comparison_baselines` (eval_cuad_spans.py L689, L704) and the
    # MAUD path renders them; mirror that here. Unlike MAUD, CUAD's
    # baseline metric is token-F1 / AUPR (CUAD §3) — NOT a degenerate-
    # AUPR construct — so DEGENERATE_CAVEAT is intentionally NOT
    # attached.
    cuad_baselines = data.get("comparison_baselines")
    if cuad_baselines:  # truthy = non-null AND non-empty dict
        for name, value in cuad_baselines.items():
            rendered, extra_note = _render_baseline_value(value)
            note = "Baseline as published; CUAD paper §3 metric"
            if extra_note:
                note = f"{extra_note}; {note}"
            rows.append((track, f"vs {name}", rendered, note))
    return rows


# The previous Round-1 implementation defined a `_P_AT_R_OK_FLAGS` set
# (with values "ACHIEVED" / "ok") which never appears anywhere in
# scripts/eval_cuad_spans.py. The REAL contract (eval_cuad_spans.py
# L107-114 + L620) is:
#   * `flag is None` → achieved (good outcome)
#   * `flag == f"recall_{target}_unachieved"` (dynamic) → fallback
# The two predicates below encode that real contract; the regex on the
# unachieved-side captures both "recall_0.8_unachieved" and
# "recall_0.9_unachieved" (and any future target).

_FLAG_UNACHIEVED_RE = re.compile(r"^recall_[0-9.]+_unachieved$")


def _flag_is_achieved(flag: Any) -> bool:
    """Return True iff `flag` represents the achieved/clean outcome.

    eval_cuad_spans.py:620 sets `flag=None` when the target recall is
    achieved. Any other value (including non-string sentinels we don't
    recognise) is NOT a clean outcome.
    """
    return flag is None


def _flag_is_unachieved(flag: Any) -> bool:
    """Return True iff `flag` represents the "target unachieved" fallback.

    eval_cuad_spans.py:107-114 emits `f"recall_{target_recall}_unachieved"`,
    so the real enum is dynamic on `target_recall`. We pattern-match the
    full family rather than hardcoding 0.8/0.9.
    """
    return isinstance(flag, str) and _FLAG_UNACHIEVED_RE.match(flag) is not None


def _p_at_r_row(track: str, payload: dict[str, Any], label: str) -> Row:
    """Build a P@R row with the `flag` surfaced in Notes."""
    # The eval JSON nests the precision number under the key
    # `p_at_r_0_8` (regardless of whether the OUTER key is 0.8 or 0.9);
    # see `_p_at_r_to_json` in scripts/eval_cuad_spans.py L708. Both
    # sub-keys are tried so a future rename doesn't silently null the row.
    value = payload.get("p_at_r_0_8")
    if value is None:
        value = payload.get("p_at_r_0_9")
    flag = payload.get("flag")
    if _flag_is_achieved(flag):
        note = "Achieved at target recall."
    elif _flag_is_unachieved(flag):
        # Honesty-guard: an unachieved P@R must visibly say so. Quote
        # the actual flag string + achieved-max-recall so a judge cannot
        # confuse a fallback number for the achieved one. The literal
        # "**FALLBACK**" token is non-negotiable per Round-2 Fix #3.
        achieved_max = payload.get("achieved_recall_max")
        achieved_part = ""
        if achieved_max is not None:
            achieved_part = (
                f" (max achieved recall = {float(achieved_max):.3f})"
            )
        note = (
            f"**FALLBACK** — flag=`{flag}`{achieved_part}. Number shown "
            "is NOT the achieved precision at target recall."
        )
    else:
        # Genuinely unknown flag — the actual "verify your eval JSON"
        # failure mode. Round-1 incorrectly raised this for the
        # achieved-case (flag=None).
        note = f"Unknown flag: {flag!r} — verify eval JSON shape."
    return (track, label, _fmt3(value), note)


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------


def render_table(
    *,
    internal30: dict[str, Any] | None,
    maud: dict[str, Any] | None,
    cuad: dict[str, Any] | None,
) -> str:
    """Render the four-column Markdown results table.

    The caption (cluster-bootstrap pre-commitment paragraph) is appended ONLY when
    Internal-30 data is present — there is nothing to pre-commit about
    when the row is a placeholder.
    """
    rows: list[Row] = []
    rows.extend(_build_internal30_rows(internal30))
    rows.extend(_build_maud_rows(maud))
    rows.extend(_build_cuad_rows(cuad))

    lines: list[str] = []
    lines.append("| Track | Metric | Value | Notes |")
    lines.append("|---|---|---|---|")
    for track, metric, value, notes in rows:
        lines.append(
            f"| {_escape_pipe(track)} | {_escape_pipe(metric)} | "
            f"{_escape_pipe(value)} | {_escape_pipe(notes)} |"
        )
    table_md = "\n".join(lines)

    if internal30 is not None:
        table_md = f"{table_md}\n\n{CLUSTER_BOOTSTRAP_PRECOMMIT_CAPTION}"
    return table_md


def _escape_pipe(text: str) -> str:
    """Escape `|` inside a cell so it doesn't break the table."""
    return str(text).replace("|", "\\|")


# ---------------------------------------------------------------------------
# README splicing
# ---------------------------------------------------------------------------


def splice_into_readme(readme_path: Path, table_md: str) -> bytes:
    """Splice `table_md` between BEGIN/END markers in the README.

    Raises `ValueError` if either marker is missing — silently
    appending would let a typo in the README hide a stale table.

    Returns the new README content as BYTES with the original
    line-ending preserved (per Round-2 Fix #7 — CRLF must survive a
    round-trip, otherwise a Windows operator gets a churn-diff on first
    run). Caller decides whether to write the bytes back.
    """
    if not readme_path.exists():
        raise FileNotFoundError(f"README not found: {readme_path}")
    # Read as BYTES so we can detect the native line-ending and emit
    # the spliced text in the same convention. `Path.read_text()` opens
    # in universal-newline mode and silently collapses CRLF→LF before
    # we ever see it; that yields a churn-diff on the first run against
    # a Windows-authored README.
    original_bytes = readme_path.read_bytes()
    # Detect line-ending: any CRLF wins (mixed-ending files are
    # extremely rare; if present we prefer CRLF because that's what a
    # Windows operator's editor will preserve).
    if b"\r\n" in original_bytes:
        newline = b"\r\n"
    else:
        newline = b"\n"
    # Decode for marker-search; the markers themselves are ASCII so
    # decoding as UTF-8 is safe.
    original = original_bytes.decode("utf-8")

    # Search both markers from the very start of the document so an
    # END-before-BEGIN ordering is caught WITHOUT raising the dead-code
    # `ValueError: substring not found` from `str.index(..., start)`.
    begin_idx = original.find(BEGIN_MARKER)
    end_idx = original.find(END_MARKER)
    if begin_idx == -1 or end_idx == -1:
        # Fix #8: spell out the exact remediation (markers are a D18
        # task — adding them is an EXPLICIT prerequisite, NOT something
        # this script does automatically).
        raise ValueError(
            f"README at {readme_path} is missing the splice markers. "
            f"Add `{BEGIN_MARKER}` and `{END_MARKER}` to the README as "
            "a one-time D18 prerequisite, then rerun."
        )
    if end_idx < begin_idx:
        raise ValueError(
            f"README at {readme_path}: END marker appears before BEGIN "
            f"marker (END at offset {end_idx}, BEGIN at offset "
            f"{begin_idx}). Fix the marker order before re-running."
        )
    # Validate that END comes strictly AFTER the closing position of
    # the BEGIN marker (otherwise the markers overlap or are stacked).
    if end_idx < begin_idx + len(BEGIN_MARKER):
        raise ValueError(
            f"README at {readme_path}: END marker overlaps the BEGIN "
            "marker. Add a line break between them and re-run."
        )

    # Rebuild using the original line-ending. The table itself is
    # rendered with \n line-endings; translate to the file's native
    # convention so we don't sneak \n into a CRLF document.
    table_native = table_md.replace("\n", newline.decode("ascii"))
    new_text = (
        original[: begin_idx + len(BEGIN_MARKER)]
        + newline.decode("ascii")
        + table_native
        + newline.decode("ascii")
        + original[end_idx:]
    )
    return new_text.encode("utf-8")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_readme_table",
        description=(
            "Render the three-track results table (Internal-30 / "
            "MAUD-MCQ / CUAD-Spans) for the README."
        ),
    )
    p.add_argument("--calibrate", type=Path, default=None,
                   help="Path to scripts/calibrate.py JSON output.")
    p.add_argument("--maud", type=Path, default=None,
                   help="Path to scripts/eval_maud_mcq.py JSON output.")
    p.add_argument("--cuad", type=Path, default=None,
                   help="Path to scripts/eval_cuad_spans.py JSON output.")
    p.add_argument("--out", type=Path, default=None,
                   help="Write rendered Markdown to this path (default: stdout).")
    p.add_argument(
        "--update-readme",
        type=Path,
        default=None,
        help=(
            f"Path to README.md; splices the table between "
            f"`{BEGIN_MARKER}` and `{END_MARKER}` markers (markers must "
            "be added to the README manually — D18 task)."
        ),
    )
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_argparser().parse_args(list(argv) if argv is not None else None)
    try:
        loaded = load_track_jsons(
            calibrate_path=args.calibrate,
            maud_path=args.maud,
            cuad_path=args.cuad,
        )
        table_md = render_table(
            internal30=loaded["internal30"],
            maud=loaded["maud"],
            cuad=loaded["cuad"],
        )
        if args.update_readme is not None:
            # `splice_into_readme` now returns bytes so the native line-
            # ending of the README is preserved on write-back. Using
            # `write_bytes` (rather than `write_text`) means no
            # automatic CRLF→LF translation by the text-mode writer.
            new_readme = splice_into_readme(args.update_readme, table_md)
            args.update_readme.write_bytes(new_readme)
            _LOG.info("Updated README at %s", args.update_readme)
        if args.out is not None:
            args.out.write_text(table_md + "\n")
            _LOG.info("Wrote table to %s", args.out)
        # Default sink: stdout. We still print to stdout when --out is
        # given so the operator sees what was written (useful when piping).
        if args.update_readme is None or args.out is not None:
            print(table_md)
        elif args.out is None and args.update_readme is None:
            print(table_md)
    except (FileNotFoundError, ValueError) as exc:
        _LOG.error("%s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    raise SystemExit(main(sys.argv[1:]))
