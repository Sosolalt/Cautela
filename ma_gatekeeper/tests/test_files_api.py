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


# ===========================================================================
# Files API URI TTL eviction — recovery from Google's 48 h auto-expiry.
# ===========================================================================
# Without TTL, a long-lived Cloud Run instance that uploads on hour 0 will
# serve the cached URI on hour 49 — Google has expired the file by then,
# and Gemini's generate_content call would 404 on Part.from_uri. Tests pin
# the eviction behavior so a future revert (removing the TTL check,
# replacing time.monotonic with time.time, leaving stale entries in the
# dict) is caught with a meaningful failure message.


def _seed_simple_active_client(monkeypatch):
    """Install a fake `google.genai.Client` whose upload returns an
    ACTIVE file. Returns the upload_count tracker dict so tests can
    assert how many uploads fired."""
    state = {"upload_count": 0, "n": 0}

    class _FakeFile:
        def __init__(self, name):
            self.name = name
            self.uri = f"https://example/{name}"
            self.state = "ACTIVE"

    class _FakeClient:
        def __init__(self):
            self.files = self

        def upload(self, *, file, config):
            state["upload_count"] += 1
            state["n"] += 1
            return _FakeFile(f"files/v{state['n']}")

        def get(self, *, name):
            return _FakeFile(name)

    sys.modules["google.genai"].Client = lambda **kw: _FakeClient()
    return state


def test_files_api_cache_hit_within_ttl_skips_reupload(monkeypatch):
    """Two consecutive `_build_gemini_part` calls within the TTL window
    must hit the cache and not re-upload."""
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 10_000.0)
    state = _seed_simple_active_client(monkeypatch)

    blob = b"a" * (9 * 1024 * 1024)
    p1 = asyncio.run(srv._build_gemini_part(blob, "text/html"))
    p2 = asyncio.run(srv._build_gemini_part(blob, "text/html"))

    assert p1.file_uri == p2.file_uri
    assert state["upload_count"] == 1, (
        f"within-TTL cache hit should reuse; got {state['upload_count']} uploads"
    )


def test_files_api_cache_past_ttl_is_evicted_and_reuploaded(monkeypatch):
    """When `time.monotonic` advances past TTL, the next call MUST
    treat the entry as expired and re-upload. This is the load-bearing
    recovery for Google's 48 h server-side URI expiry; if reverted
    (eviction `if` deleted from `_cache_get_live`) the second upload
    count stays at 1.
    """
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 1.0)
    state = _seed_simple_active_client(monkeypatch)

    blob = b"b" * (9 * 1024 * 1024)
    fake_now = {"t": 100.0}
    monkeypatch.setattr(srv.time, "monotonic", lambda: fake_now["t"])

    p1 = asyncio.run(srv._build_gemini_part(blob, "text/html"))
    assert state["upload_count"] == 1
    assert p1.file_uri.endswith("/v1")

    # Advance past TTL → next call MUST re-upload.
    fake_now["t"] = 100.0 + 2.0  # 2 s > 1 s TTL
    p2 = asyncio.run(srv._build_gemini_part(blob, "text/html"))
    assert state["upload_count"] == 2, (
        f"expected eviction + re-upload past TTL; got {state['upload_count']}. "
        "Regression: TTL eviction branch in _cache_get_live was removed."
    )
    assert p2.file_uri.endswith("/v2"), (
        f"post-TTL call should return the fresh URI, got {p2.file_uri}"
    )


def test_files_api_cache_entry_is_popped_in_place_on_expiry(monkeypatch):
    """A stale entry MUST be popped during eviction, not just bypassed.
    Otherwise a subsequent caller that doesn't go through `_cache_get_live`
    would still see the dead URI in the dict — a real foot-gun for
    future code changes.
    """
    _ensure_genai_stub(monkeypatch)
    import hashlib

    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 1.0)
    _seed_simple_active_client(monkeypatch)

    blob = b"c" * (9 * 1024 * 1024)
    sha = hashlib.sha256(blob).hexdigest()

    fake_now = {"t": 0.0}
    monkeypatch.setattr(srv.time, "monotonic", lambda: fake_now["t"])

    asyncio.run(srv._build_gemini_part(blob, "text/html"))
    assert sha in srv._files_api_uri_cache

    fake_now["t"] = 5.0  # well past TTL
    assert srv._cache_get_live(sha) is None
    assert sha not in srv._files_api_uri_cache, (
        "stale entry must be popped during eviction (not just bypassed)"
    )


