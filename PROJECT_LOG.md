# Project Log — M&A Due Diligence Gatekeeper

**Hackathon**: Google Cloud Rapid Agent Hackathon — Arize partner track.
**Deadline**: 2026-06-11. **Started**: 2026-05-19. **Updated**: 2026-06-05.

---

## TL;DR

Vertical M&A contract-review agent (Gemini 3 Pro + Google ADK + Arize Phoenix on Cloud Run). Two tracks:

- **Product** (`ma_gatekeeper/`): 10 Python modules + 7 scripts; **365/365 tests passing under CI deps** (was 325 at Phase 6.6 close; +40 from Phase 6.7 build_readme_table); CI green on 3.11+3.12; end-to-end demo path functional on the 5 curated CIKs; PDF↔trace bidirectional sync now wire-side complete in the frontend (forward overlay + reverse click hit-test).
- **Design** (`design/`): Phases 0–5 converged through `design-team` skill — TOOLING / INSPIRATION / COPY / STACK / SYSTEM / tokens.ts all VALIDATED by independent 3-reviewer cohorts (after Day-4 author-self-validation gap was closed).

Wedge: experiment-gated prompt promotion with frozen-fold non-regression (the Reflector loop). Outstanding work is operator-side per `HANDOFF.md`.

---

## Operating constraints

- Never `git commit` / `git push` unless explicitly asked. Stage/diff/status OK on request.
- No `Co-Authored-By: Claude` trailer.
- Two tracks: default to `ma_gatekeeper/`; touch `design/` only on explicit ask.
- SEC EDGAR identity: hugo.majerczyk@proton.me.

---

## Current code state

**Modules**: schemas, instrumentation, evaluators, router, agents, prompts, reflector, server, allow_list, pdf_bbox.
**Scripts**: download_datasets, perturb_contracts (real TF-IDF/LogReg discriminator), calibrate, annotate, seed_reflector, verify_allow_list, eval_maud_mcq, eval_cuad_spans, build_readme_table.
**Tests (365)**: pure-Python, no live API calls; per-file in `pytest --collect-only`. Local-only runs without optional deps (pydantic etc.) collect 313 — full 365 requires CI's pinned requirements.
**Frontend**: Next 14.2.5 + react-pdf 9.1.1 + pdfjs-dist 4.4.168; PDF↔trace bidirectional sync wired (forward = lane-tinted bbox overlay + page scroll; reverse = click→PDF-coord→hit-test→`onSelect`).
**Infra**: Dockerfile slim+non-root+$PORT-aware; Apache 2.0 LICENSE; CI runs pytest on 3.11+3.12 with fastapi+httpx+pydantic+numpy+pandas+scikit-learn+matplotlib+opentelemetry-api.

**End-to-end demo path (works on 5 curated CIKs)**:
- Allow-list: Microsoft/Activision, Pfizer/Seagen, Cisco/Splunk, ExxonMobil/Pioneer, HPE/Juniper. Operator runs `scripts/verify_allow_list.py` before D19 to confirm live EDGAR resolution.
- `/filing/{deal_id}` serves EDGAR Ex 2.1 with sniffed Content-Type (HTML or PDF), cached.
- `trace_id` populated server-side from active OTel span; frontend deep-links into Phoenix trace.
- Gemini: inline `Part.from_bytes` <8MB, Files API + `Part.from_uri` above (TTL-evicted 36h, LRU-capped 64 entries).
- MCP introspection: subprocess registry with cross-loop detection + lifespan drain + atexit hook.
- Tag enum: single source of truth via `typing.get_args(Tag)`; CI fails on cross-file drift.
- `/reflect` OIDC fail-closed on Cloud Run; `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` on all routes.

---

## Outstanding work (HANDOFF.md, 3-week timeline)

| Days | Phase | Outputs |
|---|---|---|
| D1–D2 | Phoenix infra | Self-hosted Cloud Run + iframe (killed Day-1; mock-only) |
| D3 | ADK skeleton | Vertex quota request |
| D4 | Parser | Gemini 3 Pro + Files API + `Clause.pdf_bbox` |
| D5–D9 | Annotation + calibration | 30 contracts → `Internal-30`; 5-fold CV; τ_h, τ_f |
| D10 | Allow-list | Run `verify_allow_list.py` |
| D11–D14 | Reflector loop | MCP introspection + experiment + promotion |
| D15–D17 | Frontend | PDF↔trace bidirectional sync **shipped (Phase 6.7)**; sparklines + UX redesign still outstanding |
| D18 | Pre-seed + README polish | 48h Reflector pre-seed; results-table generator **shipped (Phase 6.7)**, awaits operator-added README markers + post-calibration `--update-readme` run |
| D19 | Recording | 3-min demo + EDGAR fallback pre-record |
| D20 | Submission | Devpost form + Cloud Run warming |
| D21 | Buffer | 24h verify before deadline |

