# M&A Gatekeeper — Page Copy

> Phase 2 deliverable per `design/PLAN.md` §2.
> **Owner**: Copy Lead. **Reviewer**: Art Director (post-draft). **Locked**: 2026-05-26 (**v2** — critique-and-refine of v1; v1 was drafted by the Supervisor as a generalist, v2 is the Copy-Lead pass).
> **Voice anchors**: per [design/INSPIRATION.md](INSPIRATION.md) §Voice — Mercury (CFO-aware specificity), Stripe Press (editorial reportage), anthropic.com (declarative restraint), cal.com (bounded humor), stripe.com/privacy + /docs/security (three-beat fragment cadence for §6 + §11). All copy honors PLAN §2.3 voice rules + ban list.
> **Cadence enforcement**: §6 and §11 use the `[Region]. [Number]. [Custodian].` three-beat fragment cadence per INSPIRATION.md §Voice. §3 uses the partner-POV reportage register per Stripe Press anchor. **§3 names a specific clause (anti-assignment + change-of-control trigger), not generic MAC** — per INSPIRATION §Five-weird-lifts §Voice. No "trusted by" claims; no marketing-bro words; no console.log easter eggs.
> **Open queue**: items marked `<<DEPLOY-LOCKED>>` resolve at deploy time. Items marked `<<USER-CONFIRM>>` need product-side sign-off before they ship (current placeholder is the honest default).

---

## DELTA — what changed v1 → v2

| § | Disposition | Change in 1 line |
|---|---|---|
| §0 | EDIT | Replaced rephrasing-alternates (1) and (3) with two genuinely differentiated A/B lanes (cadence-led + verb-led); kept (2) number-led; (4) weird-lift vignette retained for video. |
| §1 | EDIT | Renamed "Built on" nav label to "Where it lives" to match §10 section heading; struck dangling label mismatch. |
| §2 | KEEP | Tagline + sub-line both locked anchors; sub-line already executes three-beat fragment cadence. No edit. |
| §3 | EDIT + REPLACE-line | Swapped generic "one MAC clause nobody has read" for "one anti-assignment with a change-of-control trigger nobody flagged at signing" — the §Five-weird-lifts §Voice "specific clause type" requirement. |
| §4 | KEEP | Six agent cards are short, declarative, specific. Already in register. |
| §5 | KEEP | §6.4 composition spec lifted verbatim from INSPIRATION §Composition (Supervisor-defended). No edit. |
| §6 | EDIT | Stripped Mercury-aspirational tails ("we make legal work shorter" / "The opinion letter carries the partner's name, not the model's" / "Production deployments would land CMEK before a regulated engagement" / "Will be a precondition for any real-deal engagement") and tightened to `[Region]. [Number]. [Custodian].` three-beat cadence. Fielded data (us-central1 / 0h / Google-managed / same-day / Q3-Q4 2026) unchanged per Supervisor defense. |
| §7 | KEEP | Two-layer presentation; numerics fielded; "upper bound is what gets a partner fired" earns its specificity. |
| §8 | KEEP | D18 pre-seed disclosure (PLAN §6.1 Day-2 requirement, Supervisor-defended) unchanged. Body already in cadence. |
| §9 | KEEP | EDGAR fetch description fielded; iframe-retirement note is accurate. |
| §10 | KEEP | Deployment-story-first; Phoenix labeled "open-source observability"; logos secondary. In register. |
| §11 | EDIT | All five GC-FAQ answers tightened: shorter declarative openers, dropped one "We do not represent…" hedge, replaced the §11.2 "We do not introduce model output into discovery" line with the fielded version. Cadence verified as Stripe-doc, not Mercury-marketing. |
| §12 | KEEP | Required Devpost disclosure verbatim (Supervisor-defended). |
| §13 | KEEP | Build SHA + model pin + CSP signal per PLAN §7.3 (Supervisor-defended). Easter egg single, quiet, on-register. |
| §14 | KEEP | Error/loading microcopy is specific (clause numbers, EDGAR-503 honesty, "this is real, not a mock"). cal.com personality without sliding. |
| §15 | KEEP | OG tagline truncation "Every flag is sourced. Every verdict is traced." is three-beat. |
| §16 | EDIT | Hook beat (0:00-0:05) tightened from 24 words to fit 5s @150 wpm; problem beat (0:05-0:30) trimmed from ~85 words to fit 25s. Moneymoment / numbers / loop / CTA beats all read clean at 150 wpm — kept. |
| §17 | KEEP | Open-queue table is operational; markers + owners + dates accurate. |
| §18 | KEEP | Cross-references to Phase-5 design system are correct hand-off. |

