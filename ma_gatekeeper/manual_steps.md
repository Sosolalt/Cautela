# Cautela — Manual Setup & Submission Runbook

> Operator runbook for everything that must be done **by hand** (accounts, billing, cloud deploys, human annotation, demo recording, Devpost submission). Code-side wiring is handled separately.

**Target dates**
- Vertex Gemini 3 Pro quota bump: **request first** (24–48h turnaround) — must land before **June 11**.
- Submit by **June 10 EOD** for a 24h buffer.
- Spot-check live services hourly through the evening of **June 11**.

---

## §1 — Accounts, Billing & Eligibility

### 1.1 Create the GCP project

```bash
gcloud auth login
gcloud projects create ma-gatekeeper-prod --name="MA Gatekeeper"
gcloud config set project ma-gatekeeper-prod
```

Then in **Console → Billing → Link a billing account** to the project. The $300 free-trial credit is fine, but the link **must exist** or Cloud Run deploy fails.

### 1.2 Enable all required APIs (one command)

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com
```

> `cloudbuild` is included because the Dockerfile-based deploy in §11 uses Cloud Build.

### 1.3 Local auth for dev runs (needed for §3–§7)

```bash
gcloud auth application-default login
```

This is what `GOOGLE_GENAI_USE_VERTEXAI=TRUE` reads when you run scripts locally.

### 1.4 ⚠️ Request the Vertex Gemini 3 Pro quota bump — **DO THIS FIRST**

**Console → IAM & Admin → Quotas & System Limits** → filter service `aiplatform.googleapis.com`, metric **"online prediction requests per minute"** for `gemini-3-pro` in `us-central1` → **Edit Quotas** → request a bump → submit.

- 24–48h turnaround.
- If it doesn't land before **June 11**, the live multi-pane demo will `429` — which is exactly why §10 has you pre-record a fallback run.

### 1.5 Devpost payment eligibility

Log in to Devpost → **profile → Tax/payment information** → complete the **W-9 (US)** or **W-8BEN (non-US)** equivalent.

> A $5K prize cannot be paid without this. **Confirm before submission, not after winning.**

### 1.6 Argilla on Hugging Face (for §6 annotation)

1. Create a free HF account if you don't have one.
2. **HF → Spaces → Create new Space → Docker → Argilla template → Create.** Wait for it to boot.
3. Note the **Space URL** + the default `owner` / `password` (**change the password**). You'll import JSONL here in §6.

### 1.7 Demo passcode into Secret Manager

```bash
printf 'pick-a-real-passcode' | gcloud secrets create demo-passcode --data-file=-
```

This becomes `DEMO_PASSCODE`. It must also appear in the Devpost description per §11.

### 1.8 (Optional) Domain

Only needed for the "we own the URL" story. Buy a domain, then map `phoenix.your-domain.com` in §2.2. Otherwise skip — Cloud Run default URLs work.

---

## §2 — Phoenix Self-Hosted on Cloud Run

### 2.1 Deploy Phoenix

Follow the GCP guide end-to-end. In short: it deploys the `arizephoenix/phoenix` container to Cloud Run with a Postgres backend (Cloud SQL) so traces persist.

> Use `--min-instances=1` so it doesn't cold-start during judging.

### 2.2 (Optional) Reverse-proxy to your subdomain

**Console → Cloud Run → your Phoenix service → Custom Domains → Add Mapping → `phoenix.your-domain.com`.** Add the DNS records it shows you at your registrar. Skip if you're using the default `*.run.app` URL.

### 2.3 Generate Phoenix API key → Secret Manager

In the Phoenix UI → **Settings → API Keys → Create.** Then:

```bash
printf 'px_live_xxx' | gcloud secrets create phoenix-api-key --data-file=-
```

### 2.4 Record the env values you'll inject at §11 deploy

From `.env.example`, the agent service needs these pointing at your Phoenix:

| Env var | Value |
| --- | --- |
| `PHOENIX_COLLECTOR_ENDPOINT` | `https://phoenix.your-domain.com` (or the `run.app` URL) |
| `PHOENIX_API_KEY` | from 2.3 |
| `PHOENIX_PROJECT` | `ma-gatekeeper` |
| `PHOENIX_MCP_BASE_URL` | same Phoenix URL |
| `PHOENIX_MCP_API_KEY` | same key (used by the Reflector's MCP toolset) |

### 2.5 Validate the iframe embed (decision gate)

Open Phoenix in a browser, then try embedding a trace URL in an `<iframe>`.

> If Phoenix sends `X-Frame-Options: DENY` / a restrictive CSP, the embed will be blank — that's the trigger to fall back to the custom trace-card (rendered against `design/claude-design-output/colors_and_type.css`). **Decide this now, not on demo night.** If you hit this, flag it and we'll wire the trace-card fetch.

---

## §3 — SDK Sanity Checks (after deps install)

Set up the local env once:

```bash
cd ma_gatekeeper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # fill in the PHOENIX_* + GOOGLE_CLOUD_* values
```

Then run the four boundary checks from `HANDOFF.md` — each must return with **no exception**:

```bash
python -c "from phoenix.evals import LLM; LLM(model='gemini-3-pro', provider='vertexai')"
python -c "from phoenix.client import Client; Client().annotations.add_span_annotation"
python -c "from google.adk import LlmAgent, ParallelAgent, SequentialAgent"
python -c "from google.adk.tools.mcp_tool import MCPToolset, StdioServerParameters"
```

> If check #2 raises `AttributeError` (i.e. the installed client exposes `client.spans.add_annotation` instead), **don't fix it by hand** — paste the error and we'll patch the SDK boundary in `agent/router.py` + `agent/reflector.py` (one line each). The README says the non-deprecated path is `client.spans.add_span_annotation`, so a mismatch here is a real version-drift signal worth catching now.

Also run the offline test suite to confirm nothing is broken locally:

```bash
.venv/bin/python -m pytest tests/ -v   # expect 208 passing
```

---

## §4 — Allow-list Verification (needs live SEC network)

```bash
cd ma_gatekeeper
export SEC_EDGAR_USER_AGENT="hugo.majerczyk@proton.me MA-Gatekeeper"
python -m scripts.verify_allow_list
```

The script sets the SEC identity from `SEC_EDGAR_USER_AGENT` (it exits with code `2` and a clear message if that env var is missing), probes each of the 5 CIKs, prints a table, and exits non-zero if any row is not `OK`.

> **If a row fails:** edit `agent/allow_list.py`, swap the failing deal (suggested replacement: **Capital One / Discover Financial Services 2025**), re-run until all 5 print `OK`. Then flag it so the README "Demo Scope" paragraph naming the deals gets updated.

After §11 deploy, set `VALIDATE_ALLOW_LIST_ON_BOOT=1` in the Cloud Run env so the lifespan probe runs in production too (keep it `0` in dev so tests stay offline).

---

## §5 — Live Eval Runs (needs Vertex + Phoenix up)

### 5.0 ⚠️ Required environment (route to Vertex + Gemini 3.1 Pro)

Every `--live` / `PORTFOLIO_LIVE=1` run needs these four vars. They are now
baked into **`.venv/bin/activate`**, so `source .venv/bin/activate` sets them
automatically — you only need to export by hand in a shell where the venv
isn't active:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=TRUE      # use Vertex (ADC), NOT the Developer API key
export GOOGLE_CLOUD_PROJECT=test-ec90e     # your GCP project id (bills the $300 credit)
export GOOGLE_CLOUD_LOCATION=global        # gemini-3.1-pro-preview is GLOBAL-ONLY
export GEMINI_MODEL=gemini-3.1-pro-preview # the model the whole app now defaults to
```

> **`GOOGLE_CLOUD_LOCATION=global` is not optional.** `gemini-3.1-pro-preview`
> is served only from Vertex's **global** endpoint — a regional location like
> `us-central1` returns `404 NOT_FOUND` for this model. (This is distinct from
> the Cloud Run `--region`, which stays `us-central1`; see §11.)
>
> **No `GOOGLE_API_KEY`.** A Developer-API key hits a separate quota/billing
> track the $300 GCP credit does *not* cover, and exercises a different code
> path than production. Keep it as an emergency fallback only.

`GEMINI_MODEL` is the single source of truth for the model: every agent
(`agents.py`, `portfolio_analyst.py`, `reflector.py`, `evaluators.py`,
`citation_linker.py`) reads it, falling back to `gemini-3.1-pro-preview`.
Change the model in one place — this env var — never per-file.

### 5.1 Get the datasets locally first

```bash
cd ma_gatekeeper
python -m scripts.download_datasets --out data/   # CUAD, MAUD, EDGAR samples
```

### 5.2 The `--live` wrapper

> **Status:** the `make_live_agent` wrappers in `eval_maud_mcq.py` + `eval_cuad_spans.py` and `make_live_portfolio` in `agent/portfolio_analyst.py` are **wired** (shared runner: `scripts/_live_agent.py`). Mock stays the CI default; live is opt-in via `--live` / `PORTFOLIO_LIVE=1`.

```bash
# MAUD MCQ track (burns quota — explicit opt-in):
python -m scripts.eval_maud_mcq --live \
    --dataset data/maud --out maud_mcq_eval.json \
    --baselines configs/maud_published_baselines.json

# CUAD spans track:
python -m scripts.eval_cuad_spans --live \
    --dataset data/cuad --out cuad_spans_eval.json
```

> The `--baselines` JSON is yours to populate from the MAUD paper — the script refuses to fabricate baseline rows; it errors if the path doesn't exist.

### 5.3 Calibration (produces `thresholds.json`)

First do a full Internal-30 inference run that writes per-finding `(h.score, f.score)` pairs to a CSV (the live agent path from 5.2 does this against Phoenix), then:

```bash
python -m scripts.calibrate --input findings.csv --out thresholds.json \
    --reliability-h reliability_h.png --reliability-f reliability_f.png
```

> `--input` is a CSV of judged findings; `--out` defaults to `thresholds.json` (matches `THRESHOLDS_JSON` in `.env`).

---

## §6 — Internal-30 Annotation (15–25h human legal judgment)

This is the irreducible human work — the value is **you adjudicating spans**. Budget ~5–10 min/span across ~150 spans; spread it, don't burst it.

### 6.1 Pass A — Gemini pre-labels (temperature 0, deterministic)

```bash
cd ma_gatekeeper
python -m scripts.annotate prelabel \
    --input data/edgar/ \
    --output data/internal30/prelabels.jsonl
```

### 6.2 Adjudicate in Argilla

1. In your Argilla Space, create a dataset, import `data/internal30/prelabels.jsonl` (SpanQuestion format).
2. Go span by span: **accept / correct / reject** each pre-labeled span against the actual contract text. This is the human-judgment step — no automation.
3. Export the adjudicated set back out when done.

### 6.3 Pass B — independent second pass on 10 contracts (for κ)

```bash
python -m scripts.annotate prelabel \
    --input data/edgar/ --limit 10 --seed 7 --temperature 0.7 \
    --output data/internal30/prelabels_b.jsonl
```

> `--temperature 0.7` is deliberate (vs pass A's temp 0) so κ reflects real annotator disagreement, not two identical deterministic runs. Adjudicate this pass in Argilla too.

### 6.4 Compute Cohen's κ

```bash
python -m scripts.annotate kappa \
    data/internal30/prelabels.jsonl data/internal30/prelabels_b.jsonl
```

Prints `Cohen's kappa: 0.XXXX`. Put that number in the README framed as **"procedural inoculation, not strong evidence of quality"** (the wording is already drafted there).

---

## §7 — Reflector Live Wiring + Cloud Scheduler

> Do this **after** §11 deploy, because the OIDC audience must equal the deployed Cloud Run service URL.

### 7.1 Create a service account for the scheduler to impersonate

```bash
gcloud iam service-accounts create reflect-invoker \
    --display-name="Cloud Scheduler -> /reflect"

# allow it to invoke the deployed agent service:
gcloud run services add-iam-policy-binding ma-gatekeeper \
    --region=us-central1 \
    --member="serviceAccount:reflect-invoker@ma-gatekeeper-prod.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

### 7.2 Create the nightly cron hitting `/reflect`

```bash
SERVICE_URL=$(gcloud run services describe ma-gatekeeper --region=us-central1 --format='value(status.url)')

gcloud scheduler jobs create http reflect-nightly \
    --location=us-central1 \
    --schedule="0 3 * * *" \
    --uri="${SERVICE_URL}/reflect" \
    --http-method=POST \
    --oidc-service-account-email="reflect-invoker@ma-gatekeeper-prod.iam.gserviceaccount.com" \
    --oidc-token-audience="${SERVICE_URL}"
```

> **Critical:** `--oidc-token-audience` must exactly match `REFLECT_OIDC_AUDIENCE` set in the Cloud Run env (§11). The server fails closed with a `503` if they don't match (on Cloud Run, empty audience → every `/reflect` returns `503`).

### 7.3 Fire one cycle manually and verify

```bash
curl -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    "${SERVICE_URL}/reflect"
```

Then open Phoenix → confirm a new **prompt version** and **two experiment runs** (regression set + frozen fold-5) landed. This is the end-to-end proof of **Arize Hooks 4/5/6/7** — the judge will look for exactly this.

---

## §8 — README Results-Table Markers

### 8.1 Add the markers

> **Status:** the markers are already present at `README.md:259`:
>
> ```html
> <!-- BEGIN_RESULTS_TABLE -->
> <!-- END_RESULTS_TABLE -->
> ```

### 8.2 Splice the table once eval JSONs exist

```bash
cd ma_gatekeeper
python -m scripts.build_readme_table \
    --calibrate thresholds.json \
    --maud maud_mcq_eval.json \
    --cuad cuad_spans_eval.json \
    --update-readme README.md
```

> Partial-input-tolerant — run it as each JSON lands; missing tracks render a "Not yet available" placeholder.

---

## §9 — Reflector Pre-seed (48h before recording → do by tonight/tomorrow)

```bash
cd ma_gatekeeper
python -m scripts.seed_reflector --show-weak   # dry-run: prints the weak template, no Phoenix writes
python -m scripts.seed_reflector --commit       # upserts strong=candidate FIRST, then weak=production
```

> The `--show-weak` path performs **no writes** and tells you to re-run with `--commit`. Then let the Reflector run twice: once via the §7.2 cron firing overnight, and trigger one manually with the §7.3 curl. This manufactures a genuine **candidate-vs-production delta** so demo night shows a real auto-promotion. The disclosure wording is already in README + `docs/devpost.md` — no edit needed.

---

## §10 — Demo Recording (physical, yours)

Follow `docs/demo_script.md` (**NOT** `plan.md` §8 — superseded). Detailed prep:

- [ ] **Stopwatch-rehearse on a real run** — the beat timings (the 25s cmd+click hold at 1:30–1:55, the 30s climax at 2:30–3:00) are designed, not measured. First rehearsal tells you what to trim.
- [ ] **Caption rendering test** — render the on-screen pre-seed caption (Inter Medium 500 @ 14px) on a 1440p frame over a bright Phoenix backdrop. If it reads light, bump to Inter 600 (same `fontSize.small` token, no other change).
- [ ] **Capture a "canonical good" rehearsal take** where the Reflector log shows all three: `Promotion gates passed: <diag>`, `PROMOTED candidate … → tag=production`, and the Phoenix prompts-list showing `production` pointing at the just-promoted version. Fallback row 3 in the script depends on having this in the can.
- [ ] **Re-verify the log-string citations haven't drifted** — `_LOG.info(...)` at `reflector.py:760` and `:851` vs `demo_script.md:157`. Anchored citations silently rot under refactors.
- [ ] **Pre-load Phoenix** in a second split-screen window so the cmd+click reveal is instant, not a loading spinner.
- [ ] **Pre-record one full successful EDGAR run** as the live-demo fallback (fallback row 1).
- [ ] **Close the video on the auto-promotion event** in Phoenix Experiments — not the static results table.
- [ ] **Upload to YouTube** as **Public** OR **"Unlisted with link accessible"** — never "Unlisted restricted." Devpost has DQ'd projects for inaccessible videos.

---

## §11 — Deploy + Devpost Submission

### 11.1 Push secrets the service reads

> Already created: `demo-passcode`, `phoenix-api-key`. Grant the Cloud Run runtime SA access:

```bash
PROJECT_NUMBER=$(gcloud projects describe ma-gatekeeper-prod --format='value(projectNumber)')
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for s in demo-passcode phoenix-api-key; do
  gcloud secrets add-iam-policy-binding $s \
    --member="serviceAccount:${RUNTIME_SA}" --role="roles/secretmanager.secretAccessor"
done
gcloud projects add-iam-policy-binding ma-gatekeeper-prod \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/aiplatform.user"
```

### 11.2 Deploy the agent service (uses your Dockerfile)

> **Two different "locations" here — don't conflate them:**
> - `--region=us-central1` is where the **Cloud Run service** runs.
> - `GOOGLE_CLOUD_LOCATION=global` is the **Vertex model endpoint** that serves
>   `gemini-3.1-pro-preview` (regional = `404`). Set it to `global` even though
>   the service deploys to `us-central1`.
> - `GEMINI_MODEL=gemini-3.1-pro-preview` is passed explicitly so prod uses the
>   same model as local (the code default matches, but pin it to be safe).

```bash
cd ma_gatekeeper
gcloud run deploy ma-gatekeeper \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --min-instances=1 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=test-ec90e,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=gemini-3.1-pro-preview,GOOGLE_GENAI_USE_VERTEXAI=TRUE,PHOENIX_COLLECTOR_ENDPOINT=https://phoenix.your-domain.com,PHOENIX_PROJECT=ma-gatekeeper,PHOENIX_MCP_BASE_URL=https://phoenix.your-domain.com,SEC_EDGAR_USER_AGENT=hugo.majerczyk@proton.me MA-Gatekeeper,CORS_ALLOW_ORIGINS=https://your-frontend-origin,VALIDATE_ALLOW_LIST_ON_BOOT=1,REFLECT_OIDC_AUDIENCE=PLACEHOLDER" \
  --set-secrets="DEMO_PASSCODE=demo-passcode:latest,PHOENIX_API_KEY=phoenix-api-key:latest,PHOENIX_MCP_API_KEY=phoenix-api-key:latest"
```

Then capture the URL and **re-deploy once** with `REFLECT_OIDC_AUDIENCE` set to that exact URL (chicken-and-egg: the audience must equal the service's own URL):

```bash
SERVICE_URL=$(gcloud run services describe ma-gatekeeper --region=us-central1 --format='value(status.url)')
gcloud run services update ma-gatekeeper --region=us-central1 \
  --update-env-vars="REFLECT_OIDC_AUDIENCE=${SERVICE_URL}"
```

> Now go back and do **§7** (scheduler) with this URL.

### 11.3 Smoke-test the deploy

```bash
curl "${SERVICE_URL}/health"   # NOT /healthz — see note below
curl -H "X-Demo-Passcode: pick-a-real-passcode" "${SERVICE_URL}/allow-list"
```

> ⚠️ **`/healthz` is poisoned at the Google edge on this service** — the exact
> path `/healthz` returns a GFE HTML 404 that never reaches the container
> (novel paths reach the app fine; survives revisions; both `*.run.app` URLs).
> The app exposes `/health` and `/livez` aliases (same handler) as un-poisoned
> health paths — use those for smoke-tests / liveness probes. The app is
> healthy regardless (`/docs` 200, `/allow-list` 401 auth-gated).

> The passcode goes in the `X-Demo-Passcode` header, **never** the query string — query passcodes leak to access logs.

### 11.4 Devpost form checklist

- [ ] **Arize track explicitly selected** — the partner prize depends on it.
- [ ] Gallery image / thumbnail uploaded.
- [ ] **"Built with" tags:** Google Cloud, Gemini 3, Agent Development Kit, Arize, Phoenix, MCP, Cloud Run, Vertex AI.
- [ ] Team members field populated.
- [ ] All **7 text sections** (drafts in `docs/devpost.md`) — each 100–300 words: Inspiration, What it does, How we built it, Challenges, Accomplishments, What we learned, What's next.
- [ ] AI-generated-content disclosure (you use Gemini extensively).
- [ ] Demo Scope paragraph + Reflector pre-seeding disclosure pasted into the description.
- [ ] Passcode in the Devpost description, not just the README (**triple-check**).
- [ ] Backup Phoenix screenshot deck linked (in case Phoenix cold-starts during judging).

### 11.5 Final

- [ ] Confirm both Cloud Run services (agent + Phoenix) are at `--min-instances=1`.
- [ ] Submit by **June 10 EOD** for a 24h buffer.
- [ ] Spot-check `${SERVICE_URL}` hourly through the evening of **June 11**; if Phoenix goes down, link the backup screenshot deck from the description.
