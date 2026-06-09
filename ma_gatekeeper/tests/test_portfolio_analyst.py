"""Tests for the Fix 7 Portfolio Analyst agent.

Mirrors `tests/test_eval_maud_mcq.py` and
`tests/test_verify_structural_reasoning.py` defensive priorities:

  - Mock mode must run end-to-end (the CI gate).
  - The schema must validate (Pydantic enforces shape).
  - Live mode is gated behind `make_live_portfolio()` which raises
    `NotImplementedError` (PROJECT_LOG Phase 6.6 / Phase 7 convention).
    We pin that behavior so a future refactor cannot silently no-op
    `--live`.
  - Every member_deal_id MUST appear in the fixture roster (no
    hallucinated deal_ids). The mutual-exclusion invariant between
    clusters and outliers MUST hold (a deal cannot both belong to a
    cluster and be flagged as an outlier).

DO NOT exercise the live agent here — Vertex quota is not available in
CI. The live path raises by design.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import portfolio_analyst as PA
from agent.schemas import PortfolioReport


_FIXTURES = Path(__file__).parent / "fixtures"
_SAMPLE_PATH = _FIXTURES / "portfolio_sample.json"
_EXPECTED_PATH = _FIXTURES / "portfolio_expected_output.json"


# ---------------------------------------------------------------------------
# Fixture sanity
# ---------------------------------------------------------------------------


def test_sample_fixture_has_30_distinct_contracts():
    """The 1M-context demo line ('thirty contracts') depends on this."""
    payload = json.loads(_SAMPLE_PATH.read_text())
    deal_ids = [c["deal_id"] for c in payload["contracts"]]
    assert len(deal_ids) == 30, (
        f"Portfolio Analyst voiceover names 'thirty contracts'; "
        f"fixture has {len(deal_ids)}. Drift here breaks the demo line."
    )
    assert len(set(deal_ids)) == 30, "duplicate deal_ids in sample fixture"


def test_expected_output_validates_against_schema():
    """The mock cannot lie about the schema — Pydantic must accept it."""
    payload = json.loads(_EXPECTED_PATH.read_text())
    report = PortfolioReport(**payload)
    assert report.clusters, "expected_output has no clusters"
    assert report.outliers, "expected_output has no outliers (demo line names an outlier)"


# ---------------------------------------------------------------------------
# Mock-default returns the canonical fixture
# ---------------------------------------------------------------------------


def test_make_mock_portfolio_returns_canonical_fixture():
    agent = PA.make_mock_portfolio()
    contracts = PA.load_sample_contracts()
    report = agent(contracts)
    expected = PortfolioReport(**json.loads(_EXPECTED_PATH.read_text()))
    assert report.model_dump() == expected.model_dump(), (
        "Mock-default drifted from the canonical fixture. Re-generate "
        "the fixture deliberately or fix the mock."
    )


def test_make_mock_portfolio_returns_independent_copy():
    """The mock must not let one caller mutate another's report."""
    agent = PA.make_mock_portfolio()
    r1 = agent([])
    r2 = agent([])
    # Mutate r1 in place; r2 must be unaffected.
    r1.clusters[0].name = "mutated"
    assert r2.clusters[0].name != "mutated", (
        "Mock returns shared state — cross-caller mutation observed."
    )


# ---------------------------------------------------------------------------
# Live path is now wired (inline-excerpt Runner). Construction stays
# ADK-free; PORTFOLIO_LIVE=0 keeps the mock as the server default.
# ---------------------------------------------------------------------------


def test_make_live_portfolio_returns_callable_without_adk():
    """`make_live_portfolio` returns a working agent closure. The google-adk
    / google-genai imports are deferred into the closure body, so
    construction (and this test) does not require google-adk or Vertex —
    only an actual invocation does. The closure is signature-compatible with
    the mock: `(list[ContractInput]) -> PortfolioReport`."""
    agent = PA.make_live_portfolio()
    assert callable(agent)


# ---------------------------------------------------------------------------
# Cluster invariants — the demo-line guarantees
# ---------------------------------------------------------------------------


def test_at_least_one_cluster():
    agent = PA.make_mock_portfolio()
    report = agent([])
    assert len(report.clusters) >= 1


def test_demo_line_holds_four_clusters_and_named_outlier():
    """The voiceover names 'four MAE-carveout clusters and flags deal seventeen
    as the outlier.' Pin the cluster count + the named outlier.
    """
    agent = PA.make_mock_portfolio()
    report = agent([])
    assert len(report.clusters) == 4, (
        f"Demo line names FOUR clusters; mock returns {len(report.clusters)}. "
        f"Update the voiceover or the fixture together."
    )
    outlier_ids = {o.deal_id for o in report.outliers}
    assert "akorn-fresenius" in outlier_ids, (
        "Demo line names the outlier by reference to the Akorn fact "
        "pattern. The canonical outlier is the akorn-fresenius row."
    )


def test_every_cluster_member_appears_in_fixture():
    """No hallucinated deal_ids — every member must trace to source."""
    agent = PA.make_mock_portfolio()
    report = agent([])
    fixture_ids = {c["deal_id"] for c in PA.load_sample_contracts()}
    for cluster in report.clusters:
        for member in cluster.member_deal_ids:
            assert member in fixture_ids, (
                f"Cluster {cluster.cluster_id!r} member {member!r} "
                f"is not in the sample fixture. Hallucinated deal_id."
            )


def test_every_outlier_appears_in_fixture():
    agent = PA.make_mock_portfolio()
    report = agent([])
    fixture_ids = {c["deal_id"] for c in PA.load_sample_contracts()}
    for outlier in report.outliers:
        assert outlier.deal_id in fixture_ids, (
            f"Outlier {outlier.deal_id!r} is not in the sample fixture."
        )


def test_clusters_and_outliers_are_mutually_exclusive():
    """A deal_id appears in AT MOST one cluster OR as an outlier — not both.
    The prompt instructs this; the test pins it as an invariant.
    """
    agent = PA.make_mock_portfolio()
    report = agent([])
    member_ids: list[str] = []
    for cluster in report.clusters:
        member_ids.extend(cluster.member_deal_ids)
    # No within-cluster duplicates either.
    assert len(member_ids) == len(set(member_ids)), (
        "A deal_id appears in more than one cluster (or twice in one). "
        "Clusters must partition the non-outlier portfolio."
    )
    member_set = set(member_ids)
    outlier_set = {o.deal_id for o in report.outliers}
    overlap = member_set & outlier_set
    assert overlap == set(), (
        f"Mutual-exclusion broken: {overlap!r} appear in both a cluster "
        f"and the outlier list."
    )


def test_clusters_have_at_least_two_members_each():
    """Prompt rule: a 1-member 'cluster' is an outlier, not a cluster."""
    agent = PA.make_mock_portfolio()
    report = agent([])
    for cluster in report.clusters:
        assert len(cluster.member_deal_ids) >= 2, (
            f"Cluster {cluster.cluster_id!r} has fewer than 2 members. "
            f"The prompt requires a 1-member group to be reported as an outlier."
        )


def test_representative_excerpts_within_length_budget():
    """Prompt caps `representative_clause_excerpt` at 400 chars."""
    agent = PA.make_mock_portfolio()
    report = agent([])
    for cluster in report.clusters:
        assert len(cluster.representative_clause_excerpt) <= 400, (
            f"Cluster {cluster.cluster_id!r} excerpt exceeds 400 chars "
            f"({len(cluster.representative_clause_excerpt)})."
        )
