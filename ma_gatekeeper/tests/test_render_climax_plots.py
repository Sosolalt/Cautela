"""Tests for `scripts/render_climax_plots.py` (spec §10).

Pattern: pure-Python; mock matplotlib's `savefig`; recorder-style
assertions on figure structure, matching the `_AxRecorder` idiom from
[test_calibration_invariants.py](./test_calibration_invariants.py).

Each test pins a single load-bearing property of the renderer:

  1. test_render_promoted_mock_does_not_crash — smoke test.
  2. test_output_file_exists_and_nonempty — PNG written, > 10 KB.
  3. test_label_text_correctness — LB/ε strings render to 3 decimals.
  4. test_color_uses_tokens_only — every hex passed to matplotlib is
     in the token palette borrowed from design/tokens.ts.
  5. test_fail_gate_renders_blocked_variant — BLOCKED string present;
     PROMOTED absent (substring + boundary check).
  6. test_byte_identical_on_rerun — two renders of identical input
     produce byte-identical PNGs (pins determinism).
  7. test_raises_on_missing_required_key — KeyError on missing field.
  8. test_raises_on_empty_delta_array — ValueError on empty array.
  9. test_diag_internal_consistency — stale-diag raises ValueError.
  10. test_mp4_mode_raises_not_implemented — pins the deferred contract.
  11. test_cited_line_numbers_resolve_to_named_functions — defends
      against fabricated SDK signatures (PROJECT_LOG.md pattern).
  12. test_footer_overflow_aborts — long source field raises
      RuntimeError; truncation/wrap forbidden.
"""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import numpy as np
import pytest

from agent import reflector
from scripts import render_climax_plots as rcp
from scripts.render_climax_plots import (
    REQUIRED_DIAG_KEYS,
    _footer_template,
    _mock_diag,
    _recompute_diag,
    derive_mode,
    load_diag,
    main,
    render_promotion_gate_figure,
)


# ---------------------------------------------------------------------------
# Recorder pattern — mirrors test_calibration_invariants._AxRecorder.
# ---------------------------------------------------------------------------

class _AxRecorder:
    """Standalone recorder masquerading as a matplotlib Axes.

    Records the structural arguments to every method
    `render_promotion_gate_figure` could call. Reused across the
    label-text + color-token tests.
    """

    def __init__(self) -> None:
        self.text_calls: list[tuple] = []      # (x, y, s, kwargs)
        self.title: str = ""
        self.barh_calls: list[dict] = []
        self.bar_calls: list[tuple] = []
        self.hist_calls: list[tuple] = []
        self.axvline_calls: list[dict] = []
        self.axvspan_calls: list[dict] = []
        self.vlines_calls: list[dict] = []
        self.plot_calls: list[tuple] = []

    # --- text + title ----------------------------------------------------
    def text(self, x, y, s, *args, **kwargs):
        self.text_calls.append((x, y, s, kwargs))

    def set_title(self, title: str, *args, **kwargs) -> None:
        self.title = title

    # --- plot primitives -------------------------------------------------
    def barh(self, **kwargs):
        self.barh_calls.append(kwargs)

    def bar(self, x, height, *args, **kwargs):
        self.bar_calls.append((list(x), list(height), kwargs))

    def hist(self, x, *args, **kwargs):
        self.hist_calls.append((list(x), args, kwargs))

    def axvline(self, x, **kwargs):
        self.axvline_calls.append({"x": x, **kwargs})

    def axvspan(self, x1, x2, **kwargs):
        self.axvspan_calls.append({"x1": x1, "x2": x2, **kwargs})

    def vlines(self, x, ymin, ymax, **kwargs):
        self.vlines_calls.append(
            {"x": x, "ymin": ymin, "ymax": ymax, **kwargs}
        )

    def plot(self, x, y, *args, **kwargs):
        self.plot_calls.append((list(x), list(y), kwargs))

    # --- styling no-ops --------------------------------------------------
    def __getattr__(self, _name):
        # Fallback for matplotlib methods the renderer may grow into
        # (spines, tick_params, etc.). Returns a chainable no-op.
        return _NoopProxy()


class _NoopProxy:
    """Chainable no-op — supports attr access and call, returns self."""

    def __getattr__(self, _name):
        return _NoopProxy()

    def __call__(self, *a, **kw):
        return _NoopProxy()

    def __getitem__(self, _key):
        return _NoopProxy()

    def __setitem__(self, _key, _value):
        return None


# ---------------------------------------------------------------------------
# Smoke tests — Spec §10 #1, #2.
# ---------------------------------------------------------------------------

