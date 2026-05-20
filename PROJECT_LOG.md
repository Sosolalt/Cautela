# Project Log — M&A Due Diligence Gatekeeper

**Hackathon**: Google Cloud Rapid Agent Hackathon — Arize partner track ($5K first place).
**Deadline**: June 11, 2026, 23:00 GMT+2.
**Started**: 2026-05-19.
**Last updated**: 2026-05-20.

---

## How to read this log (resume protocol)

If you're picking this project up cold:

1. **Read TL;DR below first** (60 seconds).
2. **Then jump to "Current norm" (Phase 4)** — what is true right now.
3. **Then "Per-file last-edit map"** — what's stable vs newly rewritten.
4. **Only then read the phase narrative** if you need the why behind a decision.
5. **Before touching any external SDK code, read "What failed" → "Fabricated API signatures table"** — that's the most expensive-to-rediscover knowledge in this file.

If you're continuing the project: cross-check the per-file map against `git log` and `ls`. If reality has drifted from this log, the log is stale — fix it as your first task.

---

## Operating constraints (from user / CLAUDE.md)

- **Never run `git commit` or `git push`** unless the user explicitly asks. Diff/status/stage are fine when requested.
- User authorization phrases granted in-session (for scope, not durable):
  - "Make a detailed analysis" — green-light deep research with parallel agents.
  - "Run the plan" / "Don't wait for my permission" — autonomous execution of the implementation plan within reversible local actions.
  - "Run a flot of agents to double check everything" — green-light multi-expert review rounds until convergence.
  - "Do this loop until they all give their validation" — stop condition is unanimous reviewer VALIDATED, not "good enough".
- User email: hugo.majerczyk@proton.me (used as SEC EDGAR identity per fair-use rules).

---

## TL;DR

A vertical M&A contract-review agent (Gemini 3 + Google ADK + Arize Phoenix on Cloud Run) went through:

- **4 rounds of plan reviews** by 4 independent expert reviewers → fully converged plan in `plan.md`.
- **Initial scaffolding** of 8 Python modules, 3 scripts, Dockerfile, 31 unit tests (all pass).
- **4 rounds of expert code reviews** by 5 specialist reviewers (legal/M&A, senior Python/ADK, Arize founding engineer, ML statistician, senior SRE).
- Discovered the scaffold was riddled with **fabricated API signatures**; rewrote against ground-truth docs.
- **All 5 reviewers VALIDATED** by round D. Final scores: legal 8.5, Python 9, Arize 9, ML 9, DevOps "would deploy".

Current state: codebase is correctness-validated. Outstanding work is operator-side per `HANDOFF.md` (GCP credentials, Phoenix deploy, 30-contract annotation, demo recording, Devpost submission).

---

## Phase 0 — Origin and idea selection

### Inputs
- `Hackathon summary.md`: track rules, deadline, judging criteria.
- `Arize AI Hackathon Strategy.md`: deep dive on Arize Phoenix capabilities, MCP, OpenInference, case studies of past winners (OilyRAGs, OpsRocket, Panelyst, Watchful.AI).

### Three candidate ideas
1. **M&A Financial Analyst / Bylaws Agent** — high impact ($, prestige), validated market, dataset risk if scoped wrong.
2. **Portfolio Management (FinRobot reimpl)** — rejected: derivative, sprawling for 3-week sprint, weak on "Quality of Idea".
3. **Automated Document Review Gatekeeper** — clean architecture, asymmetric-loss story matches Arize observability story.

### Selected
A synthesis: **"M&A Due Diligence Gatekeeper"** — Idea 3's clean architecture targeted at Idea 1's high-stakes domain. Reviews CoC, anti-assignment, MAC, and accelerated-vesting clauses; routes findings into Auto-Clear / Escalate / Block lanes.

---

## Phase 0.5 — Research (4 parallel background agents)

Before drafting `plan.md` v1, I launched 4 research agents in parallel (each ~1500 words, ~3 minutes runtime). Their findings shaped every section of the plan; quoting the load-bearing conclusions here so they survive even if the agent transcripts are lost:

