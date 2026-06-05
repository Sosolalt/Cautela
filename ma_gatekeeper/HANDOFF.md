# HANDOFF — items requiring you (Hugo)

The plan is converged. The codebase has gone through 3 phases of
scaffolding + multi-reviewer audit + Phase 5 fix-loop on 10 prioritized
Tier-1 issues — **151/151 unit tests pass**, and the end-to-end demo
path (deal pick → SSE stream → trace cmd+click) works on the code side.
The remaining work falls into items I cannot do for you (credentials,
billing, physical recording, live SEC verification) and items deferred
to you by design (UX redesign you're owning separately).

This file is the explicit operator-side list. Items are ordered by the
day they appear in the plan timeline (`plan.md` §7). Each section also
notes when a Phase 4/5 artifact has shipped to support it (so you can
skim "✅" lines as already-done).

## Before D1 (today)

- [ ] Create a Google Cloud project named `ma-gatekeeper-prod` (or
      similar).
- [ ] Set billing on the project (the $300 free-trial credit handles the
      whole hackathon trivially per the GCAB research, but billing must
      be enabled to deploy to Cloud Run).
- [ ] Enable APIs: Vertex AI, Cloud Run, Artifact Registry, Secret
      Manager, Cloud Scheduler.
- [ ] Pick a hosting domain (e.g. `ma-gatekeeper.com`) or use Cloud Run
      default URLs. The "we own the URL" demo story needs a real
      subdomain only if you want it.
- [ ] Devpost account exists; verify the **payment-eligibility profile
      is complete** (W-9/W-8BEN-equivalent) so a $5K win can actually
      be paid — easy to forget and a real failure mode.
- [ ] Decide on a public-passcode for the demo and put it in Secret
      Manager as `demo-passcode`.

## D1–D2 (Phoenix infra)

- [ ] Follow the Pro-Level Agent Observability guide to deploy Phoenix
      self-hosted on Cloud Run:
      https://medium.com/google-cloud/pro-level-agent-observability-deploying-arize-phoenix-on-google-cloud-f07a1576b578
- [ ] Reverse-proxy Phoenix through `phoenix.your-domain.com`. If the
      iframe embed is ugly (validation step on D1), pivot to the
      custom trace-card backup component.
- [ ] Generate a Phoenix API key, put it in Secret Manager as
      `phoenix-api-key`.
- [ ] Save `PHOENIX_COLLECTOR_ENDPOINT` and `PHOENIX_PROJECT` for env-var
      injection at Cloud Run deploy time.

## D3 (ADK quota)

- [ ] **Request a Vertex AI Gemini 3 Pro quota bump** — the default
      QPS limits will 429 a multi-pane demo. This requires a console
      ticket and 24-48h turnaround; don't leave it for D19.

## D4 (Parser)

✅ **Code shipped** (`agent/agents.py` Parser stage; `Clause.pdf_bbox`
field on `agent/schemas.py`). No operator action required for the
parser code itself.

- [ ] Once Vertex quota lands (D3) + Phoenix is reachable (D1-D2),
      sanity-check the live `/review` path on one MAUD PDF end-to-end
      and confirm clauses + `pdf_bbox` come back populated. If
      `pdf_bbox` is consistently null, that's the moment to wire
      Document AI Layout Parser as the fallback noted in plan §3.1
      — don't wait for D15.

## D5–D9 (annotation + three-track eval)

✅ **Annotation pipeline shipped** (`scripts/annotate.py`): Gemini pre-labels →
Argilla SpanQuestion JSONL + Cohen's κ. Includes a no-op + char-offset
invariant guard so a misconfigured run fails loud instead of silently
producing identical files.

✅ **Three-track eval shipped (Phase 6.6, 2026-05-27)** — plan §5.2 + §12's
"three-track eval results table" is now tooled in full:
  - `scripts/eval_maud_mcq.py` (38 tests) — exact-match accuracy per
    category + degenerate AUPR; HF schema adapter for `theatticusproject/maud`;
    `--baselines path/to/baselines.json` for paper-comparison rows.
  - `scripts/eval_cuad_spans.py` (54 tests) — token-F1 (project strict `>0.5`
    + paper-comparable `>=0.5` + punctuation-strip both surfaced),
    AUPR (sklearn average_precision_score), P@R=0.8 + P@R=0.9; SQuAD adapter
    for `theatticusproject/cuad-qa`.
  - `scripts/calibrate.py` v5 (existing) — Internal-30 5-fold-CV Block-recall.
  Default `--use-mock` deterministic mock; `--live` raises
  `NotImplementedError` deliberately — wiring the live ADK Runner is the D9
  operator task below.

- [ ] Sign up for Argilla on a Hugging Face Space (free).
- [ ] Run the pre-label pass:
      ```
      cd ma_gatekeeper && python -m scripts.annotate prelabel \
          --input data/edgar/ \
          --output data/internal30/prelabels.jsonl
      ```
- [ ] Import the JSONL into your Argilla Space; adjudicate spans.
      Budget ~5–10 min per span, total 15–25 hours spread across
      D5–D9 (NOT a weekend burst).
- [ ] For 10 contracts, run the B-pass (independent labels for κ):
      ```
      python -m scripts.annotate prelabel \
          --input data/edgar/ --limit 10 --seed 7 --temperature 0.7 \
          --output data/internal30/prelabels_b.jsonl
      ```
- [ ] After adjudication of both passes, run:
      ```
      python -m scripts.annotate kappa \
          data/internal30/prelabels.jsonl data/internal30/prelabels_b.jsonl
      ```
      Report the κ value in the README ("procedural inoculation, not
      strong evidence of quality").

## D10 (allow-list curation)

- [ ] The 5 deals in `ma_gatekeeper/agent/allow_list.py` were populated
      from public M&A history without live EDGAR verification (the
      generating environment had no SEC network access). Run:
      ```
      export SEC_EDGAR_USER_AGENT="hugo.majerczyk@proton.me MA-Gatekeeper"
      cd ma_gatekeeper && python -m scripts.verify_allow_list
      ```
      All five rows must print `ok=OK`. The script exits non-zero on
      any failure.
- [ ] If any CIK fails, replace it (Designer A round-1 swap suggestion:
      Capital One / Discover Financial Services 2025) and re-run.
- [ ] After deploy, set `VALIDATE_ALLOW_LIST_ON_BOOT=1` in Cloud Run
      env so the lifespan probe also runs in production (off in dev so
      the test suite stays offline).
- [ ] Draft the README "Demo Scope" paragraph naming the 5 deals
      (template already in `README.md`).

## D11–D14 (Reflector loop wired against live Phoenix)

✅ **Code shipped** (`agent/reflector.py`): MCPToolset introspection
agent, `_run_introspection_agent_async` + sync wrapper, paired-
bootstrap promotion gate, code-enforced writable-dataset allowlist,
MCP subprocess cleanup. The post-Phase-5 Reflector runs cleanly on
Python 3.12 and won't leak `npx` processes.

- [ ] Make sure `PHOENIX_MCP_BASE_URL` and `PHOENIX_MCP_API_KEY` point
      at your self-hosted Phoenix (see `.env.example`).
- [ ] One-line `gcloud scheduler jobs create http` invocation that
      hits `/reflect` nightly with an OIDC token whose `aud` matches
      `REFLECT_OIDC_AUDIENCE` (the Cloud Run service URL). Without
      this scheduler the Reflector never fires in production.
- [ ] Manually trigger one cycle (`curl -H "Authorization: Bearer
      $(gcloud auth print-identity-token)" $URL/reflect`) and confirm
      a new prompt version + experiment land in Phoenix. This is
      also Hook 4/5/6/7 end-to-end verification — the Arize judge
      will check.

## D15 (frontend)

✅ **PDF↔trace bidirectional sync shipped (Phase 6.7, 2026-06-04)** —
plan §9 "single differentiating interaction" is now wire-side complete.
`frontend/components/pdf-pane.tsx` v2 renders a lane-tinted bbox
overlay on selection (forward direction, via `viewport.convertToViewportPoint`
with PDF y-flip min/max normalization) AND hit-tests PDF clicks back to
the matching finding (reverse direction, via `viewport.convertToPdfPoint`
+ smallest-area + lexicographic clause_id tie-break). `frontend/app/page.tsx`
threads `onSelect={setSelectedFindingId}` so PdfPane shares the same
selection setter as FindingsPane + TracePane. pdfjs worker pinned to
`pdf.worker.min.mjs` per pdfjs-dist 4.x ESM-only contract (the original
`.min.js` path was a fabricated SDK signature caught by R1 bug-hunter).

The Phase 4 Next.js skeleton (`frontend/`) is otherwise still a **typed
contract reference** for the UX redesign you're owning separately (per
`design/PLAN.md`, referenced by `frontend/tailwind.config.ts:8-14`).

- [ ] Either: integrate your UX rewrite with the existing SSE/Filing
      contracts (the skeleton documents them in `frontend/lib/{api,types}.ts`)
      — the Phase 6.7 bidirectional-sync interaction is reusable as-is
      once you replace the surrounding chrome.
- [ ] Or: keep the skeleton as the demo frontend and incrementally
      replace components.
- [ ] Replace the dropdown `<select>` with a real Combobox component;
      add empty/loading/error states; confirm the Phoenix iframe
      doesn't remount on every selection (`key={traceId}` was the
      Phase 5 UX flag — keep it stable across selections).