def test_render_promoted_mock_does_not_crash(tmp_path: Path):
    """Spec §10 #1 — `render_promotion_gate_figure` returns without
    exception on the PROMOTED mock fixture."""
    diag, reg, fold5, source = _mock_diag("promoted")
    out = render_promotion_gate_figure(
        diag, reg, fold5, tmp_path / "promoted.png", source=source,
    )
    assert out.exists()


def test_output_file_exists_and_nonempty(tmp_path: Path):
    """Spec §10 #2 — output PNG written; size > 10 KB.

    The 10 KB floor catches the empty-figure regression pattern (a
    matplotlib figure that drew nothing still emits a ~7 KB PNG; a
    real climax figure with two panels + a pill + a footer lands
    >>10 KB on the canonical 2560×1440 canvas).
    """
    diag, reg, fold5, source = _mock_diag("promoted")
    out = render_promotion_gate_figure(
        diag, reg, fold5, tmp_path / "promoted.png", source=source,
    )
    assert out.stat().st_size > 10_000, (
        f"output {out} is too small ({out.stat().st_size} bytes); "
        "renderer likely no-op'd."
    )


# ---------------------------------------------------------------------------
# Label correctness — Spec §10 #3.
# ---------------------------------------------------------------------------

def test_label_text_correctness(tmp_path: Path, monkeypatch):
    """Spec §10 #3 — LB and ε strings render to 3-decimal precision.

    Mocks `add_subplot` to capture the rendered text on each panel. We
    do NOT skip `savefig` so the figure must still be coherent enough
    to save; we just inspect the recorded ax.text calls.
    """
    # Capture every ax.text on either panel by recording the real axes
    # via monkeypatching matplotlib Axes.text.
    captured_text: list[str] = []
    original_text = rcp.plt.Axes.text

    def _capturing_text(self, x, y, s, *args, **kwargs):
        captured_text.append(str(s))
        return original_text(self, x, y, s, *args, **kwargs)

    monkeypatch.setattr(rcp.plt.Axes, "text", _capturing_text)

    diag, reg, fold5, source = _mock_diag("promoted")
    render_promotion_gate_figure(
        diag, reg, fold5, tmp_path / "labels.png", source=source,
    )

    # LB string: "LB = {ci_lb:+.3f}" with the recomputed value.
    ci_lb = reflector.paired_bootstrap_ci_lb(reg)
    expected_lb = f"LB = {ci_lb:+.3f}"
    assert any(expected_lb in t for t in captured_text), (
        f"expected LB string {expected_lb!r} not found in captured "
        f"text calls: {captured_text}"
    )

    # ε string: "ε = {eps:.3f}".
    eps = reflector.epsilon_fold5(fold5)
    expected_eps = f"ε = {eps:.3f}"
    assert any(expected_eps in t for t in captured_text), (
        f"expected ε string {expected_eps!r} not found in captured "
        f"text calls: {captured_text}"
    )


# ---------------------------------------------------------------------------
# Token-only colors — Spec §10 #4.
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _allowed_palette() -> set[str]:
    """The set of allowed lower-case hex strings.

    Includes the token borrows in `_TOKENS` plus white (`#ffffff`) and
    pure black (`#000000`) which matplotlib emits internally for
    axis-spine defaults that the renderer immediately overrides. Test
    asserts subset, not equality, so silent additions still surface.
    """
    palette = set()
    for hex_str in rcp._TOKENS.values():
        palette.add(hex_str.lower())
    # Tolerated matplotlib internals — none are RENDERED in the final
    # PNG (they're overridden by `_style_axes`) but they show up in
    # the recorder's pre-style kwargs.
    palette.update({"#ffffff", "#000000", "none"})
    return palette


def test_color_uses_tokens_only(tmp_path: Path, monkeypatch):
    """Spec §10 #4 — every hex passed to matplotlib is in the palette.

    Captures `color=`, `facecolor=`, `edgecolor=`, `colors=` kwargs
    across every drawing call by monkeypatching the renderer's panel
    helpers. Asserts the captured set is a subset of the design-system
    palette borrowed in `_TOKENS`.
    """
    captured_colors: set[str] = set()

    def _harvest(value):
        """Collect a hex from `value` (str or list of strs)."""
        if isinstance(value, str) and _HEX_RE.match(value):
            captured_colors.add(value.lower())
        elif isinstance(value, (list, tuple)):
            for v in value:
                _harvest(v)

    # Wrap every Axes method that might carry a color kwarg.
    color_kwargs = (
        "color", "colors", "facecolor", "edgecolor",
        "fc", "ec",
    )

    def _patch(method_name: str):
        original = getattr(rcp.plt.Axes, method_name)

        def _wrapped(self, *args, **kwargs):
            for k in color_kwargs:
                if k in kwargs:
                    _harvest(kwargs[k])
            return original(self, *args, **kwargs)

        monkeypatch.setattr(rcp.plt.Axes, method_name, _wrapped)

    for m in (
        "text", "barh", "bar", "hist", "axvline", "axvspan", "vlines",
        "plot",
    ):
        _patch(m)

    diag, reg, fold5, source = _mock_diag("promoted")
    render_promotion_gate_figure(
        diag, reg, fold5, tmp_path / "tokens.png", source=source,
    )

    palette = _allowed_palette()
    stray = captured_colors - palette
    assert not stray, (
        f"non-token colors leaked into the renderer: {sorted(stray)}. "
        f"Allowed palette: {sorted(palette)}"
    )


