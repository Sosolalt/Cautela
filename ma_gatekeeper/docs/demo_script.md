# Demo Script — Cautela

**Devpost submission video. Record-from teleprompter, grounded in the ACTUAL
current frontend + backend (2026-06-11), after the Phase-19 UI polish.** Full
rewrite — prior revs described the pre-Phase-19 UI (right-pane Phoenix *iframe*,
"Run Reflector now" button, 5-col portfolio). Those surfaces no longer exist;
everything below is reconciled against the real components.

**Length: this cut runs ~4:00 of content at 150 wpm + on-screen action.** It's the
"full-depth" version — Hugo records it, then trims live if it runs long (the most-
cuttable beats are flagged ⤵ in the operator notes). **Narrate to the events, not
the clock** — durations are estimates, not a metronome.

Supersedes [`../../plan.md`](../../plan.md) §8 for recording.

---

## What actually exists now (the only things we can film in-app)

Reconciled against the live components on 2026-06-11:

- **Hero `/`** — WebGL "dossier" landing ([`../frontend/components/hero/hero.tsx`](../frontend/components/hero/hero.tsx)).
  - Headline (3 lines): **"Every flag, sourced. Every verdict, traced."**
  - Subhead: *"M&A contract review where every verdict links to its Phoenix
    trace — and every flag is sourced to the clause it came from."*
  - Live anchor card: **"Phoenix trace · Verdict"** · *"Clause 1.4(b) · Adverse
    effect · Cluster-bootstrap LB · 0.91"*.
  - CTAs: **"Try the demo" → `/review`** (use this). *"Watch it work"* is **inert**
    (`DEMO_VIDEO_URL = null`) — don't click it on camera.
  - Animation: a ~14s WebGL loop — a 25-page paper stack flips, verdicts land on
    pages with red overlays, a hairline "trace" connects a flagged clause to a
    Phoenix span id. Let it run under the thesis/origin VO.

