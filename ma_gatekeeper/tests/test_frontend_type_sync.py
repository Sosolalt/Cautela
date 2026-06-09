"""Defense-in-depth (Guard #3, frontend half): the TS `RiskFinding` interface
must never declare the eval-only field names (design/STATUTE_LAYER.md §2.3).

This is a lint, not the load-bearing guarantee — the SSE wire test
(tests/test_no_eval_leak.py) is. It fragment-extracts the `interface
RiskFinding { ... }` block specifically (NOT the whole file — the CitationRef
doc-comment legitimately mentions the eval-only names while explaining their
absence) and asserts none of them appear inside it.
"""
from __future__ import annotations

import re
from pathlib import Path

from agent.schemas import _EVAL_ONLY_FIELDS

_TYPES_TS = Path(__file__).resolve().parent.parent / "frontend" / "lib" / "types.ts"


def _risk_finding_interface_block() -> str:
    src = _TYPES_TS.read_text(encoding="utf-8")
    # Fields are flat (no nested `{`), so the first top-level `\n}` closes it.
    match = re.search(r"export interface RiskFinding \{(.*?)\n\}", src, re.DOTALL)
    assert match, "could not locate `export interface RiskFinding { ... }` in types.ts"
    return match.group(1)


def test_risk_finding_ts_interface_omits_eval_only_fields():
    block = _risk_finding_interface_block()
    for name in _EVAL_ONLY_FIELDS:
        assert name not in block, (
            f"{name} must NOT exist on the TS RiskFinding interface — it is "
            f"eval-only and must never reach the wire."
        )


def test_risk_finding_ts_interface_keeps_citation_ref():
    """The user-facing citation field SHOULD be on the wire shape."""
    assert "citation_ref" in _risk_finding_interface_block()
