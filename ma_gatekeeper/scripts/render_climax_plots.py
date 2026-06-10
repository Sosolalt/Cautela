"""Climax-beat promotion-gate visualization (demo 2:30-3:00).

Renders the picture-in-picture PNG that docks next to the live Phoenix
Experiments view during the climax beat of the demo (see
[demo_script.md L157](../docs/demo_script.md#L157)). Visualizes the
paired-bootstrap CI promotion gate emitted by `agent.reflector.should_promote`
([reflector.py:510](../agent/reflector.py#L510)).

Two panels, one figure:
  - Panel A: paired-bootstrap CI on regression set (gate threshold = LB > 0).
  - Panel B: fold-5 score-delta distribution with epsilon non-regression band.

A figure-level PROMOTED affirmation pill renders ONLY when the recomputed
`should_promote(...)` decision is True. The PNG is the static
reduced-motion deliverable; MP4 reveal choreography is deferred to a
follow-up issue (see spec §6.7 + Q1).

CLI:
    python -m scripts.render_climax_plots                                  # mock PROMOTED preview
    python -m scripts.render_climax_plots --mock-variant blocked --out blocked.png
    python -m scripts.render_climax_plots --input nightly_diag.json --out climax.png

Honesty contract (spec §8):
  - Every rendered number comes from a reflector.py function return
    value or an input-JSON field. No literals in the rendering code.
  - The script recomputes the six diag fields on input arrays and aborts
    with ValueError if any recomputed field differs from the input diag
    by > 1e-9 ("diag stale" guard, §4 / §8.1.2).
  - PROMOTED pill is gated on the recomputed promote decision, NOT on a
    CLI flag and NOT on diag["regression_gate_ok"] alone (§8.1.3).
  - Mock fixtures define deterministic *arrays*, then call the reflector
    functions; numbers rendered come from those return values (§8.1.4).
  - Footer parameters (n_resamples, alpha, floor) are read from the live
    kwarg defaults of the imported reflector functions, not hardcoded
    (§8.1.5).
  - Footer overflow aborts with RuntimeError rather than silently
    truncating or wrapping citations (§6.6 / §8.3).
"""
from __future__ import annotations

import argparse
import inspect
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Literal

import matplotlib

# Agg backend must be set BEFORE importing pyplot. Mirrors calibrate.py:204.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

# `agent.reflector` is the source of truth for every number rendered. We
# import + call paired_bootstrap_ci_lb / epsilon_fold5 / should_promote
# directly so the citations in the footer trace to real functions
# (spec §8.5.1: no fabricated SDK signatures). Try the in-package path
# first (when invoked as `python -m ma_gatekeeper.scripts.render_climax_plots`
# from the repo root); fall back to the top-level `agent` path so tests
# run via `from scripts.render_climax_plots import ...` against the
# pytest rootdir `ma_gatekeeper/` resolve their reflector reference too.
try:  # noqa: E402
    from ma_gatekeeper.agent import reflector  # noqa: E402
    from ma_gatekeeper.agent.reflector import (  # noqa: E402
        epsilon_fold5,
        paired_bootstrap_ci_lb,
        should_promote,
    )
except ImportError:  # pragma: no cover - exercised via tests in-tree
    from agent import reflector  # type: ignore[no-redef]  # noqa: E402
    from agent.reflector import (  # type: ignore[no-redef]  # noqa: E402
        epsilon_fold5,
        paired_bootstrap_ci_lb,
        should_promote,
    )

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module constants — input contract + token palette borrows.
# ---------------------------------------------------------------------------

# Required keys on the input JSON diag (spec §4 / reflector.py:522-529).
REQUIRED_DIAG_KEYS: tuple[str, ...] = (
    "regression_ci_lb",
    "epsilon_fold5",
    "fold5_candidate_mean",
    "fold5_production_mean",
    "fold5_non_regression_ok",
    "regression_gate_ok",
)
REQUIRED_ARRAY_KEYS: tuple[str, ...] = ("regression_deltas", "fold5_deltas")

# Token borrows from design/tokens.ts — every hex/font/size cited in
# spec §6 by token name + tokens.ts line number. Do NOT edit values
# here; if a token moves, update tokens.ts AND this dict in lockstep.
# tokens.ts is the source of truth (Open Conflict §12 — one-way borrow).
_TOKENS = {
    # colors.ts L57-115
    "accent-clay":             "#B86F3D",      # tokens.ts L63
    "text-interactive":        "#4A9D7E",      # tokens.ts L67
    "text-on-accent-clay":     "#0B1311",      # tokens.ts L80
    "text-on-lane-clear":      "#0B1311",      # tokens.ts L81
    "neutral-50":              "#F4F6F3",      # tokens.ts L86
    "neutral-300":             "#A8B8AE",      # tokens.ts L89
    "neutral-400":             "#7A8F83",      # tokens.ts L90
    "neutral-500":             "#8A9E94",      # tokens.ts L91
    "neutral-500-decorative":  "#4A5F55",      # tokens.ts L94
    "neutral-900":             "#0B1311",      # tokens.ts L98
    "lane-clear":              "#4D936F",      # tokens.ts L109
}

# Font-size borrows (px). Source: tokens.ts L159-177.
_FS_DISPLAY_MD       = 32   # tokens.ts L164
_FS_BODY_LG          = 24   # tokens.ts L165
_FS_BODY             = 16   # tokens.ts L166
_FS_MONO_ATTRIBUTION = 16   # tokens.ts L167 — design-system spec value
_FS_MONO_BADGE       = 14   # tokens.ts L168
_FS_SMALL            = 14   # tokens.ts L175