### Market & competitors research
- M&A due diligence: **30-90 days, $50K-$200K mid-market, $200-$500/hr legal**. Source: Peony 2025.
- 70-90% deal failure rate is **a worn HBR cliché** — do NOT cite as causal evidence. McKinsey's "50% of transformative value loss" is correct but does NOT attribute that solely to diligence.
- Real CUAD CoC SOTA F1 is **~70-80%**, not the 95%+ vendor marketing implies.
- Harvey is already agentic M&A; Kira has had M&A modules since 2018. **Vertical + agentic alone is not a differentiator.**
- No public competitor publishes per-clause recall at a stated abstention budget — that's the wedge.

### Arize Phoenix research
- 7 hooks identified: OpenInference tracing → inline LLM-as-judge → span annotations → MCP introspection → auto-growing dataset → prompt versioning + experiments → scheduled batch eval.
- **Phoenix MCP cannot launch experiments or write span annotations** — those require the Python SDK. Architecture must respect this split.
- **AX Online Eval Tasks are SaaS-only** — NOT available in self-hosted Phoenix. Use Cloud Scheduler + `run_evals` instead.
- `arize-phoenix-otel` ships `register(...)` with `set_global_tracer_provider=False` kwarg to avoid collisions with Vertex's default tracer.

### Datasets research
- **MAUD**: 152 real merger agreements, 47k labels, 92 ABA deal-point MCQs. CC-BY-4.0. Format is **multiple-choice**, NOT span extraction — do not conflate with CUAD.
- **CUAD**: 510 contracts, ~13k spans, native SQuAD JSON. Span-level CoC + Anti-Assignment labels (noisy). CC-BY-4.0.
- **EdgarTools MCP exists** at `@dgunning/edgartools` (MIT) — pulls live 8-K Exhibit 2.1 filings, no API key, no rate limits. Confirmed key accelerator.
- Annotation realism: 200-300 spans across 30 contracts = **15-25 hours, not "2 evenings."** LLM-assist + adjudication is mandatory.

### Google Cloud + ADK research
- ADK 2.0 (`pip install google-adk`) is the recommended SDK. `LlmAgent` + `SequentialAgent` + `ParallelAgent` + `MCPToolset`.
- **Gemini 3 Pro = 1M context** (≈1,500 pages); Files API > inline bytes for >10-page PDFs.
- Cloud Run scales to zero → cheap demo; `adk deploy cloud_run` one-liner.
- **A2A protocol** (Google → Linux Foundation, 150+ orgs) is for cross-org agents; ADK `sub_agents` is the right in-process pattern for a single-team demo.
- $300 free credit + the $300 hackathon credit handle the whole sprint trivially.

These 4 research reports were the foundation for all subsequent plan rounds. They are NOT preserved as separate files — only their conclusions in this log and in `plan.md` §14 citations.

---

## Phase 1 — Plan iteration (4 review rounds)

### Round 1: Plan v1
**What was drafted**: complete plan with sections §0–§14 covering exec summary, market, competitors, technical architecture, data strategy, Arize integration, timeline, demo flow, UX, extensions, risks, submission checklist.

**Reviewers** (4 parallel, expert briefs):
- Market/concept reviewer (M&A + hackathon judge)
- Architecture/Arize reviewer (staff engineer)
- Data strategy reviewer (legal-NLP ML researcher)
- Timeline/UX reviewer (hackathon veteran + product designer)

**Verdict round-A**: All 4 NOT VALIDATED. Score range 4–6/10.

**Major issues flagged**:
- "70–90% of deals fail" — unsupported splice of HBR cliché + McKinsey
- "$22B TAM" — fantasy back-of-envelope math
- "100% precision gatekeeper" — slogan with no operationalized metric
- 0.90 threshold hand-picked from thin air
- `HallucinationEvaluator` calling convention wrong (`hallucination(input=..., output=..., context=...)`)
- Online Eval Tasks claimed available on self-hosted Phoenix — actually AX SaaS only
- MAUD reading-comprehension MCQ vs span-extraction format conflated as a single eval
- 60 contracts × 200–300 spans "in 2 evenings" — actually 15–25 hours of work
- D1 = "Phoenix deploy + iframe validation in one day" — actually 2–3 days
- D20 = "record + submit + warm-up + README polish" — single-day cliff

