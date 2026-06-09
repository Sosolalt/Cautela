---
name: design-team
description: Run the M&A Gatekeeper landing-page design work as a multi-agent specialist team (Supervisor, Art Director, Frontend Architect, Motion Designer, Copy Lead, Component Builders, QA/Perf). Use whenever the user asks to do, advance, review, or unblock any phase of design/PLAN.md, produce a design deliverable (TOOLING / INSPIRATION / COPY / STACK / SYSTEM / tokens / REVIEW_NOTES), or generally "have the team think together" about design. Spawns role-specialists in parallel, reconciles their outputs, and loops to convergence.
---

# Design Team

Orchestrates the multi-agent team defined in [design/PLAN.md §3](../../../design/PLAN.md). The plan is the source of truth — this skill is the *operating manual* for executing it.

The premise of the plan: a flat "spawn five agents and average their output" produces mush. We use structured roles with explicit deliverables and one decision-maker. This skill enforces that structure.

## When to invoke

Invoke when the user asks to:
- Run, advance, or unblock any **Phase** of `design/PLAN.md` (Phase 0 tooling through Phase 8 sign-off).
- Produce or update any deliverable in `design/` (`TOOLING.md`, `INSPIRATION.md`, `COPY.md`, `STACK.md`, `SYSTEM.md`, `tokens.ts`, `REVIEW_NOTES.md`).
- "Have the design team think together," "get the design agents on this," "what would the team do here."
- Make a hard-to-reverse design decision (color, typography, animation language, framework) — these require Art Director + Supervisor sign-off per §3.3.
- Resolve a disagreement between prior design choices — written 1-paragraph position from each side, Supervisor decides.

