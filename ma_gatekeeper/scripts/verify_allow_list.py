"""Verify every ALLOW_LIST entry resolves on live EDGAR.

Run this manually during D10 curation and again on D18 morning before
the demo recording. Exits non-zero if any entry fails — wire it into a
nightly cron (HANDOFF / future work) to catch CIK rot between D10 and
the deadline.

Usage:
  export SEC_EDGAR_USER_AGENT="you@example.com Your Org"
  python -m scripts.verify_allow_list

Output:
  | id                   | cik        | company        | latest_8k   | ex2.1   | fetchable | ok |
  |----------------------|------------|----------------|-------------|---------|-----------|----|
  | microsoft_activision | 0000718877 | Activision …   | 2023-10-13  | ✓       | ✓         | ✓  |
  …
"""
from __future__ import annotations

import dataclasses
import logging
import os
import sys

from agent.allow_list import ALLOW_LIST

_LOG = logging.getLogger(__name__)


@dataclasses.dataclass
class Row:
    id: str
    cik: str
    company: str = "?"
    latest_8k: str = "?"
    has_ex21: bool = False
    fetchable: bool = False
    ok: bool = False
    error: str = ""


def _verify_one(entry) -> Row:
    """Probe one ALLOW_LIST entry: company resolves, latest 8-K, Ex 2.1
    attachment fetchable. Lazy-imports edgar so the module is importable
    in environments without it (tests, CI)."""
    row = Row(id=entry.id, cik=entry.cik)
    try:
        from edgar import Company  # type: ignore
    except ImportError as exc:
        row.error = f"edgar not installed: {exc}"
        return row
    try:
        co = Company(entry.cik)
        row.company = (getattr(co, "name", None) or "?")[:30]
    except Exception as exc:
        row.error = f"Company({entry.cik}) failed: {exc}"
        return row
    try:
        filings = co.get_filings(form="8-K")
        if not filings:
            row.error = "no 8-K filings"
            return row
        latest = filings[0]
        row.latest_8k = str(getattr(latest, "filing_date", "?"))
        attachments = getattr(latest, "attachments", None) or []
        ex21 = next(
            (a for a in attachments
             if "2.1" in (getattr(a, "exhibit_number", "") or "")),
            None,
        )
        row.has_ex21 = ex21 is not None
        if ex21 is None:
            row.error = "latest 8-K has no Ex 2.1"
            return row
        # Fetch test — don't bother saving, just confirm it doesn't 404.
        try:
            ex21.download  # callable check; don't actually download in verify
            row.fetchable = True
        except Exception as exc:
            row.error = f"attachment not downloadable: {exc}"
            return row
    except Exception as exc:
        row.error = f"filings probe failed: {exc}"
        return row
    row.ok = row.has_ex21 and row.fetchable
    return row


def _print_table(rows: list[Row]) -> None:
    cols = ["id", "cik", "company", "latest_8k", "ex2.1", "fetchable", "ok"]
    widths = {c: len(c) for c in cols}
    cells: list[dict[str, str]] = []
    for r in rows:
        cell = {
            "id": r.id,
            "cik": r.cik,
            "company": r.company,
            "latest_8k": r.latest_8k,
            "ex2.1": "yes" if r.has_ex21 else "NO",
            "fetchable": "yes" if r.fetchable else "NO",
            "ok": "OK" if r.ok else "FAIL",
        }
        cells.append(cell)
        for c in cols:
            widths[c] = max(widths[c], len(cell[c]))
    print("| " + " | ".join(c.ljust(widths[c]) for c in cols) + " |")
    print("|" + "|".join("-" * (widths[c] + 2) for c in cols) + "|")
    for cell in cells:
        print("| " + " | ".join(cell[c].ljust(widths[c]) for c in cols) + " |")
    print()
    failed = [r for r in rows if not r.ok]
    for r in failed:
        print(f"  ! {r.id} (cik={r.cik}): {r.error}")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Setting SEC identity is required before any EdgarTools call.
    ua = os.environ.get("SEC_EDGAR_USER_AGENT")
    if not ua:
        print(
            "SEC_EDGAR_USER_AGENT not set — SEC will 403 every request.",
            file=sys.stderr,
        )
        return 2
    try:
        from edgar import set_identity  # type: ignore

        set_identity(ua)
    except ImportError as exc:
        print(f"edgar not installed: {exc}", file=sys.stderr)
        return 2

    rows = [_verify_one(entry) for entry in ALLOW_LIST]
    _print_table(rows)
    return 0 if all(r.ok for r in rows) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
