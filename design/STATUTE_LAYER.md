# Citation-Linkage Feature — Design Spec (Wave-3 draft)

> **Purpose**: deep spec for the citation-linkage feature (Option C: deterministic citation map + LLM proposer + Phoenix-evaluated comparator). PLAN.md gets the summary + marketing-page edits; this file is the implementation truth.
>
> **Status**: Wave-2-revised. All Backend-Architect blockers + M&A-Attorney findings + Hackathon-Judge polish applied. Pending Wave-3 verification (Backend Architect re-run + M&A Attorney re-run on Roadmap/case-law).
>
> **Rename note**: prior draft called this the "statute map." Renamed to **citation map** because Delaware MAC doctrine, fiduciary-out, *Revlon* duties are common-law — case-law anchors are first-class entries, not statutes.

---

## 1. Thesis (revised)

The product renders **only deterministic, primary-source-verified citations** to users. A separate LLM proposer runs as a **fire-and-forget background task** and emits its citation **only as Phoenix annotation data** — never to the user-facing surface. The citation map mixes statute and case-law anchors (Delaware MAC is *Akorn v. Fresenius*, not a § number). A Phoenix dataset (`citation-gold-v1`) sourced separately from the curated map provides non-circular eval ground truth. **Citations are pinned to primary sources, not generated.**

(The earlier "we graded our own model against the law" line is cut from all public surfaces per Wave-2 M&A counsel: hostile counsel reads it as "vendor admits its model failed against the law and shipped it anyway." Kept internal as a team motto only.)

## 2. Architecture (rewritten — Pydantic v2 reality, no ADK shim, no Jinja templates)

### 2.1 Topology — plain asyncio, fire-and-forget LLM branch

No ADK `ParallelAgent`. Inside `server.py:_stream_findings`, after `risk_judge` emits a finding and before SSE emission:

```python
from opentelemetry.trace import format_span_id, get_current_span

# Synchronous cold path — deterministic only
static_ref: CitationRef | None = lookup_citation(finding.tag, finding.jurisdiction_hint)
finding.citation_ref = static_ref

# Capture the CURRENT span_id (16-hex) BEFORE asyncio.create_task — OTel
# context does NOT propagate across create_task by default, and finding.trace_id
# is the 32-hex TRACE id (not what _annotate needs).
current_span_id_hex: str = format_span_id(get_current_span().get_span_context().span_id)

# Fire-and-forget: LLM proposer runs in background, never blocks /review
asyncio.create_task(
    _run_llm_proposer_and_annotate(
        clause_text=finding.clause_text,
        tag=finding.tag,
        static_ref=static_ref,
        span_id=current_span_id_hex,   # 16-hex span id, NOT finding.trace_id
    )
)

# /review returns NOW with deterministic citation only.
# RiskFinding.model_dump is subclass-overridden to default-exclude
# eval-only fields (see §2.3 Guard #2); the explicit exclude= below
# is belt-and-suspenders for any future caller that passes its own
# exclude= and forgets to merge.
yield ServerSentEvent(
    event="finding",
    data=finding.model_dump(mode="json", exclude=_EVAL_ONLY_FIELDS),
)
```

The background task awaits Gemini-3-Flash, runs the deterministic comparator in Python, then writes the Phoenix annotation via the existing `_annotate` helper at `agent/router.py:56-74`. **User p50 unchanged.**

**Span-availability race fix.** Phoenix annotations POST against a span_id over HTTP. If `BatchSpanProcessor` hasn't flushed the parent span before the BG task POSTs (~3–4s later), Phoenix returns 404. Fix: after `risk_judge` emits, call `tracer_provider.force_flush(timeout_millis=500)` once before SSE emission, AND **log the return value — on False, the BG task falls back to `sync=True` on the annotation call** so we don't silently lose annotations to a missed flush. Cost: 1 LoC of logging + 1 conditional in the BG task.

