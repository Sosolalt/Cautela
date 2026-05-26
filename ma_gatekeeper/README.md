# M&A Due Diligence Gatekeeper

An auditable AI agent for M&A contract review, built for the Google Cloud
Rapid Agent Hackathon — Arize partner track. Submission deadline:
**June 11, 2026**.

The agent reads merger agreements and the underlying data-room contracts,
flags change-of-control / anti-assignment / MAC / accelerated-vesting
clauses, and routes each finding into one of three lanes (**Auto-Clear**,
**Escalate to Lawyer**, **Block**). Every decision is traced and judged
in [Arize Phoenix](https://arize.com/phoenix/), with a nightly Reflector
agent that grows a regression dataset and runs paired-bootstrap
experiments to auto-promote improved prompts — gated by a non-regression
check on a frozen held-out fold.

The thesis is **not** "AI does M&A review faster." It is
**"AI does M&A review with an audit trail the judge can click into."**

See [`plan.md`](../plan.md) for the full architecture, calibration
protocol, and 3-week timeline. The plan went through 4 independent
review rounds with final scores 9/10 (market, architecture), 9.2/10
(data strategy), 8.5/10 (timeline).

## Architecture (plan §4.2)

```
PDF upload  (Cloud Run FastAPI handler)
   v
Parser           (Gemini 3 Pro, populates pdf_bbox)
   v
Classifier       (ParallelAgent, Gemini 3 Flash fan-out)
   v
CrossReference   (Gemini 3 Pro, resolves definitions <-> operative)
   v
RiskJudge        (inline phoenix.evals + span annotation)
   v
Router           (deterministic Python, NOT an LLM)
   v
Reporter         (Jinja2 template, NOT an LLM)

Reflector (separate Cloud Scheduler cron):
  list-traces -> add-dataset-examples -> upsert-prompt -> two experiments
  (regression set + frozen fold-5) -> auto-promote ONLY if both gates pass
```

## Seven Arize hooks (plan §6.1)

1. OpenInference tracing of every ADK call (`openinference-instrumentation-google-adk`).
2. Inline `phoenix.evals.create_classifier` for hallucination + faithfulness.
3. Programmatic span annotations via `arize-phoenix-client`.
4. Phoenix MCP introspection by the Reflector (`list-traces`, `get-trace`, ...).
5. Auto-growing regression dataset via MCP `add-dataset-examples`.
6. Prompt versioning + experiment-gated promotion (paired bootstrap CI + frozen fold non-regression).
7. Hook 7: scheduled batch `run_evals` collapsed into the Reflector nightly cron — equivalent batch coverage to Arize AX Online Eval Tasks (which are SaaS-only).

## Repository layout

```
ma_gatekeeper/
  agent/
    schemas.py           # Pydantic models (plan §4.3)
    instrumentation.py   # phoenix.otel.register with set_global_tracer_provider=False
    evaluators.py        # hallucination + faithfulness create_classifier wrappers
    router.py            # deterministic gating (plan §6.2) + span annotation writer
    agents.py            # ADK SequentialAgent / ParallelAgent topology
    prompts.py           # fallback prompt templates (Phoenix is source of truth)
    reflector.py         # nightly self-improvement loop (plan §6.3)
    server.py            # FastAPI: /review, /review-by-deal, /reflect, /allow-list
  scripts/
    download_datasets.py # CUAD + MAUD + EDGAR pull
    perturb_contracts.py # adversarial slice (regex transforms) + TF-IDF/LogReg leakage AUC audit (<0.6 to ship; see plan §5.3 v4.1 honest impl note)
    calibrate.py         # 5-fold CV grid search + reliability diagrams
    annotate.py          # Gemini pre-label -> Argilla JSONL + Cohen's kappa
    seed_reflector.py    # D18 pre-seed: weaken production prompt, stage strong as candidate
  tests/
    test_fold_split.py     # D9-morning unit test (7 tests)
    test_promotion_rule.py # bootstrap CI + epsilon floor + allowlist (9 tests)
    test_router.py         # independent-gating semantics (7 tests)
    test_stats.py          # one-sided Wilson + cluster bootstrap (8 tests)
    test_annotate.py       # JSONL serialization + kappa math (21 tests)
    test_seed_reflector.py # D18 pre-seed: weak-template + tag pairing (9 tests)
    test_allow_list.py     # 5-deal schema + HTTP 503/404 invariants (9 tests)
  Dockerfile
  requirements.txt
  .env.example
  README.md
  HANDOFF.md             # things only the human can do
```

## Local quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # fill in PHOENIX_* and Google Cloud values

# Download datasets (CUAD, MAUD, EDGAR samples)
python -m scripts.download_datasets --out data/

# Run the FastAPI server locally
uvicorn agent.server:app --reload --port 8080
```

## Tests

70 pure-Python unit tests; no live API calls. Run:

```bash
.venv/bin/python -m pytest tests/ -v
```

The fold-split tests are the explicit D9-morning unit test (plan §7 v3)
catching off-by-one + leak-via-shared-state bugs. The promotion-rule
tests verify bootstrap CI math, epsilon floor (0.03), and the
code-enforced allowlist that prevents the Reflector from writing to the
frozen held-out fold.

## Tag sync points

The 8-value clause-tag enum has ONE source of truth and three derived
or hand-mirrored consumers:

- **Truth**: `agent/schemas.py:Tag` (Literal of 8 values incl. `"none"`).
  `ALL_TAGS` and `CLASSIFIER_TAGS = ALL_TAGS - {"none"}` are derived
  here via `typing.get_args`.
- **Re-export**: `agent/agents.py` imports `CLASSIFIER_TAGS` for the
  ParallelAgent fan-out. No duplicate list.
- **Re-export**: `scripts/annotate.py` imports `CLASSIFIER_TAGS` as
  `PRELABEL_TAGS`; `PRELABEL_INSTRUCTION` f-strings the list so Gemini
  always sees the current set.
- **Hand-mirror**: `frontend/lib/types.ts:Tag` union. Drift is caught
  by `tests/test_tag_sync.py:test_frontend_ts_tag_union_matches_python`
  (regex cross-check; no codegen).

**To add a new clause tag**, touch exactly two files:
1. Append the literal to `agent/schemas.py:Tag`.
2. Append the same string to `frontend/lib/types.ts:Tag`.

Then run `pytest tests/test_tag_sync.py` to confirm.

Also consider whether the new tag deserves its own bespoke
clause-family block in `agent/prompts.py:CROSS_REFERENCE_PROMPT` (the
first four tags get one; the others don't — that's a deliberate legal-
specificity choice, not an oversight). The D18 seed regex in
`scripts/seed_reflector.py` is pinned to exactly four blocks and is
guarded by `test_tag_sync.py:test_cross_reference_prompt_has_four_clause_family_headings`.

## Demo scope (plan §5.5)

The hosted demo presents a curated dropdown of **5 pre-indexed deals**,
not an open ticker box. Each is pre-vetted to surface at least one
Block-tier finding so the demo cannot land on an "all clear"
anticlimax. The EdgarTools MCP fetches the actual 8-K Exhibit 2.1
filing live for each demo invocation — the artifact is real and could
change between runs.

**Demo Scope paragraph** (required in the Devpost description):

> The hosted demo runs against a curated, pre-indexed set of five recent
> 8-K/Ex 2.1 merger filings, pre-validated to surface at least one
> change-of-control, anti-assignment, or MAC-related finding so the
> agent has something interesting to do on camera. The filings are
> fetched live from EDGAR via the EdgarTools MCP server at demo time.

## Eval headline (plan §5.4 v4)

Reported on **24 contracts (4 folds × 6)**; fold 5 (6 more contracts)
is reserved as the Reflector's frozen non-regression set and is never
used for the headline number.

> Held-out Block recall = R, Wilson 95% LB = R_lo, at abstention = Y%;
> per-evaluator thresholds (τ_h, τ_f), 4-fold CV on Internal-30.

**Expected CI width**: with ~6–10 Block findings per fold, the 95%
Wilson CI for a proportion near 1.0 spans roughly ±0.10–0.15. The LB
clearing 0.95 is **arithmetically tight, not a guarantee**; we publish
R and R_lo unmodified regardless.

## Reflector loop pre-seeding (plan §6.4)

The "production" prompt was deliberately seeded weaker 48 hours before
demo recording so the auto-improvement loop has a real signal to find.
The loop logic itself — paired-bootstrap CI, frozen-fold non-regression,
auto-promotion — is unchanged. Honest engineering of reproducibility,
not staging.

## Attributions

- [CUAD](https://www.atticusprojectai.org/cuad) — Hendrycks et al., 2021, CC-BY-4.0
- [MAUD](https://www.atticusprojectai.org/maud/) — Wang et al., EMNLP 2023, CC-BY-4.0
- [EdgarTools](https://github.com/dgunning/edgartools) — Dwight Gunning, MIT
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — Arize AI, Apache 2.0

## License

Apache 2.0. See `LICENSE`.
