# Commit plan — `ma_gatekeeper` initial history (v4)

## Goals and constraints

- Initialize the repo and lay down history as **a sequence of 11 atomic commits** that tell the project's story honestly.
- **Buildable at every commit**: `cd ma_gatekeeper && pytest tests/ -v` against whatever exists at HEAD should pass; later commits add tests for code introduced in the same commit. (Some commits add no tests because the only failure mode is live-integration — those are noted explicitly.)
- **Atomicity over cosmetics**: where two modules are leaf-level Phoenix-SDK bindings with the same dependency profile, they ride together — the alternative is a 12th commit, which the user capped at 11.
- **Per CLAUDE.md**: I write the plan and stage files; the human runs `git init`, `git commit`, `git push`.
- **No `Co-Authored-By: Claude` trailer** in any of the 11 commit messages below. Per user preference: drafted commit messages stand on their own; the AI-assistance disclosure lives in the README (Devpost requirement), not in `git log`.

## Changes vs v3 (review-round-C / independent-validation feedback)

| # | Round-D finding | Fix in v4 |
|---|---|---|
| 1 | `COMMIT_PLAN.md` itself was unaccounted-for: not in any commit, not in the "deliberately did NOT do" list. After commit 11 the user would see it as untracked in `git status` and have to make an unscripted call. | Added explicit "deliberately did NOT do" entry below: `COMMIT_PLAN.md` is a transient planning artifact for the initial laydown, intentionally left untracked. The historical narrative is preserved in `PROJECT_LOG.md` (committed in 11), which is the right place for it; this file gets deleted or kept locally at the user's discretion after the laydown is complete. |

## Changes vs v2 (review-round-B feedback)

| # | Round-B finding | Fix in v3 |
|---|---|---|
| 1 | Commit 3's message listed symbols that don't exist in `schemas.py` (`ClauseClassification`, `CrossReference`, `ReviewReport`) and omitted `GatekeeperDecision` (which `router.py` imports), `ClauseTag`, the `Tag` literal, and `Severity` | Rewrote commit 3's message to match the actual file: `Clause`, `ClauseTag`, `RiskFinding`, `GatekeeperDecision`, plus the `Tag`, `Severity`, `Lane` Literal aliases |
| 2 | Called `Lane` an "enum" — it's a `Literal["auto_clear", "escalate", "block"]` alias, not an `enum.Enum` | Reworded as "Literal type alias" |

## Changes vs v1 (review-round-A feedback)

| # | Round-A finding | Fix in v2 |
|---|---|---|
| 1 | `pytest` would fail at commits 6+10 because `from agent.X` / `from scripts.X` needs `pythonpath` config | Commit 1 now ships `ma_gatekeeper/pyproject.toml` with `[tool.pytest.ini_options] pythonpath = ["."]` |
| 2 | `scripts/__init__.py` missing — `from scripts.calibrate` import fails | Commit 1 now ships `ma_gatekeeper/scripts/__init__.py` |
| 3 | Commit 10 too lumpy (reflector + 3 unrelated scripts + 3 tests) | Split into **commit 9 (data-plumbing scripts)** and **commit 10 (reflector + calibrate + 3 tests)**. To preserve the 11-cap, merged old commits 4+5 into a single Phoenix-SDK-binding commit (atomicity preserved — both are leaf phoenix.* wrappers with identical dep profile). |
| 4 | Spot-check `agent/__init__.py` for heavy SDK imports | Verified: 1-line docstring only. Safe. |
| 5 | `.claude/skills/**` glob → enumerate explicitly | Commit 11 now lists `expert-review-loop/SKILL.md` and `project-log/SKILL.md` by name. |
| 6 | `data/perturbed/` is in `.gitignore` but doesn't exist on disk yet | Commit 1's message now states this explicitly. |
| 7 | Verify `.gitkeep` staging interacts cleanly with `!data/internal30/` negation | Added to **Pre-flight** as a `git status` checkpoint. |

## Pre-flight (not a commit; one-time setup)

```bash
cd /Users/lucas/Documents/Projects/devpost/arize_project
git init -b main
```

The repo root is `arize_project/`. Everything under `ma_gatekeeper/` plus top-level strategy markdown files goes in.

**Staging checkpoint after commit 1 is staged but before committing**: run `git status` and confirm `ma_gatekeeper/data/internal30/.gitkeep` is in the index — the existing `ma_gatekeeper/.gitignore` has `!data/internal30/` to keep the dir, and the new root `.gitignore` must not over-ignore it. If the file is absent from `git status`, the negation didn't take and the root `.gitignore` needs adjusting before commit.

