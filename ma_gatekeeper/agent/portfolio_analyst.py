"""Fix 7 — Portfolio Analyst agent (1M-context cross-deal cluster detection).

The PM-critic-flagged "one change that wins the Google Cloud bucket"
(POST_HACKATHON_BACKLOG.md #2): one Gemini 3 Pro call against all 30
Internal-30 EX-2.1 contracts concatenated, exposed as a fifth agent
(`/portfolio` endpoint, not in the per-contract SequentialAgent root).

Pattern parity (mirrors `scripts/eval_maud_mcq.py:make_live_agent` and
`scripts/verify_structural_reasoning.py:make_live_cross_reference`):

  - `make_mock_portfolio()` returns the canonical
    `tests/fixtures/portfolio_expected_output.json` deterministically —
    CI-safe, no LLM call, no Vertex quota burn.
  - `make_live_portfolio(contracts)` raises `NotImplementedError` until
    the operator wires the ADK Runner against the Files-API path. The
    docstring on the raise names the exact wiring steps.

Why NOT in the SequentialAgent at agents.py:114-117:
  - The Portfolio Analyst is a SEPARATE capability, run on demand from
    the `/portfolio` endpoint. Folding it into the per-contract
    SequentialAgent would burn one 1M-context call on every single
    /review-by-deal call (and would also break the per-contract
    review's sub-200-token-window streaming UX).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .prompts import PORTFOLIO_ANALYST_PROMPT
from .schemas import PortfolioCluster, PortfolioOutlier, PortfolioReport


_DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "portfolio_expected_output.json"
)
_DEFAULT_SAMPLE_PATH = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "portfolio_sample.json"
)


class ContractInput(Protocol):
    """One contract row sent to the Portfolio Analyst.

    Live path: the EdgarTools-fetched EX-2.1 bytes are uploaded to
    Gemini Files API via `agent.server._cache_get_live` / `_ensure_files_
    api_upload` (server.py:180-313) and a `Part.from_uri` is appended per
    contract; the deal_id is stitched into the per-part header so the
    LLM can name members by id.
    """

    deal_id: str
    source: str
    ex21_excerpt: str  # mock path; live path passes a Files-API URI


def build_portfolio_analyst():
    """Build the standalone Portfolio Analyst LlmAgent.

    Single LlmAgent on `gemini-3-pro-preview` with
    `PORTFOLIO_ANALYST_PROMPT`. NOT registered in the SequentialAgent
    root (see module docstring) — this factory is consumed only by the
    `/portfolio` endpoint live path.
    """
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="portfolio_analyst",
        model="gemini-3-pro-preview",
        instruction=PORTFOLIO_ANALYST_PROMPT,
        output_key="portfolio_report",
    )


class _PortfolioFn(Protocol):
    """Callable contract: (list[ContractInput]) -> PortfolioReport."""

    def __call__(self, contracts: list[ContractInput]) -> PortfolioReport: ...


def make_mock_portfolio(
    fixture_path: Path | str = _DEFAULT_FIXTURE_PATH,
) -> _PortfolioFn:
    """Deterministic mock: returns the canonical expected output.

    The fixture at `tests/fixtures/portfolio_expected_output.json` IS
    the contract: tests pin the cluster count, mutual-exclusion
    invariant, and the named outlier (akorn-fresenius) against it.
    Re-generating the fixture is a deliberate test-suite-level decision,
    not a runtime concern.

    The mock IGNORES its `contracts` argument (the canonical fixture is
    already keyed against the canonical contract set at
    `tests/fixtures/portfolio_sample.json`). The argument is accepted
    so call-sites are signature-compatible with `make_live_portfolio`.
    """
    path = Path(fixture_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = PortfolioReport(
        clusters=[PortfolioCluster(**c) for c in payload["clusters"]],
        outliers=[PortfolioOutlier(**o) for o in payload["outliers"]],
    )

    def _agent(contracts: list[ContractInput]) -> PortfolioReport:
        # Return a fresh model_copy so the caller can't mutate the
        # cached canonical object across calls. (Same pattern as the
        # ADK Event-stream deep-copy on the per-review path.)
        return report.model_copy(deep=True)

    return _agent


def make_live_portfolio() -> _PortfolioFn:
    """Live ADK Runner against Vertex — the actual 1M-context call.

    Wiring steps (operator, D9 dry-run):

      1. Set VERTEX_AI_PROJECT, VERTEX_AI_LOCATION envs and confirm
         Gemini 3 Pro quota bump approved for ~1M input tokens / call.
      2. Upload all 30 EX-2.1 contracts to Files API via the existing
         `agent.server._ensure_files_api_upload` (`server.py:257-311`),
         keyed by content-sha256 so re-runs hit the cache. The Files
         API path is already trust-reviewed for the /review pipeline;
         re-use the same code path.
      3. Build a single `Content(parts=[...])` with one `Part.from_uri`
         per contract (mime_type `application/pdf` for PDF EX-2.1s,
         `text/html` for HTML EX-2.1s). Prefix each part with a short
         `## DEAL: {deal_id}` header so the model can name members by id.
      4. Wrap `build_portfolio_analyst()` in an `InMemoryRunner` and
         call `run_async(user_id, session_id, new_message=Content(...))`.
         Capture the `portfolio_report` output_key from session state.
      5. `json.loads(...)` the captured text and `PortfolioReport(**...)`
         it; the schema validation will surface any drift between the
         prompt's declared shape and the model's actual output.
      6. Replace the raise below with the above sequence.

    Implementation note — inline-excerpt path:
      This wrapper sends each contract's `ex21_excerpt` inline (one
      `## DEAL: {deal_id}` header + excerpt per contract, concatenated
      into a single user message), which is sufficient for the demo's
      excerpt-sized Internal-30 sample. The Files-API URI path described
      in steps 1-5 above is the SCALING variant for full-length EX-2.1
      bytes; it re-uses `server.py`'s upload cache and is wired by the
      operator when full contracts (not excerpts) are fed in.

    Construction is cheap and ADK-free: the google-adk / google-genai
    imports live inside the returned closure, so importing this module
    (and constructing the live agent in tests) does not require google-adk
    or Vertex credentials. `PORTFOLIO_LIVE=0` remains the default in
    `server.py`, so CI never reaches this path.
    """

    def _agent(contracts: list[ContractInput]) -> PortfolioReport:
        import asyncio
        import inspect
        import uuid

        from google.adk.runners import InMemoryRunner
        from google.genai import types as gtypes

        def _excerpt(c: object) -> tuple[str, str]:
            # Accept both dict rows (load_sample_contracts) and objects.
            if isinstance(c, dict):
                return str(c.get("deal_id", "")), str(c.get("ex21_excerpt", ""))
            return str(getattr(c, "deal_id", "")), str(
                getattr(c, "ex21_excerpt", "")
            )

        blocks = []
        for c in contracts:
            deal_id, excerpt = _excerpt(c)
            blocks.append(f"## DEAL: {deal_id}\n{excerpt}")
        user_text = "\n\n".join(blocks)

        async def _run() -> str:
            agent = build_portfolio_analyst()
            runner = InMemoryRunner(agent=agent, app_name="ma-gatekeeper-portfolio")
            session_id = uuid.uuid4().hex
            user_id = "portfolio-user"
            create_session = runner.session_service.create_session
            result = create_session(
                app_name="ma-gatekeeper-portfolio",
                user_id=user_id,
                session_id=session_id,
            )
            if inspect.isawaitable(result):
                await result
            new_message = gtypes.Content(
                role="user", parts=[gtypes.Part.from_text(text=user_text)]
            )
            chunks: list[str] = []
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=new_message
            ):
                content = getattr(event, "content", None)
                parts = getattr(content, "parts", None) or []
                for part in parts:
                    text = getattr(part, "text", None)
                    if text:
                        chunks.append(text)
            return "\n".join(chunks).strip()

        raw = asyncio.run(_run())

        # Strip markdown fences and validate against the schema. A parse
        # failure FAILS LOUD (the /portfolio endpoint should 500, not
        # return a hollow report) — consistent with the legal-reviewer
        # "never look clean when broken" rule on the per-review path.
        text = raw.strip()
        if text.startswith("```"):
            import re

            text = re.sub(r"^```[a-zA-Z0-9]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text).strip()
        payload = json.loads(text)
        return PortfolioReport(
            clusters=[PortfolioCluster(**c) for c in payload["clusters"]],
            outliers=[PortfolioOutlier(**o) for o in payload["outliers"]],
        )

    return _agent


def load_sample_contracts(
    path: Path | str = _DEFAULT_SAMPLE_PATH,
) -> list[dict]:
    """Load the 30-row sample fixture as plain dicts.

    Returned shape matches ContractInput at runtime (TypedDict-like).
    The live path uploads bytes; this helper is for the mock/dev path
    and for the `/portfolio` endpoint when `PORTFOLIO_LIVE=0` (default).
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(payload["contracts"])
