# Design Track — Handoff

> Snapshot for picking up the design track in a new session. Mirror of `ma_gatekeeper/HANDOFF.md` convention.
> **Last updated**: 2026-06-08 — design system regenerated via `claude design`; the Phase-0 → Phase-5 specs in this directory are now **SUPERSEDED**.
> **Read order on cold pickup**: [`design/SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md) → [`design/claude-design-output/README.md`](claude-design-output/README.md) → [`design/claude-design-output/source/design.md`](claude-design-output/source/design.md) → this file (for code-side migration status only).

---

## ⚠ Source-of-truth changed (2026-06-08)

The canonical design system has moved to **[`design/claude-design-output/`](claude-design-output/)** — generated end-to-end by the `claude design` workflow. The visual register is **Documentary Brutalism** (court-filing aesthetic + editorial brutalism + telemetry surfaces), not the prior modern-SaaS / warm-clay direction. All legacy specs (`PLAN.md`, `INSPIRATION.md`, `STACK.md`, `SYSTEM.md`, `COPY.md`, `TOOLING.md`, `REVIEW_NOTES.md`) carry a SUPERSEDED banner and exist for audit-trail value only — do not read them as design guidance.

What this means in practice:

- **Brand decisions** — read [`SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md) (short index) and [`claude-design-output/README.md`](claude-design-output/README.md) (long-form rules).
- **Locked palette / type / motion** — `claude-design-output/colors_and_type.css` is the source; `design/tokens.ts` mirrors it (same key shape, revalued).
- **Hero variants** — `claude-design-output/ui_kits/marketing/` ships three production-ready hero compositions with `hero-scene.js` (Three.js minimal scene) and a switcher (`index.html`).
- **Voice & copy** — locked headline/sub-line/CTA strings carry forward verbatim. The surrounding section copy in legacy `COPY.md` is not load-bearing anymore.
- **Forbidden colors / patterns** — blue (any temperature), purple-pink AI gradient, **warm-clay `#B86F3D`** (the prior accent — now explicitly banned), mesh gradients, glassmorphism, noise overlays, raster imagery, Lottie, Rive, post-processing bloom, particle systems.

The product UI in `ma_gatekeeper/frontend/` continues to import from `design/tokens.ts`; values have shifted (champagne replaces signal-green; oxblood replaces warm-clay; warm-paper neutrals replace cool-green neutrals; Instrument Serif / Space Grotesk / Geist Mono replace Fraunces / Inter / JetBrains Mono) but the export shape is unchanged. No global Tailwind-class rename pass is required — migrate `bg-neutral-*` / `text-*` usages opportunistically when you touch the file for another reason.

---

---

## Phase status grid

| Phase | Deliverable | State | Cohort outcome | Hard-to-reverse decision logged |
|---|---|---|---|---|
| 0 — Tooling | `design/TOOLING.md` v3 | ✅ CONVERGED | 4-reviewer `expert-review-loop`, 2 rounds, mean 8.75/10 | n/a |
| 1 — Inspiration | `design/INSPIRATION.md` v3 | ✅ CONVERGED | 3-reviewer `design-team` challenge, 2 rounds + post-convergence polish | n/a |
| 2 — Copy | `design/COPY.md` v3.1 | ✅ CONVERGED | M&A Counsel + Devpost Judge + Voice & Cadence (R2 + R3 surgical fixes) | **§2 tagline architecture swap** (signed off — see §"Hard-to-reverse decisions" below) |
| 4 — Stack | `design/STACK.md` v2 | ✅ CONVERGED | Senior Frontend Engineer + Devpost Judge + Bug-hunter (R2 verification all GO) | Hero candidate locked to #2 contract-stack |
| 5 — System | `design/SYSTEM.md` v2 + R3 contrast-drift patch | ✅ CONVERGED | Independent AD + Component Builder cold-onboard + Accessibility Auditor (R2 verification all GO) | **Brand-vs-interactive color split** (signed off — see below) |
| 5 — Tokens.ts | `design/tokens.ts` v2 + 9 tests | ✅ CONVERGED | `feature-build-loop` 3 rounds, 3/3 GO R3 | (covered by Color split sign-off) |
| 5 — Wordmark | `design/SYSTEM.md` §Wordmark | ✅ LOCKED | Author Art Director (kill-switch defused by shipping spec) | Fraunces 600 / opsz 90 / -0.01em |
| 6 — Build (sections) | — | ⏸ NOT STARTED | Day-4 PM target | Component Builders spawn against locked tokens |
| 7 — Polish + video | — | ⏸ NOT STARTED | Day-7 (2026-05-30) target | — |
| 8 — QA + final review | — | ⏸ NOT STARTED | Day-7+ | `expert-review-loop` final-gate panel of 4 |

