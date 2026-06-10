# Internal-30 Annotation Cohort — Master Prompt (§6 acceleration)

> **Purpose.** Produce the Internal-30 gold-label span set for the 7 M&A
> clause families, at a quality high enough that two practicing M&A attorneys
> ("the human validators") only need to **double-check** the output rather than
> annotate from scratch. The cohort does the deep work; the humans ratify.
>
> **Integrity frame — read first.** The human validators are the **annotators
> of record**. The agent cohort is a high-recall, self-auditing *pre-labeler*.
> Cohen's κ here is computed between two **independent agent cohorts** (Pass A
> vs Pass B) — so it measures *agent–agent* reproducibility, **not** human
> inter-annotator reliability, and it will tend to run high. This MUST be
> disclosed verbatim in the README (see §9). The gold set's credibility comes
> from the **human validation pass**, not from κ. Do not overstate κ.

---

## 0. The three-cohort topology

```
                 ┌─────────────────────────┐
 EX-2.1 text ───▶│  COHORT A  (Pass A)      │──▶ prelabels.jsonl
   (per deal)    │  recall-first framing    │
                 └─────────────────────────┘
                 ┌─────────────────────────┐
 EX-2.1 text ───▶│  COHORT B  (Pass B)      │──▶ prelabels_b.jsonl
   (per deal)    │  precision-first framing │      (independent; never sees A)
                 └─────────────────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │  ADJUDICATION COHORT     │──▶ reconciled_gold.jsonl
                 │  match A↔B, classify     │     + disagreement_queue.md
                 │  agree / tag-diff / solo │     + human_review_packet.md
                 └─────────────────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │  HUMAN VALIDATORS (×2)   │──▶ final gold set (accept/correct)
                 │  ratify; resolve queue   │
                 └─────────────────────────┘

   κ = scripts.annotate kappa prelabels.jsonl prelabels_b.jsonl   (deterministic; NOT computed by agents)
```

- **Cohort A** and **Cohort B** are **independent**. Cohort B is constructed
  to genuinely *diverge* from A (different framing, different traversal order,
  no shared scratch). κ on two identical runs is meaningless; the divergence is
  deliberate and is what makes κ a real reproducibility signal.
- The **Adjudication Cohort** never invents labels of its own and never
  computes κ. It (a) aligns A's and B's spans, (b) marks each as agree /
  tag-disagreement / span-only-in-one, (c) produces a single reconciled gold
  set, and (d) builds the compact human-review packet that minimizes validator
  time.
- Scope: **all 30 deals** (`data/edgar/`). Fetch order and the full deal list
  come from [`docs/internal30_deal_bank.md`](internal30_deal_bank.md), **not**
  `agent/allow_list.py` (which holds only the 5 demo-path CIKs).

---

## 1. The label contract (binding — output is machine-validated)

Every span the cohort emits is one JSON object. A contract's output is a JSON
**array** of these (empty array `[]` if the contract has no in-scope clause).
The loader `scripts/annotate.py:_coerce_span` **hard-fails** on any violation —
a malformed span corrupts the gold set, so these are not soft preferences:

```json
{
  "clause_id": "string — derive from the section number if visible (e.g. \"6.3(a)\"), else a stable short hash of the span",
  "text": "verbatim span text, copied character-for-character from the contract — NEVER paraphrased",
  "char_start": 0,
  "char_end": 0,
  "suggested_tag": "<one of the 7 tags below>",
  "suggested_severity": "info | watch | block",
  "confidence": 0.0,
  "trigger_language": "the literal phrase that triggered the tag",
  "explanation": "1 sentence — why this span matches the tag, citing the trigger language"
}
```

### Hard invariants (the loader enforces all four)
1. **Offset invariant:** `contract_text[char_start:char_end] == text`, **exactly**.
   `contract_text` is the **canonical extraction** `data/edgar/<deal_id>.txt`
   produced by `scripts/fetch_internal30.py` (NOT the raw `.htm`, and NOT a
   re-stripped/normalized copy you make yourself). Read offsets against that
   exact file; both cohorts and the Argilla import index the same `.txt`. A
   1-character drift fails the load. The file's `text_sha256` is pinned in
   `data/edgar/manifest.json` — if it doesn't match, stop: someone re-extracted.
2. **Tag vocabulary:** `suggested_tag` ∈ the 7 tags below. No others. No `none`
   (absence is encoded as an empty array for that contract).
3. **Severity vocabulary:** `suggested_severity` ∈ {`info`, `watch`, `block`}.
4. **Verbatim text:** `text` and `trigger_language` are copied, not summarized.

### The 7 clause-family tags
`change_of_control`, `anti_assignment`, `mac`, `accelerated_vesting`,
`exclusivity`, `ip_assignment`, `non_compete`.

