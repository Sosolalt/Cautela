"""HTTP-level tests for `/filing/{deal_id}` + the shared PDF cache.

Hits the FastAPI app via TestClient. The actual EdgarTools call is
monkeypatched to a deterministic byte payload — these tests verify the
route plumbing, error semantics, caching invariants, and response
headers without touching the network."""
from __future__ import annotations

import asyncio

import pytest

# Minimal real-looking PDF magic-bytes payload. pdfjs won't be parsing
# it in these tests, but the cache + ETag + length headers all work
# against it.
PDF_PAYLOAD = b"%PDF-1.7\n%fake-but-binary\n%%EOF\n"


def _clear_pdf_caches(srv) -> None:
    """Reset module-level cache state between tests."""
    srv._pdf_cache.clear()
    srv._pdf_locks.clear()
    srv._cik_unreachable.clear()


@pytest.fixture
def client(monkeypatch):
    """A configured TestClient with passcode set, SEC marked ready, and
    _fetch_filing_pdf stubbed to return PDF_PAYLOAD."""
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode")
    from agent import server as srv
    from fastapi.testclient import TestClient

    async def fake_fetch(cik: str) -> bytes:
        return PDF_PAYLOAD

    with TestClient(srv.app) as c:
        monkeypatch.setattr(srv, "_sec_ready", True)
        monkeypatch.setattr(srv, "_fetch_filing_pdf", fake_fetch)
        _clear_pdf_caches(srv)
        yield c, srv


def _headers() -> dict[str, str]:
    return {"X-Demo-Passcode": "test-passcode"}


def test_pdf_proxy_returns_200_and_pdf_bytes(client):
    c, srv = client
    # Use the first curated entry (post-Issue-1 they're all curated).
    deal = srv.ALLOW_LIST[0]
    resp = c.get(f"/filing/{deal.id}", headers=_headers())
    assert resp.status_code == 200, resp.text
    assert resp.content == PDF_PAYLOAD
    assert resp.headers["content-type"].startswith("application/pdf")


def test_pdf_proxy_sets_pdfjs_friendly_headers(client):
    c, srv = client
    deal = srv.ALLOW_LIST[0]
    resp = c.get(f"/filing/{deal.id}", headers=_headers())
    assert resp.headers["content-disposition"].startswith("inline")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["cross-origin-resource-policy"] == "cross-origin"
    assert "immutable" in resp.headers["cache-control"]
    assert resp.headers["etag"].startswith('W/"')


def test_pdf_proxy_returns_304_on_matching_etag(client):
    c, srv = client
    deal = srv.ALLOW_LIST[0]
    first = c.get(f"/filing/{deal.id}", headers=_headers())
    etag = first.headers["etag"]
    second = c.get(
        f"/filing/{deal.id}",
        headers={**_headers(), "If-None-Match": etag},
    )
    assert second.status_code == 304
    assert second.content == b""


def test_pdf_proxy_unknown_deal_returns_404(client):
    c, _ = client
    resp = c.get("/filing/no_such_deal", headers=_headers())
    assert resp.status_code == 404


def test_pdf_proxy_rejects_invalid_path_chars(client):
    """Pydantic Path pattern `^[a-z0-9_]+$` rejects upper-case, dashes,
    dots, slashes — defense in depth even though ALLOW_LIST lookup is
    safe on its own."""
    c, _ = client
    resp = c.get("/filing/UPPERCASE", headers=_headers())
    assert resp.status_code == 422
    resp2 = c.get("/filing/has-dash", headers=_headers())
    assert resp2.status_code == 422


def test_pdf_proxy_uncurated_returns_503(client, monkeypatch):
    c, srv = client
    from agent.allow_list import AllowListEntry

    synthetic = AllowListEntry(
        id="synthetic_uncurated", name="(test)", filing="8-K/Ex 2.1", cik=""
    )
    monkeypatch.setattr(srv, "ALLOW_LIST", [*srv.ALLOW_LIST, synthetic])
    resp = c.get("/filing/synthetic_uncurated", headers=_headers())
    assert resp.status_code == 503
    assert "not yet curated" in resp.text.lower()


def test_pdf_proxy_cik_unreachable_returns_503(client):
    c, srv = client
    deal = srv.ALLOW_LIST[0]
    srv._cik_unreachable.add(deal.cik)
    resp = c.get(f"/filing/{deal.id}", headers=_headers())
    assert resp.status_code == 503
    assert "lifespan validation" in resp.text.lower()
    srv._cik_unreachable.discard(deal.cik)


def test_pdf_proxy_edgartools_error_returns_502(client, monkeypatch):
    c, srv = client

    async def boom(cik: str) -> bytes:
        raise RuntimeError("EDGAR 5xx")

    monkeypatch.setattr(srv, "_fetch_filing_pdf", boom)
    deal = srv.ALLOW_LIST[0]
    resp = c.get(f"/filing/{deal.id}", headers=_headers())
    assert resp.status_code == 502
    assert "edgartools" in resp.text.lower()