- [ ] Confidence sparklines on findings cards (plan §9 also calls
      these out; deferred from Phase 6.7 scope — 2–4h frontend task).

## D18 (Reflector pre-seed + README results-table publication)

✅ **Results-table generator shipped (Phase 6.7, 2026-06-04)** —
`scripts/build_readme_table.py` consumes the three-track eval JSONs
(`calibrate.py` thresholds + `eval_maud_mcq.py` + `eval_cuad_spans.py`),
renders the plan §5.2 + §12 results table to Markdown, and can splice
between literal `<!-- BEGIN_RESULTS_TABLE -->` / `<!-- END_RESULTS_TABLE -->`
markers via `--update-readme` (CRLF-preserving bytes round-trip). The
CUAD `flag` enum is regex-matched against the real
`eval_cuad_spans.py:107-114, :620` source (not a fabricated set);
DEGENERATE_CAVEAT is scoped to the AUPR row only (not baseline rows).
40/40 tests pass under `tests/test_build_readme_table.py`.

- [ ] **Add markers to README.md** (one-time D18 prerequisite — Phase 6.7
      deliberately did NOT modify README.md). Two literal HTML comments
      around where the results table should land in the "Eval headline"
      section:
      ```
      <!-- BEGIN_RESULTS_TABLE -->
      <!-- END_RESULTS_TABLE -->
      ```
