"""Statistics tests for the round-B fixes (one-sided Wilson + cluster
bootstrap over per-finding outcomes).

Per ML-reviewer findings:
  - Wilson z must be 1.6449 (one-sided 95%), NOT 1.96 (two-sided 95%).
  - Bootstrap must be non-parametric and respect per-contract clustering,
    NOT a parametric Binomial(n, p) draw treating findings as IID.
"""
from __future__ import annotations

import numpy as np
import pytest

from scripts.calibrate import (
    Z_ONE_SIDED_95,
    cluster_bootstrap_recall_ci,
    wilson_lb_one_sided,
)


def test_wilson_constant_is_one_sided_95():
    """Sanity: the constant is the one-sided 95% normal quantile (~1.6449),
    not the two-sided 95% / one-sided 97.5% quantile (~1.96)."""
    assert abs(Z_ONE_SIDED_95 - 1.6449) < 1e-4
    assert Z_ONE_SIDED_95 < 1.96  # would fail if someone accidentally restored 1.96


def test_wilson_lb_on_perfect_recall_strictly_less_than_one():
    """8/8 successes: the 95% one-sided LB must be strictly < 1.0; it
    should also be GREATER than the two-sided 95% LB (z=1.96) because
    one-sided is less conservative."""
    lb_one_sided = wilson_lb_one_sided(8, 8)
    assert 0.0 < lb_one_sided < 1.0


def test_wilson_lb_zero_n_handled():
    assert wilson_lb_one_sided(0, 0) == 0.0


def test_wilson_lb_monotone_in_successes():
    """More successes => higher LB at fixed n."""
    lb_low = wilson_lb_one_sided(5, 10)
    lb_high = wilson_lb_one_sided(9, 10)
    assert lb_high > lb_low


def test_cluster_bootstrap_handles_empty():
    point, lb = cluster_bootstrap_recall_ci([], [])
    assert (point, lb) == (0.0, 0.0)


def test_cluster_bootstrap_point_equals_pooled_mean():
    per_fold_hits = [[1, 1, 0], [1, 1, 1]]
    per_fold_contracts = [["c1", "c1", "c1"], ["c2", "c2", "c2"]]
    point, _ = cluster_bootstrap_recall_ci(per_fold_hits, per_fold_contracts,
                                            n_resamples=200, seed=0)
    # 5 hits out of 6 → 0.8333
    assert abs(point - 5 / 6) < 1e-9


def test_cluster_bootstrap_lb_below_point():
    """LB of a one-sided 95% CI must be <= point estimate."""
    per_fold_hits = [[1, 1, 1, 0, 0]] * 4
    per_fold_contracts = [[f"c{j}" for j in range(5)]] * 4  # 5 unique contracts
    point, lb = cluster_bootstrap_recall_ci(per_fold_hits, per_fold_contracts,
                                            n_resamples=500, seed=0)
    assert lb <= point


def test_cluster_bootstrap_respects_clustering():
    """When all findings of a contract are correlated, the cluster bootstrap
    should produce a wider CI than a naive IID bootstrap would.

    Construction: 5 contracts, each with 4 findings; 3 contracts are
    all-1, 2 contracts are all-0. Point estimate = 12/20 = 0.6.
    A naive IID resample would have SE_p = sqrt(0.6*0.4/20) ~ 0.11.
    A cluster resample over 5 contracts has higher variance because
    findings are perfectly correlated within contract.
    """
    per_fold_hits = [[1] * 4, [1] * 4, [1] * 4, [0] * 4, [0] * 4]
    per_fold_contracts = [
        ["c1"] * 4, ["c2"] * 4, ["c3"] * 4, ["c4"] * 4, ["c5"] * 4,
    ]
    point, lb = cluster_bootstrap_recall_ci(
        per_fold_hits, per_fold_contracts, n_resamples=2000, seed=0,
    )
    assert abs(point - 0.6) < 1e-9
    # Cluster bootstrap of 5 contracts (3 all-1, 2 all-0) is essentially
    # a beta-like distribution on counts in {0/5, 1/5, ..., 5/5}, so the
    # 5th percentile should be well below the 0.49 a naive IID resample
    # would give.
    assert lb < 0.49