**Span grouping note (Wave-4 cosmetic finding)**: `get_current_span()` at the `_stream_findings` call site captures whichever span is active there — typically the FastAPI request root or the `ma_gatekeeper` SequentialAgent parent, NOT the `risk_judge` child span (which has already closed by the time `risk_judge` yields). Phoenix accepts the annotation against any valid exported span_id, so this does not 404; it just lands one level up the tree from where §2.5 implies. The trace-list filter `label=disagree` still surfaces these as expected. If tighter grouping under `risk_judge` matters for v2: capture the span_id inside `risk_judge`'s scope and stash on the finding as a transient attr. Not gating.

(Removed prior prose claim that "OTel context already in scope from `phoenix.otel.register`" — context does not auto-propagate across `asyncio.create_task`. Span id is captured explicitly above.)

### 2.2 Schema additions to `agent/schemas.py`

```python
class CitationRef(BaseModel):
    """User-facing citation. Statute OR case-law. Only emitted by the
    deterministic lookup; the LLM proposer emits a LinkerProposal.

    NOTE on docstring examples: until the attorney sign-off pass on Day 2
    locks the actual Akorn cite, the example here uses a placeholder.
    Production map content lives in data/citation_map.json with primary
    sources verified per-entry (see CITATION_MAP_SIGNOFF.md, §4.4 #5).
    """
    citation: str = Field(..., description='e.g. "DGCL § 251(c)" — case-law cites verified against primary source before commit')
    citation_kind: Literal["statute", "case_law", "regulation"] = "statute"
    jurisdiction: str = Field(..., description='e.g. "Delaware"')
    uri: str | None = Field(default=None)
    rationale: str = Field(..., description="Why this clause maps here (<= 240 chars)")
    verified_date: date = Field(..., description="Map-commit date; CI fails if older than 180 days")
    primary_source: str = Field(..., description='e.g. "Cornell LII", "delcode.delaware.gov", "courts.delaware.gov"')


class LinkerProposal(BaseModel):
    """INTERNAL EVAL DATA. NEVER rendered to users.

    Defended by THREE structural guards (§2.3): a distinct Pydantic class
    that type-filters won't accidentally match; a subclass-override of
    RiskFinding.model_dump that default-excludes eval-only fields; and
    an SSE wire-output regression test that asserts these field names
    appear nowhere in bytes leaving the server.
    """
    citation: str
    citation_kind: Literal["statute", "case_law", "regulation"]
    jurisdiction: str
    rationale: str
    model_confidence: float = Field(..., ge=0.0, le=1.0)


# Module-level constant — referenced by the RiskFinding.model_dump override
# below AND by the SSE wire test for symbol parity.
_EVAL_ONLY_FIELDS: frozenset[str] = frozenset({
    "linker_proposal",
    "linker_agreement",
    "linker_confidence",
})


class RiskFinding(BaseModel):
    # ... existing fields ...
    citation_ref: CitationRef | None = Field(default=None)
    linker_proposal: LinkerProposal | None = Field(default=None)
    linker_agreement: bool | None = Field(default=None)
    linker_confidence: float | None = Field(default=None)

    def model_dump(self, *, exclude=None, **kwargs):
        """Default-exclude eval-only fields from EVERY public serialization.

        This is Guard #2: instead of relying on each call site to remember
        exclude=_EVAL_ONLY_FIELDS, the model itself enforces it. Any future
        public surface (REST, logging, metrics, batch export) is structurally
        defended. Eval-only sites use model_dump_internal() explicitly.
        """
        exclude_set = set(exclude or ())
        exclude_set |= _EVAL_ONLY_FIELDS
        return super().model_dump(exclude=exclude_set, **kwargs)

    def model_dump_json(self, *, exclude=None, **kwargs):
        """Override the JSON path too — Pydantic v2's model_dump_json
        does NOT call model_dump internally (it goes through the core
        schema directly), so the override at model_dump alone leaves a
        latent leak for any future caller. Belt-and-suspenders.
        """
        exclude_set = set(exclude or ())
        exclude_set |= _EVAL_ONLY_FIELDS
        return super().model_dump_json(exclude=exclude_set, **kwargs)

    def model_dump_internal(self, **kwargs):
        """Eval-only serialization — bypasses the default exclusion.
        Used ONLY by tests + the BG-task annotation diagnostic logger.
        Audited as a single grep target: `model_dump_internal\\b`.
        """
        return super().model_dump(**kwargs)
```