### Round 2: Plan v2
**Changes applied**:
- Dropped fantasy stats; sourced citations only.
- "100% precision" → "100% recall on Block-tier clauses at a published abstention rate."
- Acknowledged CUAD CoC SOTA ~70–80% F1, not 95%+.
- Reframed wedge around the Reflector self-improvement loop (the genuine differentiator).
- 3 separate eval tracks: MAUD-MCQ, CUAD-Spans, Internal-30 (30 contracts, recall@abstention).
- LLM-assist annotation mandated; Cohen's κ on 10 contracts.
- 5-deal pre-vetted allow-list for live demo (no open ticker box).
- Reflector promotion rule kept; threshold calibration sweep added.
- `LLM(provider="vertexai")` (still wrong, caught later).
- Online Eval Task → Cloud Scheduler `run_evals` cron (correctly disambiguated from AX SaaS).
- D1 stretched to D1–D2 for Phoenix infra.

**Verdict round-B**: Market reviewer VALIDATED at 8/10 with 1 carryover. Other 3 still NOT validated.

### Round 3: Plan v3
**Major fixes**:
- §6.2 code: replaced `(h+f)/2` averaging (which can let a hallucinated explanation auto-clear at high faithfulness) with **independent gating** per evaluator.
- Reflector promotion rule v2 (`δ > 0.05`) → **paired bootstrap CI lower bound > 0** AND **non-regression on a frozen held-out fold-5** with `ε = max(SE, 0.03)`.
- Calibrate-on-test contamination → **5-fold CV** with held-out fold for τ selection.
- Demo restructure: pre-load Phoenix in split-screen for the cmd+click reveal; close on auto-promotion event; pre-record EDGAR fallback.
- Recording moved D20 → D19; D20 = pure submission.
- 8 extensions → cut to 2 (Playbook customization, HITL annotation).
- Dead-URL risk Low → High; added Vertex quota risk, Devpost form risk, video aspect ratio risk.

**Verdict**: Market converged (carryover applied); Architecture/Arize NOT (LLM-as-judge code shape still wrong, `(h+f)/2` defended; promotion rule statistical noise); Data NOT (calibrate-on-test, missing held-out fold); Timeline NOT (D9/D15/D20 overloaded, PDF↔trace sync hidden 2-day work, missing risks).

### Round 4: Plan v4 (final)
**Final fixes**:
- §6.2 code: `LLM(provider="vertex")` (still wrong — caught in code review later), `min(h,f)` analytics summary, three-annotation pattern.
- Reflector ε explicitly `max(SE_fold5, 0.03)` floor for degenerate case.
- 5-fold CV with **fold 5 reserved** as frozen held-out for Reflector non-regression; **effective N=24** explicitly disclosed.
- **Expected CI width pre-disclosed**: "~±0.10–0.15 given N=24 with 6–10 Block findings per fold; LB clearing 0.95 is arithmetically tight, not a guarantee."
- Pre-commitment: publish achieved Wilson LB unmodified, no quiet downgrade.
- PDF bbox stashed in `Clause.pdf_bbox` at D4 (Parser) and onto span attributes at D7 (Risk Judge) — makes D15 sync a 1-day lookup task, not a hidden 2-day item.
- D20 split: recording moved to D19, D20 pure submission/warm-up.
- 7 new risk rows: 5-fold CV impl bug, Reflector writes to fold 5 (code-enforced allowlist), wide bootstrap CI, pre-seeding judge perception, D20 overload, PDF bbox extraction failure.
- 6 new §12 items: Devpost browse-line, YouTube public/unlisted-link-accessible, AI disclosure, backup Phoenix screenshot, pre-seeding disclosure, warmed Phoenix.

**Verdict round-D**:
- Market: VALIDATED 8/10
- Architecture/Arize: VALIDATED 9/10
- Data: VALIDATED 9.2/10
- Timeline/UX: VALIDATED 8.5/10

**Plan converged.** All 14 sections locked.

### Plan-iteration lessons
- Reviewers needed to be **briefed with the prior round's verdict** so they could check what was supposedly fixed without re-reading the whole plan.
- Single most valuable feedback per round was always the **statistical-honesty** flag (one-sided vs two-sided, calibrate-on-test, ε vs noise floor) — judges respect operationalized numbers; slogans get cut.
- **Cutting features beat adding them** — going from 8 extensions to 2, from 60-contract to 30-contract eval, from 2-pane sync to 1-pane fallback.

---

## Phase 2 — Initial codebase scaffolding

### Goal
Translate `plan.md` v4 into runnable Python with full test coverage of pure-Python correctness paths.

