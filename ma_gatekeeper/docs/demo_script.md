# Demo Script — M&A Due Diligence Gatekeeper

3-minute Devpost submission video. Synthesized E9 storytelling artifact
(deferred from Phase 5; built through `feature-build-loop` 2026-05-27).
Supersedes [`../../plan.md`](../../plan.md) §8 for recording purposes —
plan §8 stays as the design-time spec, this file is the recording-time
spec.

**Anchors** — every claim in this file traces to one of:
- [`../../plan.md`](../../plan.md) §3.2 (THE MOMENT), §5.5 (allow-list voiceover lock), §6.3 (promotion rule + ε), §6.4 (pre-seeding), §8 (current beat table), §12 (Devpost text-section budgets)
- [`devpost.md`](devpost.md) "Reflector pre-seeding disclosure" block (canonical wording)
- [`../../design/tokens.ts`](../../design/tokens.ts) (every cited typographic / motion / color token)
- [`../../PROJECT_LOG.md`](../../PROJECT_LOG.md) "Pre-commitments locked" + "What failed"

---

## Deliverable 1 — 30-second climactic voiceover script (verbatim)

Read at conversational pace (~150 wpm). Recorded by Hugo (French-fluent
English). One take. Plays over the Phoenix Experiments view at 2:30–3:00.
The recap of the deal-selection moment is intentional — it lets the
30-second block stand alone (e.g. as a Devpost teaser cut) while still
working as the in-context climax narration.

```
Five pre-indexed deals. I picked one. The agent flagged a
change-of-control clause.
Overnight, the Reflector read its failure traces and proposed a
candidate prompt.

Auto-promotion fires only when the paired-bootstrap CI lower bound
clears zero on the regression set, and the candidate does not
regress on the frozen fold within epsilon.

Disclosure: the production prompt was deliberately seeded weaker
48 hours before demo recording so the auto-improvement loop has a
real signal to find.
```

**Word count: 74 words** (verified via `len(voiceover.split()) → 74`,
treating the em-dash as its own whitespace-delimited token). At 150 wpm
conversational pace: 74 × 60 / 150 = **29.6 seconds**, inside the 30.0s
climax slot. An earlier draft included a "Cmd-click — the full Phoenix
trace opens." line at this position (81 words → 32.4s, over the slot);
that line was trimmed because the cmd+click moment is already shown
visually at 1:30–1:55 and does not need re-narration at the climax.
Word count lands at the lower edge of the 75–85 band — the trade-off is
explicit: tighter clock, fewer flavor words, all three locks below
preserved.

**Locked phrases honored** (verbatim or close-paraphrase, with sources):

| Lock | Source | Where in script |
|---|---|---|
| "five pre-indexed deals" | plan.md §5.5; PROJECT_LOG.md "Pre-commitments locked" | Sentence 1, verbatim. |
| Reflector pre-seed disclosure (21-word locked clause) | devpost.md "Reflector pre-seeding disclosure" L214–220 | Final paragraph, verbatim: "production prompt was deliberately seeded weaker 48 hours before demo recording so the auto-improvement loop has a real signal to find". |
| Paired-bootstrap CI + frozen fold + ε floor | plan.md §6.3; devpost.md "How we built it" | Middle paragraph, named without softening into "the loop got better". |

**Banned phrases verified absent** (per PROJECT_LOG.md "What failed"
and plan.md §1):

- No "100% precision" / no "100% recall" — only "Block-tier clause" and the procedural gate language.
- No "70–90% of deals fail" — no market-size or failure-rate stat.
- No "recently indexed" — uses the locked "pre-indexed" verbatim.
- No unsourced $-figure / %-figure.
- Does NOT paraphrase the §15 cadence tagline "Every flag, sourced. Every verdict, traced. Every span, clickable." (`design/COPY.md`) — that line is the landing-page OG anchor, not the voiceover.

---

## Deliverable 2 — On-screen pre-seed caption spec

The caption appears the instant the auto-promotion event chip lands in
the Phoenix prompt-history timeline. Its job is to convert §6.4
pre-seeding from "soft-deceptive staging" into "honest disclosure" —
the freeze-frame test is: *a Devpost rule-lawyer who pauses the video
on this frame must see the disclosure plainly and read both sentences
before un-pausing.*

**Caption text** (verbatim, two sentences):

```
The production prompt was deliberately seeded weaker 48 hours before
demo recording so the auto-improvement loop has a real signal to find.
The loop logic itself — paired-bootstrap CI, frozen-fold non-regression,
auto-promotion — is unchanged.
```

