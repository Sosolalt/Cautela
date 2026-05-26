---
name: project-team
description: Apex orchestrator for the entire M&A Gatekeeper project — picks the next-best work, balances design-track and product-track, and delegates to specialist skills. Spawns product-track specialists (Project Lead, ML/Eval, Agent Engineer, Backend Engineer, Data Engineer, Product Strategist) for cross-cutting decisions. Delegates design work to `design-team` and code work to `feature-build-loop`. Use whenever the user asks "what should I work on next", "advance the project", "is X ready", "plan the next phase", "what's blocking the hackathon submission", or any cross-cutting project question that isn't purely design or purely code.
---

# Project Team

The apex orchestrator. `design-team` covers the landing page; `feature-build-loop` covers any individual code feature; **`project-team` covers everything else and decides where to route each request**.

Use this when the request is bigger than one section / one feature / one specialist domain — when it's about *the project*.

## When to invoke

Invoke when the user asks:

- "What should I work on next?" / "What's blocking submission?" / "Is the project on track?"
- To plan, replan, or rebalance scope across product + design + evals + ops.
- About hackathon strategy, demo scope, jury narrative, partner-track wedges.
- To advance the agent topology, eval methodology, dataset curation, deployment, or any cross-cutting product surface.
- To resolve a decision that crosses multiple specialist domains (e.g., "should we add a new agent role?" touches ML, agent engineering, prompts, and probably the moneymoment narrative).
- To run a Phase-style cycle on the *product* side, parallel to the design-side cycles already in `design/PLAN.md`.

Do NOT invoke for:

- Pure design work — invoke `design-team` directly.
- One specific code feature — invoke `feature-build-loop` directly.
- Tasks already in flight that just need execution — finish them.
- Pure review of an already-built artifact — use `expert-review-loop`.

## The three skills, how they nest

```
project-team        ← apex; picks next work, balances tracks, owns the project narrative
  ├── design-team   ← spawned for design-track work (landing page, brand, copy, motion)
  ├── feature-build-loop  ← spawned for any code artifact (agent code, endpoint, frontend section, eval script)
  └── product-track specialists (roles/) ← spawned for cross-cutting product decisions
```

`design-team` and `feature-build-loop` are unchanged — this skill *uses* them, it does not replace them.

## The product-track specialists (briefs in `roles/`)

These run when the question is cross-cutting and not purely design or purely one code feature. Spawn only the ones whose domain is touched.

| Role | Brief | Owns |
|------|-------|------|
| **Project Lead** | [project-lead.md](roles/project-lead.md) | Persistent. Picks next work, balances tracks, owns `PROJECT_LOG.md` audit trail, makes the call when specialists disagree. Has veto. |
| **ML / Eval Specialist** | [ml-eval-specialist.md](roles/ml-eval-specialist.md) | Wilson LB, paired-bootstrap CI, 5-fold CV, calibration, frozen held-out fold, Reflector regression gates. The conservative-stats wedge is their job. |
| **Agent Engineer** | [agent-engineer.md](roles/agent-engineer.md) | Multi-agent topology (Parser → Classifier → CrossRef → RiskJudge → Router → Reporter + Reflector). Prompts, schemas, ADK patterns, tool use, Phoenix span design. |
| **Backend Engineer** | [backend-engineer.md](roles/backend-engineer.md) | FastAPI server, OIDC, CORS/CSP, Cloud Run deploy, upload caps, env/secrets, observability wiring. |
| **Data Engineer** | [data-engineer.md](roles/data-engineer.md) | EDGAR / CUAD / MAUD corpora, adversarial perturbation, demo-set curation (5 pre-indexed deals), eval-set curation (frozen held-out fold). |
| **Product Strategist** | [product-strategist.md](roles/product-strategist.md) | Hackathon-track wedge (Arize partner track), demo scoping, jury narrative, what differentiates this submission, what's at risk of looking like cosplay. |

## How to run the team

### Step 1 — Project Lead writes the dispatch plan