### Scaffold (8 modules + 3 scripts + 4 test files)

```
ma_gatekeeper/
  agent/
    schemas.py            # Pydantic models per §4.3
    instrumentation.py    # phoenix.otel.register
    evaluators.py         # hallucination + faithfulness via create_classifier
    router.py             # deterministic Python independent-gating
    agents.py             # ADK Parser → Classifier → Cross-Ref → Risk Judge
    prompts.py            # fallback prompt templates
    reflector.py          # nightly self-improvement loop (math + helpers)
    server.py             # FastAPI: /review, /review-by-deal, /reflect
  scripts/
    download_datasets.py
    perturb_contracts.py  # adversarial slice + leakage AUC audit
    calibrate.py          # 5-fold CV + reliability diagrams + Wilson/bootstrap CIs
  tests/
    test_fold_split.py    # D9-morning unit test
    test_promotion_rule.py
    test_router.py
  Dockerfile, requirements.txt, .env.example, .gitignore, README.md, HANDOFF.md
```

### Tests at end of Phase 2
- **23/23 unit tests passing** on math + dataclass + gating logic.
- No integration tests (no live Phoenix, ADK, or Vertex available).

### What I believed at this point
"Scaffolding is correct; the plan converged; the user can now hand off to D1 GCP work."

**This was wrong.** The next phase exposed why.

---

## Phase 3 — Expert code reviews (Rounds A–D)

### Reviewer panel
1. **Legal/M&A + Hackathon judge** — domain correctness + winnability.
2. **Senior Python/ADK engineer** — code review for hallucinated APIs, async bugs, deploy gotchas.
3. **Arize Phoenix founding engineer** — verified every Phoenix API against live docs.
4. **ML statistician** — calibration, bootstrap math, reliability semantics.
5. **Senior SRE** — Dockerfile, secrets, CORS, OIDC, blast-radius.

### Round A: 5/5 NOT VALIDATED

| Reviewer | Score | Critical finding |
|---|---|---|
| Legal | 6.5/10 | "25% threshold" tell in CROSS_REFERENCE_PROMPT betrays non-lawyer authorship; MAC carve-out narrowing and accelerated vesting missing despite being headline; server.py:107 stub collapsed two-evaluator story |
| Python/ADK | 4.0/10 | ADK import path wrong; `root.run_async(pdf_bytes=...)` doesn't exist; event shape fabricated; `phoenix.evals.LLM(provider="vertexai")` wrong; `create_classifier(...)` not callable that way; `client.annotations.add_span_annotation` deprecated; `client.prompts.get(name=...)` wrong; ~10 more |
| Arize | 3.0/10 | Verified every Phoenix call against live docs — almost all wrong shapes. 5 of 7 hooks were silent `pass` stubs. No `MCPToolset` import despite docstring claim |
| ML stats | NOT | `alpha/2` quantile makes bootstrap 97.5% one-sided not 95%; `z=1.96` Wilson is two-sided; parametric Binomial bootstrap ignores per-contract correlation; reliability diagram code missing |
| DevOps | NOT | `/reflect` unauthenticated → money + dataset-integrity exposure; `SEC_EDGAR_USER_AGENT` declared but never read → SEC will 403; no CORS; no upload cap; passcode in query string leaks to logs; fail-open on missing passcode; Dockerfile bloated; `$PORT` not honored |

### The pivot moment
The **Arize founding engineer reviewer used WebFetch to verify each Phoenix API against live docs**. That brief is what made the rewrite possible — I now had ground truth to write against, not just my own assumptions.

### Round B: comprehensive rewrite

Files touched: every Python module except `schemas.py` (which was already correct).