---

## Files inventory (load-bearing)

```
design/PLAN.md                   v3 — locked plan, do NOT silently amend (PLAN-section changes need Supervisor sign-off)
design/TOOLING.md                v3 — Phase-0 lock; tooling decisions canonical
design/INSPIRATION.md            v3 — Phase-1 lock; "what we're stealing" categorized
design/COPY.md                   v3.1 — Phase-2 lock; 5 user-action placeholders in §17
design/STACK.md                  v2 — Phase-4 lock; FA verdict 7/10 honest
design/SYSTEM.md                 v2 + R3 patch — Phase-5 lock; brand-vs-interactive split documented at §Architectural decision
design/tokens.ts                 v2 — code source-of-truth; 9 invariant tests in tokens.test.ts
design/tokens.test.ts            9 tests (3 weird-lift + 3 contrast + 3 filled-badge inverse)
                                 RUN: `cd design && node --test --experimental-strip-types tokens.test.ts`
                                 (Node 20.11.1 per ma_gatekeeper/frontend/.nvmrc)
design/REVIEW_NOTES.md           Audit trail of every reviewer round
design/screenshots/              5 categorized empty dirs awaiting Playwright capture pass (typography/color/motion/composition/voice)

ma_gatekeeper/frontend/tailwind.config.ts   v4 — imports from ../../design/tokens, hex codes torn out
ma_gatekeeper/frontend/app/globals.css      v3 — :root custom properties, focus-ring rule, a {color}, scoped reduced-motion, .font-mono ligatures off
ma_gatekeeper/frontend/app/layout.tsx       Dark-default per PLAN §5.1 (bg-neutral-900 text-neutral-50)
ma_gatekeeper/frontend/components/findings-pane.tsx   bg-blue-50 leak closed → bg-lane-clear/10
ma_gatekeeper/frontend/.nvmrc               20.11.1
ma_gatekeeper/agent/server.py               _frame_lockdown middleware at L533+ (X-Frame-Options: DENY + CSP frame-ancestors 'none')
ma_gatekeeper/tests/test_server_stream.py   +3 frame-lockdown tests (closes TOOLING §4 task 4)
```

---

## Hard-to-reverse decisions (signed off by Supervisor, with reversion paths)

### (A) Brand-vs-interactive color split — Supervisor sign-off 2026-05-27

`--brand-primary: #0F4A38` is **decorative-only** (logo wash, OG card, brand surface ≤5% of viewport).
`--text-interactive: #4A9D7E` (NEW v2) carries all text/focus/link surfaces — verified 5.75:1 on `--neutral-900` (claimed 4.51:1 conservatively in SYSTEM).

**Why**: PLAN §5.1 locked the deep-forest range `#0E3D2E`–`#0E5D4A` tied to the M&A semantic story. Lightening `--brand-primary` to clear 4.5:1 would push past `#4A9D7E` into wellness-app green and break the locked PLAN §5.1 thesis. Split is the only path that preserves both.

**Reversion**: not recommended (would re-introduce the contrast lie); if it must happen, the path is to undo the split in `design/tokens.ts:57-69` and `design/SYSTEM.md:54-77`, then re-pick a brand color outside PLAN §5.1's range.

**Mechanical guard**: `design/tokens.test.ts:58-66` asserts `--text-interactive` and `--lane-clear` contrast ≥ 4.5:1 against `--neutral-900`.

### (B) COPY §2 tagline architecture swap — Supervisor sign-off 2026-05-27

`§2 hero` displays the cadence-led alt-1 *"Every flag, sourced. Every verdict, traced. Every span, clickable."*
The locked PLAN §2.1 line *"M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from"* is **preserved verbatim** at:
- `design/COPY.md:103-107` (§2 anchor sub-line)
- `design/COPY.md:447-448` (§15 OG truncation)

**Why**: Devpost Judge found the 24-word PLAN-locked line cannot do the juror-5s-stop hero job. Cadence-led promotion echoes the §6/§11 three-beat fragment cadence (voice coherence top-to-bottom). PLAN §2.1's load-bearing claims (artifact name, Arize Phoenix integration, audit posture) all land in the sub-line + OG; hero handles the 5-second job.

**Reversion** (if user disagrees): one-line swap at `design/COPY.md:101-107` — flip the §2 hero text with the §2 anchor-sub-line text. The DELTA table at top of COPY.md documents the path explicitly.