### 2.3 Three structural guards (Wave-3 revised)

1. **Distinct Pydantic class** — `LinkerProposal` is not a flag on `CitationRef`. Type filters mismatch on any accidental render.
2. **Subclass `model_dump` override** — `RiskFinding.model_dump()` ALWAYS unions `_EVAL_ONLY_FIELDS` into the `exclude` set. This is the **structural** defense (vs. single-point discipline). Any future public surface (REST handler, batch export, Prometheus metric, log line) is automatically defended. Eval-only sites must call `model_dump_internal()` explicitly — a single grep target audit-checks that call site count stays small.
3. **SSE wire-output regression test** — `tests/test_no_eval_leak.py::test_sse_bytes_contain_no_eval_field_names` exercises the full `/review` endpoint with a fixture that intentionally populates `linker_proposal`, captures raw SSE bytes via `httpx.AsyncClient.stream(...)`, and asserts no string in `_EVAL_ONLY_FIELDS` appears in the bytes. This is the load-bearing wire-level safety net. **Note**: Guard #2 is the structural protection; Guard #3 is the integration sentinel that catches an override regression.

**Frontend guard** (lower-weight, complements but does not replace SSE wire test): `frontend/lib/types.ts`'s `RiskFinding` interface deliberately does not include eval-only field names. A `tests/test_frontend_type_sync.py` does a fragment-extract on the `interface RiskFinding {...}` block and asserts the substrings absent. Brittle vs. comment formatting — kept as a defense-in-depth lint, not load-bearing. The SSE wire test is the primary guarantee.

### 2.4 Comparator (deterministic Python in the background task)

```python
async def _run_llm_proposer_and_annotate(*, clause_text, tag, static_ref, span_id):
    try:
        llm_ref = await _call_linker_llm(clause_text, tag, timeout=8.0)
    except (asyncio.TimeoutError, ValidationError, json.JSONDecodeError):
        _annotate(span_id, name="citation_linker_agreement",
                  label="linker_failed", score=0.0, explanation="proposer error")
        return

    if static_ref is None:
        _annotate(span_id, name="citation_linker_agreement",
                  label="no_static", score=0.0,
                  explanation=f"llm={llm_ref.citation} no_map_match")
        return

    agreement = (
        _normalise(static_ref.citation) == _normalise(llm_ref.citation)
        and static_ref.jurisdiction == llm_ref.jurisdiction
    )
    _annotate(
        span_id,
        name="citation_linker_agreement",
        label="agree" if agreement else "disagree",
        score=1.0 if agreement else 0.0,
        explanation=f"static={static_ref.citation} llm={llm_ref.citation} conf={llm_ref.model_confidence:.2f}",
    )
```

`_normalise` is a regex that strips section punctuation variants (`§ 251(c)` ≡ `§251(c)` ≡ `Section 251(c)`).

### 2.5 Phoenix span tree

```
review.request                                  [FastAPI root]
└─ ma_gatekeeper (SequentialAgent)
   ├─ parser
   ├─ classifier (ParallelAgent, 7 children)
   ├─ cross_reference
   ├─ risk_judge                                [ann: hallucination, clause_faithfulness, risk_judge_gate]
   └─ inline_judge_and_router                   [existing inline path]
                                                [ann: citation_linker_agreement]  ◀── arrives post-hoc from BG task
                                                                                       on the SAME parent span,
                                                                                       Phoenix groups it adjacent
                                                                                       to risk_judge_gate
```

The annotation is asynchronous from the user's perspective but appears on the trace within ~3-4 s of the finding emitting. Demo recording starts after the run completes, so the trace is fully populated.