Word count: 35 words (Python `len(caption.split()) → 35`, em-dashes
counted as standalone tokens). At a 1.5×-speed reader's effective pace
(~1.67 wps), minimum readable hold is 35 / 1.67 = **20.96 seconds** —
the 22.0s on-screen hold below clears the floor with a ~1.04s fade-out
margin.

Note: canonical Sentence 3 of the Devpost pre-seeding disclosure block
("Honest engineering of reproducibility, not staging.") is intentionally
NOT carried into the caption — the 30s climax-window budget precludes a
third sentence. The long-form surface for that sentence is the Devpost
project description (`devpost.md` L220), linked from the YouTube
description.

**Spec table**:

| Property | Value | Source / token |
|---|---|---|
| Caption text | (the two sentences above, verbatim) | Sentence 1 ≈ devpost.md L216–218 with the double-quotes around `"production"` dropped for 14px legibility. Sentence 2 is the verbatim devpost.md L218–219 "loop logic itself … is unchanged" clause. Canonical Sentence 3 ("Honest engineering of reproducibility, not staging." — devpost.md L219–220) is dropped entirely for caption-budget reasons; its long-form surface is the Devpost project description. |
| Font family | `fontFamily.body` → Inter Variable | `design/tokens.ts` L149. Body register for prose disclosure; mono/overlay is reserved for span-IDs (L172–174). |
| Font weight | `500` (Inter Medium, inline axis value) | Reads as disclosure-with-conviction without crossing into bold. Not a separate token — Inter Variable's weight axis. |
| Font size | `fontSize.small` → 14px / line-height 1.5 / letter-spacing 0 | `design/tokens.ts` L175. 14px clears WCAG 1.4.4 resize-without-loss-of-function for 1440p video bake. |
| Color (text) | `colors.neutral-50` → `#F4F6F3` | `design/tokens.ts` L86. ≥17:1 contrast on neutral-900 — safe even with the scrim at 0.92 alpha. |
| Color (scrim) | `colors.neutral-900` → `#0B1311` at 0.92 alpha | `design/tokens.ts` L98. Lower-third strip behind the caption only, so the underlying Phoenix Experiments view stays visible above/below. |
| Position | Lower-third, horizontally centered. Bottom margin = `spacing.5` (24px); inner padding = `spacing.4` (16px). | `design/tokens.ts` L194–208. Lower-third anchor survives YouTube's progress-bar overlay on the lower 6%. |
| In-point | T = 2:30.000 (frame 4500 @ 30fps) | Fires the instant the Reflector `_LOG.info("PROMOTED candidate %s → tag=production on %s", ...)` line appears in the LEFT-pane terminal tail (and the `production` tag pill flips in the RIGHT-pane Phoenix prompts-list view simultaneously). |
| Out-point | T = 2:52.000 (frame 5160 @ 30fps) | 22.0s hold — clears the 20.96s 1.5×-speed readability floor for the 35-word caption with ~1.04s fade-out margin. Post-caption held shot runs 2:52 → 3:00 (8s, clears the ≥5s floor for the GitHub / hosted-demo / Phoenix URL card to register). |
| Fade-in duration | `durationComponent` → 400ms | `design/tokens.ts` L274. Not `durationMicro` (150ms — feels like a hover-tooltip and underweights the disclosure); not `durationHero` (800ms — would steal focus from the auto-promotion event); explicitly **not** `durationMoneymomentSpan` (1800ms — `@policy noreuse` per `tokens.ts` L298, reserved for §6.4 landing-page moneymoment unfurl + the §How-it-works pipeline pulse only). |
| Fade-out duration | `durationComponent` → 400ms | Symmetric with fade-in. |
| Easing | `easePrimary` → `cubic-bezier(0.16, 1, 0.3, 1)` | `design/tokens.ts` L266. The single locked easing per SYSTEM.md §Motion language §1. |
| Reduced-motion | Under `@media (prefers-reduced-motion: reduce)`: fades suppressed, caption appears instantly at in-point and disappears instantly at out-point. **Hold duration unchanged at 22s** — the readability floor is preserved. | SYSTEM.md §Motion language reduced-motion universal contract. Note: on a baked YouTube export this is a no-op; documented here for any future live-`<video>`-with-JS-overlay surface (e.g. a scroll-replay landing-page section). |

After Effects (or any future live overlay) implements the fade timing
from the spec table above; the canonical render target is the YouTube
bake.

**Honest-disclosure check** (per spec — freeze-frame survivability):

