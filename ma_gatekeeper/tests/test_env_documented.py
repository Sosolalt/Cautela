"""Sync-guard for env-var documentation.

Walks `agent/` and `scripts/` looking for `os.environ.get("KEY", ...)`
or `os.environ["KEY"]` literals, then asserts every key appears in
`.env.example`. Catches the recurring "added an env read, forgot to
document it" failure mode the Distinguished Engineer reviewer flagged
in Issue 10 (5 undocumented vars at the time, including security-
critical REFLECT_OIDC_AUDIENCE).

Also pins the security invariants from the Issue 10 fix:
  - OIDC dep raises 503 on Cloud Run (K_SERVICE set) with empty audience
  - OIDC dep skips on localhost (K_SERVICE unset) with empty audience
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# Repo-relative paths. Run with `pytest` from `ma_gatekeeper/`.
ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"

# Vars used internally that don't need to live in .env.example because
# they're not user-configurable: K_SERVICE is set by the Cloud Run
# runtime; PORT by Cloud Run's containerd; PYTHONPATH by pytest itself.
ENV_VARS_NOT_IN_DOTENV = {"K_SERVICE", "PORT", "PYTHONPATH"}


def _read_env_example_keys() -> set[str]:
    keys: set[str] = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def _collect_env_reads(py_path: Path) -> set[str]:
    """Parse `py_path` and return every literal env-var name it reads
    via `os.environ.get(NAME, ...)` or `os.environ[NAME]`."""
    keys: set[str] = set()
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return keys
    for node in ast.walk(tree):
        # os.environ.get("KEY", ...)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "environ"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
        # os.environ["KEY"]
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.add(node.slice.value)
    return keys


def test_every_env_var_in_agent_is_documented():
    """Every literal `os.environ.get("X", ...)` in `agent/` must have a
    corresponding key in `.env.example`. Catches the bug-pattern where
    a developer adds a config knob in code but forgets to surface it
    for the operator."""
    used: set[str] = set()
    for py in (ROOT / "agent").rglob("*.py"):
        used |= _collect_env_reads(py)
    documented = _read_env_example_keys()
    missing = (used - documented) - ENV_VARS_NOT_IN_DOTENV
    assert not missing, (
        f"env vars read by agent/ but not documented in .env.example: "
        f"{sorted(missing)}"
    )


def test_every_env_var_in_scripts_is_documented():
    """Same guard for `scripts/`. Operator runs these manually, so they
    need to know what to set."""
    used: set[str] = set()
    for py in (ROOT / "scripts").rglob("*.py"):
        used |= _collect_env_reads(py)
    documented = _read_env_example_keys()
    missing = (used - documented) - ENV_VARS_NOT_IN_DOTENV
    assert not missing, (
        f"env vars read by scripts/ but not documented in .env.example: "
        f"{sorted(missing)}"
    )


def test_security_critical_vars_in_required_section():
    """REFLECT_OIDC_AUDIENCE and DEMO_PASSCODE MUST live in the REQUIRED
    block, not the OPTIONAL one, so the operator can't overlook them."""
    body = ENV_EXAMPLE.read_text(encoding="utf-8")
    # Find the REQUIRED block (between "REQUIRED" header and the
    # "OPTIONAL" header).
    required_match = re.search(
        r"REQUIRED[^\n]*\n(.*?)(?=#\s*=+\s*\n#\s*OPTIONAL)",
        body,
        re.DOTALL,
    )
    assert required_match is not None, (
        "could not locate REQUIRED section in .env.example; "
        "this test is the contract that fences the section structure"
    )
    required_body = required_match.group(1)
    for var in ("DEMO_PASSCODE", "REFLECT_OIDC_AUDIENCE"):
        assert var in required_body, (
            f"{var} must be in the REQUIRED block (it currently isn't); "
            "security-critical vars belong above the OPTIONAL header"
        )


# ---------------------------------------------------------------------------
# Security invariants: OIDC fail-loud + fail-closed on Cloud Run
# ---------------------------------------------------------------------------


def test_oidc_dep_skips_on_localhost_with_empty_audience(monkeypatch):
    """Empty audience + no K_SERVICE → returns None (skip). Keeps the
    `pytest` + `uvicorn` development flow working."""
    import asyncio

    monkeypatch.delenv("K_SERVICE", raising=False)
    from agent import server as srv

    monkeypatch.setattr(srv, "EXPECTED_OIDC_AUDIENCE", "")
    # Should NOT raise; returning None is the correct skip behavior.
    asyncio.run(srv.oidc_dep(authorization=None))


def test_oidc_dep_fails_closed_on_cloud_run_with_empty_audience(monkeypatch):
    """Empty audience + K_SERVICE set → 503. The DEMO_PASSCODE-symmetric
    fail-closed path that turns the original silent-skip vulnerability
    into a loud configuration error."""
    import asyncio

    from fastapi import HTTPException

    monkeypatch.setenv("K_SERVICE", "ma-gatekeeper-prod")
    from agent import server as srv

    monkeypatch.setattr(srv, "EXPECTED_OIDC_AUDIENCE", "")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(srv.oidc_dep(authorization=None))
    assert exc_info.value.status_code == 503
    assert "oidc audience" in str(exc_info.value.detail).lower()


def test_oidc_dep_missing_bearer_when_audience_set(monkeypatch):
    """Audience set + no Authorization header → 401 missing bearer.
    Confirms the audience-set path still demands a token."""
    import asyncio

    from fastapi import HTTPException

    monkeypatch.delenv("K_SERVICE", raising=False)
    from agent import server as srv

    monkeypatch.setattr(srv, "EXPECTED_OIDC_AUDIENCE", "https://example/svc")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(srv.oidc_dep(authorization=None))
    assert exc_info.value.status_code == 401
