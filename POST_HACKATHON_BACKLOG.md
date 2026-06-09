# Post-Hackathon Backlog

Items explicitly deferred by the D-3 fix plan (2026-06-08) and by the
critic-review pass that produced it. These are NOT for the
2026-06-11 submission window. Each entry names: the item, why it was
deferred, the trigger that should bring it back, and rough cost.

Source critics referenced inline: M&A partner, Arize Phoenix engineer,
Vertex/Gemini PM, ML/eval skeptic, demo storyteller, Devpost generalist
judge (June 2026 review round).

---

## 1. Cross-clause structural reasoning agent

**Deferred from**: M&A partner critic's "demo-killing weakness" finding
— the agent flags single clauses but cannot produce structure-conditional
verdicts (e.g. same anti-assignment clause: HIGH risk in a forward
merger, LOW risk in a reverse-triangular merger under Delaware law,
citing Cincom vs. Meso Scale).

**Why deferred**: Fix 6 in `FIX_PLAN` only attempts a single demo
beat that *exhibits* structural reasoning if the existing
Cross-Reference agent already supports it. The deeper architectural
work — making structure-conditional reasoning a first-class capability
across the Risk Judge — is a multi-week build.

**Trigger to restart**: any post-hackathon engagement with a real M&A
lawyer / firm where "show me one where structure changes the answer"
is asked. This is the single highest-credibility unlock for the
product per the partner critic.

**Cost**: 2–4 weeks. Requires (a) extending the schema to carry deal
structure (RTM / forward / parent-level / asset), (b) Risk Judge
prompt redesign with structure-conditional precedent citations,
(c) a held-out test set with structure-paired clauses.

---

## 2. Gemini 3 Portfolio Analyst agent (1M-context cross-deal pattern detection)

**Deferred from**: Vertex/Gemini PM critic's "one change that wins the
Google Cloud bucket" — single Gemini 3 Pro call across all 30
contracts (~3000 pages combined) for cross-deal clustering
("MAE carve-outs cluster into 4 templates; deal #17 is the outlier"),
exposed as a fifth ADK agent.

**Why deferred**: this is Fix 7 in `FIX_PLAN`. ~8h net-new ADK
agent + prompt + UI work. Deferred to keep Day 2 unblocked for the
demo rewrite.

**Trigger to restart**: post-submission, before any Marketplace
listing attempt. This is the feature that converts "vertical contract
reviewer" into "data-room intelligence agent" — i.e. the framing a
Vertex PM can picture customers buying.

**Cost**: ~8h plus prompt iteration. Cheap relative to value.

---

## 3. Arize MCP introspection actually drives the regression-set growth

**Status (2026-06-08)**: **Partially resolved by §11 Build #3** —
`agent/reflector_loop.py` (Phase 9, pending Reviewer cohort GO).
Build #3's LoopAgent body issues an explicit Phoenix MCP `list_traces`
call per iteration (`_call_mcp_list_traces`, hard-gate-tested in
`tests/test_reflector_loop.py::test_loop_body_calls_mcp_list_traces_per_iteration`),
so introspection now feeds candidate-prompt generation directly. The
**legacy in-cycle path** (`run_reflection_cycle`'s Hook 4 also driving
`_append_to_dataset` from the MCP parser instead of discarding the
introspection summary) appears to have landed concurrently in
`reflector.py` (uncommitted working tree state at session start;
provenance: likely earlier Phase 8 work, not Phase 9). Final
resolution gated on the Reviewer cohort GO for Build #3 + an audit
of the `reflector.py` Hook-4 changes against the locked-surface
invariant.

---

(legacy entry follows)


**Deferred from**: Arize juror critic's PARTIAL rating on Hook 4 — the
MCP-mounted LlmAgent's `introspection_summary` is computed in
`reflector.py` and discarded; `_failing_traces` re-derives failures
via SDK independently.

**Why deferred**: Fix 5 in `FIX_PLAN` ships this IF pre-flight
verification confirms the agent claim AND time allows on Day 2.
The cut-criteria explicitly identifies Fix 5 as the third item to
drop if Day 2 slips.

**Trigger to restart**: if Fix 5 is cut from the hackathon submission,
this is the first post-hackathon engineering task — it's the
differentiated Phoenix hook and the only one a generic OpenInference
submission cannot replicate.

**Cost**: 2–4h with passing tests.

---

## 4. Larger annotated corpus to make the statistics non-decorative

