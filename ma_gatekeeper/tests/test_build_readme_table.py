"""Invariant tests for scripts/build_readme_table.py.

Per Builder B's defensive priorities, each test pins an UNHAPPY-PATH
or honesty-guard behavior — happy-path rendering is incidental; the
load-bearing properties are:
  * Honesty-guards never elide a degenerate-AUPR caveat or a P@R
    fallback flag.
  * The Wilson 95% LB row is ALWAYS labelled load-bearing and the
    pre-commitment caption is appended whenever Internal-30 is present.
  * Dropped folds are NEVER hidden.
  * A missing input renders a clearly-labelled "Not yet available" row
    (partial intermediate artifacts must still be valid Markdown).
  * `--update-readme` errors loudly if the markers are missing rather
    than appending silently.

Tests cover every branch enumerated in the Round-1 spec (≥15 tests).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import build_readme_table as M


# ---------------------------------------------------------------------------
# Fixture helpers — JSON payloads that match the source-of-truth contracts.
# ---------------------------------------------------------------------------


def _calibrate_payload(
    *,
    dropped: list[int] | None = None,
    point_recall: float = 0.875,
    wilson_lb: float = 0.612,
    boot_lb: float = 0.598,
) -> dict:
    return {
        "headline_folds": [1, 2, 3, 4],
        "headline_folds_present": [1, 2, 3, 4] if not dropped else
            [f for f in [1, 2, 3, 4] if f not in dropped],
        "dropped_headline_folds": dropped or [],
        "frozen_fold": 5,
        "effective_n_contracts": 24,
        "per_fold": [
            {"fold": 1, "tau_h": 0.42, "tau_f": 0.55, "recall": 1.0,
             "abstention": 0.15},
        ],
        "point_block_recall": point_recall,
        "wilson_one_sided_95_lb_block_recall": wilson_lb,
        "cluster_bootstrap_one_sided_95_lb_block_recall": boot_lb,
        "deployed_tau_h": 0.42,
        "deployed_tau_f": 0.55,
        "tau_h": 0.42,
        "tau_f": 0.55,
    }


def _maud_payload(*, baselines: dict | None | object = ...) -> dict:
    """Build a MAUD-like JSON. `baselines=...` means 'omit the key entirely';
    `None` means 'explicit null'; a dict means 'present'."""
    payload = {
        "n_total_examples": 152,
        "n_evaluated": 148,
        "n_correct": 96,
        "n_unmatched_responses": 4,
        "n_skipped_with_reason": {"no_choices_listed": 4},
        "overall_micro_accuracy": 0.6486,
        "overall_macro_accuracy": 0.6234,
        "per_category": {},
        "aupr_degenerate": 0.7123,
    }
    if baselines is not ...:
        payload["comparison_baselines"] = baselines
    return payload


def _cuad_payload(
    *,
    # Round-2 Fix #4: defaults now match the REAL enum from
    # eval_cuad_spans.py:107-114 + L620. `None` = achieved;
    # f"recall_{target}_unachieved" = fallback.
    p08_flag: str | None = None,
    p08_value: float | None = 0.812,
    p09_flag: str | None = "recall_0.9_unachieved",
    p09_value: float | None = None,
    cuad_baselines: dict | None | object = ...,
) -> dict:
    payload: dict = {
        "n_examples": 60,
        "n_contracts": 30,
        "clause_types": ["Change of Control", "Anti-Assignment"],
        "per_clause_type": {},
        "macro_f1": 0.534,
        "micro_f1": 0.512,
        "macro_f1_paper": 0.601,
        "micro_f1_paper": 0.589,
        "p_at_r_0_8": {
            "target_recall": 0.8,
            "total_gold": 100,
            "p_at_r_0_8": p08_value,
            "achieved_recall_max": 0.83,
            "p_at_achieved_max_recall": 0.78,
            "rank_at_target": 42,
            "flag": p08_flag,
        },
        "p_at_r_0_9": {
            "target_recall": 0.9,
            "total_gold": 100,
            "p_at_r_0_8": p09_value,  # back-compat key name
            "achieved_recall_max": 0.83,
            "p_at_achieved_max_recall": 0.78,
            "rank_at_target": -1,
            "flag": p09_flag,
        },
        "aupr_overall": 0.4567,
    }
    if cuad_baselines is not ...:
        payload["comparison_baselines"] = cuad_baselines
    return payload


def _write_json(tmp_path: Path, name: str, payload: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return p


# ---------------------------------------------------------------------------
# 1. Happy path — all three tracks present
# ---------------------------------------------------------------------------


def test_render_all_three_present(tmp_path: Path) -> None:
    cal = _write_json(tmp_path, "cal.json", _calibrate_payload())
    maud = _write_json(tmp_path, "maud.json", _maud_payload(baselines=...))
    cuad = _write_json(tmp_path, "cuad.json", _cuad_payload())
    loaded = M.load_track_jsons(
        calibrate_path=cal, maud_path=maud, cuad_path=cuad,
    )
    table = M.render_table(**loaded)
    assert "Internal-30" in table
    assert "MAUD-MCQ" in table
    assert "CUAD-Spans" in table
    assert "0.875" in table          # point recall
    assert "0.612" in table          # Wilson LB
    assert "62.3%" in table          # macro accuracy formatted
    assert "0.534" in table          # CUAD macro_f1
    # Pre-commitment caption present.
    assert "load-bearing" in table
    assert "arithmetically tight" in table


# ---------------------------------------------------------------------------
# 2. Only one track present — others get "Not yet available" rows
# ---------------------------------------------------------------------------


def test_render_only_maud_present(tmp_path: Path) -> None:
    maud = _write_json(tmp_path, "maud.json", _maud_payload(baselines=...))
    loaded = M.load_track_jsons(
        calibrate_path=None, maud_path=maud, cuad_path=None,
    )
    table = M.render_table(**loaded)
    assert "MAUD-MCQ" in table
    # Internal-30 + CUAD render as Not yet available placeholders.
    assert "Not yet available" in table
    # Wilson pre-commitment is NOT appended when Internal-30 is missing.
    assert "load-bearing" not in table


# ---------------------------------------------------------------------------
# 3. None present — empty banner without crashing
# ---------------------------------------------------------------------------


def test_render_none_present_renders_empty_banner() -> None:
    table = M.render_table(internal30=None, maud=None, cuad=None)
    # All three tracks visible as placeholders.
    assert table.count("Not yet available") == 3
    # Header preserved.
    assert table.startswith("| Track | Metric | Value | Notes |")


# ---------------------------------------------------------------------------
# 4. --update-readme with markers PRESENT splices correctly
# ---------------------------------------------------------------------------


def test_update_readme_with_markers_splices(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\n"
        f"{M.BEGIN_MARKER}\n"
        "STALE TABLE HERE\n"
        f"{M.END_MARKER}\n\n"
        "Tail.\n"
    )
    table_md = "| Track | Metric | Value | Notes |\n|---|---|---|---|"
    # Round-2 Fix #7: splice_into_readme now returns bytes (so line-ending
    # preservation is unambiguous). Decode for substring assertions.
    new_text = M.splice_into_readme(readme, table_md).decode("utf-8")
    assert "STALE TABLE HERE" not in new_text
    assert table_md in new_text
    assert "Tail." in new_text
    assert "# Title" in new_text


# ---------------------------------------------------------------------------
# 5. --update-readme with markers MISSING raises ValueError
# ---------------------------------------------------------------------------


def test_update_readme_with_markers_missing_raises(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\nNo markers here.\n")
    # Round-2 Fix #8: the error message now explicitly names the D18
    # prerequisite. Match against the new actionable phrasing.
    with pytest.raises(ValueError, match="missing the splice markers"):
        M.splice_into_readme(readme, "| ... |")


def test_update_readme_with_only_begin_marker_raises(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(f"# Title\n\n{M.BEGIN_MARKER}\n")
    with pytest.raises(ValueError, match="missing the splice markers"):
        M.splice_into_readme(readme, "| ... |")


def test_update_readme_missing_markers_message_mentions_d18(tmp_path: Path) -> None:
    """Round-2 Fix #8: the error must explicitly call out the D18
    prerequisite so the operator's next step is unambiguous."""
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\nNo markers.\n")
    with pytest.raises(ValueError) as excinfo:
        M.splice_into_readme(readme, "| ... |")
    msg = str(excinfo.value)
    assert "D18" in msg
    assert M.BEGIN_MARKER in msg
    assert M.END_MARKER in msg


