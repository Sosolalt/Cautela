# Devpost submission drafts — M&A Due Diligence Gatekeeper

Drafts for the seven Devpost text sections, the required Demo Scope
paragraph, the AI-generated-content disclosure, and the Reflector
pre-seeding disclosure. Word counts target 100–300 per section.

Copy these into the Devpost form on D20 (June 8). The Devpost browse-
line + AI-disclosure + YouTube public-or-unlisted-link-accessible items
are operator-side per HANDOFF.md D20.

Track checkbox: **Arize partner track** (required for the bucket prize).

Built-with tags: `Google Cloud`, `Gemini 3`, `Agent Development Kit`,
`Arize`, `Phoenix`, `Model Context Protocol`, `Cloud Run`, `Vertex AI`,
`FastAPI`, `Next.js`, `EdgarTools`.

---

## Project tagline (one sentence, 200 chars max)

> An AI agent that reads merger contracts, separates auto-clear clauses
> from deal-breakers, and ships every decision with a click-into-it
> audit trail in Arize Phoenix.

---

## Inspiration

M&A due diligence today: 30–90 days, $50K–$200K mid-market, $200–$500/h
in associate review. Most of that spend goes into clauses where the
answer is "boilerplate, fine" — and the genuine landmines are still
sometimes missed because reviewer attention is rationed. Existing
vertical tools (Harvey, Kira) tag the headline clause types, but none
publish per-clause recall at a stated abstention budget, and none ship
the experiment-gated self-improvement loop the modern observability
stack now makes cheap.

We wanted to find out whether the right architecture — a vertical
contract agent built on Gemini 3 + Google ADK, with Arize Phoenix
wired into every decision and a nightly Reflector loop that earns its
own prompt promotions — could turn that asymmetry on its head: spend
the agent's time on a known auto-clear set, abstain noisily on the
ambiguous ones, and surface deal-breakers with a citation a lawyer
can click into. Hackathons aren't products, but they're a way to find
out which prototype shape is worth taking further.

---

## What it does

The agent reads a merger agreement (8-K Exhibit 2.1 in our hosted
demo; arbitrary PDF in local mode), parses each clause with bounding-
box coordinates, runs four headline classifiers in parallel
(change-of-control, anti-assignment, MAC carve-out narrowing,
accelerated vesting), resolves cross-references between Definitions
and operative clauses, and emits Risk Findings with verbatim cited
spans.

A deterministic Python Router then routes each finding through three
lanes — **Auto-Clear**, **Escalate to Lawyer**, **Block** — using
independent gating: a hallucinated explanation cannot auto-clear no
matter how confident the faithfulness score is. Every routing
decision lands in Arize Phoenix as three span annotations
(`hallucination`, `clause_faithfulness`, `risk_judge_gate`) the user
can click into directly from the findings pane.

Overnight, a separate Reflector loop introspects its own escalation
traces via the Phoenix MCP server, drafts a candidate prompt, and
auto-promotes it ONLY if a paired-bootstrap CI lower bound clears zero
on the regression dataset AND the candidate doesn't regress on a
frozen held-out fold. The loop logic is the same on demo day as in
production — the demo just gets a 48-hour head start.

---

## How we built it

Four-stage agent topology on Google ADK 2.0:
**Parser → Classifier (ParallelAgent fan-out) → Cross-Reference →
Risk Judge**. Gemini 3 Pro on the heavy stages, Gemini 3 Flash on the
parallel classifier fan-out. Artifacts under 8 MB are inlined via
`Part.from_bytes`; larger ones go through Gemini's Files API and a
polled `Part.from_uri`, so the inline path stays snappy on the 5-deal
HTML demo and oversized PDFs stop silently truncating past page ~20.