## The 11 commits

### Commit 1 — `chore: bootstrap repo skeleton, packaging, and pytest config`

**Why first**: empty scaffolding has zero behavior to defend; lets every following commit be a real feature diff rather than mixed-in housekeeping. Crucially, **also** ships the pytest path config so that the very first commit-with-tests (commit 6) can `pytest tests/` cleanly.

**Files**:
- root `.gitignore` (new — mirrors `ma_gatekeeper/.gitignore` for `.venv/`, `__pycache__/`, `.pytest_cache/`, `data/{cuad,maud,edgar,perturbed}/`, `thresholds.json`, `.phoenix/`, `frontend/node_modules/`, `*.log`, `.DS_Store`; carries the `!data/internal30/` negation forward so the gold-set directory survives)
- `ma_gatekeeper/.gitignore`
- `ma_gatekeeper/.env.example`
- `ma_gatekeeper/requirements.txt`
- `ma_gatekeeper/Dockerfile`
- `ma_gatekeeper/pyproject.toml` (**new** — minimal, only `[tool.pytest.ini_options] pythonpath = ["."]` so `from agent.X` and `from scripts.X` resolve inside `tests/`)
- `ma_gatekeeper/agent/__init__.py` (1-line docstring; verified no heavy SDK imports at import time)
- `ma_gatekeeper/scripts/__init__.py` (**new** — empty marker so `from scripts.calibrate import ...` works in tests; the file does NOT exist on disk today and must be created before staging)
- `ma_gatekeeper/tests/__init__.py`
- `ma_gatekeeper/data/internal30/.gitkeep` (**new** — preserves the gold-set directory)

**Message**:
```
chore: bootstrap repo skeleton, packaging, and pytest config

Adds .gitignore (root + package), .env.example, requirements.txt,
slim non-root Dockerfile (port-aware via $PORT), and empty
agent/ + scripts/ + tests/ packages.

pyproject.toml carries only [tool.pytest.ini_options] pythonpath = ["."]
so tests under ma_gatekeeper/tests/ can `from agent.X import ...`
and `from scripts.X import ...` without an editable install.

data/internal30/ is retained via .gitkeep (it's our gold annotation
set, small enough to commit). CUAD / MAUD / EDGAR corpora are
pulled fresh by scripts/download_datasets.py and stay out of source
control. data/perturbed/ is gitignored even though it doesn't exist
on disk yet — scripts/perturb_contracts.py will create it.
```

---

### Commit 2 — `docs: hackathon brief, Arize strategy, and converged plan v4`

**Why second**: the plan IS the development methodology for this hackathon; everything subsequent implements it. Committing it before the code makes diffs against `plan.md` §§ trivially traceable.

**Files**:
- `Hackathon summary.md`
- `Arize AI Hackathon Strategy.md`
- `plan.md`

**Message**:
```
docs: hackathon brief, Arize strategy, and converged plan v4

plan.md is the v4 artifact after four independent review rounds
(market, architecture/Arize, data, timeline/UX). Final scores:
9/10, 9/10, 9.2/10, 8.5/10. The accompanying strategy and brief
docs are the inputs that fed plan v1.
```

---

### Commit 3 — `feat(schemas): Pydantic models for clauses, findings, and review reports`

**Why third**: every other module imports these types; they're the dependency root of the agent code.

**Files**:
- `ma_gatekeeper/agent/schemas.py`

**Message**:
```
feat(schemas): Pydantic models for clauses, findings, and gatekeeper decisions

Defines the Clause, ClauseTag, RiskFinding, and GatekeeperDecision
BaseModels, plus three Literal type aliases — Tag (8 clause kinds
including change_of_control, anti_assignment, mac, accelerated_vesting),
Severity (info/watch/block), and Lane (auto_clear/escalate/block).

clause_text, cited_spans_text, and pdf_bbox are carried on RiskFinding /
Clause so the Risk Judge can ground its citation in coordinates the
future PDF viewer can highlight (plan §4.3, §6.2). GatekeeperDecision
records the lane + the threshold_applied (min(tau_h, tau_f)) per
finding — that's the model the Router (commit 6) emits.
```

---

### Commit 4 — `feat(phoenix): OpenInference tracing setup and inline evaluator factories`

**Why fourth**: both modules are leaf phoenix-SDK bindings with identical dep profile (phoenix-otel + phoenix.evals) and the same lifecycle (registered/cached once at startup, used by every agent thereafter). Bundling them is the only way to honor the 11-cap without artificially splitting scripts later. Round-A reviewer's atomicity argument is satisfied because the two files are conceptually a single layer ("Phoenix integration").

