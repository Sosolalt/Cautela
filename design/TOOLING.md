> **⚠ SUPERSEDED — 2026-06-08.** The canonical design system is now [`design/claude-design-output/`](claude-design-output/README.md); index [`design/SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md). The skill / MCP / library decisions captured here are still load-bearing for the design *track's* tooling setup (R3F, Spline, Rive, Lottie remain forbidden), but the rationale was sized to a now-retired creative direction. Audit-trail only.

---

# Tooling Reconnaissance — Phase 0 Output

> Canonical list of skills, MCP servers, plugins, external reference libraries, type acquisition, and tooling tempations explicitly killed for the design track.
> Source: `design/PLAN.md` §0.
> Locked: 2026-05-24. Bias: install nothing unless it removes friction already felt.
> Review history: Round A multi-reviewer pass (Frontend Architect, PM, Art Director, Plan-Fidelity Skeptic) — all NOT VALIDATED on first pass; this revision applies their consolidated findings. See `design/REVIEW_NOTES.md` Phase-0 section.

---

## 1. Claude skills audit (§0.1)

All skills below enumerated against the live skills list in this environment on 2026-05-24.

| Skill | Available | Decision | Rationale |
|---|---|---|---|
| `expert-review-loop` | ✅ | **Adopt** | Run twice: (a) post-`PLAN.md` *(already done — see [REVIEW_NOTES.md](REVIEW_NOTES.md), 3 rounds, all 5 reviewers VALIDATED)*; (b) Day-7 pre-deploy on the staged build. |
| `verify` | ✅ | **Adopt** | Final-pass browser drive of the deployed Vercel preview to catch jank invisible in code review. |
| `simplify` | ✅ | **Adopt** | Run after Motion Designer's animation work lands — reuse audit + bundle bloat check before the §6.2 size-limit CI gates fire. |
| `run` | ✅ | **Adopt** | Standard "launch dev server and look at it" loop during Days 3–6. |
| `project-log` | ✅ | **Continue** | `PROJECT_LOG.md` already in flight at the repo root — log design decisions there, not in a parallel design log. |
| `review` | ✅ | **Defer** | User-triggered PR review tool — not for the marketing page. |
| `security-review` | ✅ | **Defer** | Run before deploy of the live `/reflect` route (product-track concern, ~design-Day-14), **not** the marketing page. |
| `claude-api` | ✅ | **Skip** | Marketing site does not call the Anthropic SDK. |
| `init` | ✅ | **Skip** | Repo already has `CLAUDE.md` / project context. |
| `update-config` | ✅ | **Skip** | Harness config, not design. Revisit only if hooks become needed. |
| `keybindings-help` | ✅ | **Skip** | Harness, not design. |
| `fewer-permission-prompts` | ✅ | **Skip** | Per PLAN §0.1 verbatim (Round-A Skeptic flagged silent drift in v1; reverted). |
| `loop` | ✅ | **Skip** | No recurring task — one-shot build. |
| `schedule` | ✅ | **Skip** | No cron need for the marketing page. |

**Net Adopt**: `expert-review-loop`, `verify`, `simplify`, `run`, `project-log` (5 skills) — matches §0.1 exactly.

---

## 2. MCP server reconnaissance (§0.2)

### 2.1 Currently wired up

Source: `~/.claude/mcp-needs-auth-cache.json` + `~/.claude/plugins/installed_plugins.json` + project-level `.mcp.json` (absent).

| MCP server | Source | Decision |
|---|---|---|
| `claude.ai Gmail` | user-level OAuth | **Skip** — irrelevant to design. |
| `claude.ai Google Calendar` | user-level OAuth | **Skip** — irrelevant. |
| `claude.ai Google Drive` | user-level OAuth | **Possible** — only if we end up storing reference screenshots in a shared Drive folder. Default off. |

No project-level `.mcp.json`. No design-relevant MCP servers are currently installed.

### 2.2 Design-relevant MCPs evaluated

Round-A Skeptic correctly flagged that v1 declared a search without performing one. The honest scope of an in-context search: I can enumerate MCPs **the user already has visible** (above); I cannot crawl `glama.ai`/`smithery.ai`/`mcpservers.org` registries from this agent context. The recommendations below are based on PLAN §0.2's named candidates plus the Art Director's Round-A escalation; **installation requires a user action** (no MCP server can be added by this agent alone).

| MCP | What it would give us | Decision | Why / user-action |
|---|---|---|---|
| **Figma MCP** | Round-trip Figma ↔ code | **Skip** | If hero ships as Rive (candidate #2), the asset lives in the Rive web editor — Figma adds no leverage and Rive's interaction model doesn't round-trip cleanly through Figma. If hero falls back to candidate #5 (editorial typographic), assets are CSS, not Figma frames. |
| **Image-gen MCP** (Imagen / Nano-banana / DALL·E) | Bespoke hero stills, OG card, 404 art, the §6.4 "engineered screenshot frame" | **Recommend install** *(user action required — see §2.4)* | Art Director (Round A) raised the real risk: PLAN §6.4 names a literal still (Wilson-LB headline + Block badge + span ID in mono), §4.4 wants `@vercel/og` programmatic OG, §5.4 wants a designed 404. Deferring to Day-3 risks discovering iteration latency on the moneymoment day. Zero-cost insurance to install now. |
| **Playwright / Chrome DevTools MCP** | Screenshot ~16 hand-picked reference sites + Awwwards/SiteInspire mining; final QA pass | **Recommend install** *(user action required — see §2.4)* | Art Director (Round A) flagged: 16 sites × ~4 captures = ~64 manual shots is a real Day-1 tax. PLAN §1.4 explicitly says INSPIRATION.md should *embed screenshots* "grouped by what we're stealing." The `verify` skill covers Day-7 — Playwright's value is Phase 1. |
| **Lottie / Rive MCP** | Asset pipeline for vector motion | **Skip** | Rive ships its own runtime + web editor; an MCP wrapper adds no leverage over `npm i @rive-app/react-canvas`. |
| **EDGAR / EdgarTools MCP** | Live filing fetch for demo deals | **Skip — product-track concern** | Already in scope for `ma_gatekeeper/`; marketing page only links to demo. Out of design-track scope (acknowledged: this row evaluates an MCP not in PLAN §0.2's list — kept for explicit ruling). |

### 2.3 Community plugin reconnaissance

Checked `~/.claude/plugins/installed_plugins.json`:

- `caveman@caveman` — installed at user scope, unrelated to design. **Leave alone.**

I cannot search the broader Claude Code plugin marketplace from this context. PLAN §0.2.3's targets (shadcn/ui registry helpers, Tailwind class-merge linters, Framer Motion snippet libraries, axe-core plugins) would benefit from a manual user-side `/plugin search` pass. **Recommendation: skip even after a search** — every plugin is a permanent dependency on someone else's release cadence, and the build-out is one week. Friction does not yet justify it.

### 2.4 Net MCP install plan + user-action queue

**No MCPs can be installed by this agent.** The plan now defers two design-relevant installs to the user. If you (Hugo) want them:

1. **Image-gen MCP** — pick one of Imagen / Nano-banana / a hosted Stable Diffusion MCP; install via Claude Code's MCP settings. Use case: §6.4 still, §4.4 OG image, §5.4 404 art.
2. **Playwright MCP** *(or Chrome DevTools MCP)* — install via Claude Code's MCP settings. Use case: Phase 1 inspiration mining (~64 reference captures); reusable for Day-7 `verify` pass.

Both are **optional Day-1 unlocks**. The design track can proceed without them — manual reference captures are slower but feasible.

---

## 3. Reference asset libraries (§0.3) — bookmarked, not installed

Pull patterns from these; never depend on them.

- **Aceternity UI** — https://ui.aceternity.com/ — animated hero patterns (spotlight, sparkles, wavy backgrounds), permissive copy-paste.
- **Magic UI** — https://magicui.design/ — marquees, animated beams, terminal animations, number tickers.
- **shadcn/ui** — https://ui.shadcn.com/ — primitives. **In stack** via `components/ui` convention.
- **Motion Primitives** — https://motion-primitives.com/ — Framer Motion presets.
- **Cult UI** — https://www.cult-ui.com/ — premium-feeling component variants.
- **React Bits** — https://www.reactbits.dev/ — text effects (decrypt, scramble, gradient sweeps).
- **Eldora UI** / **Syntax UI** — additional pattern libraries to cherry-pick from.

Frontend Architect maintains a "borrowed patterns" registry inside `design/STACK.md` (Phase-4 deliverable) so we never end up with the *exact* same hero as every other 2026 Awwwards entry.

---

## 4. Scaffold cleanup (§0.4) — Day-1 prerequisite status

| # | Task | Status (2026-05-24) | Owner | Notes |
|---|---|---|---|---|
| 1 | **Next 14.2.5 → 15** decision | ⏸ **Pin 14.2.5, decision deferred to STACK.md Day-2 EOD** | Frontend Architect | PLAN §0.4 explicitly permits "or pin and document." Upgrade now risks breaking [pdf-pane.tsx:36-48](../ma_gatekeeper/frontend/components/pdf-pane.tsx#L36-L48) — Next 15 / Turbopack changed `new URL(..., import.meta.url)` semantics for worker scripts; `react-pdf@9.1.1` is sensitive. Day-2 STACK.md decision must include a Next-15-features-we-need-or-don't audit (no PPR / `after()` / Turbopack call-sites today). |
| 2 | Tear out lane-color hex codes from `tailwind.config.ts` | ⏸ **Deferred to Phase-5 commit, NOT completed today** | Art Director (re-derives via `tokens.ts`) | Round-A Skeptic correctly noted "annotated ≠ tear out." Hex codes remain at [tailwind.config.ts:15-19](../ma_gatekeeper/frontend/tailwind.config.ts#L15-L19) because [findings-pane.tsx:26-28](../ma_gatekeeper/frontend/components/findings-pane.tsx#L26-L28) consumes them; deletion lands in the same commit as `design/tokens.ts` (~Day 3). Annotation prevents new references; it does not satisfy the plan's "tear out" verb. |
| 3 | Audit `react-pdf` / `pdfjs-dist` import shape | ✅ **Verified dynamic on the console side; marketing-side bleed-check outstanding (deferred — no `/` marketing bundle exists yet)** | Frontend Architect | [pdf-pane.tsx:30-46](../ma_gatekeeper/frontend/components/pdf-pane.tsx#L30-L46) uses `useState` + `import("react-pdf").then(...)` — webpack splits it. `transpilePackages` in [next.config.mjs:5](../ma_gatekeeper/frontend/next.config.mjs#L5) is a *compilation* directive, not a bundling one (does not defeat splitting). When the `/console` route is carved out, the §6.2 size-limit CI must gate "zero pdfjs bytes on `/`." |
| 4 | `X-Frame-Options` / `frame-ancestors` on `/reflect` | ✅ **SET today — `frame-ancestors 'none'` + `X-Frame-Options: DENY` defaults** | Frontend Architect | [agent/server.py:392+](../ma_gatekeeper/agent/server.py#L392) registers `_frame_lockdown` middleware at lines 402–409. Frontend Architect Round-A finding: leaving an OIDC-protected route un-framed-by-default is a security gap, not a design decision. The default is `DENY`/`'none'`; if iframe is ever resurrected, widen to the explicit marketing origin (never `*`). Coupled with §4.4 below — the iframe spike has been formally retired. **Outstanding (Skeptic Round-B polish)**: add a 3-line pytest in `ma_gatekeeper/tests/test_server_stream.py` asserting both headers land on a real 200/4xx/5xx response — until that lands, "set" is a code-read claim, not a verified behavior. Owner: Frontend Architect, Day-2 morning. |

### 4.1 Mechanical CI / scaffold scaffolding (added Round A — Frontend Architect)

| # | Task | Status | Owner | Notes |
|---|---|---|---|---|
| 5 | `.nvmrc` pinning Node version | ✅ **Added** ([`.nvmrc`](../ma_gatekeeper/frontend/.nvmrc) → `20.11.1`) | Frontend Architect | First Vercel deploy must resolve the same Node major as local. Pinned to current Vercel default LTS. |
| 6 | Lockfile (`package-lock.json` / `pnpm-lock.yaml`) | ⚠ **Missing — user action required** | User (run `npm install` in `ma_gatekeeper/frontend/` once) | `package.json` ships `^14.2.5` with no lockfile. The "pin" is theater until the lockfile lands. This agent will not run `npm install` unprompted (large side effect; modifies `node_modules/`). Run once, commit the lockfile, and the Day-7 Vercel deploy will resolve the same transitive tree as local. |
| 7 | `size-limit` baseline + CI gate | ⚠ **Config Day-2 morning — committed clock-time to close the structural deferral loop** | Frontend Architect | PLAN §6.2 names this as a CI gate (180KB above-fold / 350KB route-total). Round-B Frontend Architect correctly flagged that "wait for the marketing route" is a self-perpetuating rationalization (no marketing route exists until Phase 4 lands → gate never fires). **Commitment**: Day-2 morning (2026-05-25 12:00) — once lockfile lands, baseline against the current `/console` route with a generous ceiling (current bundle size + 20%) so the gate *exists* and prevents regression. Tighten the budget to PLAN §6.2's 180KB / 350KB targets when `/` marketing route lands in Phase 6. A loose-but-present gate beats a tight-but-absent one for the next 5 days. |
| 8 | `next-bundle-analyzer` baseline | ⚠ **Same as #7** | Frontend Architect | Capture a pre-marketing baseline at Day-2 EOD. |

### 4.2 Deferred items — clock-times and owners (revised Round A per PM)

PM Round A correctly flagged that "Day-1 spike" and "~Day 3" are vibes. Restated as ISO dates + named artifacts:

| Item | Owner | Deadline (ISO, Europe/Paris) | Artifact path | Day-2-morning checkpoint |
|---|---|---|---|---|
| Next 15 upgrade decision | Frontend Architect | 2026-05-25 23:59 | `design/STACK.md` | Supervisor confirms STACK.md exists with decision recorded. |
| `tokens.ts` shipped → lane-color teardown commit | **Art Director** (owns `tokens.ts` per PLAN §5) | 2026-05-27 23:59 | `design/tokens.ts` + same-commit edit to `ma_gatekeeper/frontend/tailwind.config.ts` | Supervisor verifies tokens.ts exists Day-3 morning. |
| Lockfile commit | User (one `npm install`) | 2026-05-25 12:00 | `ma_gatekeeper/frontend/package-lock.json` | Supervisor verifies lockfile in tree Day-2 morning. |
| `size-limit` + analyzer wiring | Frontend Architect | 2026-05-25 23:59 | `.github/workflows/tests.yml` + `.size-limit.json` | Day-3 morning. |
| Type-acquisition decision (see §6) | Art Director | 2026-05-24 23:59 (today — Day 1 EOD) | `design/SYSTEM.md` stub + `design/TYPE.md` | Day-2 morning, before §5.2 Lane A/B lock. |

### 4.3 Iframe spike: kill-switch FIRED (Round A — PM + Skeptic finding)

PLAN §6.1 Day-1 cut-trigger: *"OIDC-in-iframe spike unresolved by EOD → iframe permanently off the table."* PLAN §6.1 kill-switches summary: *"OIDC-in-iframe survival — Day-1 EOD spike. If unresolved, iframe permanently off the table — mock-only, no more deliberation."*

**Honest status of the six "Resolved decisions" sub-conditions (a–f):**

| Gate | Question | Verdict | Evidence |
|---|---|---|---|
| (a) Same-origin embed | Marketing and `/reflect` share an origin? | ⚠ **Not yet** — current scaffold has `/reflect` on FastAPI (likely `api.<domain>`), marketing on Next at `/`. PLAN §4.1 *would* unify them, but the unification has not happened — `ma_gatekeeper/frontend/` does not yet proxy or co-host `/reflect`. | grep of `frontend/app/` shows no `/reflect` route or proxy. |
| (b) `X-Frame-Options`/`frame-ancestors` set | Headers in place? | ✅ **Now set — `DENY` / `'none'`** | [agent/server.py:392+](../ma_gatekeeper/agent/server.py) `_frame_lockdown` middleware (added today). |
| (c) OIDC survives Safari ITP under iframe | Can a third-party-cookie-blocked Safari complete the Google OIDC flow inside an iframe? | ❌ **CANNOT TEST from this agent context** — requires a real Safari browser, a deployed marketing-origin page, and a live Google IDP round-trip. None are available here. Per PLAN §6.1 cut-trigger, "unresolved by EOD" → kill. |
| (d) Mobile fallback (<768px) | Static screenshot + open-in-new-tab below 768? | ❌ Not designed. |
| (e) Skeleton + warm-ping for Cloud Run cold-start | Mask cold-start latency? | ❌ Not designed. |
| (f) Loading / error / timeout states | All three designed? | ❌ Not designed. |

**Decision (firing the kill-switch per PLAN §6.1)**: **iframe upside-swap is permanently retired.** Design proceeds **mock-only** for the audit-trail section (§6.4). This was already the base case per PLAN's "Resolved decisions" — firing the kill-switch retires *optionality*, not capability. The §6.4 designed mock is now the only path; the "iframe upside swap if `/reflect` lands by Day-6" branch is closed.

Downstream effects locked here:
- `frame-ancestors` stays `'none'` permanently for `/reflect` (no widening planned).
- Day-6 "iframe go/no-go re-confirmation" in PLAN §6.1 → struck.
- §6.4 fallback ("designed playback of a real recorded review") becomes the primary plan.

---

## 5. Phase-1 prerequisites seeded today

- **`design/INSPIRATION.md`** — stubbed today with the §1.2 hand-picked reference table populated. Art Director picks up the screenshot annotation pass Day-1 EOD / Day-2 morning. See file.

---

## 6. Type acquisition — added Round A (Art Director)

PLAN §5.2 (Lane A) names **Migra, Tobias, Söhne Schmal, GT Sectra, Tiempos Headline** for display, and **Berkeley Mono** for mono. **All are paid foundry licenses**, web-use ranging ~$75 (Berkeley Mono personal) to $400-600+ (GT Sectra, Tiempos, Söhne for a single domain web license). PLAN §5.2 locks Lane A/B by **2026-05-25 23:59** and PLAN §5.6 locks the wordmark by **2026-05-26 23:59** — both depend on having the actual font files.

**Decision tree (Art Director owns, Day-1 EOD = 2026-05-24 23:59):**

| Option | Cost | Risk | Verdict |
|---|---|---|---|
| **A. Buy** GT Sectra (display) + Berkeley Mono (mono) + Inter Variable (body, free) for one domain | ~$500-700 total | Funded? Foundry approval latency? | Pick only if user pre-approves the spend today. |
| **B. Free-tier Lane-A equivalent** — **Fraunces** (display serif, OFL, Google Fonts) + **Inter Variable** (body, OFL) + **JetBrains Mono** (mono, OFL) | $0 | Fraunces has the optical-size axis to behave at display weights but lacks Tiempos' contrast/editorial gravity. Honest expectation: ~70% of Lane-A authority at 120-180px hero scale. Must be tested at hero sizes Day-2 morning before §5.2 lock | **Recommended default** unless user signs off on A by EOD today. If hero-scale test fails → escalate to **Option D** before nuclear C. |
| **C. Lane B fallback** — all-sans (Inter + Inter + JetBrains Mono) | $0 | Loses the §5.2 "law-review" GC-credibility move | Nuclear option — only if A, B, AND D all fail. |
| **D. Trial license (added Round B per PM + Art Director)** — most paid foundries (GT, Klim, Pangram Pangram, Commercial Type) offer 7-day evaluation licenses for free. Pull a trial of GT Sectra or Tiempos Headline; ship the hackathon demo on the trial, decide on permanent license post-deadline | $0 (within trial window) | Trial terms typically forbid "production" use; a hackathon-jury demo is the grey area — read the foundry's specific trial ToS before relying on this. Some foundries (Klim) explicitly permit "evaluation" public previews; others don't. | **Use when Option B fails the Day-2 morning hero test.** Day-7 Devpost deadline fits inside the 7-day trial window if pulled Day-2. |

**Cascade**: if no type is in-hand by Day-2 morning, the §5.2 lock slips → §5.6 wordmark slips → Phase-5 design system slips. This is a hard Day-1 EOD blocker. Art Director must commit option A/B/C tonight and write it into `design/SYSTEM.md` (stub) by 23:59.

---

## 7. Temptations explicitly killed (added Round A — Art Director)

Naming dead the tooling temptations that map to PLAN §1.3's anti-references — at the **tooling layer**, so no Phase-1 Builder quietly resurrects them via "this nice MCP/template existed."

- ❌ **Spline MCP** / Spline Community templates → maps to §1.3's "off-the-shelf Spline blob hero with no semantic tie." If 3D ships, it's R3F or Rive against the candidate-#2 contract-stack — never a marketplace import.
- ❌ **Generic gradient generators / "AI gradient" packs** (Mesh.cool defaults, generic UIGradients) → maps to §1.3's "purple-to-pink AI-startup gradient." Mesh gradients live in §5.1's locked palette only.
- ❌ **Framer template marketplace wholesale imports** → entire-template imports kill brand DNA; component-level borrows from §3's libraries are fine.
- ❌ **Lottie marketplace packs** ("AI loader," "data flowing," generic onboarding) — if Lottie ships, it's the bespoke fallback for our agent topology, not a marketplace import.
- ❌ **shadcn "Blocks" wholesale page copy** — primitives yes, full-section copies no.
- ❌ **3D "AI = neurons" templates / Three.js brain demos** → §1.3 "glowing-dot 3D brain."
- ❌ **"Made with AI" badges / Powered-by-Gemini chips** → §1.3 "we wrapped an API" tells; the build-SHA + model-pin console.info (PLAN §7.3) is the *only* model attribution.
- ❌ **Vercel / Next-template wholesale clones** (Next.js Commerce, Nextra, "Precedent," any Vercel-template marketplace landing page) — same failure mode as Framer marketplace wholesale; section-level borrows from §3's libraries are fine, but full-template imports kill brand DNA on Day 1. *(Added Round B — Art Director.)*
- ❌ **AI copy generators** (Copy.ai / Jasper / generic ChatGPT marketing-blurb runs) for any line in `COPY.md` — voice DNA killer; PLAN §2.3 voice rules are unreachable from generic prompts. Copy Lead writes by hand. *(Added Round B — Art Director.)*
- ❌ **Stock icon packs as primary iconography** — Lucide *is* the system per PLAN §5.4, but using Lucide *everywhere* without any custom marks is the generic tell. The §5.4 carve-out for custom illustrations (agent topology, Reflector loop, 404) is the brand-DNA escape hatch — defend it. *(Added Round B — Art Director.)*

If a Phase-1 Builder reaches for any of these, the Art Director's review at section-completion rejects on sight, and the link to this section is the rationale.

---

## 8. What changed vs. PLAN.md §0

This revision (post-Round-A) deviates from the plan's letter in two places. Both are explicit:

1. **Scaffold cleanup task 2** — PLAN says "tear out"; this revision marks it deferred (entanglement with `findings-pane.tsx`). Honest deferral, not silent compliance.
2. **Scaffold cleanup task 4** — PLAN says "confirm or set"; this revision **set** the headers (chose the second option of the disjunction). Compliant.

Plus four explicit additions beyond §0's letter, all justified in-text: §4.1 mechanical scaffolding, §4.3 iframe kill-switch firing, §6 type acquisition, §7 temptations killed.

---

## 9. Next moves (Day-2 morning)

With Phase 0 closed and the iframe kill-switch fired:

- **Frontend Architect**: ship `design/STACK.md` lock by 2026-05-25 23:59. Add `.size-limit.json` + CI step once the lockfile exists.
- **Art Director**: ship type-acquisition decision (A/B/C in §6) tonight → `design/SYSTEM.md` stub; begin Phase-1 inspiration capture against the populated `design/INSPIRATION.md` table.
- **Copy Lead**: begin PLAN §2.1 tagline A/B + §2.2 section copy + GC-FAQ draft answers → `design/COPY.md` by 2026-05-25 23:59.
- **User**: (a) run one `npm install` in `ma_gatekeeper/frontend/` to commit a lockfile; (b) optionally approve image-gen + Playwright MCP installs (§2.4); (c) approve or reject type-acquisition Option A funding by tonight.