**Deferred from**: ML/eval skeptic critic. At n=30 contracts and
~6–10 Block findings per fold, the one-sided 95% Wilson LB has noise
floor ±0.10–0.15 — the published rigor over-communicates. Fix 10
addresses this by relabeling and dropping per-fold Wilson LBs from
the headline, but the underlying remedy is more data.

**Why deferred**: 30 contracts is already 15–25h of LLM-assisted
annotation work (the D5–D9 user-action). Going to 100+ contracts
needed to make Wilson LB ≥ 0.95 arithmetically reachable is a
separate multi-week annotation pass.

**Trigger to restart**: if the post-hackathon roadmap aims at any
publication (workshop paper, blog with defensible numbers) or any
real customer pilot with a quantitative SLA.

**Cost**: ~50–80h of annotation + bootstrap pipeline tuning.
ACORD + LEDGAR (already identified in deal-bank Bucket E) provide
the silver-label pre-training; ABA Deal Points 2024/25 provide priors.

---

## 5. ADK topology beyond "minimum multi-agent shape"

**Status (2026-06-08)**: **Partially resolved by §11 Build #3** —
`agent/reflector_loop.py` (Phase 9, pending Reviewer cohort GO). The
Reflector now exists as a first-class ADK construct (via the
`_FallbackLoopRunner` shim which preserves the LoopAgent body
contract; the real `google.adk.agents.LoopAgent` is imported softly
so the test suite can run without a hard `google.adk` dependency).
Loop body queries Phoenix MCP for past traces, proposes a candidate
prompt, runs a Phoenix Experiment, and applies the existing
`should_promote` gate. The "agent that improves itself" demo now
lands **inside** the ADK runtime rather than as cron output. Final
resolution gated on the Reviewer cohort GO + verification on the
live ADK Runner path (currently exercised only against the fallback
shim in tests).

---

(legacy entry follows)


**Deferred from**: Vertex/Gemini PM critic's "solid B+, minimum
qualifying shape" rating. Current topology is
`Sequential[Parser → Parallel[7] → CrossRef → RiskJudge]`. No
agent-to-agent negotiation, no dynamic dispatch, no `LoopAgent`
self-correction inside the inference path. The Reflector runs *outside*
ADK as a Cloud Scheduler cron.

**Why deferred**: the fix plan explicitly does not attempt this
("Does not address the Vertex PM's 'ADK is minimum shape' structural
criticism. That's a multi-week refactor; out of scope for D-3.").

**Trigger to restart**: post-hackathon. Specifically: the Reflector
self-improvement loop is the team's differentiator and currently it
lives outside the agent framework being judged. Wrapping it as a
`LoopAgent` inside ADK would make the "agent that improves itself"
demo land inside the ADK runtime rather than as cron output.

**Cost**: 1–2 weeks plus careful test coverage on the loop semantics.

---

## 6. Cloud Run / Vertex idiomaticity beyond table-stakes

**Deferred from**: Vertex/Gemini PM critic — current Dockerfile is
slim + non-root + `$PORT`-aware (table-stakes). Missing: Cloud Run
Jobs for the nightly Reflector (currently HTTP-triggered),
Workload Identity, Secret Manager binding, Cloud Trace native export.
Phoenix-on-Cloud-Run was flagged as fighting the Cloud Trace + Vertex
AI Eval native story.

**Why deferred**: no critic flagged this as a winning-bucket move; it's
a hygiene item that becomes relevant for production / Marketplace
deployment, not hackathon judging.

**Trigger to restart**: any path toward Marketplace listing OR any
real customer pilot. Specifically: re-evaluate Phoenix-self-host vs.
Phoenix-managed-on-Vertex once the Vertex-native eval surface
matures.

**Cost**: 1–2 weeks for full Cloud Run Jobs + Workload Identity +
Secret Manager migration.

---

## 7. Iterative critic-review loop (vs. single-round fanout)

**Deferred from**: my own honesty pass on the June 2026 critic review.
I ran a single-round parallel fanout (6 personas, no inter-critic
visibility) rather than using the `expert-review-loop` skill (multi-
round, critics see each other's findings, iterate to convergence).

**Why deferred**: explicit in `FIX_PLAN`'s "what this plan does not
do" — "Does not re-run the critic review after fixes. Diminishing
returns at hackathon scale."

**Trigger to restart**: post-submission retro. Worth one round of
`expert-review-loop` after the demo lands to capture what jurors
*actually* reacted to vs. what critics predicted they would.

**Cost**: 2–4h of agent runtime + 1h synthesis.

---

## 8. Critic claims not independently verified during the review

**Deferred from**: my honesty pass admitted I never verified the
critics' code-line citations (e.g. Arize's `reflector.py:813`
introspection-summary-discarded claim, ML/eval skeptic's
`calibrate.py:295` pseudoreplication claim) before writing them into
the fix plan. Pre-flight verification (V1–V5 in the fix plan) catches
these for the hackathon, but only narrowly — only the line numbers
that fix items 5 and 10 depend on.

**Why deferred**: the 30+ EDGAR / FTC / court URLs in
`internal30_deal_bank.md` were also returned by agents and not
HEAD-checked beyond the 5 allow-listed deals. Same for the partner-
critic's legal-accuracy corrections (Akorn carve-out wording,
Stabroek = preemption right, Tiffany never tested on merits) — I
accepted those without independently verifying against the actual
opinions.