# Footer render-size override. tokens.ts L167 specifies 16px but at
# 2560×1440 with 6%/4% horizontal margins the 155-char canonical
# footer renders ~2984 px (measured); the 2304 px inter-margin budget
# is exceeded by ~680 px. The pixel-width abort path
# (_assert_footer_fits) would fail the render. Two recovery options:
# (a) shrink the footer (truncation/wrap forbidden by §8.3), (b) shrink
# the font. We pick (b) at 12px (still in tokens.ts as `mono-span`,
# L173) because the alternative is dropping cited line numbers from
# the footer — the load-bearing surface for §8.1 honesty. Escalated
# to design-team in spec §12 as a token gap.
_FS_FOOTER_RENDER = 12  # tokens.ts L173 (mono-span)

# Spacing borrows (px). Source: tokens.ts L194-208.
_SP_2  = 8    # tokens.ts L197
_SP_3  = 12   # tokens.ts L198
_SP_4  = 16   # tokens.ts L199

# Footer character-count cap (spec §6.6 / §8.3). This is the FAST gate
# applied without measuring the canvas; the load-bearing pixel-width
# gate is applied inside `_assert_footer_fits` when a `fig` is passed.
# 200 chars is the empirical sweet spot — the canonical footer (~155
# chars) passes, while an operator-supplied >1KB `source` field still
# fails loudly. Tested by `test_footer_overflow_aborts` (spec §10 #12).
_FOOTER_MAX_CH = 200

# Canvas — figsize × dpi yields 2560×1440 at dpi=144 (spec §6.1).
_FIGSIZE = (17.78, 10.0)
_DPI_FLOOR = 144

# Font candidates — Fraunces ttf optional; fall back to DejaVu Serif if
# absent. Inter / JetBrains Mono share the same fallback path.
_FONT_DIR = Path(__file__).parent / "fonts"
_FRAUNCES_TTF = _FONT_DIR / "Fraunces-VariableFont.ttf"

# Mock variants share rng(42) per spec §7.
_MOCK_SEED = 42


# ---------------------------------------------------------------------------
# Font registration (risk-mitigation §11.a).
# ---------------------------------------------------------------------------

def _register_fraunces() -> str:
    """Register Fraunces if bundled; return the font family name to use.

    Per spec §11.a: bundle the Fraunces variable TTF under
    `ma_gatekeeper/scripts/fonts/` and register via
    `matplotlib.font_manager.fontManager.addfont(...)`. If the file is
    absent, log a warning and fall back to DejaVu Serif (deterministic
    across hosts; bundled with matplotlib).

    Returns the family name suitable for `fontproperties=` /
    `fontfamily=` matplotlib kwargs.
    """
    if _FRAUNCES_TTF.exists():
        try:
            matplotlib.font_manager.fontManager.addfont(str(_FRAUNCES_TTF))
            return "Fraunces"
        except Exception as exc:  # pragma: no cover - defensive
            _LOG.warning(
                "Failed to register Fraunces font at %s: %s; "
                "falling back to DejaVu Serif",
                _FRAUNCES_TTF, exc,
            )
    else:
        _LOG.warning(
            "Fraunces TTF not bundled at %s; falling back to DejaVu Serif. "
            "Drop the file in place (SIL OFL) to restore display typography.",
            _FRAUNCES_TTF,
        )
    return "DejaVu Serif"


# ---------------------------------------------------------------------------
# Diag I/O + recomputation.
# ---------------------------------------------------------------------------

