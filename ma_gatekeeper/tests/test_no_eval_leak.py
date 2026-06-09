"""Load-bearing structural guard: eval-only fields NEVER leave the server.

`linker_proposal`, `linker_agreement`, and `linker_confidence` carry INTERNAL
eval data (design/STATUTE_LAYER.md §2.3). They must never appear in any byte
stream the server emits. This is defended by:

  Guard #2 — RiskFinding.model_dump / model_dump_json default-exclude
             `_EVAL_ONLY_FIELDS`. The model enforces it, not the call site.
  Guard #3 — the SSE wire-output regression test below: exercise the real
             `_stream_findings` SSE generator with a finding whose eval-only
             fields are deliberately populated, capture the raw bytes, and
             assert none of the eval-only names appear on the wire.

If a future refactor removes the override, the model-level tests flip red; if
it removes the `exclude=` at the emit site, the wire test still passes (the
override is the structural guarantee) — but if BOTH regress, Guard #3 catches it.
"""
from __future__ import annotations

import asyncio
import json
import sys
import types

from agent.schemas import _EVAL_ONLY_FIELDS, LinkerProposal, RiskFinding


def _finding_with_eval_fields() -> RiskFinding:
    """A finding whose eval-only fields are deliberately populated."""
    return RiskFinding(
        clause_id="sec_4.2_para_b",
        clause_text="Upon a Change of Control...",
        tag="change_of_control",
        severity="block",
        judge_score=0.92,
        cited_spans=["sec_4.2_para_b"],
        cited_spans_text="Upon a Change of Control...",
        explanation="Consent requirement triggers on direct equity transfer.",
        linker_proposal=LinkerProposal(
            citation="8 Del. C. § 999",
            citation_kind="statute",
            jurisdiction="Delaware",
            rationale="model-proposed — must never render",
            model_confidence=0.81,
        ),
        linker_agreement=False,
        linker_confidence=0.81,
    )


# ---------------------------------------------------------------------------
# Guard #2 — model-level default exclusion.
# ---------------------------------------------------------------------------

def test_model_dump_default_excludes_eval_only_fields():
    dumped = _finding_with_eval_fields().model_dump(mode="json")
    for name in _EVAL_ONLY_FIELDS:
        assert name not in dumped, f"{name} leaked through model_dump()"
    # The user-facing citation field is NOT eval-only — it must survive.
    assert "citation_ref" in dumped


def test_model_dump_json_default_excludes_eval_only_fields():
    blob = _finding_with_eval_fields().model_dump_json()
    for name in _EVAL_ONLY_FIELDS:
        assert name not in blob, f"{name} leaked through model_dump_json()"


def test_explicit_exclude_is_unioned_not_overwritten():
    """A caller passing its own exclude= must NOT lose the eval-only defense."""
    dumped = _finding_with_eval_fields().model_dump(
        mode="json", exclude={"explanation"}
    )
    assert "explanation" not in dumped  # caller's exclude honored
    for name in _EVAL_ONLY_FIELDS:
        assert name not in dumped, f"{name} leaked when caller passed own exclude"


def test_model_dump_internal_DOES_include_eval_only_fields():
    """The eval/diagnostic path must still see the fields (proves they were set
    and that the bypass works)."""
    internal = _finding_with_eval_fields().model_dump_internal(mode="json")
    assert internal["linker_agreement"] is False
    assert internal["linker_confidence"] == 0.81
    assert internal["linker_proposal"]["citation"] == "8 Del. C. § 999"


def test_eval_only_constant_names_are_real_fields():
    """Symbol-parity: every name in the constant is an actual RiskFinding field,
    so a rename can't silently turn the exclusion into a no-op."""
    for name in _EVAL_ONLY_FIELDS:
        assert name in RiskFinding.model_fields, f"{name} not a RiskFinding field"


# ---------------------------------------------------------------------------
# Guard #3 — SSE wire-output regression test (full `_stream_findings`).
# ---------------------------------------------------------------------------
# Minimal fake ADK so `_stream_findings` runs without the real google.adk /
# Vertex / Phoenix surface. Mirrors tests/test_server_stream.py.

def _ev(author: str, text: str):
    return types.SimpleNamespace(
        author=author,
        content=types.SimpleNamespace(parts=[types.SimpleNamespace(text=text)]),
        actions=None,
    )


