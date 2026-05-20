# HANDOFF — items requiring you (Hugo)

The plan is converged and the codebase is scaffolded. All 23 unit tests
pass. The remaining work falls into items I cannot do for you (anything
needing a credential, a payment method, or a physical recording) and
items I can do but which were lower priority than getting the spine
right (frontend, prompt-engineering iteration).

This file is the explicit list. Items are ordered by the day they
appear in the plan timeline (`plan.md` §7).

## Before D1 (today)

- [ ] Create a Google Cloud project named `ma-gatekeeper-prod` (or
      similar).
- [ ] Set billing on the project (the $300 free-trial credit handles the
      whole hackathon trivially per the GCAB research, but billing must
      be enabled to deploy to Cloud Run).
- [ ] Enable APIs: Vertex AI, Cloud Run, Artifact Registry, Secret
      Manager, Cloud Scheduler.
- [ ] Pick a hosting domain (e.g. `ma-gatekeeper.com`) or use Cloud Run
      default URLs. The "we own the URL" demo story needs a real
      subdomain only if you want it.
- [ ] Devpost account exists; verify the **payment-eligibility profile
      is complete** (W-9/W-8BEN-equivalent) so a $5K win can actually
      be paid — easy to forget and a real failure mode.
- [ ] Decide on a public-passcode for the demo and put it in Secret
      Manager as `demo-passcode`.

## D1–D2 (Phoenix infra)

- [ ] Follow the Pro-Level Agent Observability guide to deploy Phoenix
      self-hosted on Cloud Run:
      https://medium.com/google-cloud/pro-level-agent-observability-deploying-arize-phoenix-on-google-cloud-f07a1576b578
- [ ] Reverse-proxy Phoenix through `phoenix.your-domain.com`. If the
      iframe embed is ugly (validation step on D1), pivot to the
      custom trace-card backup component.
- [ ] Generate a Phoenix API key, put it in Secret Manager as
      `phoenix-api-key`.
- [ ] Save `PHOENIX_COLLECTOR_ENDPOINT` and `PHOENIX_PROJECT` for env-var
      injection at Cloud Run deploy time.

## D3 (ADK quota)

- [ ] **Request a Vertex AI Gemini 3 Pro quota bump** — the default
      QPS limits will 429 a multi-pane demo. This requires a console
      ticket and 24-48h turnaround; don't leave it for D19.

## D5–D9 (annotation)

- [ ] Sign up for Argilla on a Hugging Face Space (free).
- [ ] Annotate ~30 contracts using the LLM-assisted pipeline:
      Gemini pre-labels, you adjudicate. Budget ~5–10 min per span,
      total 15–25 hours spread across D5–D9 (NOT a weekend burst).
- [ ] Double-annotate 10 contracts so Cohen's κ can be reported
      (procedural inoculation, not strong evidence of quality —
      acknowledged in the README).

## D10 (allow-list curation)

- [ ] Hand-pick 5 recent 8-K Exhibit 2.1 filings on EDGAR, each one
      containing at least one Block-tier clause the agent should
      surface. Put their CIKs into `ALLOW_LIST` in `agent/server.py`.
- [ ] Draft the README "Demo Scope" paragraph naming the 5 deals
      (template already in `README.md`).

## D15 (frontend — only if I haven't built it yet)

- [ ] Next.js + shadcn/ui + Tailwind frontend with three-pane layout
      (`react-pdf` left, findings center, Phoenix iframe or custom
      trace-card right).
- [ ] PDF↔trace bidirectional sync — feasible because `Clause.pdf_bbox`
      is populated at D4 and span attributes carry it at D7.

## D18 (Reflector pre-seed)

- [ ] **48 hours before demo recording** (so by D17 evening):
      - Upsert a deliberately weaker "production" prompt for
        `cross_reference` (remove the cross-reference instructions
        from `prompts.py:CROSS_REFERENCE_PROMPT`).
      - Upsert the strong version as "candidate".
      - Let the Reflector run twice naturally.
- [ ] Add the **Reflector pre-seeding disclosure** sentence to the
      README:
      > "Production prompt was deliberately seeded weaker 48h before
      > demo recording so the auto-improvement loop has a real signal;
      > the loop logic itself is unchanged."

## D19 (demo recording)

- [ ] Record the 3-minute demo following the §8 beat structure.
- [ ] Pre-load Phoenix in a second visible window (split-screen) so
      the cmd+click reveal is instant, not an anticlimax.
- [ ] Close the video on the auto-promotion event in Phoenix
      Experiments, not the static results table.
- [ ] Pre-record one full successful EDGAR run as live-demo fallback.
- [ ] Upload to YouTube as **Public** or "Unlisted with link
      accessible" — never "Unlisted restricted" (Devpost has DQ'd
      projects for this).

## D20 (submission)

- [ ] Cloud Run deploy with `min-instances=1` for both the agent
      service and Phoenix.
- [ ] Devpost form:
    - [ ] Arize track explicitly selected (the bucket prize depends on this).
    - [ ] Gallery image / thumbnail uploaded.
    - [ ] "Built with" tags include: Google Cloud, Gemini 3, Agent
          Development Kit, Arize, Phoenix, MCP, Cloud Run, Vertex AI.
    - [ ] Team members field populated.
    - [ ] All 7 standard Devpost text sections (Inspiration, What it
          does, How we built it, Challenges, Accomplishments, What we
          learned, What's next) — each 100–300 words.
    - [ ] AI-generated-content disclosure (we use Gemini extensively).
    - [ ] Demo Scope paragraph and pre-seeding disclosure in the
          description.
    - [ ] Backup Phoenix screenshot deck linked in case the live
          dashboard cold-starts during judging.
- [ ] Warm Cloud Run with `min-instances=1`.
- [ ] Triple-check the passcode is on the Devpost description, not
      just the README.

## D21 (June 10 — buffer)

- [ ] Submit by D20 EOD to leave a 24-hour buffer before June 11
      23:00 GMT+2.
- [ ] Spot-check the hosted URL hourly until the evening of June 11.
- [ ] If Phoenix dashboard goes down, link the backup screenshot deck
      from the Devpost description.

## Items I could have built but didn't (lower priority)

- Next.js frontend — the spine is the agent + Reflector + calibration;
  the UI is week 3 work and depends on visual decisions you'll make
  during the iframe-validation step on D1.
- Cloud Scheduler config (a 1-line `gcloud scheduler` invocation; lives
  with the deploy work, not the codebase).
- Apache 2.0 LICENSE file at the repo root.
- CI workflow (GitHub Actions for the test suite — nice-to-have).

## Sanity checks that should pass before D7 architecture freeze

These verify that the actual installed SDK matches the shapes the code
expects (the architecture/Arize reviewer flagged these explicitly):

1. `python -c "from phoenix.evals import LLM; LLM(model='gemini-3-pro', provider='vertexai')"`
   — no exception.
2. `python -c "from phoenix.client import Client; Client().annotations.add_span_annotation"`
   — attribute exists; if it's `client.spans.add_annotation` instead,
   update `agent/router.py` (one line) and `agent/reflector.py`.
3. `python -c "from google.adk import LlmAgent, ParallelAgent, SequentialAgent"`
   — no import error.
4. `python -c "from google.adk.tools.mcp_tool import MCPToolset, StdioServerParameters"`
   — `MCPToolset(connection_params=StdioServerParameters(...))` is the
   non-deprecated form.

If any of these fail, fix at the SDK boundary in the named file. The
internal logic does not depend on the SDK shape.
