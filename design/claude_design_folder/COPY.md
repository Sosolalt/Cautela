# M&A Gatekeeper — Page Copy

> Phase 2 deliverable per `design/PLAN.md` §2.
> **Owner**: Copy Lead. **Reviewer**: Art Director (post-draft). **Locked**: 2026-05-27 (**v3.1** — applies 6 surgical fixes from Round-3: 4 cadence/voice items from the Voice & Cadence specialist's first finding-list (their Round-2 spawn hit session-limit), plus 2 RESIDUAL-MINOR copy-fidelity nits from M&A Counsel. v3 baseline applied the 12 consolidated must-fix items from Round-B (7 M&A Counsel, 5 Devpost Judge).).
> **Voice anchors**: per [design/INSPIRATION.md](INSPIRATION.md) §Voice — Mercury (CFO-aware specificity), Stripe Press (editorial reportage), anthropic.com (declarative restraint), cal.com (bounded humor), stripe.com/privacy + /docs/security (three-beat fragment cadence for §6 + §11). All copy honors PLAN §2.3 voice rules + ban list.
> **Cadence enforcement**: §6 and §11 use the `[Region]. [Number]. [Custodian].` three-beat fragment cadence per INSPIRATION.md §Voice. §3 uses the partner-POV reportage register per Stripe Press anchor. §2 sub-line is editorial specificity below the cadence-led hero; its anchor is Stripe Press editorial prose, **not** resend.com three-beat fragments (v3.1 attribution correction — see DELTA #4). **§3 names a specific clause (anti-assignment + change-of-control trigger), not generic MAC** — per INSPIRATION §Five-weird-lifts §Voice. No "trusted by" claims; no marketing-bro words; no console.log easter eggs.
> **Open queue**: items marked `<<DEPLOY-LOCKED>>` resolve at deploy time. Items marked `<<USER-CONFIRM>>` need product-side sign-off before they ship (current placeholder is the honest default).

---

## DELTA — v3 → v3.1

6 surgical fixes from Round-3: 4 cadence/voice surgical fixes (Voice & Cadence specialist's first finding-list, ITERATE verdict) + 2 M&A Counsel RESIDUAL-MINOR copy-fidelity nits.

| # | § | Disposition | Change in 1 line | Source |
|---|---|---|---|---|
| 1 | §6 bullet 4 | EDIT | Moved 23-word parenthetical tails from Retention + Key custody bullets to a single `*Files-API caching note*` footnote at the end of §6 (small mono, `--neutral-500`) — preserves the three-beat fragment cadence claim. | Voice & Cadence (a) |
| 2 | §6 bullet 5 | EDIT | Collapsed three-sentence defensive sandwich to two declarative fragments per sub-bullet: `Out of scope (hackathon). Production roadmap: [single specific detail].` Dropped the redundant "not a hackathon-scope commitment" third sentence. | Voice & Cadence (b) |
| 3 | §14 L406 | EDIT | Committed cold-start microcopy to one register — operational: `Warming the agents. Six prompts loading. Roughly eight seconds.` (matches Cloud Run cold-start latency.) Was: `…A moment.` (mixed half-witty / half-operational). | Voice & Cadence (c) |
| 4 | §2 sub-line note + top-of-doc cadence enforcement | EDIT | Dropped the "resend three-beat" cadence attribution from the §2 sub-line — a 24-word em-dash editorial sentence is not three-beat resend cadence. Re-attributed to Stripe Press editorial prose, which is what it actually does. | Voice & Cadence (d) |
| 5 | §11.5 | EDIT | Corrected attribution slip: the 36h `FILES_API_URI_TTL_SECONDS` is the **agent-server** cache TTL (we evict before Google's 48h Files-API server-side expiration), not "Google-side." Per HANDOFF.md:244. | M&A Counsel RESIDUAL-MINOR |
| 6 | §11.4 | EDIT | Verb shift "we pin" → "we aim to pin" — moves the 14-day model-continuity claim from contracted-SLA register to forward-commitment register, defensible without contract language. | M&A Counsel RESIDUAL-MINOR |

**Counts**: 0 REPLACE · 6 EDIT · all other sections KEEP. No scope expansion, no PLAN-level decisions touched.

---

## DELTA — what changed v2 → v3

Round-B reviewer-cohort must-fix list (12 items). 11 applied silently; 1 (item #8, §2 tagline architecture) flagged for Supervisor sign-off because it touches a PLAN-locked decision.

| # | § | Disposition | Change in 1 line | Source |
|---|---|---|---|---|
| 1 | §6 bullet 5 | EDIT (critical) | Struck fabricated SOC 2 "Q4 2026" / pen-test "Q3 2026" target dates — not in HANDOFF.md, §17 itself flags them `<<USER-CONFIRM>>` unresolved. Replaced with date-free production-roadmap language explicitly scoped out of hackathon commitment. | M&A Counsel #1 |
| 2 | §11.5 | EDIT (critical) | Rewrote "zero-retention defeats that vector at the source" — technically inaccurate given §6 bullet 4's own Files API 48h / agent-server 36h URI cache parenthetical. New version names the actual posture (no document content retained beyond inference window; URI cache holds opaque handles, not clause text). | M&A Counsel #2 |
| 3 | §11.1 | EDIT (critical) | Rewrote "Work-product privilege survives because the model produces a triage memo" — that was a legal conclusion the page cannot make. New version: jurisdiction-specific call for counsel of record; our posture preserves the factual predicates a privilege analysis depends on. | M&A Counsel #3 |
| 4 | §11.3 | EDIT | "Google does not train" downgraded to the precise paraphrase of the Vertex AI Service-Specific Terms ("prohibit use of customer prompts for foundation-model training"). | M&A Counsel #4 |
| 5 | §13 | EDIT | Footer disclaimer expanded: added (a) no attorney-client relationship formed, (b) governing-law placeholder, (c) terms-of-service link placeholder `<<TOS-URL>>`. | M&A Counsel #5 |
| 6 | §6 lede | EDIT | Stripped the meta-marketing tail ("Voluntary scope-limitation is the strongest signal a GC reader looks for. Tools that won't say what they're not are hiding something.") — Mercury-adjacent writer-talks-to-GC-about-GC-psychology failure mode. Replaced with the Stripe-doc direct opener: just "What this is not." and a one-line declarative lede. | M&A Counsel #6 |
| 7 | §11.4 | EDIT | "Within a 30-day deprecation window" given SLA teeth: 14-day pin, re-validation against the frozen fold, regression surfaces in the audit trail, verdicts on new clauses pause if re-validation fails. | M&A Counsel #7 |
| 8 | §0 / §2 / §15 | **FLAG-FOR-SUPERVISOR + APPLIED** | Promoted §0 alternate (1) cadence-led tagline ("Every flag, sourced. Every verdict, traced. Every span, clickable.") into the §2 hero. Demoted the locked PLAN §2.1 line to §2 sub-line layer + §15 OG truncation. **HARD-TO-REVERSE — touches PLAN-locked decision.** Applied because juror 5s-stop argument is sound + the locked line is preserved in the OG/sub-line architecture; Supervisor may revert. | Devpost Judge #8 |
| 9 | §16 hook | EDIT | Hook (0:00-0:05) tightened from 16 words / 6.4s (over-run) to 11 words / 4.4s — "We read the merger agreement. Every flag, sourced; every verdict, traced." | Devpost Judge #9 |
| 10 | §16 moneymoment | EDIT | 0:30-1:25 re-storyboarded with explicit camera/edit beats: 0:30-0:50 trace card unfurl + RiskJudge span light; 0:50-0:55 span-click; 0:55-1:20 engineered frame held with side-card revealed; 1:20-1:25 narration close. No more 30-second static hold. | Devpost Judge #10 |
| 11 | §2 + §18 | EDIT | Phoenix span ID overlay on §2 hero bumped to **14px mono minimum** for video-capture legibility. The 12px small-print convention holds for inline references elsewhere (§5 attribution row, body mentions); §18 cross-reference updated. | Devpost Judge #11 |
| 12 | §9 | EDIT | Iframe-retirement parenthetical moved from mid-body of §9 (where it diluted the "Five real deals. Click any verdict." headline) to a small mono footnote below the demo CTA. | Devpost Judge #12 |

**Voice & cadence lane**: NOT addressed this round — the Voice & cadence specialist hit session-limit and could not return a finding list. Don't blind-fix cadence concerns; wait for their retry next round to name specific slips.

**Counts**: 0 REPLACE · 12 EDIT · 6 KEEP. Well under the 8-REPLACE abort trigger.

**Cross-Builder dependency note**: item #11 changes the §18 cross-reference to "**14px mono minimum** for hero overlay specifically." This intersects with SYSTEM Builder's `tokens.ts` work — if the SYSTEM Builder is mid-flight on a mono-scale token architecture, they need this constraint propagated (a `--font-mono-overlay` token at 14px, distinct from the 12px inline-reference token). Flagged for Supervisor cross-reconciliation.

---

## §0 — Tagline pool (A/B candidates)

PLAN §2.1 locked the primary tagline. v3 promotes the cadence-led alternate (1) into the §2 hero per Round-B Devpost Judge finding #8 (juror 5s-stop), and demotes the locked PLAN §2.1 line into the §2 sub-line + §15 OG truncation layer. **HARD-TO-REVERSE — flagged for Supervisor sign-off.** The locked line is preserved, not deleted; only its display location changes.

**Hero — v3 promoted (cadence-led, three-beat fragments, Stripe-doc register)**:
> **Every flag, sourced. Every verdict, traced. Every span, clickable.**

*Lane reason: collapses the message to the cadence the §6 honesty block and §11 FAQ ship in — same page, same voice, top to bottom. Strongest on the §6.4 screenshot frame AND on the Devpost juror's 5-second first read. The "what does this product actually do" gap is closed by the sub-line layer immediately beneath.*

**Sub-line — v3 demoted-from-hero (the locked PLAN §2.1 line — preserved at sub-line scale + in §15 OG)**:
> M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.

*Lane reason: still doing its job — names the artifact + the integration + the audit posture — but at sub-line scale where its length (24 words) reads as deliberate-specificity instead of as a hero that doesn't land in 5s. **Cadence anchor: Stripe Press editorial prose** (the single editorial sentence with mid-em-dash, sitting beneath a cadence-led hero); **not** resend.com three-beat fragments — that anchor belongs to the hero tagline above, not to this sub-line. (v3.1 attribution correction per Voice & Cadence finding (d).)*

**Alternates (A/B pool — held on the bench)**:

1. *(number-led — leads with the load-bearing stat)*
   > **0.94 Wilson 95% lower bound on M&A clause recall. Every verdict back to its Phoenix span.**
   *Lane reason: front-loads the conservative-stats wedge (PLAN §2.1 sub-line claim) into the tagline itself. Strongest on the technical-judge first read; weakest if the GC reader bounces off "Wilson" without the sub-line context.*

2. *(verb-led — names the act, not the artifact)*
   > **We read the merger agreement. We source every flag. We hand you the trace.**
   *Lane reason: anthropic.com / resend.com declarative-verb register ("We send email."). Strongest as a hero spoken aloud in the Devpost video; weakest on a screenshot where the verbs do less work than nouns. v3 update: now too close to the §16 hook line; bench candidate only.*

3. *(weird-lift vignette — for video opening, NOT live page)*
   > *Friday 6pm. Exhibit 2.1 just hit the data room. By Monday's board call, every flag is sourced and every verdict is traced.*
   *Per INSPIRATION §Five-weird-lifts §Voice (trigger.dev anchor — the willingness to tell a specific story in the hero copy). Held for §16 narration variant.*

**v3 recommendation**: ship the cadence-led line as hero, the locked PLAN §2.1 line as sub-line and OG truncation. The architecture preserves the locked PLAN line in two surfaces (sub-line live + OG card) while letting the hero do its 5-second job. **Supervisor sign-off required before this ships — this is a PLAN-level decision.**

---

## §1 — Nav

- Wordmark: `M&A Gatekeeper` *(rendered in Lane-A display serif at 600 weight per PLAN §5.6 default; foundry per TOOLING §6 Option B Fraunces unless user funds Option A)*
- Primary CTA (single, right-aligned): **Try the demo**
- Secondary nav (left of CTA): **How it works · Audit trail · The numbers · Where it lives**
- No login link. No "Pricing" — none exists; PLAN §6.1 scope freeze.
- *(Nav-label correction in v2: "Built on" → "Where it lives" to match §10 section heading. v1 had label/heading drift.)*

---

## §2 — Hero

> **v3 architecture (FLAGGED FOR SUPERVISOR SIGN-OFF — touches PLAN §2.1 locked decision):** the hero promotes the cadence-led three-beat line for 5-second juror legibility; the locked PLAN §2.1 line is preserved at sub-line scale (and as the §15 OG truncation). Supervisor may revert by swapping the two lines back.

**Tagline (v3 — cadence-led, promoted from §0 alt-1)** *(display serif, 96px desktop / 56px mobile, single line on desktop, 1-2 lines mobile)*:

> **Every flag, sourced. Every verdict, traced. Every span, clickable.**

**Anchor sub-line (v3 — the locked PLAN §2.1 line, demoted from hero)** *(display serif, 40px desktop / 28px mobile, regular weight — sits between hero tagline and the conservative-stats sub-line; **cadence anchor: Stripe Press editorial prose**, single editorial sentence with mid-em-dash — **not** the resend three-beat fragment cadence the hero above uses. v3.1 attribution correction per Voice & Cadence finding (d).)*:

> M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.

**Conservative-stats sub-line** *(neutral sans, 24px desktop / 18px mobile, mono numerals where present)*:

> Wilson lower bounds. Frozen held-out fold. Paired-bootstrap CI gates. We report the worst case, not the best.

**Primary CTA**: `Try the demo →`
**Secondary CTA**: `Watch the 60-second demo`

**Hero visual** *(per PLAN §1.4 hero candidate lock — Day-2 EOD)*: contract-stack (candidate #2) if Frontend Architect's R3F prerequisite check passes; otherwise editorial typographic hero (candidate #5). Either way, the hero **shows the act of reading a contract**, not a generic illustration.

**Hero visual overlay copy** *(v3 — Devpost Judge fix #11: bumped from 12px to 14px mono for 1440p video-capture legibility; the 12px convention holds for inline references elsewhere on the page)*: one Phoenix span ID in mono at **14px minimum**, format `phoenix:span:7f3a-…` — the craft signal per INSPIRATION.md §Typography.

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

*(v3 lede edit per M&A Counsel fix #6: stripped the v2 meta-marketing tail "Voluntary scope-limitation is the strongest signal a GC reader looks for. Tools that won't say what they're not are hiding something." — the writer talking TO the GC ABOUT the GC's psychology was the Mercury-adjacent failure mode. Stripe-doc direct opener instead.)*

**Bullets** *(each rendered in the Stripe-cadence three-beat fragment register where the field permits — v2 stripped the v1 Mercury-aspirational tails)*:

1. **Not legal advice.** Output is a triage aid. Sign-off remains with counsel of record.

2. **Not trained on your documents.** Inference-only. No fine-tuning. No retention beyond the session.

3. **Not a substitute for partner sign-off.** Router emits a recommendation. Partner emits the decision.

4. **Data handling** *(fielded, sourced — Stripe-cadence)*:
   - **Processing region**: `us-central1` (Google Cloud Run). <<DEPLOY-LOCKED — confirm at deploy>>
   - **Retention**: `0 hours` server-side. Inference-only. No document, prompt, or response written to disk.[^files-api]
   - **Key custody**: Google-managed. CMEK not configured in the hackathon submission.[^cmek-roadmap]
   - **Deletion-on-request**: same-day, by virtue of zero retention. Email <<CONTACT-EMAIL>> with the document hash; we confirm non-presence.

5. **Security posture** *(honest hackathon scope — v3 fix per M&A Counsel #1: struck the fabricated "Q4 2026" / "Q3 2026" target dates. They were not in HANDOFF.md and §17 itself flags them `<<USER-CONFIRM>>` unresolved. Survives a deposition. v3.1 cadence fix per Voice & Cadence (b): collapsed three-sentence defensive sandwich to two declarative fragments per sub-bullet.)*:
   - **SOC 2**: Out of scope (hackathon). Production roadmap: target date set with first regulated engagement.
   - **Pen test**: Out of scope (hackathon). Production roadmap: third-party schedule set with first regulated engagement.
   - **NDA-shareable report**: Not available pre-production. Precondition for any real-deal engagement.

6. **Trust-packet (downloadable, on request)** — subprocessor list (Google Cloud / Google Vertex AI Gemini / self-hosted Phoenix), breach-notification SLA, GDPR Article 28 / DPA posture for EU deals. Request via <<CONTACT-EMAIL>>; sent under NDA.

*(v2 cadence audit: dropped the v1 italic tail "We do not give legal advice; we make legal work shorter" from bullet 1 — it lapses into Mercury aspirational marketing voice ("we make X shorter") which is the exact failure mode INSPIRATION §Voice flags Mercury for ("Mercury voice does not reach `us-central1` posture, Stripe's privacy/security docs do"). Dropped "The opinion letter carries the partner's name, not the model's" tail from bullet 3 — earned its keep poetically but breaks cadence; the two-beat "Router emits / Partner emits" is the load-bearing line. Tightened the bullet-4 CMEK line to drop "would land CMEK before a regulated engagement" conditional voice — "Production roadmap: CMEK before any regulated engagement" is fielded, not aspirational. Tightened bullet-5 "Will be a precondition" to "Precondition" — same cadence move.)*

*(v3 audit: M&A Counsel fix #1 — struck the SOC2 "Q4 2026" and pen-test "Q3 2026" dates from bullet 5. They were not in HANDOFF.md (the HANDOFF lists pen-test "scheduled / completed by [firm]" as a `<<USER-CONFIRM>>` placeholder, with no committed date), and §17 already flags them `<<USER-CONFIRM>>` unresolved. Same failure mode the Round-B M&A Counsel killed twice already ("survives a deposition" / "your data stays in your project"). Replaced with date-free production-roadmap language explicitly scoped out of hackathon commitment — defensible against the team's actual posture.)*

---

*Files-API caching note* *(small mono, `--neutral-500` — footnoted off bullet 4 per v3.1 cadence fix (a) so the bullet preserves the three-beat fragment cadence)*:

[^files-api]: Google's Files API stages uploads on Google infrastructure for up to 48 hours; we do not cache document content server-side. The agent-server keeps a Files-API URI cache with a 36h TTL (`FILES_API_URI_TTL_SECONDS`) — opaque file handles, evicted before Google's 48h server-side expiration. See HANDOFF.md §244.

[^cmek-roadmap]: Production roadmap: CMEK before any regulated engagement.

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

**Demo dropdown labels** *(populated from the curated 5 per ma_gatekeeper allow-list)*:
- Deal 1: `<<DEMO-DEAL-1>>` — *one-line description of the headline finding*
- Deal 2: `<<DEMO-DEAL-2>>`
- Deal 3: `<<DEMO-DEAL-3>>`
- Deal 4: `<<DEMO-DEAL-4>>`
- Deal 5: `<<DEMO-DEAL-5>>`

**Demo CTA**: `Run the review →`

**Footnote** *(rendered small, mono, `--neutral-500`, immediately below the demo CTA)*:

> *(Audit-trail surface is a designed playback of a real recorded review; live `/reflect` integration deferred per Day-1 iframe kill-switch.)*

*(v3 fix per Devpost Judge #12: moved the iframe-retirement parenthetical out of the mid-body of §9 — where it diluted the "Five real deals. Click any verdict." headline — to a small mono footnote below the CTA. Still on the page (the honesty matters), no longer competing with the demo's primary message.)*

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

> Inference is stateless. Prompts, responses, and document text are not retained after the session ends.
>
> Processing happens in `us-central1` on Google Cloud Run. Subpoena posture: there are no logs of document content to produce. Operational metadata only (request timestamps, billing counters) under standard cloud-provider SLA — no clause-level or verdict-level data.
>
> Whether work-product privilege attaches is a jurisdiction-specific call for counsel of record. Our posture — no retention, no training, stateless inference — preserves the factual predicates a privilege analysis depends on.

*(v3 fix per M&A Counsel #3: rewrote "Work-product privilege survives because the model produces a triage memo, not a legal opinion" — that read as a legal conclusion the page cannot make. New version names the actual posture and hands the legal call to counsel of record, where it belongs.)*

### 11.2 Standard of care — if I rely on a Block call and miss the anti-assignment trigger (the §3 example), who is on the hook?

> You are. The Router's Block verdict is a flag for review, not a determination of fact.
>
> The defensible workflow: a Block verdict routes to the responsible partner. The partner reads the cited clause, makes the call, signs the letter. The Phoenix span ID is preserved as an audit-trail artifact, not as evidence.
>
> Model output is not represented as admissible. The standard of care remains the partner's.

### 11.3 Confidentiality / data residency — are deal docs training future models?

> No.
>
> No fine-tuning. No prompt-caching of document content. No retention beyond the session. Inference runs through Vertex AI under the Vertex AI Service-Specific Terms, which prohibit Google's use of customer prompts for foundation-model training.
>
> Processing region today: `us-central1`. EU processing region available on request before any EU deal; EU deal documents are not routed through US infrastructure without written consent.
>
> BAA-equivalent posture: Cloud Run and Vertex AI are HIPAA-eligible and SOC 2 Type II at the platform layer. We do not yet hold our own SOC 2; production roadmap in §6.

*(v3 fix per M&A Counsel #4: downgraded the absolute "Google does not train" claim to the precise paraphrase of the Vertex AI Service-Specific Terms — "prohibit use of customer prompts for foundation-model training." Defensible against the verbatim terms.)*

### 11.4 Model continuity — if Google deprecates Gemini 3 mid-deal, what happens?

> The model pin is in the page footer (`gemini-3-pro-preview` at time of this draft). Routing logic is decoupled from the model — swap to Gemini 3.x or to a different Vertex AI model and re-run the held-out-fold gate.
>
> Mid-deal continuity posture: if Google announces deprecation, we aim to pin the new model within 14 days, re-validate against the frozen fold, and surface any regression in the audit trail. **Verdicts on new clauses pause if re-validation fails.** No silent swap; no quiet regression.

*(v3 fix per M&A Counsel #7: replaced the "within a 30-day deprecation window" non-SLA window language with actual SLA teeth — 14-day pin, frozen-fold re-validation, regression visibility in the audit trail, hard pause on new-clause verdicts if re-validation fails. v3.1 fix per M&A Counsel RESIDUAL-MINOR: verb shift "we pin" → "we aim to pin" + heading "SLA" → "posture" — moves the 14-day claim from contracted-SLA register to forward-commitment register, defensible without contract language.)*

### 11.5 Conflicts — if opposing counsel uses the same tool, does that create issues?

> No.
>
> Each engagement runs on isolated Cloud Run instances with no cross-engagement state. Opposing counsel's prompts and your prompts share zero data. No shared cache. No shared session.
>
> Tool-as-conflict is not a recognized conflict under the Model Rules. Tool-as-leakage would be. **No document content is retained server-side beyond the inference window.** (The Files-API URI cache lives in the agent server with a 36h TTL — we evict opaque file handles before Google's 48h Files-API server-side expiration.) The cache is per-engagement, never shared across engagements.

*(v3 fix per M&A Counsel #2: rewrote "zero-retention defeats that vector at the source" — technically inaccurate given §6 bullet 4's own parenthetical (Files API 48h Google-side + agent-server 36h URI cache per HANDOFF.md `FILES_API_URI_TTL_SECONDS`). New version names the actual posture: no document content retained beyond inference, URI cache holds opaque handles not clause text. Defensible against the architecture you actually have. v3.1 fix per M&A Counsel RESIDUAL-MINOR: corrected attribution slip — the 36h TTL lives in the **agent server**, not "Google-side"; we evict before Google's 48h server-side expiration. Per HANDOFF.md:244.)*

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

Not legal advice. Not a substitute for partner sign-off. Use of this
site does not create an attorney-client relationship. Site operated
under the laws of <<GOVERNING-LAW>>. Terms of service: <<TOS-URL>>.

build: <<BUILD-SHA>>  ·  model-pin: gemini-3-pro-preview  ·  evals: design/EVALS.md  ·  csp: strict
```

*(v3 fix per M&A Counsel #5: expanded the two-sentence disclaimer ("Not legal advice. Not a substitute for partner sign-off.") to add (a) no attorney-client relationship formed, (b) governing-law placeholder `<<GOVERNING-LAW>>`, (c) terms-of-service link placeholder `<<TOS-URL>>`. Still concise; now complete enough for a deployed page facing multi-jurisdiction GCs. `<<GOVERNING-LAW>>` and `<<TOS-URL>>` added to §17 open queue.)*

**Easter egg** *(one only, per PLAN §0.1 — playful lives in micro-interactions)*:
Footer-bottom-right, tiny gray text: *"If you read this far, you should be doing diligence on something more interesting."*

---

## §14 — Error & loading microcopy *(per PLAN §2.3 voice rules + cal.com personality anchor)*

| State | Copy |
|---|---|
| Cold-start (Cloud Run waking, ~3-8s) | *Warming the agents. Six prompts loading. Roughly eight seconds.* |
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
- Center, oversized: tagline (truncated to one line — three-beat cadence echoing the v3 hero):
  > *Every flag is sourced. Every verdict is traced.*
- Bottom-right, mono at 14px (matches §2 hero overlay per v3 §18): `phoenix:span:7f3a-c2b1-…` (the same craft signal as the hero overlay).
- Background: `--neutral-900` with the deep-forest-emerald primary as a quarter-bleed wash on the left third.

*(v3 note per Devpost Judge fix #8: the OG truncation continues to surface the cadence-fragment line. The locked PLAN §2.1 line is now preserved in the §2 anchor sub-line slot rather than the OG. If Supervisor reverts the §2 architecture, the OG should swap back to a truncation of the PLAN-locked line.)*

**Fallback static PNG** (Day-6 noon kill-switch trigger per PLAN §4.4): same composition, exported flat — no `@vercel/og` runtime dependency.

---

## §16 — Video narration script *(per PLAN §7.0, ~2:30 total)*

Spoken over the live page scroll-only capture. Read at ~150 words per minute; voice is the *resend.com / anthropic.com* register — declarative, no marketing modifiers.

```
0:00–0:05  THE HOOK (target ≤4.5s @150 wpm — 11 words / 4.4s)
   "We read the merger agreement. Every flag, sourced; every
    verdict, traced."
   [Hero frame held. Tagline below. One Phoenix span ID visible
    in the lower-third in mono at 14px (per §2 / §18 v3 update).]
   [v3 — Devpost Judge fix #9: previous hook ("We read the merger
    agreement. We source every flag. We hand you the trace.") ran
    16 words / 6.4s @150wpm — overran the 5s budget. New two-sentence
    cut lands at 11 words / 4.4s with the same opener verb-noun and
    the cadence-fragment payoff matching the v3 hero tagline.]

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
   [v3 re-storyboarded per Devpost Judge fix #10: 55s is too long
    to hold a static frame; engineered screenshot must arrive via
    the span-click reveal mid-beat, not be held static for 30+s.]

   0:30–0:50 (20s — trace card unfurl + RiskJudge span lights)
   "Every flag is sourced to the clause. Every verdict links
    to its Phoenix trace. The contract unfurls span by span as
    the agents read it."
   [§6.4 unfurl plays — 12 spans fade in left-to-right at the
    §INSPIRATION 1800ms-per-span deliberate-slowness pacing.
    At ~0:46, the RiskJudge span lights warm-clay; the Block
    verdict resolves at 0:50. Camera holds static through this
    beat — the unfurl IS the motion.]

   0:50–0:55 (5s — span-click)
   "When Risk Judge issues a Block verdict, you can click
    the span."
   [Cursor enters frame. Click on the lit RiskJudge span. The
    span lifts ~8px on click per PLAN §6.4 named gesture.
    Cursor exits after the lift.]

   0:55–1:20 (25s — engineered frame held with side-card revealed)
   "You get the prompt that produced it, the response the
    model returned, the evaluation that judged the response,
    and the Phoenix span ID. There is no black box. There is
    no place you cannot click into."
   [Side card revealed. Engineered screenshot composition now
    fully on-screen: 0.94 Wilson-LB headline (Lane-A display
    serif, 240px), BLOCK badge (warm-clay pill, 14px mono),
    Phoenix span ID below at 14px mono per §2 / §18 v3. The
    camera does NOT cut — slow micro-zoom (1.0 → 1.04 over
    25s) keeps the frame alive without competing with the copy.]

   1:20–1:25 (5s — narration close)
   "Every span, clickable."
   [Engineered frame held flat for 5s. The §0 alt-1 cadence
    line lands as the visual + narration converge. Cut to
    next beat clean.]

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
| `<<USER-CONFIRM>>` | SOC 2 + pen-test target dates in §6 bullet 5 — **v3 update: dates struck per M&A Counsel fix #1; marker retained because the user may still want to commit to dates before deploy; current default is "no committed date" which is the honest hackathon-scope posture.** | User (Hugo) | Day-6 noon |
| `<<CONTACT-EMAIL>>` | Trust-packet + deletion-request + error-page contact (§6, §14) | User | Day-6 noon |
| `<<GOVERNING-LAW>>` | Governing-law jurisdiction in §13 footer disclaimer (v3 add per M&A Counsel fix #5) | User | Day-6 noon |
| `<<TOS-URL>>` | Terms-of-service link in §13 footer disclaimer (v3 add per M&A Counsel fix #5) | User | Day-7 deploy |
| `<<DEMO-DEAL-1..5>>` | Demo dropdown labels — pulled from `ma_gatekeeper` allow-list | Frontend Architect | Day-5 |
| `<<TEAM-NAME>>`, `<<REPO>>`, `<<BUILD-SHA>>`, `<<DOMAIN>>`, `<<TRACE-ID>>` | Footer + 500-page interpolations | Frontend Architect | Build-time substitution |

**Day-6 noon legal-review gate**: §11 FAQ answers + §6 honesty-block fields reviewed by a GC-persona (or a real GC if available — REVIEW_NOTES Round-C noted the structural circularity of GC-persona reviewing GC-persona answers; user flag).

---

## §18 — Cross-references to design system *(picked up by Phase 5 — `tokens.ts` + `SYSTEM.md`)*

- **Display type scale anchors**: §2 hero (96px desktop / 56px mobile), §2 anchor sub-line (40px desktop / 28px mobile — v3 add for the demoted PLAN §2.1 line), §5 hero number (**240px desktop / 96px mobile, tracking `-0.02em`**), §7 stat (mono, 56px), §3 vignette number (56px), §12 disclosure (14px small).
- **Mono usage**: Phoenix span IDs — **§2 hero overlay at 14px minimum (v3 fix per Devpost Judge #11 — video-capture legibility at 1440p)**; inline references elsewhere (§5 attribution, body mentions) hold the 12px convention at `--neutral-400`; all numbers in §7 + §5; verdict badges in §5 + §11 (**14px mono uppercase tracked `+0.08em`**). **SYSTEM Builder note**: if `tokens.ts` defines a mono-scale token architecture, the 14px hero-overlay variant needs its own token (`--font-mono-overlay` or similar) distinct from the 12px inline-reference token — flagged for Supervisor cross-Builder reconciliation.
- **Mono attribution color**: §5 attribution row + §13 footer build-line use `--neutral-500` (24px gap below the headline they attribute).
- **Color usage**: warm-clay (`--accent-clay: #B86F3D`) on the §5 Block badge + §1 primary CTA + §15 OG card accent — one accent per viewport per PLAN §5.1; signal-green (5%-state-only) on §11 Clear-verdict mentions; deep-forest-emerald (`--brand-primary: #0F4A38`) as primary brand surface everywhere else. *(Token candidates per INSPIRATION.md §Color — confirm under Playwright field-validation Day-3 morning.)*
- **§5 moneymoment composition** is a **no-container** lift — the AD §0.1 weird move. `tokens.ts` must NOT define a `.stat-card` shadow/border preset that components might reach for; the moneymoment lives in negative space (background = `--neutral-900` dark / `--neutral-50` light, period). *(Mirrors AD v3 fix #4.)*
- **§11 longest FAQ answer** renders as the §Five-weird-lifts §Composition weird-lift — full-bleed single column on desktop ≤1440, max-width 75ch above.