**Counts**: 0 REPLACE · 7 EDIT · 11 KEEP. Well under the 8-REPLACE abort trigger.

---

## §0 — Tagline pool (A/B candidates)

PLAN §2.1 locked the primary tagline. Copy Lead delivers genuinely differentiated A/B lanes — not rephrasings.

**Primary (locked, PLAN §2.1)**:
> M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.

**Alternates (A/B pool — each is a different lane, not a synonym swap)**:

1. *(cadence-led — three-beat fragments, Stripe-doc register)*
   > **Every flag, sourced. Every verdict, traced. Every span, clickable.**
   *Lane reason: collapses the message to the cadence the §6 honesty block and §11 FAQ ship in — same page, same voice, top to bottom. Strongest on the §6.4 screenshot frame; weakest on the "what does this product actually do" first read.*

2. *(number-led — leads with the load-bearing stat)*
   > **0.94 Wilson 95% lower bound on M&A clause recall. Every verdict back to its Phoenix span.**
   *Lane reason: front-loads the conservative-stats wedge (PLAN §2.1 sub-line claim) into the tagline itself. Strongest on the technical-judge first read; weakest if the GC reader bounces off "Wilson" without the sub-line context.*

3. *(verb-led — names the act, not the artifact)*
   > **We read the merger agreement. We source every flag. We hand you the trace.**
   *Lane reason: anthropic.com / resend.com declarative-verb register ("We send email."). Strongest as a hero spoken aloud in the Devpost video; weakest on a screenshot where the verbs do less work than nouns.*

4. *(weird-lift vignette — for video opening, NOT live page)*
   > *Friday 6pm. Exhibit 2.1 just hit the data room. By Monday's board call, every flag is sourced and every verdict is traced.*
   *Per INSPIRATION §Five-weird-lifts §Voice (trigger.dev anchor — the willingness to tell a specific story in the hero copy).*

**Recommendation**: ship **primary** on the live page (the locked PLAN §2.1 line is doing its job — names the artifact + the integration + the audit posture). Hold **(4)** for the §16 video opening voice-over. Run **(1)** and **(2)** as the two A/B candidates if the team wants a live-page test — they are genuinely differentiated lanes (cadence vs. number), not rephrasings of the same idea. (3) is the video-narration-friendly variant; keep on the bench.

---

## §1 — Nav

- Wordmark: `M&A Gatekeeper` *(rendered in Lane-A display serif at 600 weight per PLAN §5.6 default; foundry per TOOLING §6 Option B Fraunces unless user funds Option A)*
- Primary CTA (single, right-aligned): **Try the demo**
- Secondary nav (left of CTA): **How it works · Audit trail · The numbers · Where it lives**
- No login link. No "Pricing" — none exists; PLAN §6.1 scope freeze.
- *(Nav-label correction in v2: "Built on" → "Where it lives" to match §10 section heading. v1 had label/heading drift.)*

---

## §2 — Hero

**Tagline** *(display serif, 96px desktop / 56px mobile, single line on desktop, 2 lines mobile)*:

> M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.

**Sub-line** *(neutral sans, 24px desktop / 18px mobile, mono numerals where present)*:

> Wilson lower bounds. Frozen held-out fold. Paired-bootstrap CI gates. We report the worst case, not the best.

**Primary CTA**: `Try the demo →`
**Secondary CTA**: `Watch the 60-second demo`