Arize Phoenix is the observability spine — self-hosted on Cloud Run,
proxied through our own subdomain so the iframe embed works without
sandbox warnings. Seven Phoenix hooks: OpenInference tracing on every
ADK call, inline `phoenix.evals.create_classifier` for hallucination
+ faithfulness, programmatic span annotations via the Phoenix client,
MCP introspection (`list-traces`, `get-trace`, …), auto-growing
regression datasets via MCP `add-dataset-examples`, prompt
versioning + experiment-gated promotion, and a scheduled batch
`run_evals` cron in place of the SaaS-only AX Online Eval Tasks.

The numbers stack: 5-fold CV calibration with one-sided 95% Wilson
LBs, non-parametric cluster bootstrap respecting per-contract
correlation, reliability diagrams over the full pool, and an
ε = max(SE, 0.03) noise floor on the frozen-fold non-regression
check. With ~6–10 Block findings per fold the 95% CI for a
proportion near 1.0 spans roughly ±0.10–0.15 — the Wilson lower
bound clearing 0.95 is arithmetically tight, not a guarantee, and
we publish the achieved number unmodified.

Hosting: FastAPI on Cloud Run (autoscaling to zero off-demo), Next.js
14 / Tailwind frontend with `react-pdf` + Phoenix iframe deep-link,
Cloud Scheduler driving the Reflector nightly.

---

## Challenges we ran into

Most of the genuine bugs were API-shape fabrications — across the
ADK, Phoenix client, Phoenix evals, and EdgarTools surfaces, our
first-pass code had ~15 calls with wrong signatures, hallucinated by
extrapolating from prior model knowledge. We caught them in code
review by spawning specialist reviewers and forcing each to verify
against live docs (one with WebFetch open). The most expensive single
fix: `provider="vertexai"` is `provider="vertex"`; `clf(...)` is
`clf.evaluate({...})[0]`; `client.annotations.*` is deprecated in
favor of `client.spans.add_span_annotation` since `arize-phoenix-
client` 1.17.

Statistical honesty was the second class of mistake. Our first
promotion rule used `δ > 0.05` on N=30 — pure noise, plus a Goodhart
trap. The published-elsewhere rule is the wrong rule for our
sample size; the right rule is paired-bootstrap CI with a frozen-
fold non-regression check.

A subtler one: averaging the hallucination and faithfulness scores
before routing lets a hallucinated explanation auto-clear at high
faithfulness. We rewrote the Router to gate them independently and
encoded the invariant as a unit test — it's the single most valuable
test in the suite.

---

## Accomplishments that we're proud of

- **The plan converged through 4 independent review rounds** with
  reviewers spanning M&A domain, architecture, data strategy, and
  hackathon timeline — final scores 9 / 9 / 9.2 / 8.5.
- **The code converged through 4 expert review rounds** (legal, senior
  Python/ADK, Arize Phoenix founding engineer, ML statistician,
  senior SRE) with all 5 validated. The test suite is pure-Python with
  synthetic dataframes and fixed seeds — every rewrite of the SDK
  boundary kept it green and caught logic regressions immediately. See
  `ma_gatekeeper/tests/` for the current count.
- **Two hard pre-commitments locked in writing**: we publish the
  achieved Block-recall Wilson lower bound unmodified, and the demo
  voiceover says "five pre-indexed deals" — no soft-deceptive
  "recently indexed."
- **The Reflector loop is real**, not a sketch — paired-bootstrap CI
  on a regression dataset, frozen-fold non-regression gate, and a
  code-enforced allowlist that refuses Reflector writes to the held-
  out fold 5.

---

## What we learned

The hardest engineering decisions in this kind of agent are the
ones nobody writes about: how to keep your own self-improvement
loop honest, how to abstain rather than overreach, how to keep the
audit trail clickable when the agent is moving fast. Phoenix
makes the observability part close to free — the work is in
operationalizing it correctly.

We also learned that **specialist parallel review beats general
single-pass review** by a wide margin. A Phoenix founding engineer
caught 15 SDK-shape bugs that a senior generalist would have
missed. An ML statistician caught a one-sided / two-sided alpha
mix-up that would have made our headline number look stronger than
the math supports. The commit log looks linear; the workspace
iterations were anything but.