**Files**:
- `ma_gatekeeper/agent/instrumentation.py`
- `ma_gatekeeper/agent/evaluators.py`

**Message**:
```
feat(phoenix): OpenInference tracing setup and inline evaluator factories

instrumentation.py wraps arize-phoenix-otel register(...) with
set_global_tracer_provider=False so we don't collide with Vertex's
default tracer provider. Includes openinference-instrumentation-
google-adk and openinference-instrumentation-vertexai wiring so
every ADK and Gemini call lands as a Phoenix span without per-call
boilerplate.

evaluators.py exposes two create_classifier wrappers backed by
LLM(provider="vertex", model="gemini-..."): one for explanation
faithfulness against cited spans, one for hallucination. Factories
are @functools.lru_cache(maxsize=1) to avoid re-instantiating the
classifier per request. Both return phoenix.evals Score objects
via clf.evaluate({...})[0] — DO NOT call clf({...}); that shape was
caught fabricated in the round-A code review and would raise at
runtime.
```

---

### Commit 5 — `feat(prompts): fallback prompt templates for parser, classifier, cross-ref, judge`

**Why fifth**: pure strings, no runtime deps. `agents.py` (next) imports these as fallbacks when Phoenix Prompt Store is unreachable.

**Files**:
- `ma_gatekeeper/agent/prompts.py`

**Message**:
```
feat(prompts): fallback prompt templates for parser, classifier, cross-ref, judge

Phoenix Prompt Store is the source of truth at runtime; these are
the in-repo fallback strings the agent uses when the store is
unavailable.

Domain content drafted with the round-A legal reviewer's notes:
- CoC defined via contract phrasing ("majority of voting power",
  "controlling interest", "beneficial ownership", "power to direct
  or cause the direction of management") rather than a "25% threshold"
  tell that betrays non-lawyer authorship.
- MAC carve-out narrowing detection (pandemic, regulatory, industry-wide).
- Accelerated vesting: single vs double-trigger; options/RSUs/PSUs.
- Beneficial vs record ownership distinction.
- Severity rubric expanded into per-lane concrete examples.
```

---

### Commit 6 — `feat(router): independent-gating Router with three Phoenix span annotations`

**Why sixth**: depends only on `schemas` and (transitively, at runtime) the Phoenix client. Bundling code + test in one commit makes the safety invariant ("hallucinated explanation cannot auto-clear at high faithfulness") reviewable atomically.

This is the **first commit that adds tests**. `cd ma_gatekeeper && pytest tests/ -v` must be green here. Confirmed test imports (`from agent.router import Thresholds, judge_and_route`, `from agent.schemas import RiskFinding`) resolve cleanly given commit 1's `pyproject.toml` + `agent/__init__.py` and commit 3's `schemas.py`.

**Files**:
- `ma_gatekeeper/agent/router.py`
- `ma_gatekeeper/tests/test_router.py`

**Message**:
```
feat(router): independent-gating Router with three Phoenix span annotations

Per plan §6.2: the Router is deterministic Python, NOT an LLM, and
gates each finding through hallucination and faithfulness scores
INDEPENDENTLY (not averaged). A hallucinated explanation cannot
auto-clear no matter how high the faithfulness score is; the test
suite encodes this asymmetric-loss invariant directly.

Writes three annotations per span via client.spans.add_span_annotation
(hallucination, clause_faithfulness, risk_judge_gate) — annotations.*
is deprecated as of arize-phoenix-client 1.17.

threshold_applied = min(tau_h, tau_f) for the report payload.
```

---

### Commit 7 — `feat(agents): ADK Parser -> Classifier -> Cross-Ref -> Risk Judge topology`

**Why seventh**: needs schemas + prompts + instrumentation + evaluators. No tests added in this commit — the runner is integration-only (live ADK + Vertex + Files API), which we deliberately do not exercise in unit tests. The 7 router tests from commit 6 still pass.

**Files**:
- `ma_gatekeeper/agent/agents.py`