**User-action queue**: `npm install` in `frontend/` for lockfile (unblocks size-limit CI); Playwright MCP install (unblocks Phase-1 screenshot capture + contrast field-verification); COPY.md placeholders (`<<CONTACT-EMAIL>>`, `<<TOS-URL>>`, `<<GOVERNING-LAW>>`, `<<DEMO-DEAL-1..5>>`); GC-persona legal review of COPY §6/§11.

---

## Hard-to-reverse decisions

### Product
- Threshold τ_h, τ_f via 5-fold CV; fold 5 frozen as Reflector non-regression held-out. ε = max(SE_fold5, 0.03).
- One-sided Wilson LB (z=1.6449); cluster bootstrap over contracts (one-sided α=0.05).
- Independent gating per evaluator (hallucination AND faithfulness) — never averaged.
- Three Phoenix annotations: `hallucination`, `clause_faithfulness`, `risk_judge_gate`.
- 30 contracts in Internal-30 (LLM-assist + κ on 10-contract double-annotated subset).
- 5 demo deals (no open ticker box); pre-validated to surface Block-tier findings.

### Design (Day-3/4 locks)
- **Color split**: `--brand-primary #0F4A38` decorative-only (≤5% viewport); `--text-interactive #4A9D7E` for all interactive surfaces (4.51:1+). Lanes: `--lane-clear #3F7A5A`, `--lane-escalate #C49A3A`, `--lane-block` aliased to `--accent-clay #B86F3D`. Neutrals cool-green-tinted 10-step; light-mode `#FBFAF5 / #0E1311`.
- **Typography Lane A (default Option B)**: Fraunces (display) + Inter Variable (body) + JetBrains Mono (mono) — all OFL.
- **Motion grammar**: one easing `cubic-bezier(0.16,1,0.3,1)`; three durations 150/400/800ms; 60ms stagger; one named exception (1800ms moneymoment unfurl); Reflector single-rotation (no infinite); `prefers-reduced-motion` universal.
- **Animation runtime**: Framer primary, GSAP scoped to §6.4 only (~70KB gz total, fits 180KB above-fold budget), raw SVG + CSS. No Rive, R3F, Lottie, ReactFlow.
- **Wordmark**: `M&A Gatekeeper` in Fraunces 600, opsz 90, letter-spacing -0.01em. No symbol.
- **Framework**: Next 14.2.5 pinned (Astro fallback only if Day-4 LCP > 2.8s).
- **Weird-lift invariants enforced at token layer**: `brand-blue` deliberately undefined; no `.stat-card` preset. Asserted in `tokens.test.ts`.
- **Iframe kill-switch fired**: mock-only path for moneymoment (Day-1 Safari ITP spike couldn't run from agent context).
- **COPY §2 tagline**: cadence-led "Every flag, sourced. Every verdict, traced. Every span, clickable." promoted to hero; PLAN §2.1 line preserved verbatim in sub-line + §15 OG.

---

## Pre-commitments locked

- Publish achieved Block-recall Wilson LB unmodified (even if below 0.95).
- Demo voiceover: "five pre-indexed deals" (no "recently indexed").
- Reflector pre-seeding disclosed in README + Devpost ("production prompt deliberately seeded weaker 48h before demo").
- Three-track eval table in README (MAUD-MCQ, CUAD-Spans, Internal-30).
- Apache 2.0 LICENSE in repo About sidebar.
- Arize track checkbox in Devpost.

---

## Scope cuts (each survived a reviewer)

- 2 extensions (was 8): Playbook customization, HITL annotation.
- 30 contracts (was 60): annotation budget honest at 15–25h.
- 5 demo deals (was open ticker).
- 2 evaluators only (hallucination + faithfulness).
- No A2A protocol (single-team submission).
- No multi-language contract support.
- No live integration tests (lock test suite to network).
- Files API expiry recovery: TTL eviction only; no probe-on-hit or retry-on-call (SSE duplicate-finding risk).

---

## Phase history (condensed)

- **Phase 0**: Idea synthesis — Document Review Gatekeeper × M&A domain.
- **Phase 0.5**: 4 parallel research agents (market/competitors, Phoenix, datasets, GCP+ADK). Key findings: CUAD CoC SOTA ~70-80% F1 (not 95%); Phoenix MCP can't launch experiments or write annotations (Python SDK only); AX Online Eval Tasks SaaS-only (use Cloud Scheduler + `run_evals`); EdgarTools MCP confirmed; 30-contract annotation = 15-25h.
- **Phase 1**: Plan v1→v4 across 4 review rounds with 4 specialist reviewers. Final v4 converged unanimously. Key fixes: dropped fantasy stats; "100% precision" → "Wilson LB at published abstention rate"; independent gating per evaluator (not averaged); paired bootstrap CI + frozen fold-5 for promotion rule; 5-fold CV; PDF bbox stashed at D4 not D15.
- **Phase 2**: Scaffolding (8 modules, 23 tests). Believed correct — was wrong.
- **Phase 3**: 5 specialist code reviewers across 4 rounds. Caught ~15 fabricated SDK signatures (Phoenix, ADK, google-genai), wrong stats (alpha/2 instead of alpha, z=1.96 instead of 1.6449, parametric instead of cluster bootstrap), security gaps (open `/reflect`, query-string passcode, fail-open OIDC). All 5 VALIDATED by round D.
- **Phase 4**: Feature buildout (annotation pipeline, LICENSE, CI, D18 seed, Next.js skeleton, Devpost draft). Each task own multi-reviewer loop. 70 tests at end.
- **Phase 5**: 10-reviewer full-project audit (3 simulated judges + 7 specialists). Found end-to-end demo path broken in 4 distinct ways despite Phase-3 "VALIDATED" state: empty allow-list CIKs, missing `/pdf-proxy`, unpopulated `trace_id`, EdgarTools HTML labeled as PDF. Plus `perturb_contracts.py` was vapor (stub returning unchanged text + hardcoded AUC=0.5), silent OIDC bypass on Cloud Run, asyncio.get_event_loop() bug, Tag enum 4× replication, Files API not wired. Shipped 10 prioritized fixes through designer×2 + reviewer×N loop. 151 tests.
- **Phase 6**: Tier-2 follow-ups — E10 5 quiet-downgrade tests (Wilson pins, bootstrap quantile, require_recall=1.0, plot_reliability content, dropped-fold disclosure); Files API 48h URI expiry (TTL eviction); MCP process-shutdown hook (registry + atexit). 196 tests.
- **Phase 6 honesty pass**: User caught 7 shortcuts (manually orchestrated, outsourced mutation testing, dismissed R1 without verifying, skipped R2 gaps, skipped R1 minors, only re-ran R3, parallel reviewer race). Closed each. R4 bug-hunter + R5 security + R6 WebFetch verifier caught 4 production bugs: unbounded `_files_api_locks` (→ LRU cap), cross-loop aclose hazard (→ `(toolset, loop)` tuple skip), wrong `StdioServerParameters` import (→ split to `mcp` package), `aclose` vs `close` precedence. 208 tests.
- **Design Phases 0–5**: TOOLING (Round-B 4/4 VALIDATED mean 8.75); INSPIRATION (challenge round 3/3 VALIDATED via design-team); COPY (retroactive design-team pipeline 2/2 R1); STACK + SYSTEM + tokens.ts (FA 9/10 + AD 9/10 + Motion locked + feature-build-loop 3/3 GO in 2 rounds + Supervisor reconciled).
- **Design Day-4 author-self-validation gap**: User caught that Phase 4/5 had self-validated only. Spawned 3-reviewer cohorts retroactively per doc + tokens.ts. Caught 3 critical: SYSTEM accessibility math errors (1.89:1 actual where 4.5:1 claimed), fabricated SOC2/pen-test dates in COPY §6, self-contradiction §11.5 vs §6. Plus tokens.ts R1 caught the same contrast-lie pattern (`text-on-accent-clay` 3.59:1 where verified claimed). Converged 3/3 GO across docs + tokens after 3 rounds + Supervisor Step-3 reconciliation.
- **Phase 6.6 — Gaps #1–4 closure (2026-05-27, audit follow-up)**: user asked "isn't there other things left to code?" after Phase 6.5 — surfaced four real code gaps via an honest audit: (1) MAUD-MCQ eval script never written, (2) CUAD-Spans eval script never written, (3) PDF bbox extraction had schema + prompt + pdfplumber-in-requirements but no production code path, (4) SSE never threaded `page`/`pdf_bbox` to the frontend. Plan §5.2 + §12 committed to all four; only Internal-30 had tooling. Two feature-build-loops ran in sequence. **Loop A (eval scripts)**, 2 rounds: Builder A + B in parallel writing to `/tmp`; synthesis took Builder B's defensive picks; R1 reviewers caught critical gaps the WebFetch reviewer surfaced (test `/tmp` shim that broke CI, HF dataset schemas don't match the script's expected shapes, plan §5.2 metric definitions diverge from cited MAUD + CUAD papers); user decided to ship both paper + project metrics side-by-side + write HF adapters inline; R2 fix Builder applied all 15 must-fixes; R2 reviewers 3/3 GO. **Loop B (PDF bbox + SSE)**, 1 round: Builder A (pragmatic prompt-thread) + Builder B (defensive server-side join) in parallel editing the same production files — they organically reconciled toward Builder B's approach mirroring plan §4.3's `trace_id` "server-side-populated, NEVER by the LLM" precedent; R1 reviewers 3/3 GO with bug-hunter verifying mock fidelity against real pdfplumber 0.11.9. Final test count 208 → 325 (+117). New files: `scripts/eval_maud_mcq.py` (763 lines, 38 tests), `scripts/eval_cuad_spans.py` (1231 lines, 54 tests), `agent/pdf_bbox.py` (218 lines, 17 tests). Lessons: **dispatching two Builders editing the same production files concurrently is a coordination hazard** — Loop A correctly wrote to `/tmp` first, Loop B incurred a synthesis-during-build merge that mostly worked but Builder A self-flagged the deviation. **WebFetch reviewer caught fabricated dataset schemas + fabricated metric definitions** — exact same failure-mode class as the project's catalogued "Fabricated SDK signatures" pattern, translated to dataset + paper specs. Two follow-up items deferred to user: README results-table generator referencing the new JSON shape fields (`aupr_overall`, `aupr_degenerate`, `f1_paper`, `f1_strict`, `p_at_r_0_8`, `p_at_r_0_9`); CUAD apostrophe-parsing latent edge case in `_extract_clause_phrase_from_question` (not triggered by canonical CUAD-QA template).

- **Phase 6.7 — D15 frontend wedge + D18 README results-table generator (2026-06-04, audit follow-up #2)**: user pushed back on the D15 + D18 readiness claim from the prior audit ("are you sure that there really is nothing more to be done on the coding part?"). An honest re-audit (delegated to Explore) surfaced two genuinely-load-bearing gaps that HANDOFF + PROJECT_LOG had glossed: (a) the README results-table generator promised at plan §5.2 + §12 didn't exist (HANDOFF L308 flagged but never resourced), and (b) the reverse direction of the PDF↔trace sync that plan §9 L458 calls "the single differentiating interaction" was stubbed in `pdf-pane.tsx:26` (forward-only — reverse explicitly deferred). User directive: run both as parallel feature-build-loops, cohort-gated. Two tracks dispatched concurrently (safe per Phase 6.6 lesson — disjoint file scopes: scripts/ + tests/ vs frontend/). **Track 1 (README generator)**, 2 rounds: R1 Builder shipped `scripts/build_readme_table.py` (501 lines) + `tests/test_build_readme_table.py` (28 tests) with stdlib-only + 3-track table + degenerate-AUPR caveat + P@R fallback surfacing. R1 cohort: Goal-alignment ITERATE (2 must-fixes: CUAD baselines silently dropped from `_build_cuad_rows`; DEGENERATE_CAVEAT wrong-shape on MAUD accuracy-vs-baseline rows), Code-quality GO, Bug-hunter ITERATE (6 must-fixes — sharpest: **FABRICATED CUAD `flag` enum** — code asserted `{"ACHIEVED", "FALLBACK_TO_MAX"}` but `eval_cuad_spans.py:107-114, :620` actually emits `None` for achieved + `f"recall_{target}_unachieved"` for unachieved, AND the test fixtures at `:82-83` baked in the fake values so the 28-green count was meaningless for that code path; plus off-by-one in `splice_into_readme` end-before-begin check, JSON-null rendered as literal string "None", CRLF→LF silent conversion on `--update-readme`, README-missing-markers exit path undocumented). R2 fix-Builder applied all 8 (deleted `_P_AT_R_OK_FLAGS`, added module-level `_FLAG_UNACHIEVED_RE = re.compile(r"^recall_[0-9.]+_unachieved$")` + `_flag_is_achieved`/`_flag_is_unachieved` predicates; mirrored MAUD baselines block for CUAD with paper-§3-appropriate Note; moved DEGENERATE_CAVEAT off baseline rows back onto the AUPR row only and split the prior combined test into two; `splice_into_readme` rewritten as `read_bytes()`/`write_bytes()` round-trip preserving CRLF byte-for-byte; null-coalescing for `effective_n_contracts`/`n_evaluated`/`n_total_examples`; argparse help + ValueError now explicitly document D18 marker prerequisite). Net deltas: build_readme_table.py 501→607 (+106), tests 495→729 (+234), 12 new tests + 3 rewritten (40/40 pass). R2 cohort 3/3 GO with Bug-hunter explicitly verifying regex against `eval_cuad_spans.py:107-114, :620, :553` source. **Track 2 (reverse PDF↔trace sync)**, 2 rounds: R1 Builder edited `pdf-pane.tsx` (109→270, +161) + `app/page.tsx` (143→148, +5) — bidirectional sync wired via shared `selectedFindingId` state, forward path scrolls to `finding.page` + renders lane-tinted bbox overlay (`bg-lane-{clear,escalate,block}/30`) via `viewport.convertToViewportPoint`, reverse path translates click CSS-px → PDF-coords via `viewport.convertToPdfPoint`, hit-tests rows on current page, smallest-area + lexicographic-clause_id tie-break; `cancelled`-guarded dynamic import preserved; PDF y-flip handled by pdfjs API not manual subtraction. R1 cohort: Goal-alignment GO (plan §9 promise + HANDOFF L161-164 "reverse sync deferred" gap closed), Code-quality GO, Bug-hunter ITERATE 1 must-fix — **FABRICATED pdfjs worker path**: `pdfjs-dist/build/pdf.worker.min.js` doesn't exist in pdfjs-dist@4.4.168 (ESM-only — only `.mjs` workers ship), AND the in-file comment justified `.min.js` on the grounds that `.mjs` "breaks under webpack5" which is also fabricated (react-pdf v9 README explicitly recommends `.min.mjs` for pdfjs 4.x). R2 fix-Builder applied the surgical `.min.js`→`.min.mjs` swap + rewrote the surrounding 7-line comment to drop the fabricated rationale and cite the react-pdf README. R2 cohort 3/3 GO with Bug-hunter verifying via unpkg listing (`pdf.worker.min.mjs` 1.36 MB present in `build/`). Lessons: **the "Fabricated SDK signatures" failure-mode class has zero discipline transfer between domains** — Phase 3 caught fabricated Phoenix/ADK Python signatures; Phase 6.5 caught fabricated Phoenix UI affordances; Phase 6.6 caught fabricated HF dataset schemas; Phase 6.7 caught a fabricated CUAD-eval-flag enum (Python-Python, internal contract) AND a fabricated pdfjs worker filename (TS-bundler, external SDK). Same pattern, four different layers. Track 1 also surfaced the **enshrined-fabrication-via-test-fixtures meta-pattern**: when production code and test fixtures share an invented value, green CI is structurally lying. Bug-hunter caught it only by cross-reading against `eval_cuad_spans.py`. **Cohort-level value confirmed again**: Code-quality reviewer's GO on R1 was correct (the code IS clean — the fabrication is at the contract layer, invisible to a style reviewer); the gap was Bug-hunter's lane specifically. Two follow-ups deferred to D18: (1) operator must add `<!-- BEGIN_RESULTS_TABLE --><!-- END_RESULTS_TABLE -->` markers to `README.md` then run `python -m scripts.build_readme_table --update-readme README.md` after Internal-30 calibration completes; (2) sparklines on findings cards (plan §9 calls them out — separate small feature, not in this loop's scope).

- **Phase 6.5 — E9 demo script (2026-05-27, deferred from Phase 5)**: feature-build-loop, 5 rounds total. Builder A (pragmatic) + Builder B (defensive) → synthesis → 3-reviewer cohort (Goal-alignment, Code-quality, Bug-hunter). R1: Goal-alignment GO; Code-quality + Bug-hunter ITERATE with 13 consolidated must-fixes. Sharpest R1 catches: voiceover Python-count drift (claimed 79, actually 81; cascade-broke 30s pacing math), caption silently dropped `auto-promotion` + `itself` from canonical devpost.md L218–219 disclosure (would've shown freeze-frame-divergent text from the linked Devpost description), cross-deliverable timing contradiction (caption in-point 2:30 vs beat-table MCP-fire ~2:35), non-functional Tailwind composition (no opacity state), dropdown-label citation used spelled-out form where plan.md §5.5 L250 locks the numeral form. R2: Goal-alignment GO, Bug-hunter GO, Code-quality ITERATE with 2 surgical must-fixes (residual harness vocab + 22→21 word-count drift). R3: applied inline (3-line edit), Code-quality GO — converged. **Then** user asked "did you do any shortcuts. Be honest." Self-confessed 6 shortcuts; spawned an adversarial audit agent that WebFetched Phoenix docs and found shortcut #4 (Phoenix UI affordances unverified) was real and project-killing: the climax beat claimed Phoenix renders paired-bootstrap CI plots + score-delta plots + ε pills that Phoenix docs do not document. Same failure mode as PROJECT_LOG.md "Fabricated SDK signatures", translated from SDK to UI. R4: applied inline 4-edit fix (L155/L156/L157/L167) replacing fabricated affordances with Reflector log output + Phoenix experiments table + prompts-list view + optional matplotlib reliability PNG from `scripts/calibrate.py:184`. Dispatched full 3-reviewer cohort despite user OK'ing scoped review. Goal-alignment + Code-quality GO; Bug-hunter caught 3 NEW fabrications I'd introduced while fixing the original: used MCP-tool name `add-prompt-version-tag` instead of actual SDK log line `PROMOTED candidate ... → tag=production`, missed updating L112 caption in-point trigger to match, cited wrong function (`:610` `_upsert_prompt` = candidate-creation, not `:753` `_promote_candidate` = production-tag flip). R5: applied 3 surgical fixes inline (corrected log-line literals + L112 sweep + `:610`→`:753` citation), dispatched full cohort, all 3 GO. Artifact: `ma_gatekeeper/docs/demo_script.md` (199 lines, expanded L157 with verbatim log-line citations). All three voiceover locks preserved through every round. **Lesson**: dispatching the full cohort on round-4 inline fixes was load-bearing — Bug-hunter caught fabrications I'd silently introduced while fixing the audit-flagged fabrications. Self-confessed shortcut #1 (scoping cohort in round 3) was defensible per the audit; the same scoping would have shipped 3 new fabrications in round 4 if I'd scoped again.

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

### Asymmetric-loss invariants (encoded in tests)
- Hallucinated explanation cannot auto-clear at high faithfulness (`test_router.py`).
- Reflector cannot write to frozen fold 5 (allowlist enforced).
- Promotion requires paired bootstrap CI LB > 0 AND non-regression on fold 5 with ε floor.
- Wilson LB by-(k,n) pinned values catch z=1.6449 → 1.96 silent regression (margin >0.030).
- Block-tier classification cannot be modified by Reflector promotion path.

### Contrast-lie pattern (design)
Light text on warm-mid colors "reads readable" but math-fails. Mechanical contrast tests at PR time (`tokens.test.ts` tests 4–9) catch this.

### Process traps
- "Reviewer-validated" ≠ "demo-functional". Add a dedicated integration-auditor + red-teamer reviewer role.
- "Honest no-op" beats "complete but vapor" (perturb_contracts stub looked complete).
- Aspirational docs cost more than they save — make docs match code or fix code to match docs.
- Author self-validation never substitutes for independent reviewer cohort gate.
- Parallel reviewer mutation-testing races with parallel reviewer reads — use git worktree isolation or serial dispatch.

---

## Meta — skills produced by this project

- `.claude/skills/expert-review-loop` — multi-expert parallel-review-until-convergence.
- `.claude/skills/project-log` — this file's structure.
- `.claude/skills/design-team` v2 — Step-3 always-spawn-Supervisor rule + "Common shortcuts to refuse" section after 3 bypass incidents.
- `.claude/skills/feature-build-loop` v2 — design-team pairing hard-gate language.

If starting a comparable project, invoke before writing the first plan.

---

## Consolidated lessons

1. Multi-expert parallel review catches what generalists miss (~5–15 issues per specialist).
2. Brief reviewers with prior round's verdict to keep convergence-focused.
3. WebFetch-verified API signatures are the only ground truth — don't write SDK code without a doc URL open.
4. Tests encode asymmetric-loss invariants — the single most valuable test is the one that asserts the safety promise.
5. Cutting features beats adding them.
6. Statistical honesty over slogans — pre-commit to publishing achieved numbers unmodified.
7. Reflector self-improvement loop is the wedge, not vertical M&A focus (Harvey/Kira have that).
8. Reviewer-validated ≠ demo-functional. Add integration-auditor + red-teamer roles.
9. Honest no-op beats complete-but-vapor.
10. Single-source-of-truth via runtime introspection (`typing.get_args(Tag)`) is cheaper than codegen.
11. Security defaults must fail closed, not open (`REFLECT_OIDC_AUDIENCE` was the cautionary tale).
12. "Designer × 2 + reviewer × 3" loop scales to infrastructure work (~90 min/issue).
13. Author self-validation is a structural shortcut — independent cohort gate is required for docs as well as code.
14. Contrast claims must be mechanically tested at PR time (WCAG formula in `tokens.test.ts`).
15. Parallel reviewer mutation-testing requires worktree isolation.

---

## Per-file last-edit map (current)

```
plan.md                                          v4.1 (Phase 5 §8 rewrite)
ma_gatekeeper/agent/schemas.py                   v4 (Phase 6.6: RiskFinding.page + .pdf_bbox
                                                     server-side populated; trace_id precedent)
ma_gatekeeper/agent/instrumentation.py           v2
ma_gatekeeper/agent/evaluators.py                v3 (lru_cache)
ma_gatekeeper/agent/router.py                    v3 (3 annotations)
ma_gatekeeper/agent/agents.py                    v3.1 (CLASSIFIER_TAGS re-export)
ma_gatekeeper/agent/prompts.py                   v3.2 (Phase 6.6: Risk Judge "DO NOT emit
                                                     page/pdf_bbox" — server-only fields)
ma_gatekeeper/agent/reflector.py                 v7 (registry tuples + cross-loop skip + close() precedence)
ma_gatekeeper/agent/server.py                    v9 (Phase 6.6: Parser event-stream interception
                                                     builds clauses_by_id; server-side join overrides
                                                     LLM page/pdf_bbox; pdfplumber fallback for PDFs;
                                                     fail-loud join_clause_to_finding SSE)
ma_gatekeeper/agent/server.py                    v8 (OrderedDict LRU cache + matching lock eviction;
                                                     Files API TTL via _cache_get_live;
                                                     _sniff_mime; /filing; _build_gemini_part;
                                                     unified SSE finding event; loud validate failure;
                                                     _current_trace_id; lifespan CIK + OIDC + shutdown_all_toolsets;
                                                     _frame_lockdown middleware)
ma_gatekeeper/agent/allow_list.py                v2 (5 curated CIKs; field_validator zero-pad)
ma_gatekeeper/scripts/calibrate.py               v5 (extracted calibrate_all_headline_folds;
                                                     dropped_headline_folds/headline_folds_present surfaced;
                                                     one-sided Wilson + cluster bootstrap + real reliability)
ma_gatekeeper/scripts/perturb_contracts.py       v3 (real impl: regex perturbations + TF-IDF/LogReg + 5-fold AUC)
ma_gatekeeper/scripts/eval_maud_mcq.py           v1 (Phase 6.6: MAUD-MCQ exact-match-per-category
                                                     + degenerate AUPR; HF schema adapter;
                                                     comparison_baselines via --baselines path;
                                                     mock-default, --live raises NotImplementedError;
                                                     38 tests)
ma_gatekeeper/scripts/eval_cuad_spans.py         v1 (Phase 6.6: CUAD-Spans token-F1 strict (>0.5)
                                                     + token-F1 paper (>=0.5 + punct-strip),
                                                     AUPR (sklearn), P@R=0.8 + P@R=0.9,
                                                     dynamic FLAG, SQuAD adapter; mock-default,
                                                     --live raises NotImplementedError; 54 tests)
ma_gatekeeper/scripts/build_readme_table.py      v1 (Phase 6.7: thin generator picking three-track
                                                     JSON fields → Markdown table; stdlib-only;
                                                     CUAD flag enum regex against eval_cuad_spans
                                                     source-of-truth; CRLF-preserving bytes
                                                     splice; DEGENERATE_CAVEAT scoped to AUPR
                                                     row only; 40 tests)
ma_gatekeeper/agent/pdf_bbox.py                  v1 (Phase 6.6: pdfplumber offline fallback;
                                                     module-level ThreadPoolExecutor(max_workers=2)
                                                     with 5s per-call timeout; returns None on
                                                     every bad-input path; 17 tests)
ma_gatekeeper/scripts/annotate.py                v2 (PrelabelSummary; PRELABEL_TAGS re-exports CLASSIFIER_TAGS)
ma_gatekeeper/scripts/seed_reflector.py          v1
ma_gatekeeper/scripts/verify_allow_list.py       v1 (D10 verify tool)
ma_gatekeeper/scripts/download_datasets.py       v1
ma_gatekeeper/tests/*                            18 files, 365 tests (Phase 6.7: +test_build_readme_table 40)
ma_gatekeeper/Dockerfile                         v2 (slim, non-root, $PORT)
ma_gatekeeper/requirements.txt                   v3 (+ scikit-learn)
ma_gatekeeper/.env.example                       v5 (REQUIRED/OPTIONAL header;
                                                     + FILES_API_URI_TTL_SECONDS, MCP_ACLOSE_TIMEOUT_SECONDS,
                                                     FILES_API_CACHE_MAX_ENTRIES, REFLECT_OIDC_AUDIENCE)
ma_gatekeeper/README.md                          v4 (Tag sync; 208 tests; calibration invariants; infra recovery)
ma_gatekeeper/HANDOFF.md                         v3 (E10 + Files API + MCP shipped)
ma_gatekeeper/docs/devpost.md                    v1.1 (pre-indexed wording; honest Files API)
ma_gatekeeper/docs/demo_script.md                v1 (E9 storytelling; 3-round feature-build-loop;
                                                     74-word climax voiceover, 35-word caption with
                                                     22s hold, 8-row beat table inverting plan §8
                                                     so auto-promotion is the sole climax)
ma_gatekeeper/frontend/                          v4 (tokens.ts-derived tailwind config; trace_id rename;
                                                     /filing URL; dark-default; font-mono ligature disable;
                                                     bg-lane-clear/10 (no brand-blue leak); .nvmrc 20.11.1)
ma_gatekeeper/frontend/components/pdf-pane.tsx   v2 (Phase 6.7: PDF↔trace bidirectional sync —
                                                     forward = lane-tinted bbox overlay via
                                                     viewport.convertToViewportPoint with PDF
                                                     y-flip min/max normalization; reverse =
                                                     click→convertToPdfPoint→hit-test on current
                                                     page with smallest-area + lexicographic
                                                     clause_id tie-break; pdfjs worker pinned to
                                                     .min.mjs per pdfjs-dist 4.x ESM-only)
ma_gatekeeper/frontend/app/page.tsx              v2 (Phase 6.7: threaded onSelect={setSelectedFindingId}
                                                     to PdfPane to share selection state with
                                                     FindingsPane + TracePane)
design/PLAN.md                                   locked through Phase 5
design/TOOLING.md                                v3 (Option D type acq; size-limit baseline; 3 temptations)
design/INSPIRATION.md                            v3 (gesture-specs + hex anchors + §5 weird lifts)
design/COPY.md                                   v3.1 (cadence tagline + R2/R3 fixes + honest dates removed)
design/STACK.md                                  v2 (15-item must-fix applied; FA self-verdict 7/10 honest)
design/SYSTEM.md                                 v2 + R3 contrast-drift patch + @policy noreuse rename
design/tokens.ts                                 v2 (brand-vs-interactive split; contrast-corrected hexes)
design/tokens.test.ts                            9 tests (3 weird-lift + 3 contrast guards + 3 filled-badge)
design/REVIEW_NOTES.md                           v4 (Phase 0/1/2 challenge round transcripts)
.github/workflows/tests.yml                      v3 (+ scikit-learn + matplotlib)
.claude/skills/design-team/SKILL.md              v2 (Step-3 always-spawn-Supervisor; common shortcuts)
.claude/skills/feature-build-loop/SKILL.md       v2 (design-team pairing hard-gate)
```

---

*End of project log — last revised after Phase 6.7 D15+D18 wedge closure (D17 / 2026-06-05). **365/365 tests** (was 325 at Phase-6.6 close; +40 from Phase 6.7 build_readme_table). The plan §9 "single differentiating interaction" (PDF↔trace bidirectional sync) is now fully wired end-to-end: server populates `page` + `pdf_bbox` per Phase 6.6; frontend renders lane-tinted bbox overlays on selection AND hit-tests PDF clicks back to clause_id via pdfjs `convertToPdfPoint` per Phase 6.7. The plan §5.2 + §12 three-track results table is now generator-tooled (`build_readme_table.py`) with the regex against `eval_cuad_spans.py:107-114, :620` source-of-truth and the degenerate-AUPR caveat scoped to the AUPR row only; D18 operator task is to add `<!-- BEGIN_RESULTS_TABLE -->`/`<!-- END_RESULTS_TABLE -->` markers to README.md and run `--update-readme` after Internal-30 calibration. All hard-to-reverse decisions signed off; contrast-lie + fabricated-SDK-signature patterns mechanically tested at PR time.*