#### Verified API corrections applied
| What I wrote | What the API actually is |
|---|---|
| `LLM(provider="vertexai", model=...)` | `LLM(provider="vertex", model=...)` |
| `clf(context=..., explanation=...)` returning object with `.score` | `clf.evaluate({"context": ..., "explanation": ...})` returning `List[Score]`; index `[0]` |
| `client.annotations.add_span_annotation(...)` | `client.spans.add_span_annotation(...)` (annotations.* deprecated as of 1.17) |
| `client.prompts.get(name=..., tag=...)` | `client.prompts.get(prompt_identifier=..., tag=...)` |
| `client.prompts.upsert(...)` | `client.prompts.create(name=, version=PromptVersion(...))` |
| `client.prompts.add_version_tag(...)` | `client.prompts.tags.create(prompt_version_id=, name=, ...)` |
| `client.experiments.run_experiment(dataset="regressions-v1", task=...)` | `dataset` must be a `Dataset` object from `client.datasets.get_dataset(name=...)` |
| `from google.adk import LlmAgent, ParallelAgent, SequentialAgent` | `from google.adk.agents import ...` |
| `root.run_async(pdf_bytes=pdf_bytes)` | `InMemoryRunner(agent=root, app_name=...).run_async(user_id=..., session_id=..., new_message=Content(parts=[Part.from_bytes(data=..., mime_type="application/pdf")]))` |
| `event.name`, `event.value` | `event.author`, `event.content.parts[i].text` |
| `np.quantile(means, alpha/2)` for "one-sided 95% LB" | `np.quantile(means, alpha)` |
| Wilson `z = 1.96` for "one-sided 95% LB" | `z = 1.6449` |
| Parametric `rng.binomial(n, p, ...)` bootstrap | Cluster bootstrap resampling **contracts** (each carrying its full hit-vector) |
| `asyncio.get_event_loop()` | `asyncio.get_running_loop()` |
| `@app.on_event("startup")` | `@contextlib.asynccontextmanager lifespan` + `FastAPI(lifespan=...)` |
| `EdgarTools attachment.download()` returns bytes | Writes to disk, returns path; need `tempfile.TemporaryDirectory()` |
| `provided != DEMO_PASSCODE` | `hmac.compare_digest(provided, DEMO_PASSCODE)` |
| Passcode in `?p=` query string | Header-only (`X-Demo-Passcode`) — query strings log-leak |
| `if not DEMO_PASSCODE: return` | Fail closed: 503 |
| Dockerfile `ENV PORT=8080` + `--port 8080` hard-coded | `CMD ["sh","-c","uvicorn ... --port ${PORT:-8080}"]` |
| `libmupdf-dev`, `build-essential` for PyMuPDF | Manylinux wheels — no system deps needed |

#### Domain corrections applied
- Replaced "25% threshold" with verbatim contract phrasing requirement: "majority of voting power", "controlling interest", "beneficial ownership", "power to direct or cause the direction of management".
- Added explicit MAC carve-out narrowing detection (pandemic, regulatory change, industry-wide).
- Added accelerated vesting (single vs double-trigger; options/RSUs/PSUs).
- Added beneficial vs record ownership distinction.
- Severity rubric expanded from 12 words to per-lane concrete examples.
- Three-annotation pattern: `hallucination`, `clause_faithfulness`, `risk_judge_gate` (Arize canonical).

#### Statistical corrections applied
- One-sided alpha (5th percentile) for bootstrap CI lower bound.
- `Z_ONE_SIDED_95 = 1.6449`.
- Cluster bootstrap over `contract_hits[cid] = list[hits]`.
- Reliability diagram via real matplotlib; full pool + `is_block` ground-truth labels.
- ε(fold5) = `max(paired_bootstrap_se(fold5_deltas), 0.03)`.

#### Security corrections applied
- `/reflect` OIDC bearer verification via `google.oauth2.id_token.verify_oauth2_token(...)` against `REFLECT_OIDC_AUDIENCE`.
- `set_identity(SEC_USER_AGENT)` called in `lifespan`; module-level `_sec_ready` flag; `/review-by-deal` 503s if false.
- CORS middleware with whitespace-stripped allow-origins list.
- Upload size cap (50MB default): pre-check `Content-Length`, chunked read with cumulative cap.
- Non-root `USER 1000` in Dockerfile.

**Verdict round-B**: Legal VALIDATED 8.5/10. Others still NOT (7.5, 8, NOT, NOT).