### 2.6 Failure-mode tests

In `tests/test_citation_linker.py`:
- `test_llm_timeout_emits_failed_annotation` — patch `_call_linker_llm` to raise `asyncio.TimeoutError`; assert annotation label `"linker_failed"`, `citation_ref` populated, no `linker_proposal` field set.
- `test_garbage_json_does_not_leak_to_dump` — patch to return malformed JSON; assert `finding.model_dump(exclude=_EVAL_ONLY_FIELDS)` has no eval-only keys.
- `test_sse_bytes_contain_no_eval_field_names` — full `/review` integration with deliberate `linker_proposal` population; assert wire bytes are clean.
- `test_frontend_type_sync` — parse `frontend/lib/types.ts`; assert no eval-only names.
- `test_static_lookup_returns_none_outside_map_coverage` — confirms graceful `None` when a tag has no map entry (e.g., accelerated vesting → contract-anchored, no statutory cite).

### 2.7 Implementation cost — 4.5 dev-days (revised honestly)

| Task | LoC | Days |
|------|-----|------|
| `agent/citation_linker.py` (sync lookup + async LLM call + comparator + map loader) | ~220 | 0.75 |
| `data/citation_map.json` (~25 entries: 7 tags × 3 jurisdictions + **4 named case-law anchors: `Akorn v. Fresenius` (MAC), `Revlon, Inc. v. MacAndrews` (Revlon duties), `AB Stable VIII v. MAPS Hotels` (post-Akorn MAC), `In re Trados S'holder Litig.` (fiduciary-out for preferred holders)**; each cite primary-source-verified per `CITATION_MAP_SIGNOFF.md`) | data | 0.5 |
| `schemas.py` additions (CitationRef, LinkerProposal, RiskFinding fields, _EVAL_ONLY_FIELDS) | ~50 | 0.5 |
| `server.py` integration (asyncio.create_task in `_stream_findings`, exclude= at model_dump) | ~30 | 0.5 |
| `prompts.py` (`CITATION_LINKER_PROMPT` with jurisdiction whitelist + JSON-only output) | ~50 | 0.25 |
| Tests (5 failure-mode + 3 golden map + 1 wire regression + 1 frontend sync = 10) | ~280 | 1.0 |
| `frontend/lib/types.ts` sync + `findings-pane.tsx` `<CitationCitationRow>` | ~80 | 0.5 |
| Phoenix instrumentation verification on staging trace | — | 0.25 |
| CI staleness gate (`verified_date > 180 days fails build`) | ~25 | 0.25 |
| **Total** | **~735** | **4.5** |

---

## 3. Phoenix eval surface (revised — 2 evaluators, no κ this sprint)

### 3.1 Non-circularity protocol

Two independently-sourced ground truths:

- **Ground-truth A — the citation map (~25 rows)**: curated by M&A attorney from DGCL/UCC/HSR + Delaware Chancery case-law. Primary sources: delcode.delaware.gov, courts.delaware.gov.
- **Ground-truth B — the eval gold (40 rows)**: curated by architecture lead from Cornell LII + Atticus CUAD clause-type taxonomy. Different annotator, different source set.

**Inter-rater κ moved to post-hackathon** (Wave-2 Backend Architect scope cut). The two ground truths are still independently sourced; we log the gold-vs-map agreement count as a dataset metadata field. κ computation is a 2-hour follow-up after the deadline.

### 3.2 Datasets

```
citation-gold-v1            (40 rows, frozen, public-sources, fold-aware)
citation-regressions        (auto-grown via Reflector + MCP add-dataset-examples)
```

Row schema:
```json
{
  "input":  {"clause_text": "...", "tag": "change_of_control"},
  "output": {"citation": "8 Del. C. § 251(c)",
             "citation_kind": "statute",
             "source": "https://www.law.cornell.edu/...",
             "supports": "consent-required language"},
  "metadata": {"deal_id": "MSFT-ATVI-2023", "fold": 1}
}
```

