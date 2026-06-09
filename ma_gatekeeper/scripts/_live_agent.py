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
import os
import uuid
from typing import Any

_APP_NAME = "ma-gatekeeper-eval"
_USER_ID = "eval-user"


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
    """Synchronous wrapper around `_run_agent_async` for an already-built agent."""
    return asyncio.run(_run_agent_async(agent, user_text, app_name=app_name))


def run_single_agent(
    instruction: str,
    user_text: str,
    *,
    model: str | None = None,
    agent_name: str = "eval_agent",
    app_name: str = _APP_NAME,
) -> str:
    """Build a single-purpose `LlmAgent` from `instruction` and run it once.

    `model` defaults to $GEMINI_MODEL (falling back to gemini-3-pro-preview),
    matching the rest of the agent code's model-resolution convention.
    """
    from google.adk.agents import LlmAgent

    model = model or os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview")
    agent = LlmAgent(name=agent_name, model=model, instruction=instruction)
    return run_agent(agent, user_text, app_name=app_name)
