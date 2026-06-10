# Ground-Truth Hardening Plan — Tier 1 (pre-deadline) + Tier 3 (mostly post)

**Status:** v2 — VALIDATED by a 5-agent panel (code-accuracy auditor, feasibility/deadline critic, Arize-eval judge, M&A lawyer, anti-overclaim critic). Verdicts: 2 × MAJOR_REVISION, 3 × APPROVE_WITH_CHANGES. All blockers + majors below are folded in; verdict appendix at the end. **Deadline:** 2026-06-11 (~2 working days).

**Why this exists:** the judge/client panel found the project has world-class eval *plumbing* but missing/circular *evidence*. Four gaps verified against the code; **a fifth surfaced during validation** and changes the headline framing:

1. `citation_gold_v1.jsonl` is **86% verbatim-identical** to `citation_map.json` (12/14 unique strings; 33/40 rows).
2. **No code computes** the gold-vs-map agreement README Hook 8 advertises; nothing reads the gold file.
3. The README results table markers (`README.md:262-263`) are **empty**.
4. `server.py:935` calls `lookup_citation(finding.tag)` with **no jurisdiction**.
5. **(NEW, from validation)** Running the plan's own T1.1 step today yields **map = 19/40, not "~30–35"**. Of the 21 "misses": ~14 are because `lookup_citation` returns `candidates[0]` (the gold wants `§271`/`§902`/`§2-210`, which **are** in the map but not the first entry for the tag), and ~7 are **case-law long-vs-short citation-form artifacts** (`Akorn … 2018 WL 4719347 (Del. Ch. Oct. 1, 2018), aff'd, 198 A.3d 724` vs gold `… (Del. Ch. 2018)` → `citations_match`=False even though the map is correct). **The map is not missing real authority — the comparator and the single-best-answer lookup are manufacturing the misses.** This must be fixed or T1.1 ships a *false-modesty* overclaim ("our verified map is only 48% right").

## Guardrails (anti-overclaim — non-negotiable; strengthened in v2)
- Map's gold score = **"coverage, by construction (every entry primary-source-verified), NOT accuracy."** The **graded** number is the **LLM proposer's**; it may be imperfect.
- **Never pre-announce a number** (no "~30–35"): run `eval_citation_gold.py`, report the ACTUAL value, whatever it is.
- **Run-mode honesty:** the eval JSON MUST carry `run_mode: "mock"|"live"`; any mock proposer number renders with a literal **"MOCK — deterministic stub, not the live model"** tag in the Notes column. The mirror target (`eval_maud_mcq.py`) has NO run-mode field — we add one.
- **κ is human-vs-model**, labeled verbatim `human-vs-LLM-prelabel agreement, Cohen's κ = X.XX, n = N, illustrative` — no adjectives, never "inter-annotator."
- **Correct, don't supplement,** README Hook 8 (it is a live false claim today) in the same commit the numbers land.
- **Fail-closed jurisdiction:** never serve a different jurisdiction's authority (esp. a Delaware *case*) to a NY/CA/UCC-governed clause. Low-confidence → Delaware-default-**with-a-visible-label**, or None.
- **Demo stamp ≠ human attestation:** the on-screen "verified against courts.delaware.gov" must carry a VO/caption that verification was an automated counsel-persona + web-fetch; production substitutes a named GC (signer is still `ma-counsel-persona`; do not imply otherwise).
- Don't claim "pinned by a human" anywhere — that signer fix is Tier-2, out of scope here.

---

# TIER 1 — before 2026-06-11

## T1.1 — Citation eval + de-circularize gold + fill the table  *(highest leverage)*
**Goal:** ship two HONEST numbers — `map: X/40 (coverage, by construction)` and `LLM-proposer: Y/40 (graded)` — plus their agreement, with the comparator and lookup contract fixed so neither number lies.

**Fix the measurement first (blocker, from Arize + anti-overclaim):**
- **Lookup contract:** grade `map coverage` as **recall@1 given the gold-provided tag + jurisdiction hint** — and report it as exactly that, not as "the map's accuracy." Optionally also report a "map-contains-the-authority-anywhere-for-this-tag" number; if the two differ, that gap is itself the `candidates[0]` story, reported honestly.
- **Normalise case-law citations on BOTH sides** before comparing (canonical short form: party-names + first reporter cite, or docket no.), so `Akorn (Del. Ch. 2018)` ≡ the map's parallel-cite long form. Without this, ~7 correct case-law entries score as misses.
- In `eval_citation_gold.py`, **bucket every row** as `in_map_hit` / `citation_form_mismatch` / `true_off_map_miss` and report counts separately. `map_recall` counts only true hits; form-mismatches are a labeled side bucket, not silent misses.

