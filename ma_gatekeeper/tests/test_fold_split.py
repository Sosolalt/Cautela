"""D9-morning unit test (plan §7 v3): fold split must be leak-free.

This is the test the timeline reviewer specifically called out as
mitigation for "5-fold CV implementation bug (off-by-one, shared-state
leakage)". Run it BEFORE any calibration math runs.
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.calibrate import (
    FOLD_COUNT,
    HEADLINE_FOLDS,
    FROZEN_FOLD,
    assign_folds,
    unit_test_fold_split,
)


def _toy_df(n_contracts_per_source: int = 6) -> pd.DataFrame:
    """30 contracts across 4 sources, 5 findings each, balanced."""
    rows = []
    sources = ["cuad", "maud", "edgar_holdout", "perturbed"]
    contract_id = 0
    for src in sources:
        for c in range(n_contracts_per_source):
            for f in range(5):
                rows.append({
                    "source": src,
                    "contract_id": f"{src}_{contract_id:03d}",
                    "finding_id": f"{src}_{contract_id:03d}_{f}",
                    "severity": "block" if f == 0 else "info",
                    "h_score": 0.9 - 0.02 * f,
                    "f_score": 0.85 - 0.02 * f,
                    "is_block": f == 0,
                })
            contract_id += 1
    return pd.DataFrame(rows)


def test_assign_folds_is_deterministic_per_contract():
    df = _toy_df()
    df["fold"] = assign_folds(df, seed=42)
    # Re-shuffle row order; same contract -> same fold.
    df2 = df.sample(frac=1, random_state=0).reset_index(drop=True)
    df2["fold_new"] = assign_folds(df2, seed=42)
    joined = df.merge(df2[["contract_id", "fold_new"]].drop_duplicates(),
                      on="contract_id", how="left")
    assert (joined["fold"] == joined["fold_new"]).all()


def test_no_contract_spans_multiple_folds():
    df = _toy_df()
    df["fold"] = assign_folds(df, seed=42)
    # Same assertion unit_test_fold_split makes, but explicit so a test
    # runner reports it cleanly if it fires.
    per_contract_folds = df.groupby("contract_id")["fold"].nunique()
    assert per_contract_folds.max() == 1


def test_all_five_folds_populated():
    df = _toy_df()
    df["fold"] = assign_folds(df, seed=42)
    assert set(df["fold"].unique()) == set(range(1, FOLD_COUNT + 1))


def test_every_source_appears_in_at_least_two_folds():
    df = _toy_df()
    df["fold"] = assign_folds(df, seed=42)
    for source in df["source"].unique():
        folds = df.loc[df["source"] == source, "fold"].unique()
        assert len(folds) >= 2, f"source {source} confined to one fold"


def test_unit_test_fold_split_passes_on_clean_data():
    df = _toy_df()
    df["fold"] = assign_folds(df, seed=42)
    unit_test_fold_split(df)  # raises if anything is wrong


def test_unit_test_fold_split_catches_leakage():
    """Inject a deliberate leak (same contract in two folds) and confirm
    the unit test catches it. This is the test-for-the-test.
    """
    df = _toy_df()
    df["fold"] = assign_folds(df, seed=42)
    # Inject leak.
    df.loc[df.index[0], "fold"] = (df["fold"].iloc[0] % FOLD_COUNT) + 1
    with pytest.raises(AssertionError):
        unit_test_fold_split(df)


def test_frozen_fold_constant_is_five():
    """If anyone ever changes FROZEN_FOLD by accident, this catches it.
    The Reflector's allowlist enforcement depends on this constant.
    """
    assert FROZEN_FOLD == 5
    assert FROZEN_FOLD not in HEADLINE_FOLDS
    assert set(HEADLINE_FOLDS) == {1, 2, 3, 4}
