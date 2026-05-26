"""Tests for the inline-vs-Files-API decision in `_build_gemini_part`.

The 5-deal demo HTML files (~2 MB each) MUST stay on the inline path
or every demo click pays a 1–3 s Files-API upload penalty. Large PDFs
(>5 MB application/pdf, or any blob >8 MB) MUST switch to Files API
or Gemini silently truncates pages past ~20 — a clean-looking review
of a partial document is the worst failure mode the legal reviewer
flagged.

These tests pin the threshold without making real network calls; the
upload is stubbed via monkeypatch.
"""
from __future__ import annotations

import asyncio
import sys
import types

import pytest


def _ensure_genai_stub(monkeypatch):
    """Stub `google.genai` so importing the helper functions doesn't
    require the real SDK. Returns the stub `types` module so tests can
    inspect what `Part.*` was constructed."""
    fake_types = types.SimpleNamespace()

    class _Part:
        def __init__(self, *, kind, **kw):
            self.kind = kind
            self.__dict__.update(kw)

        @classmethod
        def from_bytes(cls, *, data, mime_type):
            return cls(kind="bytes", data=data, mime_type=mime_type)

        @classmethod
        def from_uri(cls, *, file_uri, mime_type):
            return cls(kind="uri", file_uri=file_uri, mime_type=mime_type)

    fake_types.Part = _Part
    fake_types.UploadFileConfig = lambda **kw: kw

    fake_genai = types.SimpleNamespace(types=fake_types)
    monkeypatch.setitem(sys.modules, "google", types.SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)
    return fake_types


def _clear_caches(srv):
    srv._files_api_uri_cache.clear()
    srv._files_api_locks.clear()


def test_should_use_files_api_small_html_returns_false():
    from agent.server import _should_use_files_api

    assert _should_use_files_api(b"x" * (2 * 1024 * 1024), "text/html") is False


def test_should_use_files_api_huge_blob_returns_true():
    from agent.server import _should_use_files_api

    # 9 MB > 8 MB threshold regardless of mime
    assert _should_use_files_api(b"x" * (9 * 1024 * 1024), "text/html") is True


def test_should_use_files_api_medium_pdf_returns_true():
    """6 MB PDF would silently truncate under inline; Files API takes it."""
    from agent.server import _should_use_files_api

    assert _should_use_files_api(b"x" * (6 * 1024 * 1024), "application/pdf") is True


def test_should_use_files_api_small_pdf_returns_false():
    from agent.server import _should_use_files_api

    assert _should_use_files_api(b"x" * (1 * 1024 * 1024), "application/pdf") is False


def test_build_gemini_part_inline_for_small(monkeypatch):
    """The 5-deal HTML hot path. No upload, no polling — just bytes
    wrapped in Part.from_bytes."""
    fake_types = _ensure_genai_stub(monkeypatch)
    from agent import server as srv

    _clear_caches(srv)
    data = b"<html>small</html>"
    part = asyncio.run(srv._build_gemini_part(data, "text/html"))
    assert part.kind == "bytes"
    assert part.data == data
    assert part.mime_type == "text/html"


def test_build_gemini_part_files_api_for_large(monkeypatch):
    """Large blob path: upload sync-stub returns immediately ACTIVE,
    helper returns Part.from_uri with the stub URI."""
    fake_types = _ensure_genai_stub(monkeypatch)
    from agent import server as srv

    _clear_caches(srv)

    class _FakeFile:
        def __init__(self):
            self.name = "files/abc123"
            self.uri = "https://generativelanguage.googleapis.com/v1beta/files/abc123"
            self.state = "ACTIVE"

    class _FakeClient:
        def __init__(self):
            self.files = self

        def upload(self, *, file, config):
            return _FakeFile()

        def get(self, *, name):
            return _FakeFile()

    fake_genai = sys.modules["google.genai"]
    fake_genai.Client = lambda **kw: _FakeClient()

    big = b"x" * (9 * 1024 * 1024)
    part = asyncio.run(srv._build_gemini_part(big, "text/html"))
    assert part.kind == "uri"
    assert part.file_uri.endswith("files/abc123")
    assert part.mime_type == "text/html"


