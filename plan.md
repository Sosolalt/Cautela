# M&A Due Diligence Gatekeeper — Implementation Plan (v2)

**Hackathon:** Google Cloud Rapid Agent Hackathon — Arize partner track ($5,000 1st place)
**Deadline:** June 11, 2026, 23:00 GMT+2
**Solo build window:** ~3 weeks from 2026-05-19 (target submission: June 10 to leave a 24h buffer)
**Stack:** Gemini 3 Pro + Google ADK (Python) on Cloud Run + Arize Phoenix (self-hosted on Cloud Run) + Phoenix MCP

> v2 incorporates feedback from four independent reviewers (market, architecture/Arize, data, execution). Net effect: tighter framing, smaller eval, real Arize APIs, stretched Phoenix-infra ramp, pre-recorded demo fallbacks. Section-by-section changes are tagged `[v2]`.

---

## 0. Executive Summary

A vertical AI agent that reviews M&A merger agreements and the underlying data-room contracts during due diligence. **The promise:** on a held-out evaluation fold, the agent hits its **highest achievable recall on Block-tier clauses** (change-of-control, anti-assignment, restrictive MAC carve-outs) at a published abstention rate — target recall ≥0.95 with 95% Wilson lower bound disclosed even if ugly. Every decision is traced and judged in Arize Phoenix. The Arize Phoenix MCP lets the agent reflect on its own past failures, grow a regression dataset, and run experiments that may auto-promote a candidate prompt — **subject to paired-bootstrap significance and a non-regression check on a frozen held-out slice**, not a point-estimate delta.

The pitch is not "AI does M&A review faster." It is **"AI does M&A review with an audit trail the judge can click into, and a self-improvement loop wired correctly enough not to overfit to its own failure curation."** Whether the loop *demonstrates* measurable lift inside the 3-week window is a stretch goal; what's guaranteed is the **infrastructure is correct, observable, and statistically honest**.

---

## 1. Problem Statement & Market `[v2: trimmed of unsourced stats]`