**Gold schema reality (blocker, from feasibility + anti-overclaim):**
- The gold uses `row["input"]["tag"]` (NOT `row["tag"]`) and `metadata = {deal_id, fold}` only — **there is no `metadata.jurisdiction`**. The regen step MUST add `metadata.jurisdiction` to **every** row (old + new) and a `metadata.source` URL per row. The script reads `input.tag` + `metadata.jurisdiction`. README/SIGNOFF must state the jurisdiction hint is **gold-provided** (not agent-extracted — that's the separate T1.2 path), so no one reads it as "the agent inferred NY."

**De-circularize so the map can MISS for a real reason (blocker, from Arize):**
- Add ~8–12 rows whose controlling authority is **outside the map's 6-tag / 5-jurisdiction universe**, so `lookup_citation` returns **None** (a true miss): e.g. DGCL **§ 262** (appraisal), **6 Del. C.** (DRULPA, LP target), an HSR sub-threshold exemption, a state assignment statute. Plus **jurisdiction-mismatch** rows (NY CoC → § 902) and **tag-disguise** rows (an `anti_assignment` clause that is a hidden CoC, per `CROSS_REFERENCE_PROMPT` §2).
- **Source reality (major, feasibility tested it):** `legislation.gov.uk` (UK § 979) returns EMPTY via WebFetch (JS-gated); Cornell `wex/appraisal_right` 404s; DGCL § 262 is on a different `delcode` subchapter than the map's `sc09` page. **DROP UK § 979.** Use only confirmed-fetchable sources (`delcode.delaware.gov` 251–262, Cornell LII `/uscode` + `/ucc`, `nysenate.gov`, `leginfo.ca.gov`). Every new cite verified via WebFetch; record the exact URL in a new **`data/CITATION_GOLD_SIGNOFF.md`** (mirror `CITATION_MAP_SIGNOFF.md`). Unfetchable → DROP, don't guess.
- Report `n_off_map` explicitly so a reader sees "map missed K of K off-map rows by construction" as a SEPARATE line from in-map coverage.

**New file `scripts/eval_citation_gold.py`** — right-sized (~150–250 LoC; do NOT clone the 820-line `eval_maud_mcq.py`, just its conventions):
- Default = deterministic **mock** proposer; `--live` opts into `agent.citation_linker._call_linker_llm`; `--gold`, `--out`.
- Scores the **map** via `lookup_citation(input.tag, jurisdiction_hint=metadata.jurisdiction)` and the **proposer** (live) / mock, both against the SAME de-circularized gold, using `make_citation_exact_match_classifier()` (deterministic rail) + case-law normalisation.
- **Formal JSON contract** (consumed by `_build_citation_rows`): `run_mode`, `map_recall`, `proposer_recall`, `proposer_vs_map_agreement`, `n_in_map`, `n_off_map`, `n_form_mismatch`, `per_tag` (tag→{map,proposer,n}), `n_evaluated`, `n_total`, `proposer_recall_wilson_lb` (small-n CI), `confidence_reliability_bins` (**omit the key entirely when mock**; when live, **3 bins** low/med/high with per-bin `n` + an "n≈40, illustrative, ungrounded calibration" caveat — NOT 10 bins), `gold_provenance`.
- `tests/test_eval_citation_gold.py`: mock determinism; the bucketing math; agreement math; `run_mode` round-trips; assert each off-map row resolves to None or a genuinely different authority (not a form artifact).

**Modified `scripts/build_readme_table.py`** — 4th track, fully wired + tested:
- `_build_citation_rows(data)` (mirror `_build_maud_rows`); add `--citation`; **thread `citation` through BOTH `load_track_jsons` AND `render_table`** (they hardcode internal30/maud/cuad today — a row-builder alone renders nothing). Notes strings carry the guardrail verbatim: map row = "coverage, by construction — primary-source-verified, not earned accuracy"; proposer row under mock = "MOCK — deterministic stub, not the live model"; an explicit "map = coverage (recall@1); proposer = accuracy; agreement ≠ accuracy — not summed."
- Extend `tests/test_build_readme_table.py` for the citation track + the mock-label assertion + the "Not yet available" placeholder.

**Correct README Hook 8 (blocker):** replace the current sentence (which falsely claims "non-circular… a different annotator and source set… agreement logged as dataset metadata") with the true description: deliberately-divergent gold, two separately-reported numbers, both LLM-counsel-curated (not a second human). Drop standalone "non-circular."

**Effort:** M (~1 day, the comparator-fix + de-circularization + signoff push the estimate up from the v1 "0.75"). **Critical path. Safe-to-ship-without-infra:** the MOCK citation track + corrected Hook 8 closes the empty-table + circularity gaps with zero live dependency.

## T1.2 — Jurisdiction-aware citation + severity-gated case-law + the demo "money moment"
**Goal:** the rendered citation depends on the contract (NY→§902, DE→§251) and the finding (case-law only on real risk); the demo SHOWS the proposer overruled — without looking staged.

**Governing-law linkage (blocker — RiskFinding has NO jurisdiction field):**
- `CROSS_REFERENCE_PROMPT` emits a **top-level `governing_law` object** `{verbatim_clause, jurisdiction}` **separate from the RiskFinding array** (one per contract, not per finding).
- `server.py:_stream_findings` captures it **once per contract** by intercepting the `cross_reference` event (mirror the `clauses_by_id` capture), then passes `lookup_citation(finding.tag, jurisdiction_hint=normalize_jurisdiction(governing_law))` for every finding.
- `agent/citation_linker.py`: add `normalize_jurisdiction(text) -> str | None` with a **pinned keyword table** mapping contract language → the map's exact 5 jurisdiction values (`Delaware`, `Federal`, `New York`, `California`, `Uniform Commercial Code`): "State of Delaware"→Delaware, "laws of the State of New York"→New York, etc. Unknown/ambiguous → None.

**Fail-closed (blocker, lawyer + anti-overclaim):** if the hinted jurisdiction has no same-jurisdiction entry for the tag, return **None (escalate)** — NEVER fall through to a different jurisdiction's authority (today's substring fallback could surface a Delaware *case* on a NY hint; Cal. § 16600 must require a California hint). Low-confidence extraction → Delaware-default rendered with a visible "governing law not detected — Delaware default" rationale.