---

## Open queue — user-action (only you can resolve)

| Item | Where | Deadline |
|---|---|---|
| `npm install` in `ma_gatekeeper/frontend/` to commit lockfile | `frontend/` | ASAP — unblocks `size-limit` CI + `eslint-plugin-tailwindcss` rule |
| Playwright MCP install (optional but recommended) | Claude Code MCP settings | Day-5+ — unblocks field-verification of 4 hex anchors; also unblocks Phase-1 screenshot capture |
| `<<CONTACT-EMAIL>>` placeholder resolution | `design/COPY.md` §17, used in §6/§14 | Day-6 noon (legal-review gate) |
| `<<TOS-URL>>` + `<<GOVERNING-LAW>>` placeholders | `design/COPY.md` §17, used in §13 footer | Day-6 noon |
| `<<DEMO-DEAL-1..5>>` labels | `design/COPY.md` §17, used in §9 demo dropdown | Day-5 (need real EDGAR deal IDs from `ma_gatekeeper` allow-list) |
| `<<USER-CONFIRM>>` SOC 2 / pen-test target dates | `design/COPY.md` §17 §6 bullet 5 | OR strike the language entirely; current default is "Out of scope (hackathon). Production roadmap; target date set with first regulated engagement." |
| Option-A foundry funding decision (~$500-700 for GT Sectra + Berkeley Mono) | `design/SYSTEM.md` §Wordmark + §Typography | Window technically closed Day-3 EOD; reopenable. Default (Option B Fraunces + Inter + JetBrains Mono, all OFL/$0) is **locked and shipping**. |
| `<<DOMAIN>>` + `<<TEAM-NAME>>` + `<<REPO>>` + `<<BUILD-SHA>>` | `design/COPY.md` §13 footer | Build-time substitution |
| GC-persona legal review of §11 FAQ answers + §6 honesty block | A real GC if available; else GC-persona reviewer | Day-6 noon pre-merge gate per PLAN §6.1 |

---

## Open queue — next-session orchestrator (agent-actionable)

**Day-4 PM (today, if continuing this session)**:
1. **Day-4 mobile gate** per PLAN §6.1 — scroll-jacked hero on 375px viewport must feel right. If not, fall back to triggered Framer reveals (STACK.md §Perf budgets names the Day-5 static-play-card as the perf-recovery lever).
2. **Hero base layout** — Component Builder spawn against the locked tokens. Hero locked to candidate #2 (contract-stack via Framer-orchestrated SVG; ~25KB Framer + ~0KB SVG JS).

**Day-5**:
3. **Moneymoment build** (the §6.4 audit-trail section, Day-5 sole-focus per PLAN). 1.5 viewports, the engineered screenshot frame at `--text-hero-display` 240px / 96px mobile. GSAP scoped to this one scene (`pin: true, scrub: 1, end: "+=150%"`). If gate fires, drop to static designed play card (preserves the typography-layer weird-lift).
4. **Day-5 EOD scope freeze** — no new §2.2 sections after this point.

**Day-6**:
5. Numbers section (two-layer; Wilson 95% LB display) + "What this is not" (concrete fielded data, GC-persona legal-review at noon) + Reflector loop (static SVG if animation at risk per PLAN §6.1 Day-6 noon gate) + Built-on/Where-it-lives + FAQ + footer.
6. OG image (`@vercel/og` adopted; Day-6 noon kill-switch to static PNG).

**Day-7**:
7. Polish + `expert-review-loop` final round (per PLAN §3.1 final-gate trigger) + `verify` browser drive + Devpost video recording (script locked in COPY.md §16) + deploy.

---

## How to spawn agents (per the updated `design-team` skill)

The skill was updated this session to close 3 real failure modes. Key rules — read these before spawning anything:

1. **Always invoke the Supervisor first** (Step 1) — orchestrator does NOT make dispatch decisions inline. Skill rule documented in `.claude/skills/design-team/SKILL.md` Step 1 + "Common shortcuts to refuse" #1.

2. **Always spawn the Supervisor agent for Step 3** — orchestrator does NOT embody the Supervisor role for reconciliation. Documented in Step 3 + shortcut #2.