# ---------------------------------------------------------------------------
# Blocked variant — Spec §10 #5.
# ---------------------------------------------------------------------------

def test_fail_gate_renders_blocked_variant(tmp_path: Path, monkeypatch):
    """Spec §10 #5 — BLOCKED string present; PROMOTED absent.

    Substring + word-boundary check on the rendered text strings.
    Captures via the same Axes.text monkeypatch as test #3 plus a
    matching fig.text harvest.
    """
    captured: list[str] = []
    original_axes_text = rcp.plt.Axes.text
    original_fig_text = rcp.plt.Figure.text

    def _ax_capture(self, x, y, s, *args, **kwargs):
        captured.append(str(s))
        return original_axes_text(self, x, y, s, *args, **kwargs)

    def _fig_capture(self, x, y, s, *args, **kwargs):
        captured.append(str(s))
        return original_fig_text(self, x, y, s, *args, **kwargs)

    monkeypatch.setattr(rcp.plt.Axes, "text", _ax_capture)
    monkeypatch.setattr(rcp.plt.Figure, "text", _fig_capture)

    diag, reg, fold5, source = _mock_diag("blocked")
    # derive_mode on the input diag returns "blocked".
    assert derive_mode(diag) == "blocked"

    render_promotion_gate_figure(
        diag, reg, fold5, tmp_path / "blocked.png", source=source,
    )

    blob = " ".join(captured)
    assert "PROMOTION BLOCKED" in blob, (
        f"expected 'PROMOTION BLOCKED' in rendered text; got: {captured}"
    )
    # Boundary check: PROMOTED must not appear as a standalone token
    # (a lax `in` would false-trigger on 'PROMOTION'). The pill is the
    # only renderer surface that could leak the word.
    assert not re.search(r"\bPROMOTED\b", blob), (
        f"BLOCKED variant must not render 'PROMOTED' as a standalone "
        f"word: {blob!r}"
    )


# ---------------------------------------------------------------------------
# Byte identity on rerun — Spec §10 #6.
# ---------------------------------------------------------------------------

def test_byte_identical_on_rerun(tmp_path: Path):
    """Spec §10 #6 — two renders with identical input → identical PNG bytes.

    Pins the determinism guarantees in spec §5:
      - `metadata={"Software": None, "Creation Time": None}` strips
        timestamp-bearing PNG chunks.
      - Seeded `np.random.default_rng(...)` makes the recomputation +
        any bootstrap sub-paths deterministic.

    If a future commit re-enables `bbox_inches="tight"`, or removes the
    `metadata` stripping, this test fires.
    """
    diag, reg, fold5, source = _mock_diag("promoted")
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    render_promotion_gate_figure(diag, reg, fold5, a, source=source)
    render_promotion_gate_figure(diag, reg, fold5, b, source=source)
    assert a.read_bytes() == b.read_bytes(), (
        "two renders of identical input produced different PNG bytes; "
        "non-determinism leaked in (timestamps? seeded RNG drift?)"
    )


# ---------------------------------------------------------------------------
# Input contract — Spec §10 #7, #8, #9.
# ---------------------------------------------------------------------------

def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_input_payload() -> dict:
    """A payload that passes the recomputation guard.

    Built by emitting the mock diag and arrays directly so the diag
    fields match the arrays bit-for-bit.
    """
    diag, reg, fold5, _source = _mock_diag("promoted")
    return {
        **diag,
        "regression_deltas": reg.tolist(),
        "fold5_deltas": fold5.tolist(),
        "source": "test_fixture",
    }


def test_raises_on_missing_required_key(tmp_path: Path):
    """Spec §10 #7 — KeyError when a required diag field is missing."""
    payload = _valid_input_payload()
    del payload["regression_ci_lb"]
    path = _write_json(tmp_path / "missing.json", payload)
    with pytest.raises(KeyError, match="regression_ci_lb"):
        load_diag(path)


