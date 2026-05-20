---
name: expert-review-loop
description: Run rigorous multi-expert iterative reviews on a plan or codebase until all reviewers converge ("VALIDATED"). Use when the user asks for "thorough review", "double/triple check", "honest critique", or wants to iterate to consensus before shipping. Spawns specialist reviewers in parallel, applies feedback, re-runs them. Not for simple lint/format checks.
---

# Expert Review Loop

A reusable pattern for getting a plan, document, or codebase from "looks done" to "actually correct" by running independent expert reviewers in parallel, applying their feedback, and looping until convergence.

This is the pattern that took the M&A Gatekeeper plan from 4-6/10 → 8.5-9.2/10 (plan, 4 rounds) and the code from 3-6.5/10 → 9/10 (code, 4 rounds). The wins came from:

- **Specialist briefs**: one reviewer per domain dimension (legal, code, ML stats, infra, etc.), not generalists.
- **Brutal honesty in the prompt**: explicitly ask for "must change" + a score + the sharpest one-line objection.
- **Briefing each round with the prior round's verdict**: so reviewers verify convergence rather than re-litigate.
- **Asymmetric stop condition**: every reviewer must independently say VALIDATED. If one is still NOT VALIDATED, you have not converged.

## When to invoke

Use this skill when:
- The user has produced a non-trivial artifact (plan, design doc, scaffolded codebase, migration plan) and wants real-world rigor before committing to it.
- The user says "make sure", "double-check", "have an expert look", "iterate until …", "be brutal", "test everything".
- The work spans multiple expert domains (e.g., legal + ML + ops + UX).

Do NOT use this for:
- Single-perspective lint/format/style checks (just run the linter).
- Tasks the user wants done quickly without ceremony.
- Anything where one reviewer's domain covers the whole artifact.

## How to run a round

### 1. Pick the reviewer panel

3–5 specialists is the sweet spot. Each MUST have non-overlapping expertise. Common panels:

