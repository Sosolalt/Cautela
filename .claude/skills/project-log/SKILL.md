---
name: project-log
description: Maintain a structured, append-only PROJECT_LOG.md that captures the audit trail of a long-running project — initial plan, what got tested, what failed, what got implemented instead, current norm. Use when starting or resuming a multi-phase project, when the user asks for "a log" / "history" / "audit trail" / "what changed and when", or after each significant phase (plan iteration, code rewrite, reviewer round). Not for ephemeral todo lists.
---

# Project Log

A reusable structure for keeping a single authoritative file (`PROJECT_LOG.md` at the project root) that records the audit trail of a non-trivial project across sessions.

This is NOT a todo list and NOT a changelog. It is a **narrative log of decisions, claims, and reality** — what was believed at each phase, what reviewers/tests revealed, what was fixed instead, and what the current state actually is. The goal is that a teammate (or future-you, or a fresh Claude session) can read this file and pick up where things stand without re-doing the analysis.

## When to invoke

- The user starts a project that will span multiple phases (plan → review → code → review → ship).
- The user asks "record everything", "keep a log", "audit trail", "track decisions", "what changed".
- After a phase completes (plan converged, code reviewed, tests pass) — append a new section.
- When resuming work after a long gap — read the log first to recover state.

Do NOT use this skill for:
- Ephemeral session todos (use `TodoWrite`).
- Code-level change tracking (use git).
- Conversation summaries.

## File location and format

- **Location**: `PROJECT_LOG.md` at the project root. Single file, append-only narrative. Never split into multiple log files (that fragments history).
- **Format**: GitHub-flavored Markdown, single H1, then sectioned by phase or by review round.
- **Style**: written for a teammate who joins midway. Complete sentences. No unexplained shorthand. Be honest about what failed.

## Required sections

Every PROJECT_LOG.md should have these top-level sections, in this order:

1. **TL;DR** — 3-6 sentences. Updated at the END of every major phase. The version someone reads if they have 30 seconds.
2. **Phase 0 — Origin and idea selection** — what triggered the project, what alternatives were considered, why this one was chosen, with citations to the inputs.
3. **Phase N — [name of phase]** — one section per phase (plan iteration, code scaffolding, code review rounds, deployment, etc.). Each phase section should follow the per-phase template (below).
4. **What was tested** — what is and isn't covered by tests; which integration paths are deferred and why.
5. **What failed** — things that were claimed and then proven wrong (this is the section future-you most wants to read).
6. **Current norm** — what is true RIGHT NOW. Code state, plan state, outstanding work.
7. **Lessons** — generalizable takeaways, written in the imperative for future projects.
8. **Per-file last-edit map** — a small `file → version` table so the reader can see what's stable vs newly-rewritten.

## Per-phase template

```
### Phase N — [name]

**Inputs**: what artifacts/contexts existed at the start.
**Goal**: what this phase was supposed to produce.
**Approach**: what was actually done, in 2-4 sentences.
**Outcome**: result, scored honestly. If it failed or had to be redone, say so.
**Lessons** (optional): if anything generalizable came out of this phase.
```

## Per-review-round entry (for projects that use `expert-review-loop`)

For each review round, append a block like:

```
### Round X: [purpose]

**Reviewer verdicts**:
| Reviewer | Score | Status |
|---|---|---|
| Legal/M&A | 6.5 | NOT VALIDATED |
| ...

**Major issues flagged**: bulleted list, terse but specific (quote API names, line numbers when relevant).

**Fixes applied this round**: bulleted list of what changed, with the file(s) affected.

**Verdict at end of round**: how many reviewers converged, what's still open.
```

## What to write down (and what NOT to)

DO write:
- The decision that got made and why.
- The thing that was claimed and turned out to be false.
- The API signature that was wrong and the verified replacement (this is gold for future-you).
- The threshold/number that was hand-picked, and what replaced it once calibrated.
- The reviewer's sharpest one-line objection (these tend to keep teaching).

DO NOT write:
- Every commit message (git has this).
- Every tool call (the conversation has this).
- Praise. "The code is excellent" decays to "the code was excellent in May 2026".
- Speculation about future work — that goes in HANDOFF.md or plan.md.

## Update cadence

- **After every plan revision**: append a "Round N" entry under the plan-iteration phase, with the diff from the previous version.
- **After every reviewer round**: append the verdict table + applied fixes.
- **After every significant code rewrite**: bump the per-file last-edit map.
- **Whenever a claim is proven wrong**: append to the "What failed" section. This is the most-valuable kind of update because it prevents future you from repeating the mistake.

## When you resume a project

1. Read PROJECT_LOG.md first. Read TL;DR, then "Current norm", then "Per-file last-edit map".
2. Cross-check the per-file map against `ls`/`git log` — if reality has drifted from what the log says, the log is stale and your first job is to update it.
3. Read "What failed" before touching any code. The mistakes that already happened are the most likely ones to almost-happen again.

## Anti-patterns

- **The log becomes a brag sheet.** Strip praise; keep facts. A useful log says what went wrong as readily as what went right.
- **The log becomes a planning doc.** Plans go in `plan.md`. The log records what happened to the plan. They are different files.
- **The log becomes a todo list.** Todos belong in `TodoWrite` (in-session) or `HANDOFF.md` (cross-session). The log records outcomes.
- **One log per phase.** Don't split. Single file, append-only.
- **Markdown perfection.** Better to have a complete log with rough formatting than a polished log missing a phase.