3. **Hard-to-reverse document deliverables REQUIRE a 3-reviewer cohort gate** (Step 2b — added 2026-05-27). Authors do NOT validate their own drafts. Cohort is INDEPENDENT of the author. Documented in Step 2b + shortcut #5.
   - **SYSTEM.md** cohort: Independent Art Director / Component Builder cold-onboard / Accessibility Auditor.
   - **STACK.md** cohort: Senior Frontend Engineer / Hackathon Judge / Bug-hunter.
   - **COPY.md** cohort: M&A Counsel / Devpost Judge / Voice & Cadence specialist (4 is acceptable given legal exposure).
   - **tokens.ts** code: `feature-build-loop` 3-reviewer cohort (goal-alignment / code-quality / bug-hunter; security/perf optional).

4. **Soft docs stay author-self-validated**: TOOLING.md / INSPIRATION.md / REVIEW_NOTES.md / PROJECT_LOG.md.

5. **Carve-out**: minor polish (typo, rename propagation, single-bullet tightening) — Supervisor can wave the cohort at Step 3, document the carve-out in PROJECT_LOG.

---

## Skill-process notes worth knowing

- **The contrast-lie pattern**: two contrast lies (`#0F4A38` claimed 4.5:1 actual 1.89:1; `#F4F6F3` on `#B86F3D` claimed verified actual 3.59:1) shipped from author self-validation. Both caught by independent cohorts when they finally ran. Mechanical defense: `design/tokens.test.ts` tests 4-9 use WCAG 2.1 formula + assert ≥4.5:1; the v1 hexes would fail at PR time.
- **Cross-skill fix convention** (open question, logged): the R3 surgical SYSTEM.md spec-drift fix was applied inside the tokens.ts `feature-build-loop` for expedience, not by the design-team SYSTEM Builder. Convention not normalized — flag for next session: probably "OK with documented cross-skill note + handoff back to Supervisor at Step 3."
- **PLAN §3.3 hard-to-reverse decisions**: any change to color / typography / motion-language / framework / wordmark / PLAN-locked tagline requires Supervisor + Art Director sign-off captured in PROJECT_LOG. Two such sign-offs landed this session (color split, tagline swap); both have explicit reversion paths above.

---

## What changed this session vs prior

Net additions/changes vs the prior `PROJECT_LOG.md` tail:
- 3 doc-Builder passes (SYSTEM v1 → v2 + R3 patch; STACK v1 → v2; COPY v3 → v3.1)
- 3 rounds of `feature-build-loop` for tokens.ts v1 → v2 with 9 invariant tests
- 13 reviewer-verdict outcomes across rounds (10 doc + 3 tokens cohort)
- 1 Supervisor Step-3 reconciliation with 2 hard-to-reverse sign-offs
- 1 PROJECT_LOG entry documenting the full retroactive correction
- 1 `design-team` skill update: Step 2b mandates cohort for hard-to-reverse docs + Common shortcut #5 names the author-as-reviewer failure mode

---

## Quick verification commands (cold pickup)

```bash
# Sanity: token tests pass
cd /Users/lucas/Documents/Projects/devpost/arize_project/design
node --test --experimental-strip-types tokens.test.ts
# Expected: 9 pass / 0 fail

# Sanity: no contrast lies survive (grep the 3 v1-failed hexes)
grep -rn "#F4F6F3" tokens.ts SYSTEM.md | grep -v "neutral-50\|R3 corrected\|v1 failed"
# Expected: zero hits (every #F4F6F3 reference is either the legitimate --neutral-50 value or an audit-trail referent)

# Sanity: no banned hex codes in frontend
grep -rn "lane-auto\|lane-watch\|#16a34a\|#eab308\|#dc2626" /Users/lucas/Documents/Projects/devpost/arize_project/ma_gatekeeper/frontend/
# Expected: zero hits

# Sanity: frame-lockdown middleware is tested
cd /Users/lucas/Documents/Projects/devpost/arize_project/ma_gatekeeper
python -m pytest tests/test_server_stream.py -k frame_lockdown -v
# Expected: 3 passed (test_frame_lockdown_sets_x_frame_options_deny_on_healthz, sets_csp_frame_ancestors_none_on_healthz, applies_to_reflect_endpoint_regardless_of_status)
```

---

## Recommended first move in the next session

1. **Read this file** (top to bottom — it's the whole picture in <250 lines).
2. **Check the user-action queue** — resolve any newly-decided items (lockfile / Playwright / COPY placeholders).
3. **If continuing the design build**: invoke the `design-team` skill with `"advance to Phase 6 — Day-4 mobile gate + hero base layout"`. The Supervisor will dispatch.
4. **If verifying the converged state first**: run the four sanity commands above.
5. **If picking a different direction** (e.g. product-track work): the design track is paused at a clean convergence point. Nothing here blocks the product track; `ma_gatekeeper/HANDOFF.md` is the entry point.