- [ ] **After Internal-30 calibration completes (D9) AND the eval scripts
      have produced final JSON outputs** (D9/D13/D14), run:
      ```
      cd ma_gatekeeper && python -m scripts.build_readme_table \
          --calibrate thresholds.json \
          --maud maud_mcq_eval.json \
          --cuad cuad_spans_eval.json \
          --update-readme README.md
      ```
      The generator is partial-input-tolerant — any missing track
      renders a "_Not yet available_" placeholder row, so you can run
      it iteratively as numbers land. Final D18 run should have all
      three flags set.

✅ **Pre-seed automated** (`scripts/seed_reflector.py`): the 4-step
manual procedure below is a single `--commit` invocation. The script
deterministically strips the 4 numbered clause-family blocks from
`CROSS_REFERENCE_PROMPT` (regex pinned in `agent/prompts.py:81-87`),
upserts the strong version as `candidate` FIRST (mid-flight failure
keeps `production` on whatever it was), then upserts the weak version
as `production`.

- [ ] **48 hours before demo recording** (so by D17 evening):
      ```
      cd ma_gatekeeper
      # Dry-run first to inspect the weak template:
      python -m scripts.seed_reflector --show-weak
      # Then commit:
      python -m scripts.seed_reflector --commit
      ```
- [ ] Let the Reflector run twice naturally (Cloud Scheduler from
      D11-D14 should fire it on its cron; manually trigger once with
      `curl` to confirm).
- [ ] The Reflector pre-seeding disclosure is already in `README.md`
      (Reflector loop pre-seeding section) and `docs/devpost.md`. No
      further README edit needed — verify the existing wording reads:
      > "Production prompt was deliberately seeded weaker 48h before
      > demo recording so the auto-improvement loop has a real signal;
      > the loop logic itself is unchanged."

## D19 (demo recording)

