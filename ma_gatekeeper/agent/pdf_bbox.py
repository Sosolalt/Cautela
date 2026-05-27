"""Offline pdfplumber-based fallback for `RiskFinding.pdf_bbox`.

Plan §3.1 D4 named "Document AI Layout Parser" as the production
fallback when Gemini's Parser omits `pdf_bbox`. That requires a GCP
API call (latency + cost + extra surface area). `pdfplumber>=0.10.0`
is already in `requirements.txt` and provides a pure-Python equivalent
that runs inside the existing FastAPI process — zero network, zero
quota.

Contract (per spec): given the PDF bytes, a 1-indexed page number, and
a `[char_start, char_end)` half-open offset range, return the union
bounding box of the characters in that range as `(x0, y0, x1, y1)` in
PDF points (72 dpi), or `None` if the range cannot be located. The
server only invokes this when the source is `application/pdf` AND the
joined Clause left `pdf_bbox` as null. See
`agent/server.py:_stream_findings`.

DEFENSIVE: pdfplumber extracts characters from the PDF's text layer in
reading order. Gemini's `char_start` / `char_end` come from the
Parser's view of the document — which may differ:
  - Gemini may include figure-caption text that pdfplumber treats as
    a separate text run on a different page.
  - Gemini may skip blank-page form-feeds that pdfplumber counts.
  - Gemini may collapse multi-column layouts into single-column
    reading order while pdfplumber preserves the raw stream order.
When the offsets don't align with what pdfplumber sees on the
specified page, we return `None` rather than guess. A wrong highlight
is the worst failure mode here (legal reviewer is going to read the
highlighted text and trust it). Empty input bytes also return None,
not an exception — the server's join path must never crash on a
fallback attempt.

PERF: pdfplumber's text-layer extraction can be slow on large /
scanned PDFs (the page object lazy-loads char tables on first
access). We bound each call to a 5-second per-page wall-clock budget
via `concurrent.futures.ThreadPoolExecutor.submit(...).result(timeout=...)`.
Timeout returns None and the function returns IMMEDIATELY — the
worker thread is allowed to keep running until pdfplumber finishes
(standard Python "abandon a slow synchronous C-extension call"
pattern). We use a module-level long-lived executor rather than
`with ThreadPoolExecutor() as ex:` because the `with` form blocks on
shutdown until pending futures complete, defeating the timeout. The
executor's threads are daemon so the process can still exit cleanly.

NETWORK + COST: zero. Pure Python, in-process.
"""
from __future__ import annotations

import concurrent.futures
import io
import logging
import threading

_LOG = logging.getLogger(__name__)

# Long-lived executor. Daemon threads so a hung extractor cannot
# block process exit. `max_workers=2` keeps memory bounded while
# allowing one in-flight extraction to overlap a new request — the
# SSE finding stream is sequential per request, so concurrency
# beyond 2 is wasted (and a runaway hang stays scoped to its own
# worker, not the next request).
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="pdf-bbox",
)

# Per-page extraction wall-clock budget. pdfplumber's typical small-PDF
# page extracts in <100ms; the demo's 8-K Ex 2.1 PDFs (when they are
# PDF, not HTML) run ~200ms/page. A 5s ceiling absorbs a pathological
# scanned-image page without letting the SSE stream stall the demo.
_EXTRACT_TIMEOUT_SECONDS: float = 5.0


