"""Schema + curation tests for the ALLOW_LIST.

The /review-by-deal endpoint trusts the ALLOW_LIST shape; these tests
catch shape drift (typos in keys, dropped fields) before it manifests
as a 500 mid-demo. The "cik must be a real EDGAR identifier" check is
integration-only and lives in HANDOFF D10.

Imports `agent.allow_list` directly (no FastAPI / ADK / Phoenix surface)
so the CI test job stays slim."""
from __future__ import annotations

import re

import pytest

from agent.allow_list import ALLOW_LIST


def test_allow_list_has_exactly_five_entries():
    """Plan §5.5 + pre-commitment: voiceover says 'five pre-indexed deals'."""
    assert len(ALLOW_LIST) == 5


def test_allow_list_entry_ids_are_unique():
    ids = [d.id for d in ALLOW_LIST]
    assert len(set(ids)) == len(ids), f"duplicate ids in ALLOW_LIST: {ids}"


def test_allow_list_entry_id_format():
    """IDs must be safe for use in URL paths and dropdown values — no
    spaces, slashes, or special chars. `^[a-z0-9_]+$` is the contract."""
    rx = re.compile(r"^[a-z0-9_]+$")
    for d in ALLOW_LIST:
        assert rx.match(d.id), f"id {d.id!r} fails URL-safe regex"


def test_allow_list_filing_field_normalized():
    """Filing must mention 8-K Ex 2.1 — that's the only attachment shape
    `_fetch_filing_pdf` knows how to pull. Free-text filings break the
    demo silently."""
    for d in ALLOW_LIST:
        assert "8-K" in d.filing, f"deal {d.id} not an 8-K filing"


def test_allow_list_all_entries_curated():
    """Post-D10 invariant: every entry has a real 10-digit CIK and a
    human-readable name (no '(curated)' placeholders left). Inverts the
    pre-curation invariant — if this regresses to empty CIKs, the
    /review-by-deal path silently 503s on every call."""
    rx = re.compile(r"^\d{10}$")
    for d in ALLOW_LIST:
        assert d.name != "(curated)", (
            f"deal {d.id} still has placeholder name '(curated)'"
        )
        assert d.cik != "", f"deal {d.id} has empty cik"
        assert d.cik != "0" * 10, f"deal {d.id} cik is all-zero (placeholder)"
        assert rx.fullmatch(d.cik), (
            f"deal {d.id} cik={d.cik!r} not zero-padded 10-digit form"
        )


def test_cik_validator_zero_pads():
    """Operators paste CIKs from the EDGAR URL bar (unpadded). Normalize
    here so downstream logs / span attributes / frontend JSON carry the
    same canonical 10-digit form."""
    from agent.allow_list import AllowListEntry

    entry = AllowListEntry(id="x", name="X", filing="8-K", cik="789019")
    assert entry.cik == "0000789019"


def test_cik_validator_accepts_already_padded():
    from agent.allow_list import AllowListEntry

    entry = AllowListEntry(id="x", name="X", filing="8-K", cik="0000789019")
    assert entry.cik == "0000789019"


def test_cik_validator_allows_empty_during_transition():
    """Empty string is the escape hatch — without it, importing a module
    that holds placeholder rows raises and crashes the app."""
    from agent.allow_list import AllowListEntry

    entry = AllowListEntry(id="x", name="X", filing="8-K", cik="")
    assert entry.cik == ""


def test_cik_validator_rejects_too_long():
    from agent.allow_list import AllowListEntry
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AllowListEntry(id="x", name="X", filing="8-K", cik="12345678901")


def test_cik_validator_rejects_non_digits():
    from agent.allow_list import AllowListEntry
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AllowListEntry(id="x", name="X", filing="8-K", cik="MSFT")


def test_allow_list_entry_model_dump_is_frontend_compatible():
    """The frontend `Deal` type (frontend/lib/types.ts) expects exactly
    these 4 keys. Drift here means the dropdown silently breaks."""
    expected = {"id", "name", "filing", "cik"}
    for d in ALLOW_LIST:
        assert set(d.model_dump().keys()) == expected, (
            f"deal {d.id} dump keys drifted from frontend Deal type"
        )