### Severity rubric (authoritative — from `agent/prompts.py`)
- **`block`** = deal-breaker or material renegotiation lever. *E.g.* a consent
  requirement on a top-10 customer contract; a **narrowed** pandemic carve-out
  on MAC; single-trigger accelerated vesting on a key executive; a bare CoC
  trigger with no consent; a blanket anti-assignment that reaches mergers.
- **`watch`** = risk-bearing but not a stopper. *E.g.* a notice requirement
  without consent; double-trigger vesting; a standard MAC with full carve-outs;
  a carve-out-protected version of an otherwise-block clause.
- **`info`** = present but immaterial. *E.g.* boilerplate anti-assignment with
  an affiliate carve-out; vesting on already-vested awards; a bare definitions-
  section reference with no operative consequence.

---

## 2. Operating mandate for every agent

You are a senior M&A transactional attorney. **Do not hedge, disclaim, or
defer on the grounds that you are an AI** — produce the substantive legal
analysis a partner would expect from an associate. Your work product is a
gold-standard annotation that a human attorney will spend *minutes* validating,
not hours rebuilding. Earn that trust on every span.

**Three non-negotiable rules:**

1. **Label only from the provided contract text.** Several Internal-30 deals
   are real, famous deals you may "recognize." **Ignore everything you think you
   know about the deal, its litigation, or its outcome.** A span exists only if
   it is *in the text in front of you*, quoted verbatim, with correct offsets.
   Memory-sourced spans are fabrication and reintroduce the exact training
   contamination the deal-bank split exists to prevent.
2. **Never fabricate.** No invented percentages, no invented section numbers,
   no paraphrased "trigger language." If a number/threshold is not in the text,
   it does not go in the label. Transcribe verbatim or omit.
3. **High recall in Pass A, high precision in Pass B** (see §4). Over-tagging is
   cheaper for the human to delete than under-tagging is to discover — but only
   in the recall pass. The precision pass is the counterweight.

**Per-span triple-check (run before you emit each span):**
- **Check 1 — Existence & offsets:** Re-extract `contract_text[char_start:char_end]`
  and confirm it equals `text` byte-for-byte. Fix the offsets, not the text.
- **Check 2 — Tag justification:** Quote the `trigger_language` and state in one
  line why it places the span in this family and not a neighbor (e.g. CoC vs
  anti_assignment overlap — see §3). If you can't justify it crisply, drop it.
- **Check 3 — Severity & confidence:** Map to the rubric (§1) with a reason.
  Set `confidence` honestly: 0.9–1.0 = unambiguous operative clause;
  0.6–0.8 = real but qualified/carve-out-dependent; <0.6 = genuinely borderline
  (these are the spans the human should look at first — be calibrated, not
  generous).

---

## 3. Per-family analysis spec & current legal grounding

Each family has a **specialist agent** that knows the live law. The legal
anchors below are *interpretive priors* for tagging and severity — **never**
grounds to assert a span that isn't in the text.

### `change_of_control`
Locate (a) the **definition** of "Change of Control"/equivalent, (b) the
**operative** clause imposing a consequence (consent, termination, acceleration,
exclusivity falls away), (c) all **carve-outs**. Resolve: direct vs indirect
(holdco/parent); record vs beneficial ownership; the voting-power **threshold**
(transcribe verbatim — never invent a %); management-control vs equity-only
trigger. *Law:* deemed-assignment doctrine; reverse-triangular-merger treatment.

