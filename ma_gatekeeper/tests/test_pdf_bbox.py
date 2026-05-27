"""Tests for the offline pdfplumber fallback (`agent/pdf_bbox.py`).

Plan §3.1 D4 originally named Document AI Layout Parser as the
fallback when Gemini's Parser omits `pdf_bbox`. We swapped to
pdfplumber (already in requirements.txt, zero GCP API surface).
These tests pin the contract documented in `extract_bbox_from_pdf`:
  - 1-indexed page; out-of-range → None
  - half-open [char_start, char_end) slice over pdfplumber's per-page
    `chars` list
  - returns (x0, top, x1, bottom) in PDF points (top-left origin —
    matches PDF.js / react-pdf, NOT PDF native lower-left)
  - returns None (never raises) on every conceivable bad-input path

No live network, no real PDF synthesis. We monkeypatch
`pdfplumber.open` to a fake whose `pages[i].chars` is a known fixture
— the function under test is pure offset arithmetic over that list,
so the fake exercises the full code path.
"""
from __future__ import annotations

import sys
import types

import pytest


def _make_char(x0: float, top: float, x1: float, bottom: float) -> dict:
    """pdfplumber char dict has many fields; we only need bbox keys.
    The fallback ignores all other keys (text, fontname, size, etc.)."""
    return {"x0": x0, "top": top, "x1": x1, "bottom": bottom,
            "text": "x", "fontname": "Helvetica", "size": 12.0}


