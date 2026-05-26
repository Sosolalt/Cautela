"""The 5 pre-indexed demo deals (plan §5.5).

Curate on D10 (HANDOFF.md). The 5 CIKs below are populated from public
M&A history but were NOT verified live against EDGAR at curation time
(the environment that generated them had no SEC network access). The
operator MUST run `python -m scripts.verify_allow_list` before D19 demo
recording to confirm each CIK resolves and each has a fetchable 8-K
Ex 2.1 attachment.

Extracted from `agent/server.py` so the schema + data live in a module
with no FastAPI dependency — that keeps the test surface (and the CI
install) lean. `server.py` re-exports `ALLOW_LIST` and `AllowListEntry`.

Curation criteria (each entry MUST satisfy all four before going live):
  1. The CIK resolves to a real EDGAR filer.
  2. The most recent 8-K Exhibit 2.1 attachment is reachable via
     EdgarTools (`Company(cik).get_filings(form="8-K")[0].attachments`).
  3. The agent surfaces at least one Block-tier finding on the filing
     (CoC, anti-assignment, MAC carve-out narrowing, or accelerated
     vesting). Verify by running `/review-by-deal` against the entry
     and inspecting the SSE stream.
  4. The deal is uncontroversial — no live litigation, ongoing
     regulatory action, or party that would object to inclusion in a
     publicly-recorded demo.

Empty `cik` means "not yet curated" and `/review-by-deal` will 503 on
it. `/allow-list` hides uncurated rows from the dropdown so the user
cannot click a deal that will fail.

Year-in-name convention: deal names include the year ("(2023)") so the
artifact reads as a specific historical filing months after the demo,
not a stale claim about "current" deals.
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class AllowListEntry(BaseModel):
    """A pre-indexed demo deal. Mirror on the frontend lives in
    `frontend/lib/types.ts:Deal` — keep field names in sync."""

    id: str
    name: str
    filing: str
    cik: str

    @field_validator("cik")
    @classmethod
    def _normalize_cik(cls, v: str) -> str:
        """Zero-pad to EDGAR's canonical 10-digit form.

        Operators commonly paste CIKs from the EDGAR URL bar (no leading
        zeros) or from EdgarTools output (zero-padded). Normalizing
        here means logs, span attributes, and frontend JSON all carry
        the same shape downstream.

        Empty string is the transition-period escape hatch — without it,
        the import-time construction of placeholder ALLOW_LIST entries
        would raise and crash the whole app on first import. Remove the
        empty-string branch once every entry has been curated.
        """
        if v == "":
            return v
        if not v.isdigit() or len(v) > 10:
            raise ValueError(f"cik {v!r} must be 1-10 digits (got len={len(v)})")
        return v.zfill(10)


# All 5 CIKs below were populated from public-record M&A history and are
# UNVERIFIED against live EDGAR. Run `scripts/verify_allow_list.py`
# before the D19 recording — see module docstring.
ALLOW_LIST: list[AllowListEntry] = [
    AllowListEntry(
        id="microsoft_activision",
        name="Microsoft / Activision Blizzard (2023)",
        filing="8-K/Ex 2.1",
        cik="0000718877",  # Activision Blizzard, Inc. (target filer)
    ),
    AllowListEntry(
        id="pfizer_seagen",
        name="Pfizer / Seagen (2023)",
        filing="8-K/Ex 2.1",
        cik="0001060736",  # Seagen Inc. (f/k/a Seattle Genetics)
    ),
    AllowListEntry(
        id="cisco_splunk",
        name="Cisco / Splunk (2024)",
        filing="8-K/Ex 2.1",
        cik="0001353283",  # Splunk Inc.
    ),
    AllowListEntry(
        id="exxon_pioneer",
        name="ExxonMobil / Pioneer Natural Resources (2024)",
        filing="8-K/Ex 2.1",
        cik="0001038357",  # Pioneer Natural Resources Co.
    ),
    AllowListEntry(
        id="hpe_juniper",
        name="HPE / Juniper Networks (2025)",
        filing="8-K/Ex 2.1",
        cik="0001043604",  # Juniper Networks, Inc.
    ),
]