def test_files_api_cache_dedupes_uploads(monkeypatch):
    """Same bytes uploaded twice → second call returns the cached URI;
    the SDK is called exactly once. Important for the 5-deal demo where
    /review-by-deal and /filing fire on the same content within 50 ms."""
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv

    _clear_caches(srv)
    upload_count = 0

    class _FakeFile:
        name = "files/dedupe"
        uri = "https://example/files/dedupe"
        state = "ACTIVE"

    class _FakeClient:
        def __init__(self):
            self.files = self

        def upload(self, *, file, config):
            nonlocal upload_count
            upload_count += 1
            return _FakeFile()

        def get(self, *, name):
            return _FakeFile()

    sys.modules["google.genai"].Client = lambda **kw: _FakeClient()

    big = b"y" * (9 * 1024 * 1024)

    async def race():
        return await asyncio.gather(
            srv._build_gemini_part(big, "text/html"),
            srv._build_gemini_part(big, "text/html"),
            srv._build_gemini_part(big, "text/html"),
        )

    parts = asyncio.run(race())
    assert all(p.kind == "uri" for p in parts)
    assert upload_count == 1, f"expected 1 Files API upload, got {upload_count}"


def test_files_api_polls_until_active(monkeypatch):
    """When the SDK returns PROCESSING, the helper polls via
    `client.files.get(name=...)` until ACTIVE. Verifies the polling
    loop actually fires."""
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv

    _clear_caches(srv)
    get_calls = 0

    class _FakeFile:
        def __init__(self, state):
            self.name = "files/polling"
            self.uri = "https://example/files/polling"
            self.state = state

    class _FakeClient:
        def __init__(self):
            self.files = self

        def upload(self, *, file, config):
            return _FakeFile("PROCESSING")

        def get(self, *, name):
            nonlocal get_calls
            get_calls += 1
            # Settle on the second poll.
            return _FakeFile("ACTIVE" if get_calls >= 2 else "PROCESSING")

    sys.modules["google.genai"].Client = lambda **kw: _FakeClient()

    big = b"z" * (9 * 1024 * 1024)
    part = asyncio.run(srv._build_gemini_part(big, "text/html"))
    assert part.kind == "uri"
    assert get_calls >= 2, f"expected polling, got {get_calls} get() calls"


def test_files_api_failed_state_raises_502(monkeypatch):
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv
    from fastapi import HTTPException

    _clear_caches(srv)

    class _FakeFile:
        name = "files/failed"
        uri = "https://example/files/failed"
        state = "FAILED"

    class _FakeClient:
        def __init__(self):
            self.files = self

        def upload(self, *, file, config):
            return _FakeFile()

        def get(self, *, name):
            return _FakeFile()

    sys.modules["google.genai"].Client = lambda **kw: _FakeClient()

    big = b"w" * (9 * 1024 * 1024)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(srv._build_gemini_part(big, "text/html"))
    assert exc_info.value.status_code == 502


def test_files_api_timeout_raises_504(monkeypatch):
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv
    from fastapi import HTTPException

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_POLL_TOTAL_SECONDS", 0.1)

    class _FakeFile:
        name = "files/stuck"
        uri = "https://example/files/stuck"
        state = "PROCESSING"

    class _FakeClient:
        def __init__(self):
            self.files = self

        def upload(self, *, file, config):
            return _FakeFile()

        def get(self, *, name):
            return _FakeFile()  # never reaches ACTIVE

    sys.modules["google.genai"].Client = lambda **kw: _FakeClient()

    big = b"v" * (9 * 1024 * 1024)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(srv._build_gemini_part(big, "text/html"))
    assert exc_info.value.status_code == 504