`_WRITABLE_DATASETS` allowlist in `agent/reflector.py:49` extends to `{"regressions-v1", "citation-regressions"}`. Gold set is NEVER in the allowlist — frozen-set discipline per the existing pattern.

### 3.3 Two evaluators (faithfulness cut)

```python
make_citation_validity_classifier()      # rails: valid_citation, invalid_citation, malformed   ◀── LLM
make_citation_exact_match_classifier()   # rails: exact, normalised_match, miss                 ◀── DETERMINISTIC regex
```

`citation_faithfulness` cut per Wave-2 Backend Architect scope reduction — the LLM-judging-LLM signal is the weakest of the three and the most circular. `citation_validity` covers "is this even a real provision"; `citation_exact_match` covers "is it the right one." Two complementary axes, no redundancy.

`citation_exact_match` is a regex + section-normaliser wrapped in `create_classifier` shape for Phoenix UI uniformity. **README §6.1 calls this out explicitly as "deterministic comparator surfaced as a Phoenix rail for grader uniformity — NOT an LLM judge"** so partner-track reviewers don't read it as LLM-judges-LLM.

### 3.4 Experiments + promotion gate

Nightly Reflector adds a third `_run_experiment_pairwise` call against `citation-gold-v1` with `evaluators=[citation_exact_match, citation_validity]`. Pooled `citation_exact_match` score is the headline.

**Promotion gate — composite, not third gate**:
- Existing two gates unchanged.
- New necessary condition: `citation_exact_match` candidate ≥ `prod_score − max(paired_bootstrap_se(citation_deltas), 0.05)`.
- Cost: 0.4 dev-days per Wave-2 BE Architect revision (was 0.25 in original).

### 3.5 Online signal — true streaming

`citation_linker_agreement` annotation written on every `/review` (post-hoc from the background task — same trace, ~3-4 s later). Phoenix charts as per-call time series. **The README §6.1 Hook 7 footnote drops "batch-collapsed" for this one metric — the project now has a genuine streaming-eval signal.**

### 3.6 New README §6.1 hooks 8/9/10

- **Hook 8** — *Non-circular citation eval via independently-sourced gold (`citation-gold-v1`), gold-vs-map agreement logged as dataset metadata.*
- **Hook 9** — *Per-call `citation_linker_agreement` span annotation → genuine streaming-eval signal (not batch-collapsed).*
- **Hook 10** — *Deterministic regex comparator (`citation_exact_match`) surfaced as a Phoenix `create_classifier` rail for grader uniformity — explicitly NOT an LLM judge.*

### 3.7 Eval surface cost — 1.5 dev-days

- 0.5 d — architecture lead curates 40-row gold from Cornell LII + CUAD.
- 0.25 d — two `create_classifier` factories + exact-match regex normaliser + 8 unit tests.
- 0.4 d — extend `should_promote` + third `_run_experiment_pairwise` call + composite-gate test.
- 0.25 d — wire `citation_linker_agreement` annotation in background task.
- 0.1 d — README §6.1 hooks 8/9/10 + Devpost blurb.

---

## 4. UX / Surface design (Wave-2 polish applied)

### 4.1 Two-surface split

**Findings surface (user-facing)** — renders only the deterministic citation.

`<CitationCitationRow>` component:
- Citation in Lane-A display serif at 14px / 600. Statute or case-law — both render in the same row, differentiated by a 11px mono `citation_kind` badge (`statute` / `case_law` / `regulation`).
- 8px champagne-dot separator + jurisdiction badge.
- Phoenix span-link glyph (12px Lucide arrow-up-right) right-aligned.
- Microcopy: 10px `text-ink-paper/60`, `verified against [primary source] · [ISO date]`. **Date = static-map commit date.** CI staleness gate (`verified_date > 180 days fails build`) ensures the stamp doesn't become a "we stopped checking" exhibit.

The user-facing surface does not know the LLM proposer exists.