✅ **Recording-time spec shipped** (`docs/demo_script.md`): supersedes
`plan.md` §8 for the recording — 30-second climactic voiceover (74
words / 29.6s @ 150 wpm), on-screen pre-seed caption spec (Inter
Medium 500 @ 14px, 20.96s readability floor / 22s hold), restructured
8-row beat table that inverts §8 so auto-promotion is the sole
climax (cmd+click recast as setup beat establishing auditability).
Pre-recorded EDGAR fallback row + Phoenix cold-start fallback row +
auto-promotion-fails-to-fire cascade-fallback row all explicit with
cut-in/re-merge windows. Climax visual is split-screen Reflector log
output (LEFT) + Phoenix Experiments table + prompts-list view
(RIGHT), with optional matplotlib reliability-diagram PNG inset —
NO fabricated Phoenix UI affordances (the audit-and-fix follow-up
on 2026-05-27 closed an unverified-affordance defect; see
PROJECT_LOG.md Phase 6.5).

- [ ] **Stopwatch-rehearse the beat timings on D17–D18.** Beat
      timings in `docs/demo_script.md` are designed, not measured.
      First rehearsal will surface whether the 25s cmd+click hold
      (1:30–1:55) and 30s climax hold (2:30–3:00) need trimming.
- [ ] **Caption rendering test (Inter 500 vs 600 on 1440p).** Test
      once before D19; if Inter Medium 500 reads light on a
      Phoenix-dashboard-bright backdrop, escalate to 600 (same
      `fontSize.small` key, no token change).
- [ ] **Pre-select a "canonical good" D17 rehearsal capture** where
      the Reflector log shows `Promotion gates passed: <diag>` AND
      `PROMOTED candidate ... → tag=production` AND the Phoenix
      prompts-list view shows the `production` tag pointing to the
      new (just-promoted) version. Required by fallback row 3.