**Trigger to restart**: before any external publication using the
deal bank or the recall numbers. The hackathon's tolerance for
loose-cited claims is higher than any subsequent professional or
academic surface's.

**Cost**: ~4h to systematically HEAD-check the deal-bank URLs and
spot-check the legal claims against the linked opinions.

---

## 9. Demo-storytelling: depth beyond the BMS/Celgene cold open

**Deferred from**: demo storyteller critic's framing — the fix plan
adopts the BMS/Celgene "$6.4B, 36 days, one missing clause" cold open
(Fix 2) but does NOT propagate the same emotional weight through the
rest of the demo. Block-tier chips later in the demo are still
referenced as a category, not as "another $6.4B-style clause."

**Why deferred**: time-budget — the demo rewrite is already a
~2h scope on Day 2 and over-narrating risks overrunning the 3:00
cap.

**Trigger to restart**: longer-form video (5-min, 10-min) for a
sales / Marketplace surface where the runtime cap relaxes. Then each
Block-tier chip can carry its own micro-story.

**Cost**: ~4h of script + voiceover for a 5-min version.

---

## 10. Persona coverage gap in critic review

**Deferred from**: my honesty pass admitted the 6 personas didn't
cover financial-modeling judge, security/compliance judge, or actual
practicing M&A counsel (the "M&A partner" was an LLM persona).

**Why deferred**: hackathon scoring rubric is generalist + Arize
+ Vertex; the missing personas were lower-priority for the
submission decision.

**Trigger to restart**: any real pilot conversation. Specifically,
before the first customer-facing demo, a 30-min review with a real
M&A associate (paid consult OK) is worth more than another agent
round.

**Cost**: $300–$500 for a 1-hour paid consult OR a Skadden / Davis Polk
contact.

---

## Out-of-scope for this backlog (intentionally not tracked here)

- Anything in `ma_gatekeeper/HANDOFF.md` — that file owns the hackathon-
  window deferrals; this file owns post-submission roadmap.
- Design-track items — those live in `design/SOURCE_OF_TRUTH.md` and
  the `design-team` skill output.
- Bug fixes against shipped code — those go in tests + commit history,
  not backlog.

---

# Post-POC Enterprise Roadmap (added 2026-06-08)

Synthesized from a 4-agent brainstorm (M&A partner / enterprise GC+CIO /
agent engineer / product strategist) plus a 2-juror critique pass
(hostile Devpost+ex-Kira-CTO judge, Arize-engineer+M&A-practitioner
combined). Sections below correspond to items 2, 3, and 6 of that
synthesis. Items 1, 4, 5, 7–10 from the synthesis live elsewhere
(framing, demo polish, GTM) and are not roadmap entries.

## 11. The three things to build in the next 90 days

Ranked by *enterprise-credibility-per-engineering-week* after juror
cuts. Each entry is a roadmap commitment for the post-hackathon
window, not a hackathon-submission item.

### Build #1 — Issues List + Disclosure-Schedule Cross-Walk generator

The artifact an associate hands a partner Friday night. If the agent
does not output something that drops into a Word issues-list template
Monday morning, no partner takes a second call. The Cross-Walk is the
credibility move on top of it: *"§3.12(b) of the SPA references
Schedule 3.12(b), which references Exhibit C-4, which is missing from
the data room."*

