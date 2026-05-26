"""Reflector self-improvement loop (plan §6.3, statistically-honest).

Single ADK agent process that holds:
  - Phoenix MCP tools via google.adk.tools.mcp_tool.MCPToolset (for the
    "agent inspects its own traces" beat in the demo). The MCPToolset is
    built by `make_phoenix_mcp_toolset()` and mounted on the introspection
    sub-agent at construction time.
  - phoenix.client.Client() for deterministic SDK steps (datasets,
    experiments, prompts).

Verified Phoenix client API (Arize-reviewer + live docs):
  - client.datasets.get_dataset(name=...) returns a Dataset object.
  - client.datasets.append_examples(dataset=Dataset, examples=...)
  - client.prompts.get(prompt_identifier=, tag=)
  - client.prompts.create(name=, version=...)  (NOT upsert)
  - client.prompts.tags.create(prompt_version_id=, name=, description=)
                                                    (NOT add_version_tag)
  - client.experiments.run_experiment(dataset, task, evaluators=None, ...)
    where `dataset` is a Dataset object.

Promotion rule:
  1. paired_bootstrap_ci_lower_bound(regression_deltas, 1000) > 0
     ONE-SIDED at 95% (alpha not alpha/2).
  AND
  2. cand_score_on_fold5 >= prod_score_on_fold5 - eps_fold5,
     where eps_fold5 = max(paired_bootstrap_se(fold5_deltas), 0.03)

The frozen `internal-30-holdout-fold-5` dataset is enforced via a
code-level WRITABLE allowlist — the Reflector can ONLY append to
datasets in `_WRITABLE_DATASETS`. PermissionError otherwise.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import os
from typing import Sequence

import numpy as np

_LOG = logging.getLogger(__name__)

# Code-enforced allowlist. The Reflector is FORBIDDEN from writing to
# any dataset not in this set. The frozen held-out fold-5 is absent.
_WRITABLE_DATASETS: frozenset[str] = frozenset({"regressions-v1"})
_FROZEN_HELD_OUT: str = "internal-30-holdout-fold-5"


def make_phoenix_mcp_toolset():
    """Hook 4 — real MCPToolset wiring around the @arizeai/phoenix-mcp server.

    Mounted on the Reflector's introspection sub-agent so the LLM can call
    `list-traces`, `get-trace`, `get-span-annotations`, etc. directly. The
    deterministic SDK calls (datasets/experiments/prompts) continue to use
    phoenix.client; MCP is for the agent-driven introspection beat in the
    demo.

    Returns an MCPToolset, or None if the MCP integration packages are
    not installed in this environment.
    """
    try:
        from google.adk.tools.mcp_tool import MCPToolset, StdioServerParameters
    except Exception as exc:
        _LOG.warning("MCPToolset unavailable: %s", exc)
        return None
    base_url = os.environ.get("PHOENIX_MCP_BASE_URL", "")
    api_key = os.environ.get("PHOENIX_MCP_API_KEY", "")
    if not base_url or not api_key:
        _LOG.info(
            "Phoenix MCP base URL or API key unset; Hook 4 will run in "
            "no-op mode until env is configured."
        )
        return None
    params = StdioServerParameters(
        command="npx",
        args=[
            "-y", "@arizeai/phoenix-mcp@latest",
            "--baseUrl", base_url,
            "--apiKey", api_key,
        ],
    )
    return MCPToolset(connection_params=params)


def build_introspection_agent():
    """LlmAgent that calls Phoenix MCP tools to inspect its own traces.

    Invoked at the START of run_reflection_cycle so the chosen failing
    traces include the agent's own recent reasoning. This is the
    "meta-agentic observability" beat the Arize-track judges look for.
    """
    toolset = make_phoenix_mcp_toolset()
    if toolset is None:
        return None
    try:
        from google.adk.agents import LlmAgent
    except Exception:
        return None
    return LlmAgent(
        name="reflector_introspector",
        model=os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview"),
        instruction=(
            "You are inspecting the M&A Gatekeeper's own traces. "
            "Use the phoenix-mcp tools to: (1) list_traces from project "
            "'ma-gatekeeper' in the last 24 hours, (2) for each trace, "
            "fetch its risk_judge_gate annotation, (3) return a compact "
            "list of escalation-tagged spans worth promoting into the "
            "regression dataset."
        ),
        tools=[toolset],
    )


async def _run_introspection_agent_async() -> str:
    """Async body of Hook 4 — invoke the MCP-mounted introspection agent.

    Lives as an `async def` so we can `await` ADK's sync-or-async
    create_session shim cleanly and drive `runner.run_async`'s async
    generator with `async for`. The sync wrapper below calls this via
    `asyncio.run` from inside a worker thread.

    Cleans up the MCP `Toolset` subprocess(es) on every exit path —
    `npx -y @arizeai/phoenix-mcp@latest` is a child process spawned
    per toolset construction; if we don't close it, the nightly
    Reflector cron leaks one `node` process per cycle and Cloud Run
    eventually exhausts file descriptors. Found by Designer B in
    Issue-5 review — silent failure mode that the bare `except` in
    the old sync code masked completely.
    """
    agent = build_introspection_agent()
    if agent is None:
        _LOG.info("Hook 4: introspection agent unavailable (MCP env unset?).")
        return ""

    import inspect as _inspect
    from google.adk.runners import InMemoryRunner
    from google.genai import types as gtypes

    runner = InMemoryRunner(agent=agent, app_name="ma-gatekeeper-reflector")
    session_id = "introspection-" + os.urandom(4).hex()
    try:
        result = runner.session_service.create_session(
            app_name="ma-gatekeeper-reflector",
            user_id="reflector", session_id=session_id,
        )
        if _inspect.isawaitable(result):
            await result

        msg = gtypes.Content(
            role="user",
            parts=[gtypes.Part(text=(
                "Use the phoenix-mcp tools to list yesterday's traces in "
                "project 'ma-gatekeeper' and return a compact summary of "
                "escalation-tagged spans."
            ))],
        )
        chunks: list[str] = []
        async for event in runner.run_async(
            user_id="reflector", session_id=session_id, new_message=msg,
        ):
            content = getattr(event, "content", None)
            parts = getattr(content, "parts", None) or []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    chunks.append(t)
        return "\n".join(chunks)
    finally:
        # Reap MCP stdio child processes. `aclose()` is the ADK 1.x
        # contract on MCPToolset; older versions exposed `close()`.
        for tool in getattr(agent, "tools", None) or []:
            close = getattr(tool, "aclose", None) or getattr(tool, "close", None)
            if close is None:
                continue
            try:
                result = close()
                if _inspect.isawaitable(result):
                    await result
            except Exception as exc:
                _LOG.warning(
                    "Hook 4: failed to close MCP toolset %r: %s",
                    type(tool).__name__, exc,
                )


def _run_introspection_agent() -> str:
    """Hook 4 sync wrapper — invoked from `run_reflection_cycle`, which
    itself runs in a `run_in_executor` worker thread off the FastAPI
    request loop.

    `asyncio.run` is the right primitive here: it creates a fresh loop,
    sets it as the current loop for the duration, awaits the coroutine,
    and runs `shutdown_asyncgens` + closes the loop on exit. The
    previous `asyncio.get_event_loop().run_until_complete(...)` pattern
    raises `DeprecationWarning` on Python 3.12 (no loop in this thread)
    and `RuntimeError` on Python 3.14 — silently swallowed by the old
    bare `except`, which made Hook 4 a quietly-dead beat.

    Re-raises `CancelledError` (server shutdown should propagate); all
    other exceptions log with traceback + return "" so a Phoenix/MCP
    outage doesn't abort the nightly cycle.
    """
    try:
        return asyncio.run(_run_introspection_agent_async())
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOG.warning("Hook 4 introspection agent failed", exc_info=True)
        return ""


def assert_writable(dataset_name: str) -> None:
    if dataset_name not in _WRITABLE_DATASETS:
        raise PermissionError(
            f"Reflector forbidden from writing to dataset '{dataset_name}'. "
            f"Allowlist: {sorted(_WRITABLE_DATASETS)}"
        )


# ---------- statistics ----------

def paired_bootstrap_ci_lb(
    deltas: np.ndarray,
    *,
    n_resamples: int = 1000,
    alpha: float = 0.05,
    seed: int | None = 42,
) -> float:
    """One-sided lower bound at confidence (1-alpha) on mean(deltas).

    For a one-sided "candidate beats production" gate at alpha=0.05,
    we use the alpha-th percentile (5th), NOT alpha/2 (2.5th). v1 used
    alpha/2 which was actually a 97.5% one-sided LB (more conservative
    than advertised). Fixed per ML-reviewer findings.
    """
    if len(deltas) == 0:
        return float("-inf")
    rng = np.random.default_rng(seed)
    n = len(deltas)
    means = np.empty(n_resamples)
    for k in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[k] = deltas[idx].mean()
    return float(np.quantile(means, alpha))


def paired_bootstrap_se(
    deltas: np.ndarray,
    *,
    n_resamples: int = 1000,
    seed: int | None = 42,
) -> float:
    if len(deltas) == 0:
        return 0.0
    rng = np.random.default_rng(seed)
    n = len(deltas)
    means = np.empty(n_resamples)
    for k in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[k] = deltas[idx].mean()
    return float(means.std(ddof=1))


def epsilon_fold5(fold5_deltas: np.ndarray, *, floor: float = 0.03) -> float:
    """Plan §6.3 step 6: eps = max(1× paired bootstrap SE on fold 5, 0.03)."""
    return max(paired_bootstrap_se(fold5_deltas), floor)


def should_promote(
    *,
    regression_deltas: np.ndarray,
    fold5_candidate_scores: np.ndarray,
    fold5_production_scores: np.ndarray,
) -> tuple[bool, dict[str, float]]:
    """Return (promote, diagnostics) per plan §6.3 step 6."""
    fold5_deltas = fold5_candidate_scores - fold5_production_scores
    ci_lb_reg = paired_bootstrap_ci_lb(regression_deltas)
    eps = epsilon_fold5(fold5_deltas)
    cand_mean = float(fold5_candidate_scores.mean()) if len(fold5_candidate_scores) else 0.0
    prod_mean = float(fold5_production_scores.mean()) if len(fold5_production_scores) else 0.0
    non_regression_ok = cand_mean >= prod_mean - eps

    diag = {
        "regression_ci_lb": ci_lb_reg,
        "epsilon_fold5": eps,
        "fold5_candidate_mean": cand_mean,
        "fold5_production_mean": prod_mean,
        "fold5_non_regression_ok": float(non_regression_ok),
        "regression_gate_ok": float(ci_lb_reg > 0),
    }
    promote = (ci_lb_reg > 0) and non_regression_ok
    return promote, diag


# ---------- Phoenix wiring (real signatures, but a hackathon-quality
# implementation: enough to demo the loop end-to-end on Internal-30).

def _failing_traces(client, project_name: str, lookback_hours: int) -> list[dict]:
    """Pull spans whose `risk_judge_gate` annotation routed to 'escalate'.

    Important (Python-reviewer fix): we filter BEFORE returning. The
    previous version returned every span which polluted `regressions-v1`
    with successes — defeating the whole "regression dataset of failures"
    purpose.
    """
    try:
        spans = client.spans.get_spans_dataframe(project_name=project_name)
        if spans is None or len(spans) == 0:
            return []
        # The annotation name `risk_judge_gate` carries the lane label
        # (router.py writes it). Filter to escalations only; auto_clear
        # and block ARE NOT failures (block is a deliberate hard-stop).
        # The annotation column name from get_spans_dataframe depends on
        # phoenix.client version; try both standard shapes.
        cand_cols = [
            "annotation.risk_judge_gate.label",
            "annotations.risk_judge_gate.label",
            "risk_judge_gate.label",
        ]
        col = next((c for c in cand_cols if c in spans.columns), None)
        if col is None:
            _LOG.warning(
                "risk_judge_gate annotation column not found; columns=%s",
                list(spans.columns)[:30],
            )
            return []
        failing = spans[spans[col] == "escalate"]
        return failing.to_dict(orient="records")
    except Exception as exc:
        _LOG.warning("Failed to pull traces: %s", exc)
        return []


def _append_to_dataset(client, dataset_name: str, examples: Sequence[dict]) -> None:
    assert_writable(dataset_name)
    if not examples:
        return
    try:
        ds = client.datasets.get_dataset(name=dataset_name)
        client.datasets.append_examples(dataset=ds, examples=list(examples))
    except Exception as exc:
        _LOG.warning("append_to_dataset failed: %s", exc)


def _generate_candidate_prompt(failing_examples: Sequence[dict]) -> str:
    """Use Gemini to draft an improved cross_reference prompt.

    The meta-prompt is intentionally small for the hackathon: takes the
    last N failing cases, asks the model to propose 1 added instruction
    to the cross-reference rubric. Production would use DSPy or a
    BootstrapFewShot-style optimizer (plan §10 future work).
    """
    from google import genai
    client = genai.Client(vertexai=True)
    from .prompts import CROSS_REFERENCE_PROMPT
    meta = (
        "You are improving an M&A cross-reference agent's system prompt. "
        "Here is the current prompt followed by recent failure cases. "
        "Propose a REVISED full prompt that addresses the failures. "
        "Output ONLY the revised prompt, no commentary.\n\n"
        "CURRENT:\n" + CROSS_REFERENCE_PROMPT + "\n\n"
        "FAILURES (truncated):\n" + str(failing_examples[:5])
    )
    resp = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview"),
        contents=meta,
    )
    return resp.text or CROSS_REFERENCE_PROMPT


def _upsert_prompt(client, *, name: str, template: str, tag: str) -> str | None:
    """Create a new prompt version under `name`; tag it `tag`. Returns version id.

    Phoenix client API (verified): `client.prompts.create(...)` takes a
    `version` argument that is a `PromptVersion` payload, NOT a top-level
    `template=` kwarg. We build the PromptVersion with the helper, fall
    back to passing the template directly if the SDK version accepts the
    simpler form.
    """
    try:
        version_payload = None
        try:
            from phoenix.client.types import PromptVersion
            version_payload = PromptVersion(template=template,
                                            description=f"auto-{tag}")
        except Exception:
            pass
        if version_payload is not None:
            version = client.prompts.create(name=name, version=version_payload)
        else:
            # Older SDK accepted the flatter form; try as a fallback.
            version = client.prompts.create(name=name, template=template,
                                            prompt_description=f"auto-{tag}")
        version_id = (
            getattr(version, "id", None)
            or getattr(version, "version_id", None)
            or getattr(version, "prompt_version_id", None)
        )
        if version_id:
            client.prompts.tags.create(prompt_version_id=version_id,
                                       name=tag,
                                       description=f"auto-tagged {tag}")
        return version_id
    except Exception as exc:
        _LOG.warning("upsert_prompt failed: %s", exc)
        return None


@functools.lru_cache(maxsize=1)
def _genai_client():
    """Module-level cached google-genai client.

    Python-reviewer minor: previous version constructed a fresh client
    on every example, which on N=30 × 2 tags = 60 instantiations per
    nightly cycle. Cache once.
    """
    from google import genai
    return genai.Client(vertexai=True)


def _evaluate_one_example(client, example, prompt_template: str) -> float:
    """Run the cross_reference agent on one example and score with the
    faithfulness evaluator.

    This replaces the v3-B placeholder task that just returned the
    truncated prompt string. The score is the FAITHFULNESS evaluator's
    score on the agent's output against the example's clause text —
    that's what we expect a "better" prompt to improve.
    """
    from .evaluators import make_faithfulness_classifier

    genai_client = _genai_client()
    clause_text = example.get("clause_text") or example.get("input") or ""
    contents = f"{prompt_template}\n\nCLAUSE:\n{clause_text}"
    try:
        resp = genai_client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview"),
            contents=contents,
        )
        output = (resp.text or "").strip()
    except Exception as exc:
        _LOG.warning("agent call failed in experiment task: %s", exc)
        return 0.0

    try:
        f_clf = make_faithfulness_classifier()
        scored = f_clf.evaluate({"clause_text": clause_text, "tag": output[:200]})
        return float(scored[0].score)
    except Exception as exc:
        _LOG.warning("faithfulness scoring failed: %s", exc)
        return 0.0


def _run_experiment_pairwise(
    client, *, dataset_name: str, prompt_name: str,
    tags: tuple[str, str],
):
    """Run both prompt tags as separate experiments on the same dataset.

    Returns (cand_scores: np.ndarray, prod_scores: np.ndarray) aligned by
    example index. The task callable loads the prompt by tag and runs the
    real cross_reference agent against the example (Python+Arize
    reviewers flagged the v3 placeholder task that just returned the
    prompt string).

    `run_experiment` results expose evaluator scores as
    `result.runs[i].output` plus annotation rows. We pool the
    faithfulness-evaluator score per example into a numpy array.
    """
    try:
        ds = client.datasets.get_dataset(name=dataset_name)
    except Exception as exc:
        _LOG.warning("Could not fetch dataset %s: %s", dataset_name, exc)
        return np.array([]), np.array([])

    def make_task(tag: str):
        def task(example):
            prompt = client.prompts.get(prompt_identifier=prompt_name, tag=tag)
            tmpl_obj = getattr(prompt, "template", None) or prompt
            template_text = getattr(tmpl_obj, "text", None) or str(tmpl_obj)
            score = _evaluate_one_example(client, example, template_text)
            return {"output": "", "score": score, "tag": tag}
        return task

    per_tag_scores: dict[str, list[float]] = {tags[0]: [], tags[1]: []}
    for tag in tags:
        try:
            result = client.experiments.run_experiment(
                dataset=ds, task=make_task(tag),
                experiment_name=f"{prompt_name}@{tag}",
            )
            # Phoenix Experiment result exposes per-example runs; the
            # exact attr varies (`.runs`, `.results`, `.examples`). Try a
            # cascade.
            runs = (
                getattr(result, "runs", None)
                or getattr(result, "results", None)
                or getattr(result, "examples", None)
                or []
            )
            for r in runs:
                out = getattr(r, "output", None) or {}
                if isinstance(out, dict) and "score" in out:
                    per_tag_scores[tag].append(float(out["score"]))
        except Exception as exc:
            _LOG.warning("run_experiment(%s, tag=%s) failed: %s",
                         dataset_name, tag, exc)

    cand = np.array(per_tag_scores[tags[1]])
    prod = np.array(per_tag_scores[tags[0]])
    return cand, prod


def _promote_candidate(client, *, name: str, candidate_version_id: str) -> None:
    try:
        client.prompts.tags.create(
            prompt_version_id=candidate_version_id,
            name="production",
            description="auto-promoted by Reflector",
        )
        _LOG.info("PROMOTED candidate %s → tag=production on %s",
                  candidate_version_id, name)
    except Exception as exc:
        _LOG.warning("promote_candidate failed: %s", exc)


def _backstop_run_evals(client, project_name: str, lookback_hours: int) -> None:
    """Hook 7 — collapsed into the Reflector cron (plan §6.1 v3).

    Bulk-runs hallucination + faithfulness evaluators over the last N
    hours of production spans, writing annotations back. Equivalent
    batch coverage to AX Online Eval Tasks (which are SaaS-only).
    """
    try:
        from .evaluators import (
            make_faithfulness_classifier, make_hallucination_classifier,
        )
        from phoenix.evals import run_evals
        # Pull recent spans as a dataframe for run_evals.
        df = client.spans.get_spans_dataframe(project_name=project_name)
        if df is None or len(df) == 0:
            _LOG.info("Hook 7: no spans in lookback window.")
            return
        run_evals(
            dataframe=df,
            evaluators=[make_hallucination_classifier(),
                        make_faithfulness_classifier()],
        )
    except Exception as exc:
        _LOG.warning("backstop_run_evals failed: %s", exc)


def run_reflection_cycle(
    *,
    project_name: str = "ma-gatekeeper",
    lookback_hours: int = 24,
) -> dict:
    """Pull last-24h failing traces, grow regression dataset, iterate prompt.

    Each step is wrapped so a single failure (e.g., Phoenix MCP timeout)
    does not collapse the whole loop.
    """
    try:
        from phoenix.client import Client
    except Exception as exc:
        return {"error": f"phoenix.client unavailable: {exc}"}

    client = Client()

    # 0. Hook 4 — meta-agentic introspection via Phoenix MCP. The
    # LlmAgent calls list_traces / get-trace / get-span-annotations
    # tools directly so its summary of "what failed last night" is
    # generated by the same agent infrastructure being audited.
    introspection_summary = _run_introspection_agent()

    # 1. Collect failing traces (deterministic SDK path — the source of
    # truth for what we actually append to the regression set).
    failing = _failing_traces(client, project_name, lookback_hours)

    # 2. Append to regressions-v1 (allowlist-enforced).
    _append_to_dataset(client, "regressions-v1", failing)

    # 3. Generate candidate prompt and upsert with tag=candidate.
    candidate_template = _generate_candidate_prompt(failing)
    candidate_version = _upsert_prompt(
        client, name="cross_reference",
        template=candidate_template, tag="candidate",
    )

    # 4. Two experiments: regression set + frozen held-out fold 5.
    reg_cand, reg_prod = _run_experiment_pairwise(
        client, dataset_name="regressions-v1",
        prompt_name="cross_reference",
        tags=("production", "candidate"),
    )
    reg_deltas = (reg_cand - reg_prod) if min(len(reg_cand), len(reg_prod)) > 0 \
        else np.array([])

    f5_cand, f5_prod = _run_experiment_pairwise(
        client, dataset_name=_FROZEN_HELD_OUT,
        prompt_name="cross_reference",
        tags=("production", "candidate"),
    )

    # 5. Promotion decision.
    promote, diag = should_promote(
        regression_deltas=reg_deltas,
        fold5_candidate_scores=f5_cand,
        fold5_production_scores=f5_prod,
    )
    if promote and candidate_version:
        _LOG.info("Promotion gates passed: %s", diag)
        _promote_candidate(client, name="cross_reference",
                           candidate_version_id=candidate_version)
    else:
        _LOG.info("Promotion gates blocked: %s", diag)

    # 6. Hook 7 batch eval backstop on production spans.
    _backstop_run_evals(client, project_name, lookback_hours)

    return {"promoted": promote, **diag}


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print(run_reflection_cycle())