def _install_fake_pdfplumber(monkeypatch, pages_chars: list[list[dict]]):
    """Install a fake `pdfplumber` module whose `open(stream)` returns
    a context manager exposing a `.pages` list of objects with `.chars`.

    `pages_chars` is a list-of-lists: `pages_chars[i]` is the char list
    for the (0-indexed) i-th page. Returns the fake module for further
    assertions if needed.
    """
    class _FakePage:
        def __init__(self, chars):
            self.chars = chars

    class _FakePDF:
        def __init__(self):
            self.pages = [_FakePage(c) for c in pages_chars]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    fake = types.ModuleType("pdfplumber")
    fake.open = lambda _stream: _FakePDF()
    monkeypatch.setitem(sys.modules, "pdfplumber", fake)
    return fake


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_extract_bbox_returns_union_of_sliced_chars(monkeypatch):
    """The union bbox spans (min x0/top, max x1/bottom) of the slice.
    Half-open [1, 3) selects chars at indices 1 and 2 — i.e., "BC".
    B has bbox (20, 100, 30, 112); C has (30, 100, 40, 112).
    Union: (20, 100, 40, 112)."""
    page_chars = [
        _make_char(10, 100, 20, 112),   # 0: "A"
        _make_char(20, 100, 30, 112),   # 1: "B"
        _make_char(30, 100, 40, 112),   # 2: "C"
        _make_char(40, 100, 50, 112),   # 3: "D"
    ]
    _install_fake_pdfplumber(monkeypatch, [page_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    bbox = extract_bbox_from_pdf(b"%PDF-fake", page=1, char_start=1, char_end=3)
    assert bbox == (20.0, 100.0, 40.0, 112.0)


def test_extract_bbox_union_across_two_lines(monkeypatch):
    """When the slice spans a line break, the union rectangle covers
    both lines — exactly what the frontend highlights for a multi-line
    clause."""
    page_chars = [
        _make_char(10, 100, 20, 112),   # line 1
        _make_char(20, 100, 30, 112),   # line 1
        _make_char(10, 120, 20, 132),   # line 2 (lower on page)
    ]
    _install_fake_pdfplumber(monkeypatch, [page_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    bbox = extract_bbox_from_pdf(b"%PDF-fake", page=1, char_start=0, char_end=3)
    # Union: x0=10, top=100, x1=30, bottom=132.
    assert bbox == (10.0, 100.0, 30.0, 132.0)


def test_extract_bbox_single_char(monkeypatch):
    """A 1-char slice returns that char's bbox verbatim."""
    page_chars = [
        _make_char(50, 200, 58, 212),
        _make_char(60, 200, 68, 212),
    ]
    _install_fake_pdfplumber(monkeypatch, [page_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    bbox = extract_bbox_from_pdf(b"%PDF-fake", page=1, char_start=1, char_end=2)
    assert bbox == (60.0, 200.0, 68.0, 212.0)


# ---------------------------------------------------------------------------
# Bad inputs — must return None, never raise
# ---------------------------------------------------------------------------


def test_extract_bbox_returns_none_on_empty_bytes(monkeypatch):
    """Empty bytes never reach pdfplumber.open — cheap guard."""
    _install_fake_pdfplumber(monkeypatch, [[]])
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(b"", page=1, char_start=0, char_end=10) is None


def test_extract_bbox_returns_none_on_zero_page(monkeypatch):
    """1-indexed: page=0 is invalid."""
    _install_fake_pdfplumber(monkeypatch, [[_make_char(0, 0, 1, 1)]])
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(b"%PDF-x", page=0, char_start=0, char_end=1) is None


def test_extract_bbox_returns_none_on_negative_char_start(monkeypatch):
    _install_fake_pdfplumber(monkeypatch, [[_make_char(0, 0, 1, 1)]])
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=-1, char_end=1) is None


def test_extract_bbox_returns_none_on_empty_range(monkeypatch):
    """char_end <= char_start = empty/inverted range."""
    _install_fake_pdfplumber(monkeypatch, [[_make_char(0, 0, 1, 1)]])
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=5, char_end=5) is None
    assert extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=5, char_end=3) is None


def test_extract_bbox_returns_none_on_page_out_of_range(monkeypatch):
    """page=99 on a 2-page PDF → None, not IndexError."""
    _install_fake_pdfplumber(
        monkeypatch, [[_make_char(0, 0, 1, 1)], [_make_char(0, 0, 1, 1)]]
    )
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(b"%PDF-x", page=99, char_start=0, char_end=1) is None


def test_extract_bbox_returns_none_when_char_start_at_or_past_page_end(monkeypatch):
    """char_start == len(chars) is a degenerate "starts past end" range
    even though char_end - char_start would be positive. Guard pinned
    so a future refactor that drops the `if char_start >= len(chars)`
    branch is caught — without it, `chars[50:51]` on a 50-char page
    returns [] silently and the caller's `if not sliced` catches it,
    but pinning the more explicit guard is better."""
    page_chars = [_make_char(0, 0, 10, 12) for _ in range(50)]
    _install_fake_pdfplumber(monkeypatch, [page_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(
        b"%PDF-x", page=1, char_start=50, char_end=51
    ) is None
    assert extract_bbox_from_pdf(
        b"%PDF-x", page=1, char_start=100, char_end=101
    ) is None


def test_extract_bbox_returns_none_when_offsets_exceed_page_chars(monkeypatch):
    """Spec: 'pdfplumber's char offsets may not match Gemini's
    char_start/char_end exactly ... returns None on mismatch rather
    than guessing.' If char_end exceeds the page's char count we have
    no idea what the Parser was counting; degrade rather than
    return a partial bbox that would highlight the wrong text."""
    page_chars = [_make_char(0, 0, 10, 12) for _ in range(50)]
    _install_fake_pdfplumber(monkeypatch, [page_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(
        b"%PDF-x", page=1, char_start=0, char_end=500
    ) is None


def test_extract_bbox_returns_none_on_empty_page(monkeypatch):
    """An image-only / scanned page has no text layer; chars list is
    empty. Must return None, not crash on min()/max() of empty seq."""
    _install_fake_pdfplumber(monkeypatch, [[]])
    from agent.pdf_bbox import extract_bbox_from_pdf

    assert extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=0, char_end=10) is None


def test_extract_bbox_returns_none_when_pdfplumber_raises(monkeypatch):
    """A malformed/encrypted PDF makes pdfplumber.open raise. The
    fallback swallows it so a single bad PDF doesn't blow up the SSE
    stream — the frontend already handles `pdf_bbox: null` gracefully.
    """
    fake = types.ModuleType("pdfplumber")

    def _boom(_stream):
        raise RuntimeError("encrypted or malformed")

    fake.open = _boom
    monkeypatch.setitem(sys.modules, "pdfplumber", fake)
    from agent.pdf_bbox import extract_bbox_from_pdf

    # No raise — returns None.
    result = extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=0, char_end=10)
    assert result is None


def test_extract_bbox_returns_none_when_pdfplumber_missing(monkeypatch):
    """If pdfplumber isn't installed (defensive — it's in
    requirements.txt), the helper degrades to None instead of
    propagating ImportError. A missing optional dep should never
    crash the inference pipeline."""
    # Block the import — even if the real module is installed in the
    # venv, this monkeypatch routes the import attempt to a path that
    # raises.
    monkeypatch.setitem(sys.modules, "pdfplumber", None)
    from agent.pdf_bbox import extract_bbox_from_pdf

    result = extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=0, char_end=10)
    assert result is None


# ---------------------------------------------------------------------------
# Return-type pins
# ---------------------------------------------------------------------------


def test_extract_bbox_returns_floats(monkeypatch):
    """The return tuple is (float, float, float, float). Pydantic's
    `tuple[float, float, float, float] | None` accepts both int and
    float, but pinning floats prevents accidental int-truncation in
    a future refactor (e.g., `int(min(...))` would silently floor)."""
    page_chars = [_make_char(10, 100, 20, 112)]
    _install_fake_pdfplumber(monkeypatch, [page_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    bbox = extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=0, char_end=1)
    assert bbox is not None
    assert all(isinstance(v, float) for v in bbox), bbox


def test_extract_bbox_preserves_pdfjs_coordinate_orientation(monkeypatch):
    """We return (x0, top, x1, bottom) — top-left origin, matching
    PDF.js / react-pdf. A regression to PDF-native lower-left (y0,
    y1 swapped or flipped against page height) would silently
    mis-highlight every clause."""
    page_chars = [_make_char(10, 50, 20, 70)]  # top=50, bottom=70
    _install_fake_pdfplumber(monkeypatch, [page_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    bbox = extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=0, char_end=1)
    # top (50) < bottom (70) — i.e., y increases downward, matching
    # PDF.js. If someone flipped to PDF-native, top would be >
    # bottom or the values would be transformed by page height.
    assert bbox is not None
    _, top, _, bottom = bbox
    assert top < bottom, (
        f"top ({top}) should be < bottom ({bottom}) under PDF.js "
        "convention; regression to PDF-native lower-left detected"
    )


# ---------------------------------------------------------------------------
# Multi-page isolation — requested range stays on the specified page
# ---------------------------------------------------------------------------
# Pinned by Builder B (defensive spec): multi-page bboxes don't make
# sense (PDF highlights are per-page rectangles). The function MUST
# never silently fall through to page 2's chars when page 1's are
# insufficient. If it did, the bbox could span two coordinate frames
# (each page has its own (0,0) origin) and produce a garbage rectangle.


def test_chars_only_pulled_from_specified_page(monkeypatch):
    """When page 1 is short on chars, the function does NOT consult
    page 2 to fill the request. Returns None rather than guess."""
    page1_chars = [
        _make_char(10, 100, 20, 112),
        _make_char(20, 100, 30, 112),
    ]
    page2_chars = [
        _make_char(100, 200, 110, 212),
        _make_char(110, 200, 120, 212),
        _make_char(120, 200, 130, 212),
    ]
    _install_fake_pdfplumber(monkeypatch, [page1_chars, page2_chars])
    from agent.pdf_bbox import extract_bbox_from_pdf

    # Page 1 only has 2 chars, but we ask for [0, 4). Must return None
    # — NOT a bbox that happens to include page 2's chars 0 and 1.
    assert (
        extract_bbox_from_pdf(b"%PDF-x", page=1, char_start=0, char_end=4)
        is None
    )

    # Sanity: page 2 standalone still works, with its own coordinates.
    assert extract_bbox_from_pdf(
        b"%PDF-x", page=2, char_start=0, char_end=3
    ) == (100.0, 200.0, 130.0, 212.0)


# ---------------------------------------------------------------------------
# Timeout — slow pdfplumber returns None rather than stalling the SSE stream
# ---------------------------------------------------------------------------
# Pinned by Builder B (defensive spec): pdfplumber's text-layer
# extraction can be slow on large / scanned PDFs. The function must
# bound each call by a per-page wall-clock budget — a hung extractor
# would otherwise block the SSE stream and drag down the demo.


def test_slow_extraction_times_out_to_none(monkeypatch):
    """A pdfplumber.open that hangs past the per-page timeout returns
    None, and the function returns promptly (does NOT wait for the
    worker thread to finish)."""
    import time
    from agent import pdf_bbox as bbox_module

    fake = types.ModuleType("pdfplumber")

    def _slow_open(_stream):
        time.sleep(2.0)  # well past the lowered timeout

    fake.open = _slow_open
    monkeypatch.setitem(sys.modules, "pdfplumber", fake)
    # Override the module-level timeout to keep the test fast.
    monkeypatch.setattr(bbox_module, "_EXTRACT_TIMEOUT_SECONDS", 0.05)

    from agent.pdf_bbox import extract_bbox_from_pdf
    start = time.monotonic()
    result = extract_bbox_from_pdf(
        b"%PDF-x", page=1, char_start=0, char_end=10
    )
    elapsed = time.monotonic() - start

    assert result is None
    # Must return promptly — well under the fake's 2s sleep. 1s ceiling
    # is generous for CI jitter (default timeout is 0.05s + executor
    # startup overhead).
    assert elapsed < 1.5, (
        f"timeout fallback should return promptly, took {elapsed:.2f}s"
    )