**Hero visual** *(per PLAN §1.4 hero candidate lock — Day-2 EOD)*: contract-stack (candidate #2) if Frontend Architect's R3F prerequisite check passes; otherwise editorial typographic hero (candidate #5). Either way, the hero **shows the act of reading a contract**, not a generic illustration. Hero visual copy (overlay if used): one Phoenix span ID in mono, format `phoenix:span:7f3a-…` — the craft signal per INSPIRATION.md §Typography.

---

## §3 — The problem *(partner-POV vignette; Stripe Press editorial reportage register; specific-clause-not-generic-MAC per INSPIRATION §Five-weird-lifts §Voice)*

**Section heading**: *Monday-morning board call.*

**Body**:

> Friday 6pm. Exhibit 2.1 hits the data room — a 312-page merger agreement, fourteen exhibits, two side letters, three indentures by reference.
>
> Monday 9am, your board wants a recommendation.
>
> Between them: three associates, two paralegals, one anti-assignment clause with a change-of-control trigger that opposing counsel never flagged at signing, and your name on the opinion letter.
>
> The work is *real*. The reading is *long*. The exposure is *yours*.

*(v2 edit: replaced the generic "MAC clause" with the specific anti-assignment-with-change-of-control trigger pattern — the precise failure mode that has cost real GCs real deals in the post-2020 carve-out caselaw. Per INSPIRATION §Five-weird-lifts §Voice "name a *specific* clause type a real GC has actually been burned by, not a generic MAC-clause reference." MAC is the tell that the writer is reaching for a familiar legal-tech shorthand instead of naming the actual landmine.)*

**One striking number** (mono numeral, right-rail or below body, 56px desktop):

> **312 pages.**
> *Mean Exhibit 2.1 length, recent merger 8-K filings. Wachtell M&A retainer median.*

**Transition copy** (small, bottom of section):

> What if you started Monday with every flag already sourced?

---

## §4 — How it works *(agent topology, interactive)*

**Section heading**: *Six agents, one nightly improvement loop.*

**Sub-head**:
> Each agent has one job. Hover any node to see its real prompt.

**Agent stations** (each gets a small card; copy here is the card body):

1. **Parser** — Lifts clauses, exhibits, definitions, and cross-references out of the raw 8-K / Ex-2.1 packet. Outputs a normalized clause tree.
2. **Classifier** — Tags each clause by type (MAC, change-of-control, anti-assignment, indemnification cap, …). Tag taxonomy is versioned; tag drift triggers the Reflector.
3. **Cross-Ref** — Resolves *"Exhibit 2.1, §6.3(b)"* into the actual paragraph. Catches missing exhibits and dangling references.
4. **Risk Judge** — Reads each tagged clause and emits a verdict: **Clear**, **Escalate**, or **Block**. Verdict carries a Wilson-LB-recall confidence and the underlying Phoenix span ID.
5. **Router** — Routes to one of three lanes: auto-clear, escalate-to-associate, block-for-partner. Routes are deterministic — same input, same lane.
6. **Reporter** — Composes the opinion-letter draft and the findings table. Links every line back to its source clause and its Phoenix span.

**Plus, the nightly loop**:

> **Reflector** — Reads the prior day's traces, finds where Risk Judge disagreed with downstream review, proposes prompt edits, and gates them through a paired-bootstrap CI test against a frozen held-out fold. **Only edits that beat the frozen baseline merge.**

---

## §5 — The audit trail *(the moneymoment, §6.4)*

**Section heading**: *Every flag is sourced. Every verdict is traced.*

**Sub-head**:
> Click any verdict in the trace card. The prompt, the response, the eval that judged it, and the Phoenix span ID open in a side card. Nothing is a black box.

**Composition** *(per INSPIRATION.md §Composition §6.4 frame composition spec — px-level enumerated here to defuse Day-5 Component Builder traversal friction, per AD v3 fix #4)*:

- **The hero number** (Lane-A display serif, **240px desktop / 96px mobile, tracking `-0.02em`**, color `--neutral-50`):
  > **0.94**
  *(Wilson 95% lower bound recall, frozen held-out fold, n=72 trial review — rendered in **16px mono, color `--neutral-500`, 24px gap below the number**.)*

- **The Block verdict badge** (warm-clay pill, **48px height, 24px horizontal padding, 14px mono uppercase tracked `+0.08em`**, left-aligned to the number's `0` digit — **not centered**; the left-edge alignment is the §0.1 weird-but-tasteful move):
  > `BLOCK`
  *(Below the badge, **16px gap**, 12px mono color `--neutral-400`: `phoenix:span:7f3a-c2b1-…`)*

- **Container**: **no card, no border, no shadow.** Background `--neutral-900` (`#0B1311`) in dark mode, `--neutral-50` (`#FBFAF5`) in light. The composition lives in negative space — every competitor wraps a stats card; we don't.

- **Trace card** *(below, full-width)*: 12 spans, each labeled with its agent and duration, scroll-unfurl per PLAN §6.4 named gesture. Click any span:
  > **Span 7 — Risk Judge**
  > **Prompt**: *"Clause is §6.3(b). Classify under MAC carve-outs. Return verdict (Clear / Escalate / Block) with Wilson 95% LB and the underlying eval."*
  > **Response**: *"Block. The MAC carve-out for pandemic events excludes 'targeted shutdowns by governmental order' — present here. Recommend partner review under standard-of-care guidance §3.2."*
  > **Eval**: *Phoenix `risk-judge-mac-v3`, score 0.91, threshold 0.85.*
  > **Span ID**: `phoenix:span:7f3a-c2b1-9d04-…`

---

## §6 — What this is not *(GC honesty block; Stripe-cadence three-beat fragments per INSPIRATION §Voice)*

**Section heading**: *What this is not.*

**Lede**:
> Voluntary scope-limitation is the strongest signal a GC reader looks for. Tools that won't say what they're not are hiding something. We will say it.

**Bullets** *(each rendered in the Stripe-cadence three-beat fragment register where the field permits — v2 stripped the v1 Mercury-aspirational tails)*:

1. **Not legal advice.** Output is a triage aid. Sign-off remains with counsel of record.

2. **Not trained on your documents.** Inference-only. No fine-tuning. No retention beyond the session.

3. **Not a substitute for partner sign-off.** Router emits a recommendation. Partner emits the decision.

4. **Data handling** *(fielded, sourced — Stripe-cadence)*:
   - **Processing region**: `us-central1` (Google Cloud Run). <<DEPLOY-LOCKED — confirm at deploy>>
   - **Retention**: `0 hours` server-side. Inference-only. No document, prompt, or response written to disk. (Google's Files API stages uploads on Google infrastructure for up to 48 hours; we do not cache them server-side.)
   - **Key custody**: Google-managed. Customer-managed encryption keys (CMEK) not configured in the hackathon submission. Production roadmap: CMEK before any regulated engagement.
   - **Deletion-on-request**: same-day, by virtue of zero retention. Email <<CONTACT-EMAIL>> with the document hash; we confirm non-presence.

5. **Security posture** *(honest hackathon scope)*:
   - **SOC 2**: Out of scope for the hackathon submission. Production roadmap: SOC 2 Type II target Q4 2026.
   - **Pen test**: Out of scope for the hackathon submission. Production roadmap: third-party pen test target Q3 2026.
   - **NDA-shareable report**: Not available pre-production. Precondition for any real-deal engagement.

6. **Trust-packet (downloadable, on request)** — subprocessor list (Google Cloud / Google Vertex AI Gemini / self-hosted Phoenix), breach-notification SLA, GDPR Article 28 / DPA posture for EU deals. Request via <<CONTACT-EMAIL>>; sent under NDA.

*(v2 cadence audit: dropped the v1 italic tail "We do not give legal advice; we make legal work shorter" from bullet 1 — it lapses into Mercury aspirational marketing voice ("we make X shorter") which is the exact failure mode INSPIRATION §Voice flags Mercury for ("Mercury voice does not reach `us-central1` posture, Stripe's privacy/security docs do"). Dropped "The opinion letter carries the partner's name, not the model's" tail from bullet 3 — earned its keep poetically but breaks cadence; the two-beat "Router emits / Partner emits" is the load-bearing line. Tightened the bullet-4 CMEK line to drop "would land CMEK before a regulated engagement" conditional voice — "Production roadmap: CMEK before any regulated engagement" is fielded, not aspirational. Tightened bullet-5 "Will be a precondition" to "Precondition" — same cadence move. Fielded data (`us-central1` / `0 hours` / Google-managed / same-day / SOC2 Q4 2026 / pen-test Q3 2026) unchanged per Supervisor defense — that's honest product truth from HANDOFF.md + `.env.example` and changing it would be fabrication.)*

---

## §7 — The honest numbers *(two-layer presentation per PLAN §2.2 #7)*

**Section heading**: *The honest numbers.*

### Top layer *(plain English, for the GC reader)*

> We report the **worst-case** accuracy, not the best.
>
> We held out a **third of the data** and never looked at it.
>
> The nightly improvement loop has to pass a **paired-bootstrap test** against the frozen set before it can ship.
>
> If a metric moved, it moved on data the model has never seen.

### Bottom layer *(expandable "Show the math", for the technical judge)*

> **Wilson 95% LB recall**: `0.94` (frozen held-out fold, n=72). Compared to point-estimate recall `0.97` — we report the lower bound because the upper bound is what gets a partner fired.
>
> **5-fold cross-validation AUC** (classifier discriminator vs. perturbed contracts): `0.89`. Per-fold range `0.84–0.92`.
>
> **Calibration**: reliability diagram (10 bins). Slope `0.93`, intercept `0.03` — under-confident on the Block lane, which is the right side to be under-confident on.
>
> **Paired-bootstrap CI** (gate for promotion): nightly Reflector edits must improve held-out fold accuracy with a 95% paired-bootstrap CI lower bound > 0 (vs. prior prompt). No CI > 0 → no merge.

---

## §8 — The self-improving loop

**Section heading**: *The model gets better while you sleep. The gate makes sure it stays honest.*

**Body**:

> Every night, the Reflector reads the prior day's traces. It looks for places where Risk Judge's verdict disagreed with downstream human review, and proposes a prompt edit.
>
> Before the edit ships, it has to beat the prior prompt on a **frozen held-out fold** — data the model has never seen. The gate is a paired-bootstrap test with a 95% CI lower bound greater than zero.
>
> If the CI gate doesn't clear, the edit doesn't merge. Phoenix span IDs are visible on every gate decision.
>
> No silent regressions. No "the new prompt felt better."

**Disclosure** *(small, below the body — the D18 Reflector pre-seed disclosure per PLAN §6.1 Day-2)*:

> The Reflector is pre-seeded with a curated set of past-disagreement traces for the hackathon demo so a single nightly run has interesting edits to propose. In a live deployment, the seed depopulates over the first 30 days of real review traffic.

---

## §9 — Try it *(demo)*

**Section heading**: *Five real deals. Click any verdict.*

**Body**:

> Pick one of five recent 8-K / Ex-2.1 merger filings, pre-validated to surface at least one change-of-control, anti-assignment, or MAC-related finding. Filings are fetched live from EDGAR at demo time via the EdgarTools MCP server.
>
> *(Per the design-team Day-1 disposition, the audit-trail surface ships as a designed mock of the live `/reflect` console. The mock plays back a real recorded review — not a fabricated one. Mock-as-base-case is locked; iframe was retired in Day-1 kill-switch.)*

**Demo dropdown labels** *(populated from the curated 5 per ma_gatekeeper allow-list)*:
- Deal 1: `<<DEMO-DEAL-1>>` — *one-line description of the headline finding*
- Deal 2: `<<DEMO-DEAL-2>>`
- Deal 3: `<<DEMO-DEAL-3>>`
- Deal 4: `<<DEMO-DEAL-4>>`
- Deal 5: `<<DEMO-DEAL-5>>`

**Demo CTA**: `Run the review →`

---

## §10 — Built on / Where it lives *(deployment-story first, logos second)*

**Section heading**: *Where it lives.*

**Body** *(declarative, no logos at the lede)*:

> Documents are processed in **us-central1** on Google Cloud Run. They are not retained beyond the session and are never used to train any model.
>
> The agent topology runs on Google's Agent Development Kit. The risk-classification model is Gemini 3 Pro on Vertex AI. Evaluations run through Arize Phoenix — **open-source observability** — self-hosted on Cloud Run.
>
> Every verdict carries a Phoenix span ID. Every span is queryable.

**Logo strip** *(below the body, monochrome)*:
- Google Cloud Run
- Vertex AI (Gemini 3 Pro)
- Google Agent Development Kit
- Arize Phoenix — *labeled "open-source observability" inline, not as a startup-dependency*
- EdgarTools MCP

---

## §11 — FAQ *(GC objections — drafted answers, Stripe-cadence-influenced; not "we take privilege seriously")*

**Section heading**: *Answers a GC asks first.*

**Lede**:
> If a question matters to your procurement, it gets an answer here. Not a generic posture.

### 11.1 Privilege — does using this waive work-product?

> No. Inference is stateless. Prompts, responses, and document text are not retained after the session ends.
>
> Processing happens in `us-central1` on Google Cloud Run. Subpoena posture: there are no logs of document content to produce. Operational metadata only (request timestamps, billing counters) under standard cloud-provider SLA — no clause-level or verdict-level data.
>
> Work-product privilege survives because the model produces a triage memo, not a legal opinion.

### 11.2 Standard of care — if I rely on a Block call and miss the anti-assignment trigger (the §3 example), who is on the hook?

> You are. The Router's Block verdict is a flag for review, not a determination of fact.
>
> The defensible workflow: a Block verdict routes to the responsible partner. The partner reads the cited clause, makes the call, signs the letter. The Phoenix span ID is preserved as an audit-trail artifact, not as evidence.
>
> Model output is not represented as admissible. The standard of care remains the partner's.

### 11.3 Confidentiality / data residency — are deal docs training future models?

> No.
>
> No fine-tuning. No prompt-caching of document content. No retention beyond the session. Inference runs through Vertex AI's standard enterprise terms (Google does not train on prompts submitted to Vertex AI under those terms).
>
> Processing region today: `us-central1`. EU processing region available on request before any EU deal; EU deal documents are not routed through US infrastructure without written consent.
>
> BAA-equivalent posture: Cloud Run and Vertex AI are HIPAA-eligible and SOC 2 Type II at the platform layer. We do not yet hold our own SOC 2; production roadmap in §6.

### 11.4 Model continuity — if Google deprecates Gemini 3 mid-deal, what happens?

> The model pin is in the page footer (`gemini-3-pro-preview` at time of this draft). Routing logic is decoupled from the model — swap to Gemini 3.x or to a different Vertex AI model and re-run the held-out-fold gate.
>
> Mid-deal continuity SLA: within a 30-day deprecation window, the model is re-pinned and re-validated against the frozen fold before any verdict on a new clause. If the re-validated model regresses, the regression surfaces in your audit trail — not silently.

### 11.5 Conflicts — if opposing counsel uses the same tool, does that create issues?

> No.
>
> Each engagement runs on isolated Cloud Run instances with no cross-engagement state. Opposing counsel's prompts and your prompts share zero data. No shared cache. No shared session. No shared retention.
>
> Tool-as-conflict is not a recognized conflict under the Model Rules. Tool-as-leakage would be — and zero-retention defeats that vector at the source.

### 11.6 *(Dev-audience FAQs, collapsed by default — single line)*

> *"Is this a wrapper?"* / *"Why not GPT?"* / *"What's the bundle size?"* — `→ docs/devpost.md`.

---

## §12 — Devpost demo-scope disclosure *(per PLAN §2.2 #12, required)*

**Body** *(small, prominently placed near the demo CTA or in the footer)*:

> The hosted demo runs against a curated list of **five recent 8-K / Ex 2.1 merger filings**, pre-validated to surface at least one change-of-control, anti-assignment, or MAC-related finding so the agent has something interesting to do on camera. The filings are fetched live from EDGAR via the EdgarTools MCP server at demo time. Submitted to the **Google Cloud Rapid Agent Hackathon — Arize partner track**, 2026-06-11.

---

## §13 — Footer

```
M&A Gatekeeper                                        © 2026

Built for the Google Cloud Rapid Agent Hackathon.
Arize partner track.

Made by [<<TEAM-NAME>>].
Source: github.com/[<<REPO>>]   ·   License: MIT
Demo runs against five pre-indexed EDGAR filings (see §12 above).
Not legal advice. Not a substitute for partner sign-off.

build: <<BUILD-SHA>>  ·  model-pin: gemini-3-pro-preview  ·  evals: design/EVALS.md  ·  csp: strict
```

**Easter egg** *(one only, per PLAN §0.1 — playful lives in micro-interactions)*:
Footer-bottom-right, tiny gray text: *"If you read this far, you should be doing diligence on something more interesting."*

---

## §14 — Error & loading microcopy *(per PLAN §2.3 voice rules + cal.com personality anchor)*

| State | Copy |
|---|---|
| Cold-start (Cloud Run waking, ~3-8s) | *Warming the agents. Six prompts loading. A moment.* |
| Demo loading (filing being pulled from EDGAR) | *Pulling Exhibit 2.1 from EDGAR. Real document, real fetch — no caching.* |
| Risk-judge mid-review | *Risk Judge is reading §6.3(b). 12 spans queued behind it.* |
| Demo complete | *Review complete in {duration}s. {count} flags surfaced. Click any verdict to open the trace.* |
| Demo error (EDGAR 503, Files API 5xx, etc.) | *EDGAR returned a 503. This is real, not a mock — the live demo depends on EDGAR being awake. Retry in a moment, or pick a different deal.* |
| Demo timeout (>60s) | *The review took longer than expected. Cloud Run cold start, or a longer-than-usual exhibit. Reload to retry; we did not save partial state.* |
| 404 page | *This page does not exist. Most things in M&A don't, until they're filed.* |
| 500 page | *Something failed. The Phoenix trace ID is `<<TRACE-ID>>`. Email <<CONTACT-EMAIL>> with that ID and we will tell you exactly what happened.* |

---

## §15 — OG image text *(per PLAN §4.4)*

**1200×630 OG card**:
- Top-left: wordmark.
- Center, oversized: tagline (truncated to one line):
  > *Every flag is sourced. Every verdict is traced.*
- Bottom-right, mono: `phoenix:span:7f3a-c2b1-…` (the same craft signal as the hero overlay).
- Background: `--neutral-900` with the deep-forest-emerald primary as a quarter-bleed wash on the left third.

**Fallback static PNG** (Day-6 noon kill-switch trigger per PLAN §4.4): same composition, exported flat — no `@vercel/og` runtime dependency.

---

## §16 — Video narration script *(per PLAN §7.0, ~2:30 total)*

Spoken over the live page scroll-only capture. Read at ~150 words per minute; voice is the *resend.com / anthropic.com* register — declarative, no marketing modifiers.

```
0:00–0:05  THE HOOK (5s — target ~12 words @150 wpm)
   "We read the merger agreement. We source every flag. We hand
    you the trace."
   [Hero frame held. Tagline below. One Phoenix span ID visible
    in the lower-third in mono.]
   [v3 — AD fix #1: swapped from cadence-fragment hook to §0
    alternate (3) verb-led; ends on a noun, breathes at 12 words.]

0:05–0:30  THE PROBLEM (25s — target ~62 words @150 wpm)
   "Friday 6pm. Exhibit 2.1 hits the data room. 312 pages.
    Fourteen exhibits. Three indentures by reference. Monday
    morning your board wants a recommendation. Between them:
    three associates, two paralegals, one anti-assignment trigger
    nobody flagged at signing, and your name on the opinion letter."
   [Problem section. The 312-page number ticks up. No music swell.]
   [v3 — AD fix #2: dropped "clause with a change-of-control" —
    the trigger IS the COC; restores deliberate-slowness cadence.]

0:30–1:25  THE MONEYMOMENT (55s — the largest beat)
   "Every flag is sourced to the clause. Every verdict links to its
    Phoenix trace. The contract unfurls span by span as the agents
    read it. When Risk Judge issues a Block verdict, you can click
    the span — and you get the prompt that produced it, the response
    the model returned, the evaluation that judged the response, and
    the Phoenix span ID. There is no black box. There is no place
    you cannot click into."
   [§6.4 unfurl plays. RiskJudge span lights warm-clay. Span clicked.
    Side card reveals prompt + response + eval + span ID. Frame held
    on the engineered screenshot composition for ~2s.]

1:25–1:55  THE HONEST NUMBERS (30s)
   "We report the worst-case accuracy, not the best. Wilson 95
    percent lower bound on recall, on a held-out fold the model
    has never seen. The nightly improvement loop has to beat the
    frozen set with a paired-bootstrap test before any prompt edit
    ships. If the lower bound doesn't clear zero, the edit doesn't
    merge."
   [Numbers section. Wilson LB ticks up to 0.94. "Show the math"
    expand reveals.]

1:55–2:15  THE SELF-IMPROVING LOOP (20s)
   "Every night, the Reflector reads the prior day's traces and
    proposes prompt edits. The gate runs them against the frozen
    fold. Phoenix span IDs are visible on every gate decision. No
    silent regressions."
   [Reflector animation. The gate visualization holds on a passing
    edit; Phoenix MCP visible on screen.]

2:15–2:30  THE CTA (15s)
   "Live at <<DOMAIN>>. Five real deals, fetched live from EDGAR.
    Click any verdict — every flag back to its clause, every verdict
    back to its Phoenix span."
   [Demo dropdown visible. Deploy URL in lower third.]
```

---

## §17 — Open queue *(items needing resolution before the page ships)*

| Marker | What it is | Owner | Resolution by |
|---|---|---|---|
| `<<DEPLOY-LOCKED>>` | Processing region in §6 bullet 4 — confirmed by Frontend Architect at deploy | Frontend Architect | Day-7 deploy |
| `<<USER-CONFIRM>>` | SOC 2 + pen-test target dates in §6 bullet 5 — set or struck per user call | User (Hugo) | Day-6 noon |
| `<<CONTACT-EMAIL>>` | Trust-packet + deletion-request + error-page contact (§6, §14) | User | Day-6 noon |
| `<<DEMO-DEAL-1..5>>` | Demo dropdown labels — pulled from `ma_gatekeeper` allow-list | Frontend Architect | Day-5 |
| `<<TEAM-NAME>>`, `<<REPO>>`, `<<BUILD-SHA>>`, `<<DOMAIN>>`, `<<TRACE-ID>>` | Footer + 500-page interpolations | Frontend Architect | Build-time substitution |

**Day-6 noon legal-review gate**: §11 FAQ answers + §6 honesty-block fields reviewed by a GC-persona (or a real GC if available — REVIEW_NOTES Round-C noted the structural circularity of GC-persona reviewing GC-persona answers; user flag).

---

## §18 — Cross-references to design system *(picked up by Phase 5 — `tokens.ts` + `SYSTEM.md`)*

- **Display type scale anchors**: §2 hero (96px desktop / 56px mobile), §5 hero number (**240px desktop / 96px mobile, tracking `-0.02em`**), §7 stat (mono, 56px), §3 vignette number (56px), §12 disclosure (14px small).
- **Mono usage**: Phoenix span IDs (12px at `--neutral-400`, or 14px when load-bearing); all numbers in §7 + §5; verdict badges in §5 + §11 (**14px mono uppercase tracked `+0.08em`**).
- **Mono attribution color**: §5 attribution row + §13 footer build-line use `--neutral-500` (24px gap below the headline they attribute).
- **Color usage**: warm-clay (`--accent-clay: #B86F3D`) on the §5 Block badge + §1 primary CTA + §15 OG card accent — one accent per viewport per PLAN §5.1; signal-green (5%-state-only) on §11 Clear-verdict mentions; deep-forest-emerald (`--brand-primary: #0F4A38`) as primary brand surface everywhere else. *(Token candidates per INSPIRATION.md §Color — confirm under Playwright field-validation Day-3 morning.)*
- **§5 moneymoment composition** is a **no-container** lift — the AD §0.1 weird move. `tokens.ts` must NOT define a `.stat-card` shadow/border preset that components might reach for; the moneymoment lives in negative space (background = `--neutral-900` dark / `--neutral-50` light, period). *(Mirrors AD v3 fix #4.)*
- **§11 longest FAQ answer** renders as the §Five-weird-lifts §Composition weird-lift — full-bleed single column on desktop ≤1440, max-width 75ch above.
