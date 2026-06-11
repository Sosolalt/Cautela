# Review prompt — "what's left to ship" plan

> Paste the fenced block below as the first message of a fresh Claude Code
> conversation **in this repo** (`ma_gatekeeper/`). It has agents audit the
> real project state and produce a step-by-step plan to submission, splitting
> every step into **[AGENT]** (AI-doable) vs **[MANUAL]** (human-only).
>
> Prepend the word `ultracode` (already in the block) to fan the verification
> out across a small agent panel; remove it for a single-agent review.

---

```text
ultracode

ROLE: You are a delivery lead auditing the Cautela / M&A Gatekeeper hackathon
submission (a Google Cloud Agent-Builder/ADK + Vertex Gemini 3.1 + Arize Phoenix
project). Produce an evidence-based status report and a step-by-step plan of
what's left to ship, with every step tagged [AGENT] or [MANUAL].

DEADLINE: Devpost submission is due June 11, 2pm PT (submit with a buffer —
ideally tonight). Optimize the plan for that.

=== STEP 1: READ THE AUTHORITATIVE SOURCES ===
- ma_gatekeeper/manual_steps.md — the §1–§11 operator runbook (the spine of
  "what must happen"). Treat its section numbers as the canonical work breakdown.
- The auto-memory: /Users/lucas/.claude/projects/-Users-lucas-Documents-Projects-devpost-arize-project/memory/MEMORY.md
  and the project_*.md files it links — they record what's DONE, what's BLOCKED,
  and hard-won gotchas (Vertex global endpoint, CUAD eval verdict, deploy state,
  calibration-is-mock, Internal-30 gold built, etc.).
- ma_gatekeeper/docs/ — demo_script.md, devpost.md, internal30_deal_bank.md,
  internal30_annotation_cohort.md.

=== STEP 2: VERIFY STATE — DO NOT TRUST CLAIMS, CHECK ===
For each runbook section, establish the REAL status with evidence. In particular:
- Eval JSONs: do maud_mcq_eval.json / cuad_baseline.json exist, and what does
  the README results table (between the BEGIN/END_RESULTS_TABLE markers) show?
- Calibration: is thresholds.json a real calibration or the `_placeholder`?
  Is data/internal30/judged_findings.csv from the LIVE judge or the MOCK
  (`judge_internal30.py` mock = hash-derived 0/0.5/1 scores)?
- Citation eval: evals/citation_gold_eval.json — is `run_mode` "mock" or "live"?
- Internal-30 gold: do data/internal30/reconciled_gold.jsonl etc. exist? how many rows?
- Cloud Run: run `gcloud run services describe ma-gatekeeper --region=us-central1`
  — is it serving? what is REFLECT_OIDC_AUDIENCE (PLACEHOLDER = /reflect 503s)?
  VALIDATE_ALLOW_LIST_ON_BOOT? Is Phoenix deployed? Smoke-test /healthz + /docs.
- Reflector: has §7 (Cloud Scheduler cron) / §9 (seed_reflector --commit) run?
  Has a /reflect cycle ever landed a prompt version + experiment runs in Phoenix?
- Tests: run the offline suite; note pass count + any pre-existing failure.
A claim in a doc/memory that the working tree or cloud contradicts MUST be
flagged, not repeated.

=== STEP 3: OUTPUT A — STATUS TABLE ===
A table over runbook §1–§11 (plus the eval sub-tracks): each row =
section | DONE / PARTIAL / BLOCKED / TODO | evidence (file, command output, or
README row) | blocker if any.

=== STEP 4: OUTPUT B — STEP-BY-STEP PLAN TO SUBMISSION ===
An ordered, dependency-aware checklist from now to "submitted on Devpost." For
EACH step give: a one-line action, the tag [AGENT] / [MANUAL] / [HYBRID], why,
rough effort/quota cost, and what it unblocks. Order by the critical path.

Tagging rule (apply strictly):
- [MANUAL] = needs a human: GCP Console / billing / quota-bump requests;
  executing or authorizing production `gcloud` deploys; spending Vertex
  quota/credit; reading or setting secrets; the human legal validation /
  Argilla annotation; recording + editing the demo video and YouTube upload;
  filling and submitting the Devpost form; any irreversible or outward-facing
  action; anything requiring human judgment or an account login.
- [AGENT] = an AI in this repo with tools can fully do it: code edits, writing
  and running offline tests, README/doc edits, drafting Devpost text, building
  scripts/workflows, OFFLINE calibration math, drafting (not executing) gcloud
  commands, read-only state verification.
- [HYBRID] = AI does the work but a human must authorize/execute the
  irreversible or quota-spending part (e.g. AI writes the live-judging script
  and the exact command; operator runs it because it burns Vertex credit). Say
  who does which half.

For every [AGENT] step, name the concrete deliverable (file/command). For every
[MANUAL] step, give the exact console path or command the operator runs.

=== INTEGRITY CONSTRAINTS (non-negotiable — this project's whole thesis) ===
- NEVER plan to report mock/placeholder numbers as real. The calibration
  thresholds and the citation eval are currently MOCK; a real number needs a
  live Vertex judging run. The README rows must stay "Not yet available" until
  then. Plan the live run as a step; do not plan to fake it.
- The CUAD headline is the single-pass macro_f1 (~0.38, clean test split), NOT
  the train+test-pooled 0.43 (contaminated) and NOT the multipass number
  (measured, does not beat single-pass — keep it OFF, report it only as a
  disclosed negative result if at all).
- Flag any step where a shortcut would cross into dishonest territory.

=== STEP 5: BOTTOM LINE ===
Close with: (1) the single most important next action, (2) the minimum set of
[MANUAL] steps only the operator can do (so they know exactly where they're the
bottleneck), and (3) an honest go/no-go read on hitting the June 11 2pm deadline.

Before writing, show the few verification commands you ran and their key
outputs, so the plan is grounded in real state, not the docs' claims.
```