### Round C
Specific remaining items addressed:
- `_failing_traces` actually filters by `risk_judge_gate.label == "escalate"` (cascade over 3 column-name variants).
- `_run_experiment_pairwise.task` now calls `_evaluate_one_example` which invokes the real cross_reference agent via `genai.Client().models.generate_content(...)` and scores with the faithfulness evaluator.
- `prompts.create(version=PromptVersion(...))` with fallback to flat kwarg for older SDKs.
- `plot_reliability` semantics: bin scores over **full pool**, use `is_block` ground-truth labels.
- `MCPToolset(connection_params=StdioServerParameters(command="npx", args=["-y", "@arizeai/phoenix-mcp@latest", "--baseUrl", ..., "--apiKey", ...]))` real wiring.
- `build_introspection_agent()` LlmAgent with `tools=[toolset]`.
- `@functools.lru_cache(maxsize=1)` on classifier factories.
- `inspect.isawaitable` guard around `create_session` for ADK 1.x sync/async drift.
- `Part.from_bytes(data=, mime_type=)` verified against `googleapis/python-genai` main.

**Verdict round-C**: Python 9/10 VALIDATED. ML stats 9/10 VALIDATED. DevOps VALIDATED. Legal already validated. Arize NOT — `build_introspection_agent()` defined but never invoked from `run_reflection_cycle`.

### Round D
- Added `_run_introspection_agent()` helper that builds the introspection agent, wraps in `InMemoryRunner`, drains `runner.run_async(...)` for text parts.
- Wired it as step 0 of `run_reflection_cycle()`.
- Module-level `@functools.lru_cache _genai_client()` (Python-reviewer minor).

**Verdict round-D**: Arize 9/10 VALIDATED. **All 5 reviewers now validated.**

---

## What was tested

### Passing throughout (31/31)
- `tests/test_fold_split.py` (7) — fold assignment deterministic per contract; no contract spans folds; all 5 folds populated; each source in ≥2 folds; unit-test catches injected leakage; `FROZEN_FOLD == 5`.
- `tests/test_promotion_rule.py` (9) — bootstrap CI math on positive/zero/negative deltas; ε floor honored; ε uses SE when above floor; promotion fires on both gates; blocked when CI includes 0; blocked when fold-5 regresses; allowlist refuses writes to frozen dataset.
- `tests/test_router.py` (7) — block severity passing both gates keeps block; info severity passing both auto-clears; **hallucination fail escalates even at 0.95 faithfulness** (the critical asymmetric-loss test); faithfulness fail escalates even at 0.99 hallucination score; watch always escalates; `threshold_applied = min(τ_h, τ_f)`; `Thresholds.from_json` loads correctly.
- `tests/test_stats.py` (8) — Wilson constant is one-sided 95% (~1.6449), not 1.96; LB monotone in successes; LB on 0/0 is 0; cluster bootstrap handles empty; cluster bootstrap point equals pooled mean; cluster bootstrap LB ≤ point; cluster bootstrap respects within-contract clustering.

### What was NOT tested (acceptable for hackathon)
- Live Phoenix integration (requires self-hosted instance).
- Live Vertex AI Gemini calls (requires GCP credentials).
- Live ADK runner end-to-end (requires PDF + Files API + quota).
- Live EdgarTools 8-K fetch (requires SEC identity).
- Live MCP server connection (requires `npx` + `@arizeai/phoenix-mcp` running).
- Frontend (Next.js skeleton deferred — depends on D1 iframe-validation decision).

### Test pattern that worked
Every test is **pure Python with no live API calls**, using small synthetic dataframes and deterministic seeds. This lets every rewrite of the SDK boundary keep the test suite green and catch logic regressions immediately.

---

## What failed

### Things that were claimed and then proven wrong
- "Scaffolding is correct" after Phase 2 — round A found ~15 fabricated API signatures.
- "API verification step before D7 will catch any issues" — this is a deferral, not a verification; reviewers caught the issues in code review before D7.
- v1 averaging `(h + f) / 2` for risk score — averaging across two evaluators with different failure modes hides one signal; a hallucinated explanation can auto-clear at high faithfulness. Tests in `test_router.py` would not have caught this without the explicit `test_hallucination_fail_escalates_even_high_faithfulness` test.
- v2 promotion rule `δ > 0.05` on N=30 — statistical noise, plus a Goodhart trap (promote prompts overfit to the same failures used to train them). Required paired bootstrap CI + frozen held-out fold + SE-scaled ε.
- "60 contracts in 2 evenings" annotation budget — actually 15–25 hours; corrected to 30 contracts with LLM-assist + κ on a 10-contract double-annotated subset.