## Starter template (copy-paste at project start)

```markdown
# Project Log — [Project Name]

**Goal**: [one-sentence aim].
**Deadline**: [date + timezone].
**Started**: [YYYY-MM-DD].
**Last updated**: [YYYY-MM-DD].

---

## How to read this log (resume protocol)

1. Read TL;DR below first (60 seconds).
2. Jump to "Current norm" — what is true RIGHT NOW.
3. Then "Per-file last-edit map" — what's stable vs newly rewritten.
4. Only then read phase narrative if you need the why.
5. Before touching any external SDK, read "What failed" → API signatures table.

---

## Operating constraints

- [Hard constraints from CLAUDE.md, user instructions, organization policy.]
- [User authorization phrases granted in-session, with their scope.]
- [Contact info, identity strings (SEC user agent, API keys location, etc).]

---

## TL;DR

[3-6 sentences. The version someone reads if they have 30 seconds. Update at end of every major phase.]

---

## Phase 0 — Origin and idea selection

### Inputs
- [Files / documents that triggered the project, with paths.]

### Alternatives considered
1. [Option A]: pros / cons.
2. [Option B]: pros / cons.

### Selected
[The choice + the reasoning.]

---

## Phase 0.5 — Research artifacts (if any)

[Quote the load-bearing conclusions from any research the project did,
because the transcripts may be lost. One subsection per research topic.]

---

## Phase 1 — [Name of phase, e.g. "Plan iteration"]

### Round 1: [Artifact name v1]

**What was drafted**: [terse description].

**Reviewers** (N parallel, specialist briefs): [list].

**Verdict**: [VALIDATED / NOT VALIDATED]. Score range.

**Major issues flagged**: [bulleted, specific].

### Round 2: [Artifact name v2]

**Changes applied**: [list].

**Verdict**:
| Reviewer | Score | Status |
|---|---|---|
| ...

[Repeat for each round.]

---

## Phase 2 — [Next phase, e.g. "Initial codebase scaffolding"]

[Per-phase template.]

---

## Phase 3 — [Next phase, e.g. "Expert code reviews"]

[Per-phase template. Include verdict tables and applied-fix lists for each round.]

---

## What was tested

[Categorize coverage by component. List what's deliberately deferred and why.]

---

## What failed

[A table of: claim → reality. This is the single most-valuable section
for future-you. Specifically include:]

| What was claimed | What turned out to be true |
|---|---|
| [API signature wrongly assumed] | [verified signature] |
| [metric wrongly computed] | [correct computation] |
| [scope estimate that was too optimistic] | [actual cost] |

---

## Current norm

### Code/artifact state
[What modules / files exist, in what version, with what test coverage.]

### Outstanding work
[Calendar-ordered. Mirror HANDOFF.md if there's one.]

### What I chose NOT to do (deliberate scope cuts)
[Each cut is here so future iterations don't accidentally re-introduce them.]

### Pre-commitments locked in
[Promises in the README / on the submission form. Don't change quietly.]

---

## Lessons for future projects

[Generalizable takeaways, written in the imperative.
"Verify external SDK signatures with WebFetch before writing code."
"Cut features over adding them."
etc.]

---

## Per-file last-edit map

```
path/to/file.py    vN  (what changed in vN)
...
```
```

## When the log grows too long

If `PROJECT_LOG.md` exceeds ~1000 lines, the cure is **summarization, not splitting.**

- Replace verbose round-N narrative with a 1-paragraph summary + the verdict table.
- Move detailed reviewer outputs to a `docs/archive/` folder (NEVER delete; this is the audit trail).
- Keep the API-signatures table fully detailed; that's the most-referenced section.
- Keep "Current norm" and "Per-file last-edit map" canonical — never archive these.

Splitting into multiple files (per-phase logs, per-quarter logs) is an anti-pattern. The point is single-file resume — one open file recovers full project state. Splitting forces the reader to know which file to open, which is exactly what the log is supposed to prevent.

## Companion skill

`expert-review-loop` produces the verdict tables that the log records. Pair the two: every review round generates an entry in PROJECT_LOG.md as part of its completion.

## Example structure (from a real project)

The M&A Gatekeeper project's `PROJECT_LOG.md` follows this skill exactly:

- TL;DR (4 sentences with final reviewer scores).
- Phase 0 — chose between 3 candidate ideas; recorded the synthesis logic.
- Phase 1 — 4 rounds of plan reviews, one entry per round, with verdict tables.
- Phase 2 — scaffold the code; honest "what I believed at this point" + "this was wrong".
- Phase 3 — 4 rounds of code reviews, verdict tables + applied fixes per round.
- "What was tested" — 31 unit tests categorized, plus the integration paths deliberately deferred.
- "What failed" — a table of fabricated API signatures and the verified replacements.
- "Current norm" — code state, plan state, outstanding HANDOFF work, pre-commitments.
- "Lessons" — 7 generalizable takeaways for future projects.
- Per-file last-edit map.

Total length: ~600 lines. Reading time: ~15 minutes. Recovers full project state in one session.