def test_update_readme_end_before_begin_raises_actionable_error(tmp_path: Path) -> None:
    """Round-2 Fix #5: with END before BEGIN, the previous implementation
    raised the generic `str.index(..., start)` ValueError BEFORE the
    custom branch could fire, making the actionable error dead code.
    Pin the actionable phrasing."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\n"
        f"{M.END_MARKER}\n"
        "stale\n"
        f"{M.BEGIN_MARKER}\n"
        "Tail.\n"
    )
    with pytest.raises(ValueError, match="END marker appears before BEGIN"):
        M.splice_into_readme(readme, "| ... |")


def test_update_readme_preserves_crlf_line_endings(tmp_path: Path) -> None:
    """Round-2 Fix #7: a CRLF README must round-trip without a silent
    LF conversion. Path.read_text() + Path.write_text() collapses CRLF
    to LF (universal-newlines); the bytes-based implementation must
    preserve the original convention."""
    readme = tmp_path / "README.md"
    crlf_content = (
        "# Title\r\n\r\n"
        f"{M.BEGIN_MARKER}\r\n"
        "STALE\r\n"
        f"{M.END_MARKER}\r\n\r\n"
        "Tail.\r\n"
    )
    readme.write_bytes(crlf_content.encode("utf-8"))
    table_md = "| Track | Metric | Value | Notes |\n|---|---|---|---|"
    result = M.splice_into_readme(readme, table_md)
    # Result is bytes, with CRLF preserved everywhere — including for
    # the freshly-spliced table content.
    assert isinstance(result, bytes)
    assert b"\r\n" in result
    # No bare LF (every LF must be paired with a CR).
    assert b"\n" in result  # sanity: there ARE newlines
    decoded = result.decode("utf-8")
    bare_lf_count = sum(
        1 for i, ch in enumerate(decoded)
        if ch == "\n" and (i == 0 or decoded[i - 1] != "\r")
    )
    assert bare_lf_count == 0, "found a bare LF — CRLF was not preserved"


def test_update_readme_preserves_lf_when_lf_source(tmp_path: Path) -> None:
    """Round-2 Fix #7 corollary: an LF-only README must NOT get CRLF
    injected just because we now support CRLF — same convention in,
    same convention out."""
    readme = tmp_path / "README.md"
    lf_content = (
        "# Title\n\n"
        f"{M.BEGIN_MARKER}\n"
        "STALE\n"
        f"{M.END_MARKER}\n\n"
        "Tail.\n"
    )
    readme.write_bytes(lf_content.encode("utf-8"))
    result = M.splice_into_readme(readme, "| ... |")
    assert b"\r\n" not in result


# ---------------------------------------------------------------------------
# 6. MAUD without comparison_baselines — no vs-baseline rows rendered
# ---------------------------------------------------------------------------


def test_maud_without_baselines_no_vs_rows(tmp_path: Path) -> None:
    maud_data = _maud_payload(baselines=None)
    rows = M._build_maud_rows(maud_data)
    metrics = [r[1] for r in rows]
    assert not any(m.startswith("vs ") for m in metrics)


def test_maud_aupr_row_carries_degenerate_caveat() -> None:
    """Round-2 Fix #2: the AUPR row itself is where DEGENERATE_CAVEAT
    belongs (eval_maud_mcq.py emits a single confidence, not per-choice
    probs)."""
    rows = M._build_maud_rows(_maud_payload(baselines=...))
    aupr_rows = [r for r in rows if "AUPR" in r[1]]
    assert len(aupr_rows) == 1
    _, _, _, note = aupr_rows[0]
    assert M.DEGENERATE_CAVEAT in note


def test_maud_baseline_rows_use_accuracy_note_not_aupr_caveat() -> None:
    """Round-2 Fix #2: plan §5.2 line 203 frames MAUD baselines as
    exact-match-accuracy comparisons. Attaching the AUPR-shaped
    DEGENERATE_CAVEAT to an accuracy comparison mislabels the metric
    and weakens the honesty signal by crying wolf. Baseline rows MUST
    instead surface that they are accuracy-comparisons."""
    maud_data = _maud_payload(baselines={"MAUD paper §4": 0.687})
    rows = M._build_maud_rows(maud_data)
    metrics = [r[1] for r in rows]
    assert any(m == "vs MAUD paper §4" for m in metrics)
    baseline_rows = [r for r in rows if r[1].startswith("vs ")]
    assert baseline_rows, "expected at least one baseline row"
    for _, _, _, note in baseline_rows:
        # The accuracy framing is explicit.
        assert "exact-match accuracy" in note
        # The AUPR-shaped caveat is intentionally NOT present.
        assert M.DEGENERATE_CAVEAT not in note


# ---------------------------------------------------------------------------
# 7. CUAD with FALLBACK flag — fallback explicitly surfaced in Notes
# ---------------------------------------------------------------------------


def test_cuad_fallback_flag_surfaced_in_notes() -> None:
    """Round-2 Fix #3 + #4: the real fallback flag is dynamic on
    target recall (eval_cuad_spans.py:107-114 emits
    f"recall_{target}_unachieved"). The fallback Notes must quote that
    actual string, surface achieved_recall_max, and include the literal
    '**FALLBACK**' so a judge cannot miss it."""
    rows = M._build_cuad_rows(
        _cuad_payload(p09_flag="recall_0.9_unachieved", p09_value=None),
    )
    p09_rows = [r for r in rows if r[1] == "P@R=0.9"]
    assert len(p09_rows) == 1
    _, _, value, note = p09_rows[0]
    # Value defaults to em-dash when None — never silently 0.000 or 1.000.
    assert value == "—"
    # The literal "**FALLBACK**" marker is mandatory.
    assert "**FALLBACK**" in note
    # The actual flag string is quoted verbatim (so an unfamiliar reader
    # can grep for it in eval_cuad_spans.py).
    assert "recall_0.9_unachieved" in note
    # The achieved-max-recall is exposed so the reader sees what was
    # *actually* achieved.
    assert "max achieved recall" in note
    assert "0.830" in note  # from the fixture's achieved_recall_max=0.83
    assert "NOT the achieved" in note


def test_cuad_achieved_flag_clean_note() -> None:
    """Round-2 Fix #3 + #4: the achieved case is `flag is None` (NOT
    the fabricated 'ACHIEVED' string). The note must be clean."""
    rows = M._build_cuad_rows(_cuad_payload(p08_flag=None))
    p08_rows = [r for r in rows if r[1] == "P@R=0.8"]
    assert len(p08_rows) == 1
    _, _, _, note = p08_rows[0]
    # Achieved → no fallback warning, no "**FALLBACK**" marker.
    assert "fallback" not in note.lower()
    assert "**FALLBACK**" not in note
    # No false "verify your eval JSON shape" alarm either (Round-1 bug).
    assert "verify eval JSON shape" not in note
    # And the note explicitly affirms the achieved outcome.
    assert "Achieved at target recall" in note


def test_cuad_unknown_flag_surfaces_verify_message() -> None:
    """Round-2 Fix #3: a genuinely unrecognised flag (neither None nor
    the recall_*_unachieved family) is the REAL 'verify eval JSON shape'
    failure mode — surface it loudly without conflating it with the
    achieved or fallback paths."""
    rows = M._build_cuad_rows(_cuad_payload(p08_flag="some_brand_new_flag"))
    p08_rows = [r for r in rows if r[1] == "P@R=0.8"]
    assert len(p08_rows) == 1
    _, _, _, note = p08_rows[0]
    assert "Unknown flag" in note
    assert "verify eval JSON shape" in note
    # The unknown flag value must appear so the operator can fix it.
    assert "some_brand_new_flag" in note
    # It is NOT misclassified as fallback or achieved.
    assert "**FALLBACK**" not in note
    assert "Achieved at target recall" not in note


def test_cuad_unachieved_flag_p08_dynamic_target() -> None:
    """Round-2 Fix #3: the unachieved regex must also match the
    P@R=0.8 target (not just 0.9). Pin the dynamic enum."""
    rows = M._build_cuad_rows(
        _cuad_payload(p08_flag="recall_0.8_unachieved", p08_value=None),
    )
    p08_rows = [r for r in rows if r[1] == "P@R=0.8"]
    _, _, _, note = p08_rows[0]
    assert "**FALLBACK**" in note
    assert "recall_0.8_unachieved" in note


def test_cuad_with_baselines_renders_vs_rows_without_aupr_caveat() -> None:
    """Round-2 Fix #1: plan §5.2 line 204 commits CUAD-Spans to
    'Compared to CUAD published baselines'; the eval JSON exposes
    `comparison_baselines` (eval_cuad_spans.py L689, L704). Mirror the
    MAUD baseline-row pattern — but unlike MAUD, CUAD's baseline metric
    is token-F1 / AUPR (CUAD §3), NOT a degenerate-AUPR construct, so
    DEGENERATE_CAVEAT must NOT be attached."""
    cuad = _cuad_payload(cuad_baselines={"CUAD paper §3 (RoBERTa-base)": 0.456})
    rows = M._build_cuad_rows(cuad)
    metrics = [r[1] for r in rows]
    assert any(m == "vs CUAD paper §3 (RoBERTa-base)" for m in metrics)
    baseline_rows = [r for r in rows if r[1].startswith("vs ")]
    assert baseline_rows
    for _, _, _, note in baseline_rows:
        # CUAD-appropriate note (NOT the degenerate-AUPR caveat).
        assert "CUAD paper §3 metric" in note
        assert M.DEGENERATE_CAVEAT not in note


def test_cuad_without_baselines_no_vs_rows() -> None:
    """Round-2 Fix #1: missing comparison_baselines → NO vs-rows
    (same shape as the MAUD-side guard)."""
    rows = M._build_cuad_rows(_cuad_payload())  # baselines key absent
    metrics = [r[1] for r in rows]
    assert not any(m.startswith("vs ") for m in metrics)


def test_cuad_null_baselines_no_vs_rows() -> None:
    """Round-2 Fix #1: explicit JSON null → NO vs-rows (NOT a stray
    'vs None' row)."""
    rows = M._build_cuad_rows(_cuad_payload(cuad_baselines=None))
    metrics = [r[1] for r in rows]
    assert not any(m.startswith("vs ") for m in metrics)


def test_cuad_empty_baselines_dict_no_vs_rows() -> None:
    """Round-2 Fix #1: empty dict → NO vs-rows (no header-without-body)."""
    rows = M._build_cuad_rows(_cuad_payload(cuad_baselines={}))
    metrics = [r[1] for r in rows]
    assert not any(m.startswith("vs ") for m in metrics)


