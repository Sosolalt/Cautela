"""Shared ADK Runner wrapper for the eval scripts' `--live` paths.

Mirrors the *verified* invocation pattern in
`agent/server.py:_stream_findings` (InMemoryRunner + session-create
sync/async guard + Content/Part + async event drain). Kept in its own
module — and with every google-adk / google-genai import deferred inside
a function — so that importing `eval_maud_mcq` / `eval_cuad_spans` for
unit tests never requires google-adk to be installed. Only an actual
`--live` invocation touches the ADK SDK.

The eval-agent callables (`_AgentFn` in each eval module) are synchronous
by contract, and a CLI batch eval runs them sequentially, so each call
spins a fresh event loop via `asyncio.run`. That is intentionally simple:
correctness over throughput for an offline scoring pass.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import os
import random
import time
import uuid
from typing import Any

_LOG = logging.getLogger(__name__)

_APP_NAME = "ma-gatekeeper-eval"
_USER_ID = "eval-user"

# Resilience knobs for live eval runs against Vertex's (preview-model) quota.
# A batch eval — chunked extraction most of all — easily exceeds the
# tokens/requests-per-minute limit; one transient 429 should not kill the run.
# All env-overridable so the operator can tune without code changes.
_MAX_RETRIES = int(os.environ.get("EVAL_MAX_RETRIES", "6"))
_RETRY_BASE_SEC = float(os.environ.get("EVAL_RETRY_BASE_SEC", "10"))
_RETRY_CAP_SEC = float(os.environ.get("EVAL_RETRY_CAP_SEC", "120"))
# Fixed delay AFTER each successful call, to pace under a tokens/min quota.
_REQUEST_DELAY_SEC = float(os.environ.get("EVAL_REQUEST_DELAY_SEC", "0"))


def _is_rate_limited(exc: BaseException) -> bool:
    """True if the exception looks like a Vertex 429 / resource-exhausted error.

    Matches both the status token `RESOURCE_EXHAUSTED` and the human message
    `Resource exhausted` (space vs underscore), plus the bare `429` code.
    """
    s = str(exc).upper()
    return "429" in s or "EXHAUSTED" in s


async def _run_agent_async(agent: Any, user_text: str, *, app_name: str) -> str:
    """Drive one ADK agent over a single user message; return joined text.

    Import paths are the ones pinned as non-fabricated in
    `agent/server.py` / `agent/agents.py`:
      - `from google.adk.runners import InMemoryRunner`
      - `from google.genai import types as gtypes`
    """
    from google.adk.runners import InMemoryRunner
    from google.genai import types as gtypes

    runner = InMemoryRunner(agent=agent, app_name=app_name)

    session_id = uuid.uuid4().hex
    # ADK SDK drift guard (same as server.py:_stream_findings): some 1.x
    # releases expose a sync create_session, others async. Try sync, await
    # if the return is awaitable.
    create_session = runner.session_service.create_session
    result = create_session(
        app_name=app_name, user_id=_USER_ID, session_id=session_id
    )
    if inspect.isawaitable(result):
        await result

    new_message = gtypes.Content(
        role="user", parts=[gtypes.Part.from_text(text=user_text)]
    )

    chunks: list[str] = []
    async for event in runner.run_async(
        user_id=_USER_ID, session_id=session_id, new_message=new_message
    ):
        content = getattr(event, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def run_agent(agent: Any, user_text: str, *, app_name: str = _APP_NAME) -> str:
    """Synchronous wrapper around `_run_agent_async`, with 429 backoff.

    On a Vertex 429 / RESOURCE_EXHAUSTED we retry with exponential backoff +
    jitter (capped at `_RETRY_CAP_SEC`) so one transient quota hit does not
    abort the whole batch eval. Non-rate-limit errors propagate immediately.
    `EVAL_REQUEST_DELAY_SEC` paces successful calls to stay under a tokens/min
    quota. Tune via EVAL_MAX_RETRIES / EVAL_RETRY_BASE_SEC / EVAL_RETRY_CAP_SEC.
    """
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = asyncio.run(
                _run_agent_async(agent, user_text, app_name=app_name)
            )
            if _REQUEST_DELAY_SEC > 0:
                time.sleep(_REQUEST_DELAY_SEC)
            return result
        except Exception as exc:  # noqa: BLE001 — re-raised unless rate-limited
            if not _is_rate_limited(exc) or attempt >= _MAX_RETRIES:
                raise
            delay = min(_RETRY_CAP_SEC, _RETRY_BASE_SEC * (2**attempt))
            delay += random.uniform(0, min(3.0, delay * 0.25))
            _LOG.warning(
                "Vertex rate-limited (attempt %d/%d) — backing off %.1fs",
                attempt + 1,
                _MAX_RETRIES,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError("unreachable: retry loop exhausted")  # pragma: no cover


def run_single_agent(
    instruction: str,
    user_text: str,
    *,
    model: str | None = None,
    agent_name: str = "eval_agent",
    app_name: str = _APP_NAME,
    max_output_tokens: int | None = None,
) -> str:
    """Build a single-purpose `LlmAgent` from `instruction` and run it once.

    `model` defaults to $GEMINI_MODEL (falling back to gemini-3.1-pro-preview),
    matching the rest of the agent code's model-resolution convention.

    `max_output_tokens`, when set, raises the generation output cap so a long
    structured response (e.g. a big span list) is not silently truncated — a
    cheap recall lever for the CUAD span eval. Default None preserves the SDK
    default for callers (e.g. the MAUD MCQ path) that emit short answers.
    """
    from google.adk.agents import LlmAgent

    model = model or os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
    kwargs: dict[str, Any] = {}
    if max_output_tokens is not None:
        from google.genai import types as gtypes

        kwargs["generate_content_config"] = gtypes.GenerateContentConfig(
            max_output_tokens=max_output_tokens
        )
    agent = LlmAgent(
        name=agent_name, model=model, instruction=instruction, **kwargs
    )
    return run_agent(agent, user_text, app_name=app_name)