**Message**:
```
feat(agents): ADK Parser -> Classifier -> Cross-Ref -> Risk Judge topology

SequentialAgent composing four LlmAgent / ParallelAgent stages,
imported from google.adk.agents (NOT google.adk — that import path
was fabricated and caught in round-A review).

Parser uses Gemini 3 Pro on Files-API-uploaded PDFs and stashes
Clause.pdf_bbox at parse time so the D15 frontend sync becomes a
1-day lookup rather than a hidden 2-day extraction job.

Classifier fans out per clause via ParallelAgent on Gemini 3 Flash;
Cross-Ref resolves definitions <-> operative on Gemini 3 Pro; Risk
Judge invokes the inline evaluators (commit 4) and emits the three
span annotations the Router (commit 6) reads.

No new unit tests: this module is exercised by integration tests
against a live ADK runner + Vertex + Files API, which require
credentials and are deferred to operator-side per HANDOFF.md.
```

---

### Commit 8 — `feat(server): FastAPI app with OIDC-protected /reflect, CORS, and upload caps`

**Why eighth**: the HTTP surface; depends on schemas, agents, router, instrumentation. Last commit before the data-plumbing scripts and self-improvement layer.

**Files**:
- `ma_gatekeeper/agent/server.py`

**Message**:
```
feat(server): FastAPI app with OIDC-protected /reflect, CORS, and upload caps

Endpoints: /review (PDF upload), /review-by-deal (EDGAR 8-K Ex 2.1
fetched live), /reflect (Cloud Scheduler cron target), /allow-list.

Security posture per round-A SRE review:
- /reflect verifies a Google OIDC bearer against REFLECT_OIDC_AUDIENCE
  via google.oauth2.id_token.verify_oauth2_token; fails closed (503)
  if DEMO_PASSCODE / audience env not set.
- Demo passcode read from X-Demo-Passcode header only — query-string
  passcodes leak to access logs.
- hmac.compare_digest for the demo-passcode equality check.
- CORS middleware with whitespace-stripped allow-origins list.
- 50MB upload cap: Content-Length pre-check + cumulative cap on the
  chunked read loop.
- SEC fair-use identity set_identity(SEC_USER_AGENT) wired in the
  asynccontextmanager lifespan; /review-by-deal 503s if not ready
  (no silent 403 from SEC on missing User-Agent).
- ADK runner shape verified against googleapis/python-genai main:
  InMemoryRunner(agent=root, app_name=...).run_async(user_id=...,
  session_id=..., new_message=Content(parts=[Part.from_bytes(
  data=..., mime_type="application/pdf")])).
```

---

### Commit 9 — `feat(scripts): EDGAR/CUAD/MAUD downloaders and adversarial perturbation`