**Evals surface — Phoenix-hosted only**:
- No `arize_project`-owned route. The Devpost video shows Phoenix UI screen captures directly.
- Lower-third in the video carries the Phoenix dataset URL. **15-second pre-launch dry-run from a clean device** to confirm the URL resolves — failure mode: click-through 404 during judging.

### 4.2 Marketing-page edits to PLAN.md

**§2.1 tagline — DO NOT touch.**

**§2.2 #5 — three-layer moneymoment**: trace → clause → **citation** (statute OR case-law). §6.4 unfurl gesture gains a third frame at ~0:55, ~3 s hold.

**§2.2 #6 — new bullet (exact copy, Wave-2 revised)**:
> **Not a substitute for primary-source review.** Citations are pinned to a deterministic, hand-curated map of clause-tag → controlling authority (statute or case-law), verified against the primary source on the date stamped on each citation. The LLM never proposes citations to users; an internal proposer is graded against the map, and its output is never rendered.

(Removed "self-improvement signal" — contradicted the prior Roadmap and read as "AI learning." Replaced with deposition-proof "never rendered.")

**§2.2 #10 — append (exact copy)**:
> Citations resolve through a deterministic clause-tag → controlling-authority map, versioned in source and verified against primary sources. A separate LLM proposer is graded against that map in a Phoenix dataset (`citation-gold-v1`); its output is never rendered to users.

**§2.2 — insert new #11 "What ships next"** (Wave-2 revised — no future-malpractice commitment):
> **Today.** Citations resolve through a deterministic clause-tag → controlling-authority map (statutes and case-law), hand-curated across four jurisdictions (Delaware, federal, NY, UK), verified against primary sources and stamped with the verification date.
>
> **Next.** A Phoenix-evaluated LLM proposer continues to run as an internal grader against the map. Expansion of the deterministic map is informed by — never replaced by — its disagreement set. The proposer never reaches user-facing rendering.
>
> **Future.** An ELI/LKIF ontology graph for cross-jurisdiction resolution — so a Delaware DGCL § 251(c) citation resolves automatically to its NY BCL § 902 and UK Companies Act 2006 § 979 analogues for cross-border deals.

(Deleted the "promoted to user-facing only if its agreement rate clears a Wilson lower bound" clause per M&A counsel — that line was the future-malpractice exhibit.)

**§6.4 engineered screenshot frame**:
- Top-left: Wilson-LB recall headline — Lane-A display serif at max scale.
- Mid-left: Block verdict badge in warm clay.
- Mid-right: `DGCL § 251(c) · Delaware` row in display serif 14px / 600, champagne pill on jurisdiction, mono `statute` badge in 11px.
- Lower-left: Phoenix span ID in 11px mono, `verified 2026-06-01` microcopy in 10px below.
- **Single oxblood underline on `§ 251(c)` — locked rule.** No other accent. Builder enforcement: the per-frame timing sheet has an explicit "ACCENT BUDGET: 1" line.

**§7.0 video storyboard rebalance**:
- Beat **0:30–1:25** (moneymoment, 55s): statute frame lands at ~0:55, held ~3s.
- Beat **1:55–2:15** (loop section, 20s): Phoenix-hosted dataset shown ~4s. **Disagreement-rate y-axis is fuzzed**: trend curve visible, exact percentage not legible at frame-pause. **Tick labels and axis values stripped entirely** (Wave-3 attorney follow-up: fuzzed gridlines alone are insufficient — visible tick numbers still constitute a vendor representation). The chart shows a labeled time axis only ("agreement over time"), no y-axis numbers.
- Hard rule: no cross-fade between Findings and Evals frames; cut only.

### 4.3 Deposition test (revised — all 4 PASS post-Wave-2 fixes)