def _install_fake_adk(monkeypatch, events: list):
    class _FakeSessionService:
        def create_session(self, **kw):
            return None

    class _InMemoryRunner:
        def __init__(self, *, agent, app_name):
            self.session_service = _FakeSessionService()

        async def run_async(self, *, user_id, session_id, new_message):
            for e in events:
                yield e

    class _Part:
        def __init__(self, **kw):
            self.__dict__.update(kw)

        @classmethod
        def from_bytes(cls, *, data, mime_type):
            return cls(kind="bytes", data=data, mime_type=mime_type)

        @classmethod
        def from_uri(cls, *, file_uri, mime_type):
            return cls(kind="uri", file_uri=file_uri, mime_type=mime_type)

    class _Content:
        def __init__(self, *, role, parts):
            self.role = role
            self.parts = parts

    runners_mod = types.ModuleType("google.adk.runners")
    runners_mod.InMemoryRunner = _InMemoryRunner
    adk_pkg = types.ModuleType("google.adk")
    adk_pkg.runners = runners_mod
    gtypes_mod = types.ModuleType("google.genai.types")
    gtypes_mod.Part = _Part
    gtypes_mod.Content = _Content
    gtypes_mod.UploadFileConfig = lambda **kw: kw
    genai_pkg = types.ModuleType("google.genai")
    genai_pkg.types = gtypes_mod
    google_pkg = types.ModuleType("google")
    google_pkg.adk = adk_pkg
    google_pkg.genai = genai_pkg

    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.adk", adk_pkg)
    monkeypatch.setitem(sys.modules, "google.adk.runners", runners_mod)
    monkeypatch.setitem(sys.modules, "google.genai", genai_pkg)
    monkeypatch.setitem(sys.modules, "google.genai.types", gtypes_mod)


def _stub_server_deps(monkeypatch):
    from agent import server as srv
    from agent.router import Thresholds

    monkeypatch.setattr(
        "agent.agents.build_root_agent", lambda: types.SimpleNamespace()
    )
    monkeypatch.setattr(
        "agent.evaluators.run_inline_judges",
        lambda **kw: (0.05, "hallucinated", 0.9, "faithful"),
    )
    monkeypatch.setattr(
        Thresholds, "from_json",
        classmethod(lambda cls, path: cls(tau_h=0.5, tau_f=0.5)),
    )
    return srv


async def _collect(stream) -> list[bytes]:
    return [chunk async for chunk in stream]


_PARSER_CLAUSE_JSON = json.dumps([
    {
        "id": "sec_4.2_para_b",
        "section_path": ["Article IV", "Section 4.2", "(b)"],
        "text": "Upon a Change of Control...",
        "page": 17,
        "char_start": 100,
        "char_end": 250,
        "pdf_bbox": [72.0, 144.0, 540.0, 180.0],
    },
])

# The raw risk_judge text is CLEAN — the LLM never emits eval-only fields (it
# doesn't know they exist). We populate them on the finding OBJECT after
# validation (see the taint below), so any eval-only name appearing on the wire
# could only come from serializing the finding — which is what the guard prevents.
_RISK_JUDGE_JSON = json.dumps([
    {
        "clause_id": "sec_4.2_para_b",
        "clause_text": "Upon a Change of Control...",
        "tag": "change_of_control",
        "severity": "block",
        "judge_score": 0.92,
        "cited_spans": ["sec_4.2_para_b"],
        "cited_spans_text": "Upon a Change of Control...",
        "explanation": "Consent requirement triggers on direct equity transfer.",
    },
])


def test_sse_bytes_contain_no_eval_field_names(monkeypatch):
    """The load-bearing wire-level safety net: run the real SSE generator with a
    finding whose eval-only fields are populated; assert NONE of the eval-only
    names appear anywhere in the bytes the server emits."""
    events = [_ev("parser", _PARSER_CLAUSE_JSON), _ev("risk_judge", _RISK_JUDGE_JSON)]
    _install_fake_adk(monkeypatch, events)
    srv = _stub_server_deps(monkeypatch)

    # Taint every finding post-validation, simulating a world where the
    # background proposer (or a future bug) stamped eval-only data onto the
    # object. The raw LLM text stays clean — so a leak can only be a
    # serialization leak, which is exactly what Guard #2 must stop.
    import agent.schemas as schemas
    _orig_validate = schemas.RiskFinding.model_validate

    def _validate_and_taint(cls, raw, *a, **k):
        finding = _orig_validate(raw, *a, **k)
        return finding.model_copy(update={
            "linker_proposal": LinkerProposal(
                citation="8 Del. C. § 999",
                citation_kind="statute",
                jurisdiction="Delaware",
                rationale="model-proposed — must never render",
                model_confidence=0.81,
            ),
            "linker_agreement": False,
            "linker_confidence": 0.81,
        })

    monkeypatch.setattr(
        schemas.RiskFinding, "model_validate", classmethod(_validate_and_taint)
    )

    chunks = asyncio.run(_collect(
        srv._stream_findings(b"%PDF-fake", mime_type="application/pdf")
    ))
    wire = b"".join(chunks)

    for name in _EVAL_ONLY_FIELDS:
        assert name.encode() not in wire, (
            f"{name} appeared in SSE wire bytes — eval-only leak!"
        )

    # Sanity: a finding frame really was emitted (so we didn't pass vacuously).
    frames = [
        json.loads(line[len("data: "):])
        for c in chunks
        for line in c.decode().split("\n")
        if line.startswith("data: ")
    ]
    assert any(f.get("event") == "finding" for f in frames), frames