# ---------------------------------------------------------------------------
# HTTP-level: /review-by-deal must 503 (not 500, not 200) on uncurated deals.
# ---------------------------------------------------------------------------


def test_review_by_deal_uncurated_returns_503(monkeypatch):
    """Asymmetric-loss invariant at the HTTP layer: an uncurated deal
    (cik=='') is the silent-failure mode for the demo dropdown. The
    contract is 503; a 500 would leak server internals into the UI and
    a 200 would mean we tried to fetch from a malformed CIK.

    Now that all real ALLOW_LIST entries are curated, we monkeypatch a
    synthetic uncurated entry onto srv.ALLOW_LIST for this test only —
    that keeps the HTTP-layer guarantee tested without re-introducing a
    placeholder row to the deployed list."""
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode")
    from agent import server as srv
    from agent.allow_list import AllowListEntry
    from fastapi.testclient import TestClient

    synthetic = AllowListEntry(
        id="synthetic_uncurated", name="(test)", filing="8-K/Ex 2.1", cik=""
    )
    monkeypatch.setattr(srv, "ALLOW_LIST", [*srv.ALLOW_LIST, synthetic])

    with TestClient(srv.app) as client:
        # Lifespan runs on __enter__ and resets _sec_ready based on
        # whether `edgar` imports — set after enter so the lifespan
        # doesn't undo our monkeypatch.
        monkeypatch.setattr(srv, "_sec_ready", True)
        resp = client.post(
            "/review-by-deal",
            headers={"X-Demo-Passcode": "test-passcode"},
            json={"deal_id": "synthetic_uncurated"},
        )
    assert resp.status_code == 503, (
        f"expected 503 on uncurated deal, got {resp.status_code}: {resp.text}"
    )
    assert "not yet curated" in resp.text.lower()


def test_allow_list_endpoint_hides_uncurated_by_default(monkeypatch):
    """The dropdown must NOT surface uncurated rows by default; otherwise
    a user clicks a deal that 503s. include_uncurated=1 is the explicit
    operator-tooling escape hatch."""
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode")
    from agent import server as srv
    from agent.allow_list import AllowListEntry
    from fastapi.testclient import TestClient

    synthetic = AllowListEntry(
        id="synthetic_uncurated", name="(test)", filing="8-K/Ex 2.1", cik=""
    )
    monkeypatch.setattr(srv, "ALLOW_LIST", [*srv.ALLOW_LIST, synthetic])

    with TestClient(srv.app) as client:
        default_resp = client.get(
            "/allow-list", headers={"X-Demo-Passcode": "test-passcode"}
        )
        opt_in_resp = client.get(
            "/allow-list?include_uncurated=1",
            headers={"X-Demo-Passcode": "test-passcode"},
        )
    assert default_resp.status_code == 200
    default_ids = {d["id"] for d in default_resp.json()["deals"]}
    assert "synthetic_uncurated" not in default_ids
    opt_in_ids = {d["id"] for d in opt_in_resp.json()["deals"]}
    assert "synthetic_uncurated" in opt_in_ids


def test_review_by_deal_unknown_returns_404(monkeypatch):
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode")
    from agent import server as srv
    from fastapi.testclient import TestClient

    with TestClient(srv.app) as client:
        monkeypatch.setattr(srv, "_sec_ready", True)
        resp = client.post(
            "/review-by-deal",
            headers={"X-Demo-Passcode": "test-passcode"},
            json={"deal_id": "deal_does_not_exist"},
        )
    assert resp.status_code == 404


def test_allow_list_endpoint_returns_dump_compatible_shape(monkeypatch):
    """The /allow-list endpoint must serialize each entry as a dict with
    exactly the frontend's expected keys — not a Pydantic-tagged
    representation."""
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode")
    from agent import server as srv
    from fastapi.testclient import TestClient

    with TestClient(srv.app) as client:
        resp = client.get(
            "/allow-list", headers={"X-Demo-Passcode": "test-passcode"}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "deals" in body
    expected = {"id", "name", "filing", "cik"}
    for deal in body["deals"]:
        assert set(deal.keys()) == expected