def test_files_api_cache_uses_monotonic_not_wallclock(monkeypatch):
    """Eviction MUST consult `time.monotonic`, not `time.time`. We
    patch only `time.monotonic` and leave `time.time` alone — if the
    implementation regressed to wall-clock, the TTL would never elapse
    and `upload_count` would stay at 1.
    """
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 1.0)
    state = _seed_simple_active_client(monkeypatch)

    fake_mono = {"t": 0.0}
    # Deliberately patch ONLY monotonic. `time.time` continues to
    # report the real wall clock; a regressed implementation that
    # uses `time.time` would not see TTL elapse.
    monkeypatch.setattr(srv.time, "monotonic", lambda: fake_mono["t"])

    blob = b"d" * (9 * 1024 * 1024)
    asyncio.run(srv._build_gemini_part(blob, "text/html"))
    fake_mono["t"] = 999.0
    asyncio.run(srv._build_gemini_part(blob, "text/html"))
    assert state["upload_count"] == 2, (
        f"expected monotonic-based eviction; got {state['upload_count']} "
        f"uploads. Regression: implementation may be using time.time."
    )


def test_files_api_cache_value_carries_inserted_timestamp(monkeypatch):
    """Pins the cache value shape: each entry is a (uri, monotonic_seconds)
    tuple. A regression that drops the timestamp (back to plain str)
    would break the TTL machinery without any other test failing first.
    """
    _ensure_genai_stub(monkeypatch)
    import hashlib

    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 10_000.0)
    _seed_simple_active_client(monkeypatch)

    blob = b"e" * (9 * 1024 * 1024)
    sha = hashlib.sha256(blob).hexdigest()
    asyncio.run(srv._build_gemini_part(blob, "text/html"))
    entry = srv._files_api_uri_cache[sha]
    assert isinstance(entry, tuple)
    assert len(entry) == 2, f"cache value should be 2-tuple, got {entry}"
    uri, inserted_at = entry
    assert isinstance(uri, str) and uri.startswith("https://"), uri
    assert isinstance(inserted_at, float), type(inserted_at)


# ===========================================================================
# R4-1 + R5-2: bounded LRU eviction — the per-sha lock dict and the URI
# cache must stay capped so a long-lived Cloud Run instance doesn't leak
# Lock objects with every distinct upload.
# ===========================================================================


def test_files_api_lock_dict_is_evicted_alongside_uri_on_ttl_expiry(monkeypatch):
    """When a URI is TTL-evicted, the matching Lock entry in
    `_files_api_locks` MUST also be popped — otherwise the lock dict
    leaks one entry per all-time unique upload (R4-1 bug-hunter
    finding). Repro: insert with a 1 s TTL, advance time past TTL,
    call `_cache_get_live`, verify both dicts no longer contain sha.
    """
    _ensure_genai_stub(monkeypatch)
    import hashlib

    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 1.0)
    _seed_simple_active_client(monkeypatch)

    fake_now = {"t": 0.0}
    monkeypatch.setattr(srv.time, "monotonic", lambda: fake_now["t"])

    blob = b"lock-leak" * (9 * 1024 * 1024 // 9 + 1)
    sha = hashlib.sha256(blob).hexdigest()
    asyncio.run(srv._build_gemini_part(blob, "text/html"))

    # After the upload, both dicts have the sha.
    assert sha in srv._files_api_uri_cache
    assert sha in srv._files_api_locks

    # Advance past TTL and trigger eviction.
    fake_now["t"] = 5.0
    assert srv._cache_get_live(sha) is None

    # BOTH dicts must be empty for this sha. A regression that pops the
    # URI without popping the lock would fail the second assertion.
    assert sha not in srv._files_api_uri_cache
    assert sha not in srv._files_api_locks, (
        f"lock dict leaked: sha {sha[:8]}... still has a Lock entry "
        f"after URI TTL eviction"
    )


def test_files_api_cache_enforces_max_entries_lru(monkeypatch):
    """Cap on the URI cache + lock dict — inserting beyond the cap
    evicts the LRU entry from BOTH dicts (R4-1 + R5-2). Repro: cap at
    3, insert 4 unique uploads, verify oldest is evicted from both.

    The defense has two sites that BOTH need cap eviction: `_cache_put`
    (URI side) and `_get_or_create_files_api_lock` (lock side). The
    assertions below pin BOTH dicts at <= cap to catch removal of
    either eviction site.
    """
    _ensure_genai_stub(monkeypatch)
    import hashlib

    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 10_000.0)
    monkeypatch.setattr(srv, "_FILES_API_CACHE_MAX_ENTRIES", 3)
    _seed_simple_active_client(monkeypatch)

    blobs = [bytes([i]) * (9 * 1024 * 1024) for i in range(4)]
    shas = [hashlib.sha256(b).hexdigest() for b in blobs]

    for blob in blobs:
        asyncio.run(srv._build_gemini_part(blob, "text/html"))

    # BOTH dicts must be at cap size. Removing the cap eviction at
    # either site lets one dict grow past the cap.
    assert len(srv._files_api_uri_cache) <= 3, (
        f"URI cache exceeded cap: size={len(srv._files_api_uri_cache)}. "
        f"Cap eviction in `_cache_put` was likely removed."
    )
    assert len(srv._files_api_locks) <= 3, (
        f"Lock dict exceeded cap: size={len(srv._files_api_locks)}. "
        f"Cap eviction in `_get_or_create_files_api_lock` was likely "
        f"removed — `_files_api_locks` would grow unbounded on a "
        f"long-lived Cloud Run instance (R4-1)."
    )

    # First sha (oldest) should be evicted from both dicts.
    assert shas[0] not in srv._files_api_uri_cache, (
        "LRU eviction did not fire; oldest URI entry still present"
    )
    assert shas[0] not in srv._files_api_locks, (
        "LRU eviction left the matching Lock entry behind"
    )
    for sha in shas[1:]:
        assert sha in srv._files_api_uri_cache


