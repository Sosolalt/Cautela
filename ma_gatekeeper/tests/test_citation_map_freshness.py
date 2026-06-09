"""CI staleness gate for data/citation_map.json (design/STATUTE_LAYER.md §4.4 #3).

A citation's `verified_date` is a vendor representation that the cite was
checked against its primary source on that date. If the map goes stale, the
"verified against ... · <date>" microcopy becomes a "we stopped checking"
exhibit. This gate fails the build when the map ages past 180 days so the stamp
stays honest.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "citation_map.json"
_MAX_AGE = timedelta(days=180)


def _verified_dates() -> list[date]:
    data = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    entries = data.get("entries", []) if isinstance(data, dict) else data
    dates = [date.fromisoformat(e["verified_date"]) for e in entries]
    assert dates, "citation_map.json has no entries with verified_date"
    return dates


def test_citation_map_is_not_stale():
    """The newest entry must be within 180 days (prompt §Phase E assertion)."""
    cutoff = date.today() - _MAX_AGE
    dates = _verified_dates()
    assert max(dates) > cutoff, (
        f"citation_map.json newest verified_date {max(dates)} is older than "
        f"180 days (cutoff {cutoff}) — re-verify the map against primary sources."
    )


def test_no_individual_citation_entry_is_stale():
    """Stricter half of the gate: NO single entry may be older than 180 days
    (hard constraint: 'fail the build if ANY verified_date is older than 180
    days')."""
    cutoff = date.today() - _MAX_AGE
    stale = [d for d in _verified_dates() if d <= cutoff]
    assert not stale, f"stale citation_map.json entries (>180d): {sorted(stale)}"
