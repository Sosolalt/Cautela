# Project Log — M&A Due Diligence Gatekeeper

**Hackathon**: Google Cloud Rapid Agent Hackathon — Arize partner track.
**Deadline**: 2026-06-11. **Started**: 2026-05-19. **Updated**: 2026-06-08 (Phase 9).

> **Note on this file**: condensed 2026-06-09 to recover context budget. The full
> blow-by-blow audit trail (every reviewer round, exact tool-call counts, LOC deltas)
> is preserved verbatim in `PROJECT_LOG.archive.md`. This file keeps every
> load-bearing fact, decision, lock, and lesson; it drops only the repeated
> narration. When in doubt about *how* a thing was decided, read the archive.

---

## TL;DR

Vertical M&A contract-review agent (Gemini 3 Pro + Google ADK + Arize Phoenix on Cloud Run). Two tracks:

- **Product** (`ma_gatekeeper/`): 10 Python modules + scripts; **~376 tests** (365 baseline + 11 from Phase 9 Build #3, pending the CI re-run the Phase-9 reviewer cohort signed off on). CI green on 3.11+3.12. End-to-end demo path functional on the 5 curated CIKs. PDF↔trace bidirectional sync wire-complete in the frontend.
- **Design** (`design/`): Phases 0–5 converged, then **Phase 7 (2026-06-08) replaced the entire register** — Documentary Brutalism with M&A luxury palette (champagne / oxblood / ivory on near-black) + Instrument Serif / Space Grotesk / Geist Mono. Prior locked palette (warm-clay `#B86F3D`, Fraunces/Inter/JetBrains, cool-green neutrals) is SUPERSEDED. `design/SOURCE_OF_TRUTH.md` is the new index; legacy `design/*.md` carry SUPERSEDED banners. `plan.md` website sections rewritten through 9-critic red-team (Phase 7B).

**Wedge**: experiment-gated prompt promotion with frozen-fold non-regression (the Reflector loop). Phase 9 extended it to a Reflector-as-ADK-LoopAgent that recursively calls Phoenix MCP (Build #3, the demo climax).

### ⚠️ Current git state (read first)
**Last commit is `f998386` = Phase 6.7.** Everything from **Phase 7, 8, and 9 is uncommitted working-tree state** (design-system regen, all 10 FIX_PLAN fixes, the Phase-9 Build #3 LoopAgent + 5 new files / 1804 LOC). `git status` shows ~40 modified + many untracked. The user handles commits; do not commit/push unless asked.

---

## Operating constraints

- Never `git commit` / `git push` unless explicitly asked. Stage/diff/status OK on request.
- No `Co-Authored-By: Claude` trailer.
- Two tracks: default to `ma_gatekeeper/`; touch `design/` only on explicit ask.
- SEC EDGAR identity: hugo.majerczyk@proton.me.

---

## Current code state

**Modules**: schemas, instrumentation, evaluators, router, agents, prompts, reflector, **reflector_loop** (Phase 9), server, allow_list, pdf_bbox.
**Scripts**: download_datasets, perturb_contracts (real TF-IDF/LogReg), calibrate, annotate, seed_reflector, verify_allow_list, eval_maud_mcq, eval_cuad_spans, build_readme_table, verify_structural_reasoning (Phase 8 Fix 6).
**Tests**: pure-Python, no live API calls. Local-without-optional-deps collects ~313; full count requires CI's pinned requirements.
**Frontend**: Next 14.2.5 + react-pdf 9.1.1 + pdfjs-dist 4.4.168. PDF↔trace bidirectional sync wired (forward = lane-tinted bbox overlay + page scroll; reverse = click→PDF-coord→hit-test→`onSelect`). Phase 9 added `reflector-loop-button.tsx` ("Run Reflector now" + streamed status panel).
**Infra**: Dockerfile slim+non-root+$PORT; Apache 2.0 LICENSE; CI pytest on 3.11+3.12.

**End-to-end demo path (works on 5 curated CIKs)**:
- Allow-list: Microsoft/Activision, Pfizer/Seagen, Cisco/Splunk, ExxonMobil/Pioneer, HPE/Juniper. Operator runs `scripts/verify_allow_list.py` before D19.
- `/filing/{deal_id}` serves EDGAR Ex 2.1 with sniffed Content-Type (HTML or PDF), cached.
- `trace_id` populated server-side from active OTel span; frontend deep-links into Phoenix.
- Gemini: inline `Part.from_bytes` <8MB, Files API + `Part.from_uri` above (TTL-evicted 36h, LRU-capped 64).
- MCP introspection: subprocess registry + cross-loop detection + lifespan drain + atexit hook.
- Tag enum: single source of truth via `typing.get_args(Tag)`; CI fails on cross-file drift.
- `/reflect` OIDC fail-closed on Cloud Run; `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'`.
- Phase 9: `POST /reflect/loop` (passcode-gated) streams a LoopAgent run as SSE.

---

## Outstanding work (`ma_gatekeeper/HANDOFF.md` is the canonical operator list)

| Days | Phase | Status |
|---|---|---|
| D1–D2 | Phoenix infra | Self-hosted Cloud Run + iframe (iframe killed Day-1; mock-only) |
| D3 | ADK skeleton | Vertex quota request (operator) |
| D4 | Parser | ✅ code shipped (`agents.py` + `Clause.pdf_bbox`) |
| D5–D9 | Annotation + calibration | ✅ tooling shipped; operator runs annotation (15–25h) + calibration |
| D10 | Allow-list | operator runs `verify_allow_list.py` |
| D11–D14 | Reflector loop | ✅ code shipped; operator wires Cloud Scheduler |
| D15–D17 | Frontend | ✅ PDF↔trace sync shipped (6.7); **sparklines still outstanding** (2–4h) |
| D18 | Pre-seed + README | ✅ results-table generator shipped (6.7); operator adds README markers + runs `--update-readme` post-calibration |
| D19 | Recording | operator: 3-min demo + EDGAR fallback pre-record |
| D20 | Submission | operator: Devpost form + Cloud Run warming |
| D21 | Buffer | 24h verify before deadline |

**Scope-clock change (Phase 9)**: submission is **T-48h (D22)**, not D19/D20.

**User-action queue**: `npm install` in `frontend/` (lockfile → unblocks size-limit CI); Playwright MCP install (Phase-1 screenshots + contrast field-verification); COPY.md placeholders (`<<CONTACT-EMAIL>>`, `<<TOS-URL>>`, `<<GOVERNING-LAW>>`, `<<DEMO-DEAL-1..5>>`); GC-persona legal review of COPY §6/§11.

**Remaining engineering nits (non-blocking)**: confidence sparklines on findings cards; D15 Tailwind sweep (3 real violations at `findings-pane.tsx:55/:61`, `deal-picker.tsx:25`); live ADK Runner wrappers for `--live` eval paths (raise `NotImplementedError` by design); CUAD apostrophe-parsing latent edge case; frontend↔backend OpenAPI codegen (TS Tag union hand-mirrored, regex-guarded).

---

## Hard-to-reverse decisions

### Product
- Threshold τ_h, τ_f via 5-fold CV; fold 5 frozen as Reflector non-regression held-out. ε = max(SE_fold5, 0.03).
- One-sided Wilson LB (z=1.6449); cluster bootstrap over contracts (one-sided α=0.05).
- **Cluster-bootstrap 95% LB over contracts is the headline published-unmodified statistic** (Phase 8 Fix 10); Wilson retained as exploratory per-finding-IID cross-check only.
- Independent gating per evaluator (hallucination AND faithfulness) — never averaged.
- Three Phoenix annotations: `hallucination`, `clause_faithfulness`, `risk_judge_gate`.
- 30 contracts in Internal-30 (LLM-assist + κ on 10-contract double-annotated subset).
- 5 demo deals (no open ticker box); pre-validated to surface Block-tier findings.
- **Internal-30 contamination fix (Phase 8 Fix 1)**: Gemini 3 Pro cutoff = **2025-01-01** (DeepMind model card). All famous busted-deal cases (Akorn, AB Stable, BMS/Celgene CVR, Tiffany, Hexion, etc.) predate it and saturate indexed law-firm alerts → recall on them is a memorization check. Deal bank split into **Calibration-17** (12 post-cutoff core, every row a primary-source URL dated strictly > 2025-01-01, + 5 demo-path-flagged) and **Narrative-12** (famous precedents, captioned "illustrative use only; NOT in reported recall metrics"). Fold-5 entirely inside Calibration-17.

### Design — Phase 7 locks (2026-06-08) — CANONICAL
Source of truth: `design/SOURCE_OF_TRUTH.md` → `claude-design-output/README.md` → `source/design.md` → `colors_and_type.css`.
- **Palette** (lived set in `colors_and_type.css:30-35`): `--surface #0B0B0C` (NEVER `#000000`), `--ink #ECECEA`, `--ink-muted #8A8A86`, `--ink-faint #54534F`, `--accent-champagne #C9A961` (primary), `--accent-champagne-deep #9C7E3F`, `--accent-champagne-soft #E0CB94`, `--accent-oxblood #8B2635`, `--accent-ivory #E8DDC4`. **Warm-clay `#B86F3D` explicitly forbidden** (asserted in `tokens.test.ts`).
- **Lane → palette**: clear → champagne-soft `#E0CB94`, escalate → champagne `#C9A961`, block → oxblood `#8B2635`. Text-on-filled: `#1A1916` on champagne, ivory `#E8DDC4` on oxblood. All pairs pass 4.5:1 (tokens.test.ts).
- **Typography**: Instrument Serif (display → Newsreader → Georgia), Space Grotesk (body → Inter Tight; plain Inter forbidden), Geist Mono (→ IBM Plex Mono). Display 88px floor / 216px ceiling.
- **Composition non-negotiables**: `border-radius: 0` globally, `box-shadow: none`, no centered hero, no row-of-buttons CTA, no card frame, one accent per surface ≤3 placements, mono ligatures off, em-dashes + footnote markers (`† ‡ §` taxonomy / `¹ ² ³` footnotes) load-bearing.
- **Motion**: one easing `cubic-bezier(0.16, 1, 0.3, 1)`; two durations 200ms (hover) / 800ms (entry). 400ms preserved as back-compat alias only.
- **Three surfaces share `design/tokens.ts`**: `/review` (working agent, champagne, Hosted-URL target), `/marketing` (landing, ochre, demo-video bookend), `/results` (eval table, champagne).
- **Finding-row lane disambiguation**: 2px lane-color left-edge bar (first-read) + taxonomy footnote marker `† = Block, ‡ = Escalate, § = Auto-Clear` mapped to `GatekeeperDecision.lane` post-routing. Numeric `¹²³` rejected (collides with "Block" priority-order). Filled colored row backgrounds banned.
- **PDF clauses**: 2px stroke 2px below glyph baseline + 2px rail tick (the tick reads at 720p). Hover/selected → 4px in 200ms.
- **Demo flow** (`plan.md §8`): cmd+click→Phoenix is the **cold-open at 0:00–0:04**; brand hero is the **closing bookend at 2:45–3:00** (reverse of v3 plan; forced by hostile-juror critic).
- **Hosted Project URL** → `/review?deal=NVDA-MLNX-2024&autostart=1` (NOT `/marketing`). Requires net-new `?deal=X&autostart=1` handler in `app/page.tsx`.
- **Streamlit fallback OFF.** Three-tier landing slip-protection: Next.js route group → SVG-with-depth → static `hero-b.html` via FastAPI parent-mount at `/dso` (parent-mount needed so relative `../../colors_and_type.css` resolves).
- **Three.js stretch OFF the critical path.** `hero-b.html` is 1534 LOC of bespoke WebGL (NOT "CSS 3D parallax"); SVG-with-depth is the primary marketing ship.

### Design — pre-Phase-7 (SUPERSEDED 2026-06-08, kept for audit)
- ~~`--brand-primary #0F4A38`, `--accent-clay #B86F3D`, cool-green neutrals; Fraunces+Inter+JetBrains; motion 150/400/800ms; Fraunces-600 wordmark~~. Iframe kill-switch (mock-only) still applies.

---

## Pre-commitments locked

- Cluster-bootstrap 95% LB over contracts published unmodified (Wilson exploratory cross-check). (Supersedes the original "publish Wilson LB unmodified" commitment — see Fix 10.)
- Demo voiceover: "five pre-indexed deals" (no "recently indexed").
- Reflector pre-seeding disclosed in README + Devpost ("production prompt deliberately seeded weaker 48h before demo").
- Three-track eval table in README (MAUD-MCQ, CUAD-Spans, Internal-30).
- Apache 2.0 LICENSE in repo About sidebar.
- Arize track checkbox in Devpost.

## Scope cuts (each survived a reviewer)

2 extensions (was 8: Playbook customization, HITL annotation); 30 contracts (was 60); 5 demo deals (was open ticker); 2 evaluators only; no A2A; no multi-language; no live integration tests; Files API expiry recovery = TTL eviction only.

---

## Phase history (condensed — full detail in `PROJECT_LOG.archive.md`)

- **Phase 0 / 0.5**: Idea synthesis (Document Review Gatekeeper × M&A). 4 research agents. Key findings: CUAD CoC SOTA ~70-80% F1 (not 95%); Phoenix MCP can't launch experiments or write annotations (Python SDK only); AX Online Eval SaaS-only (use Cloud Scheduler + `run_evals`); 30-contract annotation = 15-25h.
- **Phase 1**: Plan v1→v4, 4 review rounds. Dropped fantasy stats; "100% precision" → "Wilson LB at published abstention rate"; independent gating; paired bootstrap CI + frozen fold-5; 5-fold CV; PDF bbox at D4.
- **Phase 2**: Scaffolding (8 modules, 23 tests). Believed correct — was wrong.
- **Phase 3**: 5 reviewers × 4 rounds. Caught ~15 fabricated SDK signatures, wrong stats (α/2, z=1.96, parametric bootstrap), security gaps (open `/reflect`, query-string passcode, fail-open OIDC). All VALIDATED by round D.
- **Phase 4**: Feature buildout (annotation pipeline, LICENSE, CI, D18 seed, Next.js skeleton, Devpost draft). 70 tests.
- **Phase 5**: 10-reviewer full-project audit. Found end-to-end demo path broken in 4 ways despite Phase-3 "VALIDATED": empty allow-list CIKs, missing `/pdf-proxy`, unpopulated `trace_id`, EdgarTools HTML mislabeled PDF. Plus `perturb_contracts.py` vapor, silent OIDC bypass, `get_event_loop()` bug, Tag enum 4× replication, Files API not wired. Shipped 10 prioritized fixes. 151 tests.
- **Phase 6 + honesty pass**: Tier-2 follow-ups (E10 quiet-downgrade tests, Files API TTL eviction, MCP shutdown hook). User caught 7 orchestration shortcuts; closed each. R4 bug-hunter + R5 security + R6 WebFetch verifier caught 4 production bugs (unbounded `_files_api_locks` → LRU cap; cross-loop aclose hazard → `(toolset, loop)` skip; wrong `StdioServerParameters` import → `mcp` package; `aclose` vs `close` precedence). 208 tests.
- **Design Phases 0–5**: TOOLING / INSPIRATION / COPY / STACK / SYSTEM / tokens.ts converged via `design-team`. Day-4 gap: user caught Phase 4/5 self-validated only → retroactive 3-reviewer cohorts caught 3 critical (SYSTEM contrast math 1.89:1 where 4.5:1 claimed; fabricated SOC2/pen-test dates in COPY §6; §11.5 vs §6 self-contradiction; tokens.ts contrast-lie). 3/3 GO after 3 rounds.
- **Phase 6.5 — E9 demo script (2026-05-27)**: `docs/demo_script.md` via 5-round feature-build-loop. Climax = auto-promotion (inverts plan §8). Audit-and-fix follow-up closed a fabricated-Phoenix-UI-affordance defect.
- **Phase 6.6 — three-track eval + PDF bbox (2026-05-27)**: closed 4 real gaps. New: `eval_maud_mcq.py` (38 tests), `eval_cuad_spans.py` (54 tests), `agent/pdf_bbox.py` (17 tests) + SSE threading of `page`/`pdf_bbox`. 208 → 325 tests. WebFetch reviewer caught fabricated HF dataset schemas + fabricated metric definitions. Lesson: dispatching two Builders editing the same production files concurrently is a coordination hazard (write to `/tmp` first).
- **Phase 6.7 — D15 reverse sync + D18 README generator (2026-06-04)**: re-audit surfaced two glossed gaps. `scripts/build_readme_table.py` (40 tests) + reverse direction of PDF↔trace sync in `pdf-pane.tsx` (109→270). Bug-hunter caught a **fabricated CUAD `flag` enum** (code asserted `{ACHIEVED, FALLBACK_TO_MAX}`; real source emits `None` / `recall_{t}_unachieved`, and the test fixtures baked in the fake values → green CI was structurally lying) and a **fabricated pdfjs worker filename** (`.min.js` doesn't exist in pdfjs-dist@4.4.168 ESM-only → `.min.mjs`). 325 tests.
- **Phase 7 — design-system regeneration (2026-06-08)**: user shipped a new system via `claude design` into `design/claude-design-output/` (Documentary Brutalism). **7A (mechanical migration)**: `tokens.ts` revalued under same keys + new keys; `tokens.test.ts` 9→13 invariants (warm-clay never exported, `border-radius:0` everywhere, one easing); `tailwind.config.ts` + `globals.css` + `layout.tsx` updated; 7 legacy `design/*.md` SUPERSEDED-bannered; `SOURCE_OF_TRUTH.md` new. **7B (plan.md website rewrite)**: `WEBSITE_PLAN_UPDATE.md` v0→v3 over 3 red-team rounds (9 critics). Caught the `hero-b.html` "CSS 3D parallax" → actually-Three.js misframing; "shadcn removed" (never installed); Hosted URL = `/` unforced error → `/review?deal=...&autostart=1`; broken brand-QA grep regex; footnote `¹²³` lane collision → `† ‡ §`. `plan.md` 654→719 lines. Lesson: **hostile-juror critic role is load-bearing** for juror-facing surfaces; **pair every red-team with a convergence verifier as the last round**.
- **Phase 8 — pre-submission critic review + FIX_PLAN (2026-06-08)**: 6 parallel critics (M&A partner, Arize engineer, GCP/Gemini PM, Devpost judge, ML/eval skeptic, demo storyteller). 4/6 concluded auto-promotion is the **wrong climax** (jargon-stacked, no human stake/dollar, gate "essentially cannot fail to fire"). ML/eval skeptic surfaced the **Internal-30 contamination** finding (→ Fix 1). Wrote `FIX_PLAN` (10 ordered fixes + pre-flight gates V1–V5) + `POST_HACKATHON_BACKLOG.md` (10 deferred items). Pre-flight: V1 `introspection_summary` dead; V2 `calibrate.py:295` Wilson uses `total_findings` (pseudoreplication); V3 CrossReference is a real `LlmAgent`; V4 HEAD-checked 43 deal-bank URLs (40/43 OK); V5 confirmed contamination (cutoff 2025-01-01). Gate evidence in `FIX_PLAN_NOTES.md`.
  - **Fix 1** — deal-bank split (Calibration-17 + Narrative-12), 2 rounds. Bug-hunter caught a **fabricated SEC accession** (Synopsys URL parsed clean but pointed at a Feb-2025 pro-forma, not the Jul close) — contamination-rule violation inside the contamination-fix doc. R2 repaired Synopsys / Mars-Kellanova / Albertsons URLs with HEAD + body-grep date verification.
  - **Fix 2** — BMS/Celgene CVR cold-open in `demo_script.md` ("Dec 31 2020 · 36 days · $6.4B · single missing clause"); cmd+click moved to a mid-demo audit-proof beat. R1 caught 4 token-citation errors (line numbers / hex pasted without opening `tokens.ts`).
  - **Fix 3** — climax VO plain-English rewrite ("two gates passed: A, and B"). 1 round. All three Locks held ("five pre-indexed deals"; 22-word pre-seed disclosure verbatim; three component names: paired-bootstrap CI, frozen fold, ε floor). Honest +1.6s overflow disclosed (absorbs into the 8s held shot).
  - **Fix 4 (+ Fix 9 + token sweep)** — nuked 22s pre-seed caption → 6s lower-third badge; added 1:00–1:15 "$6.4B at risk" BMS-tie beat; Fix 9 honesty edit "real signal to find" → "structurally guaranteed to outperform" across all 3 freeze-frame surfaces (`devpost.md` canonical + `demo_script.md` VO + Lock table); swept the pre-existing Deliverable-2 token-citation errors.
  - **Fix 5** — Arize MCP introspection rewire in `reflector.py` (Hook-4 path: `_failing_traces` → `_parse_introspection_output(_run_introspection_agent())`, with `_failing_traces` as fallback). Highest-value engineering fix per the Arize juror.
  - **Fix 6** — structural-reasoning beat: built infra (`tests/fixtures/structural_reasoning_pair.json` + `verify_structural_reasoning.py` + conditional beat) with an explicit **SHIP/CUT gate on Day-3** `--live` exit code ("faking it is worse than skipping"). Later superseded as the demo beat by Fix 7 (juror panel said Fix-6 beat was theater).
  - **Fix 7** — **SHIPPED** (undeferred after a 7-juror panel confirmed "the one change that wins the Google Cloud bucket"). Standalone `LlmAgent` on `gemini-3-pro-preview` consuming all 30 Internal-30 contracts in a **single ~800k-token call** for cross-deal carve-out structural clustering (impossible per-contract — schema needs `member_deal_ids` spanning deals). Exposed as `/portfolio` endpoint + dedicated pane; demo beat at 1:55–2:05 replacing the Fix-6 beat.
  - **Fix 8** — folded into Fix 1 R2 (the URL repairs).
  - **Fix 10** — `calibrate.py:295` Wilson pseudoreplication relabel: cluster-bootstrap LB over contracts is now the headline statistic; Wilson per-finding kept as exploratory cross-check. Propagated across 10 anchors in 7 marketing files + a grep-missed 4-anchor mirror in `_ds_bundle.js` (design-team carve-out, rename-only).
- **Phase 9 — Reflector-as-LoopAgent Build #3 + §12 demo button (2026-06-08)**: `/project-team` round on the post-POC roadmap; user **narrowed scope mid-round** — submission is T-48h, only Build #3 ships pre-submission, everything else (Build #1/#2, §13.1–13.5) deferred to ≥2026-06-12 with a "no merge before 2026-06-12" kill-switch; the 365-test + 5-deal demo path stays byte-stable. **Build #3 shipped via feature-build-loop, 4/4 GO Round 1.** New files: `agent/reflector_loop.py` (720 LOC — LoopAgent wrap with hard-gate `_call_mcp_list_traces`), `tests/test_reflector_loop.py` (487 LOC, 9 tests), `tests/test_reflector_loop_demo_e2e.py` (282 LOC, TestClient HTTP→SSE→LoopAgent), `frontend/components/reflector-loop-button.tsx` (193 LOC), `docs/post_poc_demo_script.md` (122 LOC, ≤90s VO Python-counted = 77 words/30.8s). Additive edits: `server.py` (+114, `POST /reflect/loop` passcode-gated), `schemas.py` (+142, `ReflectorLoopEvent`/`ReflectorLoopReport`), `frontend/lib/{types,api}.ts`, `findings-pane.tsx`, `.env.example`. **~1804 LOC new across 5 files.** Reviewer non-blocking notes: `deal_id` has no length cap / ALLOW_LIST check; LLM `candidate_template[:400]` embedded in `gh pr create --body` (wrap in `<!-- UNTRUSTED -->` before flipping `REFLECTOR_LOOP_AUTO_PR=1` in prod). The `reflector.py` Hook-4 mutation (+103/-21) is pre-Phase-9 uncommitted Fix-5 work (mtime forensics), not a Phase-9 violation. **Process lesson**: a `/project-team` dispatch estimating 6× build-loops against a 3-day deadline to a locked submission is correctly resolved by writing the plan + appending operator items + deferring execution — not by burning context on code that can't merge for ≥4 days.

---

## What failed (most expensive-to-rediscover knowledge)

### Fabricated SDK signatures (Phase 3) — DO NOT regress
- `LLM(provider="vertex")` not `"vertexai"`.
- `clf.evaluate({...})` returning `List[Score]`, not `clf(...)` returning object with `.score`.
- `client.spans.add_span_annotation` not `client.annotations.*` (deprecated).
- `client.prompts.get(prompt_identifier=...)` not `name=...`.
- `client.prompts.create(version=PromptVersion(...))` not `upsert(...)`.
- `client.experiments.run_experiment(dataset=Dataset)` not `dataset="name"`.
- `from google.adk.agents import ...` not `from google.adk import ...`.
- `InMemoryRunner(...).run_async(user_id=, session_id=, new_message=Content(parts=[Part.from_bytes(...)]))` — not `root.run_async(pdf_bytes=...)`.
- `event.author` + `event.content.parts[i].text`, not `event.name`/`event.value`.
- `StdioServerParameters` is in `mcp` package, NOT `google.adk.tools.mcp_tool`.
- ADK `MCPToolset.close()` not `aclose()` (sentinel comment was wrong).
- `asyncio.get_running_loop()` not `get_event_loop()`.
- FastAPI lifespan asynccontextmanager, not `on_event`.
- EdgarTools `attachment.download()` writes to disk and returns path (use `tempfile.TemporaryDirectory()`).

**The "Fabricated External References" failure-mode class generalizes far beyond SDKs.** Caught in 7+ distinct layers: Phase 3 Python SDKs; 6.5 Phoenix UI affordances; 6.6 HF dataset schemas; 6.7 CUAD-flag enum + pdfjs worker filename; 7B Three.js misframing; 8-Fix-1 SEC accession number; 8-Fix-2 design-token line/hex citations. **Rule: any reference to a structured external surface (SDK method, design token, schema line, SEC accession, eval-flag enum, model worker filename) must be verified against the actual source file before pasting — and verification of a URL means HEAD-check *and* body-grep for the claimed value, not HEAD alone.** When production code and test fixtures share an invented value, green CI is structurally lying.

### Asymmetric-loss invariants (encoded in tests)
- Hallucinated explanation cannot auto-clear at high faithfulness (`test_router.py`).
- Reflector cannot write to frozen fold 5 (allowlist enforced).
- Promotion requires paired bootstrap CI LB > 0 AND non-regression on fold 5 with ε floor.
- Wilson LB by-(k,n) pinned values catch z=1.6449 → 1.96 silent regression (margin >0.030).
- Block-tier classification cannot be modified by Reflector promotion path.

### Contrast-lie pattern (design)
Light text on warm-mid colors "reads readable" but math-fails. Mechanical WCAG contrast tests at PR time (`tokens.test.ts` tests 4–9) catch this.

### Phase 7B — design-system-docs fabrications (caught by Round-2/3 critics)
| Claimed (v0/v1/v2 plan) | Actually true |
|---|---|
| "`hero-b.html` is CSS 3D parallax" (4-6h port) | `three@0.160.0` CDN; `hero-scene.js` 1534 LOC bespoke WebGL (page-curl vertex math, staple/paper materials, projection-to-SVG overlay, 7s loop). 10-16h; demoted to D16 stretch; SVG-with-depth is primary. |
| "shadcn/ui removed" | Never installed. `package.json` = next/react/react-pdf/clsx/tailwindcss only. Reframed "never adopted." |
| Brand-QA grep `\brounded(?!\s|-none)\b` | Structurally broken (needs `-P`; whitespace exclusion rejects real violations, matches comments). Real violations at `findings-pane.tsx:61/:55`, `deal-picker.tsx:25` uncaught. v3 → three independent passes incl. `bg-lane-*`. |
| `hero-b.html` served at `/marketing` | Relative `../../colors_and_type.css` would 404. v3 mounts parent at `/dso` + `/marketing` redirect. |
| "v1 grep zero matches after D14 sweep" | The sweep never happened — aspirational. Violations still live. D15-AM sweep is the first build step. |
| `¹ ² ³` disambiguates lanes | At 720p reads as row index. v3 → 2px lane-color left-edge bar + taxonomy glyphs `† ‡ §`. |
| Hosted URL → `/` | Devpost convention = working agent. v3 → `/review?deal=NVDA-MLNX-2024&autostart=1` (net-new `app/page.tsx` handler). |
| `¹=Block, ²=Escalate, ³=Auto-Clear` | Two three-value enums exist (`RiskFinding.severity` vs `GatekeeperDecision.lane`). v3 maps marker to `lane` post-routing. |
| "48h pre-seed on D18" | §6.4 "48h before recording" + recording moved to D19 → pre-seed is D17. Pre-existing 24h drift fixed. |

### Process traps
- "Reviewer-validated" ≠ "demo-functional". Add a dedicated integration-auditor + red-teamer role.
- "Honest no-op" beats "complete but vapor" (perturb_contracts stub looked complete).
- Aspirational docs cost more than they save — make docs match code or fix code to match docs.
- Author self-validation never substitutes for an independent reviewer cohort gate.
- Parallel reviewer mutation-testing races with parallel reviewer reads — use git worktree isolation or serial dispatch.
- Dispatching two Builders editing the same production files concurrently is a coordination hazard — write to `/tmp` first or keep file scopes disjoint.

---

## Meta — skills produced by this project

- `.claude/skills/expert-review-loop` — multi-expert parallel-review-until-convergence.
- `.claude/skills/project-log` — this file's structure.
- `.claude/skills/design-team` v2 — Step-3 always-spawn-Supervisor + "Common shortcuts to refuse".
- `.claude/skills/feature-build-loop` v2 — design-team pairing hard-gate language.
- `.claude/skills/project-team` — apex orchestrator (used Phase 8/9).

If starting a comparable project, invoke before writing the first plan.

---

## Consolidated lessons

1. Multi-expert parallel review catches what generalists miss (~5–15 issues per specialist).
2. Brief reviewers with the prior round's verdict to keep convergence-focused.
3. WebFetch-verified API signatures are the only ground truth — don't write SDK code without a doc URL open.
4. Tests encode asymmetric-loss invariants — the single most valuable test asserts the safety promise.
5. Cutting features beats adding them.
6. Statistical honesty over slogans — pre-commit to publishing achieved numbers unmodified.
7. Reflector self-improvement loop is the wedge, not vertical M&A focus (Harvey/Kira have that).
8. Reviewer-validated ≠ demo-functional. Add integration-auditor + red-teamer roles.
9. Honest no-op beats complete-but-vapor.
10. Single-source-of-truth via runtime introspection (`typing.get_args(Tag)`) is cheaper than codegen.
11. Security defaults must fail closed, not open (`REFLECT_OIDC_AUDIENCE` was the cautionary tale).
12. "Designer × 2 + reviewer × 3" loop scales to infrastructure work (~90 min/issue).
13. Author self-validation is a structural shortcut — independent cohort gate required for docs as well as code.
14. Contrast claims must be mechanically tested at PR time.
15. Parallel reviewer mutation-testing requires worktree isolation.
16. The Fabricated-SDK-Signatures failure mode applies to design-system docs (and SEC accessions, eval enums, design tokens) — verify tech-stack/reference claims against the source file, not the brief.
17. `claude design` output is input-to-be-verified, not drop-in canonical — cross-reference shipped CSS against the README (they contradicted on the palette).
18. Hostile-juror critic role is load-bearing for juror-facing artifacts.
19. Pair every multi-round red-team with a convergence verifier as the LAST round.
20. Three-pass grep beats one-pass nested negative lookahead (PCRE lookaheads are syntactically fragile).
21. The bug can live at the contract layer, invisible to a style reviewer — a Code-quality GO does not substitute for a Bug-hunter lane. Keep full cohorts (goal-alignment + code-quality + bug-hunter [+ security]).
22. Recording-time pacing math: pick ONE model (split()-count vs spoken-equivalent vs staged-timestamp) and document both counts + the chosen model on every voiceover row.

---

## Per-file last-edit map (current — Phase 9 working tree, UNCOMMITTED past Phase 6.7)

```
plan.md                              v4.2 (Phase 7B website rewrite: §3.2/§4.1/§7/§8/§9/§11/§12/§15)
agent/schemas.py                     v5 (Phase 9: +ReflectorLoopEvent/Report/Kind; Phase 6.6 page+pdf_bbox)
agent/instrumentation.py             v2
agent/evaluators.py                  v3 (lru_cache)
agent/router.py                      v3 (3 annotations)
agent/agents.py                      v3.x (CLASSIFIER_TAGS re-export; Phase 8 Fix 7 Portfolio agent)
agent/prompts.py                     v3.2 (Risk Judge "DO NOT emit page/pdf_bbox" — server-only)
agent/reflector.py                   v8 (Phase 8 Fix 5: Hook-4 MCP-parsed introspection, _failing_traces fallback;
                                         v7 base: registry tuples + cross-loop skip + close() precedence)
agent/reflector_loop.py              v1 NEW (Phase 9 Build #3: LoopAgent wrap; hard-gate _call_mcp_list_traces;
                                         should_promote reuse-by-symbol; 720 LOC)
agent/server.py                      v10 (Phase 9: +POST /reflect/loop passcode-gated SSE; Phase 8 Fix 7 /portfolio;
                                         v9 Parser event-stream interception → clauses_by_id, server-side bbox join,
                                         pdfplumber fallback; v8 LRU cache + Files API TTL + /filing + frame lockdown)
agent/allow_list.py                  v2 (5 curated CIKs; field_validator zero-pad)
agent/pdf_bbox.py                    v1 (pdfplumber offline fallback; ThreadPoolExecutor max_workers=2, 5s timeout; 17 tests)
scripts/calibrate.py                 v5 (calibrate_all_headline_folds; dropped_headline_folds; one-sided Wilson +
                                         cluster bootstrap + real reliability; Fix 10 cluster-bootstrap = headline)
scripts/perturb_contracts.py         v3 (real: regex perturbations + TF-IDF/LogReg + 5-fold AUC)
scripts/eval_maud_mcq.py             v1 (MAUD-MCQ exact-match-per-category + degenerate AUPR; --live NotImplemented; 38 tests)
scripts/eval_cuad_spans.py           v1 (token-F1 strict>0.5 + paper>=0.5; AUPR; P@R=0.8/0.9; --live NotImplemented; 54 tests)
scripts/build_readme_table.py        v1 (three-track JSON → Markdown; CUAD flag regex vs source; CRLF-preserving
                                         splice; DEGENERATE_CAVEAT on AUPR row only; 40 tests)
scripts/verify_structural_reasoning.py  v1 NEW (Phase 8 Fix 6: --live SHIP/CUT gate for the structural beat)
scripts/annotate.py                  v2 (PrelabelSummary; PRELABEL_TAGS re-exports CLASSIFIER_TAGS)
scripts/seed_reflector.py            v1
scripts/verify_allow_list.py         v1 (D10 verify tool)
scripts/download_datasets.py         v1
tests/*                              ~20 files, ~376 tests (Phase 9 +11: reflector_loop 9 + e2e 2)
Dockerfile                           v2 (slim, non-root, $PORT)
requirements.txt                     v3 (+ scikit-learn)
.env.example                         v6 (Phase 9: +REFLECTOR_LOOP_AUTO_PR default=0; FILES_API_URI_TTL_SECONDS,
                                         MCP_ACLOSE_TIMEOUT_SECONDS, FILES_API_CACHE_MAX_ENTRIES, REFLECT_OIDC_AUDIENCE)
README.md                            v4 (Tag sync; calibration invariants; infra recovery)
HANDOFF.md                           v3 (canonical operator list)
docs/devpost.md                      v1.2 (Phase 8 Fix 9 honesty edit; pre-indexed wording; honest Files API)
docs/demo_script.md                  v2 (Phase 8 Fix 2/3/4: BMS cold-open, plain-English climax VO, 6s badge, $6.4B beat)
docs/post_poc_demo_script.md         v1 NEW (Phase 9: ≤90s Build-#3 VO + beat table + fallback matrix)
docs/internal30_deal_bank.md         v2 (Phase 8 Fix 1: Calibration-17 + Narrative-12 contamination split)
frontend/                            v5 (Phase 7A Tailwind Documentary-Brutalism tokens; globals.css/layout.tsx)
frontend/components/pdf-pane.tsx     v2 (Phase 6.7 bidirectional sync; pdfjs worker .min.mjs)
frontend/components/findings-pane.tsx  v3.1 (Phase 9 +reflector-loop-button mount; bg-lane-clear/15 STILL flagged for D15 sweep)
frontend/components/reflector-loop-button.tsx  v1 NEW (Phase 9: "Run Reflector now" + streamed ASCII-CI panel)
frontend/lib/{types,api}.ts          Phase 9 (+ReflectorLoopEvent/SseFrame; streamReflectorLoop SSE fetcher)
frontend/app/page.tsx                v2 (Phase 6.7 onSelect={setSelectedFindingId})
design/SOURCE_OF_TRUTH.md            v1 NEW (Phase 7: locked Documentary-Brutalism index + old→new revaluation)
design/WEBSITE_PLAN_UPDATE.md        v3 NEW (Phase 7B: 3-round red-team audit trail; NOT mutated into plan.md)
design/tokens.ts                     v3 (Phase 7A: Documentary-Brutalism palette; border-radius "0" everywhere)
design/tokens.test.ts                v3 (9→13 invariants: no warm-clay, border-radius 0, one easing, champagne/oxblood contrast)
design/claude-design-output/         v1 NEW (claude design workflow output)
design/{PLAN,TOOLING,INSPIRATION,COPY,STACK,SYSTEM,REVIEW_NOTES}.md  SUPERSEDED 2026-06-08 (banner-flagged)
design/HANDOFF.md                    v4 (cold-pickup read order: SOURCE_OF_TRUTH → claude-design-output)
.github/workflows/tests.yml          v3 (+ scikit-learn + matplotlib)
.claude/skills/{design-team,feature-build-loop}/SKILL.md  v2
```

---

## Phase 10 — Citation-linkage layer (2026-06-09)

Implements `design/STATUTE_LAYER.md` (Option C: deterministic citation map + internal LLM proposer graded in Phoenix + deterministic comparator). **The LLM proposer never reaches user-facing output — structurally enforced.** *Citations are pinned to primary sources, not generated.*

**What shipped (new files, LoC):**
- `data/citation_map.json` (161) — 15 primary-source-verified entries (11 statute + 4 named case-law anchors).
- `data/CITATION_MAP_SIGNOFF.md` (89) — audit trail, one row per entry.
- `data/citation_gold_v1.jsonl` (40) — frozen eval gold, independently sourced (Cornell LII + CUAD), 6 tags, balanced folds.
- `agent/citation_linker.py` (245) — sync `lookup_citation`, async `_call_linker_llm`, async fire-and-forget `_run_llm_proposer_and_annotate`, `_normalise` comparator, cached map loader, sync-fallback annotation writer.
- `tests/test_no_eval_leak.py` (262), `tests/test_citation_linker.py` (208), `tests/test_frontend_type_sync.py` (39), `tests/test_citation_map_freshness.py` (43).

**What shipped (changed files, additive):**
- `agent/schemas.py` — `CitationRef`, `LinkerProposal`, `_EVAL_ONLY_FIELDS`, 4 new `RiskFinding` fields, and the `model_dump` / `model_dump_json` / `model_dump_internal` overrides (Guard #2).
- `agent/server.py` — `_stream_findings` integration (span-id capture, sync lookup, `asyncio.create_task` proposer, `force_flush` + `flushed` plumbing, `exclude=_EVAL_ONLY_FIELDS` at emit); `_current_span_id` + `_force_flush_spans` helpers; `_BG_TASKS` strong-ref registry.
- `agent/prompts.py` — `CITATION_LINKER_PROMPT` (jurisdiction whitelist, JSON-only).
- `agent/evaluators.py` — `make_citation_validity_classifier` (LLM) + `make_citation_exact_match_classifier` (deterministic regex, NOT an LLM judge).
- `agent/reflector.py` — `_WRITABLE_DATASETS` += `citation-regressions`; composite citation gate in `should_promote` (optional kwargs, vacuous when absent); 3rd `_run_experiment_pairwise` vs `citation-gold-v1`.
- `frontend/lib/types.ts` — `CitationRef` interface + `citation_ref?` on `RiskFinding` (NO eval-only fields). `frontend/components/findings-pane.tsx` — `CitationRow` + dependency-free span-link glyph.
- `README.md` — §6.1 hooks 7→10 (Hook 10 labeled "NOT an LLM judge" verbatim).
- Tests updated to track spec-mandated changes: `tests/test_promotion_rule.py` (+4: allowlist + composite-gate block/pass/vacuous), `tests/test_introspection_agent.py` (writable-set invariant now includes `citation-regressions`, gold stays frozen), `tests/test_reflector_loop.py` (signature now 3 required + 2 optional kw-only).

**Three structural guards (load-bearing):** (1) `LinkerProposal` is a distinct class; (2) `RiskFinding.model_dump*` default-exclude `_EVAL_ONLY_FIELDS`; (3) SSE wire-output regression test. Verified: `linker_proposal`/`linker_agreement`/`linker_confidence` appear in **zero** SSE bytes (unit + full-stream integration), **zero** in the frontend. Cold path unchanged (proposer is `create_task` fire-and-forget; only the sync map lookup is on the user's path). The banned internal motto (STATUTE_LAYER.md §4.5) appears in **zero** code/comments/docs/strings added by this phase.

**Test results:** full suite **435 passed, 2 skipped** (`--ignore` the matplotlib-gated plotting module). New: `test_no_eval_leak` (6), `test_citation_linker` (11), `test_frontend_type_sync` (2), `test_citation_map_freshness` (2), promotion-gate (4). `tsc --noEmit`: my two frontend files are **error-free** (the 3 tsc errors are all pre-existing in `tailwind.config.ts`, a design-track file modified before this session).

**5 pre-existing failures (NOT introduced here, proven against HEAD):**
- 4× `test_calibration_invariants` + 1 collection error in `test_render_climax_plots` → `matplotlib` not installed in `.venv` (it IS in `requirements.txt` line 49 — incomplete venv install). Those test files were modified pre-session; they shell out to `calibrate.py`/plotting, untouched here. Fix: `pip install -r requirements.txt`.
- `test_env_documented` → **passes at HEAD** (verified via a detached worktree); fails in the working tree because the pre-session `.env.example` edit dropped `REFLECTOR_LOOP_MAX_ITERATIONS` + `REFLECTOR_LOOP_USE_REAL_ADK` (read in `reflector_loop.py`, a file untouched here). I add no new env vars and am barred from editing `.env.example` — **user action**: re-add those two keys to `.env.example`.

**SIGNOFF audit summary:** 15/15 entries primary-source-verified via WebFetch — 7 via Cornell LII (15 U.S.C. §§ 18/18a/1060, 35 U.S.C. § 261, 17 U.S.C. § 204, U.C.C. §§ 9-406/2-210), 2 via delcode.delaware.gov (8 Del. C. §§ 251/271), 1 via nysenate.gov (N.Y. BCL § 902), 1 via leginfo.ca.gov (Cal. B&P § 16600); 4 case-law anchors — Akorn & Trados read directly from the courts.delaware.gov opinion PDFs (true primary source), Revlon via Penn Carey Law, AB Stable via the Fox Rothschild Delaware-Chancery blog + multi-source reporter corroboration. The Akorn placeholder is resolved: Chancery merits = 2018 WL 4719347, aff'd 198 A.3d 724.

**Deviations from spec (with reason):**
- **Map size 15, not ~25.** Correctness-first per hard-constraint #7 + §4.4 failure-path ("does NOT ship a partially-unverified map"). Omnicare/Hexion (non-named extras) dropped — their fetchable opinion pages 403'd (Justia/FindLaw) this session; not cited from memory. `accelerated_vesting` intentionally omitted (contract-anchored → graceful `None`, the §2.6 test). Expansion is mechanical once fetchable pages are available.
- **`jurisdiction_hint`** — §2.1's snippet calls `lookup_citation(finding.tag, finding.jurisdiction_hint)`, but §2.2 never adds that field (4 fields only). Resolved: `lookup_citation(tag, jurisdiction_hint=None)` defaults to the map's canonical per-tag entry; the server calls `lookup_citation(finding.tag)`.
- **No new `CITATION_LINKER_MODEL` env var** — reuses the already-documented `GEMINI_MODEL` to respect the `.env`-edit prohibition + the env-doc CI gate. (Spec mentioned Flash for the proposer; swap via `GEMINI_MODEL`.)
- **`_run_llm_proposer_and_annotate(..., flushed=...)`** — §2.4's snippet omits the param, but hard-constraint #6 (sync=True fallback on `force_flush`→False) requires it. Added; `router._annotate` reused unchanged for the async path, sync path writes directly with `sync=True`.
- **3rd experiment scorer** — per instruction, reuses `_run_experiment_pairwise` as-is (faithfulness scorer) rather than wiring `citation_exact_match` into it (that helper is out-of-scope to modify). The deterministic `citation_exact_match` evaluator is exposed via `evaluators.py` for Phoenix `run_evals`/UI; the composite-gate plumbing + formula are exact.
- **Component named `CitationRow`** (spec wrote `<CitationCitationRow>`, a doubled-word typo) for readability. `lucide-react` not installed → inline SVG arrow-up-right.

**Remaining (deferred per spec):** κ inter-rater pass; `citation_faithfulness` evaluator; real-attorney sign-off; map expansion toward ~25. No code remaining for Phases A–F — all complete. Not committed (left staged for user review per house rule).

---

**Naming decision (2026-06-09).** Product brand/display name chosen: **Cautela** (Latin: prudent precaution / conservative gatekeeping doctrine), replacing the descriptive working name "M&A Gatekeeper". Selected by the user from a multi-agent naming run (48 candidates → 14 shortlist → 4 judge personas: M&A GC, brand strategist, trademark-collision skeptic, hackathon judge). Judge-panel top pick was "Plumb" (rejected: homophone risk); "Caveat" was runner-up (rejected: *Caveat Legal* collision). `ma_gatekeeper/` directory and all code identifiers intentionally NOT renamed — brand/display-name only; surfaces still to update on wire-in: README title, `docs/devpost.md` title/tagline.

---

*End of project log — last revised 2026-06-09 (condensed; full audit trail in `PROJECT_LOG.archive.md`). Latest work = Phase 10 (citation-linkage layer — deterministic map + Phoenix-graded internal proposer; 15 primary-source-verified citations; 3 structural guards; +25 tests; Arize hooks 7→10). Phase 9 (Reflector-as-LoopAgent Build #3 + §12 demo button, 4/4 reviewer GO, ~376 tests). **Everything past commit `f998386` (Phase 6.7) is uncommitted working-tree state** — Phase 7 design-system regen, all 10 Phase-8 FIX_PLAN fixes, Phase-9 Build #3. Canonical design system = `design/claude-design-output/` (Documentary Brutalism), indexed from `design/SOURCE_OF_TRUTH.md`; Phase-5 design lock SUPERSEDED. Submission window is T-48h (D22). Contrast-lie + fabricated-external-reference patterns are mechanically tested at PR time.*