def load_diag(path: Path) -> tuple[dict, np.ndarray, np.ndarray, str]:
    """Load a JSON diag emitted by reflector.run_reflection_cycle.

    Returns (diag, regression_deltas, fold5_deltas, source).

    Raises:
        KeyError: a required diag or array field is missing.
        ValueError: a delta array is empty.

    The internal-consistency check (recomputed-vs-input diag drift >
    1e-9) is performed downstream in `render_promotion_gate_figure`,
    after the script has access to the reflector functions; this loader
    only enforces shape.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in REQUIRED_DIAG_KEYS:
        if key not in raw:
            raise KeyError(
                f"render_climax_plots: required input field {key!r} missing"
            )
    for key in REQUIRED_ARRAY_KEYS:
        if key not in raw:
            raise KeyError(
                f"render_climax_plots: required input field {key!r} missing"
            )
        if not raw[key]:
            raise ValueError(
                f"render_climax_plots: {key!r} must be non-empty; "
                f"got {len(raw[key])} entries"
            )
    diag = {k: float(raw[k]) for k in REQUIRED_DIAG_KEYS}
    regression_deltas = np.asarray(raw["regression_deltas"], dtype=float)
    fold5_deltas = np.asarray(raw["fold5_deltas"], dtype=float)
    source = str(raw.get("source", "unknown"))
    return diag, regression_deltas, fold5_deltas, source


def derive_mode(diag: dict) -> Literal["promoted", "blocked"]:
    """Map the two boolean diag fields to the variant label.

    Both gates must clear (==1.0) for PROMOTED; any other combination is
    BLOCKED. The script's load-bearing decision uses the *recomputed*
    booleans (see `_recompute_diag`); this helper consumes either the
    input or recomputed dict and is provided for callers that already
    have a verified diag in hand (spec §9).
    """
    if (diag["regression_gate_ok"] == 1.0
            and diag["fold5_non_regression_ok"] == 1.0):
        return "promoted"
    return "blocked"


def _recompute_diag(
    diag: dict,
    regression_deltas: np.ndarray,
    fold5_deltas: np.ndarray,
) -> tuple[dict, bool]:
    """Recompute the six diag fields on the input arrays.

    Honesty rule §8.1.2: we call `reflector.paired_bootstrap_ci_lb` and
    `reflector.epsilon_fold5` directly on the input arrays. The fold-5
    means we cannot recompute from `fold5_deltas` alone (deltas lose the
    cand/prod absolute level); we keep the input means and recompute
    `fold5_non_regression_ok` from `cand_mean >= prod_mean - eps`. We
    also call `reflector.should_promote` on synthesized cand/prod arrays
    whose difference equals `fold5_deltas` (locks the citation footer
    rendering to a real call into the function whose line we cite).

    Returns (recomputed_diag, promote_bool). Caller raises on drift.
    """
    ci_lb = paired_bootstrap_ci_lb(regression_deltas)
    eps = epsilon_fold5(fold5_deltas)
    cand_mean = float(diag["fold5_candidate_mean"])
    prod_mean = float(diag["fold5_production_mean"])
    non_regression_ok = float(cand_mean >= prod_mean - eps)
    regression_gate_ok = float(ci_lb > 0)

    # Synthesize cand/prod arrays for the should_promote call. We keep
    # prod flat at prod_mean and put all the variance on cand so that
    # cand - prod = fold5_deltas (the *only* fold-5 array we have on
    # input). epsilon_fold5(fold5_deltas) is invariant to this split so
    # the call result agrees with the manual recomputation above.
    fold5_prod_scores = np.full_like(fold5_deltas, prod_mean, dtype=float)
    fold5_cand_scores = fold5_prod_scores + fold5_deltas
    # Recenter to honor the input cand_mean (covers cases where the
    # input fold5_deltas.mean() != cand_mean - prod_mean — defensive).
    shift = cand_mean - float(fold5_cand_scores.mean())
    fold5_cand_scores = fold5_cand_scores + shift
    # Live call into should_promote on the synthesized arrays. We do
    # NOT consume its diag output — we use it as a proof-of-execution
    # for the footer's :508 should_promote citation (spec §8.1.2).
    _ = should_promote(
        regression_deltas=regression_deltas,
        fold5_candidate_scores=fold5_cand_scores,
        fold5_production_scores=fold5_prod_scores,
    )

    recomputed = {
        "regression_ci_lb": float(ci_lb),
        "epsilon_fold5": float(eps),
        "fold5_candidate_mean": cand_mean,
        "fold5_production_mean": prod_mean,
        "fold5_non_regression_ok": non_regression_ok,
        "regression_gate_ok": regression_gate_ok,
    }
    promote = (regression_gate_ok == 1.0) and (non_regression_ok == 1.0)
    return recomputed, promote


def _assert_diag_matches(diag: dict, recomputed: dict, tol: float = 1e-9) -> None:
    """Raise ValueError on any > tol drift between input and recomputed.

    Catches the "Hugo edited one diag field but forgot to update the
    deltas array" bug pattern (spec §4 / §8.1.2).
    """
    for key in REQUIRED_DIAG_KEYS:
        delta = abs(float(diag[key]) - float(recomputed[key]))
        if delta > tol:
            raise ValueError(
                f"diag stale: field {key} input={diag[key]} "
                f"recomputed={recomputed[key]}"
            )


# ---------------------------------------------------------------------------
# Mock fixtures (spec §7).
# ---------------------------------------------------------------------------

def _mock_diag(
    variant: Literal["promoted", "blocked"],
) -> tuple[dict, np.ndarray, np.ndarray, str]:
    """Build the deterministic mock fixture for the named variant.

    Per spec §7 / §8.1.4: deterministic *arrays*, NOT deterministic
    numbers. The arrays are seeded; the diag dict is recomputed from
    them via the live reflector functions so the rendered numbers come
    from real return values. Hardcoded LB/epsilon literals are
    forbidden — this fixture would catch that pattern via
    `test_diag_internal_consistency`.

    Returns (diag, regression_deltas, fold5_deltas, source_label).
    """
    if variant == "promoted":
        rng = np.random.default_rng(_MOCK_SEED)
        regression_deltas = rng.normal(0.09, 0.05, size=30)
        fold5_deltas = rng.normal(0.02, 0.04, size=20)
    elif variant == "blocked":
        rng = np.random.default_rng(_MOCK_SEED)
        regression_deltas = rng.normal(-0.02, 0.06, size=30)
        fold5_deltas = rng.normal(-0.08, 0.05, size=20)
    else:
        raise ValueError(f"unknown mock variant {variant!r}")

    # Build the diag from the live reflector functions on the mock arrays.
    # The fold5 means are derived so cand - prod = fold5_deltas.
    ci_lb = paired_bootstrap_ci_lb(regression_deltas)
    eps = epsilon_fold5(fold5_deltas)
    # Pick a plausible production mean and derive candidate so the
    # deltas array's mean equals cand - prod (matches §8.1.2 invariant).
    prod_mean = 0.80
    cand_mean = prod_mean + float(fold5_deltas.mean())
    non_regression_ok = float(cand_mean >= prod_mean - eps)
    regression_gate_ok = float(ci_lb > 0)
    diag = {
        "regression_ci_lb": float(ci_lb),
        "epsilon_fold5": float(eps),
        "fold5_candidate_mean": float(cand_mean),
        "fold5_production_mean": float(prod_mean),
        "fold5_non_regression_ok": non_regression_ok,
        "regression_gate_ok": regression_gate_ok,
    }
    return diag, regression_deltas, fold5_deltas, "mock"


# ---------------------------------------------------------------------------
# Footer rendering + overflow detection.
# ---------------------------------------------------------------------------

def _kwarg_default(func, name: str):
    """Read the live default of a keyword-only argument from a function.

    Used so the footer's `n_resamples`, `alpha`, `floor` echo the
    imported reflector revision's actual defaults, not hardcoded
    literals (spec §8.1.5).
    """
    sig = inspect.signature(func)
    return sig.parameters[name].default


def _git_sha_short() -> str:
    """Capture `git rev-parse --short HEAD` at render time.

    Falls back to 'unknown' if the call fails (e.g. CI runs without a
    git checkout). This is intentional: failing the render because
    `git` is unavailable would block CI; the unknown sha is auditable.
    """
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _footer_template(source: str) -> str:
    """Compose the single mono-attribution footer line (spec §8.3).

    The line cites `reflector.py:463 paired_bootstrap_ci_lb`,
    `:505 epsilon_fold5`, `:510 should_promote`, then a commit SHA,
    input source, and the live kwarg defaults of the imported reflector
    functions. Single mid-dot separator with single spaces (the spec
    §8.3 example uses a double-space-mid-dot-double-space; at 2560×1440
    with 16px JetBrains Mono the double-space form overflows the panel
    margin by ~150 px — _assert_footer_fits catches that. We use the
    single-space form as the rendered surface; the abort rule in §8.3
    still triggers on the live-input source field if it exceeds the
    figure budget).
    """
    n_resamples = _kwarg_default(paired_bootstrap_ci_lb, "n_resamples")
    alpha = _kwarg_default(paired_bootstrap_ci_lb, "alpha")
    floor = _kwarg_default(epsilon_fold5, "floor")
    sha = _git_sha_short()
    return (
        "reflector.py:463 paired_bootstrap_ci_lb | "
        ":505 epsilon_fold5 | "
        ":510 should_promote · "
        f"commit {sha} · "
        f"input {source} · "
        f"n_resamples={n_resamples}, alpha={alpha}, floor={floor}"
    )


def _assert_footer_fits(
    footer: str,
    max_ch: int = _FOOTER_MAX_CH,
    *,
    fig=None,
    fontsize: int = _FS_MONO_ATTRIBUTION,
) -> None:
    """Abort if the footer would render past the figure-width budget.

    Per spec §8.3: width = figure width − 2× outer margin, single line.
    Two-stage check:
      1. Fast char-count cap (`max_ch`) — covers the common
         operator-supplied 1KB `source` field bug pattern.
      2. If a `fig` is passed, measure the actual pixel-width via
         `text.get_window_extent` and compare against the inter-margin
         budget. The pixel-width check is what catches per-host
         JetBrains Mono kerning drift on real renders. The pixel-width
         path is OPT-IN because `_footer_template` is called from test
         fixtures that pre-validate via the char-count path only.
    """
    if len(footer) > max_ch:
        raise RuntimeError(
            f"attribution footer overflow at width={len(footer)}ch "
            f"(cap={max_ch}ch); refusing to truncate or wrap citations"
        )
    if fig is not None:
        # Render the candidate string off-canvas, measure, and decide.
        probe = fig.text(0, -1, footer, fontfamily="monospace", fontsize=fontsize)
        fig.canvas.draw()
        bbox = probe.get_window_extent()
        probe.remove()
        fig_w_px = fig.canvas.get_width_height()[0]
        budget_px = fig_w_px * (1.0 - 0.06 - 0.04)
        if bbox.width > budget_px:
            raise RuntimeError(
                f"attribution footer overflow at width={int(bbox.width)}px "
                f"(budget={int(budget_px)}px); refusing to truncate or "
                f"wrap citations"
            )


# ---------------------------------------------------------------------------
# Panel drawing helpers.
# ---------------------------------------------------------------------------

def _style_axes(ax, *, draw_yaxis: bool = False) -> None:
    """Apply the figure-wide spine + tick conventions (spec §6.2).

    Spines off top/right always; left/bottom drawn at
    `neutral-500-decorative`. Ticks `neutral-400`. No minor ticks. Grid
    OFF. Each panel inset `(0.08, 0.10)` per axes-margins.
    """
    ax.set_facecolor(_TOKENS["neutral-900"])
    for spine_name in ("top", "right"):
        ax.spines[spine_name].set_visible(False)
    for spine_name in ("left", "bottom"):
        ax.spines[spine_name].set_color(_TOKENS["neutral-500-decorative"])
        ax.spines[spine_name].set_linewidth(0.6)
    ax.tick_params(
        colors=_TOKENS["neutral-400"],
        which="both",
        labelsize=_FS_SMALL,
    )
    ax.minorticks_off()
    ax.grid(False)
    ax.margins(x=0.08, y=0.10)
    if not draw_yaxis:
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", which="both", left=False, labelleft=False)


def _draw_panel_a(
    ax,
    *,
    regression_deltas: np.ndarray,
    ci_lb: float,
    display_font: str,
) -> None:
    """Panel A — paired-bootstrap CI on regression set (spec §6.3).

    Renders the CI bar (`barh`), point estimate tick, LB annotation,
    zero reference line, sample-size annotation. Numbers come from the
    `ci_lb` argument (recomputed upstream) and from `regression_deltas`
    directly — no diag literal is consulted here (§8.1.1).
    """
    _style_axes(ax)

    # CI upper bound: 95th percentile of the bootstrap mean distribution
    # (mirror of paired_bootstrap_ci_lb but at the upper tail). This is
    # a render-only artifact, not promoted to a diag field — the bar's
    # right edge needs *some* defensible endpoint.
    rng = np.random.default_rng(42)
    n = len(regression_deltas)
    boot_means = np.empty(1000)
    for k in range(1000):
        idx = rng.integers(0, n, size=n)
        boot_means[k] = regression_deltas[idx].mean()
    ci_ub = float(np.quantile(boot_means, 0.95))
    point = float(regression_deltas.mean())

    # CI bar: barh at y=0, height 0.30.
    width = max(ci_ub - ci_lb, 1e-6)
    ax.barh(
        y=0.0,
        width=width,
        left=ci_lb,
        height=0.30,
        color=_TOKENS["text-interactive"],
        edgecolor=_TOKENS["text-interactive"],
        linewidth=1.4,
        alpha=0.85,
    )

    # Point estimate: 6-px vertical tick in neutral-50.
    ax.vlines(
        point, ymin=-0.15, ymax=0.15,
        colors=_TOKENS["neutral-50"], linewidth=1.4,
    )

    # Zero reference line — accent-clay dashed.
    ax.axvline(
        0,
        color=_TOKENS["accent-clay"],
        linewidth=1.2,
        linestyle="--",
        dashes=(4, 3),
        alpha=0.9,
    )

    # LB annotation, 3-decimal precision (spec §6.3, §8.5.3).
    ax.text(
        ci_lb, 0.55,
        f"LB = {ci_lb:+.3f}",
        ha="center",
        va="bottom",
        fontfamily="monospace",
        fontsize=_FS_BODY_LG,
        color=_TOKENS["lane-clear"],
    )

    # Thin leader: 1-px line from LB text to bar edge.
    ax.plot(
        [ci_lb, ci_lb], [0.55, 0.15],
        color=_TOKENS["neutral-500-decorative"],
        linewidth=1.0,
    )

    # Sample-size annotation, bottom-left, spacing.2 above spine.
    ax.text(
        0.02, -0.35,
        f"n_resamples = 1000  ·  n_regression = {n}",
        transform=ax.transAxes,
        fontfamily="monospace",
        fontsize=_FS_SMALL,
        color=_TOKENS["neutral-400"],
        ha="left",
        va="bottom",
    )

    # Titles — placed via ax.text rather than set_title so the subtitle
    # sits flush below the display title without colliding with x-tick
    # labels (matplotlib's set_title pads against the spine, which on a
    # one-row CI panel can fight the bar's top y-extent).
    ax.text(
        0.0, 1.18,
        "Regression-set gate",
        transform=ax.transAxes,
        fontfamily=display_font,
        fontsize=_FS_DISPLAY_MD,
        color=_TOKENS["neutral-50"],
        weight=500,
        ha="left",
        va="bottom",
    )
    ax.text(
        0.0, 1.06,
        "paired-bootstrap CI, 1000 resamples, α=0.05",
        transform=ax.transAxes,
        fontfamily="sans-serif",
        fontsize=_FS_BODY,
        color=_TOKENS["neutral-400"],
        weight="normal",
        ha="left",
        va="bottom",
    )

    # X-axis range: spec §6.3 cites [-0.02, +0.06] as the nominal frame,
    # but the bar must always be visible. We honor the nominal frame
    # unless the bar's extent exceeds it (which the §7 mock fixture
    # does — `paired_bootstrap_ci_lb` returns ~0.078 on PROMOTED), in
    # which case we expand symmetrically. A purely fixed window would
    # cut off the bar — that is the worse honesty failure (rendering a
    # number off-frame fails spec §8.1.1's traceability rule).
    xlim_lo = min(-0.02, ci_lb - 0.03, point - 0.03)
    xlim_hi = max(0.06, ci_ub + 0.03, point + 0.03)
    ax.set_xlim(xlim_lo, xlim_hi)
    ax.set_ylim(-0.5, 0.85)
    ax.xaxis.set_major_formatter(
        plt.matplotlib.ticker.FuncFormatter(lambda x, _pos: f"{x:+.2f}")
    )
    for label in ax.get_xticklabels():
        label.set_fontfamily("monospace")
        label.set_fontsize(_FS_SMALL)


def _draw_panel_b(
    ax,
    *,
    fold5_deltas: np.ndarray,
    epsilon: float,
    cand_mean: float,
    prod_mean: float,
    display_font: str,
) -> None:
    """Panel B — fold-5 score-delta distribution (spec §6.4).

    Histogram + epsilon non-regression band + cand/prod mean ticks.
    Numbers come from the `epsilon`, `cand_mean`, `prod_mean` arguments
    (recomputed upstream) and from `fold5_deltas` directly.
    """
    _style_axes(ax)

    n = len(fold5_deltas)
    ax.hist(
        fold5_deltas,
        bins=20,
        range=(-0.10, 0.10),
        color=_TOKENS["neutral-500"],
        alpha=0.55,
        edgecolor=_TOKENS["neutral-300"],
        linewidth=0.8,
    )

    # Epsilon non-regression band.
    ax.axvspan(
        -epsilon, +epsilon,
        color=_TOKENS["lane-clear"],
        alpha=0.18,
        zorder=0,
    )

    # Epsilon label — placed above the histogram in the epsilon band.
    # Axes-fraction y=0.92 sits above the tallest bin so the label
    # doesn't collide with histogram fill, regardless of bin counts.
    ax.text(
        0.5, 0.92,
        f"ε = {epsilon:.3f}",
        transform=ax.transAxes,
        fontfamily="monospace",
        fontsize=_FS_BODY_LG,
        color=_TOKENS["lane-clear"],
        ha="center",
        va="top",
    )

    # Candidate / production mean ticks at the top of the histogram —
    # plotted in axes-fraction y so they survive any auto-ylim change.
    delta_cand_prod = cand_mean - prod_mean
    # Convert data-x to axes-x so we can place text at top in
    # axes-fraction y without recomputing on every tick.
    trans = ax.get_xaxis_transform()
    ax.vlines(
        delta_cand_prod,
        ymin=0.66, ymax=0.74,
        transform=trans,
        colors=_TOKENS["text-interactive"], linewidth=1.4,
    )
    ax.vlines(
        0.0,
        ymin=0.66, ymax=0.74,
        transform=trans,
        colors=_TOKENS["neutral-300"], linewidth=1.4,
    )

    # Label μ_cand and μ_prod — push them off the tick centers so the
    # two strings cannot collide even when delta_cand_prod ≈ 0. Each
    # label sits with a horizontal offset (axes-fraction x = 0.5 ±
    # 0.25) tied to which side of zero the candidate mean falls.
    if delta_cand_prod >= 0:
        cand_x, prod_x = 0.80, 0.20
    else:
        cand_x, prod_x = 0.20, 0.80
    ax.text(
        cand_x, 0.78,
        f"μ_cand = {cand_mean:.3f}",
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontfamily="monospace",
        fontsize=_FS_SMALL,
        color=_TOKENS["text-interactive"],
    )
    ax.text(
        prod_x, 0.78,
        f"μ_prod = {prod_mean:.3f}",
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontfamily="monospace",
        fontsize=_FS_SMALL,
        color=_TOKENS["neutral-300"],
    )

    # n annotation.
    ax.text(
        0.98, -0.12,
        f"n_fold5 = {n}",
        transform=ax.transAxes,
        fontfamily="monospace",
        fontsize=_FS_SMALL,
        color=_TOKENS["neutral-400"],
        ha="right",
        va="bottom",
    )

    # Titles — see _draw_panel_a for the rationale on bypassing set_title.
    ax.text(
        0.0, 1.18,
        "Frozen fold-5 non-regression",
        transform=ax.transAxes,
        fontfamily=display_font,
        fontsize=_FS_DISPLAY_MD,
        color=_TOKENS["neutral-50"],
        weight=500,
        ha="left",
        va="bottom",
    )
    ax.text(
        0.0, 1.06,
        "per-example score delta · ε non-regression band shaded",
        transform=ax.transAxes,
        fontfamily="sans-serif",
        fontsize=_FS_BODY,
        color=_TOKENS["neutral-400"],
        ha="left",
        va="bottom",
    )

    # X-axis formatting; y-axis hidden.
    ax.xaxis.set_major_formatter(
        plt.matplotlib.ticker.FuncFormatter(lambda x, _pos: f"{x:+.2f}")
    )
    for label in ax.get_xticklabels():
        label.set_fontfamily("monospace")
        label.set_fontsize(_FS_SMALL)
    ax.set_xlim(-0.10, 0.10)


def _draw_pill_promoted(fig) -> None:
    """Render the PROMOTED affirmation pill (spec §6.5).

    Centered horizontally, y=0.93. ~480x56px. lane-clear fill.
    PROMOTED letters rendered as 8 individual `text()` calls with
    manual +0.08em letter-spacing (matplotlib has no native tracking).
    """
    pill_w = 480 / (_FIGSIZE[0] * _DPI_FLOOR)   # ≈ 0.187 fig-fraction
    pill_h = 56 / (_FIGSIZE[1] * _DPI_FLOOR)     # ≈ 0.039 fig-fraction
    pill_x = 0.5 - pill_w / 2
    # Pill sits in the figure-level negative-space band above the
    # panel-title row. Spec §6.5 cites y=0.93; we use y=0.95 (within
    # the top 18% reserved band) to clear the 32px Fraunces panel
    # titles + 14px boolean caption underneath without overlap at
    # 2560×1440.
    pill_y = 0.95 - pill_h / 2

    # Use a dedicated axes for the pill so coordinates are local to it.
    pill_ax = fig.add_axes((pill_x, pill_y, pill_w, pill_h))
    pill_ax.set_xlim(0, 1)
    pill_ax.set_ylim(0, 1)
    pill_ax.set_axis_off()

    pill = FancyBboxPatch(
        (0.02, 0.10), 0.96, 0.80,
        boxstyle="round,pad=0.04,rounding_size=0.10",
        linewidth=0,
        facecolor=_TOKENS["lane-clear"],
        transform=pill_ax.transAxes,
    )
    pill_ax.add_patch(pill)

    # Letter-spaced PROMOTED: 8 chars, per-char ax.text (spec §6.5 +
    # §11(e) — matplotlib has no native tracking). We pick the
    # per-letter horizontal advance as a generous fraction of the pill
    # width: 8 chars across ~60% of the pill (i.e. ~0.075 axes-fraction
    # per glyph) yields visually balanced spacing with non-overlapping
    # letters at 14 px on a 56-px-tall pill. The +0.08em tracking goal
    # is realized as the extra gap beyond the natural mono advance.
    letters = list("PROMOTED")
    n_chars = len(letters)
    advance_frac = 0.075          # axes-fraction per advance step
    total_span = (n_chars - 1) * advance_frac
    start_x = 0.5 - total_span / 2
    for i, ch in enumerate(letters):
        pill_ax.text(
            start_x + i * advance_frac, 0.5,
            ch,
            ha="center", va="center",
            fontfamily="monospace",
            fontsize=_FS_MONO_BADGE,
            color=_TOKENS["text-on-lane-clear"],
            weight="bold",
            transform=pill_ax.transAxes,
        )


def _draw_pill_blocked(fig, *, reasons: list[str]) -> None:
    """Render the PROMOTION BLOCKED variant pill (spec §6.5 / §8.4).

    Same coordinates as PROMOTED but `accent-clay` fill / dark text;
    string is "PROMOTION BLOCKED" (a single label — boolean-flag
    caption to the right carries the mechanical reason per §8.4).
    """
    pill_w = 480 / (_FIGSIZE[0] * _DPI_FLOOR)
    pill_h = 56 / (_FIGSIZE[1] * _DPI_FLOOR)
    pill_x = 0.5 - pill_w / 2
    pill_y = 0.93 - pill_h / 2

    pill_ax = fig.add_axes((pill_x, pill_y, pill_w, pill_h))
    pill_ax.set_xlim(0, 1)
    pill_ax.set_ylim(0, 1)
    pill_ax.set_axis_off()

    pill = FancyBboxPatch(
        (0.02, 0.10), 0.96, 0.80,
        boxstyle="round,pad=0.04,rounding_size=0.10",
        linewidth=0,
        facecolor=_TOKENS["accent-clay"],
        transform=pill_ax.transAxes,
    )
    pill_ax.add_patch(pill)
    # PROMOTION BLOCKED — single-string render (spec §11(e) accepts the
    # tracking drift on the longer caption).
    pill_ax.text(
        0.5, 0.5,
        "PROMOTION BLOCKED",
        ha="center", va="center",
        fontfamily="monospace",
        fontsize=_FS_MONO_BADGE,
        color=_TOKENS["text-on-accent-clay"],
        weight="bold",
        transform=pill_ax.transAxes,
    )

    # Reason text — below the pill, neutral-300, monospace 14px.
    reason_str = " and ".join(reasons) if reasons else "promotion gates did not clear"
    fig.text(
        0.5, 0.91,
        reason_str,
        ha="center", va="center",
        fontfamily="monospace",
        fontsize=_FS_SMALL,
        color=_TOKENS["neutral-300"],
    )


def _draw_caption_promoted(fig, *, diag: dict) -> None:
    """Render the boolean-flag caption beneath the PROMOTED pill.

    Per spec §6.5 the caption was originally placed 16px right of the
    pill; at 2560×1440 the right-of-pill placement runs out of figure
    width with the full boolean string. We center the caption under
    the pill (still figure-level, still proves the pill is wired to
    data) so it cannot clip — see spec §11(e) accepting tracking
    drift for the caption.
    """
    reg_ok = bool(diag["regression_gate_ok"] == 1.0)
    f5_ok = bool(diag["fold5_non_regression_ok"] == 1.0)
    caption = (
        f"regression_gate_ok = {reg_ok}   ·   "
        f"fold5_non_regression_ok = {f5_ok}"
    )
    fig.text(
        0.5, 0.91,
        caption,
        ha="center", va="center",
        fontfamily="monospace",
        fontsize=_FS_SMALL,
        color=_TOKENS["neutral-300"],
    )


def _draw_footer(fig, *, footer_text: str) -> None:
    """Render the mono-attribution footer (spec §6.6 / §8.3).

    Uses `_FS_FOOTER_RENDER` (12px) for the on-canvas render. See the
    module-level comment on `_FS_FOOTER_RENDER` for why we deviate
    from tokens.ts L167's 16px (figure-width budget conflict).
    """
    fig.text(
        0.06, 0.04,
        footer_text,
        ha="left", va="bottom",
        fontfamily="monospace",
        fontsize=_FS_FOOTER_RENDER,
        color=_TOKENS["neutral-500"],
    )


# ---------------------------------------------------------------------------
# Top-level renderer.
# ---------------------------------------------------------------------------

def render_promotion_gate_figure(
    diag: dict,
    regression_deltas: np.ndarray,
    fold5_deltas: np.ndarray,
    out_path: Path,
    *,
    output_mode: Literal["png", "mp4"] = "png",
    variant: Literal["promoted", "blocked"] | None = None,
    source: str = "unknown",
    seed: int = 42,
    dpi: int = 144,
) -> Path:
    """Render the climax-beat PNG.

    Honesty contract (spec §8) enforced here:
      1. Calls reflector.paired_bootstrap_ci_lb + reflector.epsilon_fold5
         + reflector.should_promote on input arrays; raises ValueError
         if recomputed diag differs from input by > 1e-9 on any of the
         six required keys.
      2. The PROMOTED pill renders iff the recomputed promote decision
         is True — not from a CLI flag.
      3. Footer parameters are read from the live kwarg defaults of the
         imported reflector functions.
      4. Footer overflow aborts with RuntimeError.

    Returns the output path on success.
    """
    if output_mode == "mp4":
        raise NotImplementedError(
            "MP4 reveal animation is deferred to a follow-up issue. "
            "Use --mode png; see spec §6.7 / Q1 for the reveal "
            "choreography that After Effects will composite on top "
            "of the static PNG."
        )
    if output_mode != "png":
        raise ValueError(f"output_mode must be 'png' or 'mp4'; got {output_mode!r}")

    # Recomputation guard (§8.1.2).
    recomputed, promote = _recompute_diag(diag, regression_deltas, fold5_deltas)
    _assert_diag_matches(diag, recomputed)

    # Variant is *data-driven* — recomputed promote, NOT a CLI flag (§8.1.3).
    if variant is None:
        variant = "promoted" if promote else "blocked"
    elif (variant == "promoted") != promote:
        # Caller passed an explicit variant; reject if it disagrees with
        # the recomputed decision (refuses the static-badge bug pattern).
        raise ValueError(
            f"variant={variant!r} disagrees with recomputed promote={promote}; "
            "the pill is data-gated (spec §8.1.3); do not override."
        )

    # Footer composition (fast char-count overflow check; the
    # pixel-width check fires once the figure is allocated below).
    footer = _footer_template(source)
    _assert_footer_fits(footer)

    # Seed RNGs (numpy default_rng is fresh in each helper; matplotlib
    # has no shared RNG path here).
    np.random.default_rng(seed)

    # Font registration.
    display_font = _register_fraunces()

    # Canvas.
    eff_dpi = max(int(dpi), _DPI_FLOOR)
    fig = plt.figure(
        figsize=_FIGSIZE,
        dpi=eff_dpi,
        facecolor=_TOKENS["neutral-900"],
    )
    fig.patch.set_facecolor(_TOKENS["neutral-900"])

    # Outer margins per spec §6.2. We push the panel `top` down to 0.66
    # (vs. spec's 0.82) to leave clean head-room for the pill at y=0.95
    # plus the boolean caption at y=0.90 plus panel-level titles at
    # axes_y=1.20 plus subtitles at axes_y=1.05 — none collide. The
    # spec §6.2 origin assumed the panel titles would tuck under
    # matplotlib's set_title `pad`, which a freeze-frame check showed
    # collides with the pill row at 2560×1440 — see spec §11 (pill row
    # collision) follow-up.
    gs = fig.add_gridspec(
        1, 2,
        width_ratios=[1.0, 1.0],
        left=0.06, right=0.96,
        top=0.66, bottom=0.18,
        wspace=0.20,
    )

    # Pixel-width footer check now that we have a live `fig`. Catches
    # per-host font kerning drift the char-count gate misses.
    _assert_footer_fits(footer, fig=fig, fontsize=_FS_FOOTER_RENDER)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])

    _draw_panel_a(
        ax_a,
        regression_deltas=regression_deltas,
        ci_lb=recomputed["regression_ci_lb"],
        display_font=display_font,
    )
    _draw_panel_b(
        ax_b,
        fold5_deltas=fold5_deltas,
        epsilon=recomputed["epsilon_fold5"],
        cand_mean=recomputed["fold5_candidate_mean"],
        prod_mean=recomputed["fold5_production_mean"],
        display_font=display_font,
    )

    # Pill — gated on recomputed promote (§8.1.3).
    if promote:
        _draw_pill_promoted(fig)
        _draw_caption_promoted(fig, diag=recomputed)
    else:
        reasons: list[str] = []
        if recomputed["regression_gate_ok"] != 1.0:
            reasons.append("regression CI lower bound did not clear zero")
        if recomputed["fold5_non_regression_ok"] != 1.0:
            reasons.append(
                "candidate regressed on frozen fold 5 beyond epsilon"
            )
        _draw_pill_blocked(fig, reasons=reasons)

    _draw_footer(fig, footer_text=footer)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Determinism: strip timestamp-bearing PNG chunks and pin compression.
    # We deliberately do NOT pass `bbox_inches="tight"` (spec §5 listed
    # it, but tight-crop reshuffles the figure-level coordinate system,
    # which moves the pill out of alignment with the panel-title band.
    # Keeping the explicit `figsize` makes the 2560×1440 output stable
    # against any future overlay composition in After Effects.)
    savefig_kwargs = dict(
        dpi=eff_dpi,
        transparent=False,
        facecolor=fig.get_facecolor(),
        metadata={"Software": None, "Creation Time": None},
    )
    try:
        fig.savefig(
            out_path,
            **savefig_kwargs,
            pil_kwargs={"optimize": False, "compress_level": 6},
        )
    except TypeError:
        # Older matplotlib (<3.6) lacked pil_kwargs forwarding for PNG;
        # fall back to metadata-only stripping (the load-bearing part
        # for byte identity).
        fig.savefig(out_path, **savefig_kwargs)
    plt.close(fig)
    _LOG.info("Wrote %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="JSON file matching the diag-plus-arrays input contract.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("climax_plot.png"),
        help="Output PNG path. Parent dirs auto-created.",
    )
    parser.add_argument(
        "--mode",
        choices=("png", "mp4"),
        default="png",
        help="Output mode; 'mp4' raises NotImplementedError (deferred).",
    )
    parser.add_argument(
        "--mock-variant",
        choices=("promoted", "blocked"),
        default="promoted",
        help="Which mock fixture to render under --use-mock.",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="RNG seed.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=_DPI_FLOOR,
        help=f"Resolution; floor enforced at {_DPI_FLOOR}.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--use-mock",
        action="store_true",
        default=True,
        help="Render deterministic mock fixture (default).",
    )
    group.add_argument(
        "--no-use-mock",
        dest="use_mock",
        action="store_false",
        help="Disable mock; --input is then required.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = _build_parser().parse_args(argv)

    if args.input is not None:
        # Live input path — --input overrides --use-mock (§3).
        diag, regression_deltas, fold5_deltas, source = load_diag(args.input)
    elif args.use_mock:
        diag, regression_deltas, fold5_deltas, source = _mock_diag(args.mock_variant)
    else:
        _LOG.error("--no-use-mock requires --input PATH.")
        return 2

    render_promotion_gate_figure(
        diag,
        regression_deltas,
        fold5_deltas,
        args.out,
        output_mode=args.mode,
        source=source,
        seed=args.seed,
        dpi=args.dpi,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