| Surface | Worst spin | Defense |
|---|---|---|
| (a) Live UI on Block | "Citation came from an LLM." | Triple-guard at schema + `exclude=` + wire-output regression test. LLM never touches user-facing render. |
| (b) Devpost screenshot | "Marketing shows AI proposing citations." | Moneymoment is deterministic map; eval surface shown separately under "internal eval signal — never shown to users" copy; no cross-fade. |
| (c) Phoenix dataset row | "9% disagreement, shipped anyway." | LLM never shipped to users; dataset measures whether map expansion is informed by proposer's disagreement set. Map remains the only render path. |
| (d) Marketing roadmap | "Vendor will eventually replace map with LLM." | Roadmap explicit: proposer informs map expansion, **never replaces it**, proposer never reaches user-facing rendering. (Future-malpractice exhibit removed.) |

### 4.4 Malpractice-defusing UI patterns (locked)

1. Banned verbs in user-facing copy: *thinks, suggests, agrees, disagrees, recommends, proposes.* Enforced via `.eslintrc` `no-restricted-imports` against `frontend/components/findings-*`.
2. `verified_date` = map-commit date. Static, auditable.
3. CI staleness gate: `verified_date > 180 days` fails build.
4. §2.2 #6 bullet appears verbatim in marketing page + Devpost long description + future `/security` trust-packet. Drift = deposition opening.
5. In-house counsel sign-off on the citation map content before Day-3 code lands. **Hard gate. Spec**:
   - **Signer**: for hackathon scope, attorney-persona (LLM agent prompted as M&A counsel with WebFetch enabled) signs each entry against its primary source. For production: named in-house GC.
   - **Artifact**: `data/CITATION_MAP_SIGNOFF.md` committed alongside `data/citation_map.json`. Format: one row per entry → `{tag, citation, primary_source_url, verified_date, signer_id, commit_sha}`. SIGNOFF.md is the audit trail.
   - **Failure path**: if any entry is unsigned at Day-3 EOD, that tag is removed from the live map (graceful `None` per §2.6 test). Code does NOT ship a partially-unverified map under any banner.
   - The `Akorn` citation in the spec docstring is a known placeholder pending this pass — the Round-3 attorney reviewer flagged that `198 A.3d 724` may be the affirmance cite rather than the Chancery merits opinion (`2018 WL 4719347`). Day-2 sign-off resolves this before code lands.

### 4.5 The marketing line (Wave-2 revised)

Public copy:
> *"Citations are pinned to primary sources, not generated."*

Boring, declarative, deposition-proof. Replaces the cut "We graded our own model" line. **The "we graded our own model" line is banned from every written channel (no Slack, no commit messages, no internal docs, no PR descriptions) — Slack-as-trial-exhibit is real precedent (cf. *Twitter v. Musk* discovery).** Verbal use only, never recorded.

### 4.6 UX cost — 0.75 dev-days (Wave-2 revised, includes frontend types)