def test_raises_on_empty_delta_array(tmp_path: Path):
    """Spec §10 #8 — ValueError on empty `regression_deltas`."""
    payload = _valid_input_payload()
    payload["regression_deltas"] = []
    path = _write_json(tmp_path / "empty.json", payload)
    with pytest.raises(ValueError, match="must be non-empty"):
        load_diag(path)


def test_diag_internal_consistency(tmp_path: Path):
    """Spec §10 #9 — stale diag (recomputed disagrees with input by
    > 1e-9) raises ValueError on call to `render_promotion_gate_figure`.

    Catches the "Hugo edited one diag field but forgot to re-run
    `should_promote` on the arrays" bug (spec §4 internal-consistency).
    """
    diag, reg, fold5, _source = _mock_diag("promoted")
    # Drift the regression_ci_lb diag value by 0.05 (well above 1e-9).
    diag_stale = dict(diag)
    diag_stale["regression_ci_lb"] = diag["regression_ci_lb"] + 0.05
    with pytest.raises(ValueError, match=r"diag stale: field regression_ci_lb"):
        render_promotion_gate_figure(
            diag_stale, reg, fold5, tmp_path / "stale.png", source="x",
        )


# ---------------------------------------------------------------------------
# Deferred contract — Spec §10 #10.
# ---------------------------------------------------------------------------

def test_mp4_mode_raises_not_implemented(tmp_path: Path):
    """Spec §10 #10 — `output_mode='mp4'` raises NotImplementedError."""
    diag, reg, fold5, source = _mock_diag("promoted")
    with pytest.raises(NotImplementedError, match="MP4"):
        render_promotion_gate_figure(
            diag, reg, fold5, tmp_path / "x.mp4",
            output_mode="mp4", source=source,
        )


# ---------------------------------------------------------------------------
# Cited line numbers — Spec §10 #11.
# ---------------------------------------------------------------------------

def test_cited_line_numbers_resolve_to_named_functions():
    """Spec §10 #11 — `inspect.getsourcelines` lines match footer cites.

    PROJECT_LOG.md "fabricated SDK signatures" failure pattern: the
    footer cites `reflector.py:465 paired_bootstrap_ci_lb`,
    `:507 epsilon_fold5`, `:512 should_promote`. If a future
    `agent/reflector.py` refactor moves any of those line numbers, the
    citation on screen becomes a lie. This test catches the silent
    drift.
    """
    expected = {
        "paired_bootstrap_ci_lb": 465,
        "epsilon_fold5": 507,
        "should_promote": 512,
    }
    for name, expected_line in expected.items():
        func = getattr(reflector, name)
        _, actual_line = inspect.getsourcelines(func)
        assert actual_line == expected_line, (
            f"reflector.{name} now lives at line {actual_line}, "
            f"but the climax-plot footer cites line {expected_line}. "
            "Update the footer template AND this pin together (the "
            "rendered audit trail must stay accurate per spec §8.5.1)."
        )


# ---------------------------------------------------------------------------
# Footer overflow — Spec §10 #12.
# ---------------------------------------------------------------------------

def test_footer_overflow_aborts():
    """Spec §10 #12 — long `source` field → RuntimeError("footer overflow…").

    Truncation and wrapping are explicitly forbidden by spec §6.6 /
    §8.3 because either hides cited references. The char-count cap
    fires before any matplotlib allocation, so this test runs fast.
    """
    huge_source = "reflector.run_id=" + "a" * 500
    huge_footer = _footer_template(huge_source)
    with pytest.raises(RuntimeError, match="footer overflow"):
        rcp._assert_footer_fits(huge_footer)


# ---------------------------------------------------------------------------
# Bonus coverage — extras that don't have a numbered spec slot but
# guard adjacent invariants the spec relies on.
# ---------------------------------------------------------------------------

def test_recompute_diag_matches_input_on_clean_mock():
    """Defense in depth on the recomputation invariant: the mock
    fixture's diag matches the recomputed diag bit-for-bit on every
    required key. If `_mock_diag` ever drifts from `should_promote`,
    the recomputation guard fires inside test #1 — but this isolates
    the failure here so the recorder-style tests don't false-positive.
    """
    for variant in ("promoted", "blocked"):
        diag, reg, fold5, _source = _mock_diag(variant)
        recomputed, _promote = _recompute_diag(diag, reg, fold5)
        for key in REQUIRED_DIAG_KEYS:
            assert abs(diag[key] - recomputed[key]) <= 1e-9, (
                f"variant={variant} drift on key {key}: "
                f"input={diag[key]} recomputed={recomputed[key]}"
            )
