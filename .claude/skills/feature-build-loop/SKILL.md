---
name: feature-build-loop
description: Build any new feature (UI section, agent, endpoint, eval, script) through a gated cycle — Builder cohort writes code, Reviewer cohort grades it across goal-alignment / code-quality / bug-hunt / (optional security & perf), Builders iterate on the feedback, loop continues until every reviewer returns GO. Use whenever the user says "build feature X", "add Y", "ship Z", "implement [section/agent/endpoint]", or any task that produces a code artifact that will be merged. Pairs with `design-team` for design-track features and runs standalone for backend/agent/eval work.
---

# Feature Build Loop

A gated build cycle. Builders ship code; a Reviewer cohort grades it; Builders iterate until every reviewer returns `GO`. No feature merges without unanimous `GO` from the cohort.

This is the codebase-side equivalent of `expert-review-loop` (which reviews documents/plans). The difference: `feature-build-loop` *includes* the build step in the cycle — Builders write code, reviewers gate, Builders fix, reviewers re-check, until convergence.

## When to invoke

Invoke whenever the user asks to:

- Build, add, implement, or ship a feature, section, agent, endpoint, script, or eval.
- "Make X happen" where X is a code artifact.
- Land a design section as code (this skill is the cycle the `design-team` skill hands off to for each section).
- Apply a non-trivial fix or refactor that needs review before merge.

Do NOT invoke for:

- Pure documentation edits (use direct Edit).
- One-line typos / dependency bumps.
- Pure design deliverables (`COPY.md`, `SYSTEM.md`, etc.) — those are handled by `design-team`'s specialist roles directly, not this build loop.
- Pre-built artifacts that just need review (use `expert-review-loop` for that).

## The two cohorts

### Builder cohort (writes the code)

| Role | Brief | When to spawn |
|------|-------|---------------|
| **Builder** | [builder.md](roles/builder.md) | Always. 1–3 in parallel on independent files. |

For design-track features, Builders inherit the §3.2 escalation rule from `design-team`: they ship within locked tokens and escalate only on token-violations or novel patterns.

For backend / agent / eval features, Builders follow the conventions in `ma_gatekeeper/HANDOFF.md` and the project's existing test patterns.

### Reviewer cohort (gates the merge)

Spawned **in parallel** after each Builder round. Every reviewer must independently return `GO` before merge.

| Role | Brief | Always-on? |
|------|-------|------------|
| **Goal-alignment Reviewer** | [goal-alignment-reviewer.md](roles/goal-alignment-reviewer.md) | Always. Does the change advance the project's stated goal, or is it scope creep / wrong-shape? |
| **Code-quality Reviewer** | [code-quality-reviewer.md](roles/code-quality-reviewer.md) | Always. Readability, structure, reuse, tests, conventions. |
| **Bug-hunter Reviewer** | [bug-hunter-reviewer.md](roles/bug-hunter-reviewer.md) | Always. Edge cases, null/empty/race, off-by-one, error paths, regressions in adjacent code. |
| **Security Reviewer** | [security-reviewer.md](roles/security-reviewer.md) | When the change touches: auth, OIDC, file upload, PDF parsing, env/secrets, CORS, CSP, iframe, server endpoints, prompt-injection surfaces, eval data flow. |
| **Perf Reviewer** | [perf-reviewer.md](roles/perf-reviewer.md) | When the change touches: marketing route, hero, animation, bundle imports, agent latency-critical paths, database queries, eval batch runners. |

The Supervisor (or invoking agent) picks which optional reviewers apply per feature — but **never skip the three always-on**.

## The cycle

```
round N:
  1. Builders write/modify code per the spec
  2. ALL applicable reviewers spawned in parallel
  3. Each reviewer returns GO or ITERATE — must-fix list
  4. If any reviewer returns ITERATE:
       → consolidate must-fix list
       → return to Builders with consolidated list
       → round N+1
     else (all GO):
       → merge, write PROJECT_LOG.md entry, done
```

### Round 1 — initial build

1. **Write the spec.** Before any code, the invoking agent writes a one-paragraph spec: what the feature does, what file(s) it touches, what success looks like, what the goal-alignment story is. For design-track features, this comes from the `design-team` Supervisor's dispatch plan.
2. **Spawn Builder(s).** 1–3 in parallel only when files are independent. Each receives the spec verbatim plus paths to the relevant existing code.
3. **After Builders return**, spawn the full applicable Reviewer cohort in a **single message with parallel `Agent` calls**.

### Round 2+ — iterate

1. **Consolidate the must-fix list** from all `ITERATE` reviewers. Deduplicate; group by file. If two reviewers contradict each other, the invoking agent decides — written one-line rationale.
2. **Re-brief Builders** with: (a) the original spec, (b) the consolidated must-fix list, (c) which reviewer raised each item, (d) the round number.
3. **Re-spawn the full Reviewer cohort.** Brief each with the round-N+1 changes plus the round-N verdict — reviewers verify convergence rather than re-litigate.
4. **Stop condition** is asymmetric: every reviewer must independently say `GO`. One reviewer still saying `ITERATE` = not converged.

### Convergence safety

- **Max rounds: 4.** If round 4 still has `ITERATE`, escalate to the user — there is a real disagreement that needs a human call, not more loops.
- **No reviewer downgrade.** A reviewer that said `GO` in round N is not re-asked to lower their bar in round N+1; they're re-asked to verify the new diff doesn't regress.
- **Builders cannot become reviewers.** Roles do not switch within a cycle.

## What each reviewer must return

Every reviewer ends with one of:

```
GO — [one-line summary of what they verified]
```

or

```
ITERATE — must fix:
1. [most-impactful issue, with file:line]
2. [next issue]
...
```

No "looks good but consider…" — either it's `GO` and they own that judgment, or it's `ITERATE` with a numbered must-fix.

## Pairing with `design-team`

For design-track features, the call chain is:

```
design-team Supervisor → dispatch plan → component-builder spec
                              ↓
                       feature-build-loop
                              ↓
                  Builder ↔ Reviewer cohort cycle
                              ↓
                       merge + PROJECT_LOG entry
                              ↓
                   design-team Supervisor reconciles  ← HARD GATE
```

The Reviewer cohort here is **additive** to (not a replacement for) the Art Director's section-completion review. Art Director still signs off at section-completion for visual coherence; the cohort gates the *code* for goal-alignment, quality, and bugs on every PR.

**The design-team Supervisor reconciliation is a hard gate, not optional housekeeping.** When this skill is invoked as a sub-step of `design-team`, returning unanimous reviewer `GO` does NOT close the round. The orchestrator must spawn the `design-team` Supervisor for a Step-3 reconciliation pass (see `design-team` SKILL.md Step 3 + "Common shortcuts to refuse"). The Supervisor checks specialist cross-references, internal consistency, kill-switch defusal, and PROJECT_LOG fidelity — none of which the reviewer cohort here is briefed to do. Skipping the Supervisor pass after this skill converges is exactly the "embodying the Supervisor" shortcut documented in `design-team`'s anti-pattern list.

## Logging

Every cycle ends with a single `PROJECT_LOG.md` entry summarizing:

- Feature name + scope.
- How many rounds it took.
- The sharpest must-fix from each round (the audit trail of what got caught — useful for the post-mortem).
- Final verdict from each reviewer.

This is the trail that lets a future reader see *what got reviewed* and *what got caught*, not just the final merged code.