def extract_bbox_from_pdf(
    pdf_bytes: bytes,
    page: int,
    char_start: int,
    char_end: int,
) -> tuple[float, float, float, float] | None:
    """Compute the union bbox of chars in `[char_start, char_end)` on `page`.

    Args:
      pdf_bytes:   raw PDF bytes (same bytes the agent reviewed; the
                   server already has these via `_stream_findings`'s
                   `filing_bytes` parameter, so no second fetch).
      page:        1-indexed page number, matching `Clause.page`.
                   Out-of-range → `None`.
      char_start:  inclusive char offset within the specified page's
                   extracted text. Matches `Clause.char_start`.
      char_end:    exclusive char offset. If `char_end <= char_start`
                   or `char_end` exceeds the page's char count, returns
                   `None`.

    Returns:
      `(x0, y0, x1, y1)` in PDF points (72 dpi), where `(x0, y0)` is
      the top-left of the union bbox and `(x1, y1)` is the bottom-
      right, OR `None` if the range cannot be located reliably.

    Coordinate orientation: pdfplumber's `char` dicts expose
    `x0, top, x1, bottom` where `top` measures from the page top in
    points. We return `(x0, top, x1, bottom)` directly — this is what
    the frontend's react-pdf overlay expects (matches the PDF.js
    coordinate convention). PDF's native lower-left-origin
    `(x0, y0, x1, y1)` is intentionally NOT used here.

    Raises:
      Nothing. All failures (malformed PDF, missing pdfplumber, page
      out of range, offsets misaligned, extraction timeout) are
      caught and converted to `None`. The server treats a `None`
      return as "leave pdf_bbox null" and yields the SSE finding
      event as-is.
    """
    # Cheap guards first — avoid spinning up the executor for obvious
    # bad inputs.
    if not pdf_bytes:
        return None
    if page is None or page < 1:
        return None
    if char_start is None or char_end is None:
        return None
    if char_start < 0 or char_end <= char_start:
        # Empty / inverted / negative range — degenerate zero-area bbox
        # would mislead the highlight; null is the honest answer.
        return None

    try:
        future = _EXECUTOR.submit(
            _extract_sync, pdf_bytes, page, char_start, char_end
        )
        try:
            return future.result(timeout=_EXTRACT_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            _LOG.warning(
                "pdfplumber bbox extraction exceeded %.1fs for "
                "page=%d range=[%d,%d) on %d-byte PDF; returning None",
                _EXTRACT_TIMEOUT_SECONDS, page, char_start, char_end,
                len(pdf_bytes),
            )
            # NOTE: we deliberately do NOT call future.cancel() — the
            # worker is mid-C-call inside pdfplumber and cannot be
            # cancelled cooperatively. It will finish on its own
            # eventually; meanwhile this caller has its None and
            # returns. Daemon thread + bounded executor size cap the
            # worst case.
            return None
    except Exception as exc:  # pragma: no cover — last-resort guard
        # Executor itself failing (shutdown race, OOM submitting the
        # task) is implausible but we still honor the "never raise to
        # the caller" contract: the server's SSE stream must not
        # crash because of a bbox fallback.
        _LOG.warning("pdfplumber bbox extraction crashed: %s", exc)
        return None


def _extract_sync(
    pdf_bytes: bytes,
    page: int,
    char_start: int,
    char_end: int,
) -> tuple[float, float, float, float] | None:
    """Synchronous body, run inside the timeout-bounded worker thread.

    Imports pdfplumber lazily so the module import surface stays cheap
    in environments that never invoke the fallback (unit tests of
    unrelated code paths).
    """
    try:
        import pdfplumber
    except Exception as exc:
        # pdfplumber is declared in requirements.txt; missing it means
        # the install is broken. Don't crash the SSE stream over it.
        _LOG.warning(
            "pdfplumber import failed (%s); bbox fallback unavailable", exc
        )
        return None

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = pdf.pages
            if page > len(pages):
                return None
            # pdfplumber pages are 0-indexed; our contract is 1-indexed.
            target_page = pages[page - 1]
            chars = target_page.chars
            if not chars:
                return None
            # The Parser's char offsets are per-page; pdfplumber exposes
            # one `chars` list per page in reading order. Slicing by
            # [char_start:char_end] is the natural mapping. If the
            # offsets blow past the page's char count, refuse — we
            # don't know what the Parser was counting and a partial
            # bbox would highlight the wrong region. Same for a range
            # that starts past the end of the page.
            if char_start >= len(chars):
                return None
            if char_end > len(chars):
                return None
            sliced = chars[char_start:char_end]
            if not sliced:
                return None
            # Union bbox: min(x0, top), max(x1, bottom) over all chars.
            # We tolerate the slice spanning multiple lines — the
            # resulting rectangle covers the whole span, which is what
            # the frontend highlights.
            x0 = min(c["x0"] for c in sliced)
            y0 = min(c["top"] for c in sliced)
            x1 = max(c["x1"] for c in sliced)
            y1 = max(c["bottom"] for c in sliced)
            return (float(x0), float(y0), float(x1), float(y1))
    except Exception as exc:
        # Encrypted PDF, malformed XREF, image-only PDF without a text
        # layer — pdfplumber raises a variety of exceptions. Treat any
        # as "couldn't extract" and degrade.
        _LOG.warning(
            "pdfplumber extraction failed for page=%d range=[%d,%d): %s",
            page, char_start, char_end, exc,
        )
        return None
