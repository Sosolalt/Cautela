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

from pydantic import BaseModel, Field, field_validator


class AllowListEntry(BaseModel):
    """A pre-indexed demo deal. Mirror on the frontend lives in
    `frontend/lib/types.ts:Deal` — keep field names in sync."""

    id: str
    name: str
    filing: str
    cik: str
    # Pinned SEC-archive URL of this deal's merger-agreement EX-2.1
    # (mirrors data/edgar/manifest.json `source_url`). The fetch path GETs
    # this directly. Navigating to the company's *latest* 8-K does not work
    # for a closed merger — its most recent 8-K is a post-close filing with
    # no EX-2.1 — and EdgarTools' attachment.exhibit_number is not a reliable
    # "2.1" match; both were confirmed against live EDGAR for cik 718877.
    # Empty => fall back to the legacy latest-8-K EdgarTools search.
    # `exclude=True`: internal fetch detail — never serialized into the
    # /allow-list response (the frontend `Deal` type is {id,name,filing,cik}).
    ex21_url: str = Field(default="", exclude=True)

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
        ex21_url="https://www.sec.gov/Archives/edgar/data/718877/000110465922005154/tm223212d3_ex2-1.htm",
    ),
    AllowListEntry(
        id="pfizer_seagen",
        name="Pfizer / Seagen (2023)",
        filing="8-K/Ex 2.1",
        cik="0001060736",  # Seagen Inc. (f/k/a Seattle Genetics)
        ex21_url="https://www.sec.gov/Archives/edgar/data/1060736/000119312523068474/d467472dex21.htm",
    ),
    AllowListEntry(
        id="cisco_splunk",
        name="Cisco / Splunk (2024)",
        filing="8-K/Ex 2.1",
        cik="0001353283",  # Splunk Inc.
        ex21_url="https://www.sec.gov/Archives/edgar/data/1353283/000110465923102594/tm2326347d1_ex2-1.htm",
    ),
    AllowListEntry(
        id="exxon_pioneer",
        name="ExxonMobil / Pioneer Natural Resources (2024)",
        filing="8-K/Ex 2.1",
        cik="0001038357",  # Pioneer Natural Resources Co.
        ex21_url="https://www.sec.gov/Archives/edgar/data/1038357/000119312523253935/d417986dex21.htm",
    ),
    AllowListEntry(
        id="hpe_juniper",
        name="HPE / Juniper Networks (2025)",
        filing="8-K/Ex 2.1",
        cik="0001043604",  # Juniper Networks, Inc.
        ex21_url="https://www.sec.gov/Archives/edgar/data/1043604/000119312524005659/d107225dex21.htm",
    ),
]