- Caption sits on a 92%-opacity scrim. Max-contrast neutral-50 text on near-black. Inter Medium 500 at 14px on a 1440p bake reads as clean disclosure prose, not a code/terminal block.
- 22s hold — above the 20.96s 1.5×-speed floor for 35 words. A passive native-pace viewer registers it inside ~3s.
- Wording names: (a) the seeding action, (b) the 48-hour window, (c) what the loop logic actually consists of (paired-bootstrap CI, frozen-fold non-regression, auto-promotion), (d) that the loop logic is unchanged. Each is the clause a literal-minded judge could otherwise infer the opposite of.

---

## Deliverable 3 — Restructured beat table

**Invariants preserved** (from plan.md §8):

- Total runtime ≤ 3:00.
- Ordering: problem → architecture → live demo → climax → close.
- Pre-recorded EDGAR fallback exists (separate row below).
- Cmd+click reveal present (now as setup beat, NOT climax).
- §5.5 voiceover lock ("five pre-indexed deals") fires at dropdown open and is recapped in the climax voiceover.
- Architecture beat compressed to 15s, per plan.md §8 v2/v3.

**Inversion (the spec's load-bearing change)** — current plan.md §8
has the cmd+click @ 1:50–2:05 as "THE MOMENT" with auto-promotion
trailing it as the loop reveal. This table inverts: cmd+click is the
**setup beat that establishes auditability**, and the auto-promotion
event is the **single climax** (final 30s, held).

| Time | Beat | What's on screen | Voiceover gist |
|---|---|---|---|
| **0:00–0:15** | Problem | Quote card from Potomac Law CoC piece (citation bottom-right, mono 14px); cut to a 312-page Exhibit 2.1 PDF scrolling fast. Source-on-screen: "Potomac Law — The Change-of-Control Problem Nobody Owns" (plan.md §1.1). | "M&A due diligence reads thousands of pages, and the deal-killer clause is the one nobody flags at signing." |
| **0:15–0:30** | Architecture | Static one-slide architecture diagram: Parser → Classifier → Cross-Reference → Risk Judge → Router; Reflector loop wired through Arize Phoenix MCP. Three callouts only: (1) Gemini 3 + ADK, (2) Phoenix tracing on every span, (3) MCP-driven self-improvement loop. | "Gatekeeper runs Gemini 3 on Google ADK, traced end-to-end in Arize Phoenix. A nightly Reflector loop reads its own traces back through Phoenix MCP." |
| **0:30–0:50** | Deal selection (live demo opens) | UI dropdown opens. Verbatim label visible on-screen: **"5 pre-indexed deals our agent has reviewed end-to-end"** (plan.md §5.5 L250 wording — locked, numeral form). 5 entries rendered with deal names from [`../agent/allow_list.py`](../agent/allow_list.py) (Microsoft/Activision, Pfizer/Seagen, Cisco/Splunk, ExxonMobil/Pioneer, HPE/Juniper). Hugo clicks one. | **"I pick one of five pre-indexed deals."** (§5.5 voiceover lock fires verbatim — spelled-out form per plan.md §5.5 L254 voiceover obligation — at dropdown open.) |
| **0:50–1:30** | Streaming findings via SSE | Findings populate left-to-right into three lanes (Auto-Clear / Escalate / Block). Each chip shows numeric judge score AND lane color (plan.md §9). Block-tier finding appears at ~1:20 with score badge visible. Header shows τ_h and τ_f thresholds. | "The agent surfaces a Block-tier finding — every flag carries the cited clause and the judge score." |
| **1:30–1:55** | Setup beat: cmd+click → Phoenix trace ("every decision is auditable" — **NOT** the climax) | Cursor moves to Block finding. Cmd+click. Phoenix dashboard opens in pre-loaded second window (split-screen per plan.md §7 D19). On-screen: full trace tree; the three Phoenix annotations `hallucination`, `clause_faithfulness`, `risk_judge_gate` (PROJECT_LOG.md L72) visible; cited clause span highlighted. Hold ~25s — enough to register the audit surface, NOT the climax hold. | "Cmd-click — the full Phoenix trace opens. Every span, every evaluator, every cited clause. Every decision is auditable." |
| **1:55–2:15** | Honest numbers | Switch to the README results table. Wilson 95% LB on Block recall displayed with the achieved number (pre-committed to publish unmodified per PROJECT_LOG.md L91). Three-track table visible: MAUD-MCQ accuracy, CUAD-Spans token-F1, Internal-30 5-fold-CV Block recall. Footer label: "5-fold CV; fold 5 reserved for Reflector non-regression." | "Numbers are reported as Wilson lower bounds on a frozen held-out fold. We publish the achieved number, not the best case." |
| **2:15–2:30** | Loop setup: Reflector grows the regression dataset, candidate proposed | Switch to the Phoenix Experiments tab. Visible: `regressions-v1` dataset row added by Reflector overnight; `candidate` prompt row in the prompts list. Two experiment-run rows visible in the experiments table (both completed overnight via Cloud Scheduler): one against `regressions-v1`, one against `internal-30-holdout-fold-5`. | "Overnight, the Reflector read its failure traces and proposed a candidate prompt." |
| **2:30–3:00** | **CLIMAX (sole) — auto-promotion event** | **Split-screen.** LEFT pane: Reflector run output (terminal tail / stdout capture from the nightly Cloud Scheduler hit on `/reflect`) — two adjacent log lines visible: `_LOG.info("Promotion gates passed: %s", diag)` with the `diag` dict surfacing `regression_ci_lb`, `epsilon_fold5`, `fold5_candidate_mean`, `fold5_production_mean`, `fold5_non_regression_ok`, `regression_gate_ok`, followed by `_LOG.info("PROMOTED candidate %s → tag=production on %s", ...)`. Function entry points: [`agent/reflector.py:461`](../agent/reflector.py#L461) (`paired_bootstrap_ci_lb`), [`:503`](../agent/reflector.py#L503) (`epsilon_fold5`), [`:508`](../agent/reflector.py#L508) (`should_promote`), [`:753`](../agent/reflector.py#L753) (`_promote_candidate` — which calls `client.prompts.tags.create` to flip the `production` tag), [`:760`](../agent/reflector.py#L760) (PROMOTED log line), [`:851`](../agent/reflector.py#L851) (Promotion-gates-passed log line). RIGHT pane: Phoenix Experiments tab — the experiments results table for the regression-set + fold-5-holdout runs (per-example scores in columns), with the prompts-list view visible underneath showing the `production` tag pointing to the new (just-promoted) version. Optional inset: reliability-diagram PNG from [`scripts/calibrate.py:184`](../scripts/calibrate.py#L184) `plot_reliability` for fold-5, picture-in-picture. The moment the climax beat opens (T = 2:30.000) the auto-promotion event lands in both panes simultaneously. **Caption per Deliverable 2 fades in at 2:30, holds through 2:52, fades out by 2:52.4.** Final ~8s (2:52 → 3:00) holds the post-promotion state; bottom-of-frame card shows GitHub URL + hosted demo URL + Phoenix project URL in `fontSize.mono-attribution`. **Honest framing**: the CI LB / ε narrative is proven by Reflector code output (LEFT) and by Phoenix experiment scores + prompts-list view (RIGHT) — NOT by a custom Phoenix CI-bar visualization. Phoenix Experiments ships a results table + comparison summaries, not custom paired-bootstrap CI plots; the visuals on screen are the artifacts that actually exist in the deployed system. The MCP-tool name `add-prompt-version-tag` is the protocol-level surface (Phoenix MCP server); the deployed Reflector uses the equivalent Phoenix Python SDK path (`client.prompts.tags.create`) — both flip the same `production` tag, but the visible log line is the SDK one. | (The full Deliverable-1 voiceover plays across this 30s window.) |

**Total runtime: exactly 3:00.**

### Pre-recorded EDGAR fallback (separate row, explicit cut-in / re-merge)

| Trigger | Cut-in window | What plays instead | Voiceover behavior |
|---|---|---|---|
| Live EDGAR fetch latency > 30s, OR EdgarTools MCP raises, OR Vertex AI 429s during the live demo segment | Cuts in at 0:50 (seam at the deal-selection click); re-merges with the live recording at 1:55 (start of the honest-numbers beat — Phoenix tab + cursor state re-aligned at the cut). Cmd+click setup beat (1:30–1:55) is **inside** the pre-recorded segment; per plan.md §8 "the cmd+click moment is recorded against the local data and works deterministically." | A D19-captured walkthrough of one known-good run on Microsoft/Activision (the most reliable per `verify_allow_list.py` D10 output — confirm at recording time), against local cached EDGAR fixtures for bit-identical takes. | Live voiceover continues uncut over the pre-recorded segment. |
| Phoenix Cloud Run cold-start > 10s on cmd+click | Phoenix is pre-loaded in a second window from 0:00 per plan.md §7 D19, AND `min-instances=1` from D20 per plan.md §12. Belt-and-suspenders fallback: if both fail, the cmd+click jump shows a full-screen still of the trace from a prior recording, with a "captured 2026-06-{date}" timestamp in the corner. | Single still image of the trace from the most-recent good capture. | Voiceover line trimmed by ~1.5s (recoverable in edit). |
| Auto-promotion event fails to fire during recording (paired-bootstrap CI LB does not clear zero, OR ε(fold5) blocks promotion) | Climax beat (2:30–3:00) cuts to a D17 rehearsal capture pre-verified to show BOTH: (a) the LEFT-pane Reflector log output containing `paired_bootstrap_ci_lb` > 0 on the regression set AND `epsilon_fold5` passing on the frozen fold, AND (b) the RIGHT-pane Phoenix prompts-list view showing the `production` tag flip from candidate to new prompt. Timestamp ribbon: "captured during D17 rehearsal". The disclosure caption still plays. If no D17 rehearsal capture meets both gates, the climax voiceover must be edited to a procedural variant ("the gate fires only when the paired-bootstrap CI lower bound clears zero on the regression set, and the candidate does not regress on the frozen fold within epsilon") and the post-caption held shot replaced by the most recent good Reflector promotion event from production traces (Reflector log tail + Phoenix prompts-list view, same split-screen layout as the primary climax beat). | D17 rehearsal capture pre-verified against both gates via the LEFT-pane Reflector log + RIGHT-pane Phoenix prompts-list flip (or, on cascade-fallback, the most recent good production promotion event). | Voiceover unchanged on the primary path; on the cascade-fallback path it shifts to the procedural variant above. |

### Devpost description anchors (linked from the YouTube description, NOT read aloud)

The close-beat card on screen at 2:52–3:00 surfaces the README/hosted/Phoenix URLs. The YouTube video description below the video links explicitly to (each is already drafted verbatim in [`devpost.md`](devpost.md)):

- **Demo Scope paragraph** — devpost.md "Demo scope paragraph" block. Names all 5 deals + the selection rationale. Required in the Devpost project description per plan.md §12.
- **Reflector pre-seeding disclosure** — devpost.md "Reflector pre-seeding disclosure" block. The caption from Deliverable 2 is the freeze-frame surface for this disclosure; the Devpost text is the long-form surface.
- **AI-generated-content disclosure** — devpost.md "AI-generated-content disclosure" block. Required per plan.md §12.

---

## Recording-day operator notes (for Hugo)

These are not part of the deliverables — they are the operational
notes that must be stopwatch-verified at recording time.

- **Word counts are Python-counted, not eyeballed.** If you trim or add a word, re-run `len(text.split())` against the literal block. Hand-counts drift across column breaks; trust the script, not the count.
- **Pacing target: ~150 wpm.** At that pace the climax voiceover lands at 29.6s, inside the 30.0s climax slot. If you naturally pace at 140 wpm, the same script lands at ~31.7s — trim one short connective phrase or widen the climax slot by ~2s and tighten the streaming-findings beat (0:50–1:30) to compensate.
- **The "five pre-indexed deals" line fires twice**: once at the dropdown open (0:30–0:50) and once as recap inside the climax voiceover (2:30–3:00). Both are verbatim. This is intentional — the §5.5 lock is a recording-day disclosure obligation, not a single-utterance constraint.
- **Caption rendering**: Inter Medium 500 at 14px on a 1440p export should be tested before recording day. The token system would also support Inter 600 at the same size if the 500 weight reads light on a Phoenix-dashboard-bright backdrop. Test once; if 500 holds, ship; if not, escalate weight to 600 (same `fontSize.small` key, no token change).
- **Beat timings are designed, not stopwatch-tested.** The 25s cmd+click hold (1:30–1:55) and the 30s climax hold (2:30–3:00) need at least one full-rehearsal stopwatch pass on D17–D18. If a beat overruns, trim from the streaming-findings beat (0:50–1:30) — it has the most natural slack.
- **The fallback rows ARE the live demo for any judge watching the bake.** The "live demo" framing exists for in-person / Q&A — the bake should look identical whether the EDGAR fetch was live or pre-recorded.

---

## Cross-references (audit trail)

- Plan beat-table being superseded for recording: [`../../plan.md`](../../plan.md) §8.
- Pre-commitments enforced verbatim: [`../../PROJECT_LOG.md`](../../PROJECT_LOG.md) "Pre-commitments locked".
- Canonical disclosure wordings reused: [`devpost.md`](devpost.md) "Demo scope paragraph", "Reflector pre-seeding disclosure", "AI-generated-content disclosure".
- Token sources for every cited typography / motion / color value: [`../../design/tokens.ts`](../../design/tokens.ts).
- Operator-side recording checklist (D19 row): [`../HANDOFF.md`](../HANDOFF.md) "D19 (demo recording)".
