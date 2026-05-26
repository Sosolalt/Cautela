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

## D5–D9 (annotation)

✅ **Pipeline shipped** (`scripts/annotate.py`): Gemini pre-labels →
Argilla SpanQuestion JSONL + Cohen's κ. Includes a no-op + char-offset
invariant guard so a misconfigured run fails loud instead of silently
producing identical files.

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

The Phase 4 Next.js skeleton (`frontend/`) is now a **typed contract
reference** rather than the production frontend. You are owning the
full UX redesign separately (per `design/PLAN.md`, referenced by
`frontend/tailwind.config.ts:8-14`).

- [ ] Either: integrate your UX rewrite with the existing SSE/Filing
      contracts (the skeleton documents them in `frontend/lib/{api,types}.ts`).
- [ ] Or: keep the skeleton as the demo frontend and incrementally
      replace components.
- [ ] PDF↔trace bidirectional sync — feasible because `Clause.pdf_bbox`
      is populated at D4 and span attributes carry it at D7. The
      current skeleton stubs this (forward sync uses `page` if the
      server threads it through, reverse sync deferred).
- [ ] Replace the dropdown `<select>` with a real Combobox component;
      add empty/loading/error states; confirm the Phoenix iframe
      doesn't remount on every selection (`key={traceId}` was the
      Phase 5 UX flag — keep it stable across selections).

## D18 (Reflector pre-seed)

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

- [ ] Record the 3-minute demo following the §8 beat structure.
- [ ] Pre-load Phoenix in a second visible window (split-screen) so
      the cmd+click reveal is instant, not an anticlimax.
- [ ] Close the video on the auto-promotion event in Phoenix
      Experiments, not the static results table.
- [ ] Pre-record one full successful EDGAR run as live-demo fallback.
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

## Items still NOT done (lower priority for the hackathon spine)

- **Cloud Scheduler config** (a 1-line `gcloud scheduler` invocation; lives with the deploy work, not the codebase).
- **UX redesign** — user is doing this separately (see `design/PLAN.md` referenced by `frontend/tailwind.config.ts`); the current skeleton stays as a contract reference.
- **Files API expiry recovery** — uploaded file URIs auto-expire after 48 h on Google's side; a long-lived Cloud Run instance after 48 h would 404 on a cached URI. Acceptable for the hackathon (Cloud Run scales to zero off-demo, re-warm on demo day).
- **MCP subprocess process-shutdown cleanup** — per-call cleanup is in place; process-shutdown hook not.
- **5 quiet-downgrade vectors on the headline number** (Phase 5 E10 audit, deferred): Wilson LB by-(k,n) pinned-value test; paired-bootstrap alpha recovered-quantile test; `require_recall=1.0` parameter test; `plot_reliability` golden-image test; dropped-fold fallback "all headline folds present" test.
- **Demo storytelling pass** (Phase 5 E9 audit, deferred): verbatim 30-second voiceover script, on-screen pre-seed caption spec, beat-table restructure to make auto-promotion the sole climax.
- **Frontend↔backend OpenAPI codegen** — TS Tag union is hand-mirrored; drift is regex-guarded by `tests/test_tag_sync.py` instead of generated.

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