And: **cutting features beats adding them**. Plan v4 has 2
extensions, not 8. Eval has 30 contracts, not 60. UI has one
mandatory pane, not three. Each cut survived a reviewer.

---

## What's next

- **Per-clause precision/recall at the deployed thresholds**, broken
  out by deal-point family — the asymmetric-loss story is only as
  strong as the numbers behind it.
- **Multi-contract data-room mode**: the diligence reality is 50–500
  related contracts, not one merger agreement; the agent's wedge gets
  much larger when cross-references span documents.
- **Playbook customization**: per-firm or per-deal preference profiles
  (e.g. a private-equity acquirer's CoC sensitivity differs from a
  strategic acquirer's).
- **Human-in-the-loop annotation surface** wired to the same Argilla
  pipeline we use today for our gold set — so the Reflector grows
  from live adjudication, not just synthetic regressions.
- **A2A integration**: today the agent is single-team; once exposed
  via the A2A protocol (Linux Foundation, 150+ orgs), upstream
  diligence agents can hand off to it cross-org without re-uploading
  the data room.

---

## Demo scope paragraph (REQUIRED in Devpost description)

> The hosted demo runs against a curated, pre-indexed set of five recent
> 8-K/Ex 2.1 merger filings, pre-validated to surface at least one
> change-of-control, anti-assignment, or MAC-related finding so the
> agent has something interesting to do on camera. The filings are
> fetched live from EDGAR via the EdgarTools MCP server at demo time.

---

## Reflector pre-seeding disclosure (REQUIRED in Devpost description)

> The "production" prompt was deliberately seeded weaker 48 hours
> before demo recording so the auto-improvement loop has a real
> signal to find. The loop logic itself — paired-bootstrap CI,
> frozen-fold non-regression, auto-promotion — is unchanged. Honest
> engineering of reproducibility, not staging.

---

## AI-generated-content disclosure (REQUIRED in Devpost description)

> This project uses Gemini 3 (Pro + Flash) as its core inference
> engine for parsing, classification, cross-referencing, and risk
> judgment. The Reflector self-improvement loop also uses Gemini 3
> Pro to draft candidate prompt versions. Source code, plan
> documents, and submission text were drafted with AI assistance and
> then reviewed by the human author; the M&A domain content was
> additionally cross-checked against current contract drafting
> conventions.

---

## Repo links + supporting docs

- **GitHub**: TBD on D20 (push from `main`).
- **Demo video**: TBD on D19 — YouTube, set to **Public** or
  **Unlisted (link accessible)**, NOT "Unlisted restricted" (Devpost
  has DQ'd projects for the restricted setting).
- **Live demo URL**: TBD — Cloud Run with `min-instances=1` from D20.
- **Plan**: `plan.md` (4-round-converged v4).
- **Audit trail**: `PROJECT_LOG.md`.
- **License**: Apache 2.0.

---

## Devpost submission checklist (lift from HANDOFF.md D20)

- [ ] Arize partner track box ticked.
- [ ] Gallery image / thumbnail uploaded.
- [ ] "Built with" tags listed (above).
- [ ] Team members field populated.
- [ ] All 7 standard text sections (above), each 100–300 words.
- [ ] AI-generated-content disclosure pasted (above).
- [ ] Demo Scope paragraph pasted (above).
- [ ] Reflector pre-seeding disclosure pasted (above).
- [ ] Backup Phoenix screenshot deck linked.
- [ ] Cloud Run warmed with `min-instances=1`.
- [ ] Passcode on the Devpost description (not just README).
- [ ] YouTube link verified accessible from an incognito window —
      privacy MUST be **Public** or **Unlisted (link accessible)**.
      Do NOT use "Unlisted restricted"; Devpost has DQ'd projects
      for it. Open the link in an incognito browser before submitting.
- [ ] Payment-eligibility profile (W-9/W-8BEN) complete on Devpost.