- **Phoenix artifact**: a Phoenix Dataset of 25 partner-annotated
  deals → Phoenix Experiment scoring (issue extracted, severity tier,
  schedule cross-ref resolved Y/N) per prompt version.
- **Cost**: ~3–4 weeks for v1 against the existing 5-deal allow-list
  + 20 additional EDGAR-derived deals.
- **Demo-killer-fix**: this is the demo-killer per the M&A-juror —
  shipping it is the *minimum* for any post-hackathon partner
  conversation. Topology Lens (item 1 above) is the *follow-up*
  meeting, not the first.

### Build #2 — Jurisdiction-Pair Conflict DSL + faithfulness eval

The honest version of the founder's "current law of both
jurisdictions" intuition. **Not** a pgvector dump of DGCL / NY BCL /
EU MR (12-month research project, $400K/yr Westlaw license,
permanent legal-engineering team). Instead: a curated
**200–400-entry Jurisdiction-Pair Conflict DSL**, maintained by one
part-time M&A counsel, stored as **versioned Phoenix Prompts**, each
with an attached `phoenix.evals` custom evaluator scoring
claim ↔ retrieved DSL entry ↔ cited authority.

Example DSL entry: *Delaware-target / NY-governing-law no-shop with
Revlon carve-out drafted under DGCL but fiduciary-out under NY
contract law → flag known conflict pattern, cite Cincom +
Meso Scale + the relevant Chancery line.*

- **Phoenix artifact**: trace per finding cites DSL entry ID +
  version hash; faithfulness score inline; drift detected as
  Phoenix Experiment delta against frozen golden set.
- **Cost**: 8 weeks for the 300-entry DSL + custom evaluator. The
  DSL is the cost center, not the engineering.
- **Why this version, not the RAG version**: jury was blunt that
  scraping case-law corpora and calling it "jurisdiction-aware
  reasoning" gets the demo eaten alive on the first edge case
  (§251(h), EU MR Art. 22 referral, CFIUS mandatory filing). The
  DSL is finite, enumerable, defensible, and ships in 8 weeks.

### Build #3 — Reflector-as-ADK-LoopAgent calling Phoenix MCP recursively

Today the Reflector is a Cloud Scheduler cron, *outside* the ADK
runtime being judged. Wrapping it as `LoopAgent` is theater *unless*
the loop body **queries Phoenix MCP for its own past traces** to pick
examples, runs a Phoenix Experiment, then auto-PRs the τ change.
That recursion — Phoenix observing the agent that uses Phoenix to
improve the agent Phoenix is observing — is the actual differentiator
per the Arize-engineer juror. Without the MCP introspection in the
loop body, it's a cosmetic re-wrap.

- **Phoenix artifact**: parent span = LoopAgent run; child spans =
  the Phoenix Experiments comparing today's τ_h, τ_f against
  yesterday's on the frozen fold; green AUTO-PROMOTED badge linked
  to the auto-opened PR.