Do NOT invoke for:
- Routine product/code work in `ma_gatekeeper/` that is not design-track.
- Single-file edits that are clearly within already-locked tokens (a Component Builder running solo doesn't need the whole team — just read `SYSTEM.md` and ship).
- Pure review of an already-built artifact — use `expert-review-loop` instead (and the Supervisor will call it at the two checkpoints anyway: post-plan, pre-launch).

## The roles (briefs live in `roles/`)

Each role has a self-contained brief that you pass verbatim into an `Agent` call. **Do not paraphrase the briefs** — they encode hard rules from the plan that drift if rewritten.

| Role | Brief | Persistence | Decision rights |
|------|-------|-------------|-----------------|
| **Supervisor / Creative Director** | [supervisor.md](roles/supervisor.md) | Persistent | Veto on anything. Owns `PROJECT_LOG.md` design entries. |
| **Art Director** | [art-director.md](roles/art-director.md) | Persistent | Owns palette, type, motion principles, forbidden-patterns list. Section-completion review only (≤1/day per §3.2). |
| **Frontend Architect** | [frontend-architect.md](roles/frontend-architect.md) | Persistent | Owns stack, perf budgets, scaffold cleanup. Reviews every PR for bundle + re-renders. |
| **Motion Designer** | [motion-designer.md](roles/motion-designer.md) | Persistent | Owns animation choreography, timing system, page-load sequence. |
| **Copy Lead** | [copy-lead.md](roles/copy-lead.md) | Persistent | Owns `COPY.md`, voice rules, FAQ answers, video narration script. |
| **Component Builder** | [component-builder.md](roles/component-builder.md) | Ephemeral (2–3 per section) | Implements within locked tokens. Escalates only on token-violation or novel pattern. |
| **QA / Perf** | [qa-perf.md](roles/qa-perf.md) | Ephemeral (polish pass) | Lighthouse, axe-core, real-device, dark-mode parity, reduced-motion. |

## How to run the team

### Step 1 — Supervisor decides what phase / question we're on

Before spawning specialists, **always** invoke the Supervisor first (in the foreground, single agent call). It reads `design/PLAN.md`, `PROJECT_LOG.md`, and any deliverables already shipped, and outputs:

1. Which Phase / section we're working on.
2. Which roles need to be spawned for this turn (and which can be skipped).
3. The specific written spec each spawned role receives (per §3.2 handoff rule: every handoff is a written spec).
4. Whether this is a **parallel** round (independent specialists each produce in their own lane) or **sequential** (one role's output is input to another).
5. Whether `expert-review-loop` should run as the final gate (it does at the two checkpoints: post-plan, pre-launch).

Pass the Supervisor the user's request verbatim plus the path to `design/PLAN.md`. Its output is the dispatch plan for Step 2.

### Step 2 — Spawn the specialists per the Supervisor's dispatch plan

For a **parallel round**: send a single message with multiple `Agent` tool-uses, one per role, each receiving the written spec the Supervisor produced. Common parallel sets:

- Phase 1 inspiration: Art Director (owns) + Copy Lead (assists).
- Phase 2 message/IA: Copy Lead (owns) + Art Director (reviews — runs after Copy Lead).
- Phase 5 system: Art Director (owns) + Motion Designer (parallel — motion language lives in `SYSTEM.md`).
- Phase 6 build: 2–3 Component Builders on **independent sections only** (hero / FAQ / footer can parallelize; problem-section and how-it-works share visual language → sequential).

For a **sequential round**: chain the calls. The plan's hard sequence points:
- Typography lane choice (§5.2 Lane A vs B) blocks the wordmark (§5.6).
- Tokens (`tokens.ts`) block all Component Builders.
- Hero candidate lock (§1.4) blocks Day-3 base layout.

### Step 2a — Code-producing sections go through `feature-build-loop`

For any specialist round whose deliverable is **code** (a Component Builder shipping a section, a new agent, a new endpoint, an eval script), the Supervisor does NOT spawn Builders directly. Instead it invokes the `feature-build-loop` skill, passing the written spec as input. That skill runs the gated cycle:

```
Builder(s) write → Reviewer cohort (goal-alignment + code-quality + bug-hunter +
  optional security/perf) grades → if any ITERATE, Builders fix → re-grade →
  loop until every reviewer returns GO → merge
```

The Reviewer cohort gate is **non-bypassable** — design-team's existing Art Director section-completion review is *additive* (visual coherence), it does not substitute for the cohort's code-quality / bugs / goal-alignment verdict. A section is not "done" until the cohort returns unanimous `GO` *and* the Art Director signs off at the daily section-completion review.

For non-code rounds (writing `COPY.md`, drafting `SYSTEM.md` tokens, choosing the typography lane), the specialists run directly without the build loop — there's no code artifact to gate.

### Step 2b — Hard-to-reverse document deliverables require a 3-reviewer cohort gate

**Hard-to-reverse document deliverables MUST go through a 3-reviewer cohort before they ship.** This rule was added after a real failure mode: Phases 4/5 shipped with "VALIDATED 9/10" from author self-validation (Frontend Architect on STACK.md, Art Director on SYSTEM.md); when an independent cohort actually ran, it caught ~50 issues including 3 critical blockers (a 1.89:1 contrast lie claimed at 4.5:1, fabricated SOC 2 dates, a self-contradiction across §11.5 vs §6). Author self-validation is not a reviewer cohort. The pattern is documented in the "Common shortcuts to refuse" section below as #5.

**Which deliverables count as hard-to-reverse** (per PLAN §3.3 + precedent):

- `design/SYSTEM.md` — any color / typography / motion-language / iconography / primitives / wordmark decision.
- `design/STACK.md` — framework lock, perf-budget commitments, animation library split.
- `design/COPY.md` — tagline (§2 hero), honesty-block fielded answers (§6), GC-FAQ answers (§11), video narration script (§16). Any change to a PLAN-locked decision (e.g. swapping the locked tagline into the sub-line) is hard-to-reverse by definition.
- `design/tokens.ts` — already covered by `feature-build-loop` per Step 2a; the cohort gate is mandatory for code artifacts regardless.

**Which deliverables stay author-self-validated** (soft docs):

- `design/TOOLING.md` updates (status flips, deferred-item dates).
- `design/INSPIRATION.md` additions (new reference rows, what-to-steal annotations).
- `design/REVIEW_NOTES.md` audit-trail appends.
- `PROJECT_LOG.md` entries.

**Cohort structure for hard-to-reverse doc deliverables** (mirrors `feature-build-loop` for code):

- **3 reviewers minimum**, spawned in parallel after the doc Builder/author ships their draft. Reviewers must be **independent** of the author — the author of SYSTEM.md (Art Director) cannot also be the SYSTEM.md reviewer; spawn an Independent Art Director + a Component Builder cold-onboard + an Accessibility Auditor (or equivalent non-overlapping specialties).
- The 3 reviewers are picked per-doc to cover non-overlapping lanes. Typical packs:
  - **SYSTEM.md**: Independent Art Director / Component Builder cold-onboard / Accessibility Auditor.
  - **STACK.md**: Senior Frontend Engineer / Hackathon Judge persona / Bug-hunter (internal consistency + cross-doc).
  - **COPY.md**: M&A Counsel / GC persona / Devpost Hackathon Judge / Voice & Cadence specialist (4 is acceptable for COPY given the legal exposure surface).
- Convergence rule mirrors `feature-build-loop`: **unanimous GO from every reviewer; max 4 rounds.**
- The cohort gate is **additive** to the Step-3 Supervisor reconciliation — both run. Reviewer cohort gates content; Supervisor reconciliation gates cross-artifact consistency + hard-to-reverse sign-off.

**When a cohort is genuinely overkill** (the option-2 carve-out): if the doc change is a minor polish (e.g. tightening a single bullet, fixing a typo, propagating a rename) and does NOT touch a PLAN-locked decision or a hard-to-reverse token, the Supervisor at Step 3 can wave the cohort and rely on their own reconciliation pass. Document the carve-out in `PROJECT_LOG.md` so the next reader sees that the cohort was deliberately skipped, not bypassed.

### Step 3 — Reconcile

**Always spawn the Supervisor agent for the reconciliation pass.** This is symmetric to Step 1: the Supervisor is a *role*, not the orchestrator. The orchestrator (you) does not embody the Supervisor for Step 3 just because the dispatch plan in Step 1 came from one. A fresh Supervisor spawn with explicit access to the round's outputs is what closes the round — not an orchestrator summary.

Why this rule exists: a real failure mode caught in practice was the orchestrator writing a "looks-converged" `PROJECT_LOG` entry without spawning the Supervisor, missing 4 of 5 specialist-flagged cross-references in the process. Step 3 without a spawned Supervisor is a shortcut, not a reconciliation. (See "Common shortcuts to refuse" at the bottom of this file.)

**The Step 3 Supervisor spawn must verify all of the following** (do NOT brief it as "reconcile generally"; brief it as the explicit checklist below):

1. **Per-specialist flagged cross-references.** Every specialist may end their output with a "for Supervisor to verify" list — e.g. the Motion Designer's 5 cross-references on token-name parity, conditional bundle deps, register assignment, etc. The Supervisor spawn must walk each one and tag VERIFIED / GAP / REJECT-as-shipped with file:line refs. **Skipping any specialist's flagged list is the failure mode this rule defends against.**
2. **Internal consistency across all artifacts shipped this round.** Same token names across STACK + SYSTEM + tokens.ts. Same animation library names. Same scaffold-cleanup status. No contradictions on kill-switch outcomes or wordmark defaults.
3. **Kill-switch defusal for today's date** (see Step-3 kill-switch list below). Day-3 EOD locks tokens.ts + SYSTEM + wordmark; Day-5 EOD locks moneymoment v1; etc. If a gate is red, the Supervisor invokes the fallback *during this Step 3 spawn*, not "tomorrow."
4. **Hard-to-reverse decisions logged in `PROJECT_LOG.md`** per PLAN §3.3 (color, typography, animation language, framework, wordmark). Every such decision in this round needs an explicit log line — not a parenthetical buried inside a verdict block.
5. **The `PROJECT_LOG.md` entry actually matches what shipped on disk.** Read the tail of `PROJECT_LOG.md` and audit against the artifacts. Line counts, file names, decision rows, kill-switch defusal status all need to match reality, not the orchestrator's claim of reality.

The Supervisor's output ends with one of three verdicts:

- **`CONVERGED — Step 3 reconciliation complete. PROJECT_LOG entry valid. Phase X ships.`** All five checks pass (or any gaps are ACCEPTED-AS-SCOPED with a written reason — e.g. a specialist-flagged item lands at an enforcement layer that catches regression at a later phase).
- **`REJECT — must fix before round closes: [specific items]`** with the minimum edits named.
- **`DISAGREEMENT — [parties] disagree on [issue]; requesting 1-paragraph written position from each side, Supervisor decides on next pass.`** Per PLAN §3.3, Supervisor decides on the second round at the latest. Do NOT loop endlessly.

If the Supervisor returns `REJECT` or `DISAGREEMENT`, the orchestrator spawns the relevant role(s) to apply the fix, then re-spawns the Supervisor for a Step 3 second pass. The Supervisor is the *only* role that can sign off the round.

### Step 4 — Active kill-switches (reference list — folded into Step 3)

The plan has explicit kill-switches (summary in PLAN §6.1). The Supervisor's Step 3 reconciliation **must** check the gates active for today's date:

- **Day-1 EOD**: iframe-OIDC-Safari-ITP spike — unresolved → iframe permanently off, mock-only.
- **Day-2 EOD**: framework (§4.1), typography lane (§5.2), hero candidate (§1.4), tagline (§2.1), GC-FAQ draft answers.
- **Day-3 EOD**: tokens + SYSTEM lock, wordmark lock, hero base layout.
- **Day-4 morning**: 3D prototype "wow" check → kill to 2D if no.
- **Day-4 mobile gate**: scroll-jacked hero on 375px → fallback to Framer reveals if no.
- **Day-5 morning**: Phoenix trace animation gate → static "play" card if no.
- **Day-5 EOD**: moneymoment v1 + scope freeze on §2.2 section list.
- **Day-6 noon**: Reflector animation / OG image / Built-on / FAQ collapse decisions.

If a gate is red, the fallback fires *during the Step 3 Supervisor spawn*, not "try again tomorrow." Kill-switch outcomes get logged in `PROJECT_LOG.md` in the same entry as the round close.

### Step 5 — Final gate

At Phase 8 (pre-launch), invoke the `expert-review-loop` skill with the panel from §8.3:
- Hackathon Judge persona
- Skeptical M&A Counsel / GC persona
- Senior Frontend Engineer
- Accessibility Auditor

Iterate until all four return `VALIDATED`. Apply feedback between rounds via the relevant specialist (Art Director for visual, Copy Lead for copy, Frontend Architect for technical, QA/Perf for accessibility).

## The central tension (must be honored every round)

Per [design/PLAN.md §0](../../../design/PLAN.md): the content is enterprise legal-tech; the vibe is playful, color-forward, motion-rich. Every decision must answer: **does this make a serious tool feel inevitable and fun, or does it make a serious tool feel unserious?** The Art Director has veto power on anything that fails that test. The Supervisor enforces that every specialist's output passes this check before reconciliation.

Composition rule (§0.1): playful lives in micro-interactions, hover states, accent usage, footer easter egg, 404, OG image. Serious owns macro grid, typography, color system, numbers, "What this is not," FAQ answers, moneymoment trace card, footer credits. If a component reads as both, the Art Director picks one and rewrites until it commits.

## Outputs

Every invocation of this skill ends with one or more of:
- A new or updated file under `design/` (per the deliverables list at the end of `PLAN.md`).
- A new `PROJECT_LOG.md` entry for any hard-to-reverse decision (§3.3).
- A clear written next step for the user (the next gate, the next blocked item, the next role to spawn).

Never end the skill with "the team thought about it" and no artifact. The plan is rules-of-the-game; this skill produces moves.

## Common shortcuts to refuse

These are real failure modes caught in past runs of this skill. The orchestrator (you) is the one most likely to take them — they look like efficiency in the moment and produce silent gaps that cost a round to recover.

### 1. Bypassing Step 1 (write the deliverable yourself)

**Symptom**: the user says "do Phase X" and the orchestrator drafts the Phase-X artifact directly, skipping both Supervisor (Step 1) and the owner specialist (Step 2). The artifact looks fine. The pipeline says nothing about whether it's actually fine.

**Why it happens**: terse user prompts ("go on with phase 2") feel like authorization to skip ceremony. Earlier phases that went through `expert-review-loop` separately make Step 1's "always invoke" feel optional.

**Refuse it by**: re-reading Step 1's "**always** invoke the Supervisor first" before the first edit. If you are about to write `design/COPY.md` / `design/STACK.md` / `design/SYSTEM.md` / etc. without having spawned the Supervisor in *this* turn, stop and spawn the Supervisor. A retroactive correction is more expensive than spawning first.

### 2. Embodying the Supervisor for Step 3 (orchestrator-as-Supervisor reconciliation)

**Symptom**: the parallel specialists return, the orchestrator reads all their outputs, writes a `PROJECT_LOG.md` entry that summarizes what shipped, and declares the round closed. No Supervisor agent was spawned for the reconciliation. The Motion Designer's "for Supervisor to verify" cross-references were never explicitly walked. The kill-switch defusal was claimed in the log but not audited.

**Why it happens**: Step 1 already spawned the Supervisor for the dispatch plan; it feels redundant to spawn it again for the close-out. The orchestrator has all the context. Reading the artifacts and writing a summary feels like reconciliation.

**Refuse it by**: treating Step 3 like Step 1 — **always spawn the Supervisor agent for the reconciliation pass.** The orchestrator's job is to spawn roles, not to embody them. Brief the Step 3 Supervisor spawn with the explicit 5-item checklist (per-specialist cross-references, internal consistency, kill-switch defusal, hard-to-reverse log entries, PROJECT_LOG audit). The Supervisor returns CONVERGED / REJECT / DISAGREEMENT; only then is the round closed.

### 3. Skipping a specialist's "for Supervisor to verify" tail block

**Symptom**: a specialist (most often Motion Designer or Art Director) ends their output with a numbered list of cross-references for the Supervisor to walk. The orchestrator merges the specialist's main output into the relevant `design/*.md` file and moves on, never feeding the cross-reference list into a Step-3 Supervisor spawn.

**Why it happens**: the cross-reference list reads as housekeeping after the main deliverable. It's easy to treat as "noted" instead of "to verify."

**Refuse it by**: when briefing the Step-3 Supervisor spawn, copy every specialist's cross-reference list into the brief verbatim and instruct the Supervisor to tag each one VERIFIED / GAP / REJECT-as-shipped with file:line refs. If a cross-reference can't be verified at the artifact layer this round, it gets ACCEPTED-AS-SCOPED with a written reason naming when/where it *will* be verified — not silently dropped.

### 4. Treating `expert-review-loop` as a substitute for design-team reconciliation

**Symptom**: a round closes without the Step 3 Supervisor pass, but with a Round-A/B `expert-review-loop` against the outputs. The orchestrator says "we reviewed it, so it's reconciled."

**Why it happens**: `expert-review-loop` has its own multi-reviewer convergence record. Design-team's Step 3 Supervisor pass and `expert-review-loop`'s reviewer cohort serve different functions, but both *feel like* "review."

**Refuse it by**: `expert-review-loop` is a quality gate on a finished artifact (per PLAN §3.1 it runs at post-plan and pre-launch checkpoints only). The design-team Step 3 Supervisor pass is the *internal* reconciliation of a parallel round — kill-switch defusal, specialist cross-references, decision logging. They are not interchangeable. Both run when both are required; neither substitutes for the other.

### 5. Treating author self-validation as a reviewer cohort gate

**Symptom**: Phase 4 ships with the Frontend Architect's own self-verdict ("VALIDATED 9/10"). Phase 5 ships with the Art Director's own self-verdict ("VALIDATED 9/10"). Phase 2 ships with a single reviewer after the Copy Lead. No independent 3-reviewer cohort runs on any of the docs. The Supervisor's Step-3 reconciliation only catches cross-artifact consistency, not content quality. When a real cohort eventually runs (because a user catches the gap), it surfaces ~50 issues including 3 critical blockers (a 1.89:1 contrast lie claimed as 4.5:1, fabricated SOC 2 dates, a self-contradiction across §11.5 vs §6). Then, the v2 fix-pass contains a SECOND contrast lie of the same shape (`text-on-accent-clay #F4F6F3` = 3.59:1) that the corrected spec authored — only the code cohort (`feature-build-loop` on `tokens.ts`) catches it, because the doc cohort does not yet exist.

**Why it happens**: specialists are role-tagged and bring domain expertise to their own draft. Their self-verdict feels load-bearing. The skill's Step 2 only says "spawn the specialists per the dispatch plan" — it does NOT explicitly require an independent reviewer cohort gate before document deliverables ship. The author/reviewer roles collapse into one. Authors mark their own work pass/fail.

**Refuse it by**: hard-to-reverse document deliverables (`COPY.md` / `SYSTEM.md` / `STACK.md` content per PLAN §3.3 — color, typography, motion-language, framework, tagline, fielded honesty-block, GC-FAQ answers, video narration) **require a 3-reviewer cohort gate per Step 2b above**. Authors do not validate their own drafts. The cohort is INDEPENDENT of the author — spawn an Independent Art Director if the Art Director wrote SYSTEM.md; spawn a Senior Frontend Engineer + Hackathon Judge + Bug-hunter if the Frontend Architect wrote STACK.md; spawn an M&A Counsel + Devpost Judge + Voice & Cadence specialist if the Copy Lead wrote COPY.md. Soft docs (`TOOLING.md` updates, `INSPIRATION.md` additions, `PROJECT_LOG.md` entries) stay author-self-validated. The cohort gate is non-bypassable for hard-to-reverse content; the Step-3 Supervisor reconciliation is additive, not a substitute.

**When you can carve out**: minor polish that doesn't touch a PLAN-locked decision (typo, rename propagation, single-bullet tightening). The Supervisor at Step 3 documents the carve-out in `PROJECT_LOG.md` so the next reader sees the cohort was deliberately skipped, not bypassed.