**Severity-gated case-law (major, with the no-statute-fallback fix):**
- After lookup, if `static_ref.citation_kind == "case_law"` and `finding.severity != "block"`: drop to the **statute entry for that tag/jurisdiction ONLY IF ONE EXISTS**; otherwise **KEEP the case-law** (do not blank it). `mac` and `exclusivity` have ONLY case-law entries (Akorn/AB Stable; Revlon) — for those, a watch-tier finding keeps the case (or renders a doctrinal note), it does NOT become "no controlling statute."
- The graceful-None render must distinguish **"authority is case-law X"** from **"contract-anchored, no controlling authority"** (e.g. accelerated_vesting). The None-state render is therefore a **hard dependency** of the gate, not an independent nicety.
- **Per-tag apposite authority:** `change_of_control` maps to §251 (merger), §271 (asset sale), §18a/§18, §902 — these are NOT co-equal. An asset-sale clause must not render §251. Until per-clause selection exists, render only the canonical entry and label it precisely; do not imply the others.
- **Eval-consistency:** the offline `eval_citation_gold.py` grades the **RAW map (pre-severity-gate)**; the server renders **post-gate**. State this explicitly so "the script and the Phoenix rail agree" doesn't silently break on gated rows.

**Money moment — decoupled + de-risked (major, feasibility + Arize + anti-overclaim):**
- **Ship the deterministic code regardless** (jurisdiction switch + severity gate + None-state + `normalize_jurisdiction`), fully unit-tested — this is the durable artifact and must NOT be coupled to a live recording.
- The on-camera beat needs **live Phoenix + Vertex** (the `disagree` annotation is best-effort and silently no-ops with no collector; `_call_linker_llm` needs Vertex). **Operator pre-flight gate:** run one real `/review` on the chosen deal, visually confirm the `disagree` span exists in Phoenix BEFORE recording; if not green, fall back to a pre-recorded clip / canned annotation.
- **Substantive-disagreement check:** the comparator flags `disagree` on EITHER citation-form OR jurisdiction-string mismatch — verify the chosen demo disagreement is a REAL wrong-authority error (inspect the span's `explanation`), not a long-vs-short-form or jurisdiction-string artifact, or the climax shows the system "overruling" a proposer that was actually right.
- **Anti-rigging disclosure:** the deal is curated, so the VO/caption must tie the anecdote to the aggregate — "one illustrative case selected to show the map catching a proposer error; proposer-vs-map agreement across the gold is Y/40 — not every clause disagrees." Demo-script integration is NOT free: `docs/demo_script.md` is frame-locked at 30fps; **repurpose the existing 1:30–1:55 cmd-click→Phoenix beat** rather than adding a new one. (Demo-track owns this; hand off explicitly.)
- For the live switch, **hard-select one DE and one NY deal** rather than trusting free-form governing-law extraction on camera (a misread on camera is worse than not switching).

**Frontend:** surface `CitationRef.rationale` in `CitationRow`; implement the two distinct None-states above.

**Tests:** extend `tests/test_citation_linker.py` — jurisdiction selection (NY→§902); fail-closed (NY hint never returns a DE case; CA hint required for §16600); severity-gating (watch-mac keeps Akorn, does NOT blank; a tag with a statute fallback drops correctly); `normalize_jurisdiction` table; a `_stream_findings` test that a NY governing-law deal renders §902.

**Effort:** M (~0.75–1 day): governing-law extraction is the M part; fail-closed + severity-gate + normalize are S; money-moment is live-gated and may slip to the demo track.

## T1.3 — One real human-vs-model κ (re-scoped per validation)
- Machinery exists (`annotate.py kappa`; `_load_clause_tags` accepts flat `{contract_id, clause_id, char_start, tag}`).
- **`scripts/make_kappa_template.py` is REQUIRED (not optional):** it emits the selected 10–15 clauses with a **blank `tag`** and **the prelabel withheld** (no anchoring), on **exact matching `(contract_id, clause_id, char_start)` keys** so `cohen_kappa`'s intersection isn't empty (eyeballed offsets → `ValueError: no overlapping clause_ids`).
- **Operator (human, not Claude)** fills the tags → `human_adjudicated.jsonl` → `annotate.py kappa`.
- **Re-scope the claim (blocker per Arize):** as specified this is **human-vs-one-LLM TAG agreement on Internal-30 — a sanity check on the tag layer, NOT a measure of citation-gold reliability.** Report it verbatim as such, with per-class support / a small confusion matrix (a high κ can be driven by the `change_of_control` marginal). **OR**, to make it bear on the citation layer, have the human independently re-pick the **controlling authority** for the 10–15 citation-gold clauses and compute agreement on the *citation* label. Pick one and state which.
- **Effort:** S scaffold + ~1–2h human. **Operator-gated; cut first if Day-1 slips.**

## Tier-1 triage / explicit cut-list (if Day-1 AM overruns)
1. **KEEP no matter what:** `eval_citation_gold.py` + `_build_citation_rows` + corrected Hook 8 + the committed **MOCK** map(by-construction)/proposer(MOCK-labeled) numbers — closes circularity + empty-table with **zero infra**.
2. **First to drop:** UK/exotic off-map cites — keep only NY-mismatch (§902) + UCC/DE rows confirmed fetchable; even 4–5 credible off-map rows kill the tautology.
3. **Operator/live-gated stretch (cut before the headline):** T1.3 κ, the T1.2 live money moment, and the rest of the table (calibrate.py needs a judged-findings CSV from a real agent pass — itself an unsized live Vertex run).
- **Operator-bandwidth warning:** Day-2 serializes the human κ + a calibrate.py live pass + the live demo dry-run on ONE operator — do not assume they parallelize; the calibrate-fed Internal-30 rows are the likeliest casualty.

---

# TIER 3 — what real clients want (mostly post-deadline)

## T3.1 — Off-market posture ("is this clause normal?")
- New `data/deal_point_norms.json` + `DealPointNorm` schema + server-authoritative `market_posture`/`market_basis`/`frequency_pct`/`n` on RiskFinding + an OFF-MARKET pill.
- **Hard signoff gate (major, anti-overclaim):** ABA Deal Points Studies are **paywalled** (the deal-bank §4 names them as PRIORS, not loaded data). Every shipped frequency MUST carry a fetchable public source URL + exact quoted figure + study-year + sample-n in a new `data/DEAL_POINT_NORMS_SIGNOFF.md`; the pill shows source + n inline ("seller-favorable — 18%, ABA 2024 Public Target, n=…"), never a bare verdict. Unconfirmable → DROP. Until real sourced figures exist, call it an **"illustrative market-posture heuristic,"** NOT "benchmarked against the ABA Deal Points Study."
- **Verdict: post-deadline** (one sourced demo line is the only pre-deadline-feasible slice).

## T3.2 — Cross-deal triage queue
- `/triage` over N deals → `triage-pane.tsx`: per-deal Block-count, off-market-count, worst deviation, MAE-cluster membership; sortable; cells deep-link the finding's Phoenix trace. Weights inherit calibrated τ + the published recall LB caveat. **Post-deadline** (needs multi-deal UX; depends on T3.1).

## T3.3 — Precedent receipts + audit bundle
- **Precedent receipts (S–M, demoable stretch):** `data/precedents.json` from the **Narrative-10** bank (already stamped *illustrative-only; NOT in recall* — their sanctioned role). **Legal corrections (blocker + cautions):**
  - **Akorn:** reword to **"the FIRST Delaware decision to find a Material Adverse Effect that excused a buyer from closing; turned on a missing industry-wide carve-out + undisclosed regulatory-compliance failures."** DROP "only Delaware case to let a buyer walk" — **FALSE**: AB Stable (in this repo) also excused a buyer (on an ordinary-course-covenant breach, not an MAE).
  - **BMS/Celgene:** tag as **CVR / earn-out** (not a buyer's-walk/MAE precedent); attribute "$6.4B forfeited, 36 days late" to the **Skadden SDNY summary** (motion-to-dismiss posture), not as an adjudicated holding.
  - **Revlon:** frame as "deal-protection devices draw enhanced (Revlon/Unocal) scrutiny when a change of control is in play" — do NOT let the demo harden "this no-shop triggers Revlon" (false on many fact patterns).
- **Audit bundle (M, high GC value, post-deadline):** `/review/{id}/audit` → signed portable JSON (findings + prompt-version-hash + model-id + the 3 Phoenix annotation scores + citation-map version/verified_date + deployed τ + source-filing hash) + "Download audit record" button.

## Data-integrity fix that gates T1.1 + T3.3 (major, lawyer)
- **AB Stable entry is inconsistent:** `citation_map.json:135` `uri`=justia while `primary_source`="courts.delaware.gov", and `CITATION_MAP_SIGNOFF.md` records the verifying fetch as a **Fox Rothschild blog** (a secondary source). The gold rows point AB Stable at a Chancery-2020 justia path while citing the Supreme-Court-2021 reporter (268 A.3d 198). **Reconcile before T1.1 grades the map or T3.3 cites it:** either point `uri` at the real courts.delaware.gov opinion PDF and set `primary_source` accordingly, or honestly relabel `primary_source` as "law.justia.com / secondary." This sits in the exact case-law row the money moment leans on.

---

# Explicit non-goals / deferrals
- Citation-faithfulness rail (ContractNLI-style) — L, post-deadline.
- Full ABA off-market dataset, triage UX, audit bundle — post-deadline.
- Human attestation on `CITATION_MAP_SIGNOFF.md` — Tier-2, separate.
- Filling the **entire** results table is operator-gated (calibrate.py needs a real judged-findings CSV); only the **citation track** is fillable end-to-end without that.

# Open questions — resolved by validation
- ~~Can the off-map cites be WebFetch-verified?~~ **UK §979 NO (JS-gated); use delcode/Cornell/nysenate/leginfo only; drop UK.**
- ~~Is governing-law extraction reliable on camera?~~ **For the demo, hard-select one DE + one NY deal; reserve free-form extraction for post-deadline.**
- ~~Does the money moment need live Phoenix, and is it green?~~ **Yes; unverified by the suite. Decouple the deterministic code; gate the live beat on an operator pre-flight; mock/clip fallback.**
- Confirmed: gold is `input.tag` + `metadata={deal_id,fold}` (no jurisdiction — must add); README Hook 8 is a live overclaim (must correct); map naive coverage today = 19/40 (comparator + lookup artifacts — must fix before reporting).

---

# Validation appendix (5-agent panel)
| Validator | Verdict | Headline |
|---|---|---|
| Code-accuracy auditor | MAJOR_REVISION | Plan is accurate & concrete; blocker = T1.2 governing-law has nowhere to ride (RiskFinding has no jurisdiction field). |
| Feasibility / deadline | APPROVE_WITH_CHANGES | Right scope; blocker = gold is `input.tag`/no `metadata.jurisdiction`; UK source not fetchable; needs an explicit cut-list. |
| Arize-eval judge | MAJOR_REVISION | Map = 19/40 not 30–35; misses are `candidates[0]` + case-law form artifacts; de-circularization must add truly-off-map authority; κ measures the wrong thing. |
| M&A lawyer | APPROVE_WITH_CHANGES | §902 mapping & lease-bug correct; blocker = Akorn "only" receipt is false; jurisdiction switch must fail-closed; AB Stable provenance inconsistent. |
| Anti-overclaim critic | APPROVE_WITH_CHANGES | Guardrails strong; blocker = Hook 8 live overclaim + comparator manufactures a false-modesty 19/40; needs `run_mode`/MOCK label. |