- **Supersedes**: item 3 above ("Arize MCP introspection actually
  drives the regression-set growth") and item 5 above ("ADK topology
  beyond minimum multi-agent shape"). Both are subsumed by this
  build.
- **Cost**: ~2 weeks. The functionality exists scattered across
  `reflector.py` + the cron; the work is the wrapping + the MCP
  call sites + the parent-span tracing.

### Explicitly cut from the 90-day window

Each of these was named by one or more brainstormers and explicitly
killed by the juror pass:

| Item | Why cut |
|---|---|
| 1M-context portfolio analyst | Costly per run; no demo legibility; competes with the wedge |
| Post-Close Watchtower | Different product, different buyer (GC not partner), dilutes pitch |
| Topology Lens as P0 | Follow-up meeting, not first; partners tolerate absence in v1 |
| Full Westlaw / Lexis-grounded jurisdiction RAG | Replaced by the curated DSL above |
| Argilla integration | Phoenix has native annotations + datasets — use those |
| Ten specialty sub-agents (tax / ERISA / antitrust / IP / env) | Year-3 product, dilutes year-1 focus |
| EDGAR Precedent Library as a feature | Table-stakes-claimable by every vendor; not the wedge |

## 12. The ONE demo moment that beats 90% of the field

A single ≤90-second sequence, end-to-end, with all real artifacts.
No other hackathon submission has a frozen-fold non-regression
chart. That chart is the pitch.

1. Phoenix trace pane shows yesterday's finding (lane = Escalate).
   Partner has already clicked "wrong — should be Block" in the HITL
   pane.
2. Operator presses **"Run Reflector now."** The ADK `LoopAgent`
   spawns visibly inside the ADK runtime panel. Three sub-traces
   appear: candidate-prompt generation, paired-bootstrap CI on the
   regression set, frozen-fold non-regression check.
3. Output: side-by-side prompt diff (old vs candidate), CI bar chart
   (Δrecall +4.2% on Block lane, 95% CI excludes 0, frozen-fold Δ
   within ±0.5%), green **AUTO-PROMOTED** badge with a git commit
   hash.
4. Click the commit hash → opens the auto-PR with the τ_h / τ_f
   update.
5. Re-run yesterday's finding. Now Block. Click the finding → the
   existing clickable trace shows the *new* reasoning chain citing
   the *new* prompt version.

This is the artifact that the Arize-track and the generalist Devpost
panels both score on. It is also what makes Build #3 (above) load-
bearing rather than cosmetic: the LoopAgent + Phoenix MCP recursion
*is* the demo.

## 13. Enterprise pilot bill of materials — what makes a partner write $50K

The realistic first pilot is **not** a Fortune 500 procurement cycle
(9–12 months, $2–3M platform spend, SOC 2 Type II prerequisite).
It is one M&A partner at a mid-market boutique writing $50K to run
the agent on **one live deal next quarter**. Five items, no more:

1. **Single-tenant deployment in the customer's GCP project with
   CMEK** via Vertex AI Private Endpoint + VPC Service Controls
   perimeter. Skip SOC 2 for the pilot; have the SOC-2 gap analysis
   ready.
2. **`.docx` round-trip with track-changes redlines and margin
   comments** that opens cleanly in Word + iManage. Not PDF, not
   JSON, not a dashboard. The four brainstormers all missed this.
   `python-docx` post-processor on the Issues List; each margin
   comment deep-links to the Phoenix trace. ~1 week.
3. **Customer-playbook DSL** — the partner's own MAC carve-outs,
   their own anti-assignment preferences, their own escalation
   thresholds — loaded as YAML or via a simple form, stored as
   versioned Phoenix Prompts with diff view. This is what makes
   "consistent recall" defensible to a partner who has been burned
   by AI tools that "opined in a vacuum."
4. **Clickable trace per finding** (existing wedge) + **immutable
   model/prompt versioning** + **signed audit-log export bundle**.
   The artifact their malpractice insurer and the client will demand
   under FRCP 26.
5. **Single HITL reviewer queue** with Block / Escalate / Auto-Clear
   triage. Not ten specialist sub-agents. Not role-tiered queues
   with partner sign-off (that's Year-2). Just one queue with three
   lanes and a "wrong" button that writes to the Phoenix Dataset
   that feeds Build #3.

### What is explicitly NOT in the $50K pilot BOM

- VDR ingest (Datasite / Intralinks / iManage / SharePoint) — Year-2
- Westlaw / Lexis / Bloomberg-Law-grounded jurisdiction layer — see
  Build #2 for the cheaper, defensible version
- SOC 2 Type II — gating *project*, not a pilot feature, runs in
  parallel from Day 1 of post-hackathon
- Chinese-wall / matter-scoped RBAC — Phoenix Sessions handles the
  per-matter trace isolation at pilot scale; full RBAC is Year-2
- OTLP dual-export to Datadog / Splunk — Year-2
- Word + Outlook plug-ins — the `.docx` round-trip (item 2 above) is
  the minimum-viable embed; plug-ins are Year-2 adoption work
- Specialty-counsel sub-agents (tax / antitrust / ERISA / IP / env)
  — Year-3 revenue lever, not pilot

### The malpractice-and-liability gate (nobody flagged this)

None of the four brainstormers and none of the prior plan docs cover
the question every partner asks in minute 4 of the procurement call:
*"When your agent misses a CoC clause and our client sues us, who
pays?"* Before the first pilot conversation, the founder needs:

- A signed MSA template with a liability cap and an explicit
  "decision-support, not decision-making" disclaimer
- An **AI-specific E&O policy** naming the customer as additional
  insured (Munich Re / Beazley / Coalition write these; $5–25M tower,
  $100–500K/yr premium for the early-stage tier)
- A UI-enforced human sign-off step before any Auto-Clear finding
  becomes work product — currently the Auto-Clear path likely
  doesn't enforce this

Without this, the pilot dies in legal review regardless of how good
the Phoenix traces look.