def test_explicit_null_int_renders_as_em_dash() -> None:
    """Round-2 Fix #6: `dict.get(key, "—")` only returns the default
    when the key is ABSENT. JSON `null` → Python `None` → renders as
    the literal string "None" with the old pattern. All three
    int-shaped fields must coerce explicit-null to em-dash."""
    # Internal-30 effective_n_contracts
    calibrate = _calibrate_payload()
    calibrate["effective_n_contracts"] = None
    rows = M._build_internal30_rows(calibrate)
    eff_n_rows = [r for r in rows if r[1] == "Effective N (contracts)"]
    assert eff_n_rows[0][2] == "—"
    assert eff_n_rows[0][2] != "None"

    # MAUD n_evaluated / n_total_examples — both null.
    maud = _maud_payload(baselines=...)
    maud["n_evaluated"] = None
    maud["n_total_examples"] = None
    rows_m = M._build_maud_rows(maud)
    n_rows = [r for r in rows_m if r[1] == "N evaluated / N total"]
    assert n_rows[0][2] == "— / —"
    assert "None" not in n_rows[0][2]

    # MAUD only one of the two null — mixed case still safe.
    maud2 = _maud_payload(baselines=...)
    maud2["n_evaluated"] = None
    rows_m2 = M._build_maud_rows(maud2)
    n_rows2 = [r for r in rows_m2 if r[1] == "N evaluated / N total"]
    assert n_rows2[0][2] == "— / 152"


