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

### Step 3 — Reconcile

Each specialist returns a deliverable + a position. The Supervisor reads all of them and either:

- **Converges** → writes the unified output to the relevant `design/*.md` file, logs the decision in `PROJECT_LOG.md` if it's hard-to-reverse (per §3.3).
- **Surfaces a disagreement** → per §3.3, request a 1-paragraph written position from each side, then Supervisor decides. Do NOT loop endlessly — Supervisor decides on the second round at the latest.
- **Identifies a missing role** → spawn the missing specialist and re-run reconciliation.

### Step 4 — Gates and kill-switches

The plan has explicit kill-switches (summary in §6.1). Before declaring a round done, the Supervisor checks the active gates:

- **Day-1 EOD**: iframe-OIDC-Safari-ITP spike — unresolved → iframe permanently off, mock-only.
- **Day-2 EOD**: framework (§4.1), typography lane (§5.2), hero candidate (§1.4), tagline (§2.1), GC-FAQ draft answers.
- **Day-3 EOD**: tokens + SYSTEM lock, wordmark lock, hero base layout.
- **Day-4 morning**: 3D prototype "wow" check → kill to 2D if no.
- **Day-4 mobile gate**: scroll-jacked hero on 375px → fallback to Framer reveals if no.
- **Day-5 morning**: Phoenix trace animation gate → static "play" card if no.
- **Day-5 EOD**: moneymoment v1 + scope freeze on §2.2 section list.
- **Day-6 noon**: Reflector animation / OG image / Built-on / FAQ collapse decisions.

If a gate is red, the Supervisor invokes the fallback immediately — does not "try again tomorrow."

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