Always spawn the **Project Lead** first, single-agent foreground call. They read:
- `plan.md` (root) — overall project plan.
- `Arize AI Hackathon Strategy.md` and `Hackathon summary.md` — strategy + judging context.
- `PROJECT_LOG.md` — audit trail.
- `design/PLAN.md` if the request is design-adjacent.
- `ma_gatekeeper/HANDOFF.md` and `ma_gatekeeper/README.md` — product truth.
- The user's request verbatim.

The Project Lead outputs:
1. **Where the project is** — design-track and product-track each in one sentence; current gates / deadlines / blockers.
2. **What the user is really asking** — translate the request into concrete next moves.
3. **Routing decision** — design-team / feature-build-loop / product-track specialists / mix.
4. **Specialists to spawn** (if any) with written spec each.
5. **Parallel vs. sequential** plan.
6. **Risks this round** — what could go wrong, what's the kill-switch.
7. **PROJECT_LOG entry** they will add at end of round.

### Step 2 — Route to the right skill or specialists

- **Pure design work** → invoke `design-team` skill with the relevant brief. Project Lead receives `design-team`'s output and folds it into the project narrative.
- **Pure code feature** → invoke `feature-build-loop` skill with the spec. Project Lead receives the cohort verdict and the merged code summary.
- **Cross-cutting product decision** → spawn product-track specialists in parallel (single message, multiple `Agent` calls) per the dispatch plan. Reconcile their outputs at Project Lead level.
- **Mixed** (a feature that crosses tracks — e.g., the moneymoment requires Backend Engineer + Agent Engineer + design-team + feature-build-loop) → sequence the calls per the dispatch plan, do not run all in parallel if they have dependencies.

### Step 3 — Reconcile

The Project Lead consolidates the outputs into a single project-level decision or deliverable. For hard-to-reverse decisions (new agent role, eval methodology change, deploy target, demo scope change), this gets a `PROJECT_LOG.md` entry with date + rationale + alternatives considered.

### Step 4 — Disagreements

Same rule as `design-team` §3.3: one paragraph from each side, Project Lead decides by the second round. No endless ping-pong.

### Step 5 — Cross-track sanity check

Before declaring a round done, the Project Lead verifies:

- **Honesty-block consistency** — any new product capability that gets shipped must be reflected truthfully in `design/COPY.md` §2.2 #6. If we deployed something that contradicts the data-handling claim, *we either fix the product or fix the claim* — never leave the claim wrong.
- **Conservative-stats wedge intact** — no metric anywhere in product or marketing is shipped without Wilson LB / paired-bootstrap framing.
- **Phoenix-trace surface intact** — every new agent action must produce a Phoenix span the moneymoment can link to. If the new feature dark-ships a call without instrumentation, it doesn't pass.
- **Hackathon deadline reality** — submission is **2026-06-11**. Project Lead asserts how today's work moves that date closer or further.

## When to invoke `feature-build-loop` from inside this skill

Any time the round produces code. The Project Lead does not let specialists ship code without the cohort gate — even backend / agent / eval code. The cohort's `goal-alignment-reviewer` knows about the three pillars, and the cohort's optional `security-reviewer` and `perf-reviewer` are exactly the ones who catch a `react-pdf` import bleeding into marketing or a CORS widening that contradicts the honesty block.

## When to invoke `expert-review-loop`

At project-level milestones — not on every round. Currently scheduled:
- Pre-deploy of the live `/reflect` route.
- Pre-submission (final Devpost video + deployed site, the whole project).

The Project Lead picks the reviewer panel from §8.3 of `design/PLAN.md` and adds product-side reviewers as needed (M&A counsel persona, Arize partner-track judge persona, senior agent engineer).

## Outputs

Every invocation of this skill ends with:
- A clear written decision OR a routed delegation to `design-team` / `feature-build-loop` with results folded back.
- A `PROJECT_LOG.md` entry for any hard-to-reverse decision.
- A named next step for the user, with a deadline anchored to **2026-06-11**.

Never end a round with "the team thought about it" and no artifact. The skill produces decisions and routes; it does not deliberate in a vacuum.