def test_files_api_lock_dict_capped_under_upload_failure_path(monkeypatch):
    """The `_get_or_create_files_api_lock` cap-eviction site exists
    specifically for the upload-FAILURE scenario, where `_cache_put`
    is never called. Without this site, the lock dict would grow
    unbounded as failed uploads accumulate. Test pins the cap by
    forcing N+1 uploads to fail (Files API FAILED state) and
    asserting the lock dict stays at cap.
    """
    _ensure_genai_stub(monkeypatch)
    from agent import server as srv
    from fastapi import HTTPException

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 10_000.0)
    monkeypatch.setattr(srv, "_FILES_API_CACHE_MAX_ENTRIES", 3)

    # Every upload returns FAILED state → _cache_put never runs.
    class _AlwaysFailFile:
        def __init__(self, n):
            self.name = f"files/fail-{n}"
            self.uri = f"https://example/{self.name}"
            self.state = "FAILED"

    state = {"n": 0}

    class _FailingClient:
        def __init__(self):
            self.files = self

        def upload(self, *, file, config):
            state["n"] += 1
            return _AlwaysFailFile(state["n"])

        def get(self, *, name):
            return _AlwaysFailFile(0)

    sys.modules["google.genai"].Client = lambda **kw: _FailingClient()

    for i in range(5):
        blob = bytes([i]) * (9 * 1024 * 1024)
        with pytest.raises(HTTPException):
            asyncio.run(srv._build_gemini_part(blob, "text/html"))

    # Even though every upload raised before `_cache_put`, the lock
    # dict must stay at cap thanks to `_get_or_create_files_api_lock`'s
    # cap-eviction. If that site is removed (mutation), the lock dict
    # grows past cap here.
    assert len(srv._files_api_locks) <= 3, (
        f"Lock dict exceeded cap on upload-failure path: "
        f"size={len(srv._files_api_locks)}. Regression: "
        f"`_get_or_create_files_api_lock` cap-eviction was removed."
    )


def test_files_api_cache_lru_touch_on_read_keeps_hot_entries(monkeypatch):
    """Reading a cache entry should `move_to_end` it so under LRU
    cap pressure, hot entries survive eviction. Construction:
    cap=3, insert A, B, C. Read A (touch). Insert D. Expected: B
    is the LRU and gets evicted; A is hot and stays.
    """
    _ensure_genai_stub(monkeypatch)
    import hashlib

    from agent import server as srv

    _clear_caches(srv)
    monkeypatch.setattr(srv, "_FILES_API_URI_TTL_SECONDS", 10_000.0)
    monkeypatch.setattr(srv, "_FILES_API_CACHE_MAX_ENTRIES", 3)
    _seed_simple_active_client(monkeypatch)

    blobs = [b"A" * (9 * 1024 * 1024), b"B" * (9 * 1024 * 1024),
             b"C" * (9 * 1024 * 1024), b"D" * (9 * 1024 * 1024)]
    shas = [hashlib.sha256(b).hexdigest() for b in blobs]

    for blob in blobs[:3]:
        asyncio.run(srv._build_gemini_part(blob, "text/html"))

    # Touch A. After this, A should be the most recently used.
    asyncio.run(srv._build_gemini_part(blobs[0], "text/html"))

    # Insert D. B should be evicted, A should remain.
    asyncio.run(srv._build_gemini_part(blobs[3], "text/html"))
    assert shas[0] in srv._files_api_uri_cache, "hot entry A was evicted"
    assert shas[1] not in srv._files_api_uri_cache, "LRU entry B was retained"