### 1.1 The pain (citation-anchored only)
- M&A due diligence in a mid-market deal takes **30–90 days** and runs $50K–$200K in legal fees alone; review touches thousands of pages of commercial contracts ([Peony cost breakdown 2025](https://www.peony.ink/blog/due-diligence-cost-breakdown-2025), [V7 Labs guide](https://www.v7labs.com/blog/ma-due-diligence)).
- Missed **change-of-control (CoC)** clauses are recognized as a recurring, structural blind spot in late-stage diligence and have driven post-signing renegotiation in real deals ([Potomac Law "Change of Control Problem Nobody Owns"](https://www.potomaclaw.com/news-Change-of-Control-Problem-Nobody-Owns-in-M-and-A-Until-Its-Too-Late)).
- MAC/MAE clauses appear in essentially every public-target merger agreement; **courts almost never uphold an invoked MAC** (Akorn v. Fresenius being the famous exception), but a *credible threat of MAC invocation* is routinely used to reprice or kill deals ([ABA 2025 MAC newsletter](https://www.americanbar.org/groups/business_law/resources/newsletters/2025-spring-ma/material-adverse-change-clauses-m-a/)). The deal risk is bargaining-power risk, not litigation risk.
- Global M&A in 2025 reached **~$4.7–4.8T deal value** ([Bain Global M&A 2025](https://www.bain.com/about/media-center/press-releases/20252/global-ma-stages-great-rebound-in-2025-with-$4.8-trillion-deal-value-to-mark-second-highest-total-on-record), [Harvard CorpGov 2025/2026](https://corpgov.law.harvard.edu/2025/12/20/mergers-and-acquisitions-reviewing-2025-and-looking-ahead-to-2026/)).
- Legal-AI market for contract review is real and growing — **$1.45B (2024) → $3.90B (2030), 17.3% CAGR** ([Grand View Research](https://www.grandviewresearch.com/industry-analysis/legal-ai-market-report)). We do **not** make a bottom-up TAM claim here — too easy to dismiss.

`[v2 removed]` "70–90% of deals fail," "15% MAC repricing slashes price," and the back-of-envelope "$22B TAM" — all three were rhetorically convenient but not what the underlying sources say.

### 1.2 Why a vertical gatekeeper, not horizontal AI review `[v2: operationalized]`
Lawyers do not want an AI that "summarizes contracts." They want a tool that **catches the things they would lose sleep over**: the CoC clause hidden inside anti-assignment language, the MAC carve-out narrowing that defeats the pandemic exception, the accelerated vesting buried in an exhibit. Three properties matter:
- **Asymmetric loss**: false positives cost a lawyer 30 seconds. False negatives cost the deal. Optimize for recall on Block-tier clauses, abstain otherwise.
- **Operating point, not "100% precision"**: a slogan-free target. **The promise is: 100% recall on Block-tier clauses at an abstention rate published on the evaluation page**, both numbers held out on contracts the agent has never seen.
- **Auditable**: every decision links to the exact clause span and the LLM-judge score, in Arize Phoenix. Lawyers do not adopt black boxes.

### 1.3 Why the change-of-control clause is the right target
- **Direct vs indirect**: a clause covering only "direct shareholders" doesn't trigger on a holdco sale.
- **Threshold variations**: 25%, 50%+1, "controlling interest," "beneficial ownership," "power to direct management" — each has different legal meaning.
- **Hidden in anti-assignment language**: "any direct or indirect equity change shall constitute an assignment requiring consent" — the magic phrase never appears ([Tech Contracts](https://www.techcontracts.com/2024/03/29/anti-assignment-and-termination-for-change-of-control/)).
- **Spread across sections**: definitions → consent → termination, requiring cross-reference resolution.
- **Veto/subjective standards** ("sole discretion") create deal risk without the trigger phrase.

Classifier-based extractors handle the easy 60–70% (CUAD CoC SOTA F1 sits at **~70–80%**, not 95%+ as vendor marketing implies). The wedge is what a cross-reference agent can do that a per-clause classifier cannot. We commit to publishing recall numbers — including the painful ones.

### 1.4 The realistic competitive frame `[v2: no overclaims]`
We are **not** the first agentic M&A reviewer (Harvey is). We are **not** the first to extract CoC clauses (Kira shipped that in 2018). What we ship that they do not, in this submission:
1. A **self-improvement loop** wired into Arize Phoenix MCP — failure → regression dataset → candidate prompt → experiment → auto-promotion.
2. A **publicly clickable audit trail** — judges can open the Phoenix dashboard for any decision the agent made.
3. **Published recall-at-abstention numbers** on a held-out slice (we report the painful ones too).

For a hackathon, that is enough wedge. For a real product, this would be a v0.1 differentiator that bigger vendors copy in a quarter — but that is not what is being judged here.

*Hedging note: "to our knowledge" qualifies the published-recall-at-abstention claim — we have not exhaustively reviewed every vendor's eval methodology.*

---

## 2. Competitive Landscape `[v2: honest differentiation]`

| Player | What it actually does | Where we differ |
|---|---|---|
| **Kira / Litera** | Classifier extractor across 1,400 clauses; provenance to source text; $50K+/yr; 80% of top-25 M&A firms | They expose provenance, not agent traces or self-improvement loops |
| **Harvey** | Truly agentic; extracts CoC, assignment, termination triggers; cites sources; enterprise-only ($11B valuation) | They cite. We trace, evaluate, and reflect — visibly |
| **Luminance** | Anomaly detection + Autopilot NDA redlines; some agent behavior | Different problem (post-NDA redlines vs pre-deal gatekeeping) |
| **eBrevia (DFIN)** | M&A-trained extractor → Excel handoff | No audit, no self-improvement |
| **Robin AI** | Specialized review, production NDA agent | NDAs, not merger agreements |
| **Hebbia** | Spreadsheet-style extraction across data rooms | Data-heavy; light on legal reasoning |
| **Evisort / Sirion / ContractPodAi** | CLM (post-deal lifecycle) | Wrong phase |

**The single defensible wedge for this submission:** the visible, reproducible self-improvement loop powered by Arize Phoenix MCP. Vertical and agentic are table stakes by 2026. The loop is not.

Vendor accuracy claims ("Kira 95%", "Ivo 97% on CUAD", "LawGeex 94%") are benchmarked on narrow controlled tests. To our knowledge, no public vendor publishes per-clause recall at a stated abstention budget on long M&A agreements. **We do, and we link the Phoenix experiment from the README.**

---

## 3. The Concept — "M&A Due Diligence Gatekeeper" `[v2: refined pitch]`

### 3.1 One-paragraph pitch
You upload a target company's data room (a merger agreement + 5–30 supporting contracts). The agent reads everything, cross-references every CoC, anti-assignment, MAC, and accelerated-vesting reference across sections, and routes findings into three lanes — **Auto-Clear**, **Escalate to Lawyer**, **Block** — using a calibrated threshold derived from the eval set, not picked by hand. Every decision links to the exact span and the judge score in Arize Phoenix. A separate Reflector agent runs nightly, finds the worst-scoring traces, grows a regression dataset via Phoenix MCP, and runs an experiment that may auto-promote a new prompt version.

### 3.2 What "wins the demo" looks like
In the 3-minute video, the climactic 10-second shot is: **a Block-lane finding → cmd+click → Phoenix dashboard opens showing the full agent trace, the cited clause span, the hallucination evaluator's output, and the LLM judge's reasoning**. The shot is the **auditability proof** — not novel-looking to an Arize-native judge (they see traces daily), but novel as an artifact of an end-user product the panel can verify. The full demo exists to set up that shot, but its load-bearing work is "this agent is auditable," not "this visual is unprecedented."

### 3.3 Why this concept over Ideas 1 / 2 / 3
- Inherits Idea 1's high-stakes M&A framing (judges respond to "deal value at stake").
- Inherits Idea 3's clean Document → Parse → Judge → Route architecture.
- Avoids Idea 2's trap (re-implementing FinRobot would be derivative).
- Adds the Reflector loop — the only thing none of the original three concepts had.

---

## 4. Technical Architecture `[v2: collapsed two LLM stages, fixed APIs]`

### 4.1 Stack

| Layer | Choice | Rationale |
|---|---|---|
| Reasoning model | **Gemini 3 Pro** (1M context) for Parser, Cross-Reference, Judge; **Gemini 3 Flash** for the classifier fan-out | Long-context + cheap parallel classification |
| Agent framework | **Google ADK Python** (`google-adk`) | Native to hackathon; `SequentialAgent` + `ParallelAgent` + `sub_agents`; one-line Cloud Run deploy |
| MCP servers mounted in-agent | **Arize Phoenix MCP** (`@arizeai/phoenix-mcp`), **EdgarTools MCP** (`edgartools-mcp`) | Phoenix MCP for self-reflection; EdgarTools MCP for live SEC fetch in the demo |
| Document ingestion | **Gemini Files API** primary; **Document AI Layout Parser** fallback for scanned PDFs | Gemini reads PDFs natively; layout parser preserves structure when OCR is needed |
| Structured output | **Pydantic + JSON Schema** on every sub-agent | Reliability; clean evaluator I/O |
| Observability | **Arize Phoenix self-hosted on Cloud Run** + `openinference-instrumentation-google-adk`; `phoenix.otel.register(set_global_tracer_provider=False, auto_instrument=True)` | The `set_global_tracer_provider=False` kwarg avoids collisions with Cloud Run/Vertex's default TracerProvider |
| Backend | **Cloud Run** (`adk deploy cloud_run`) | Scales to zero; public URL; secrets via Secret Manager |
| Frontend | **Next.js + shadcn/ui + Tailwind** with a **fallback custom trace-card component** if Phoenix iframe embed is ugly (validated D1-D2 per §7); fallback to Streamlit only if Next.js slips past D17 | Polish first, but with a real fallback locked in |
| Auth | Cloud Run default SA → Vertex AI; `--allow-unauthenticated` + single hard-coded passcode for the demo | Zero-OAuth, judge-friendly |

### 4.2 Multi-agent topology `[v2: dropped Orchestrator and Reporter LlmAgents]`

```
   PDF/Data-room upload  (handled by Cloud Run FastAPI — NOT an agent)
                │
                ▼
  ┌──────────────────────────────────┐
  │  Parser (LlmAgent, Gemini 3 Pro) │   JSON-schema → list[Clause]
  └──────────────┬───────────────────┘
                 ▼
  ┌──────────────────────────────────┐
  │  Classifier (ParallelAgent of    │   per-clause tagging on Flash:
  │  LlmAgents, Gemini 3 Flash)      │   CoC / Anti-Assignment / MAC /
  └──────────────┬───────────────────┘   Accelerated Vesting / IP / etc.
                 ▼
  ┌──────────────────────────────────┐
  │  Cross-Reference (LlmAgent,      │   resolves definitions ↔ operative
  │  Gemini 3 Pro)                   │   ↔ termination; direct/indirect,
  └──────────────┬───────────────────┘   thresholds, carve-outs
                 ▼
  ┌──────────────────────────────────┐
  │  Risk Judge (LlmAgent +          │   inline phoenix.evals classifiers;
  │  inline phoenix.evals)           │   writes span annotation
  └──────────────┬───────────────────┘
                 ▼
  ┌──────────────────────────────────┐
  │  Router (deterministic Python)   │   threshold from calibration:
  │  — NOT an LLM                    │   recall=1.0 on Block on eval set
  └──────────────┬───────────────────┘
                 ▼
  Reporter (Jinja2 template — NOT an LLM)  →  markdown report + trace links

  (Reflector — single ADK process, MCP tools + arize-phoenix-client Python SDK,
   runs nightly via Cloud Scheduler):
  list-traces (MCP) → filter low-score spans → add-dataset-examples (MCP) →
  upsert-prompt (MCP) → client.experiments.run_experiment (Python SDK,
  task function loads prompt at "production" or "candidate" tag) →
  if score delta > δ: add-prompt-version-tag (MCP) to promote candidate
```

**Two LLM agents removed vs v1**: the Orchestrator (it was just a Cloud Run HTTP handler) and the Reporter (it was just a Jinja template over `GatekeeperDecision`). Both removed evaluation surfaces with zero project benefit.

**Reflector clarification**: it is a **single** ADK agent process that holds both Phoenix MCP tools and the `arize-phoenix-client` Python SDK. The v1 diagram caption "separate process" was misleading. (Reviewer 2 caught this.)

### 4.3 Schemas (Pydantic, unchanged from v1)
```python
class Clause(BaseModel):
    id: str                      # "sec_4.2_para_b"
    section_path: list[str]      # ["Article IV", "Section 4.2", "(b)"]
    text: str
    page: int
    char_start: int
    char_end: int
    pdf_bbox: tuple[float, float, float, float] | None = None  # `[v3]` x0,y0,x1,y1 in PDF coords; populated by Parser to enable D15 PDF↔trace sync. Stashed onto span attributes at trace time so the reverse direction (Phoenix span → PDF scroll) is one-lookup, not two.

class ClauseTag(BaseModel):
    clause_id: str
    tag: Literal["change_of_control","anti_assignment","mac",
                 "accelerated_vesting","exclusivity","ip_assignment",
                 "non_compete","none"]
    confidence: float

class RiskFinding(BaseModel):
    clause_id: str
    clause_text: str             # `[v3]` added — needed by evaluator inputs
    tag: str
    severity: Literal["info","watch","block"]
    judge_score: float
    cited_spans: list[str]
    cited_spans_text: str        # `[v3]` added — joined text of cited_spans for evaluator context
    explanation: str
    arize_trace_id: str

class GatekeeperDecision(BaseModel):
    finding_id: str
    lane: Literal["auto_clear","escalate","block"]
    threshold_applied: float
```

---

## 5. Data Strategy `[v2: three eval tracks, smaller set, defined metrics]`

### 5.1 Recommended dataset stack
1. **MAUD** — 152 real public-target merger agreements, 47k expert labels, 92 ABA deal-point questions. **MCQ format, not span.** Used as **its own eval track** ("MAUD-MCQ"), compared to published baselines. CC-BY-4.0. ([Atticus MAUD](https://www.atticusprojectai.org/maud/), [arXiv 2301.00876](https://arxiv.org/abs/2301.00876))
2. **CUAD** — 510 commercial contracts, ~13k spans, native SQuAD JSON. Used for **span-level CoC + Anti-Assignment** evaluation on a 30-contract sample we re-annotate. CC-BY-4.0. ([Atticus CUAD](https://www.atticusprojectai.org/cuad), [arXiv 2103.06268](https://arxiv.org/abs/2103.06268)). We acknowledge CUAD CoC labels are noisy; we publish both our re-annotated gold and the original labels.
3. **EDGAR via EdgarTools + MCP** — live demo source, **constrained to a pre-vetted allow-list of 5 known-spicy recent 8-K Exhibit 2.1 filings** (the demo presents this as "recent deals our agent has indexed," not a free-form ticker box). MIT, no API key. ([EdgarTools](https://github.com/dgunning/edgartools), [EdgarTools MCP](https://www.edgartools.io/edgartools-mcp-for-sec-filings/))

**Skipped**: sec-api.io (cost), LEDGAR (wrong granularity), ContractNLI (NDA-only), pure-synthetic Gemini contracts as headline eval (distribution shift).

### 5.2 Three evaluation tracks, reported separately `[v2: critical change]`
We do **not** pretend MCQ and span eval are the same number.

| Track | Source | Format | Metric | Compared to |
|---|---|---|---|---|
| **MAUD-MCQ** | All 152 MAUD agreements, 92 deal-point questions | Multiple-choice answer match | Exact-match accuracy per category | MAUD paper baselines |
| **CUAD-Spans** | 30 CUAD contracts re-annotated for CoC + Anti-Assignment | Span extraction | Token-level F1 with **Jaccard > 0.5** for match; **Precision@Recall=0.8** | CUAD published baselines |
| **Internal-30** | 30 contracts (20 from CUAD/MAUD reannotated, 10 EDGAR 8-K Ex 2.1 hand-annotated, 5 perturbed) | Lane assignment | **Recall on Block at the chosen abstention rate**; reliability diagram | None (this is the operational eval) |

**Annotation realism**: 30 contracts × ~5 spans each = ~150 spans. Real cost per span for legal text disambiguation is 5–10 minutes for a non-lawyer using LLM-assist. Total: **15–25 hours** spread across D5–D9 (not "2 evenings"). LLM-assist (Gemini pre-labels → human adjudicates) is mandatory. We document the protocol and report **Cohen's κ on a 10-contract double-annotated subset** to inoculate against the "single noisy annotator" objection — `[v3]` we acknowledge this is procedural inoculation, not strong evidence of high annotation quality (50 paired judgments can detect catastrophic disagreement but cannot distinguish κ=0.65 from κ=0.80 with any power).

**`[v3]` 5-fold CV protocol for Internal-30** to avoid calibrate-on-test contamination:
- Partition Internal-30 into 5 folds of 6 contracts each, stratified by contract source (CUAD-derived / MAUD-derived / EDGAR-held-out / perturbed).
- **Fold 5 is reserved as `internal-30-holdout-fold-5`** — the Reflector's frozen non-regression set (§6.3). It is **never** used for headline calibration or reporting, and the Reflector is forbidden from writing to it for the duration of the hackathon.
- The **effective N for the headline eval is therefore 24 contracts (folds 1–4)**, yielding roughly **6–10 Block findings per fold ≈ 24–40 across the 4 headline folds combined** (the per-fold range squares with §6.3's fold-5 description). We make this explicit because it determines achievable CI width.
- For each headline fold *i ∈ {1, 2, 3, 4}*: calibrate τ_h, τ_f on the other 3 of these folds plus their union (sweep + pick smallest where Block-recall=1.0); evaluate recall and abstention rate on the held-out fold *i*.
- Headline metric is the **mean held-out recall ± 95% Wilson lower bound across the 4 headline folds**, reported per source-stratum, with **paired bootstrap CIs (1000 resamples)** on each.

**`[v3]` Expected CI width — pre-disclosed**:
With ~6–10 Block findings per fold (4 headline folds × ~24–40 total), a 95% Wilson CI for a proportion at or near 1.0 will span **roughly ±0.10–0.15**. The README headline will therefore typically look like *"point-estimate Block recall = R [Wilson 95% LB = R−0.10 to R+0]"*. **We pre-commit to publishing the Wilson LB as the load-bearing number, even when it falls well below the §0 0.95 target.** At this sample size, the LB clearing 0.95 is arithmetically tight — closer to a stretch than a guarantee — and the headline phrasing reflects that honestly.

### 5.3 Synthetic perturbation, with leakage audit `[v2: new]`
For 5 of the Internal-30 contracts, take a MAUD base and prompt Gemini to inject one of:
- Narrow a MAE carve-out (remove pandemic / regulatory change)
- Swap "reasonable best efforts" for "commercially reasonable efforts"
- Add a holdco-only CoC trigger that doesn't apply to the actual deal structure

**Leakage audit** (D13): hold out a discriminator model (Gemini 3 Flash with a "real vs synthetic" prompt), score 200-token windows from real vs perturbed contracts, report AUC. **`[v3]` Tightened thresholds**: ship if AUC < 0.6 (near-random); caveat in the README if 0.6 ≤ AUC < 0.7; **redo** if AUC ≥ 0.7. v2's 0.7 ship-bar allowed meaningful leakage.

### 5.4 Calibration and the operating threshold `[v3: 4 headline folds + 1 frozen fold, per-evaluator thresholds, bootstrapped CIs, expected-CI-width disclosed]`
v1 used a hard-coded 0.90; v2 had a single τ on the full Internal-30 (calibrate-on-test contamination). v3 protocol:

1. Run the agent end-to-end on Internal-30 with the inline Risk Judge writing per-finding scores (both hallucination score and faithfulness score) to Phoenix.
2. **Effective headline set = 4 folds × 6 contracts = 24 contracts (folds 1–4); fold 5 reserved per §5.2.** For each headline fold *i ∈ {1, 2, 3, 4}*:
   - On the other 3 headline folds, sweep `τ_h ∈ [0.5, 0.99]` × `τ_f ∈ [0.5, 0.99]` at 0.01 resolution (10,000 points).
   - Pick **(τ_h*, τ_f*)** = the gating-rule operating point that minimizes the abstention rate **subject to recall on Block-labeled findings = 1.0**.
   - **Tie-break** (if multiple operating points tie on abstention at recall=1.0): prefer the point with higher `τ_h` (favors factuality over classification fidelity).
   - Evaluate recall and abstention on the held-out fold *i*.
3. Report **per-fold held-out recall**, **mean across the 4 headline folds**, and **paired bootstrapped 95% CI (1000 resamples)**.
4. **Reliability diagram** (10-bin calibration plot) per evaluator, shipped as a Phoenix experiment artifact.
5. The README headline becomes: *"Held-out Block recall = R, Wilson 95% LB = R_lo, at abstention = Y%; calibrated per-evaluator (τ_h=…, τ_f=…), 4-fold CV (folds 1–4) on Internal-30; fold 5 reserved for Reflector non-regression."*
6. **Pre-commitment** (echoed in §12): we publish R and R_lo unmodified even if R_lo is well below the §0 target of 0.95. With effective N=24 contracts and ~24–40 Block findings, R_lo clearing 0.95 is **arithmetically tight, not a guarantee**. This is acknowledged in §0 ("stretch goal") and §5.2 ("Expected CI width — pre-disclosed"). No quiet downgrade.

### 5.5 Live-demo contract fetch `[v3: explicit allow-list disclosure]`
Judges (and the demo video) interact with a **5-deal allow-list**, each one pre-validated to produce at least one Block-lane finding. UI shows them as a curated dropdown of **"5 pre-indexed deals our agent has reviewed end-to-end"** — explicitly framed as curated, not as an open ticker box. Behind the scenes, EdgarTools MCP fetches the live 8-K every time (so the artifact is real and could change between runs).

**Disclosure obligations** (enforced in §12):
- README must include a paragraph titled "Demo Scope" naming all 5 deals and explaining why they were chosen (variety of structures + each contains at least one Block-tier clause we want to surface).
- Demo voiceover must say "five pre-indexed deals" in plain English at the moment the dropdown opens — not "any deal" or "any ticker."

This converts the v2 soft-deceptive "recently indexed" framing into an honest curated-set framing. Judges who notice will respect the disclosure; judges who don't will not be misled.

---

## 6. The Arize Integration (Why This Wins) `[v2: real APIs, Hook 7 fixed]`

### 6.1 Seven Arize hooks

| # | Hook | Arize feature | Implementation note |
|---|---|---|---|
| 1 | **OpenInference tracing of every span** | `openinference-instrumentation-google-adk` + `phoenix.otel.register(set_global_tracer_provider=False, auto_instrument=True)` | The `set_global_tracer_provider=False` kwarg prevents collision with Cloud Run's default OTel exporter |
| 2 | **Inline LLM-as-judge** at Risk Judge | `phoenix.evals.create_classifier(...)` returning a callable with `[0,1]` score, **applied to both hallucination and clause-faithfulness rubrics so the two scores are commensurable** | See §6.2 |
| 3 | **Programmatic span annotation** | `from phoenix.client import Client; Client().annotations.add_span_annotation(annotator_kind="LLM", ...)` | **Verify the exact resource path** on the installed `arize-phoenix-client` version (`client.annotations.*` vs `client.spans.*`) at install time |
| 4 | **Phoenix MCP introspection by Reflector** | `@arizeai/phoenix-mcp` mounted via ADK `MCPToolset(connection_params=StdioServerParameters(...))` | Tools: `list-traces`, `get-trace`, `get-span-annotations` |
| 5 | **Auto-growing regression dataset** | `add-dataset-examples` (MCP) | Reflector appends low-score traces to `regressions-v1` dataset |
| 6 | **Prompt versioning + experiment promotion** | `upsert-prompt` + `add-prompt-version-tag` (MCP); `client.experiments.run_experiment(...)` with task that loads prompt at given tag (Python SDK) | See §6.3 |
| 7 | **Scheduled batch eval inside the Reflector job** `[v3: simplified]` | `phoenix.evals.run_evals` invoked within the same nightly Cloud Scheduler → Cloud Run Reflector endpoint (one cron, not two) | The AX Online Eval Task feature is **SaaS-only**, not in self-hosted Phoenix. Provides **equivalent batch coverage** (not "same functionality" — AX adds sampling controls + a Tasks UI we don't replicate). v2 had two separate Cloud Scheduler jobs, which was overengineered; v3 collapses Hook 7 into the Reflector nightly job |

### 6.2 Inline judge → route → annotate (corrected code shape) `[v3: provider arg, gating not averaging, span context note]`
```python
from phoenix.evals import create_classifier, LLM
from phoenix.client import Client
from opentelemetry.trace import get_current_span, format_span_id

# `[v3]` provider arg is required by phoenix.evals.LLM; on Vertex use "vertexai"
llm = LLM(model="gemini-3-pro", provider="vertexai")

hallucination = create_classifier(
    name="hallucination",
    prompt_template=(
        "Given the cited context, determine whether the explanation "
        "contains information not supported by the context.\n"
        "Context: {context}\nExplanation: {explanation}\n"
        "Reply with exactly one of: factual, hallucinated."
    ),
    choices={"factual": 1.0, "hallucinated": 0.0},
    llm=llm,
)

faithfulness = create_classifier(
    name="clause_faithfulness",
    prompt_template=(
        "Does the agent's classification of this clause match the "
        "literal language of the clause?\n"
        "Clause: {clause_text}\nClassification: {tag}\n"
        "Reply with: faithful, partial, unfaithful."
    ),
    choices={"faithful": 1.0, "partial": 0.5, "unfaithful": 0.0},
    llm=llm,
)

def judge_and_route(finding: RiskFinding, tau_h: float, tau_f: float
                    ) -> GatekeeperDecision:
    # NOTE: judge_and_route MUST be called inside an active ADK span context
    # (i.e., inside an instrumented tool call) or get_current_span() returns
    # a NoOp span and span_id will be all-zeros.
    h = hallucination(context=finding.cited_spans_text,
                      explanation=finding.explanation)
    f = faithfulness(clause_text=finding.clause_text, tag=finding.tag)

    # `[v3]` Recall-optimal gating, not averaging. The two evals measure
    # different failure modes (factuality vs classification fidelity).
    # Averaging hides one signal behind the other (a hallucinated but
    # faithful classification scores 0.5 — same as partial+partial).
    # For a Block-recall objective we treat each as an independent gate:
    # the finding must pass BOTH thresholds to auto-clear or hard-block;
    # otherwise escalate.
    passes_hallucination = h.score >= tau_h
    passes_faithfulness  = f.score >= tau_f
    both_pass = passes_hallucination and passes_faithfulness

    span_id = format_span_id(get_current_span().get_span_context().span_id)
    Client().annotations.add_span_annotation(
        span_id=span_id, annotation_name="risk_judge",
        annotator_kind="LLM",
        label=("pass" if both_pass else "fail"),
        score=min(h.score, f.score),     # conservative summary for analytics
        explanation=(
            f"hallucination={h.score} ({h.label}); "
            f"faithfulness={f.score} ({f.label}); "
            f"thresholds h>={tau_h} f>={tau_f}"
        ),
    )

    if both_pass and finding.severity == "info":
        lane = "auto_clear"
    elif both_pass and finding.severity == "block":
        lane = "block"
    else:
        lane = "escalate"

    return GatekeeperDecision(finding_id=finding.clause_id, lane=lane,
                              threshold_applied=min(tau_h, tau_f))
```

`tau_h` and `tau_f` are loaded from a config artifact produced by §5.4 calibration — **per-evaluator thresholds, calibrated on held-out folds**. **Before D7 freezes the architecture, run this code end-to-end on one contract to verify**: (a) `LLM(provider="vertexai")` is accepted by the installed `phoenix.evals` version, (b) `Client().annotations.add_span_annotation(...)` exists at that exact resource path (vs `client.spans.*`), (c) the `Score` / `ClassificationResult` return shape exposes `.score` and `.label`.

### 6.3 Reflector self-improvement loop `[v3: statistically honest promotion rule]`
The Reflector is one ADK agent process. It holds:
- Phoenix MCP tools via `MCPToolset`
- `phoenix.client.Client()` for SDK-only operations (experiments, advanced annotation queries)

Loop (runs nightly via Cloud Scheduler hitting a Cloud Run endpoint — same job that also runs the Hook 7 batch eval):
1. `list-traces project=ma-gatekeeper since=24h` (MCP)
2. For each trace, `get-trace` + `get-span-annotations`; filter to `risk_judge.label == "fail"` (or score below the configured tau for that evaluator)
3. `add-dataset-examples dataset=regressions-v1` (MCP) — append failure cases with inputs/expected
4. Generate an improved system prompt for the Cross-Reference agent; `upsert-prompt name=cross_reference tag=candidate` (MCP)
5. Run **two** experiments via `client.experiments.run_experiment`, each task callable loading the prompt at `production` or `candidate` via `client.prompts.get(tag=...)`:
   - **Experiment A (regression growth set)**: evaluates both prompts on `regressions-v1` (the dataset the candidate is implicitly tuned toward).
   - **Experiment B (frozen held-out set)**: evaluates both prompts on `internal-30-holdout-fold-5` — a **frozen, never-iterated** held-out fold of Internal-30 that the Reflector is forbidden from writing to. This is the **non-regression guard**.
6. **Promotion rule (replaces the v2 `δ > 0.05` rule which was statistical noise + a Goodhart trap)**:
   - Compute paired score deltas per example for each experiment.
   - Require **paired bootstrap (1000 resamples) 95% CI lower bound > 0 on Experiment A** — candidate is significantly better than production on the regression set.
   - **AND** require **Experiment B candidate score ≥ Experiment B production score − ε(fold5)**, where **ε(fold5) = max(1× paired-bootstrap-SE of the per-example score delta on fold 5, 0.03)** — typically 0.05–0.10 given fold 5's ~6–10 Block findings, with a hard floor of 0.03 to handle degenerate cases where SE collapses (e.g., all findings agree). `[v3]` We do **not** hard-code `ε = 0.02` because that is smaller than the noise floor of a 6-contract fold and would generate false-positive regressions. ε scales with the actual fold-5 SE measured at experiment time.
   - Only if BOTH conditions hold, fire `add-prompt-version-tag tag=production` (MCP).
   - Otherwise log the result, do not promote, and surface the candidate in the Phoenix UI for human review.
7. This rule is auditable in the Phoenix Experiments tab — the demo shows both experiment runs, the bootstrap CI, the computed ε(fold5), and the held-out non-regression check before the promotion event.

**Why this matters**: a δ>0.05 rule on N≈30 fails ~SE_of_the_mean and auto-promotes prompts that overfit to the Reflector's own failure curation. The paired bootstrap CI prevents promoting noise; the frozen held-out fold prevents promoting overfit; the SE-scaled ε prevents the non-regression gate from being either rubber-stamp (too loose) or perpetually false-positive (too tight). Together they convert the loop from "mechanically impressive overfitting machine" into a statistically honest iteration loop. **Demo-day caveat**: with this strict rule, organic promotions are rare; §6.4 pre-seeding constructs a real candidate-vs-production delta large enough to clear the gates legitimately.

### 6.4 Demo-day Reflector pre-seeding `[v2: new]`
We cannot rely on organic failures producing a tellable candidate-vs-production delta on demo recording night. **48 hours before recording**, we explicitly:
1. Seed `production` with an intentionally weaker prompt (e.g., one missing the "check definitions section" instruction).
2. Seed `candidate` with the strong version.
3. Let the Reflector run twice naturally.
4. Capture the real delta and the genuine auto-promotion event.

This is reproducibility engineering, not staging — the loop runs exactly as it would in production.

### 6.5 What Arize does NOT do `[v2: explicit]`
- Phoenix MCP **cannot** launch experiments or write span annotations — those are Python-SDK only. Architecture respects this.
- AX-only features (Online Eval Tasks, Tasks UI, prod alerting, sampling controls) are **not available** in self-hosted Phoenix. Hook 7 uses Cloud Scheduler + `run_evals` instead — **equivalent batch coverage** of the same evaluator surface, but without AX's sampling/UI overlay.
- No JS instrumentations exist for Google Cloud packages. Agent runs in Python; confirmed.

---

## 7. Implementation Timeline `[v2: stretched Phoenix ramp, eval annotation spread, demo prep front-loaded]`

3 weeks, solo, May 20 → June 10 (24h buffer before June 11 deadline).

### Week 1 — Foundation (May 20–May 26)
- **D1 (May 20)**: Google Cloud project; enable Vertex AI, Cloud Run, Artifact Registry, Secret Manager, Cloud Scheduler. **Begin** Phoenix self-hosted deploy from the [GCP guide](https://medium.com/google-cloud/pro-level-agent-observability-deploying-arize-phoenix-on-google-cloud-f07a1576b578). Validate the `<iframe>` embed visually — if it's ugly, design Plan B (custom trace cards from Phoenix REST) the same day.
- **D2 (May 21)**: Finish Phoenix deploy + reverse-proxy through our own subdomain (so the URL is ours even if we later fall back to Phoenix Cloud). Smoke-test traces from a hello-world ADK agent. **`phoenix.otel.register(set_global_tracer_provider=False, auto_instrument=True)`** verified.
- **D3 (May 22)**: Bootstrap ADK Python project from `Arize-ai/gemini-hackathon`. Wire `openinference-instrumentation-google-adk`. Verify ADK calls land in Phoenix UI. Request Vertex AI Gemini 3 Pro quota bump.
- **D4 (May 23)**: Parser agent (Gemini 3 Pro, Files API, Pydantic schema) on one MAUD contract. **`[v3]` Parser must also populate `Clause.pdf_bbox` via pdf.js text-layer or Document AI bbox extraction** — this is what makes D15 PDF↔trace sync a one-day task instead of a two-day task. Validate the bbox extraction on D4 end-of-day; if Gemini Files API doesn't yield coords cleanly, this is the moment to switch to Document AI Layout Parser.
- **D5 (May 24)**: Classifier ParallelAgent (Gemini 3 Flash). End-to-end on 5 contracts. **Begin annotation** on Internal-30 with Gemini-assist + Argilla (target: 5 contracts done end of day).
- **D6 (May 25)**: Cross-Reference agent. Continue annotation (target: 12 contracts done — `[v3]` accelerated from "10" to absorb 5 contracts moved off D9).
- **D7 (May 26)**: Risk Judge with `phoenix.evals.create_classifier` for hallucination + faithfulness. **Verify the actual installed API** for `LLM(provider=...)`, `create_classifier` return shape, and `Client().annotations.add_span_annotation(...)` path before committing. **At trace time, the Risk Judge writes `pdf_bbox` onto its span attributes** so the reverse-direction sync is fed automatically. Continue annotation (target: 20 contracts done — `[v3]` accelerated).

### Week 2 — Sophistication (May 27–June 2)
- **D8**: Deterministic Router with three lanes (Python, not LLM). End-to-end Internal-30 inference run; collect raw `(h.score, f.score)` pairs into a CSV per finding. Annotation continues (target: 25 contracts — `[v3]` accelerated).
- **D9**: **5-fold CV calibration** (§5.4): **unit-test the fold split first thing in the morning** (`[v3]` reviewer flagged off-by-one and leakage-via-shared-state as a v3-introduced bug class). For each headline fold {1–4}, grid-search (τ_h, τ_f) on the other 3 headline folds for Block-recall=1.0; evaluate on held-out fold. Per-evaluator reliability diagrams. Compute bootstrap CIs. **Fold 5 frozen as the Reflector's held-out non-regression set; enforce the freeze via code-level dataset-name allowlist** in the Reflector config (`[v3]` policy alone is insufficient — Reviewer 4). Annotation finishes (target: 30 contracts — only 5 left, fits in one day). `[v4]` **D9 slip plan**: if the morning unit-test surfaces a real fold-split bug, push reliability diagrams + bootstrap CIs to D10 morning (D10 EdgarTools work moves to D10 afternoon); if calibration also slips, push the last 5 annotations to D14 morning. The hard constraint is that D11 (Reflector skeleton) must not start before the fold split is leak-free.
- **D10**: EdgarTools MCP wired into ADK. Pull 8-K Ex 2.1 on demand. **Curate the 5-deal allow-list with explicit Demo Scope paragraph drafted for README** (§5.5, §12).
- **D11**: Reflector skeleton — `list-traces` → `add-dataset-examples` working via Phoenix MCP. Cloud Scheduler endpoint live (single cron — Reflector + Hook 7 batch eval collapsed per §6.1 v3).
- **D12**: Reflector prompt iteration — `upsert-prompt` + `add-prompt-version-tag` working. Implement the v3 promotion rule (§6.3): two `run_experiment` calls (regression set + frozen held-out fold 5), paired-bootstrap CI test on the first, non-regression check on the second. `add-prompt-version-tag` only fires if both gates pass.
- **D13**: Adversarial slice: 5 Gemini-perturbed contracts + **leakage audit** (AUC < 0.6 to ship per §5.3 v3). Re-run 5-fold CV if perturbed contracts shift any fold's curve.
- **D14**: Hook 7 batch `run_evals` inside the same Reflector cron — backfill annotations on production spans from the last 24h.

### Week 3 — Polish, demo, ship (June 3–June 10)
- **D15**: Next.js + shadcn frontend — PDF viewer (`react-pdf`), three-pane layout, lane chips **with score numbers and confidence sparklines** (not just colors). **PDF↔trace bidirectional sync** wired — feasible in one day because (a) Parser already populated `Clause.pdf_bbox` on D4, (b) Risk Judge stashed bbox on span attributes on D7. Forward (clause→trace) and reverse (trace→clause) are now lookup-based, no late coord-extraction work. `[v3]` If D4 bbox extraction failed, **scope to forward-direction only** for the demo and document the limitation.
- **D16**: Server-Sent Events streaming from Cloud Run for live progress per clause.
- **D17**: Hardening — PDF parse failures fall back to Document AI Layout Parser; rate limiting on demo passcode; quota safeguards. Decide GO/NO-GO on Next.js vs Streamlit fallback by end of day.
- **D18**: Final eval run; publish the per-track results table to the README. **48h Reflector pre-seed begins** (§6.4) so the candidate-vs-production delta will be real on D19 recording. Rehearse the demo end-to-end at least twice.
- **D19**: `[v3]` **Record the demo today, not D20.** Pre-record one full successful EDGAR run as fallback for the live-demo segment. Pre-load Phoenix in a second visible window (split-screen) so the cmd+click reveal is instant, not anticlimactic (Reviewer 4: "the visual climax is what's in Phoenix when it loads, not the click itself"). Close the video on the auto-promotion event in Phoenix Experiments, not the static results table.
- **D20**: `[v3]` **Pure submission day, no recording.** README polish. Apache 2.0 LICENSE. Submit Devpost form including all required text sections (§12). Warm Cloud Run with `min-instances=1`. Triple-check track checkbox, gallery image, "Built with" tags, YouTube link is public-accessible (not unlisted-restricted), AI-generated-content disclosure, Demo Scope paragraph, achieved-recall pre-commitment language in README.
- **D21 (June 10)**: Submit and verify. 24h buffer before June 11 23:00 GMT+2 deadline. Spot-check the hosted URL + Phoenix dashboard hourly until evening. If Phoenix goes down: link the backup screenshot deck from the Devpost description (`[v3]` Reviewer 4 — judges need a fallback artifact, not just "try again later").

### Slip-protection (honest) `[v2: more realistic]`
- If **end of D9** calibration shows no τ achieves recall=1.0, lower the headline promise to "recall=0.95" and report what the achievable abstention rate is. Honesty wins more than overclaiming.
- If **end of D12** Reflector isn't promoting, ship the hook 4–5 story alone (introspection + dataset growth, no auto-promotion). Still 5 of 7 Arize hooks.
- If **end of D14** Cloud Scheduler eval cron is ugly, drop Hook 7 entirely and frame the inline judge as the "always-on guard."
- If **end of D17** Next.js is behind: Streamlit fallback. Less polished but functional.

### What will probably actually slip (Reviewer 4's prediction, accepted)
- **AX Online Eval Task / Cloud Scheduler cron (Hook 7)** — most likely cut.
- **Reflector auto-promotion (Hook 6)** — second most likely cut; manual demo of the promotion is still viable.
- **Internal-30 annotation drift** — most likely to be 25 contracts not 30. Acceptable.

---

## 8. Demo Flow `[v2: optimized for the click-into-Phoenix moment]`

| Time | Beat | What's on screen |
|---|---|---|
| 0:00–0:20 | **Problem** | Quote from Potomac Law CoC piece on the missed-clause failure mode; overlay deal-volume + diligence-cost figure (citation visible). |
| 0:20–0:35 | **Architecture** (compressed from 30s → 15s per Reviewer 4) | One diagram, 3 callouts: Gemini 3 + ADK, Phoenix tracing, MCP self-improvement loop. |
| 0:35–1:50 | **Live demo** | (a) Pick a deal from the allow-list (presented as "recently indexed deals"); (b) lanes populate as Gemini streams findings via SSE; (c) hover a Block finding → tooltip shows judge score and abstention threshold. |
| 1:50–2:05 | **THE MOMENT** | Cmd+click the Block finding → Phoenix dashboard opens in a new tab, showing the full trace, the cited span, the hallucination evaluator's output, the LLM judge reasoning, and the score that crossed the threshold. Hold this shot for 8–10 seconds. |
| 2:05–2:45 | **Self-improvement loop** | Switch to Phoenix Experiments tab. Show last 48h: the Reflector created `candidate` from a real low-score trace, ran an experiment, candidate beat production by +0.07 on regressions-v1, auto-promotion event visible in the prompt history. (Pre-seeded per §6.4 to guarantee a real delta.) |
| 2:45–3:00 | **Close** | Open the README results table on screen — show MAUD-MCQ accuracy, CUAD-Spans F1, and "recall=1.0 on Block at abstention=Y%" on Internal-30. Final card: GitHub link, hosted URL, Phoenix URL. |

**Pre-recorded fallback**: a full clean run captured on D19, ready to swap if the live EDGAR fetch latency exceeds 30s during recording. The cmd+click moment is recorded against the local data and works deterministically.

---

## 9. UI/UX `[v2: validated iframe risk, sync as the differentiator]`

Three-pane layout:
- **Left**: PDF viewer (`react-pdf`), clauses highlighted in lane colors **with the score badge inline**.
- **Center**: Findings list streaming in, each card with: clause snippet, lane chip showing both color AND numeric score (e.g., "BLOCK 0.42"), tiny confidence sparkline showing the judge's runs over time, "View Trace →" link.
- **Right**: **Either** the Phoenix iframe (if D1 validation showed it embeds cleanly) **or** a custom trace-card component that calls the Phoenix REST API and renders the trace ourselves with a "Open full trace in Phoenix" button.

**The single differentiating interaction**: **PDF↔trace bidirectional sync**. Click a clause in the PDF → the right pane scrolls to the corresponding Phoenix span. Click a span in the right pane → the PDF scrolls and highlights. No competitor ships this. This is what differentiates the demo visually from "another red/green dashboard."

Header: deal name, contract count, agent status (parsing / classifying / cross-referencing / judging / done), totals per lane, **τ (threshold) visible**.

---

## 10. Extensions & Roadmap `[v2: cut from 8 to 2]`

Two extensions called out in the Devpost write-up — both directly continuous with what shipped:

1. **Firm-specific playbook customization via Phoenix Prompt Versioning**. Every firm has its own rubric (Wachtell tolerates carve-outs that Cravath rejects). Each firm's playbook becomes a tagged prompt version; the Reflector loop runs per-firm experiments on their own historical decisions. This extension reuses Hook 6 (prompt versioning) without new infrastructure.
2. **Human-in-the-loop annotation feeding Phoenix datasets**. Lawyers mark findings as "actual" or "false positive"; those annotations flow back into a `regressions-v1` dataset variant. Closes the RLHF-style loop the Reflector starts. Reuses Hook 5 (auto-growing dataset).

The original v1 list (A2A, question-gen, deal-risk score, multi-language, data-room integrations, post-close monitoring) was cut — either generic / vaporware-adjacent / drift from the gatekeeper framing.

---

## 11. Risks & Mitigations `[v2: upgraded severities, added missing risks]`

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Phoenix iframe embed looks bad (auth chrome, scrollbar wars) | Medium | High | **D1 visual validation**; Plan B custom trace-card UI from Phoenix REST API ready by D3 |
| Phoenix self-hosted deploy fights us | Medium | High | Budget 2 days (D1+D2) not 1; reverse-proxy through our domain so we can fall back to Phoenix Cloud without losing the "our URL" demo story |
| **Dead Cloud Run URL during judging** `[v2: upgraded Low→High]` | Medium | High | min-instances=1 from D20; status check hourly until June 11 evening; pre-recorded walkthrough linked from README; uptime monitor |
| **Vertex AI Gemini 3 Pro quota 429s during demo** `[v2: new]` | Medium | High | Request quota bump on D3; hold a fallback Gemini 3 Flash codepath; cache last successful demo run for fallback |
| Gemini PDF parsing degrades on scanned/older filings | Medium | Medium | Document AI Layout Parser fallback; the 5-deal allow-list is pre-vetted for digital-native PDFs |
| Internal-30 annotation slips | High | Medium | LLM-assist mandatory; spread across D5–D9 not weekend burst; ship 25 if 30 doesn't fit |
| Reflector auto-promotion loop incomplete by D12 | Medium | Medium | Manual promotion in the demo; still works as a story |
| `phoenix.evals` API signature wrong in v1 code | (was) High | (was) Catastrophic | **Verify on installed package D7**; reviewer flagged this is the single most likely "judge spots bullshit in 5 seconds" risk; mitigated by running code end-to-end before architecture freezes |
| AX Online Eval Task confusion (only in SaaS) | (was) Medium | (was) High | **Fixed in v2 §6.1 Hook 7**: replaced with Cloud Scheduler `run_evals` cron; renamed honestly |
| `MCPToolset.from_server` deprecated | Low | Medium | Use `MCPToolset(connection_params=...)` per current ADK; verify on install |
| `Client().annotations.add_span_annotation` vs `Client().spans.add_annotation` | Medium | Low | Verify on installed `arize-phoenix-client` D7 |
| Demo passcode leaks → bot abuse exhausts credits | Low | Medium | Per-IP rate limit; rotate passcode at submission; Vertex budget alert at $250 |
| **Devpost form requirements missed** `[v2: new]` | Medium | Catastrophic | **Track checkbox is Arize, explicitly**; submit by D20 not D21; verify gallery image, "Built with" tags, every text section is filled |
| **Devpost video aspect ratio / size rejection** `[v2: new]` | Low | High | Follow Devpost video spec exactly; upload to YouTube unlisted as backup |
| MAUD/CUAD attribution miss | Low | Medium | Attribution block in README and demo video credits per CC-BY-4.0 |
| **Synthetic perturbation leakage detectable by agent** | Medium | Medium | D13 leakage audit; **`[v3]` tightened to AUC < 0.6 to ship, redo if ≥ 0.7** |
| **Phoenix dashboard cold-start during judging window** `[v3: new]` | Medium | High | min-instances=1 on Phoenix Cloud Run; monitor uptime; the README's "Click any decision to verify" wedge depends on Phoenix being reachable — treat as SLO from D20 onward |
| **Calibrate-on-test contamination undermines headline number** `[v3: new — was a real v2 bug]` | Was High | Was Catastrophic | **Fixed in §5.4 v3** with 5-fold CV and per-fold held-out reporting; no remaining mitigation needed |
| **Reflector auto-promotes overfit / noise** `[v3: new — was a real v2 bug]` | Was High | Was High | **Fixed in §6.3 v3** with paired-bootstrap CI + frozen held-out non-regression check |
| **5-fold CV implementation bug (off-by-one, shared-state leakage)** `[v3]` | Medium | High | D9-morning unit test on fold split before any calibration math runs |
| **Reflector accidentally writes to fold 5** `[v3]` | Low | Catastrophic | Enforce by code: Reflector config holds a dataset-name allowlist, NOT a denylist; `regressions-v1` only; `internal-30-holdout-fold-5` not in allowlist |
| **Bootstrap CI on N≈6 per fold produces embarrassing-wide intervals** `[v3]` | High | Medium | Pre-disclosed in §5.2 + §5.4 step 6; README leads with Wilson LB regardless of width |
| **§6.4 Reflector pre-seeding read as staging by judges** `[v3]` | Low | Medium | One-line README disclosure: "production prompt deliberately seeded weaker 48h before recording so the loop has a real signal to find; loop logic itself unchanged" |
| **D20 single-day overload (record + submit + README + warm-up)** `[v3]` | High | High | **Fixed in §7 v3**: recording moved to D19, D20 is pure submission |
| **PDF bbox extraction fails at D4** `[v3]` | Medium | Medium | Switch to Document AI Layout Parser at D4 EOD; if both fail, scope D15 sync to forward-direction only and document |

---

## 12. Submission Checklist `[v2: Devpost-specific items added]`

- [ ] **Hosted Project URL** — Cloud Run, `--allow-unauthenticated` + passcode prominent in Devpost description (not just README)
- [ ] **Public Phoenix instance URL** — credentialed in a way judges can click without auth (read-only or shared link)
- [ ] **Public GitHub repo** with **Apache 2.0 LICENSE** in About sidebar
- [ ] **Demo video** (≤3:00) on YouTube unlisted + uploaded to Devpost (aspect ratio and size verified)
- [ ] **Devpost track**: **Arize explicitly selected**
- [ ] **Gallery image / thumbnail** (often forgotten; affects browse-page visibility)
- [ ] **"Built with" tech tags**: Google Cloud, Gemini 3, Agent Development Kit, Arize, Phoenix, MCP, Cloud Run, Vertex AI
- [ ] **Team members field** filled (confirms eligibility even solo)
- [ ] **Devpost text sections** (each 100–300 words): Inspiration, What it does, How we built it, Challenges, Accomplishments, What we learned, What's next
- [ ] **Eligibility / region confirmation** for Arize $5K prize
- [ ] **README**: problem, architecture diagram, Arize hooks list, **three-track eval results table** (MAUD-MCQ accuracy vs baselines, CUAD-Spans token-F1 + P@R=0.8, Internal-30 5-fold-CV held-out Block-recall with bootstrapped 95% CI), install instructions, passcode, attributions (MAUD, CUAD, EdgarTools)
- [ ] **README "Demo Scope" paragraph** `[v3]`: explicit 5-deal allow-list named, with reasoning
- [ ] **README pre-commitment** `[v3]`: publish the achieved Block-recall number unmodified even if < target (no quiet downgrade)
- [ ] **README κ caveat** `[v3]`: state that κ on 10 double-annotated contracts is procedural inoculation against single-annotator bias, not strong evidence of high κ
- [ ] **CITATIONS.md**: MAUD, CUAD, EDGAR, all cited sources
- [ ] `[v3]` **Devpost browse-page preview line** (first sentence of description) tuned to be selling — judges click in from here
- [ ] `[v3]` **YouTube video set to Public or "Unlisted with link accessible"** — never "Unlisted restricted." Devpost has DQ'd projects for this
- [ ] `[v3]` **AI-generated-content disclosure** per Devpost rules (we use Gemini extensively; disclose)
- [ ] `[v3]` **Backup Phoenix screenshot deck** linked from Devpost description, in case the Phoenix instance is cold/down during judging
- [ ] `[v3]` **Reflector pre-seeding disclosure** in README: "production prompt was deliberately seeded weaker 48h before demo recording to give the auto-improvement loop a real signal; the loop logic itself is unchanged"
- [ ] `[v3]` **Phoenix dashboard URL warmed by `min-instances=1`** at D20 and verified clickable by judges with no login (read-only / shared link)
- [ ] `[v4]` **Devpost payment-eligibility verification** completed in Devpost user profile (W-9 / W-8BEN equivalent) — required to actually receive the $5K if we win, easy to forget
- [ ] `[v4]` **README "Expected CI width" paragraph** — explicitly state "~±0.10-0.15 expected Wilson CI width given N=24 contracts and 6-10 Block findings per fold" so judges aren't surprised by a wide interval

---

## 13. Open Questions `[v2: still relevant]`

1. Phoenix self-hosted vs Phoenix Cloud: try self-hosted D1 morning; fall back to Phoenix Cloud through our reverse-proxy if it fights us past lunch D2.
2. Stay tight on the 4 trigger clause types (CoC, anti-assignment, MAC, accelerated vesting); resist scope creep into reps & warranties.
3. Reflector cron cadence: nightly is enough. Demo recording uses pre-seeded prompts (§6.4).

---

## 14. Appendix — Source citations

**Market & legal:**
- Peony — Due Diligence Costs 2025: https://www.peony.ink/blog/due-diligence-cost-breakdown-2025
- Potomac Law CoC: https://www.potomaclaw.com/news-Change-of-Control-Problem-Nobody-Owns-in-M-and-A-Until-Its-Too-Late
- Sidley Austin CoC: https://www.sidley.com/en/insights/publications/2020/07/change-of-control
- Tech Contracts anti-assignment: https://www.techcontracts.com/2024/03/29/anti-assignment-and-termination-for-change-of-control/
- ABA MAC 2025: https://www.americanbar.org/groups/business_law/resources/newsletters/2025-spring-ma/material-adverse-change-clauses-m-a/
- Bain Global M&A 2025: https://www.bain.com/about/media-center/press-releases/20252/global-ma-stages-great-rebound-in-2025-with-$4.8-trillion-deal-value-to-mark-second-highest-total-on-record
- Harvard CorpGov 2025/2026: https://corpgov.law.harvard.edu/2025/12/20/mergers-and-acquisitions-reviewing-2025-and-looking-ahead-to-2026/
- V7 Labs — M&A Due Diligence: https://www.v7labs.com/blog/ma-due-diligence
- Grand View Research — Legal AI Market: https://www.grandviewresearch.com/industry-analysis/legal-ai-market-report

**Competitors:**
- Harvey: https://www.harvey.ai/blog/harvey-in-practice-how-m-and-a-teams-use-harvey
- Kira/Litera: https://www.litera.com/products/kira
- eBrevia: https://www.ebrevia.com/m-and-a-and-other-transactional-diligence

**Datasets:**
- CUAD: https://www.atticusprojectai.org/cuad — paper https://arxiv.org/abs/2103.06268
- MAUD: https://www.atticusprojectai.org/maud/ — paper https://arxiv.org/abs/2301.00876
- EdgarTools: https://github.com/dgunning/edgartools
- EdgarTools MCP: https://www.edgartools.io/edgartools-mcp-for-sec-filings/
- Argilla: https://argilla.io/

**Arize:**
- Phoenix MCP: https://github.com/Arize-ai/phoenix/tree/main/js/packages/phoenix-mcp
- Phoenix MCP docs: https://arize.com/docs/phoenix/integrations/phoenix-mcp-server
- OpenInference monorepo: https://github.com/Arize-ai/openinference
- Hallucination eval: https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/hallucinations
- Custom LLM evaluators: https://arize.com/docs/phoenix/evaluation/how-to-evals/custom-llm-evaluators
- Annotations REST: https://arize.com/docs/phoenix/sdk-api-reference/rest-api/annotations
- Hackathon starter: https://github.com/Arize-ai/gemini-hackathon
- Phoenix on GCP guide: https://medium.com/google-cloud/pro-level-agent-observability-deploying-arize-phoenix-on-google-cloud-f07a1576b578
- Hackathon resources: https://rapid-agent.devpost.com/details/arize-resources

**Google:**
- Agent Builder: https://cloud.google.com/products/agent-builder
- ADK: https://adk.dev/ — GitHub https://github.com/google/adk-python
- ADK MCP tools: https://adk.dev/tools-custom/mcp-tools/
- Cloud Run deploy: https://adk.dev/deploy/cloud-run/
- Gemini 3 docs: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro
- Gemini structured outputs: https://ai.google.dev/gemini-api/docs/structured-output

---

*v2 — ready for second review pass. Targeted change log: §1 stats trimmed; §1.4 differentiation honest; §2 wedge limited to the Reflector loop; §4 dropped Orchestrator/Reporter; §5 three eval tracks, 30 contracts, defined metrics, calibration protocol, leakage audit, allow-list demo; §6 corrected `phoenix.evals` API + `arize-phoenix-client` annotation path, fixed Hook 7 Online-Eval/Self-hosted mismatch via Cloud Scheduler, added §6.4 demo pre-seeding; §7 Phoenix ramp stretched to D1-D2, annotation spread D5-D9; §8 reordered around the cmd+click climax + pre-recorded fallback; §9 PDF↔trace sync + score-on-chip; §10 cut 6 of 8 extensions; §11 upgraded dead-URL/quota risks, added Devpost form & video-spec risks; §12 added Devpost gallery image / Built-with tags / text sections / eligibility.*
