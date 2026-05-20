"""Tests for the Reflector promotion rule (plan §6.3 v4).

Validates that:
- The paired bootstrap CI lower bound is computed correctly.
- The SE-scaled epsilon honors its 0.03 floor.
- Promotion fires ONLY when both gates pass.
- The frozen-fold allowlist refuses writes to fold 5.
"""
from __future__ import annotations

import numpy as np
import pytest

from agent.reflector import (
    assert_writable,
    epsilon_fold5,
    paired_bootstrap_ci_lb,
    paired_bootstrap_se,
    should_promote,
)


def test_bootstrap_ci_lb_on_positive_uniform_deltas_is_positive():
    deltas = np.full(50, 0.10)
    lb = paired_bootstrap_ci_lb(deltas, n_resamples=2000, seed=0)
    assert lb > 0.05


def test_bootstrap_ci_lb_on_zero_deltas_is_at_zero():
    deltas = np.zeros(50)
    lb = paired_bootstrap_ci_lb(deltas, n_resamples=2000, seed=0)
    assert lb == pytest.approx(0.0, abs=1e-9)


def test_bootstrap_ci_lb_on_negative_deltas_is_negative():
    deltas = np.full(50, -0.05)
    lb = paired_bootstrap_ci_lb(deltas, n_resamples=2000, seed=0)
    assert lb < 0


def test_epsilon_honors_floor_when_se_collapses():
    """If all fold-5 findings agree perfectly, SE is 0; eps falls to 0.03."""
    deltas = np.zeros(8)  # six-to-ten Block findings per fold
    eps = epsilon_fold5(deltas)
    assert eps == pytest.approx(0.03)


def test_epsilon_uses_se_when_above_floor():
    # SE of mean ≈ 0.25 / sqrt(8) ≈ 0.088 — comfortably above the 0.03 floor.
    rng = np.random.default_rng(0)
    deltas = rng.normal(0.0, 0.25, size=8)
    eps = epsilon_fold5(deltas)
    assert eps > 0.03  # SE > floor


def test_promotion_fires_when_both_gates_pass():
    rng = np.random.default_rng(0)
    # Big lift on the regression set: candidate clearly better.
    reg = rng.normal(0.20, 0.05, size=40)  # mean ~0.20, well above 0
    # Fold-5: candidate effectively matches production.
    f5_cand = rng.normal(0.85, 0.02, size=8)
    f5_prod = rng.normal(0.85, 0.02, size=8)
    ok, diag = should_promote(
        regression_deltas=reg,
        fold5_candidate_scores=f5_cand,
        fold5_production_scores=f5_prod,
    )
    assert ok, diag
    assert diag["regression_ci_lb"] > 0
    assert diag["fold5_non_regression_ok"] == 1.0


def test_promotion_blocked_when_regression_ci_includes_zero():
    """Noisy small lift => CI LB <= 0 => block promotion."""
    rng = np.random.default_rng(0)
    reg = rng.normal(0.005, 0.10, size=10)  # tiny mean, wide noise
    f5_cand = rng.normal(0.85, 0.02, size=8)
    f5_prod = rng.normal(0.85, 0.02, size=8)
    ok, diag = should_promote(
        regression_deltas=reg,
        fold5_candidate_scores=f5_cand,
        fold5_production_scores=f5_prod,
    )
    assert not ok, diag


def test_promotion_blocked_on_held_out_regression():
    """Even if regression set shows a big lift, held-out regression blocks it."""
    rng = np.random.default_rng(0)
    reg = rng.normal(0.20, 0.05, size=40)  # candidate wins on regression set
    f5_cand = rng.normal(0.60, 0.02, size=8)  # but loses badly on fold 5
    f5_prod = rng.normal(0.85, 0.02, size=8)
    ok, diag = should_promote(
        regression_deltas=reg,
        fold5_candidate_scores=f5_cand,
        fold5_production_scores=f5_prod,
    )
    assert not ok, diag
    assert diag["fold5_non_regression_ok"] == 0.0


def test_allowlist_blocks_writes_to_frozen_fold5():
    assert_writable("regressions-v1")
    with pytest.raises(PermissionError):
        assert_writable("internal-30-holdout-fold-5")
    with pytest.raises(PermissionError):
        assert_writable("anything-else")
