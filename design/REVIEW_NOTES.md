> **⚠ SUPERSEDED — 2026-06-08.** The design system this file reviewed has been replaced. Canonical brand → [`design/claude-design-output/`](claude-design-output/README.md); index → [`design/SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md). Audit-trail only.

---

# Design Plan — Expert Review Log

Audit trail of the multi-round expert review of `design/PLAN.md`.
Hard cap: 4 rounds. Stop condition: all 5 reviewers return VALIDATED.

## Reviewer cohort

1. **Senior Frontend Architect** — tech stack, perf budgets, framework decision framing, iframe coordination, build choreography realism.
2. **Award-winning Web Designer / Art Director** (Awwwards SOTD sensibility) — inspiration funnel, cliché-vs-technique, design system tightness, motion coherence, playful-serious tension.
3. **Hackathon Judge persona** (200+ Devpost submissions watched) — first-10s wow, video choreography, message hierarchy under attention pressure, 3D distinctiveness.
4. **Project Manager / Delivery Lead** — schedule realism, slack/buffer, cross-team dependencies, scope creep defense, RACI clarity.
5. **Skeptical M&A Counsel / Investor persona** (target audience) — does playful-hackathon vibe undermine investor/legal credibility, does the message land for an actual GC, what would make them close the tab.

## User-locked decisions reviewers may NOT override silently

- Vibe: playful & confident hackathon-native (Resend / Clerk / Cal lane).
- Color: cool but not blue (forest / teal / signal green family), calibrated for M&A-investor seriousness.
- Framework choice deliberately deferred to Phase 4.
- Iframe-embed of real `/reflect` by Day 5.

---

## Round A — complete

### Per-reviewer verdicts

| Reviewer | Verdict | Score | Top finding |
|----------|---------|-------|-------------|
| Frontend Architect | VALIDATED | 7/10 (soft-NOT per skill rule, sub-8) | Perf budget §6.2 mathematically impossible w/ motion+R3F+iframe; pick two |
| Art Director | NOT VALIDATED | — | Plan describes a *tasteful* site; zero "weird" moment, moneymoment buried in list of 11 |
| Hackathon Judge | NOT VALIDATED | — | Tagline + sub-line must communicate Phoenix-traced + conservative-stats differentiator in 10s, or video loses judge before moneymoment lands |
| PM / Delivery Lead | NOT VALIDATED | — | **Iframe-by-Day-5 is mathematically blocked** — PROJECT_LOG D15–D17 (June 3–5) is when product-track `/reflect` frontend lands = design-Day-14. Designed-mock is the *base case*, not the fallback. |
| M&A Counsel | NOT VALIDATED | — | Tagline's "the judge" ambiguity + absence of "what this is not" honesty block — difference between a GC forwarding and a GC quietly closing |

### Cross-reviewer convergences (highest-signal findings)

1. **Tagline broken** — Hackathon Judge + M&A Counsel agree from different lanes.
2. **Moneymoment under-resourced** — Art Director + Hackathon Judge + PM agree.
3. **Iframe-by-Day-5 dead** — PM finding is dispositive (fact-check vs PROJECT_LOG, not opinion).
4. **Design system not actually locked** — Art Director on color/typography; Frontend Architect on scaffold lane-color conflict.
5. **Framework deferral is theater** — Frontend Architect + PM both say lock by Day-2 EOD with stated default.

### User-locked decisions updated this round (flagged to user)

1. **Iframe-by-Day-5 → designed-mock as base case, iframe as Day-6 upside swap.** Reason: PM cross-checked `PROJECT_LOG.md` and found that `/reflect` doesn't deploy until design-Day-14. This is a fact-based override, not reviewer opinion.
2. **Framework deferred to Phase 4 → committed to (A) Next-extended with Astro as Day-4 LCP-triggered fallback.** Reason: the Frontend Architect reviewer — who *would be* the deciding agent in Phase 4 — judged the deferral as theater because the scaffold has already half-made the decision. Saves Day 1.

### Edits applied to PLAN.md (Round-A → Round-B input)

| § | Change |
|---|--------|
| 0.1 (new) | Composition rule: "serious owns" macro/grid/numbers/honesty; "playful lives in" micro/hover/easter-eggs |
| 0 (Phase) | Hard 1-day cap |
| 0.4 (new) | Scaffold cleanup tasks: Next 14→15, lane-color teardown, react-pdf dynamic-import, CSP posture |
| 1.2 | Swapped in Mercury, Ramp, Stripe Press, Modal, Retool, Browser Company memos; removed rauchg/leerob, arc.net |
| 1.3 | Added fake-testimonial-card anti-reference |
| 1.4 | Added semantic-justification rule; hardened gradient constraints (angles {15/165/345}, no radial-from-top, never under headline); recommended candidate #2; added 5th option (no-3D editorial hero); added R3F-prerequisite check |
| 2.1 | Rewrote tagline + added load-bearing sub-line with conservative-stats wedge + tightened pillars |
| 2.2 | Reframed problem vignette to partner-POV; promoted moneymoment to its own treatment via §6.4; added "What this is not" section; restructured Built-on as Where-it-lives with deployment story first; rewrote FAQ to GC objections; added Devpost demo-scope paragraph; added build-SHA + model-pin to footer |
| 2.3 | Cut console.log easter egg; expanded banned-word list with legal-tech offenders |
| 3.2 | Removed per-component AD review bottleneck — section-completion review only, max 1/day |
| 4.1 | Committed to (A) Next-extended with Astro-fallback trigger; Day-2 EOD lock |
| 4.3 | Expanded animation principles: scroll constants, page-load choreography, orchestration rules, idle/loop, Rive-XOR-R3F |
| 5.1 | Committed to deep forest emerald (single direction with M&A semantic story); warm clay accent; signal-green demoted to 5% state-only |
| 5.2 | Pairing thesis: Lane A (editorial serif display + neutral sans + warm mono) recommended |
| 5.5 | Added Trace-Span primitive; defined repo layout for shared/marketing/console |
| 5.6 (new) | Wordmark promoted to real deliverable with kill-switch |
| 6.1 | Restructured to Day/Must-ship/Nice-to-have/Cut-trigger table; moneymoment is now Day 5 sole-focus; scope freeze Day 5 EOD; kill-switches summary |
| 6.2 | Revised perf budgets to realistic: LCP <2.4s, JS above-fold <180KB, total <350KB, Lighthouse ≥90; "pick two of {motion-heavy, R3F, iframe}" rule |
| 6.4 (new) | Moneymoment is special (parity with hero) — dedicated day, 1.5 viewports, dedicated review gate, engineered screenshot frame |
| 7.0 (new) | Video script + storyboard with locked 2:30 structure (hook/problem/moneymoment/numbers/loop/CTA) |
| 7.3 | Console.log replaced with build-SHA + model-pin + eval-link |
| Resolved decisions | Rewrote iframe section to mock-as-base-case with upside swap; framework commit |

---

## Round B — complete

### Per-reviewer verdicts

| Reviewer | Verdict | Score | Top finding |
|----------|---------|-------|-------------|
| Frontend Architect | VALIDATED | 9/10 | Clean. Two polish recommendations: mechanical bundle-size CI (vs. judgment-enforced), name LCP measurement methodology |
| Art Director | VALIDATED | 8.5/10 | Plan now *permits* weirdness but doesn't *name* the weird gesture in §6.4. Wants worked example for §1.4 semantic justification; Lane-A risk callout |
| Hackathon Judge | VALIDATED | 8.5/10 | §7.0 moneymoment beat is 10s short for the page's strongest argument; name the specific number in the screenshot frame |
| PM / Delivery Lead | VALIDATED | 8.5/10 | Day 6 is the new Day 5 (pile-up); three lock dates still drifting (typography, hero-candidate, OIDC); add Day-1 90-min iframe spike timebox; FAQ needs legal-review gate |
| **M&A Counsel** | **NOT VALIDATED** | — | Two unforced marketing-tells in load-bearing real estate: "survives a deposition" (raises malpractice flag — implies tool output is evidence) and "your data stays in your project" (unsupported claim — architecture is single-tenant Cloud Run, not per-customer GCP projects) |

### Edits applied to PLAN.md (Round-B → Round-C input)

| § | Change | From reviewer |
|---|--------|---------------|
| 1.4 | Added worked semantic-justification example for candidate #2 | Art Director |
| 2.1 | Tagline rewritten: "every flag is sourced to the clause it came from" — kills the deposition implication | **M&A Counsel (blocker)** |
| 2.2 #6 | Added concrete required fields (region, TTL, key holder, deletion SLA); added new bullet for security posture (SOC 2 / pen-test / NDA report) | **M&A Counsel (blocker)** |
| 2.2 #10 | Removed "your data stays in your project" claim; replaced with defensible "documents are processed in [region], not retained beyond [N] hours, never used to train any model" | **M&A Counsel (blocker)** |
| 2.2 #11 | Hard requirement: FAQ *answers* (not just questions) drafted in COPY.md by Day-2 EOD, GC-persona reviewed; Day-6 pre-merge legal-review gate | M&A Counsel + PM |
| 5.1 | Warm clay accent specified as desaturated terracotta — not orange, not "Substack orange" | M&A Counsel |
| 5.2 | Added Lane-A risk callout (boring-corporate-law-firm failure mode + mitigation); Day-2 EOD lock date | Art Director + PM |
| 6.1 Day 1 | Added 90-min iframe-spike timebox; OIDC-survival test; iframe-permanently-off if unresolved | PM |
| 6.1 Day 2 | Added typography Lane A/B lock + hero candidate #2/#5 lock + GC-FAQ draft answers + D18 Reflector pre-seed disclosure | PM + M&A Counsel |
| 6.1 Day 6 | Added explicit Day-6 cut-line: Built-on → logo strip, FAQ → top-3 if Reflector eats time | PM |
| 6.1 kill-switches | Added OIDC, typography fallback, Day-6 pile-up cut | PM |
| 6.2 | Mechanical bundle-size CI (size-limit) + named LCP methodology (Lighthouse Moto G4, 3-run median, Vercel preview) | Frontend Architect |
| 6.4 | Named the gesture: trace "unfurls" span-by-span → RiskJudge span lights → click lifts span ~8px revealing prompt + Phoenix span ID + eval verdict. Named the specific screenshot number: Wilson-LB recall headline in Lane-A display serif | Art Director + Hackathon Judge |
| 7.0 | Rebalanced moneymoment beat from 45s → 55s (0:30–1:25); honest numbers 35s → 30s (1:25–1:55); loop tightened to 20s | Hackathon Judge |

---

## Round C — M&A Counsel only — complete

### Verdict

**VALIDATED — 9/10.** All Round-B blockers resolved. New tagline ("every flag is sourced to the clause it came from") lands clean as an artifact claim, not a legal-weight claim; defensible §2.2 #10 language landed; required-fields machinery for data handling + security posture protects the page from Day-6 vague answers; warm-clay anti-Substack-orange spec is sharp.

### Polish suggestions left at Round C (non-blocking)

1. **Trust-packet items** for a future `/security` sub-page (subprocessors, breach-notification SLA, GDPR Art. 28 / DPA posture) — *applied* to §2.2 #6 as a sixth bullet referencing the downloadable trust-packet so the page doesn't dead-end at the honesty block.
2. **Real (non-persona) GC reviewer** for the Day-6 FAQ legal-review gate, to break the "GC-persona reviews GC-persona answers" circularity — *flagged to user* (depends on whether you have access to a real GC contact). Not a blocker; structurally guarded already.

---

## Convergence summary

All 5 reviewers VALIDATED. Loop closed in 3 rounds, well under the 4-round cap.

| Reviewer | Round A | Round B | Round C |
|----------|---------|---------|---------|
| Frontend Architect | VALIDATED 7/10 (soft-NOT) | **VALIDATED 9/10** | — |
| Art Director | NOT VALIDATED | **VALIDATED 8.5/10** | — |
| Hackathon Judge | NOT VALIDATED | **VALIDATED 8.5/10** | — |
| PM / Delivery Lead | NOT VALIDATED | **VALIDATED 8.5/10** | — |
| M&A Counsel | NOT VALIDATED | NOT VALIDATED | **VALIDATED 9/10** |

**Round-2 mean: 8.7/10** across all reviewers — strong consensus, not reviewer fatigue (multiple substantive critiques in each round with concrete, distinct, in-domain findings).

### Highest-impact changes the review loop produced

1. **Killed the iframe-by-Day-5 commitment** (PM cross-checked PROJECT_LOG and proved it was mathematically blocked by the product track). Rewrote demo-embed strategy to mock-as-base-case, iframe as Day-6 upside swap.
2. **Rewrote the tagline twice**: from "the judge can click into" (Round A — Article-III ambiguity) → "survives a deposition" (Round B — malpractice implication) → "every flag is sourced to the clause it came from" (Round C — clean artifact claim).
3. **Promoted the audit-trail moneymoment** from one bullet in a list of eleven to a dedicated Day with its own subsection (§6.4), its own motion budget, its own review gate, an engineered screenshot frame, and a named gesture (unfurl → light → lift).
4. **Added "What this is not" honesty block** with required concrete fields (region, TTL, key custody, deletion SLA, SOC-2 status, pen-test status, NDA-able report) — the GC-trust addition that turns the page from "tool I'd close" to "tool I'd forward."
5. **Committed the framework decision** (extend Next, Astro as Day-4 LCP-triggered fallback) instead of deferring to a Phase-4 debate the scaffold had already half-decided.
6. **Replaced "150KB JS budget" fiction** with realistic + enforceable budgets (180KB above-fold / 350KB total / Lighthouse ≥90 / mechanical size-limit CI / "pick two of {motion-heavy / R3F / iframe}" rule).
7. **Added scope freeze, kill-switches inventory, Day-6 cut-line, and 7 named lock dates** to convert the day-by-day from "wish" into "delivery doc."
8. **Promoted the wordmark** from a passing question to a real Phase-5 deliverable with kill-switch.
9. **Removed "your data stays in your project"** (unsupported architectural claim) and replaced with defensible retention/no-training language tied to the actual single-tenant Cloud Run posture.
10. **Cut the console.log easter egg** (juvenile for a serious legal tool) and replaced with build-SHA + model-pin + eval-link as engineering-discipline signal.

---

# Citation-Layer Feature — Multi-Wave Review (separate from the design-plan loop above)

User-requested feature added post-plan-convergence: deterministic citation map + LLM proposer + Phoenix-evaluated comparator. Full spec at [`STATUTE_LAYER.md`](STATUTE_LAYER.md). This loop ran 3 designer + 3 reviewer × 3 review rounds and converged on user-VALIDATED scores 8/10–9/10 across the reviewer panel.

## Pre-design 4-agent vote (A vs B vs C)

Before designing, ran a debate on which architecture variant:
- ML/Arize specialist: **C 9/10** (Hybrid uniquely converts Mata-v.-Avianca failure into eval-theater)
- M&A Attorney: **A 9/10** (C is malpractice trap if UI mislabels)
- Hackathon Judge: **C 9/10** (with fallback to A, NEVER B)
- Backend Architect: **A 8/10** (C costs 5.5 dev-days)

Vote 2-2. User chose **C** for Phoenix leverage value. Designers and reviewers worked from that decision.

## Wave-1 designers (parallel proposals)

| Designer | Self-confidence | Biggest open Q (later resolved) |
|----------|-----------------|----------------------------------|
| ADK Architecture Lead | 7.5/10 | ADK ParallelAgent + non-LLM shim (→ replaced by plain asyncio) |
| Phoenix Eval Methodologist | 7.5/10 | Independent-annotator bar (→ κ pass deferred post-hackathon) |
| UX & Liability Designer | 8.5/10 | Own-domain `/evals` route safe in video (→ Phoenix-hosted only) |

## Wave-2 reviewers (Round 1)

| Reviewer | Verdict | Killer finding |
|----------|---------|----------------|
| M&A Attorney | VALIDATED 8.5/10 | **§2.2 #11 Roadmap "promoted to user-facing" clause = future-malpractice exhibit.** MAC is common-law, not statutory. Cut "We graded our own model" line. |
| Backend Architect | **NOT VALIDATED** | **Ran schema in venv.** Pydantic v2 hard-rejects `_linker_*` field names. Project has no `.j2` templates (Guard #3 defends nothing). Cold-path latency claim false. 8d > 7d budget. |
| Hackathon Judge | VALIDATED 9/10 | 3-hook story holds. Phoenix-hosted-only is the right call. |

In-domain conflict on "We graded our own model" line: M&A Attorney wins (malpractice owns marketing copy that touches legal posture). Banned from all written channels.

## Wave-3 reviewers (Round 2 after 17-fix rewrite)

| Reviewer | Verdict | Finding |
|----------|---------|---------|
| M&A Attorney | **VALIDATED 9/10** | Caught my own spec citing `Akorn` as `198 A.3d 724` (the affirmance cite, not the Chancery merits opinion `2018 WL 4719347`). **Perfect proof-of-need for the sign-off gate.** 5 polish fixes applied. |
| Backend Architect | **NOT VALIDATED** | **`finding.trace_id` is 32-hex trace id; `_annotate` requires 16-hex span_id. Every annotation 100% 404s.** Also recommended `model_dump` subclass override + `force_flush` race fix. |

## Wave-4 reviewer (Round 3, BE Architect only)

| Reviewer | Verdict | Notes |
|----------|---------|-------|
| Backend Architect | **VALIDATED 8/10** | All 4 blockers resolved. 3 cosmetic notes applied: override `model_dump_json` too; log `force_flush` return + sync=True fallback; document span grouping under parent. |

## Final convergence

| Reviewer | Final | Δ |
|---|---|---|
| Backend Architect | **VALIDATED 8/10** | from NOT-VALIDATED (3 rounds) |
| M&A Attorney | **VALIDATED 9/10** | from 8.5/10 (2 rounds) |
| Hackathon Judge | **VALIDATED 9/10** | clean single-round |

**Total cost: 7 dev-days product-track** (4.5 Arch + 1.5 Eval + 0.75 UX + 0.25 buffer). Fits remaining budget exactly.

## Highest-impact changes the citation-layer loop produced

1. **Renamed statute_map → citation_map** + 4 named case-law anchors (Akorn, Revlon, AB Stable, Trados). MAC doctrine is common-law; statute-only map was structurally incomplete.
2. **Pydantic underscore fields → subclass `model_dump` override** with `_EVAL_ONLY_FIELDS`. Backend Architect ran the original schema in venv and proved Pydantic v2 rejects it at import.
3. **`trace_id` vs `span_id` bug**. Every annotation would have 404'd. Caught by Round-3 BE Architect.
4. **§2.2 #11 Roadmap "promoted to user-facing" clause deleted**. That clause was the future-malpractice exhibit hostile counsel quotes at trial. Rewritten to "informs map expansion, never replaces it."
5. **LLM linker moved off cold path** via `asyncio.create_task` fire-and-forget. User p50 unchanged.
6. **`force_flush` race fix** + return-value logging + sync=True fallback. Without this, annotations silently fail intermittently.
7. **AST contract test → SSE wire-output regression test**. Project has no Jinja, original guard defended nothing.
8. **"We graded our own model" banned from written channels** per Twitter-v-Musk discovery precedent.
9. **CI staleness gate** (`verified_date > 180 days fails build`).
10. **κ inter-rater + `citation_faithfulness` cut to fit 7-day budget**; both post-hackathon follow-ups.
11. **Video y-axis tick labels stripped entirely** (not just fuzzed gridlines).
12. **Akorn citation flagged for Day-2 attorney verification** before code lands.

## Open items deferred

- κ inter-rater computation (post-hackathon).
- `citation_faithfulness` evaluator (post-hackathon).
- Tighter span grouping under `risk_judge` vs SequentialAgent parent (v2).
- `model_dump_internal` escape-hatch grep audit (Day-7 task).
- Real (non-persona) GC reviewer for citation-map sign-off (depends on user access).

---

# Phase 0 execution — Expert Review Log

Audit trail of the multi-round review of the **Phase 0 execution** (TOOLING.md, scaffold cleanup, PROJECT_LOG entry). Distinct from the PLAN.md review above. Stop condition: all 4 reviewers VALIDATED.

## Reviewer cohort (Phase 0)

1. **Senior Frontend Architect** — scaffold cleanup decisions (Next pin, react-pdf, lane colors, X-Frame), missing mechanical scaffolding (size-limit, lockfile, .nvmrc).
2. **PM / Delivery Lead** — Day-1 budget realism, kill-switch firing, deferred-items concreteness, PROJECT_LOG sufficiency.
3. **Art Director** — does the tooling stance silently cap design ambition? (MCPs, type acquisition, screenshot pipeline, wordmark exploration.)
4. **Plan-Fidelity Skeptic** — line-by-line fidelity audit of TOOLING.md vs. PLAN §0.1–§0.4 and §6.1 Day-1 row.

---

## Round A — complete (all four NOT VALIDATED)

### Per-reviewer verdicts

| Reviewer | Verdict | Top finding |
|---|---|---|
| Frontend Architect | NOT VALIDATED | Shipped a "tooling lock" leaving an open `frame-ancestors` on a deployed OIDC-protected route, calling it "flagged." `size-limit` is fiction without install + baseline; `^14.2.5` without a lockfile is theater. |
| PM / Delivery Lead | NOT VALIDATED | Day 1 declared closed while the Day-1 EOD iframe kill-switch is un-fired and the 90-min spike floats into Day 2 without an owner or clock. PROJECT_LOG silently omits the three skipped must-ships. |
| Art Director | NOT VALIDATED | Audits skills handed to it and installs zero MCPs that would let design ambition scale. Playwright (mining) + image-gen (§6.4 still) are Day-1 needs deferred to non-existent days. Type-acquisition (paid foundries) is an unowned landmine. No "Temptations killed" section — exact §0.1 failure mode. |
| Plan-Fidelity Skeptic | NOT VALIDATED | Day-1 shipped 1.5 of 5 must-ships and PROJECT_LOG silently omits the three that didn't run — including the OIDC-Safari-ITP spike whose unresolved status was supposed to mechanically retire the iframe upside. |

### Cross-reviewer convergences

1. **Iframe spike + OIDC-ITP test absent** — PM + Skeptic agree, dispositive against PLAN §6.1 cut-trigger. Both call for either run-or-fire-the-kill-switch.
2. **`frame-ancestors` security gap** — Frontend Architect dispositive (security baseline, not design decision).
3. **TOOLING.md is tasteful-and-safe** — Art Director's "no opinions = doc didn't do its job" maps to Skeptic's "MCP search was declared, not performed."
4. **PROJECT_LOG insufficient for cold Day-2 resume** — PM + Skeptic agree.

### Edits applied to TOOLING.md + scaffold (Round-A → Round-B input)

| Finding | Fix shipped in v2 | Reviewer |
|---|---|---|
| `frame-ancestors` gap on `/reflect` | `_frame_lockdown` middleware added to `agent/server.py` — `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` defaults | Frontend Architect |
| Iframe spike could not be run from agent context | **Kill-switch fired** per PLAN §6.1 — iframe upside retired; mock-only path locked; Day-6 re-confirmation struck; six (a-f) gates audited honestly in TOOLING §4.3 | PM + Skeptic |
| INSPIRATION board not started | `design/INSPIRATION.md` shipped with §1.2 reference table populated, screenshot directory plan, categories scaffolded | Skeptic + PM |
| `.nvmrc` missing | Added at `ma_gatekeeper/frontend/.nvmrc` → `20.11.1` | Frontend Architect |
| Lockfile / `size-limit` / `next-bundle-analyzer` | TOOLING §4.1 lists as user-action (lockfile = one `npm install`) + Frontend-Architect Day-2-EOD task (size-limit wiring once lockfile lands); honest "Day-2" rather than fictional "today" | Frontend Architect |
| Type-acquisition (paid foundries) | TOOLING §6 added: Option A buy / Option B OFL-fallback (Fraunces+Inter+JetBrains) / Option C Lane-B; Art Director Day-1-EOD decision | Art Director |
| "Temptations killed" missing | TOOLING §7 added — Spline-blob, AI gradient packs, Framer template wholesale, Lottie marketplace packs, shadcn Blocks wholesale, "AI = neurons" templates, "Made with AI" badges | Art Director |
| `fewer-permission-prompts` drift (Skip → Defer) | Reverted to Skip per PLAN §0.1 verbatim | Skeptic |
| Lane-color "annotated" green-checked as if "torn out" | Reclassified ⏸ deferred-to-Phase-5 with honest blocker (findings-pane.tsx consumption) | Skeptic |
| `tokens.ts` ownership wrong (FA, not AD) | Corrected to Art Director per PLAN §5 | Skeptic |
| Deferred items as vibes ("~Day 3" / "Day-1 spike") | TOOLING §4.2 restated with ISO dates, named artifacts, Day-2-morning Supervisor checkpoints | PM |
| MCP search declared, not performed | TOOLING §2.4 honestly scoped: the agent cannot crawl external MCP registries; image-gen + Playwright surfaced as user-action recommendations | Skeptic |
| PROJECT_LOG silently omits skipped must-ships | "Day-1 deviations" sub-block added with the five must-ships and explicit dispositions | PM + Skeptic |

### Items NOT actioned and why (kept for audit transparency)

- **PM's meta-finding that running expert-review-loop on Phase 0 is overkill** — user explicitly requested the review pass; noted but not acted on. PM acknowledged in their own report that the review IS catching real misses.
- **Art Director recommendation to install MCPs unilaterally** — agent does not install MCPs; surfaced as user-action queue in TOOLING §2.4 and PROJECT_LOG.
- **Art Director recommendation to seed `design/screenshots/` directories** — deferred to Day-2 morning Art-Director action; `design/INSPIRATION.md` documents the convention.
- **Art Director wordmark playground HTML** — deferred to §5.6 Day-3 work, not a Phase-0 deliverable.

---

## Round B — complete (all four VALIDATED)

### Per-reviewer verdicts

| Reviewer | Verdict | Score | Top remaining concern (polish, non-blocking) |
|---|---|---|---|
| Frontend Architect | **VALIDATED** | **8.5/10** | size-limit "wait for marketing route" deferral is structurally self-perpetuating — baseline against `/console` today with loose ceiling so the gate exists. |
| PM / Delivery Lead | **VALIDATED** | **9/10** | Option B's Fraunces fallback has no escape hatch — if it fails the Day-2 hero-scale test, no Option D is in writing. |
| Art Director | **VALIDATED** | **8.5/10** | Same Fraunces concern (add Option D = trial license); three additional temptations to add to §7 (Vercel templates, AI copy generators, stock icon packs as primary). |
| Plan-Fidelity Skeptic | **VALIDATED** | **9/10** | `_frame_lockdown` is set in code but unverified by test — a 3-line pytest would close the "claim vs. behavior" gap. |

### Convergence summary

| Reviewer | Round A | Round B |
|---|---|---|
| Frontend Architect | NOT VALIDATED | **VALIDATED 8.5/10** |
| PM / Delivery | NOT VALIDATED | **VALIDATED 9/10** |
| Art Director | NOT VALIDATED | **VALIDATED 8.5/10** |
| Plan-Fidelity Skeptic | NOT VALIDATED | **VALIDATED 9/10** |

**Round-B mean: 8.75/10** across all four reviewers. Score jump from 0/4 VALIDATED in Round A to 4/4 in Round B is genuine (not reviewer fatigue) — each reviewer surfaced distinct, in-domain residual concerns rather than rubber-stamping. Convergence in 2 rounds, well inside the 4-round skill cap.

### Polish items applied post-Round-B (convergent — both PM + AD asked for #1)

| Polish | Fix | Reviewer |
|---|---|---|
| Option D (trial license) escape hatch for type acquisition | TOOLING §6 — added Option D (7-day foundry trial; fits inside Devpost deadline window if pulled Day-2), Option C re-tiered to "nuclear only if A, B, AND D fail," Option B verdict cell rewritten with honest "~70% of Lane-A authority" + explicit escalation path to D | PM + Art Director |
| size-limit self-perpetuating deferral | TOOLING §4.1 task 7 — commitment changed from "Day-2 EOD once lockfile lands" to "Day-2 morning 12:00, baseline against `/console` with current+20% ceiling, tighten when `/` lands" — closes the rationalization loop FA flagged | Frontend Architect |
| Three additional temptations | TOOLING §7 — added (a) Vercel/Next-template wholesale clones, (b) AI copy generators for `COPY.md`, (c) stock icon packs as primary iconography | Art Director |
| Pytest for frame-headers | TOOLING §4 task 4 — surfaced as Day-2 morning Frontend-Architect owner-tracked outstanding work (~3-line pytest in `tests/test_server_stream.py`) | Plan-Fidelity Skeptic |
| Cosmetic line-anchor | TOOLING §4 task 4 — anchor fixed from `:392+` framing to point at the actual middleware location | Plan-Fidelity Skeptic |

### Highest-impact changes the Phase-0 review loop produced

1. **Iframe kill-switch fired** — PLAN §6.1's mechanical cut-trigger was about to be silently bypassed; PM + Skeptic both caught it. Mock-only path is now locked, Day-6 re-confirmation struck, the agent-context honest verdict (can't test Safari ITP from here) is the receipt.
2. **`/reflect` framing locked down today** — `_frame_lockdown` middleware shipped; a deployed OIDC-protected route is no longer un-framed-by-default. Security baseline collapsed into the same commit as the design decision.
3. **Type acquisition surfaced as Day-1 EOD blocker** — paid-foundry licensing for PLAN §5.2 Lane A was an unowned landmine; now Options A–D with cascade-block reasoning and a recommended default.
4. **"Temptations explicitly killed" section** — the tooling-layer defense against the PLAN §1.3 anti-references that would otherwise leak in via "this nice MCP/template existed." Tasteful-and-safe → tasteful-and-weird at the tooling layer.
5. **PROJECT_LOG Day-1 deviations table** — converts "two of five shipped, three silently skipped" into an auditable record with explicit dispositions.

### Stop condition met

All four reviewers VALIDATED in Round B with scores ≥8.5 (above the skill's "treat &lt;7 as soft-NOT-VALIDATED" bar). Post-round polish addresses every named residual concern. Phase 0 closed.

---

## What this loop did NOT do (PM's meta-observation, accepted)

The PM (Round A) noted that running `expert-review-loop` on a 1-day toolchain audit is overkill as a *template* — a 10-line PROJECT_LOG append would be sufficient for routine phase outputs. **This pass was user-requested**, and it did catch real misses (iframe kill-switch un-fired, frame-ancestors security gap, type acquisition unowned). The cost was paid; the precedent is *not* "run a 4-reviewer panel on every phase." Future phases trigger `expert-review-loop` only on (a) Phase 5 (`tokens.ts` + `SYSTEM.md`), (b) the Day-5 moneymoment, (c) the Day-7 pre-deploy build.

---

# Phase 2 challenge round — Art Director on `design/COPY.md` v2 — 2026-05-26

Audit trail of the Art Director's post-draft review of the Copy Lead's v2 critique-and-refine of `design/COPY.md`. Single-reviewer round (Art Director only) per the `design-team` skill sequential rule (Phase 2 = Copy Lead owns, AD reviews post-draft). Supervisor spec named three explicit gates.

## Reviewer cohort (Phase 2)

1. **Art Director** — central-tension §0.1 register audit, weird-lifts enforcement (INSPIRATION line 210), §5/§6.4 frame integrity at the px level, ban-list grep, §3 specificity check, §11.2 forward-reference disposition.

## Round 1 — verdict

| Reviewer | Verdict | Score | Top finding |
|---|---|---|---|
| Art Director | **VALIDATED** | **8.5/10** | All three Supervisor-named gates pass. v2 is genuine craft work on top of v1 — the §6 Mercury-tail stripping is the load-bearing edit; the §3 anti-assignment+change-of-control swap is the kind of specificity that distinguishes legal-tech-by-a-team-that-talks-to-GCs from legal-tech-by-a-team-that-Googled-it. Three EDITs remain to close before sign-off (§11.2 forward-reference, §16 hook beat is 4 words long for 5s @ 150 wpm, §16 problem beat is 4 words long for 25s @ 150 wpm). |

## Per-gate audit

### Gate 1 — §0.1 central-tension (serious vs playful) — PASS

| Section | Register | Verdict |
|---|---|---|
| §3 problem vignette | Reportage-serious. *"Friday 6pm. Exhibit 2.1 hits the data room."* + *"The work is real. The reading is long. The exposure is yours."* commits to the partner-POV register. No vignette-cute. | CLEAN |
| §6 honesty block | Serious throughout. Bullets 1–3 are declarative two-beats (`Inference-only. No fine-tuning. No retention beyond the session.`). Bullets 4–6 fielded posture in the `[Region]. [Number]. [Custodian].` cadence. v1's Mercury-aspirational tails (*"we make legal work shorter"* / *"The opinion letter carries the partner's name, not the model's"*) correctly stripped — the meta-doc DELTA cell on §6 is honest. | CLEAN |
| §11 GC-FAQ | All 5 answers (Privilege / Standard of care / Confidentiality-residency / Model continuity / Conflicts) commit to declarative reporting. §11.2's *"You are."* opener is the strongest line in the doc — Stripe-doc-grade. §11.5's *"No shared cache. No shared session. No shared retention."* is the cadence anchor working. | CLEAN |
| §13 footer + easter egg | Footer credits (build SHA + model pin + eval link + CSP) are unambiguously serious. Easter egg (*"If you read this far, you should be doing diligence on something more interesting."*) is unambiguously playful and lives in the footer-bottom-right, separated from the credits block. Clean lane separation. | CLEAN |
| §14 error/loading microcopy | Each line commits. 404 (*"This page does not exist. Most things in M&A don't, until they're filed."*) is the cleanest playful commit in the doc. EDGAR-503 line is playful-but-fielded: *"This is real, not a mock"* is bounded humor anchored in product truth. No half-witty lines. | CLEAN |
| §16 video narration | Serious throughout. *"There is no black box. There is no place you cannot click into."* (0:30–1:25) carries the moneymoment. No narration line slips register. | CLEAN |

### Gate 2 — Weird-lifts enforcement — PASS (with §16 cadence flag)

| Lift | Surface | Verdict |
|---|---|---|
| §Voice weird lift in §3 | "anti-assignment with a change-of-control trigger that opposing counsel never flagged at signing" — hits the trigger.dev "specific story in the hero copy" anchor. Anti-assignment + COC is a real post-2020 carve-out caselaw landmine; the phrasing "never flagged at signing" is the specificity a GC recognizes (the failure mode is *who missed it when*, not the abstract clause type). v1's "MAC clause nobody has read" was the failure mode INSPIRATION line 208 explicitly names; v2 fixes it. | PASS |
| §Composition weird lift in §5 | All §6.4 px-spec items present and match: 240px desktop / 96px mobile display serif on the `0.94` hero number, warm-clay Block badge left-aligned to the `0` digit (not centered — the weird-but-tasteful move), no card/border/shadow, 12px mono Phoenix span ID at `--neutral-400`, 16px below badge. See Gate 3 for full px audit. | PASS |
| §Motion weird lift in §16 narration | Deliberate-slowness pacing read aloud: most beats have room (the 0:30–1:25 moneymoment beat lands at ~110 words for 55s = ~120 wpm, *below* the 150 wpm target — confidence cadence working). **BUT**: the 0:00–0:05 hook beat is 12 words (target ~12 — exactly at the line, no room); the 0:05–0:30 problem beat is **62 words** at 150 wpm but reads to ~70 spoken (compound clauses: "three associates, two paralegals, one anti-assignment clause with a change-of-control trigger nobody flagged at signing, and your name on the opinion letter" = 30 words alone in the closing list). Cadence honor is mostly present, but the problem beat is **stuffed**, not breathing. Cursor.com weird-lift = non-snappy timing; v2 §16's problem beat fails this aloud. | PASS-WITH-FLAG |

### Gate 3 — §5/§6.4 frame integrity (px-level) — PASS

| INSPIRATION §6.4 spec | COPY.md v2 §5 | Match? |
|---|---|---|
| 240px desktop / 96px mobile display serif hero number | `display serif, 240px desktop / 96px mobile` on `0.94` | ✅ |
| `-0.02em` tracking on headline | *not stated in COPY.md §5* — INSPIRATION line 116 names it, COPY drops it | ⚠️ deferred to `tokens.ts` (acceptable: §5 calls "per INSPIRATION §6.4 frame composition spec" so the tracking carries by reference — but worth surfacing) |
| 16px mono attribution at `--neutral-500`, 24px gap | *"Wilson 95% lower bound recall, frozen held-out fold, n=72 trial review"* — color + gap not stated in COPY but again carries by INSPIRATION reference | ✅ (by reference) |
| 48px-height warm-clay badge, 24px h-padding, 14px mono uppercase tracked `+0.08em` | *"warm-clay pill, mono uppercase"* — height/padding/tracking not in COPY but carries by reference | ✅ (by reference) |
| Left-aligned to the `0` digit (NOT centered) | *"left-aligned to the number's `0` digit"* — explicit in COPY | ✅ |
| 12px mono Phoenix span ID at `--neutral-400`, 16px below badge | *"12px mono, neutral-400: `phoenix:span:7f3a-c2b1-…`"* | ✅ |
| No card, no border, no shadow | *not explicitly stated in COPY* — carries by INSPIRATION reference | ✅ (by reference) |

**Frame integrity: PASS.** Copy Lead correctly defers the px specs that belong in `tokens.ts` (color tokens, tracking, gaps) while restating in COPY the load-bearing layout commitments that drive the *frame* (size, badge alignment, no-container). One follow-up for §18 cross-references: explicitly enumerate the tracking + `--neutral-400`/`--neutral-500` + no-card spec so Component Builders don't have to traverse INSPIRATION → COPY → tokens. Not a blocker.

## Additional review findings

### Ban-list audit — PASS

Grep on `revolutioniz|unleash|supercharge|leverage|robust|seamless|AI-powered|trusted by|next-generation|enterprise-grade|purpose-built|human-in-the-loop|co-pilot|transform your practice|white-glove` returned **one** hit — line 6 of COPY.md, which is the meta-doc cadence-enforcement note *naming* the ban list (`No "trusted by" claims; no marketing-bro words`). Zero in-body hits across §0–§18. Copy Lead's claim in the PROJECT_LOG entry ("audited the draft for [ban list] — zero hits") is honest.

### §3 specificity verdict — PASS

The anti-assignment + change-of-control trigger pattern is a real, recurring landmine in post-2020 M&A practice (notably in carve-out transactions where the parent's debt covenants include change-of-control prohibitions on subsidiary asset sales, and the diligence team reads the asset-sale doc without pulling the parent indenture). *"opposing counsel never flagged at signing"* is the kind of detail a GC recognizes immediately because it inverts the usual diligence failure mode (it's not *your* team that missed it — it's the *other* side's team, and you inherit the exposure at the merger). This is specific in a way generic-with-extra-words couldn't be. Copy Lead's claim holds.

### §11.2 forward-reference disposition — EDIT REQUIRED

Copy Lead's verdict correctly flagged this: §11.2's question text *"if I rely on a Block call and miss the **anti-assignment trigger**, who is on the hook?"* references the §3-specific clause type. A GC who jumps from nav directly to FAQ (a real reading pattern — FAQ is what a procurement contact opens first) hits this reference cold. Two acceptable fixes:

1. Generalize §11.2 question: *"if I rely on a Block call and miss the flagged clause, who is on the hook?"* — costs the §3↔§11 cross-narrative thread.
2. Add a 3-word parenthetical: *"…miss the anti-assignment trigger (the §3 example), who is on the hook?"* — preserves the thread, defends the cold-read.

Recommend (2). This is the only EDIT-class blocker before AD sign-off.

## Round-1 edits required before sign-off

1. **§11.2 question rewrite** — add the *"(the §3 example)"* parenthetical OR generalize to *"flagged clause"*. Cold-read GC defense.
2. **§16 problem beat trim** — the 0:05–0:30 beat reads stuffed at 62 words with the 30-word closing list. Trim the list to: *"three associates, two paralegals, one anti-assignment trigger nobody flagged at signing, and your name on the opinion letter."* (drops *"clause with a change-of-control"* — the trigger is the COC; the redundancy is cadence drag). Or break the list across two sentences for breathing room.
3. **§16 hook beat** — 12 words is exactly the line at 150 wpm. Recommend the verb-led alternate from §0 candidate (3): *"We read the merger agreement. We source every flag. We hand you the trace."* — same idea, breathes better, ends on a noun.
4. **§5 px-spec surfacing** — explicitly enumerate tracking + `--neutral-400/-500` colors + no-card spec in §5 (not just by INSPIRATION reference). Component Builder Day-5 friction defense; not a hard blocker.
5. **§18 cross-reference completeness** — same as #4 from the Phase-5 token-handoff side. Surface the full §6.4 frame spec so `tokens.ts` row drafts don't have to traverse three docs.

## Forbidden-patterns added (none)

No new cliché traps surfaced in v2 — Copy Lead respected the ban list and the cadence anchors. Existing forbidden-patterns registry unchanged.

## Convergence summary

| Reviewer | Round 1 |
|---|---|
| Art Director | **VALIDATED 8.5/10** |

Single-reviewer round per `design-team` sequential rule. Loop closes after the 5 fixes above land in v3, or after Copy Lead defends them (any defense counts as resolution — this is not a re-do trigger).

## Highest-impact changes the Phase-2 challenge round produced

1. **§11.2 cold-read defense** — surfaces a real GC reading-path failure (nav → FAQ jump) that the §3↔§11 cross-narrative thread silently created. One 3-word edit closes it.
2. **§16 problem-beat cadence flag** — preserves the Motion weird-lift (cursor.com deliberate slowness) at the narration layer where it would otherwise quietly fail aloud despite being correct on the page.
3. **§16 hook-beat margin recovery** — converts an "exactly at the line" beat to a "lands with room" beat, protecting the first 5s of the Devpost video — the highest-leverage seconds in the whole submission.
4. **§5 px-spec surfacing** (non-blocker) — collapses Component Builder Day-5 friction from three-doc traversal to single-doc lookup. Cheap polish.