def test_pdf_proxy_timeout_returns_504(client, monkeypatch):
    c, srv = client

    async def hang(cik: str) -> bytes:
        await asyncio.sleep(60.0)  # would block longer than the timeout
        return b""

    monkeypatch.setattr(srv, "_fetch_filing_pdf", hang)
    monkeypatch.setattr(srv, "_PDF_FETCH_TIMEOUT_SECONDS", 0.05)
    deal = srv.ALLOW_LIST[0]
    resp = c.get(f"/filing/{deal.id}", headers=_headers())
    assert resp.status_code == 504


def test_pdf_proxy_requires_passcode(client):
    c, srv = client
    deal = srv.ALLOW_LIST[0]
    resp = c.get(f"/filing/{deal.id}")  # no header
    assert resp.status_code == 401


def test_pdf_cache_de_dups_concurrent_fetches(monkeypatch):
    """Per-key asyncio.Lock means N concurrent calls to _get_artifact_cached
    on the same cik invoke `_fetch_filing_pdf` exactly once. Without
    this guard, the demo's "/review-by-deal + /pdf-proxy fire within
    50ms" pattern would double-hit SEC and risk the 10 req/s throttle."""
    from agent import server as srv

    call_count = 0

    async def slow_fetch(cik: str) -> bytes:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.02)
        return PDF_PAYLOAD

    monkeypatch.setattr(srv, "_fetch_filing_pdf", slow_fetch)
    _clear_pdf_caches(srv)

    async def race():
        return await asyncio.gather(
            srv._get_artifact_cached("0000718877"),
            srv._get_artifact_cached("0000718877"),
            srv._get_artifact_cached("0000718877"),
        )

    results = asyncio.run(race())
    # Cache now stores (bytes, mime_type) tuples; PDF_PAYLOAD starts
    # with `%PDF-` so the sniffer returns application/pdf.
    assert all(r == (PDF_PAYLOAD, "application/pdf") for r in results)
    assert call_count == 1, f"expected 1 EdgarTools fetch, got {call_count}"


# ---------------------------------------------------------------------------
# /filing serves the actual mime type (HTML or PDF), not always application/pdf
# ---------------------------------------------------------------------------


HTML_PAYLOAD = (
    b'<!doctype html><html><head><title>EX-2.1</title></head>'
    b'<body><p>This Agreement and Plan of Merger...</p></body></html>'
)


def test_filing_returns_html_with_text_html_mime(monkeypatch):
    """3/3 sampled 2024 8-K Ex 2.1 attachments are HTML. The route must
    surface that to the frontend so the iframe path (not the broken
    react-pdf path) renders the content."""
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode")
    from agent import server as srv
    from fastapi.testclient import TestClient

    async def html_fetch(cik):
        return HTML_PAYLOAD

    with TestClient(srv.app) as c:
        monkeypatch.setattr(srv, "_sec_ready", True)
        monkeypatch.setattr(srv, "_fetch_filing_pdf", html_fetch)
        _clear_pdf_caches(srv)
        deal = srv.ALLOW_LIST[0]
        resp = c.get(f"/filing/{deal.id}", headers=_headers())
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert resp.headers["content-disposition"].endswith('.html"')


def test_filing_pdf_disposition_extension(monkeypatch):
    """When the artifact is a PDF the filename extension should be `.pdf`
    so the browser's Save As dialog produces something sensible."""
    monkeypatch.setenv("DEMO_PASSCODE", "test-passcode")
    from agent import server as srv
    from fastapi.testclient import TestClient

    async def pdf_fetch(cik):
        return PDF_PAYLOAD

    with TestClient(srv.app) as c:
        monkeypatch.setattr(srv, "_sec_ready", True)
        monkeypatch.setattr(srv, "_fetch_filing_pdf", pdf_fetch)
        _clear_pdf_caches(srv)
        deal = srv.ALLOW_LIST[0]
        resp = c.get(f"/filing/{deal.id}", headers=_headers())
    assert resp.headers["content-disposition"].endswith('.pdf"')


# ---------------------------------------------------------------------------
# Magic-byte mime sniffer unit tests
# ---------------------------------------------------------------------------


def test_sniff_mime_recognizes_pdf_magic():
    from agent.server import _sniff_mime

    assert _sniff_mime(b"%PDF-1.7\nrest") == "application/pdf"


def test_sniff_mime_recognizes_html_doctype():
    from agent.server import _sniff_mime

    assert _sniff_mime(b"<!doctype html>\n<html></html>") == "text/html"


def test_sniff_mime_recognizes_html_with_bom():
    from agent.server import _sniff_mime

    # BOM-prefixed HTML — should still detect as html.
    assert _sniff_mime(b"\xef\xbb\xbf<html><body/>") == "text/html"


def test_sniff_mime_defaults_to_html_for_unknown():
    """Mislabeling unknown bytes as PDF produces a 'broken PDF' toast
    that hides the real content; HTML is the empirical 2024 majority
    and the iframe path degrades better than the pdf viewer path."""
    from agent.server import _sniff_mime

    assert _sniff_mime(b"garbage bytes with no magic") == "text/html"


def test_sniff_mime_handles_xml_declarations():
    from agent.server import _sniff_mime

    assert _sniff_mime(b'<?xml version="1.0"?>\n<root/>') == "text/html"