- [ ] **Verify the `_LOG.info(...)` format strings at**
      [`agent/reflector.py:760`](agent/reflector.py#L760) **and**
      [`:851`](agent/reflector.py#L851) **haven't drifted since**
      [`docs/demo_script.md:157`](docs/demo_script.md#L157) **was
      written.** Anchored citations will silently rot under a
      reflector.py refactor.
- [ ] Record the 3-minute demo following `docs/demo_script.md`
      (NOT `plan.md` §8 — superseded).
- [ ] Pre-load Phoenix in a second visible window (split-screen) so
      the cmd+click reveal is instant, not an anticlimax.
- [ ] Close the video on the auto-promotion event in Phoenix
      Experiments, not the static results table.
- [ ] Pre-record one full successful EDGAR run as live-demo fallback
      (per fallback row 1 in `docs/demo_script.md`).
- [ ] Upload to YouTube as **Public** or "Unlisted with link
      accessible" — never "Unlisted restricted" (Devpost has DQ'd
      projects for this).

## D20 (submission)

- [ ] Cloud Run deploy with `min-instances=1` for both the agent
      service and Phoenix.
- [ ] Devpost form:
    - [ ] Arize track explicitly selected (the bucket prize depends on this).
    - [ ] Gallery image / thumbnail uploaded.
    - [ ] "Built with" tags include: Google Cloud, Gemini 3, Agent
          Development Kit, Arize, Phoenix, MCP, Cloud Run, Vertex AI.
    - [ ] Team members field populated.
    - [ ] All 7 standard Devpost text sections (Inspiration, What it
          does, How we built it, Challenges, Accomplishments, What we
          learned, What's next) — each 100–300 words.
    - [ ] AI-generated-content disclosure (we use Gemini extensively).
    - [ ] Demo Scope paragraph and pre-seeding disclosure in the
          description.
    - [ ] Backup Phoenix screenshot deck linked in case the live
          dashboard cold-starts during judging.
- [ ] Warm Cloud Run with `min-instances=1`.
- [ ] Triple-check the passcode is on the Devpost description, not
      just the README.

## D21 (June 10 — buffer)

- [ ] Submit by D20 EOD to leave a 24-hour buffer before June 11
      23:00 GMT+2.
- [ ] Spot-check the hosted URL hourly until the evening of June 11.
- [ ] If Phoenix dashboard goes down, link the backup screenshot deck
      from the Devpost description.

## Items that have since shipped (Phase 4 + Phase 5; tracked here so the
## checklist below reflects current state)

- ✅ Apache 2.0 LICENSE at `ma_gatekeeper/LICENSE`.
- ✅ GitHub Actions CI workflow (`.github/workflows/tests.yml`) — pytest on Python 3.11 + 3.12; runs in <30 s.
- ✅ Next.js 14 frontend skeleton in `ma_gatekeeper/frontend/` — three-pane scaffold wired against the SSE contract. **The user is redoing the full UX separately**; the skeleton is now a typed contract reference rather than the production frontend.
- ✅ LLM-assisted annotation pipeline (`scripts/annotate.py`) — Gemini pre-label → Argilla SpanQuestion JSONL + Cohen's κ. D5-D9 task now has tooling.
- ✅ D18 Reflector pre-seed automated (`scripts/seed_reflector.py`) — the 4-step manual pre-seed is a `--commit` flag away from running.
- ✅ ALLOW_LIST populated with 5 real (but unverified-against-live-EDGAR) CIKs — Microsoft/Activision, Pfizer/Seagen, Cisco/Splunk, ExxonMobil/Pioneer, HPE/Juniper. **Operator MUST run `scripts/verify_allow_list.py` before D19.**
- ✅ Devpost text drafts (`docs/devpost.md`) — 7 sections + scope + disclosures + D20 checklist.
- ✅ `/filing/{deal_id}` route serving the EDGAR Ex 2.1 with correct Content-Type (Phase 5 Issue 4 found Ex 2.1 is HTML, not PDF).
- ✅ `trace_id` populated server-side from the active OTel span (Phase 5 Issue 3) — cmd+click demo climax now fires on a real trace.
- ✅ Files API wired with an 8 MB / 5 MB-PDF threshold (Phase 5 Issue 8) — keeps the HTML 5-deal demo on the fast inline path while preventing inline-PDF truncation past page ~20.
- ✅ `_run_introspection_agent` rewritten for Python 3.12 + MCP subprocess cleanup (Phase 5 Issue 5).
- ✅ Single source of truth for the Tag enum (Phase 5 Issue 6) — adding a tag now touches 2 files, not 5.
- ✅ `perturb_contracts.py` rewritten as real ML (Phase 5 Issue 9) — was a vapor stub returning 0.5 AUC on identical files.
- ✅ `REFLECT_OIDC_AUDIENCE` fail-closed on Cloud Run (Phase 5 Issue 10) — silent OIDC bypass is now a 503.
- ✅ **5 quiet-downgrade vectors on the headline number** (Phase 5 E10 audit) — `tests/test_calibration_invariants.py` (28 tests) pins: Wilson LB by-(k,n) values with calibrated z=1.6449 vs z=1.96 gap; paired-bootstrap alpha recovered-quantile (defaults to 0.05); `calibrate_fold` `require_recall=1.0` default + None-on-unachievable behavior; `plot_reliability` per-bin rates over the full pool (catches the block-only-subset regression); dropped-fold disclosure via the new `dropped_headline_folds` + `headline_folds_present` summary fields (extracted from `main()` into `calibrate_all_headline_folds`).
- ✅ **Files API URI expiry recovery** — `agent/server.py:_cache_get_live` evicts cached URIs at `FILES_API_URI_TTL_SECONDS` (36 h default) before Google's 48 h server-side expiry. Monotonic clock so an NTP correction can't extend or shorten a live entry. 5 new tests in `tests/test_files_api.py` pin the eviction, the pop-in-place behavior, and the monotonic-not-wallclock requirement.
- ✅ **MCP subprocess process-shutdown cleanup** — `agent/reflector.py` now has a module-level `_mcp_toolset_registry` (strong-set + `threading.Lock`), `_aclose_one_with_timeout` (idempotent via `_MCP_CLOSED_ATTR` sentinel + per-instance `asyncio.wait_for` timeout of 5 s), `shutdown_all_toolsets` (snapshot under lock + `asyncio.gather(return_exceptions=True)`), and `atexit` hook. FastAPI lifespan post-yield calls `shutdown_all_toolsets`. 9 new tests in `tests/test_introspection_agent.py` cover registration, drain, timeout, exception isolation, idempotency, empty-drain, thread safety, and unregister.

## Items still NOT done (lower priority for the hackathon spine)

- **Cloud Scheduler config** (a 1-line `gcloud scheduler` invocation; lives with the deploy work, not the codebase).
- **UX redesign** — user is doing this separately (see `design/PLAN.md` referenced by `frontend/tailwind.config.ts`); the current skeleton stays as a contract reference.
- ✅ **Demo storytelling pass** (Phase 5 E9 audit) — **shipped 2026-05-27 as `docs/demo_script.md` via a 5-round feature-build-loop with an embedded audit-and-fix follow-up after self-confessed shortcuts. See PROJECT_LOG.md Phase 6.5 entry.**
- ✅ **MAUD-MCQ + CUAD-Spans eval scripts** (plan §5.2 + §12 gap closure) — **shipped 2026-05-27 as `scripts/eval_maud_mcq.py` + `scripts/eval_cuad_spans.py` via Phase 6.6. Both ship project metrics + paper-comparable metrics side-by-side. See PROJECT_LOG.md Phase 6.6 entry.**
- ✅ **PDF bbox extraction + SSE threading** (plan §3.1 D4 + §9 gap closure) — **shipped 2026-05-27 as `agent/pdf_bbox.py` + `agent/schemas.py` + `agent/server.py` updates via Phase 6.6. RiskFinding now carries `page` + `pdf_bbox`, server-side populated via Parser event-stream interception mirroring the `trace_id` precedent. pdfplumber offline fallback for null bbox on PDFs with 5s timeout. Frontend D15 work unblocked.**
- **Frontend↔backend OpenAPI codegen** — TS Tag union is hand-mirrored; drift is regex-guarded by `tests/test_tag_sync.py` instead of generated.
- **LRU-2b benign-redundancy mutation gap** — documented in `agent/server.py:_get_or_create_files_api_lock` docstring; refactor to single eviction site would close it.
- **Live ADK Runner wrapper for `--live` eval paths** — `eval_maud_mcq.py:make_live_agent` and `eval_cuad_spans.py:make_live_agent` both raise `NotImplementedError` by design (per Phase 6.6 Goal-alignment review). Operator wires the live path on D9/D13 when Vertex + Phoenix are deployed; the mock-default ensures CI never accidentally burns quota.
- **CUAD apostrophe-parsing latent edge case** — `eval_cuad_spans.py:_extract_clause_phrase_from_question` may silently drop a CUAD row if its question contains a stray `'` (apostrophe-vs-single-quote ambiguity). Not triggered by the canonical CUAD-QA template; flagged for hardening if a future mirror adds prose containing apostrophes.
- ✅ **README results-table generator** (plan §5.2 + §12 publication artifact) — **shipped 2026-06-04 as `scripts/build_readme_table.py` + 40 tests via Phase 6.7. Three-track Markdown table with regex against the real `eval_cuad_spans.py` flag enum, DEGENERATE_CAVEAT scoped to AUPR row only, partial-input-tolerant (missing tracks render placeholders), CRLF-preserving bytes splice between `<!-- BEGIN_RESULTS_TABLE -->` / `<!-- END_RESULTS_TABLE -->` markers. Operator must add the markers + run `--update-readme` after eval JSONs land on D9/D13/D14. See PROJECT_LOG.md Phase 6.7 entry.**
- ✅ **PDF↔trace bidirectional sync** (plan §9 "single differentiating interaction") — **shipped 2026-06-04 as `frontend/components/pdf-pane.tsx` v2 + `frontend/app/page.tsx` v2 via Phase 6.7. Forward = lane-tinted bbox overlay via `viewport.convertToViewportPoint`; reverse = click → `convertToPdfPoint` → hit-test on current page with smallest-area + lexicographic tie-break. pdfjs worker pinned to `.min.mjs` per pdfjs-dist 4.x ESM-only contract (R1 bug-hunter caught the fabricated `.min.js` path). See PROJECT_LOG.md Phase 6.7 entry.**
- **Confidence sparklines on findings cards** — plan §9 calls these out; deferred from Phase 6.7 scope. 2–4h frontend task on `findings-pane.tsx`.

## Sanity checks that should pass before D7 architecture freeze

These verify that the actual installed SDK matches the shapes the code
expects (the architecture/Arize reviewer flagged these explicitly):

1. `python -c "from phoenix.evals import LLM; LLM(model='gemini-3-pro', provider='vertexai')"`
   — no exception.
2. `python -c "from phoenix.client import Client; Client().annotations.add_span_annotation"`
   — attribute exists; if it's `client.spans.add_annotation` instead,
   update `agent/router.py` (one line) and `agent/reflector.py`.
3. `python -c "from google.adk import LlmAgent, ParallelAgent, SequentialAgent"`
   — no import error.
4. `python -c "from google.adk.tools.mcp_tool import MCPToolset, StdioServerParameters"`
   — `MCPToolset(connection_params=StdioServerParameters(...))` is the
   non-deprecated form.

If any of these fail, fix at the SDK boundary in the named file. The
internal logic does not depend on the SDK shape.