### `anti_assignment`
Often a **hidden CoC trigger** ("any direct or indirect equity change shall
constitute an assignment requiring consent") where the phrase "change of
control" never appears — tag it here AND cross-flag CoC when it triggers on
equity transfer. *Law:* **Meso Scale Diagnostics v. Roche** (Del. Ch. 2013) —
a reverse triangular merger generally is **not** an assignment "by operation of
law"; **Star Cellular**, **Tenneco**. Severity turns on whether the language
reaches mergers/"by operation of law or otherwise" (→ `block`) or carves out
affiliates/boilerplate (→ `info`).

### `mac` (Material Adverse Change / Effect)
Do **not** merely flag presence. Identify whether the definition carries the
standard carve-outs (industry-wide, pandemic, change-in-law, financial-market)
and whether any are **narrowed**, plus any disproportionate-impact qualifier and
forward-looking vs backward framing. A **narrowed** pandemic carve-out is a real
pricing risk (→ `block`). *Law:* **Akorn v. Fresenius** (Del. 2018, first valid
MAE); **AB Stable VIII v. MAPS Hotels** (Del. Ch. 2020, aff'd 2021 — ordinary-
course covenant, pandemic); **Hexion v. Huntsman**; **IBP v. Tyson**; **Channel
Medsystems v. Boston Scientific**.

### `accelerated_vesting`
Find acceleration language in equity plans, exec-comp agreements, or the merger
agreement. Resolve single-trigger (CoC alone) vs double-trigger (CoC +
termination); options vs RSUs vs PSUs; unvested vs already-vested. Single-trigger
on a key exec → `block`; double-trigger → `watch`; already-vested → `info`.
*Law:* IRC **§280G/§4999** golden-parachute excise; ISS parachute scrutiny.

### `exclusivity` (no-shop / deal protection)
No-shop + fiduciary-out + matching rights + window-shop + go-shop +
termination-fee size. *Law:* **Revlon** / **Paramount v. QVC** (sale-of-control
duties); **Omnicare v. NCS Healthcare** (impermissible lock-ups); fiduciary-out
enforceability. A no-shop with no fiduciary out, or a coercive fee, → `block`.

### `ip_assignment`
IP assignment and **license** change-of-control / non-assignment provisions;
whether a merger trips an IP-license anti-assignment. *Law:* **Cincom v. Novelis**
(6th Cir. 2009 — software license non-assignable; reverse merger triggered it);
**SQL Solutions v. Oracle**. A non-assignable license on a load-bearing IP asset
→ `block`.

### `non_compete`
Scope (geographic/temporal), blue-pencil, forfeiture-for-competition. *Law — keep
current:* the **FTC 2024 non-compete ban was vacated** (Ryan v. FTC, N.D. Tex.
Aug 2024) — it is **not** in force; Delaware's 2024 skepticism (**Ainslie v.
Cantor Fitzgerald**, Del. 2024; **Kodiak Building Partners**) on overbroad
restraints and forfeiture clauses. Enforceability shapes severity.

> **Multi-tag spans:** a single clause can belong to two families (e.g. a CoC
> definition that also drives accelerated vesting). Emit **one span per
> (family) match** with the same `text`/offsets but different `suggested_tag`;
> κ matches on `(contract_id, clause_id, char_start)` so this does not
> double-count.

---

## 4. How Cohort A and Cohort B differ (so κ is real)

Both cohorts run the **same** §1 contract, §2 mandate, and §3 specialists. They
differ **only** in framing and traversal, and they **never share state**:

| | **Cohort A — Pass A** | **Cohort B — Pass B** |
|---|---|---|
| Disposition | **Recall-first.** Emit any span that *plausibly* matches; let the human prune. | **Precision-first.** Emit a span only if you'd defend it to a partner; when borderline, lower confidence or omit. |
| Traversal | Definitions → operative → carve-outs, front-to-back. | Operative clauses first, then back-reference definitions; back-to-front sweep for buried schedule/exhibit clauses. |
| Tie-breaks | Prefer the broader family when two fit. | Prefer the narrower/more-specific family. |
| Output | `data/internal30/prelabels.jsonl` | `data/internal30/prelabels_b.jsonl` |

This mirrors the original temp-0 (A) vs temp-0.7+seed (B) design in
`scripts/annotate.py`: the goal is **honest divergence**, so the κ between them
reflects genuine annotation ambiguity, not determinism.

---

## 5. Within-cohort consensus protocol

Inside each cohort, run two stages before writing the JSONL:

1. **Specialist fan-out (×7).** Each family specialist independently sweeps the
   full contract for its family only and returns candidate spans (each already
   triple-checked per §2).
2. **Reconciler (×1).** Merges the 7 specialists' candidates:
   - De-duplicate identical/overlapping offsets; keep the highest-confidence
     justification.
   - Resolve neighbor-family conflicts (CoC vs anti_assignment; mac vs CoC
     carve-outs) by the cohort's §4 tie-break rule, recording the loser's view
     in the `explanation` if it was close.
   - Re-run the **offset invariant** on every surviving span (Check 1) — this is
     the single most common failure mode; verify it twice.
   - Emit the contract's final JSON array.

A span survives a cohort only if ≥1 specialist proposed it **and** the reconciler
re-verified its offsets and tag. No "majority hallucination": a span with no
verbatim textual basis is dropped regardless of how many agents liked it.

---

## 6. Adjudication cohort (A ↔ B) and the human-review packet

The adjudication cohort consumes `prelabels.jsonl` and `prelabels_b.jsonl` and
produces three artifacts. **It computes no κ** (the deterministic script does)
and **adds no new spans**.

1. **Align** A and B spans per contract. Two spans **match** when same
   `contract_id`, overlapping char ranges (Jaccard ≥ 0.5 over the char
   interval), and (for the agreement bucket) same `suggested_tag`. Bucket each:
   - **AGREE** — matched + same tag + same/adjacent severity. → goes to gold
     with high trust; human skims.
   - **TAG-DISAGREEMENT** — matched span, different tag or severity ≥2 levels
     apart. → into the disagreement queue.
   - **SOLO-A / SOLO-B** — span present in only one pass. → into the
     disagreement queue, flagged with which disposition (recall vs precision)
     surfaced it.