### Things that almost shipped wrong but were caught
- `provider="vertexai"` (would have raised on first call).
- Single-annotation `min(h,f)` (would have hidden one signal in Phoenix analytics).
- `client.annotations.*` (deprecated path; would silently no-op in production).
- `/reflect` open to the internet (would expose Vertex experiments to anyone).
- Upload with no size cap (Vertex billing incident waiting).
- `build_introspection_agent()` defined but never invoked (Hook 4 vapor — judges grep for it).

---

## Current norm (as of 2026-05-20)

### Code state
- 8 Python modules: schemas, instrumentation, evaluators, router, agents, prompts, reflector, server.
- 3 scripts: download_datasets, perturb_contracts, calibrate.
- 4 test files: 31/31 passing.
- Dockerfile: slim, non-root, $PORT-aware.
- All 5 expert reviewers validated.

### Plan state
- `plan.md` v4 — converged across 4 review rounds.

### Outstanding work (in `HANDOFF.md`)
3-week timeline summary — full details in `plan.md` §7 and `HANDOFF.md`:

| Days | Phase | Outputs |
|---|---|---|
| D1–D2 (May 20–21) | Phoenix infra | Self-hosted Cloud Run + iframe validation + reverse-proxy through own domain |
| D3 (May 22) | ADK skeleton | Bootstrap from `Arize-ai/gemini-hackathon`; Vertex quota request |
| D4 (May 23) | Parser | Gemini 3 Pro + Files API + `Clause.pdf_bbox` extraction |
| D5–D9 (May 24–28) | Annotation + calibration | 30 contracts → `Internal-30`; 5-fold CV; τ_h, τ_f deployed |
| D10 (May 29) | Allow-list | 5 hand-picked EDGAR 8-K Ex 2.1 deals |
| D11–D14 (May 30–June 2) | Reflector loop | MCP introspection + experiment + promotion against real Phoenix |
| D15–D17 (June 3–5) | Frontend | Next.js + PDF viewer + bidirectional sync + SSE streaming + hardening |
| D18 (June 6) | Pre-seed | 48h Reflector pre-seed for the demo recording delta |
| D19 (June 7) | Recording | 3-min demo + EDGAR fallback pre-record + Phoenix split-screen |
| D20 (June 8) | Submission | Pure submission day; Devpost form + Cloud Run warming |
| D21 (June 10) | Buffer | 24h verify before June 11 deadline |

### What I chose NOT to do (deliberate scope cuts)

- **Next.js frontend**: deferred to D15 per HANDOFF.md. Reasoning: the frontend depends on the D1 Phoenix-iframe-validation decision; building it before that is wasted work.
- **Live integration tests**: no test hits live Phoenix, Vertex, ADK runner, EdgarTools, or the Phoenix MCP server. Reasoning: would require operator credentials and would lock the test suite to network conditions. Unit tests cover pure-Python correctness paths (math, gating logic, schemas, allowlist enforcement).
- **Custom evaluator beyond hallucination + faithfulness**: kept to 2. Reasoning: 3+ evaluators bloat the calibration grid and the inline judge cost without clear differentiation gain.
- **More than 30 contracts in Internal-30**: capped at 30. Reasoning: round-A reviewers showed 60 in 2 evenings was a 3x underestimate; cap honors the realistic annotation budget.
- **More than 5 demo deals in the allow-list**: capped at 5. Reasoning: each must be pre-validated to surface a Block-tier finding; more deals = more curation overhead with no demo benefit.
- **CI/CD via GitHub Actions**: not set up. Reasoning: tests run locally with `pytest`; Cloud Build will run on `gcloud run deploy` automatically.
- **A2A protocol**: mentioned only in plan §10 as future work. Reasoning: A2A is for cross-org agents; single-team hackathon submission doesn't need it.
- **Multi-language contract support**: deferred. Reasoning: eval would need multilingual annotators; out of scope for 3 weeks.

These cuts each survived a reviewer round. They are listed here so future iterations don't accidentally re-introduce them.

### Pre-commitments locked in
- Publish achieved Block-recall Wilson LB unmodified, even if well below 0.95.
- Demo voiceover must say "five pre-indexed deals" (no soft-deceptive "recently indexed").
- Reflector pre-seeding disclosed in README ("production prompt deliberately seeded weaker 48h before demo recording").
- Three-track eval table in README (MAUD-MCQ, CUAD-Spans, Internal-30).
- Apache 2.0 LICENSE in repo "About" sidebar.
- Arize track checkbox in Devpost form.

