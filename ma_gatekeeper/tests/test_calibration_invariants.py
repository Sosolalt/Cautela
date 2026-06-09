"""Calibration quiet-downgrade invariants (Phase 5 E10 audit).

The math in scripts/calibrate.py is correct today. These tests pin five
properties that would silently degrade the headline Block-recall number
if any of the following bug patterns landed unnoticed:

  1. Wilson z=1.96 (two-sided 95% / one-sided 97.5%) restored over the
     correct one-sided 95% z=1.6449. Silently inflates conservatism.
  2. ``np.quantile(means, alpha/2)`` replacing ``np.quantile(means, alpha)``
     in the cluster bootstrap. Silently flips one-sided into two-sided.
  3. ``calibrate_fold`` default ``require_recall`` relaxed from 1.0 to 0.95
     (or below), silently relaxing the headline Block-recall gate.
  4. ``plot_reliability`` regressing to a degenerate step function
     (``hits = (score >= tau)`` over the Block-only subset).
  5. Folds silently dropped from headline aggregation without surfacing
     which folds contributed to the headline number.

Numeric pins below were verified against the live function output.
Tolerance 5e-5 catches any plausible z or alpha drift; the calibrated
gap between the correct value and the round-A bug values is >0.030
for every Wilson row and >0.025 for the bootstrap quantile pin.
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.calibrate import (
    HEADLINE_FOLDS,
    TAU_GRID,
    Z_ONE_SIDED_95,
    calibrate_all_headline_folds,
    calibrate_fold,
    cluster_bootstrap_recall_ci,
    plot_reliability,
    wilson_lb_one_sided,
)


# ============================================================================
# 1. Wilson LB by-(k, n) pinned values.
# ============================================================================

# Each row: (k, n, expected_lb_z_1p6449, expected_lb_z_1p96).
# Both columns verified against wilson_lb_one_sided() in calibrate.py.
# Min gap across rows is 0.0307 — well outside the 5e-5 pin tolerance,
# so a silent z=1.96 revert fails every row with >600x-tolerance margin.
WILSON_PINS = [
    (5,  5,  0.6488707, 0.5655085),
    (10, 10, 0.7870486, 0.7224598),
    (8,  10, 0.5407852, 0.4901568),
    (19, 20, 0.8039870, 0.7638641),
    (24, 24, 0.8986847, 0.8620194),
    (27, 30, 0.7744931, 0.7437856),
]


@pytest.mark.parametrize("k,n,expected_lb,_lb_z196", WILSON_PINS)
def test_wilson_lb_pinned(k: int, n: int, expected_lb: float, _lb_z196: float):
    """Pin Wilson one-sided 95% LB output to 5 decimals.

    A silent revert to Z_ONE_SIDED_95=1.96 (round-A bug pattern) would
    push every row's LB down by >=0.030, triggering this assertion with
    a calibrated quantitative margin.
    """
    got = wilson_lb_one_sided(k, n)
    assert got == pytest.approx(expected_lb, abs=5e-5), (
        f"wilson_lb_one_sided({k}, {n}) = {got:.7f} differs from "
        f"pinned {expected_lb:.7f}. Was Z_ONE_SIDED_95 silently changed "
        f"(e.g. 1.96 two-sided revert)? See WILSON_PINS at module top."
    )


@pytest.mark.parametrize("k,n,expected_lb,lb_z196", WILSON_PINS)
def test_wilson_lb_distinguishable_from_two_sided(
    k: int, n: int, expected_lb: float, lb_z196: float,
):
    """Anti-revert assertion: the one-sided LB and the would-be z=1.96 LB
    are separated by >0.020 on every row. If someone restores 1.96 the
    function output collapses to ``lb_z196``, which is < expected_lb - 0.020.
    """
    assert expected_lb - lb_z196 > 0.020, (
        f"WILSON_PINS row ({k}, {n}) has too-narrow z-gap "
        f"{expected_lb - lb_z196:.6f}; update the fixture."
    )
    got = wilson_lb_one_sided(k, n)
    # The function output must be closer to the one-sided pin than to
    # the z=1.96 pin — a "which side of the gap" assertion.
    assert abs(got - expected_lb) < abs(got - lb_z196)


def test_wilson_constant_is_one_sided_95():
    """Defense in depth on Z_ONE_SIDED_95 itself."""
    assert abs(Z_ONE_SIDED_95 - 1.6449) < 5e-5
    # Hard upper bound: would catch any z >= 1.70 (so z=1.96 fails here too).
    assert Z_ONE_SIDED_95 < 1.70


def test_wilson_lb_perfect_recall_below_one():
    """Wilson exploratory-IID pin: k=n=24 must stay strictly below 1.0,
    and at the documented 0.8986847 value. Per Fix 10 the Wilson LB is
    now the exploratory per-finding-IID statistic (not the headline —
    cluster bootstrap is); the numeric pin remains byte-stable because
    `wilson_lb_one_sided`'s signature/math is unchanged. A bug that
    clamps LB to k/n would silently push the value to 1.000.
    """
    lb = wilson_lb_one_sided(24, 24)
    assert lb < 1.0
    assert lb == pytest.approx(0.8986847, abs=5e-5)


# ============================================================================
# 2. Cluster bootstrap alpha recovered-quantile.
# ============================================================================

def test_cluster_bootstrap_alpha_default_is_0p05():
    """Default ``alpha`` must remain 0.05 (one-sided 95%). A silent
    default flip to 0.025 would tighten the LB upward (two-sided 95%).
    """
    sig = inspect.signature(cluster_bootstrap_recall_ci)
    assert sig.parameters["alpha"].default == 0.05


def _bootstrap_fixture_40_contracts():
    """40 contracts: 30 with hits=[1,1] and 10 with hits=[0,0]. The
    cluster-resample distribution of means has well-separated quantiles
    (verified against the live function with seed=42, n_resamples=5000):
        q_0.025 = 0.600
        q_0.05  = 0.625
        q_0.95  = 0.850
    Gap q_0.05 vs q_0.025 = 0.025 (catches alpha->alpha/2 bug).
    """
    contracts = [f"c{i}" for i in range(40)]
    hits_by_contract = {c: [1, 1] for c in contracts[:30]}
    for c in contracts[30:]:
        hits_by_contract[c] = [0, 0]
    per_fold_hits = [[h for c in contracts for h in hits_by_contract[c]]]
    per_fold_contracts = [[c for c in contracts for _ in hits_by_contract[c]]]
    return contracts, hits_by_contract, per_fold_hits, per_fold_contracts


def test_cluster_bootstrap_lb_matches_empirical_fifth_percentile():
    """LB equals the empirical 5th percentile of the resample distribution
    within a numerical tie. A silent ``alpha/2`` revert (the round-A bug)
    would push LB down by 0.025 on this fixture — comfortably outside
    any reasonable tolerance.

    Computes the recomputation by hand with the same seed and asserts
    `lb == np.quantile(means, 0.05)` exactly.
    """
    contracts, hits_by_contract, per_fold_hits, per_fold_contracts = (
        _bootstrap_fixture_40_contracts()
    )

    point, lb = cluster_bootstrap_recall_ci(
        per_fold_hits, per_fold_contracts,
        n_resamples=5000, alpha=0.05, seed=42,
    )
    assert point == pytest.approx(0.75, abs=1e-9)

    rng = np.random.default_rng(42)
    means = np.empty(5000)
    for k in range(5000):
        idx = rng.integers(0, len(contracts), size=len(contracts))
        pooled = []
        for j in idx:
            pooled.extend(hits_by_contract[contracts[j]])
        means[k] = float(np.mean(pooled))

    q_025 = float(np.quantile(means, 0.025))
    q_05 = float(np.quantile(means, 0.05))
    q_95 = float(np.quantile(means, 0.95))

    # The recomputation matches the live distribution: q_0.025=0.600,
    # q_0.05=0.625, q_0.95=0.850.
    assert q_025 == pytest.approx(0.600, abs=1e-9)
    assert q_05 == pytest.approx(0.625, abs=1e-9)
    assert q_95 == pytest.approx(0.850, abs=1e-9)

    # The function returned q_0.05 — neither the two-sided LB nor the UB.
    assert lb == pytest.approx(q_05, abs=1e-9), (
        f"cluster_bootstrap_recall_ci returned LB={lb:.6f} but the "
        f"empirical 5th percentile is {q_05:.6f}. q_0.025={q_025:.6f} "
        f"(alpha/2 bug pattern), q_0.95={q_95:.6f}. Was alpha silently "
        f"halved or replaced with 1-alpha?"
    )
    assert q_05 - q_025 > 0.020
    assert q_95 - q_05 > 0.10


def test_cluster_bootstrap_alpha_half_revert_yields_different_value():
    """Test-for-the-test: re-run the same fixture with alpha=0.025 and
    confirm the function returns the q_0.025 quantile (0.600, lower than
    the correct 0.625). This documents the bug pattern that the
    previous test rejects.
    """
    _, _, per_fold_hits, per_fold_contracts = _bootstrap_fixture_40_contracts()

    _, lb_correct = cluster_bootstrap_recall_ci(
        per_fold_hits, per_fold_contracts,
        n_resamples=5000, alpha=0.05, seed=42,
    )
    _, lb_buggy = cluster_bootstrap_recall_ci(
        per_fold_hits, per_fold_contracts,
        n_resamples=5000, alpha=0.025, seed=42,
    )

    assert lb_correct == pytest.approx(0.625, abs=1e-9)
    assert lb_buggy == pytest.approx(0.600, abs=1e-9)
    # The alpha/2 path is strictly more conservative, i.e. lower LB.
    assert lb_buggy < lb_correct
    assert lb_correct - lb_buggy > 0.020


# ============================================================================
# 3. ``require_recall`` parameter — no silent gate relaxation.
# ============================================================================

def test_calibrate_fold_default_require_recall_is_one():
    """``calibrate_fold(require_recall=...)`` default must remain 1.0.
    A silent flip to 0.95 would relax the headline gate everywhere it's
    called without an explicit argument (including main()'s headline loop).
    """
    sig = inspect.signature(calibrate_fold)
    assert sig.parameters["require_recall"].default == 1.0


def _calibratable_train_df(
    *, n_block_at_high: int, n_block_below_floor: int,
) -> pd.DataFrame:
    """Synthetic frame:
      - 20 non-blocks at (h=0.95, f=0.95) — pass every grid point.
      - ``n_block_at_high`` blocks at (h=0.85, f=0.85) — pass (tau<=0.85).
      - ``n_block_below_floor`` blocks at (h=0.40, f=0.40) — BELOW the
        0.50 grid floor, so NO grid point in TAU_GRID can include them.

    Construction guarantees Block-recall at any (tau_h, tau_f) on TAU_GRID:
      n_block_at_high / (n_block_at_high + n_block_below_floor)
    iff tau_h <= 0.85 and tau_f <= 0.85; lower otherwise.
    """
    assert TAU_GRID[0] == pytest.approx(0.50, abs=1e-9), \
        "TAU_GRID floor changed — update _calibratable_train_df."
    rows: list[dict] = []
    for i in range(20):
        rows.append({"contract_id": f"nb_{i}", "source": "x",
                     "h_score": 0.95, "f_score": 0.95, "is_block": False})
    for i in range(n_block_at_high):
        rows.append({"contract_id": f"bh_{i}", "source": "x",
                     "h_score": 0.85, "f_score": 0.85, "is_block": True})
    for i in range(n_block_below_floor):
        rows.append({"contract_id": f"bl_{i}", "source": "x",
                     "h_score": 0.40, "f_score": 0.40, "is_block": True})
    return pd.DataFrame(rows)


def test_calibrate_fold_returns_thresholds_when_perfect_achievable():
    """All blocks pass at (tau_h, tau_f) <= (0.85, 0.85). Tie-break
    'prefer higher tau_h' picks tau_h=0.85; the minimum-abstention
    tau_f at that row is 0.50 (lowest grid value — non-blocks pass
    everywhere). Expected: (0.85, 0.50).
    """
    train = _calibratable_train_df(n_block_at_high=5, n_block_below_floor=0)
    res = calibrate_fold(train, require_recall=1.0)
    assert res is not None
    tau_h, tau_f = res
    assert tau_h == pytest.approx(0.85, abs=1e-9)
    assert tau_f == pytest.approx(0.50, abs=1e-9)


def test_calibrate_fold_returns_none_when_recall_1_unachievable():
    """At least one block sits below the 0.50 grid floor. NO grid point
    achieves Block-recall=1.0 — function MUST return None, never an
    auto-fallback to a lower require_recall.
    """
    train = _calibratable_train_df(n_block_at_high=3, n_block_below_floor=1)
    assert calibrate_fold(train, require_recall=1.0) is None


def test_calibrate_fold_with_lowered_recall_finds_pair_on_same_frame():
    """Test-for-the-test: the same unachievable-at-1.0 frame DOES find
    a feasible (tau_h, tau_f) at require_recall=0.75 (3 of 4 blocks
    pass at high tau). Confirms the gate is the real constraint, not
    a spurious empty grid.
    """
    train = _calibratable_train_df(n_block_at_high=3, n_block_below_floor=1)
    res = calibrate_fold(train, require_recall=0.75)
    assert res is not None


# ============================================================================
# 4. ``plot_reliability`` content — anti-degenerate-step regression.
# ============================================================================

class _AxRecorder:
    """Standalone recorder masquerading as a matplotlib Axes.

    Records the arguments to every method the plot_reliability code path
    calls. Avoids golden-image byte comparisons (notoriously brittle
    across matplotlib versions) by intercepting the structural calls
    instead.
    """
    def __init__(self) -> None:
        self.bar_calls: list[tuple] = []
        self.plot_calls: list[tuple] = []
        self.text_calls: list[tuple] = []
        self.title: str = ""

    def plot(self, x, y, *args, **kwargs):
        self.plot_calls.append((list(x), list(y), args, kwargs))

    def bar(self, x, height, *args, **kwargs):
        self.bar_calls.append((list(x), list(height), kwargs.get("width")))

    def text(self, x, y, s, *args, **kwargs):
        self.text_calls.append((x, y, s))

    def set_xlim(self, *a, **kw): pass
    def set_ylim(self, *a, **kw): pass
    def set_xlabel(self, *a, **kw): pass
    def set_ylabel(self, *a, **kw): pass
    def set_title(self, title: str) -> None: self.title = title
    def legend(self, *a, **kw): pass

    def __getattr__(self, _name):
        # Fallback for matplotlib methods plot_reliability may grow into
        # (axhline, grid, tick_params, etc.). Returns a no-op callable
        # so a future plot_reliability addition doesn't AttributeError
        # this recorder. Per R1 minor #5.
        return lambda *a, **kw: None


class _FigRecorder:
    def __init__(self, ax: _AxRecorder) -> None:
        self._ax = ax
    def tight_layout(self): pass
    def savefig(self, *a, **kw): pass


def _install_matplotlib_recorder(monkeypatch):
    ax = _AxRecorder()
    fig = _FigRecorder(ax)
    import matplotlib.pyplot as plt
    monkeypatch.setattr(plt, "subplots", lambda *a, **kw: (fig, ax))
    monkeypatch.setattr(plt, "close", lambda *a, **kw: None)
    return ax


def test_plot_reliability_bins_full_pool_not_block_only_subset(
    monkeypatch, tmp_path,
):
    """Pin per-bin empirical positive rates AND the identity reference
    line. The fixture is constructed so the canonical full-pool
    full-correct implementation yields visibly distinct rates per bin
    (``[0.0, 0.0, 0.25, 0.75, 1.0]``), while the known-bad
    ``hits = (score >= tau)`` over the Block-only subset would collapse
    every populated bin to 1.0 (a step function).
    """
    scores = np.array([
        0.05, 0.10, 0.15, 0.18,    # bin 0 (0.0-0.2), all label=0  -> rate 0.0
        0.25, 0.30, 0.32, 0.38,    # bin 1 (0.2-0.4), all label=0  -> rate 0.0
        0.45, 0.50, 0.55, 0.58,    # bin 2 (0.4-0.6), one label=1  -> rate 0.25
        0.65, 0.70, 0.72, 0.78,    # bin 3 (0.6-0.8), three label=1 -> rate 0.75
        0.85, 0.90, 0.92, 0.98,    # bin 4 (0.8-1.0), all label=1  -> rate 1.0
    ])
    labels = np.array([
        0, 0, 0, 0,
        0, 0, 0, 0,
        1, 0, 0, 0,
        1, 1, 1, 0,
        1, 1, 1, 1,
    ])

    ax = _install_matplotlib_recorder(monkeypatch)
    plot_reliability(
        scores, labels, n_bins=5,
        path=tmp_path / "reliability.png",
        title="Reliability — hallucination eval (deployed tau_h=0.8)",
    )

    assert len(ax.bar_calls) == 1
    centers, heights, width = ax.bar_calls[0]
    assert centers == pytest.approx([0.1, 0.3, 0.5, 0.7, 0.9], abs=1e-9)
    # The canonical full-pool rates. A revert to the Block-only step
    # function would yield [1.0, 1.0, 1.0, 1.0, 1.0] — caught by this
    # assertion with a >=0.25 margin per bin.
    assert heights == pytest.approx([0.0, 0.0, 0.25, 0.75, 1.0], abs=1e-9)
    assert width == pytest.approx(1 / 5, abs=1e-9)

    # The identity reference line [0,1] vs [0,1] is plotted exactly once.
    identity_calls = [
        c for c in ax.plot_calls if c[0] == [0, 1] and c[1] == [0, 1]
    ]
    assert len(identity_calls) == 1, (
        f"identity reference line missing from ax.plot() calls: {ax.plot_calls}"
    )

    # Per-bin n=K annotation: one ax.text() per populated bin, content "n=4".
    assert len(ax.text_calls) == 5
    annotated = [t[2] for t in ax.text_calls]
    assert all(s == "n=4" for s in annotated)

    # Title threads through verbatim (defense against a refactor losing it).
    assert "tau_h=0.8" in ax.title


def test_plot_reliability_empty_input_is_noop(monkeypatch, tmp_path):
    """Empty input must early-return without drawing anything. Pins the
    line 203-205 early-return path of plot_reliability.
    """
    ax = _install_matplotlib_recorder(monkeypatch)
    plot_reliability(
        np.array([]), np.array([]),
        n_bins=5, path=tmp_path / "empty.png", title="empty",
    )
    assert ax.bar_calls == []
    assert ax.plot_calls == []
    assert ax.text_calls == []


# ============================================================================
# 5. Dropped-fold disclosure — no silent headline-fold drops.
# ============================================================================

def _internal30_with_poison(poisoned_fold: int | None) -> pd.DataFrame:
    """Build a 24-contract Internal-30-shaped frame across HEADLINE_FOLDS
    (5 contracts per fold) + 4 frozen-fold contracts.

    Each contract has one block finding and two non-block findings.
    Non-blocks score (0.95, 0.95) — pass every grid point. Block findings
    score (0.85, 0.85) by default — pass at (tau_h, tau_f) <= (0.85, 0.85).

    If ``poisoned_fold`` is a headline fold, all block findings in that
    fold are scored (0.40, 0.40) — BELOW the 0.50 grid floor. Any
    training partition that includes the poisoned fold cannot reach
    Block-recall=1.0, so ``calibrate_fold`` returns None on it.

    Behavior verified against live ``calibrate_fold``:
      poisoned=None  -> every fold calibrates to (0.85, 0.50).
      poisoned=2     -> held-out fold 2 calibrates (its train = {1,3,4});
                        folds 1, 3, 4 each drop (their trains include 2).
    """
    rows: list[dict] = []
    sources = ["cuad", "maud", "edgar", "perturbed"]
    cid = 0
    for fold in HEADLINE_FOLDS:
        for _ in range(5):
            src = sources[cid % 4]
            contract = f"{src}_{cid:03d}"
            poisoned = (fold == poisoned_fold)
            score = 0.40 if poisoned else 0.85
            rows.append({
                "fold": fold, "contract_id": contract, "source": src,
                "h_score": score, "f_score": score, "is_block": True,
            })
            for j in range(2):
                rows.append({
                    "fold": fold, "contract_id": contract, "source": src,
                    "h_score": 0.95, "f_score": 0.95, "is_block": False,
                })
            cid += 1
    # 4 frozen-fold contracts — never enter headline accounting.
    for _ in range(4):
        src = sources[cid % 4]
        contract = f"{src}_{cid:03d}"
        rows.append({
            "fold": 5, "contract_id": contract, "source": src,
            "h_score": 0.85, "f_score": 0.85, "is_block": True,
        })
        cid += 1
    return pd.DataFrame(rows)


def test_calibrate_all_headline_folds_all_succeed():
    """Clean fixture: every train slice has every block at (0.85, 0.85),
    so all four headline folds calibrate. ``dropped`` must be [], and the
    present list must cover HEADLINE_FOLDS exactly.
    """
    df = _internal30_with_poison(poisoned_fold=None)
    results, dropped = calibrate_all_headline_folds(df)
    assert dropped == []
    assert sorted(r["fold"] for r in results) == HEADLINE_FOLDS
    # Anti-regression: present + dropped partitions HEADLINE_FOLDS.
    present = [r["fold"] for r in results]
    assert sorted(present + dropped) == HEADLINE_FOLDS


def test_calibrate_all_headline_folds_poisoned_fold_surfaces_in_dropped():
    """Poison fold 2's blocks. Fold 2's train = {1, 3, 4} (clean) — fold
    2 calibrates and is the SURVIVOR. Folds 1, 3, 4 each have a train
    slice that includes fold 2 (poisoned) — their calibrations fail and
    those folds appear in ``dropped``.

    Anti-regression: a future commit that silently skips a fold without
    populating ``dropped`` would fail the assertion below.
    """
    df = _internal30_with_poison(poisoned_fold=2)
    results, dropped = calibrate_all_headline_folds(df)
    assert sorted(dropped) == [1, 3, 4]
    present = [r["fold"] for r in results]
    assert present == [2]
    # Coverage invariant: every headline fold accounted for exactly once.
    assert sorted(present + dropped) == HEADLINE_FOLDS
    assert len(present) + len(dropped) == len(HEADLINE_FOLDS)


def test_calibrate_all_headline_folds_all_fail_returns_empty_results():
    """Poison every headline fold's blocks. Every train slice is
    infeasible. ``results`` is empty, ``dropped`` is exactly HEADLINE_FOLDS.
    This is the precondition for the main() SystemExit at calibrate.py
    line ~263; tested directly here to isolate the helper from CLI/IO.
    """
    df = _internal30_with_poison(poisoned_fold=None)
    block_mask = df["is_block"] & df["fold"].isin(HEADLINE_FOLDS)
    df.loc[block_mask, "h_score"] = 0.40
    df.loc[block_mask, "f_score"] = 0.40
    results, dropped = calibrate_all_headline_folds(df)
    assert results == []
    assert sorted(dropped) == HEADLINE_FOLDS


def test_main_exits_nonzero_when_no_headline_fold_calibrates(tmp_path):
    """End-to-end: a CSV input where every headline fold is uncalibratable
    must drive main() to exit non-zero with the disclosure message.
    Pins the SystemExit contract — silent fallback to a lower
    require_recall would skip the SystemExit and write a misleadingly
    confident thresholds.json.
    """
    df = _internal30_with_poison(poisoned_fold=None)
    df.loc[df["is_block"], "h_score"] = 0.40
    df.loc[df["is_block"], "f_score"] = 0.40
    csv_path = tmp_path / "all_fail.csv"
    # main() recomputes fold assignment, so drop the column.
    df.drop(columns=["fold"]).to_csv(csv_path, index=False)

    out_path = tmp_path / "thresholds.json"
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.calibrate",
         "--input", str(csv_path),
         "--out", str(out_path),
         "--reliability-h", str(tmp_path / "h.png"),
         "--reliability-f", str(tmp_path / "f.png")],
        cwd=repo_root,
        capture_output=True, text=True,
    )
    assert result.returncode != 0, (
        f"main() exited 0 with no calibrations; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "No headline fold" in combined
    assert not out_path.exists()


def test_summary_carries_disclosure_fields_when_main_succeeds(tmp_path):
    """When main() succeeds, the summary JSON must carry the
    ``dropped_headline_folds`` and ``headline_folds_present`` fields,
    AND ``len(per_fold) + len(dropped) == len(HEADLINE_FOLDS)``.

    This is the contract that protects future readers from a silent
    fold-drop regression: if any fold goes silent (warning logged but
    not surfaced), this invariant fails.
    """
    df = _internal30_with_poison(poisoned_fold=None)
    csv_path = tmp_path / "ok.csv"
    df.drop(columns=["fold"]).to_csv(csv_path, index=False)
    out_path = tmp_path / "thresholds.json"
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.calibrate",
         "--input", str(csv_path),
         "--out", str(out_path),
         "--reliability-h", str(tmp_path / "h.png"),
         "--reliability-f", str(tmp_path / "f.png")],
        cwd=repo_root,
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"main() failed unexpectedly: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    summary = json.loads(out_path.read_text())
    assert "dropped_headline_folds" in summary
    assert "headline_folds_present" in summary
    assert summary["dropped_headline_folds"] == []
    assert sorted(summary["headline_folds_present"]) == HEADLINE_FOLDS
    # Coverage invariant on the persisted summary.
    n_per_fold = len(summary["per_fold"])
    n_dropped = len(summary["dropped_headline_folds"])
    assert n_per_fold + n_dropped == len(HEADLINE_FOLDS)


def test_summary_carries_headline_statistic_field(tmp_path):
    """Fix 10: the summary JSON must carry an explicit `headline_statistic`
    field naming the cluster-bootstrap key, so downstream tooling has a
    single source of truth rather than guessing which LB is load-bearing.
    Also pins that the Wilson key was renamed to the exploratory-IID name
    while the cluster bootstrap key stays byte-stable.
    """
    df = _internal30_with_poison(poisoned_fold=None)
    csv_path = tmp_path / "ok.csv"
    df.drop(columns=["fold"]).to_csv(csv_path, index=False)
    out_path = tmp_path / "thresholds.json"
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.calibrate",
         "--input", str(csv_path),
         "--out", str(out_path),
         "--reliability-h", str(tmp_path / "h.png"),
         "--reliability-f", str(tmp_path / "f.png")],
        cwd=repo_root,
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"main() failed unexpectedly: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    summary = json.loads(out_path.read_text())
    assert summary.get("headline_statistic") == (
        "cluster_bootstrap_one_sided_95_lb_block_recall"
    )
    # The renamed Wilson key is present; the legacy key name is GONE.
    assert "wilson_one_sided_95_lb_block_recall_exploratory_iid" in summary
    assert "wilson_one_sided_95_lb_block_recall" not in summary
    # Cluster bootstrap key remains byte-stable (referenced by
    # build_readme_table.py and external tooling).
    assert "cluster_bootstrap_one_sided_95_lb_block_recall" in summary