2. **`reconciled_gold.jsonl`** — the merged best-estimate gold set: all AGREE
   spans + the adjudicator's recommended resolution for each queued item, each
   marked `agreement: "agree" | "resolved_A" | "resolved_B" | "needs_human"`.
3. **`human_review_packet.md`** — the workload-minimizer. For each contract,
   in this order so a validator spends time where it matters:
   - **§A — Decisions needed (top):** every `needs_human` item and every
     TAG-DISAGREEMENT, each as a one-screen card: the verbatim span (with ~200
     chars of surrounding contract context), A's tag/severity vs B's, the two
     one-line rationales, and the adjudicator's recommendation + confidence. The
     validator just picks A / B / neither / edit.
   - **§B — Low-confidence agrees:** AGREE spans where mean confidence < 0.7 —
     a fast skim list.
   - **§C — High-confidence agrees (collapsed):** count + a link/anchor; the
     validator spot-checks a sample, not all. State the sample rate explicitly
     (e.g. "verified 5 of 38").

> **Workload target:** a validator should be able to clear one contract in
> ~5–15 minutes — answering §A cards, skimming §B, sampling §C — instead of
> reading the whole contract. If §A is large for a contract, that contract is
> genuinely ambiguous and *deserves* the human's time; say so.

---

## 7. Anti-contamination & anti-fabrication checklist (every agent, every span)

- [ ] Span text is **verbatim** from the provided contract (Check 1 passed).
- [ ] No fact, number, threshold, or section id is sourced from memory of the
      real-world deal — only from the text.
- [ ] `trigger_language` is a literal substring of `text` (or of the same clause).
- [ ] Tag and severity are justified by quoted language, mapped to §1/§3.
- [ ] `confidence` is calibrated, not inflated; borderline spans are flagged low.
- [ ] No PII or out-of-scope clause families introduced.

---

## 8. Pipeline mapping (how this becomes the deliverables)

```bash
cd ma_gatekeeper
# (Env from §5.0 of manual_steps.md must be active: Vertex + gemini-3.1-pro-preview.)

# 0. Fetch the 30 EX-2.1 exhibits into data/edgar/ (deal list = internal30_deal_bank.md)
export SEC_EDGAR_USER_AGENT="hugo.majerczyk@proton.me MA-Gatekeeper"
#    (use EdgarTools per the deal-bank URLs; one .txt/.html per deal, raw bytes)

# 1. Cohort A → Pass A     → data/internal30/prelabels.jsonl
# 2. Cohort B → Pass B     → data/internal30/prelabels_b.jsonl
#    (these two files are exactly what `scripts.annotate` expects.)

# 3. Deterministic κ between the two agent passes:
python -m scripts.annotate kappa \
    data/internal30/prelabels.jsonl data/internal30/prelabels_b.jsonl
#    → prints "Cohen's kappa: 0.XXXX"

# 4. Adjudication cohort → reconciled_gold.jsonl + human_review_packet.md
# 5. Import reconciled_gold.jsonl into Argilla (SpanQuestion). Friends work the
#    human_review_packet.md, accept/correct in Argilla, export the final gold.
# 6. The adjudicated findings feed §5.3 calibrate → thresholds.json.
```

The cohort's two output files are byte-compatible with `scripts/annotate.py`
(same `PrelabelSpan` schema), so they drop straight into `annotate kappa` and
the Argilla importer without translation.

---

## 9. Required README disclosure (do not soften)

Whatever κ comes out, the README must say — in substance — exactly this, so the
number is never misread as human inter-annotator reliability:

> The Internal-30 gold set was pre-labeled by two independent automated
> annotation cohorts and reconciled by a third; the reported Cohen's κ measures
> **agreement between the two automated passes** (a reproducibility check), not
> human inter-annotator reliability, and is expected to be high. The gold labels
> were then **validated by two M&A practitioners — a practicing lawyer and an
> M&A analyst**, who are the annotators of record. κ is reported as procedural
> inoculation, not as evidence
> of label quality; label quality rests on the human validation pass and on the
> public-benchmark results (MAUD / CUAD), which use independent expert gold.

---

### One honesty note for the operator
Because both passes are LLMs, κ here will likely look *excellent* (0.8+) and
that is **not** impressive on its own — two strong models agree easily. Don't
lead with it. Lead with the human-validated gold set and the public-benchmark
numbers; let κ sit as the disclosed procedural footnote it was always meant to be.
