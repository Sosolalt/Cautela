"""5-fold cross-validation calibration script (plan §5.4).

Runs AFTER the agent has produced raw (h_score, f_score) pairs for every
finding across Internal-30 (output of D8 inference run).

Inputs:
  - CSV with columns: contract_id, source, finding_id, severity,
    h_score, f_score, is_block (ground truth)

Outputs:
  - thresholds.json with the deployed (tau_h, tau_f), per-fold metrics,
    one-sided Wilson + non-parametric bootstrap CIs
  - reliability_h.png, reliability_f.png  (10-bin calibration plots)
  - calibration_summary.json (for inclusion in the README results table)

Hard rules:
  - FOLD 5 is reserved for the Reflector's frozen non-regression set.
    Never used in headline calibration.
  - Per-evaluator thresholds, calibrated jointly via 2D grid.
  - Bootstrap on per-finding hits/misses (non-parametric), NOT
    Binomial(n,p) parametric, because findings within a contract are
    correlated (ML-reviewer fix).
  - Wilson z = 1.6449 (one-sided 95% LB), NOT 1.96 (two-sided).
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

_LOG = logging.getLogger(__name__)

FOLD_COUNT = 5
HEADLINE_FOLDS = [1, 2, 3, 4]
FROZEN_FOLD = 5
TAU_GRID = np.round(np.arange(0.50, 1.00, 0.01), 2)  # 50 values

# One-sided 95% normal quantile (NOT 1.96 which is two-sided 95% / one-sided 97.5%).
Z_ONE_SIDED_95 = 1.6449


def assign_folds(df: pd.DataFrame, seed: int = 42) -> pd.Series:
    """Per-source round-robin (group K-fold).

    NOTE: ML reviewer flagged this as "not stratified in the strict
    sense" — it's a group K-fold balanced by construction on equal
    source sizes. For Internal-30 with 4 sources × ~6-8 contracts each,
    it's adequately balanced. If source sizes diverge, switch to
    sklearn.model_selection.GroupKFold + stratification.
    """
    rng = np.random.default_rng(seed)
    fold_for_contract: dict[str, int] = {}
    for source, group in df.groupby("source"):
        contracts = sorted(group["contract_id"].unique())
        rng.shuffle(contracts)
        for i, c in enumerate(contracts):
            fold_for_contract[c] = (i % FOLD_COUNT) + 1
    return df["contract_id"].map(fold_for_contract)


def unit_test_fold_split(df: pd.DataFrame) -> None:
    """D9-morning leak check — runs before any calibration math."""
    per_contract_folds = df.groupby("contract_id")["fold"].nunique()
    assert per_contract_folds.max() == 1, "contract spans multiple folds"
    assert set(df["fold"].unique()) == set(range(1, FOLD_COUNT + 1)), \
        "missing fold(s)"
    for source in df["source"].unique():
        folds = df.loc[df["source"] == source, "fold"].unique()
        assert len(folds) >= 2, f"source '{source}' confined to one fold"
    _LOG.info("Fold split unit test PASSED.")


def calibrate_fold(
    train_df: pd.DataFrame,
    *,
    require_recall: float = 1.0,
) -> tuple[float, float] | None:
    """Grid-search (tau_h, tau_f) on training folds.

    Returns (tau_h*, tau_f*) minimizing abstention subject to
    Block-recall >= require_recall. Tie-break: prefer higher tau_h.
    """
    block_mask = train_df["is_block"].to_numpy(dtype=bool)
    h = train_df["h_score"].to_numpy()
    f = train_df["f_score"].to_numpy()

    best: tuple[float, float, float, float] | None = None  # (-tau_h, abstain, tau_h, tau_f)

    for tau_h in TAU_GRID:
        for tau_f in TAU_GRID:
            passes = (h >= tau_h) & (f >= tau_f)
            block_recall = passes[block_mask].mean() if block_mask.any() else 1.0
            if block_recall < require_recall:
                continue
            abstain_rate = 1.0 - passes.mean()
            if best is None or (abstain_rate, -tau_h) < (best[1], best[0]):
                best = (-tau_h, abstain_rate, float(tau_h), float(tau_f))
    return (best[2], best[3]) if best else None


def evaluate_fold(test_df: pd.DataFrame, tau_h: float, tau_f: float) -> dict[str, float]:
    h = test_df["h_score"].to_numpy()
    f = test_df["f_score"].to_numpy()
    passes = (h >= tau_h) & (f >= tau_f)
    block_mask = test_df["is_block"].to_numpy(dtype=bool)
    block_passes = passes[block_mask] if block_mask.any() else np.array([])
    block_recall = float(block_passes.mean()) if len(block_passes) else 1.0
    abstain_rate = float(1.0 - passes.mean())
    return {
        "tau_h": tau_h,
        "tau_f": tau_f,
        "block_recall": block_recall,
        "abstain_rate": abstain_rate,
        "n_block": int(block_mask.sum()),
        "n_total": int(len(test_df)),
        "block_hit_vector": block_passes.astype(int).tolist(),
        "contract_ids": test_df["contract_id"].tolist(),
    }


def wilson_lb_one_sided(successes: int, n: int, *, z: float = Z_ONE_SIDED_95) -> float:
    """One-sided 95% Wilson lower bound on a binomial proportion.

    Reverted to one-sided per ML-reviewer: previous code used
    z=1.959963... (two-sided 95% = one-sided 97.5%), which silently
    over-claimed conservatism.
    """
    if n == 0:
        return 0.0
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return float(center - half)


def cluster_bootstrap_recall_ci(
    per_fold_hits: list[list[int]],
    per_fold_contracts: list[list[str]],
    *,
    n_resamples: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float]:
    """Non-parametric cluster bootstrap over (contract -> findings).

    ML reviewer flagged that the v1 parametric Binomial(n, p) bootstrap
    treats findings as IID, which they aren't (findings within a
    contract are correlated). Cluster-resample contracts (with
    replacement) and pool hits/misses across them. Returns (mean, LB).
    """
    # Group hit-vectors by contract id across all folds.
    contract_hits: dict[str, list[int]] = {}
    for hits, contracts in zip(per_fold_hits, per_fold_contracts):
        for h_int, cid in zip(hits, contracts):
            contract_hits.setdefault(cid, []).append(h_int)
    all_contracts = list(contract_hits.keys())
    if not all_contracts:
        return 0.0, 0.0

    rng = np.random.default_rng(seed)
    means = np.empty(n_resamples)
    for k in range(n_resamples):
        idx = rng.integers(0, len(all_contracts), size=len(all_contracts))
        pooled = []
        for j in idx:
            pooled.extend(contract_hits[all_contracts[j]])
        means[k] = float(np.mean(pooled)) if pooled else 0.0

    point = float(np.mean([h for hits in contract_hits.values() for h in hits]))
    # One-sided 95% LB.
    lb = float(np.quantile(means, alpha))
    return point, lb


def plot_reliability(
    scores: np.ndarray, labels: np.ndarray, *, n_bins: int = 10,
    path: Path, title: str,
) -> None:
    """10-bin reliability diagram.

    Canonical semantics (ML-reviewer fix): bin the predictions by score
    and plot `mean(labels)` (i.e. the empirical positive rate, here =
    Block-recall) per bin against the bin center. Perfect calibration
    is the y=x identity line.

    - `scores`: per-finding model score (e.g. h_score or f_score) over
                THE WHOLE POOL (not just blocks).
    - `labels`: per-finding ground-truth indicator (1 if is_block, 0 otherwise).

    v3 passed `hits = (score >= tau)` over the BLOCK-ONLY subset which
    collapsed to a degenerate step function, not a calibration curve.
    Fixed.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if len(scores) == 0:
        _LOG.warning("plot_reliability: empty scores; skipping %s", path)
        return
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.digitize(scores, bins) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    bin_centers, bin_rate, bin_counts = [], [], []
    for b in range(n_bins):
        mask = bin_idx == b
        if not mask.any():
            continue
        bin_centers.append((bins[b] + bins[b + 1]) / 2)
        bin_rate.append(float(labels[mask].mean()))
        bin_counts.append(int(mask.sum()))

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect calibration")
    ax.bar(bin_centers, bin_rate, width=1.0 / n_bins, alpha=0.6, edgecolor="k")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("model score (bin)")
    ax.set_ylabel("empirical P(is_block) in bin")
    ax.set_title(title)
    # Annotate each bar with the bin's finding count so judges can see
    # the sample-size context behind sparse bins.
    for x, y, n in zip(bin_centers, bin_rate, bin_counts):
        ax.text(x, min(y + 0.02, 0.98), f"n={n}", ha="center", fontsize=7)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    _LOG.info("Wrote %s", path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV of judged findings")
    parser.add_argument("--out", default="thresholds.json")
    parser.add_argument("--reliability-h", default="reliability_h.png")
    parser.add_argument("--reliability-f", default="reliability_f.png")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df["fold"] = assign_folds(df)
    unit_test_fold_split(df)

    per_fold_results: list[dict] = []
    for i in HEADLINE_FOLDS:
        train = df[df["fold"].isin([k for k in HEADLINE_FOLDS if k != i])]
        test = df[df["fold"] == i]
        thresholds = calibrate_fold(train)
        if thresholds is None:
            _LOG.warning("Fold %s: no (tau_h, tau_f) achieves Block-recall=1.0", i)
            continue
        tau_h, tau_f = thresholds
        per_fold_results.append({"fold": i, **evaluate_fold(test, tau_h, tau_f)})

    if not per_fold_results:
        raise SystemExit("No headline fold produced a calibration. "
                         "Lower require_recall and re-run with disclosure.")

    # Aggregate with cluster bootstrap + one-sided Wilson.
    per_fold_hits = [r.pop("block_hit_vector") for r in per_fold_results]
    per_fold_contracts = [r.pop("contract_ids") for r in per_fold_results]
    point, boot_lb = cluster_bootstrap_recall_ci(per_fold_hits, per_fold_contracts)

    total_hits = int(sum(sum(hits) for hits in per_fold_hits))
    total_findings = int(sum(len(hits) for hits in per_fold_hits))
    wilson_lb = wilson_lb_one_sided(total_hits, total_findings)

    deployed_tau_h = float(np.median([r["tau_h"] for r in per_fold_results]))
    deployed_tau_f = float(np.median([r["tau_f"] for r in per_fold_results]))

    # Reliability diagrams over all headline folds pooled (full pool,
    # not the block-only subset). ML-reviewer fix: pass the model score
    # AND the ground-truth label (is_block) so the plot shows empirical
    # P(is_block | score in bin) — a real calibration curve, not a step.
    pool = df[df["fold"].isin(HEADLINE_FOLDS)]
    if not pool.empty:
        is_block = pool["is_block"].astype(int).to_numpy()
        plot_reliability(
            pool["h_score"].to_numpy(), is_block,
            path=Path(args.reliability_h),
            title=f"Reliability — hallucination eval (deployed tau_h={deployed_tau_h})",
        )
        plot_reliability(
            pool["f_score"].to_numpy(), is_block,
            path=Path(args.reliability_f),
            title=f"Reliability — faithfulness eval (deployed tau_f={deployed_tau_f})",
        )

    summary = {
        "headline_folds": HEADLINE_FOLDS,
        "frozen_fold": FROZEN_FOLD,
        "effective_n_contracts": int(
            df[df["fold"].isin(HEADLINE_FOLDS)]["contract_id"].nunique()
        ),
        "per_fold": per_fold_results,
        "point_block_recall": point,
        "wilson_one_sided_95_lb_block_recall": wilson_lb,
        "cluster_bootstrap_one_sided_95_lb_block_recall": boot_lb,
        "deployed_tau_h": deployed_tau_h,
        "deployed_tau_f": deployed_tau_f,
        # router.Thresholds.from_json reads these:
        "tau_h": deployed_tau_h,
        "tau_f": deployed_tau_f,
    }
    Path(args.out).write_text(json.dumps(summary, indent=2))
    _LOG.info("Wrote %s", args.out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
