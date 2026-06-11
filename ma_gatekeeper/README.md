# Cautela — M&A Due Diligence

An auditable AI agent for M&A contract review, built for the Google Cloud
Rapid Agent Hackathon — Arize partner track. Submission deadline:
**June 11, 2026**.

The agent reads merger agreements and the underlying data-room contracts,
flags change-of-control / anti-assignment / MAC / accelerated-vesting
clauses, and routes each finding into one of three lanes (**Auto-Clear**,
**Escalate to Lawyer**, **Block**). Every decision is traced and judged
in [Arize Phoenix](https://arize.com/phoenix/), with a nightly Reflector
agent that grows a regression dataset and runs paired-bootstrap
experiments to auto-promote improved prompts — gated by a non-regression
check on a frozen held-out fold.

The thesis is **not** "AI does M&A review faster." It is
**"AI does M&A review with an audit trail the judge can click into."**

See [`plan.md`](../plan.md) for the full architecture, calibration
protocol, and 3-week timeline. The plan went through 4 independent
review rounds with final scores 9/10 (market, architecture), 9.2/10
(data strategy), 8.5/10 (timeline).

## Architecture (plan §4.2)

The six-stage review pipeline runs end-to-end on **Gemini 3.5 Flash**
(GA), pinned via `GEMINI_FLASH_MODEL` — it carries the structured
extract/classify/judge work at the accuracy the eval rail demands
(held-out Block-recall 1.0) for roughly an order of magnitude less than
the Pro preview, whose large-context pricing on a ~150K-token merger
agreement made per-review cost untenable. **Gemini 3.1 Pro**
(`GEMINI_MODEL`) is reserved for the two stages whose 1M-context
reasoning pays for itself: the Portfolio Analyst and the Reflector.
Every stage reads its model from env, so any deployment can dial a stage
up to Pro without touching code.

```
PDF / HTML upload  (Cloud Run FastAPI handler)
   v
Parser           (Gemini 3.5 Flash, populates pdf_bbox)
   v
Classifier       (ParallelAgent, Gemini 3.5 Flash fan-out)
   v
CrossReference   (Gemini 3.5 Flash, resolves definitions <-> operative)
   v
RiskJudge        (Gemini 3.5 Flash + inline phoenix.evals + span annotation)
   v
Router           (deterministic Python, NOT an LLM)
   v
Reporter         (Jinja2 template, NOT an LLM)

Portfolio Analyst (separate agent, Gemini 3.1 Pro):
  one ~800k-token call across all 30 demo contracts -> cross-deal
  cluster taxonomy (MAC templates, outlier deal, representative clause)

Reflector (separate Cloud Scheduler cron, Gemini 3.1 Pro):
  list-traces -> add-dataset-examples -> upsert-prompt -> two experiments
  (regression set + frozen fold-5) -> auto-promote ONLY if both gates pass
```

## Ten Arize hooks (plan §6.1)

1. OpenInference tracing of every ADK call (`openinference-instrumentation-google-adk`).
2. Inline `phoenix.evals.create_classifier` for hallucination + faithfulness.
3. Programmatic span annotations via `arize-phoenix-client`.
4. Phoenix MCP introspection by the Reflector (`list-traces`, `get-trace`, ...).
5. Auto-growing regression dataset via MCP `add-dataset-examples`.
6. Prompt versioning + experiment-gated promotion (paired bootstrap CI + frozen fold non-regression).
7. Hook 7: scheduled batch `run_evals` collapsed into the Reflector nightly cron — equivalent batch coverage to Arize AX Online Eval Tasks (which are SaaS-only).
8. Citation eval against a **deliberately-divergent** gold set (`citation-gold-v1`): two SEPARATELY-reported numbers — the deterministic map's *coverage, by construction* (recall@1 + a contains-anywhere coverage number, whose gap is the honest single-best-answer `candidates[0]` story) and the LLM proposer's *graded* recall — plus their agreement, which is **not** accuracy and is **not** summed. The gold is LLM-counsel-curated (the same M&A-counsel persona as the map, **not** a second human annotator); its independence comes from off-map rows whose controlling authority sits outside the map's tag/jurisdiction universe, so the map can **miss for a real reason**. Run mode (`mock`/`live`) is stamped in the eval JSON; mock proposer numbers render with a literal "MOCK" tag. Audit trail: `data/CITATION_GOLD_SIGNOFF.md`.
9. Per-call `citation_linker_agreement` span annotation written post-hoc from the fire-and-forget proposer — a genuine streaming-eval signal (not batch-collapsed).
10. Deterministic regex comparator (`citation_exact_match`) surfaced as a Phoenix `create_classifier` rail for grader uniformity — NOT an LLM judge.

## Repository layout

```
ma_gatekeeper/
  agent/
    schemas.py           # Pydantic models (plan §4.3) + the 8-value Tag enum (source of truth)
    instrumentation.py   # phoenix.otel.register (HTTP-OTLP /v1/traces, set_global_tracer_provider=False)
    evaluators.py        # hallucination + faithfulness create_classifier wrappers
    router.py            # deterministic independent gating (plan §6.2) + span annotation writer
    agents.py            # ADK Sequential/Parallel topology (review pipeline on GEMINI_FLASH_MODEL)
    portfolio_analyst.py # 5th agent: one ~800k-token Gemini 3.1 Pro pass over all 30 deals
    reflector.py         # nightly self-improvement loop (plan §6.3) + Phoenix MCP introspection
    reflector_loop.py    # demo-facing observe->propose->experiment->gate->promote loop
    citation_linker.py   # deterministic primary-source citation map + internal LLM proposer
    pdf_bbox.py          # bounding-box extraction for span pins
    allow_list.py        # curated 5-deal demo registry (ticker, EDGAR ex-2.1 URL)
    prompts.py           # fallback prompt templates (Phoenix is source of truth)
    server.py            # FastAPI: /review, /review-by-deal, /filing, /portfolio,
                         #          /reflect, /reflect/loop, /allow-list, /healthz
  frontend/              # Next.js 14 + Tailwind UI (see "Frontend" below)
  scripts/
    download_datasets.py     # CUAD + MAUD + EDGAR pull
    fetch_internal30.py      # pull the Internal-30 cohort filings
    build_internal30_gold.py # multi-agent Pass A/B cohort gold builder
    judge_internal30.py      # D8 -> calibration bridge (--live grades each finding)
    annotate.py / make_kappa_template.py  # pre-label JSONL + Cohen's kappa
    calibrate.py             # 5-fold CV grid search + reliability diagrams
    eval_maud_mcq.py / eval_cuad_spans.py / eval_citation_gold.py  # public + gold benchmarks
    build_readme_table.py    # regenerates the results table between the HTML markers
    perturb_contracts.py     # adversarial slice + TF-IDF/LogReg leakage AUC audit (<0.6 to ship)
    seed_reflector.py / seed_reflector_datasets.py  # D18 pre-seed + Phoenix dataset seeding
    render_climax_plots.py   # demo reliability/promotion plots
    confirm_selfimprove_promotes.py  # asserts the self-improve loop actually promotes
  tests/                 # 571 pure-Python unit tests; no live API calls (see "Tests")
  Dockerfile
  requirements.txt
  .env.example
  README.md
  HANDOFF.md             # things only the human can do
```

## Local quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # fill in PHOENIX_* and Google Cloud values

# Download datasets (CUAD, MAUD, EDGAR samples)
python -m scripts.download_datasets --out data/

# Run the FastAPI server locally
uvicorn agent.server:app --reload --port 8080
```

## Frontend (`frontend/`)

A **Next.js 14 + Tailwind** app served on Cloud Run as `cautela-frontend`.
The `/review` page is a three-pane workspace: the document exhibit (left),
the streaming findings pane (middle), and the trace / "in plain English"
pane (right). Selecting a deal **auto-starts** the review; findings stream
in over SSE and appear as the Risk Judge emits them.

- **Document pane** (`components/pdf-pane.tsx`) — react-pdf for PDFs; for
  the HTML EDGAR exhibits the demo deals actually ship, it renders the
  filing in a `sandbox="allow-scripts"` (opaque-origin, **no**
  `allow-same-origin`) blob iframe and splices in a postMessage
  highlighter that draws span-level bands on the cited clause when a
  finding is selected.
- **Phoenix board** (`components/phoenix-board.tsx`, `lib/phoenix.ts`) —
  embeds the self-hosted Phoenix project and deep-links each finding to
  its span tree through a same-origin `/phoenix-api/*` proxy; the project
  id is resolved by name at runtime.
- **Portfolio pane** (`components/portfolio-pane.tsx`) — surfaces the
  cross-deal cluster taxonomy from the Portfolio Analyst.
- **Self-improvement panel** (`components/reflector-loop-button.tsx`) —
  triggers the Reflector loop and shows AUTO-PROMOTED / NO PROMOTION
  outcome badges with the CI-LB and Δ/ε from the experiment.

Frontend type-safety against the Python schemas is pinned by
`tests/test_frontend_type_sync.py` (and `test_tag_sync.py` for the clause-
tag union).

## Deployment

Self-hosted on Google Cloud Run (`test-ec90e`), scales to zero off-demo:

- **Backend** — `ma-gatekeeper` (FastAPI). Deploy with
  `gcloud run deploy ma-gatekeeper --source . --region=us-central1`
  (no env flags preserves baked env + secrets).
- **Frontend** — `cautela-frontend` (Next.js, Cloud Build).
- **Phoenix** — self-hosted on Cloud Run, OpenInference tracing over
  HTTP-OTLP (`/v1/traces` — Cloud Run can't receive the gRPC:4317 default).
- **Reflector** — Cloud Scheduler cron hitting `/reflect` (OIDC-gated).

A live `/review-by-deal` on `microsoft_activision` streams four real
findings (change-of-control, anti-assignment, MAC carve-out, accelerated
vesting) and lands a full trace tree in the Phoenix `ma-gatekeeper`
project.

## Tests

**571 pure-Python unit tests** with fixed seeds and zero live API calls.
Run:

```bash
.venv/bin/python -m pytest tests/ -v
```

Current status: **570 pass / 1 fail**, where the only failure is
`test_env_documented` (`.env.example` is missing two non-secret
Reflector knobs — `GEMINI_FLASH_MODEL` and `GEMINI_MIN_CALL_INTERVAL_SEC`
— a cosmetic one-line operator fix; the file is house-rule off-limits to
the agent). Coverage now spans the eval rail (`test_eval_maud_mcq`,
`test_eval_cuad_spans`, `test_eval_citation_gold`), the Internal-30 gold
builder, the SSE review stream (`test_server_stream`), the PDF/HTML proxy
and bbox layers, the Portfolio Analyst, the citation linker + freshness
gate, the demo-facing reflector loop, and the frontend type-sync guard.

The fold-split tests are the explicit D9-morning unit test (plan §7 v3)
catching off-by-one + leak-via-shared-state bugs. The promotion-rule
tests verify bootstrap CI math, epsilon floor (0.03), and the
code-enforced allowlist that prevents the Reflector from writing to the
frozen held-out fold. The calibration-invariants tests (see next
section) pin the headline-number math against silent regression.

## Calibration invariants (`tests/test_calibration_invariants.py`)

`scripts/calibrate.py` produces the headline Block-recall number plus
its one-sided 95% Wilson and cluster-bootstrap lower bounds. The
following five **quiet-downgrade vectors** would silently soften that
number if a future commit reverted them; each has at least one pinned
test:

1. **Wilson LB by-(k, n) pinned values** — the `WILSON_PINS` table
   pins one-sided 95% LB for six `(k, n)` pairs to 5 decimals. A revert
   to two-sided z=1.96 fails every row with a calibrated >0.030 margin.
2. **Cluster-bootstrap alpha recovered-quantile** — pins
   `cluster_bootstrap_recall_ci` to return the empirical 5th percentile
   of the resample distribution (NOT the 2.5th or 95th). A revert to
   `np.quantile(means, alpha/2)` fails by >0.020 on a 40-contract fixture.
3. **`require_recall=1.0` parameter** — pins the default of
   `calibrate_fold(require_recall=...)` to 1.0; verifies the function
   returns `None` (not a softened fallback) when no grid point achieves
   recall=1.0.
4. **`plot_reliability` content** — intercepts matplotlib `ax.bar` /
   `ax.plot` calls (no brittle golden-image diff) and pins per-bin
   empirical positive rates over the FULL pool. A revert to the
   block-only-subset bug pattern collapses every populated bin to 1.0
   and trips this assertion.
5. **Dropped-fold disclosure** — when a headline fold can't be
   calibrated, the calibrator now surfaces it via two summary fields:
   - `headline_folds_present` — folds that contributed to the headline.
   - `dropped_headline_folds` — folds that were skipped.

   `calibrate_all_headline_folds` (extracted from `main()`) is unit-testable
   without IO. A silent `continue` without populating `dropped_headline_folds`
   would fail the coverage invariant `len(per_fold) + len(dropped) == 4`
   asserted in two tests.

**To add a new headline-defending invariant**: add a test to this file
following the existing section banners. The test must mutate the
function under test (manually, locally) and confirm the test FAILS;
revert; commit only the test. See `PROJECT_LOG.md` Phase-5 for the
two-builder-plus-three-reviewer convergence pattern that produced this
file.

## Infrastructure recovery

Two long-running failure modes the spine guards against:

### Files API URI expiry (`agent/server.py:_cache_get_live`)

Gemini's Files API auto-expires uploaded file URIs after 48 hours on
Google's side. A long-lived Cloud Run instance that uploads on hour 0
would otherwise serve a dead URI on hour 49 — Gemini's
`generate_content` call would 404 on `Part.from_uri`. The cache value
shape is `tuple[uri, inserted_at_monotonic]`; entries are evicted at
`FILES_API_URI_TTL_SECONDS` (default 36 h, env-overridable). Eviction
is monotonic-clock-based so an NTP correction during a Cloud Run cold
start can't falsely extend or shorten a live entry. Pinned by 5 tests
in `tests/test_files_api.py`.

### MCP subprocess shutdown drain (`agent/reflector.py`)

The Reflector's introspection agent spawns an `npx
@arizeai/phoenix-mcp` child process per cycle. Per-call `try/finally`
in `_run_introspection_agent_async` aclose()s the toolset on every
exit — that's the fast path. The shutdown drain is the safety net for
"process dies between MCPToolset construction and the finally":
SIGTERM during a `/reflect` cycle, uncaught exception in the executor
thread, FastAPI lifespan teardown mid-call.

- Strong-set + `threading.Lock` registry — the same toolset may be
  built from multiple worker threads (Cloud Run worker pool + manual
  `/reflect` + CLI cron); `asyncio.Lock` is the wrong primitive.
- `_aclose_one_with_timeout` wraps each close in `asyncio.wait_for`
  with `MCP_ACLOSE_TIMEOUT_SECONDS` (default 5 s) — Cloud Run's
  SIGTERM-to-SIGKILL grace is 10 s, we leave headroom.
- `_MCP_CLOSED_ATTR` sentinel guarantees per-call finally + lifespan
  drain are idempotent (both can fire; only the first does real work).
- `atexit` hook handles the non-FastAPI invocation path (`python -m
  agent.reflector` cron).

Pinned by 9 tests in `tests/test_introspection_agent.py`.

## Tag sync points

The 8-value clause-tag enum has ONE source of truth and three derived
or hand-mirrored consumers:

- **Truth**: `agent/schemas.py:Tag` (Literal of 8 values incl. `"none"`).
  `ALL_TAGS` and `CLASSIFIER_TAGS = ALL_TAGS - {"none"}` are derived
  here via `typing.get_args`.
- **Re-export**: `agent/agents.py` imports `CLASSIFIER_TAGS` for the
  ParallelAgent fan-out. No duplicate list.
- **Re-export**: `scripts/annotate.py` imports `CLASSIFIER_TAGS` as
  `PRELABEL_TAGS`; `PRELABEL_INSTRUCTION` f-strings the list so Gemini
  always sees the current set.
- **Hand-mirror**: `frontend/lib/types.ts:Tag` union. Drift is caught
  by `tests/test_tag_sync.py:test_frontend_ts_tag_union_matches_python`
  (regex cross-check; no codegen).

**To add a new clause tag**, touch exactly two files:
1. Append the literal to `agent/schemas.py:Tag`.
2. Append the same string to `frontend/lib/types.ts:Tag`.

Then run `pytest tests/test_tag_sync.py` to confirm.

Also consider whether the new tag deserves its own bespoke
clause-family block in `agent/prompts.py:CROSS_REFERENCE_PROMPT` (the
first four tags get one; the others don't — that's a deliberate legal-
specificity choice, not an oversight). The D18 seed regex in
`scripts/seed_reflector.py` is pinned to exactly four blocks and is
guarded by `test_tag_sync.py:test_cross_reference_prompt_has_four_clause_family_headings`.

## Demo scope (plan §5.5)

The hosted demo presents a curated dropdown of **5 pre-indexed deals**,
not an open ticker box. Each is pre-vetted to surface at least one
Block-tier finding so the demo cannot land on an "all clear"
anticlimax. Each deal's actual 8-K Exhibit 2.1 is fetched live from SEC
EDGAR at demo time — a direct request to the filing's public EDGAR
archive URL, so the agent reviews the real document, not a repo copy.
(The `edgartools` library registers the required SEC identity at startup
and backs the fallback fetch for any not-yet-pinned deal.)

**Demo Scope paragraph** (required in the Devpost description):

> The hosted demo runs against a curated, pre-indexed set of five recent
> 8-K/Ex 2.1 merger filings, pre-validated to surface at least one
> change-of-control, anti-assignment, or MAC-related finding so the
> agent has something interesting to do on camera. The filings are
> fetched live from SEC EDGAR at demo time.

## Eval headline (plan §5.4 v4)

Reported on **24 contracts (4 folds × 6)**; fold 5 (6 more contracts)
is reserved as the Reflector's frozen non-regression set and is never
used for the headline number.

> Held-out Block recall = R, cluster-bootstrap 95% LB = R_lo (headline,
> contracts as IID unit), at abstention = Y%; Wilson 95% LB = R_lo_iid
> reported as a secondary exploratory per-finding-IID cross-check;
> per-evaluator thresholds (τ_h, τ_f), 4-fold CV on Internal-30.

**Judge design — high-precision flagging.** Each finding is graded against
its cited clause by two inline judges (`agent/evaluators.py`). The
hallucination judge scores the *operative claim* — what the explanation says
the clause itself says or does — and treats standard legal-doctrine framing
(Revlon, Omnicare, MAC, fiduciary-out…), market-customary benchmarks, and
risk-direction judgments as expert work-product rather than fabrication; it
returns `hallucinated` only on a direct contradiction with the clause or
invented clause content. The faithfulness judge grades the explanation
against the clause text **and** the trigger language, returning `unfaithful`
only on contradiction. Both are deliberately conservative about *raising* a
defect, so every flag is trustworthy: when a judge objects, there is a
concrete, identifiable problem (verified on the 530-row lawyer+analyst gold,
where the judges still flag genuine over-reach rather than rubber-stamping).

Because the judges flag conservatively, the routing gate (τ_h, τ_f) is
permissive by construction; the headline Block-recall is therefore reported
**with** its cluster-bootstrap 95% lower bound, not as a point estimate
alone. The deployed τ_f is pinned by the lowest-scoring Block finding
(f=0.50), which is the binding constraint on recall.

<!-- BEGIN_RESULTS_TABLE -->
| Track | Metric | Value | Notes |
|---|---|---|---|
| Internal-30 | Block recall (point estimate) | 1.000 | Pooled across 4 headline fold(s); frozen fold 5 excluded. |
| Internal-30 | Block recall (cluster bootstrap 95% LB, one-sided) | 1.000 | Load-bearing number per plan §0 + §5.4 v3 — published unmodified. Cluster bootstrap over contracts (1000 resamples) — findings within a contract are correlated, so contracts are the IID unit. |
| Internal-30 | Block recall (Wilson 95% LB — exploratory, per-finding IID) | 0.942 | Exploratory cross-check only — assumes findings are IID Bernoulli trials, which they are not (findings within a contract are correlated). Over-tight as a cluster-corrected estimate; the cluster bootstrap row above is the headline. |
| Internal-30 | Effective N (contracts) | 12 | Per plan §5.2 v3 — fold 5 (Reflector frozen set) excluded. |
| Internal-30 | Deployed thresholds | τ_h=0.99, τ_f=0.50 | Median across headline folds; written to router config. |
| MAUD-MCQ | Exact-match accuracy (macro) | 99.8% | Per-category mean (plan §5.2). |
| MAUD-MCQ | Exact-match accuracy (micro) | 99.7% | Pooled over all evaluated questions. |
| MAUD-MCQ | Degenerate per-question AUPR (paper-comparable, see caveat) | 0.562 | degenerate (single confidence, not per-choice probs) |
| MAUD-MCQ | N evaluated / N total | 300 / 624 | Skipped rows tallied in `n_skipped_with_reason`. |
| CUAD-Spans | Token-F1 (project, macro, strict >0.5) | 0.380 | Plan §5.2 strict-Jaccard variant; CoC + Anti-Assignment only. |
| CUAD-Spans | Token-F1 (paper-comparable, macro, ≥0.5 + punct-strip) | 0.413 | CUAD §3 paper variant (≥0.5 Jaccard, punctuation-stripped). |
| CUAD-Spans | AUPR (overall) | 0.654 | CUAD paper primary metric (§3). |
| CUAD-Spans | P@R=0.8 | — | **FALLBACK** — flag=`recall_0.8_unachieved` (max achieved recall = 0.374). Number shown is NOT the achieved precision at target recall. |
| CUAD-Spans | P@R=0.9 | — | **FALLBACK** — flag=`recall_0.9_unachieved` (max achieved recall = 0.374). Number shown is NOT the achieved precision at target recall. |
| Citation-Gold | Map coverage (by construction) | 100.0% (40/40) | coverage, by construction — primary-source-verified, not earned accuracy |
| Citation-Gold | Map recall@1 (single best answer) | 70.0% (28/40) | single-best-answer (recall@1). 12 in-map row(s) where the gold authority IS in the map for the tag but is not the canonical first entry (e.g. § 271 asset-sale vs § 251 merger) — the candidates[0] gap, reported not hidden. 4 case-law row(s) matched via caption-only normalisation. |
| Citation-Gold | LLM-proposer recall (graded) | 70.0% (Wilson 95% LB 0.571) | MOCK — deterministic stub, not the live model. Mirrors the map by construction, so this is a reproducibility stub — only `--live` yields a real proposer signal. |
| Citation-Gold | Proposer-vs-map agreement | 100.0% | map = coverage (recall@1); proposer = accuracy; agreement ≠ accuracy — not summed |
| Citation-Gold | Off-map rows correctly missed (de-circularization) | 5/5 | Rows whose controlling authority is outside the map's universe by construction; the map returns None or a different authority — proof the map can MISS for a real reason. |
| Citation-Gold | Run mode | mock | `mock` = deterministic stub (zero quota); `live` = real Vertex proposer. The JSON always carries this field. |

_Pre-commitment (plan §0 + §5.4 v3): the cluster-bootstrap 95% LB on Block recall is the load-bearing headline number and is published unmodified regardless of whether it clears 0.95. With ~6–10 Block findings per fold, the 95% CI for a proportion near 1.0 spans roughly ±0.10–0.15; the LB clearing 0.95 is **arithmetically tight, not a guarantee**. The Wilson row is retained as an exploratory per-finding-IID cross-check only._
<!-- END_RESULTS_TABLE -->

> **Internal-30 gold-set provenance (honest disclosure).** The Internal-30
> gold labels were **pre-labeled by two independent automated annotation
> cohorts** (Pass A recall-first, Pass B precision-first — each a fan-out of
> seven per-clause-family specialist agents plus a reconciler) and reconciled
> by a third adjudication cohort. The reported **Cohen's κ = 0.8783 measures
> agreement between the two automated passes** (a reproducibility check), **not
> human inter-annotator reliability**, and is expected to run high — two strong
> models agree easily, so it is reported as procedural inoculation, not as
> evidence of label quality. The gold labels were then **validated in depth by
> two M&A practitioners — a practicing lawyer and an M&A analyst**, who are the
> **annotators of record**. Label quality rests on that human validation pass
> and on the public-benchmark results (MAUD / CUAD), which use independent
> expert gold — never on κ.

> **CUAD-Spans methodology (honest disclosure).** Scope: **2 of CUAD's 41
> clause types** (Change-of-Control + Anti-Assignment); **n = 150
> (contract, clause-type) pairs over 75 contracts**, evaluated on the **`test`
> split only** (earlier numbers that pooled train+test were contaminated and
> are not reported). The model is prompted with the **canonical CUAD-QA
> question including its `Details:` clause definition** — the same input the
> published baselines receive — so the comparison is faithful, not handicapped.
> This is a **single-pass** zero-shot LLM over the full contract: we also built
> and measured chunked-window + recall-sweep extraction, but on a same-sample
> A/B it did **not** beat single-pass (it traded precision for recall), so
> single-pass is the reported configuration. These numbers are **CUAD-derived,
> our protocol** — a zero-shot generative model over whole contracts, not the
> fine-tuned paragraph-span models of the CUAD paper — so they are not a
> leaderboard-equivalent comparison. Where P@R=0.8/0.9 is unachievable
> (max recall ≈ 0.37), we report the `recall_unachieved` flag, never a
> substituted precision.

**Expected CI width**: with ~6–10 Block findings per fold, the 95%
Wilson CI for a proportion near 1.0 spans roughly ±0.10–0.15. The LB
clearing 0.95 is **arithmetically tight, not a guarantee**; we publish
R and R_lo unmodified regardless.

## Reflector loop pre-seeding (plan §6.4)

The "production" prompt was deliberately seeded weaker 48 hours before
demo recording so the auto-improvement loop has a real signal to find.
The loop logic itself — paired-bootstrap CI, frozen-fold non-regression,
auto-promotion — is unchanged. Honest engineering of reproducibility,
not staging.

## Attributions

- [CUAD](https://www.atticusprojectai.org/cuad) — Hendrycks et al., 2021, CC-BY-4.0
- [MAUD](https://www.atticusprojectai.org/maud/) — Wang et al., EMNLP 2023, CC-BY-4.0
- [EdgarTools](https://github.com/dgunning/edgartools) — Dwight Gunning, MIT
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — Arize AI, Apache 2.0

## License

Apache 2.0. See `LICENSE`.