- 0.25 d — `<CitationCitationRow>` component + types + tests.
- 0.25 d — `frontend/lib/types.ts` sync + `test_frontend_type_sync.py`.
- 0.25 d — marketing-page copy edits (§2.2 #5/#6/#10/#11, §6.4 frame, §7.0 rebalance).

---

## 5. Total cost (Wave-2 honest)

| Track | Days |
|-------|------|
| Architecture (§2) | 4.5 |
| Eval (§3) | 1.5 |
| UX (§4) | 0.75 |
| **Subtotal** | **6.75** |
| Hidden-cost buffer (Phoenix client pinning, ADK compat, integration smoke) | 0.25 |
| **Total** | **7.0 dev-days** |

**Against ~1 week (7 day) remaining product-track budget.** Zero buffer. Mitigations:
- Map curation (0.5 d) runs in parallel with design-track Phase 0 if user does it during design agents' work.
- Gold curation (0.5 d) parallelisable similarly.
- κ pass moved post-hackathon (was 0.25 d).
- `citation_faithfulness` evaluator cut (was 0.25 d).
- ADK ParallelAgent topology dropped → plain asyncio (avoided the 0.25 d shim trial-and-error).

The cuts make a 7-day fit; if any line slips, additional cut candidates (impact-ordered): drop composite promotion gate → ship hooks 8/9/10 without changing `should_promote` (saves 0.4 d); drop frontend sync test (saves 0.25 d, weakens Guard #3 frontend half).

---

## 6. Day-by-day schedule

| Day | Work | Owner |
|-----|------|-------|
| 1 | Citation map curation begins (statute + case-law). Schemas drafted. CI staleness gate scaffolded. | Backend + attorney persona |
| 2 | Citation map locked + **in-house counsel sign-off gate**. Gold curation begins (Cornell LII + CUAD). | Backend + attorney |
| 3 | `agent/citation_linker.py` (sync lookup + async LLM call + comparator) + first 5 tests. | Backend |
| 4 | `server.py` integration (asyncio.create_task in `_stream_findings`) + `exclude=` wiring + Phoenix annotation. | Backend |
| 5 | Two `create_classifier` factories + experiments wiring + remaining 5 tests. | Backend |
| 6 | Reflector composite-gate + frontend types sync + wire-output regression test + staging trace verification + README §6.1 update. | Backend |
| 7 | 15-second URL dry-run + Devpost-video screen capture of Phoenix dataset + design-track integration. | Backend + design |

---

## 7. PLAN.md edits required (summary)

After Wave-3 VALIDATES this spec, the following land in PLAN.md verbatim:

1. **§2.2 #5** — three-layer moneymoment (trace → clause → citation).
2. **§2.2 #6** — new bullet (verbatim copy from §4.2 above).
3. **§2.2 #10** — append (verbatim).
4. **§2.2 new #11** — "What ships next" roadmap (verbatim, no future-malpractice clause).
5. **§6.4** — engineered screenshot frame upgraded with citation element + locked single-accent rule.
6. **§7.0** — video beats rebalanced; disagreement-rate axis fuzzed.
7. **§Resolved decisions** — append: *Citation-layer = Option C (deterministic map + LLM proposer + Phoenix eval), spec at `design/STATUTE_LAYER.md` (filename retained), total 7 dev-days product-track.*
8. **Deliverables list** — add `STATUTE_LAYER.md`.
9. **§2.3 voice rules** — append: ban "We graded our own model. The law won." from any public surface (allowed internal-only).

---

## 8. Open items resolved by Wave-2

- ~~ADK ParallelAgent + non-LLM shim~~ → dropped; plain asyncio.
- ~~Pydantic underscore-prefix field guard~~ → replaced with public field names + `exclude=_EVAL_ONLY_FIELDS` single-point pattern.
- ~~Jinja .j2 AST contract test~~ → replaced with SSE wire-output regression test (project has no Jinja).
- ~~Cold-path latency~~ → LLM moved to fire-and-forget background task; user p50 unchanged.
- ~~"We graded our own model" line~~ → cut from public surfaces; replaced with "Citations are pinned to primary sources, not generated."
- ~~§2.2 #11 Roadmap "promoted to user-facing" clause~~ → deleted; replaced with "proposer informs map expansion, never replaces it."
- ~~Statute-only map~~ → renamed citation map; includes case-law anchors (MAC = *Akorn v. Fresenius*, fiduciary-out = *Revlon*, etc.).
- ~~Missing CI staleness gate~~ → added.
- ~~Missing in-house counsel sign-off~~ → added as Day-2 hard gate.
- ~~Missing single-accent rule in §6.4 timing sheet~~ → added.
- ~~README Hook 10 mislabel risk~~ → explicit "deterministic comparator, not LLM judge" framing.
- ~~Missing 15-s URL dry-run~~ → Day-7 task.
- ~~Disagreement-rate y-axis legible at frame-pause~~ → fuzzed.
- ~~Missing frontend types sync test~~ → `tests/test_frontend_type_sync.py` added.

## 9. Open items remaining (small, parking)

- Citation map content (~25 entries): needs primary-source verification + attorney sign-off. Day-1/2 task.
- κ inter-rater computation: post-hackathon follow-up.
- Background-task error-handling for OpenTelemetry span context retention across `asyncio.create_task`: requires verification on staging.

---

*End of Wave-3 draft.*
