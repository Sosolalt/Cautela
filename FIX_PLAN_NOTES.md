# Fix Plan — Pre-flight Verification Notes

**Run**: 2026-06-08, before Fix 1 execution.
**Gates source**: `FIX_PLAN` Pre-flight section (5 gates V1–V5).
**Verifier agents**: 3 (code-claims, URL HEAD-check, contamination-evidence).
**Decision rule**: a fix may proceed only if its dependent gate(s) PASS.

---

## V1 — Arize MCP introspection-discard claim — **PASS**

`reflector.py:813` assigns `introspection_summary = _run_introspection_agent()`. The variable is **dead** — never read by `_failing_traces`, `_append_to_dataset`, `_generate_candidate_prompt`, `should_promote`, or the returned dict at line 860. An in-code comment at line 815-816 confirms it: *"deterministic SDK path — the source of truth for what we actually append to the regression set"*. `_failing_traces` is at line 537 (not 817; 817 is the call site) and independently calls `client.spans.get_spans_dataframe` at line 546.

**Implication**: Fix 5 (Arize MCP rewire) is in scope and well-defined. The work is real, not based on a hallucinated claim.

## V2 — calibrate.py Wilson pseudoreplication claim — **PASS**

`calibrate.py:295` reads `wilson_lb = wilson_lb_one_sided(total_hits, total_findings)` where `total_findings` (line 294) counts findings across folds — treating each finding as an independent Bernoulli trial. The cluster bootstrap `cluster_bootstrap_recall_ci` (line 145) explicitly treats **contracts** as the IID unit (line 172 resamples contracts, docstring says "findings within a contract are correlated"). The two estimators disagree on the IID unit. There is also a computed-but-unused `effective_n_contracts` at line 323 that does not flow into the Wilson call.

**Implication**: Fix 10 (stats cleanup) is in scope. The fix is small (wire `effective_n_contracts` into the Wilson call, OR relabel Wilson as exploratory).

## V3 — agents.py CrossReference reality claim — **PASS**

`agents.py:67-117` assembles `SequentialAgent("ma_gatekeeper", sub_agents=[parser, classifier, cross_reference, risk_judge])`. CrossReference (lines 100-105) is a real `LlmAgent` on `gemini-3-pro-preview` with `output_key="findings"`, prompted via `CROSS_REFERENCE_PROMPT` in `prompts.py:90+` to resolve definition→operative links and emit `cited_spans`. Not regex, not heuristic, not single-prompt. Caveat: cross-clause linkage is whatever the LLM reconstructs from inlined clause text; no graph-based retrieval.

**Implication**: Fix 6 (structural-reasoning demo beat) is **not architecturally blocked**. Whether it produces structure-conditional verdicts on demo prompts is empirically open and must be tested on Day 3.

## V4 — Deal-bank URL health — **PASS with 3 secondary breakages**

40 of 43 URLs return 200. The **5 Bucket-A allow-listed Ex 2.1 EDGAR URLs all 200** — live demo path is intact. Three secondary citations need replacement during Fix 1 or Fix 8:

| Bucket | What | Status | Fix |
|---|---|---|---|
| A | HPE/Juniper newsroom press release | 301 → generic HPE newsroom (deal page gone) | Replace with DOJ Final Judgment URL (already identified in V5 below) |
| B | Leagle / IBP-Tyson Strine opinion | 403 | Replace with Google Scholar or Casetext mirror |
| C | Chevron close 8-K (`eh250651090_8k.htm`) | 404 | Path is wrong; re-lookup accession for Chevron CIK 93410 close 8-K (Jul 2025) |

## V5 — Contamination concern — **CONFIRMED**

Gemini 3 Pro training cutoff = **January 2025** per the official DeepMind model card. All 11 famous busted-deal cases (Akorn, AB Stable, Tiffany, BMS/Celgene, Hexion, IBP/Tyson, Channel Medsystems, Forescout, SQL Solutions, Meso Scale, Cincom) predate the cutoff AND saturate publicly-indexed law-firm alerts (Skadden, Cleary, Jones Day, Cooley, Cadwalader, V&E, Weil, Milbank, Akin, Hogan Lovells, Faegre, ABA Business Law Today, Harvard CGI), Wikipedia, Quimbee, and casebook entries. Probability Gemini 3 Pro has memorized them ≈ 1.0. Internal-30 cannot be held-out as currently composed.

Three clean **post-cutoff** primary-source deals identified for Calibration-20 seed:
1. **HPE/Juniper DOJ Final Judgment** (Jun 28, 2025) — clean. URL: `https://www.sec.gov/Archives/edgar/data/0001043604/000119312525154400/d912160dex991.htm` (Juniper 8-K).
2. **Stabroek JOA arbitration ruling** (Jul 18, 2025) — clean. Primary: ICC press + CNBC + V&E analysis.
3. **Albertsons v. Kroger Chancery merits docket** (Jan 2025+) — borderline (complaint Dec 11 2024 pre-cutoff by ~3 wks); use the post-cutoff merits briefing and Kroger counterclaims, not the press-release narrative. Harvard CGI Jan 21 2025 practice-points note is post-cutoff.

**Implication**: Fix 1 (deal-bank split) MUST proceed. The cutoff date for the split is **2025-01-01**. Calibration-20 deals must have their load-bearing event date AFTER that.

---

## Gate decisions

| Fix | Depends on | Gate status | Proceed? |
|---|---|---|---|
| Fix 1 (split deal bank) | V5 | CONFIRMED | **YES** |
| Fix 2 (BMS cold open) | none (script-only) | — | **YES** |
| Fix 3 (climax voiceover) | none (script-only) | — | **YES** |
| Fix 4 (nuke 22s caption) | none | — | YES, runs with Fix 3 |
| Fix 5 (Arize MCP rewire) | V1 | PASS | YES, scheduled Day 2 |
| Fix 6 (structural-reasoning beat) | V3 + Day-3 empirical test | PASS architecturally; empirical TBD | Conditional, Day 3 |
| Fix 8 (cite cleanup) | V4 | PASS with 3 fixes | YES, folded into Fix 1 + Fix 8 |
| Fix 10 (stats cleanup) | V2 | PASS | YES, scheduled Day 1 |

No fix is blocked at pre-flight. Proceed to Fix 1.