- **`/review`** — three panes:
  **PDF/HTML exhibit (LEFT, wide) · Findings list (CENTER) · Phoenix Verdict card (RIGHT)**.
  - Header: wordmark **"Cautela"** (a link → hero), nav `Review / Portfolio →`,
    and the **"Pre-indexed deal"** dropdown. Options render as `name (filing)`,
    e.g. *"Microsoft / Activision Blizzard (2023) (8-K/Ex 2.1)"*.
  - Pick a deal → review **auto-starts** (no run button). Empty state shows a
    pulsing vermillion dot + **"Analyzing the deal"** (first finding ~30–60s).
  - Findings **STREAM in** (SSE) into one list. Each row: a **lane chip**
    (Auto-clear / Escalate / Block), the `tag`, a 2-line explanation,
    `judge=0.xx · τ=0.xx`, and a **citation row** — the cite + a `STATUTE / CASE
    LAW` kind badge + a champagne **jurisdiction** chip + a one-line rationale +
    *"verified against `<source>` · `<date>`"* + a ↗ glyph. **This citation row
    is the on-screen proof for the law point in the Block beat.**
  - **Click a finding** → **all three panes snap on the same frame**: LEFT
    exhibit **scrolls + highlights the cited clause** (vermillion band; HTML
    highlighter — the common case; true-PDF gets a bbox overlay); CENTER row gets
    a 4px vermillion left-bar; RIGHT **Verdict card** fills.
  - **RIGHT pane = the Verdict card** ([`../frontend/components/trace-pane.tsx`](../frontend/components/trace-pane.tsx)),
    NOT an embedded Phoenix SPA: **Status pill** (root span) · **Latency** ·
    **Spans** · a **"This finding"** block · an **"In plain English"** explainer ·
    the **lane meaning** (*"Flagged for a human to review — a 'look here' signal,
    not an error."*) · a **Span breakdown** · and a vermillion **"Open full trace
    in Phoenix"** CTA → new tab. **We click this CTA at the audit peak.**
  - Bottom of the findings pane: a boxed **"Self-improvement · Phoenix"** panel
    with a **"Self-improve now"** button.

- **Reflector log** (climax surface) — streams in order: `LoopAgent spawned` →
  `Phoenix MCP list_traces — N traces` → `candidate prompt generated` →
  `Phoenix Experiment complete — CI lower = 0.xxx` → `frozen-fold non-regression
  check — Δ=0.xxx (ε=0.xxx)` → `iteration complete` → **`AUTO-PROMOTED`**
  (champagne-deep badge) + PR link. (Fallback terminal row: `NO PROMOTION`.)

- **`/portfolio`** ([`../frontend/components/portfolio-pane.tsx`](../frontend/components/portfolio-pane.tsx)) —
  header *"Portfolio Analyst · One Gemini 3 Pro call reads all 30 contracts at
  once — grouped by how each deal's 'walk-away' clause is written"*.
  - LEFT: a **6-col / 30-tile grid** — loads pulsing grey, resolves to **22 grey
    "standard"** tiles, **3 colored clusters**, and the lone **`akorn-fresenius`
    outlier** spanning 2 cols, ringed + pulsing vermillion, stamped **"⚠ Outlier"**.
  - RIGHT: **"What this shows"** primer, **"4 patterns across 30 deals · 1 deal
    fits no pattern"**, per-cluster name/n/theme, and a vermillion **"Review this
    one first"** block (the `akorn-fresenius` rationale: *"close to the exact
    wording a court used to let a buyer cancel the real Akorn / Fresenius merger."*).
  - Deterministic fixture ([`../tests/fixtures/portfolio_expected_output.json`](../tests/fixtures/portfolio_expected_output.json));
    live Vertex path is opt-in (`PORTFOLIO_LIVE=1`).

### What does NOT exist (so it's an EDIT asset, or it's cut)

- ❌ a right-pane Phoenix *iframe* → the **in-app Verdict card** + a new-tab CTA
  (clicked at the audit peak to show the real trace tree + scores).
- ❌ "Run Reflector now" → **"Self-improve now"** in a boxed panel.
- ❌ a 5-col portfolio → **6-col, 30 tiles**, outlier spans 2 cols.
- ❌ any on-screen `$69B` / `$6.4B` / `800k-token` counter → **spoken VO only**.
- ❌ an in-app architecture diagram → folded into the DEAL-PICK VO (no slide).
- ❌ **The user-facing legal citations are NOT model output** — they come from a
  deterministic, hand-curated, primary-source-verified map (see the law backbone
  below). The model flags the clause; it never invents the citation. ("We trained
  the agents against the gold set" is fine to say — see the operator note on what
  "trained" means here — but never "the model cites the law".)

---

## The law backbone (say it accurately — this is a credibility anchor)

The Block beat leans on this, so get it right. The citations a user sees are
**deterministic**, from [`../data/citation_map.json`](../data/citation_map.json)
via [`../agent/citation_linker.py`](../agent/citation_linker.py):

- **A hand-curated, primary-source-verified map of 15 controlling authorities**
  (11 statutes + 4 cases) across 6 clause tags. Real entries include: **8 Del. C.
  § 251 / § 271** (Delaware merger statutes), **15 U.S.C. § 18a / § 18** (HSR /
  Clayton antitrust), **U.C.C. § 9-406 / § 2-210** (anti-assignment), **35 U.S.C.
  § 261** (IP assignment), and the case law — **Akorn v. Fresenius** + **AB Stable
  v. MAPS** (MAC), **Revlon** (exclusivity), **In re Trados** (change-of-control).
- **The model never generates the citation.** `lookup_citation(tag, jurisdiction)`
  is a synchronous deterministic lookup; it **fails closed** (returns "authority
  not resolved") rather than serve the wrong jurisdiction's law. A separate
  internal LLM proposer is compared to the map and logged to Phoenix as eval data
  only — it never reaches the user.
- **So the honest pitch is the inverse of "we fed the model a law dataset":** the
  law is pinned to primary sources and *can't be hallucinated*, because it isn't
  generated. That's the line.
- **Clause→authority you'll actually see:** a **change-of-control** block cites
  **Delaware merger statutes / In re Trados**; **Akorn v. Fresenius** is the **MAC**
  case (it shows on a MAC finding + is the portfolio outlier). Name the
  clause-correct authority on camera.

---

## Deliverable 1 — Beat table (12 beats, ~4:00, self-paced)

`[IN-APP]` films the running site; `[EDIT]` is a built asset. Durations are
estimates (VO @150 wpm + action). ★ = load-bearing.

| ~Start | Beat | Surface | On screen / what to do |
|---|---|---|---|
| **0:00** (~10s) | Cold open — stakes (real M&A deal) | `[EDIT]` title card | Black; **voice from t=0.** BMS / Celgene (2019); one missed deadline cost $6.4B. Stakes only — no claim Cautela catches this. |
| **0:10** (~22s) | Thesis — triage / preprocess | `[IN-APP] /` hero | Hero loop + headline. Cautela = the **first-pass / double-check layer** that lets human reviewers spend time only where it matters. Lanes + sourced + traced. |
| **0:32** (~19s) | **ORIGIN — why it's real** | `[IN-APP] /` hero | Personal, to camera: **two M&A friends** who read contracts all day pushed Hugo to build it; the hours are what they want back. Makes it concrete + real. *(They're also the gold-set annotators — Q&A.)* |
| **0:51** (~28s) | Deal pick **+ architecture** | `[IN-APP] /review` | Click **"Try the demo"** → open **"Pre-indexed deal"** (5 visible). Two-word gloss on *pre-indexed*, then the **4-agent ADK pipeline** (parser → 6-way classifier fan-out → cross-reference → risk judge) for the technical jury. Pick **Microsoft / Activision Blizzard (2023)**. |
| **1:20** (~21s) | Live run — findings stream | `[IN-APP] /review` | "Analyzing the deal" → rows stream into the CENTER list. Narrate the **triage framing** (escalate ≠ error); let the **Block** row land. |
| **1:41** (~30s) | **BLOCK FINDING + credibility + law ★** | `[IN-APP] /review` | Cursor on the red **Block** chip (change-of-control) + its **citation row**. Value **spoken** ($69B). Land the law backbone (**citations pinned to a curated, primary-source-verified map**) + the training story (**we trained the agents against a gold set hand-validated by two M&A experts**). Then: *supposed to be there; triage, not gotcha.* |
| **2:11** (~32s) | **AUDIT PEAK ★** | `[IN-APP] /review → Phoenix` | **Click the Block row** → 3 panes snap. Then **click "Open full trace in Phoenix"** → new tab: **pan the full span tree** (parser → classifiers → cross-ref → risk-judge), **then zoom the 3 evaluator annotations** (hallucination · faithfulness · routing-gate). "Recorded, not asserted." |
| **2:43** (~19s) | **WHY THIS EXISTS ★** (differentiator) | `[IN-APP]` (rest on the Phoenix trace / cut back to `/review`) | Harvey / Kira / Luminance read contracts too — what they don't ship is an honest answer to **"how do you know?"** Ours does, because it's **built on Arize** — every verdict traces back to its evidence. |
| **3:03** (~14s) | **PORTFOLIO ★** | `[IN-APP] /portfolio` | Click **"Portfolio →"**. The whole data room in one view — **every contract sorted by priority**; the vermillion **outlier pops to the top = open it first.** Let the visual carry it; one short line. |
| **3:17** (~21s) | **LOOP PREMISE** | `[IN-APP] /review` Reflector | Scroll to **"Self-improvement · Phoenix"**; click **"Self-improve now"**. **Disclosure badge fires on the click.** Narrate the premise as the log streams. |
| **3:38** (~16s) | **PAYOFF ★ (climax)** | `[IN-APP]` Reflector log | Log reaches **`AUTO-PROMOTED`** (champagne badge). Land it; hold ~3s. *(Optional receipt: external Phoenix → Experiments.)* |
| **3:54** (~6s) | Close | `[EDIT]` card | Cautela wordmark + one-line thesis + GitHub / hosted-demo / Phoenix URLs. Held silent. |

**~4:00 total.** Trim further toward 3:00 (if needed) via the operator-note cuts.

---

## Deliverable 2 — Teleprompter (SAY + DO interleaved) — the record-from surface

Read the **bold** lines aloud (~150 wpm). `▸ DO` / `▸ SHOW` cues sit at the exact
point in the read. VO word counts are Python-counted; re-run `len(text.split())`
on any edit.

---

**[COLD OPEN]** `[EDIT]` title card.
`▸ SHOW:` black title card; lines land one at a time. Voice from t=0.

> **"In 2019, Bristol-Myers Squibb acquired Celgene."**  *(hold ~1s)*
> **"One deadline, buried in that merger agreement, slipped and made them loose six point four billion dollars."**

`▸ DO:` hard cut to the **hero `/`**. *(22 words. The real, sourced BMS/Celgene CVR forfeiture — the Liso-cel milestone missed by 36 days. Stakes only; no claim Cautela catches this. Accuracy note: the merger itself closed — it was the CVR payout that was forfeited — so "a deadline slipped and $6.4B vanished" is true; don't say "the merger collapsed".)*

---

**[THESIS]** `[IN-APP] /`
`▸ SHOW:` the WebGL hero loop + headline *"Every flag, sourced. Every verdict, traced."*

> **"Reading a merger agreement end-to-end takes a team of lawyers weeks. Cautela does the first pass — it reads every clause and sorts each one between clear, escalate, or block. The reviewers then spend their hours only where it matters, and every flag stays sourced to its clause and traced in Phoenix."**

*(51 words. A preprocessing / double-check layer that focuses human attention — NOT a replacement for lawyers.)*

---

**[DEAL PICK + ARCHITECTURE]** `[IN-APP] /review`
`▸ DO:` click **"Try the demo"** → `/review`. Open the **"Pre-indexed deal"** dropdown — 5 options render as `name (filing)`.

> **"These are five pre-indexed deals — real merger filings, already fetched and parsed. Behind each one, four agents on Google's ADK: a parser splits the contract into clauses, six classifiers fan out in parallel to flag the risky ones, a cross-reference agent resolves the definitions, and a risk judge scores each finding — every call on Gemini 3.5 Flash, traced in Arize Phoenix."**

`▸ DO:` select **Microsoft / Activision Blizzard (2023)** → review auto-starts. *(63 words. "Pre-indexed" = already fetched + parsed. Pipeline detail for the technical jury — the real backbone. This click is the boundary; everything after depends on the live parse.)*

---

**[LIVE RUN]** `[IN-APP] /review`
`▸ SHOW:` findings **streaming into the CENTER list**; rows carry a lane chip + `judge=… · τ=…` + a citation row.

> **"Auto-clear for the boilerplate. Escalate when a human should take a look — that's not an error, it's a 'look here'. And block for a hard stop."**

`▸ DO:` hold, let the list fill; wait for the **Block** row. *(38 words)*


---

**[AUDIT PEAK ★ — keep moving]** `[IN-APP] /review → Phoenix`
`▸ DO:` **click the Block row.** All three panes snap on the same frame.
`▸ SHOW:` LEFT — the exhibit **scrolls + draws a vermillion band on the cited clause**. RIGHT — the **Verdict card** ("In plain English" + the lane-meaning line).

> **"One click, and all three panes line up. Left: the exact clause, highlighted in the real filing. Right: the verdict in plain English."**

---

**[BLOCK FINDING + CREDIBILITY + LAW ★]** `[IN-APP] /review`
`▸ SHOW:` cursor on the red **Block** chip row (change-of-control), then along its **citation row** (the `STATUTE / CASE LAW` badge, the Delaware jurisdiction chip, "verified against …").

> **"So when you click on a flagged clause, the cause is not guessed. Their is law underneath: every citation is pinned to a curated, primary-source-verified map of controlling authority — Delaware statutes and the real case law. We trained the agents against a gold set of real deals. So this isn't second-guessing elite counsel — it's first-pass triage in seconds, with the law attached."**

*(72 words. THIS is where the law backbone + the training story land. Accuracy: name **Delaware merger statutes / In re Trados** for a change-of-control block — **Akorn v. Fresenius is the MAC case**, so only say "Akorn" if the visible finding is MAC. The "two M&A experts" are the ORIGIN friends = the gold-set annotators. Spoken $69B; no on-screen counter — other deal → operator table. This is the credibility beat; see the ⭐ appendix.)*

---

`▸ DO:` click the RIGHT-pane **"Open full trace in Phoenix"** CTA → real trace in a **new tab**.
`▸ SHOW:` **first pan the full span tree** top-to-bottom — parser, the six classifiers, cross-reference, risk-judge — **then zoom into the risk-judge span's three evaluator annotations** (hallucination · clause-faithfulness · risk-judge gate).

> **"Now I open the full trace in Phoenix — the whole pipeline: parser, the six classifiers, cross-reference, risk judge. And down here, the three evaluators that scored it: hallucination, faithfulness, and the routing gate. Every number behind the verdict is recorded, not asserted."**

*(66 words. WHY: the span tree proves the pipeline actually ran + every call is traced; the evaluator annotations prove the verdict is grounded — the exact scores that drove clear/escalate/block are recorded, so a reviewer can audit instead of trust. The Arize money shot. **If Phoenix is cold/unset, skip the new-tab click — the Verdict card carries the proof; see fallbacks.**)*

---

**[WHY THIS EXISTS ★]** `[IN-APP]` rest on the Phoenix trace, or cut back to `/review`.
`▸ SHOW:` linger a beat on the trace you just opened as you say "how do you know?", then the cursor back on the findings.

> **"Vertical legal-AI tools already exist — Harvey, Kira, Luminance. What they don't ship is an honest answer to one question: how do you know? Ours does — because we built it on Arize. Every verdict you just saw traces back to its evidence."**

*(43 words. The differentiator, straight from the README. It foregrounds Arize for the partner track and pays off the audit you just showed.)*

---

**[PORTFOLIO ★]** `[IN-APP] /portfolio`
`▸ DO:` click **"Portfolio →"** in the header nav.
`▸ SHOW:` the grid loads **pulsing grey**, then **resolves**; the **outlier pulses vermillion** (spans 2 cols, "⚠ Outlier"). Cursor to the right **"Review this one first"** block as you say the last line.

> **"And this is the whole data room in one view — every contract in the deal, sorted by priority, so the team knows exactly which ones to open first."**

*(29 words. The vermillion outlier pulsing top-of-grid IS "open first" — let the visual carry it. Optional add if you want the scale/Gemini point: "One Gemini call across all of them at once.")*

---

**[LOOP PREMISE]** `[IN-APP] /review` Reflector
`▸ DO:` back on `/review`, scroll to the **"Self-improvement · Phoenix"** panel and click **"Self-improve now"**. **Disclosure badge fires on this click.**
`▸ SHOW:` the **event log streams** — narrate as rows appear: `LoopAgent spawned` → `Phoenix MCP list_traces` → `candidate prompt generated` → `Phoenix Experiment complete — CI lower = …` → `frozen-fold non-regression check — Δ=… (ε=…)`.

> **"This is the self-improvement loop. Through Phoenix's MCP server, the Reflector reads its own escalation traces, grows them into a regression dataset, and drafts a candidate cross-reference prompt. A Phoenix Experiment scores it against the live prompt — and it only ships if the gain clears two statistical gates it can't fake: a bootstrap confidence lower-bound above zero, and non-regression on a held-out fold."**

*(48 words)*

---

**[PAYOFF ★ climax]** `[IN-APP]` Reflector log
`▸ SHOW:` the log reaches the **`AUTO-PROMOTED`** champagne badge. Hold ~3s. Land the last word on the stamp.

> **"List the traces, draft a candidate, run the experiment, clear the frozen fold — auto-promoted. The system improved its own prompt, and Phoenix is the gate that proved it earned the ship."**

`▸ DO (optional receipt):` cut to **external Phoenix → Experiments** (candidate-vs-production). *(32 words. Assume populated.)*

---

**[CLOSE]** `[EDIT]` card
`▸ SHOW:` **Cautela wordmark + one-line thesis + GitHub / hosted-demo / Phoenix URLs.**

> *(silent — hold ~6s)*

---

**Locked phrases honored:** "five pre-indexed deals" (plan §5.5) spoken at the
dropdown open while 5 options show. The two gates (paired-bootstrap CI +
frozen-fold) are **named** in LOOP PREMISE and **shown live** in the log.

**Banned (PROJECT_LOG "What failed"):** no "100% precision/recall"; no "we caught
what the lawyers missed"; no "the model cites the law" (the citation map is
deterministic); no market/failure-rate stat; no "recently indexed"; no on-screen
"$6.4B at risk" counter implying Cautela catches the Celgene loss; no unsourced
$/%-figure. $69B is the real reported Microsoft/Activision value — spoken only.

---

## Deliverable 3 — Disclosure badge spec

Fires **the instant Hugo clicks "Self-improve now"** (LOOP PREMISE) — framing the
coda instead of competing with the payoff. 6.0s hold, out before AUTO-PROMOTED.

```
Pre-seeded prompt — full disclosure in description
```

`len(badge.split()) → 7`. Lower-third, centered. `fontFamily.body` 500 /
`fontSize.small` 14px; `colors.neutral-50` on `colors.neutral-900` @ 0.92 scrim;
fade `durationComponent` 400ms / `easePrimary`. Long-form lives in the YouTube +
Devpost descriptions ([`devpost.md`](devpost.md) "Reflector pre-seeding disclosure").

---

## Fallbacks (real-UI failure modes)

| Trigger | Mitigation | What plays instead |
|---|---|---|
| Live SSE latency / EdgarTools raises / Vertex 429 during LIVE RUN | Pre-record one known-good Microsoft/Activision `/review` run; the AUDIT-PEAK click is deterministic against the captured stream. | Captured `/review` walkthrough; live VO continues uncut. |
| **Phoenix cold-start / `NEXT_PUBLIC_PHOENIX_URL` unset at the AUDIT PEAK** | The Verdict card degrades gracefully — Status/Latency/Spans show "—" but **"In plain English" + the citation row still render**. **Skip the new-tab Phoenix click**; trim the second half of the audit VO. *(Best: pre-warm Phoenix `min-instances=1` + capture the trace tab once at rehearsal.)* | Verdict card only, or a captured Phoenix-trace still. |
| HTML highlighter doesn't land the band (legacy EDGAR markup) | If it misses, the proof is the **citation row + Verdict card** (highlight-independent). Say "the clause it came from", not "highlighted". | Citation row + Verdict card only. |
| Citation row shows "authority not resolved" / "contract-anchored" on the chosen finding | Pick a finding whose tag is in the **6 map-covered tags** (change_of_control, anti_assignment, ip_assignment, mac, exclusivity, non_compete) at rehearsal — those carry the cite the **Block-beat law point** needs. | A finding with a populated CitationRef. |
| Portfolio live path errors / not wired | `/portfolio` serves the **mock fixture** by default (deterministic — 4 clusters + the Akorn outlier). VO claims capability, not live-ness. | Mock-backed grid. |
| Reflector ends in **NO PROMOTION** at recording | Prompt is pre-seeded weak to promote; if it still fails, cut the payoff to a rehearsal capture pre-verified to reach **AUTO-PROMOTED** ("captured during rehearsal" ribbon). Badge still plays on the click. | Rehearsal capture of the AUTO-PROMOTED log. |

---

## Recording-day operator notes (for Hugo)

- **Length:** this is the ~4:20 full-depth cut. To reach ≤3:00, trim in this
  order: (1) drop the optional Phoenix **new-tab click**, keep the Verdict card
  (−~10s); (2) tighten the **architecture** VO to the parser + parallel-classifier
  line only (−~8s); (3) shorten the **Live-run** hold (−~6s); (4) tighten the
  **Portfolio** to the data-room scenario + the pop-out, drop the token line
  (−~8s). That recovers ~30s without losing a ★ beat.
- **Law accuracy:** the on-screen citation for a **change-of-control** block is a
  **Delaware merger statute (§ 251 / § 271) or In re Trados** — **Akorn v.
  Fresenius is the MAC case** (it's the portfolio outlier). Name the
  clause-correct authority. Confirm the loaded Block's citation row at rehearsal.
- **What "trained" means here (for a Q&A follow-up):** saying *"we trained the
  agents against a gold set"* on camera is fine — but technically it's **calibration
  + the Reflector loop**, not gradient fine-tuning: the judge thresholds (τ_h/τ_f)
  were tuned by cross-validation against the ~530-finding lawyer+analyst gold set,
  and the nightly Reflector loop improves the prompts from failure traces. If a
  judge drills in, give that accurate version. (Separately: the **citations** are a
  deterministic primary-source map — never model output.)
- **ORIGIN beat:** deliver to camera; optional lower-third with the two friends'
  names/roles (with consent). It's the same two people who validated the gold set.
- **Set `NEXT_PUBLIC_PHOENIX_URL` + `NEXT_PUBLIC_PHOENIX_PROJECT`** and confirm the
  Phoenix project is populated (trace tree + the three span annotations) before
  the AUDIT PEAK take — needed for the tree+scores reveal.
- **AUDIT PEAK choreography:** click finding → 3 panes snap → click "Open full
  trace in Phoenix" → in the new tab, **pan the span tree first, THEN zoom the
  risk-judge evaluator annotations**. Rehearse the tab-switch warm.
- **Two EDIT assets to build:** the cold-open title card and the close card. **No
  architecture slide, no results-table capture** (both cut).
- **Per-deal value table** (BLOCK is spoken): Microsoft/Activision ≈ **$69B**
  (default) · Exxon/Pioneer ≈ **$60B** · Pfizer/Seagen ≈ **$43B** · Cisco/Splunk ≈
  **$28B** · HPE/Juniper ≈ **$14B**.
- **The Reflector log is the climax — narrate to the events, not the clock.**
- **Word counts are Python-counted.** Re-run `len(text.split())` on any edit.

---

<!-- =====================================================================
     ⭐⭐⭐  USE THIS DURING THE DEMO / Q&A  ⭐⭐⭐
     THE REAL GOAL OF THE PROJECT — CREDIBILITY FRAMING
     Woven into LIVE-RUN + BLOCK + AUDIT + WHY-THIS-EXISTS, and carried
     visually by the UI ("In plain English" + lane-meaning Verdict block,
     the case-law citation row, the portfolio Akorn outlier). Verbatim for Q&A.
     ===================================================================== -->

## ⭐ THE REAL GOAL — credibility framing (say this; the example is load-bearing)

**The trap to avoid:** never claim Cautela "found problems the lawyers missed."
That's false. The Microsoft–Activision agreement was drafted by elite counsel; the
clauses we flag are *supposed to be there*.

**The truthful, stronger framing — Cautela is a TRIAGE / SCREENING layer, not a
gotcha detector:**

- **"Escalate" ≠ "error."** It means *"a human should look at this."* Auto-clear =
  standard/low-risk · Escalate = flagged for attention · Block = hard-stop pending
  review. Flagging change-of-control or MAC is *correct triage* — what a first-year
  associate's first pass produces, in seconds instead of hours, **with the
  controlling law attached.** *(The Verdict card states this on screen.)*

- **The clauses it surfaced are real, material, heavily-negotiated terms, grounded
  in primary law:** the **$2,270,100,000 termination fee** + no-solicitation /
  fiduciary-out structure; the **MAC walk-away with its COVID/pandemic carve-outs**,
  cited to **Akorn v. Fresenius** — the *one* Delaware case where a MAC justified
  killing a merger; **single-trigger vesting** (Section 2.8).

- **The citations can't be hallucinated** because they're **not generated** — they
  come from a hand-curated, primary-source-verified map (15 authorities; statutes +
  the real cases). The model flags the clause; the law is pinned. *(This is the
  Block-beat point and the answer to a "did the model make up that case?" follow-up.)*

- **For THIS deal the MAC flag is genuinely on-point:** Microsoft–Activision sat in
  regulatory limbo ~18 months (FTC/CMA/EU); whether a MAC had occurred was a live,
  real-world question. The model surfaced the clause that mattered most.

- **The portfolio makes the same point at scale:** the `akorn-fresenius` outlier is
  flagged because its walk-away clause is *"close to the exact wording a court used
  to cancel the real Akorn / Fresenius merger."* The screening layer pointing at the
  one exposed contract in thirty — exactly the data-room scenario in the VO.

- **The origin is real, and it's the same two people:** the two M&A friends in the
  ORIGIN beat — a lawyer and an analyst — are the **annotators of record** for the
  human-validated Internal-30 gold set the judges were calibrated against. The
  people who inspired the project are the people who graded it.

**THE LINE TO SAY ON CAMERA (or under questioning):**
> *"Cautela isn't second-guessing the lawyers. It does first-pass triage in
> seconds and grounds every flag in controlling Delaware law — pinned to the
> primary source, not generated. On a $69 billion deal, this is the screening
> layer that tells a reviewer where to look and why it matters legally."*

<!-- END credibility framing -->

---

## Cross-references (audit trail)

- Real components: [`../frontend/app/review/page.tsx`](../frontend/app/review/page.tsx) · [`../frontend/components/findings-pane.tsx`](../frontend/components/findings-pane.tsx) · [`../frontend/components/trace-pane.tsx`](../frontend/components/trace-pane.tsx) · [`../frontend/components/pdf-pane.tsx`](../frontend/components/pdf-pane.tsx) · [`../frontend/components/reflector-loop-button.tsx`](../frontend/components/reflector-loop-button.tsx) · [`../frontend/components/portfolio-pane.tsx`](../frontend/components/portfolio-pane.tsx) · [`../frontend/components/deal-picker.tsx`](../frontend/components/deal-picker.tsx) · [`../frontend/components/hero/hero.tsx`](../frontend/components/hero/hero.tsx).
- Portfolio fixture (what `/portfolio` films): [`../tests/fixtures/portfolio_expected_output.json`](../tests/fixtures/portfolio_expected_output.json).
- **Law backbone:** [`../agent/citation_linker.py`](../agent/citation_linker.py) + [`../data/citation_map.json`](../data/citation_map.json) — 15 controlling authorities (11 statutes + 4 cases) across 6 tags; **deterministic, primary-source-verified, never model output**; fails closed on wrong jurisdiction. Design: `design/STATUTE_LAYER.md`.
- Backend routes: `agent/server.py` `/allow-list`, `/review-by-deal` (SSE), `/reflect/loop` (SSE), `/portfolio`, `/filing/{deal_id}`. Reflector events: [`../agent/reflector.py`](../agent/reflector.py).
- 5 deals: [`../agent/allow_list.py`](../agent/allow_list.py). Topology + models: [`../agent/agents.py`](../agent/agents.py) (review on `GEMINI_FLASH_MODEL` = gemini-3.5-flash; Portfolio on `GEMINI_MODEL` = gemini-3.1-pro-preview).
- Origin/calibration: the two M&A friends (lawyer + analyst) are the Internal-30 gold annotators of record (~530 findings) — README §9.
- "Why this exists" differentiator: root [`../../README.md`](../../README.md) §"Why this exists" — *"Vertical legal-AI tools already exist (Harvey, Kira, Luminance). What they don't ship is an honest answer to the question, 'how do you know?'"* (the VO is verbatim from this).
- Cold-open stakes + Skadden citation: [`internal30_deal_bank.md`](internal30_deal_bank.md) §2 (BMS/Celgene CVR — Liso-cel milestone, $6.4B).
- Disclosure wordings: [`devpost.md`](devpost.md).
</content>