# ---------------------------------------------------------------------------
# 8. Calibrate with non-empty dropped_headline_folds — never hidden
# ---------------------------------------------------------------------------


def test_dropped_folds_surfaced_as_row() -> None:
    rows = M._build_internal30_rows(_calibrate_payload(dropped=[3]))
    metrics = [r[1] for r in rows]
    assert "Dropped folds" in metrics
    dropped_row = [r for r in rows if r[1] == "Dropped folds"][0]
    assert "3" in dropped_row[2]


def test_no_dropped_folds_no_row() -> None:
    rows = M._build_internal30_rows(_calibrate_payload(dropped=[]))
    metrics = [r[1] for r in rows]
    assert "Dropped folds" not in metrics


# ---------------------------------------------------------------------------
# 9. Malformed JSON file → ValueError with clear message
# ---------------------------------------------------------------------------


def test_malformed_json_raises_with_path(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{this is not json")
    with pytest.raises(ValueError, match="malformed"):
        M.load_track_jsons(
            calibrate_path=bad, maud_path=None, cuad_path=None,
        )


def test_nonexistent_path_raises_filenotfound(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        M.load_track_jsons(
            calibrate_path=tmp_path / "does_not_exist.json",
            maud_path=None,
            cuad_path=None,
        )


# ---------------------------------------------------------------------------
# 10. comparison_baselines null vs missing key — both yield NO vs-rows
# ---------------------------------------------------------------------------


def test_comparison_baselines_null_no_vs_rows() -> None:
    rows = M._build_maud_rows(_maud_payload(baselines=None))
    metrics = [r[1] for r in rows]
    assert not any(m.startswith("vs ") for m in metrics)


def test_comparison_baselines_key_missing_no_vs_rows() -> None:
    rows = M._build_maud_rows(_maud_payload(baselines=...))
    metrics = [r[1] for r in rows]
    assert not any(m.startswith("vs ") for m in metrics)


def test_comparison_baselines_empty_dict_no_vs_rows() -> None:
    rows = M._build_maud_rows(_maud_payload(baselines={}))
    metrics = [r[1] for r in rows]
    assert not any(m.startswith("vs ") for m in metrics)


# ---------------------------------------------------------------------------
# 11. Wilson pre-commitment caption attaches ONLY when Internal-30 present
# ---------------------------------------------------------------------------


def test_wilson_caption_only_when_internal30_present() -> None:
    with_int30 = M.render_table(
        internal30=_calibrate_payload(), maud=None, cuad=None,
    )
    without_int30 = M.render_table(internal30=None, maud=None, cuad=None)
    assert "load-bearing" in with_int30
    assert "arithmetically tight" in with_int30
    assert "load-bearing" not in without_int30


# ---------------------------------------------------------------------------
# 12. Number formatting: f-string (not double-rounded)
# ---------------------------------------------------------------------------


def test_3dp_formatting_no_double_round() -> None:
    # 0.6125 — f"{x:.3f}" → '0.612' (banker's rounding on this build);
    # round(0.6125, 3) → 0.612 as well, but the pattern that DOUBLE-rounds
    # (str(round(round(x, 4), 3))) would produce '0.613'. Pinning here.
    rows = M._build_internal30_rows(
        _calibrate_payload(wilson_lb=0.6125),
    )
    wilson_row = [r for r in rows if "Wilson" in r[1]][0]
    # Either 0.612 or 0.613 depending on banker's rounding; pin that
    # we used `f"{x:.3f}"` directly (no extra round-then-format step).
    assert wilson_row[2] in {"0.612", "0.613"}


def test_percent_formatting_one_decimal() -> None:
    rows = M._build_maud_rows(_maud_payload(baselines=...))
    macro = [r for r in rows if "macro" in r[1]][0]
    assert macro[2].endswith("%")
    assert macro[2] == "62.3%"


# ---------------------------------------------------------------------------
# 13. Markdown table shape — header + separator + correct column count
# ---------------------------------------------------------------------------


def test_table_header_shape() -> None:
    table = M.render_table(internal30=None, maud=None, cuad=None)
    lines = table.splitlines()
    assert lines[0] == "| Track | Metric | Value | Notes |"
    assert lines[1] == "|---|---|---|---|"
    # Every data line has exactly 4 cells (5 pipes).
    for line in lines[2:]:
        if line.startswith("|"):
            assert line.count("|") == 5, line


# ---------------------------------------------------------------------------
# 14. CLI entry point — main(argv) returns 0 on empty banner
# ---------------------------------------------------------------------------


def test_main_no_args_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    code = M.main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "Track" in out
    assert "Not yet available" in out


def test_main_writes_out_file(tmp_path: Path) -> None:
    out = tmp_path / "table.md"
    code = M.main(["--out", str(out)])
    assert code == 0
    written = out.read_text()
    assert "Track" in written


def test_main_returns_1_on_missing_marker(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Title\nno markers")
    code = M.main(["--update-readme", str(readme)])
    assert code == 1
    # README untouched on failure.
    assert "no markers" in readme.read_text()


def test_main_returns_1_on_malformed_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    code = M.main(["--calibrate", str(bad)])
    assert code == 1


# ---------------------------------------------------------------------------
# 15. End-to-end CLI smoke via subprocess — the real `python -m` path
# ---------------------------------------------------------------------------


def test_cli_smoke_via_subprocess() -> None:
    """Round-trip the CLI exactly as a CI/operator would invoke it.

    Pins that `python -m scripts.build_readme_table` exits 0 with no
    flags and emits the table header.
    """
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.build_readme_table"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "| Track | Metric | Value | Notes |" in result.stdout
    assert "Not yet available" in result.stdout


# ---------------------------------------------------------------------------
# 16. Pipe-escaping inside notes (defensive against pipes in track strings)
# ---------------------------------------------------------------------------


def test_pipe_in_cell_is_escaped() -> None:
    maud = _maud_payload(baselines={"x|y": 0.5})
    rows = M._build_maud_rows(maud)
    # Render the table from this single-track payload.
    table = M.render_table(internal30=None, maud=maud, cuad=None)
    # The pipe inside the baseline name must be escaped.
    assert "x\\|y" in table


# ---------------------------------------------------------------------------
# 17. End-to-end render: all three tracks + dropped fold + fallback flag
# ---------------------------------------------------------------------------


def test_e2e_all_three_with_dropped_and_fallback(tmp_path: Path) -> None:
    cal = _write_json(tmp_path, "cal.json", _calibrate_payload(dropped=[2]))
    maud = _write_json(
        tmp_path, "maud.json",
        _maud_payload(baselines={"MAUD paper §4": 0.687}),
    )
    cuad = _write_json(
        tmp_path, "cuad.json",
        # Round-2 Fix #4: real fallback flag is dynamic on target.
        _cuad_payload(p09_flag="recall_0.9_unachieved", p09_value=None),
    )
    loaded = M.load_track_jsons(
        calibrate_path=cal, maud_path=maud, cuad_path=cuad,
    )
    table = M.render_table(**loaded)
    # Dropped fold surfaced.
    assert "Dropped folds" in table
    # Real fallback flag surfaced (per Round-2 Fix #3/#4).
    assert "recall_0.9_unachieved" in table
    assert "**FALLBACK**" in table
    # MAUD baseline rendered with accuracy framing (Round-2 Fix #2).
    assert "vs MAUD paper §4" in table
    # AUPR-row caveat still present (the canonical degenerate caveat is
    # attached to the AUPR row, not to baseline rows — Round-2 Fix #2).
    assert M.DEGENERATE_CAVEAT in table
    # Pre-commitment caption attached.
    assert "load-bearing" in table