**Plan/document review**:
- Domain expert (M&A lawyer, healthcare clinician, etc.)
- Architecture/technical reviewer
- Data/eval reviewer (if there are metrics)
- Timeline/execution reviewer (if there's a schedule)
- Product/UX reviewer (if there's an interface)

**Codebase review**:
- Senior engineer in the primary language/framework
- Library/integration specialist (verifies API signatures against live docs — they MUST be given WebFetch)
- ML/statistics reviewer (if there's any math)
- Security/DevOps reviewer
- Domain expert (does the thing the code claims to do match reality?)

### 2. Brief each reviewer

Each `Agent` invocation must include:
- The artifact path(s) to read.
- Hard context: deadline, stakes, target audience.
- An instruction to be **HONEST and BRUTAL** (not nice).
- A numbered list of specific questions they must answer.
- A request for **the SHARPEST one-line objection** they have.
- A request for **N concrete fixes ordered by impact**.
- A required ending: `"VALIDATED — X/10"` OR `"NOT VALIDATED — must fix: [single most important thing]"`.

For rounds ≥ 2, ALSO include:
- The prior round's verdict (their own previous feedback).
- A bullet list of what was claimed to be fixed in this round.
- Instruct them to verify each claimed fix with line refs.

Launch all reviewers **in parallel** with `run_in_background: true` so they don't serialize.

### 3. Apply feedback

Hold all fixes until every reviewer returns. Then:
- Consolidate findings into one fix list, deduplicated.
- Order by impact (statistical correctness > security > performance > polish).
- Apply fixes systematically; re-run tests after each batch.
- Never apply piecemeal fixes mid-round — they may conflict with later reviewer findings.

### 4. Loop

Launch round N+1 with the same panel (or fresh agents with the verdict log). Stop when EVERY reviewer returns `VALIDATED`. If one is still `NOT VALIDATED`, fix that issue and re-run only that reviewer.

### 5. Convergence is real

A common failure mode is "reviewer fatigue" — applying fixes that satisfy the letter of feedback but not the spirit. Guard against this:
- If a reviewer flips from NOT-VALIDATED to VALIDATED but the score barely moved (e.g., 6.5 → 7), the fixes were superficial.
- If a reviewer says "VALIDATED — X/10" with X < 7, treat as soft-NOT-VALIDATED and probe their remaining concern.

## Pitfalls that bit me

1. **Don't write code against APIs without verifying signatures.** My initial scaffold had ~15 fabricated Phoenix/ADK API calls because I assumed. Brief at least one reviewer with WebFetch access and instruct them to verify every external API signature.
2. **Don't fix things piecemeal while other reviewers are still working.** A "small" fix to one section can invalidate another reviewer's premise. Hold for the full round.
3. **Don't trust unit tests as sufficient.** 23/23 passing is consistent with broken code if the tests only cover pure math and the integration paths are fabricated.
4. **Specialist briefs ≠ generic "be thorough" briefs.** The Arize reviewer found 10 wrong signatures because the brief explicitly listed Phoenix APIs to verify. A generic "check the code" reviewer would have caught 2.
5. **Statistical honesty over slogans.** Reviewers consistently rewarded operationalized metrics ("Wilson LB at fixed N=24 with disclosed CI width") over slogans ("100% recall"). Bake this into reviewer instructions.

## Output

At each round, write a brief summary to `PROJECT_LOG.md` (see the companion `project-log` skill) showing:
- Per-reviewer score
- VALIDATED / NOT VALIDATED status
- Critical findings to address
- What got fixed this round

## Reviewer prompt template (copy-paste)

Use this skeleton for every reviewer agent. The bracketed slots get filled per-reviewer.

```
You are a [SPECIALTY — e.g. "senior Python engineer with deep ADK
experience"]. [Round X of the review loop OR "first round of"].

File(s) to read:
  - [path1]
  - [path2]
  [list every file the reviewer must touch; do NOT make them go searching]

Context: [project name, deadline, stakes, target audience].
  Specifically, the reviewer panel includes [list other specialties so
  this reviewer knows what NOT to re-litigate].

[FOR ROUND ≥ 2:
**Prior verdict from you (or your predecessor): [NOT VALIDATED / X out of 10]**
**Items you flagged previously:**
  1. [issue 1]
  2. [issue 2]
  ...
**Claimed fixes in this round:**
  - [fix description with file ref]
  - [fix description]
  ...
Your job: verify each claimed fix landed, then re-assess.]

Be HONEST and BRUTAL — not nice. Specifically answer:
  1. [question 1 in your domain]
  2. [question 2]
  ...

Then:
  N. What's the SHARPEST one-line objection that remains?
  N+1. Three (or fewer) concrete fixes ordered by impact.
  N+2. End your response with EXACTLY:
       "VALIDATED — score X/10" OR
       "NOT VALIDATED — must fix: [single most important thing]"

Report under [WORD BUDGET — usually 500-1000]. Quote file:line refs.
Do not pad with praise. If something is fine, say "fine" and move on.
```

## Reviewer panel selection (the WebFetch rule)

At least one reviewer per panel MUST be given WebFetch access AND explicit instructions to verify every external API signature against live docs. In the M&A Gatekeeper project, this was the Arize founding-engineer reviewer; their WebFetch table of (claimed signature → real signature) is what made round-B's rewrite possible.

Without this, you will write code against APIs that don't exist — exactly the failure mode that took the M&A Gatekeeper code from "23/23 tests passing" to round-A 4/10. Tests cannot catch this; only doc-verified review can.

When briefing the library/integration specialist, list each external API call by name in the prompt and require a verdict per call (real / wrong signature / wrong resource path / deprecated). This makes the reviewer's output actionable as a diff list.

## Example invocation skeleton

```
Round A — code review

Launch in parallel (single message, 5 Agent tool calls):

1. Legal/M&A + hackathon judge → reads prompts.py, schemas.py, server.py, README
2. Senior Python/ADK engineer → reads all agent/*.py + Dockerfile + requirements.txt
3. Arize founding engineer (WebFetch enabled) → reads agent/*, scripts/calibrate.py
4. ML statistician → reads scripts/calibrate.py + agent/reflector.py + tests/
5. Senior SRE → reads server.py + Dockerfile + .env.example + HANDOFF.md

Each prompt includes:
- File paths
- "Be HONEST and BRUTAL"
- 8-12 specific questions
- Required ending: VALIDATED X/10 or NOT VALIDATED must fix: thing

Wait for ALL 5 before applying any fixes.
```

## Reviewer fatigue — how to detect it

After 3+ rounds, reviewers can drift toward "VALIDATED" because they're tired, not because the artifact is good. Symptoms:

- Score barely moves (e.g., 6.5 → 7.0) but reviewer flips to VALIDATED.
- "Remaining concerns" become cosmetic (naming, comments) when the artifact still has real correctness gaps.
- New issues mentioned in passing are not added to the "must fix" line.

Defense: when a reviewer flips to VALIDATED with a score < 8, treat it as soft-NOT-VALIDATED. Re-prompt them with the specific concerns they mentioned and ask whether those are blockers. If yes, fix and re-verify. If genuinely not, accept.

## Cost and time budget

A full review loop is not free. M&A Gatekeeper used:

| Phase | Agents | Rounds | Total agent-invocations |
|---|---|---|---|
| Plan reviews | 4 | 4 | ~13 (some rounds skipped some reviewers) |
| Code reviews | 5 | 4 | 19 (round A 5, B 5, C 4, D 1) |
| Research | 4 | 1 | 4 |
| **Total** | | | **~36 specialist agent runs** |

Each agent typically runs 30-120 seconds. In parallel, a full round of 5 reviewers takes ~3 minutes of wall time. Budget accordingly when telling the user "this will take a while."

If cost is a concern, cut from the bottom up: skip rounds where only one reviewer has remaining issues (just re-run that reviewer), or drop reviewers whose domain is covered well by another.

## Reviewer disagreements

It's rare but possible: two reviewers give contradictory advice (e.g., one wants more agents, one wants fewer). Resolve by:

1. Side with the reviewer whose domain owns the disputed area (ADK structure = Python reviewer wins over generalist; legal correctness = legal reviewer wins).
2. If both are in-domain, give them each other's feedback and ask each to defend their position. Usually one concedes.
3. If neither concedes, escalate to the user with both positions stated honestly. Don't pick silently.

## Stop conditions

- All reviewers return VALIDATED. Done.
- 4+ rounds completed without convergence on the same reviewer. Stop and escalate to the user — there may be an unresolvable disagreement (or the artifact genuinely has a blocker the reviewers and you cannot fix in scope).
- Scope creep — if reviewers start flagging things outside the original work's purpose, stop and reset scope with the user.