**Why ninth (split from old commit 10 per round-A finding #3)**: these scripts are pure data plumbing — `download_datasets.py` pulls corpora; `perturb_contracts.py` builds the adversarial slice and runs a leakage AUC audit (must be <0.6 to ship per plan §5.3). Neither imports the reflector or the calibrator. Atomic separation makes them reviewable on their own, and the calibrator (next commit) explicitly depends on the outputs of both, so the order is forced.

**Files**:
- `ma_gatekeeper/scripts/download_datasets.py`
- `ma_gatekeeper/scripts/perturb_contracts.py`

**Message**:
```
feat(scripts): EDGAR/CUAD/MAUD downloaders and adversarial perturbation

download_datasets.py pulls CUAD (Atticus, CC-BY-4.0), MAUD (Atticus,
CC-BY-4.0), and a small EDGAR 8-K Ex 2.1 sample via EdgarTools using
$SEC_EDGAR_USER_AGENT identity. Writes under data/{cuad,maud,edgar}/,
all gitignored.

perturb_contracts.py builds the adversarial slice (synonym swaps,
clause reordering, definition shadowing) and runs a leakage AUC audit
on the perturbations vs. originals. Slice ships only if AUC < 0.6 per
plan §5.3 — anything higher means the perturbations are leaking the
clause identity through surface form, and the eval would inflate.
Output lands under data/perturbed/ (created by this script; gitignored).
```

---

### Commit 10 — `feat(reflector+calibration): nightly self-improvement loop + 5-fold CV + tests`

**Why tenth**: bundles the reflector with its tightly-coupled calibration script and the three test files that exercise its math. `reflector.py` ↔ `test_promotion_rule.py` (promotion CI gate); `scripts/calibrate.py` ↔ `test_stats.py` + `test_fold_split.py` (Wilson + cluster bootstrap + deterministic fold assignment). The scripts in commit 9 are inputs to this calibration; this commit is where they pay off.

**Files**:
- `ma_gatekeeper/agent/reflector.py`
- `ma_gatekeeper/scripts/calibrate.py`
- `ma_gatekeeper/tests/test_fold_split.py`
- `ma_gatekeeper/tests/test_promotion_rule.py`
- `ma_gatekeeper/tests/test_stats.py`

**Message**:
```
feat(reflector+calibration): nightly self-improvement loop + 5-fold CV + tests

Reflector (plan §6.3):
- Phoenix MCPToolset via StdioServerParameters(command="npx",
  args=["-y", "@arizeai/phoenix-mcp@latest", ...]) and an LlmAgent
  introspection step wired as step 0 of run_reflection_cycle.
- list-traces filter cascades over 3 column-name variants of
  risk_judge_gate.label == "escalate" (Phoenix schema drift defense).
- Two-experiment promotion gate: regression set + frozen fold-5
  non-regression; promote ONLY if paired-bootstrap CI lower bound > 0
  AND fold-5 delta within epsilon = max(SE_fold5, 0.03).
- Code-enforced allowlist refuses Reflector writes to fold 5.

Calibration script (plan §5.4):
- 5-fold CV, fold 5 reserved as frozen held-out.
- One-sided 95% Wilson LB (z = 1.6449, NOT 1.96).
- Cluster bootstrap over contracts (each contract resampled with its
  full hit-vector) — parametric Binomial bootstrap ignores within-
  contract correlation and was caught in round-A stats review.
- Reliability diagrams binned over the FULL pool against is_block
  ground truth, not the test-fold subset.

Tests: 23 of the 31 total tests live here; the other 7 are
test_router from commit 6. All pure-Python with synthetic dataframes
and fixed seeds; no live API calls. Includes the asymmetric-loss
test that fails if a hallucinated explanation can auto-clear at
0.95+ faithfulness — the entire safety promise of the system in
one assertion.
```

---

### Commit 11 — `docs: README, HANDOFF, PROJECT_LOG, and extracted Claude skills`

**Why last**: README cross-references the converged-and-implemented system; HANDOFF lists what the human operator still has to do; PROJECT_LOG is the audit trail covering all prior commits; the two Claude skills were the abstractions extracted from this very process. None makes sense to commit before the code they describe exists.

**Files**:
- `ma_gatekeeper/README.md`
- `ma_gatekeeper/HANDOFF.md`
- `PROJECT_LOG.md`
- `.claude/skills/expert-review-loop/SKILL.md`
- `.claude/skills/project-log/SKILL.md`

**Message**:
```
docs: README, HANDOFF, PROJECT_LOG, and extracted Claude skills

README: architecture, seven Arize hooks, repository layout, quickstart,
demo-scope paragraph required by Devpost, eval headline framing, and
the explicit Reflector pre-seeding disclosure.

HANDOFF: things only Hugo can do (GCP project, billing, Phoenix
self-host on Cloud Run, Vertex quota, EDGAR identity, demo passcode
in Secret Manager, 30-contract annotation, demo recording, Devpost
submission). Ordered by plan §7 timeline day.

PROJECT_LOG: append-only audit of the planning phase (4 review rounds),
scaffolding phase, and 4 rounds of expert code review that ended with
all 5 reviewers (legal, Python/ADK, Arize, ML stats, SRE) validated.

.claude/skills/expert-review-loop/SKILL.md and
.claude/skills/project-log/SKILL.md are the two reusable Claude
skills extracted from this project's process: the multi-expert
convergence pattern and the structure of PROJECT_LOG.md itself.
```

## What I deliberately did NOT do

- **No `git tag v0.1.0`**: initial history laydown, not a release.
- **No `git push`**: per CLAUDE.md, the user runs pushes themselves.
- **No squash of round-A/B/C/D rewrite history into per-file v1/v2/v3/v4 commits**: the iterations happened in a workspace, not in git; committing the final validated state in one shot per module is honest about that. The narrative lives in `PROJECT_LOG.md`.
- **No frontend/, evals/, docs/ empty-directory commits**: they exist as placeholders for D15+ work per HANDOFF.md; empty dirs aren't tracked by git, and the placeholder is documented in plan + HANDOFF.
- **No CI/CD config**: round-A reviewer flagged a (more important) `pyproject.toml`/`pytest.ini` gap; a full CI setup is out of scope for initial laydown and gets added when the operator wires Cloud Build.
- **`COMMIT_PLAN.md` (this file) is intentionally NOT committed**. It is a transient planning artifact for the initial laydown only; its purpose ends the moment commit 11 lands. The durable narrative — what was built, what each module is, why the structure is what it is — lives in `PROJECT_LOG.md` (committed in 11) and in the commit messages themselves. After the laydown, the user can keep this file locally as a reference or delete it; either way it should NOT appear in `git log`. Expect it to show as untracked in `git status` after commit 11 — that is the intended end state.