---

## Meta — skills this project produced

The process that worked here was extracted into two reusable Claude skills committed to the repo at `.claude/skills/`:

- **`expert-review-loop`** — the multi-expert parallel-review-until-convergence pattern. Spawn 3-5 specialist reviewers, brief each with a domain-specific prompt + the prior round's verdict, hold all fixes until every reviewer returns, loop until each independently says VALIDATED.
- **`project-log`** — the structure of this very file. Single append-only `PROJECT_LOG.md` at repo root, with required sections (TL;DR, Phase 0..N, What was tested, What failed, Current norm, Lessons, Per-file last-edit map). Companion to `expert-review-loop`.

If you're starting a new project of comparable complexity, invoke these two skills before writing the first plan, not after.

---

## Lessons for future projects

1. **Multi-expert parallel review caught what one general reviewer would have missed.** Each specialist (legal, Python, Arize, stats, SRE) found 5–15 issues a generalist would miss.
2. **Brief reviewers with the prior round's verdict.** Round-B prompts said "round-A verdict was X; v3 claims to have fixed each item; verify". This kept reviewers focused on convergence rather than re-litigating.
3. **WebFetch-verified API signatures are the only ground truth.** My own assumptions about Phoenix/ADK APIs were wrong in 15+ places. Don't write SDK code without a doc URL open.
4. **Tests should encode the asymmetric-loss invariants.** The single most valuable test in `test_router.py` is the one asserting a hallucinated explanation cannot auto-clear at high faithfulness — that's the entire safety promise in one assertion.
5. **Cutting features beats adding them.** Plan v4 has 2 extensions, not 8. Eval has 30 contracts, not 60. UI has 1 mandatory pane, not 3. Each cut survived a reviewer.
6. **Statistical honesty over slogans.** "100% recall" → "Wilson LB clearing 0.95 is arithmetically tight, not a guarantee". "Pre-commit to publishing achieved number unmodified" beats overclaiming.
7. **The Reflector self-improvement loop is the wedge.** Not vertical M&A focus (Harvey/Kira have that). Not the agent itself (Gemini does the work). The thing no public competitor ships is the experiment-gated prompt promotion with frozen-fold non-regression check.

---

## Per-file last-edit map

```
plan.md                              v4 (4 review rounds)
ma_gatekeeper/agent/schemas.py       v2 (added clause_text, cited_spans_text, pdf_bbox)
ma_gatekeeper/agent/instrumentation.py v2 (set_global_tracer_provider kwarg verified)
ma_gatekeeper/agent/evaluators.py    v3 (real phoenix.evals API + lru_cache)
ma_gatekeeper/agent/router.py        v3 (3 annotations, client.spans.add_span_annotation)
ma_gatekeeper/agent/agents.py        v3 (google.adk.agents import path; prompt_identifier=)
ma_gatekeeper/agent/prompts.py       v3 (MAC, vesting, beneficial/record, mgmt-control, severity)
ma_gatekeeper/agent/reflector.py     v4 (real MCPToolset; introspection agent wired; PromptVersion)
ma_gatekeeper/agent/server.py        v4 (Runner+Content+Part; OIDC; CORS; upload cap; lifespan)
ma_gatekeeper/scripts/calibrate.py   v3 (one-sided Wilson; cluster bootstrap; real reliability)
ma_gatekeeper/scripts/download_datasets.py  v1 (untouched after Phase 2)
ma_gatekeeper/scripts/perturb_contracts.py  v1 (leakage AUC < 0.6 to ship)
ma_gatekeeper/tests/test_fold_split.py      v1
ma_gatekeeper/tests/test_promotion_rule.py  v2 (epsilon SE test tightened)
ma_gatekeeper/tests/test_router.py          v1
ma_gatekeeper/tests/test_stats.py           v1 (new — covers Wilson + cluster bootstrap)
ma_gatekeeper/Dockerfile             v2 (slim, non-root, $PORT-aware)
ma_gatekeeper/requirements.txt       v2 (removed pymupdf; added arize-phoenix-otel, google-auth, openinference-vertexai)
ma_gatekeeper/README.md              v1
ma_gatekeeper/HANDOFF.md             v1
PROJECT_LOG.md                       this file
```

---

*End of project log v1.*
