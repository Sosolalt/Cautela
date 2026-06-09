# Website-related updates to `plan.md` — proposed (v3, third-round-reviewed)

> **Status: v3 — three rounds of multi-agent red-team applied, awaiting user sign-off.** Round 1 (PM / brand / frontend feasibility) produced v1. Round 2 (cross-doc / Devpost / impl-detail / hostile juror) produced v2. Round 3 (convergence verifier confirmed 16/16 v2 claims CLOSED + a fresh red-team found 5 net-new ship-blocking nits) produced this v3. The plan below is what we propose to apply to `plan.md` once the user gives the green light.
>
> **Scope of "website" here**: (a) the demo-day product review-app UI in `ma_gatekeeper/frontend/`; (b) the **marketing landing page** (new — absent from current `plan.md`, made possible by `design/claude-design-output/`); (c) demo-video visuals that frame both surfaces; (d) any risk / checklist item gated on UI choices.
>
> **Source of design truth (canonical):** [`design/SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md) → [`design/claude-design-output/README.md`](claude-design-output/README.md) → [`design/claude-design-output/source/design.md`](claude-design-output/source/design.md) → [`design/claude-design-output/colors_and_type.css`](claude-design-output/colors_and_type.css) (canonical for the M&A luxury palette extension: champagne / oxblood / ivory). All proposals below conform to the **Documentary Brutalism** register specified there.

---

## 0. What changed v1 → v2 (Round-2 red-team responses)

| # | Critic (Round 2) | Finding | Fix |
|---|---|---|---|
| 1 | Implementation | **`hero-b.html` is NOT "CSS 3D parallax"** — it loads Three.js (three@0.160.0 CDN) and `hero-scene.js` is **1534 LOC of bespoke WebGL** (page-curl vertex math, staple/paper materials, projection-to-SVG hairline overlay, 7s loop). v1 misrepresented this in §7, §9, §11 and gravely underestimated the port cost. | §7 D16 + §9 marketing-surface + §11 dimensional-layer risk all rewritten to name the actual technology (Three.js). Port estimate raised 4-6h → **10-16h, or drop to SVG-with-depth fallback as the *primary* path** with the WebGL scene as a stretch goal. v2 ships the SVG-with-depth variant by default; WebGL is a D16 PM stretch only if AM is clean. |
| 2 | Devpost + hostile juror | **Hosted Project URL → `/` (marketing)** is an unforced error. Both critics independently flag it: Devpost's "Try It Out" field expects a working agent; a juror clicking the URL and landing on a hero with "Try the demo →" will close the tab. | **v2 flips open question #2**: Hosted Project URL points to **`/review`** (working app with a deal pre-loaded mid-stream — hostile juror's specific suggestion). Marketing landing lives at `/marketing` (or `/about`) **and** is also the demo-video opening; brand exists in the channels jurors *expect* presentation (video, Devpost description, shared screenshots), not where they expect to click into a working tool. |
| 3 | Hostile juror | **`¹ BLOCK 0.42`** reads as "1 BLOCK 0.42" (row index) at 720p thumbnail scale — footnote-marker disambiguation is a 2000ms second-read interaction; jurors give 200ms first-read. Color carries the 200ms recognition; markers carry the second read. v1 made markers load-bearing alone. | §9 product surface adds a **2px lane-color left-edge bar per finding row** (still a brand-legal hairline per `claude-design-output/README.md` §Backgrounds — *"depth through overlap, scale, or a single hairline rule"*). The bar is the 200ms color signal; the marker is the second-read disambiguator. Belt-and-suspenders, both brand-compliant. |
| 4 | Hostile juror | The 0:00-0:05 brand hero in the video reads as "design portfolio" — burns 5s of a 90s attention budget on something that does not look like a working agent. | §8 demo flow rewritten: **0:00-0:03 cold-open on the cmd+click→Phoenix moment** (the actual wedge); brand hero moves to the **closing bookend** at 2:45-3:00 instead. Working-agent proof leads; brand lands as the closer. |
| 5 | Implementation | **The brand-QA grep in v1 is structurally broken.** `\brounded(?!\s|-none)\b` rejects `"rounded px-1.5..."` because the negative lookahead excludes whitespace — so the actual violation at `findings-pane.tsx:61` is *not* caught, while comments in `globals.css` *are*. Same failure at `deal-picker.tsx:25`. | §12 grep rewritten as **two passes** (more readable than nesting): `rg -nP '\bbg-blue\b\|\bshadow-(?!none\b)' ma_gatekeeper/frontend/{app,components}` + `rg -n '\brounded\b' ma_gatekeeper/frontend/{app,components} \| rg -v 'rounded-none'`. v2 explicitly notes the regex was tested against today's tree and flags the two real violations. |
| 6 | Cross-doc | **Footnote-marker → lane mapping breaks the schema.** `RiskFinding.severity` is `info/watch/block`; `GatekeeperDecision.lane` is `auto_clear/escalate/block`. v1 says `¹=Block, ²=Escalate, ³=Auto-Clear` without naming which enum. | §9 explicitly maps the marker to `GatekeeperDecision.lane` (post-routing). Pre-routing streaming state (`RiskFinding.severity`) shows **no marker** until routing assigns a lane — *"the marker appears in the same SSE frame that the lane lands; until then the row is markerless mono, which reads as `pending`."* |
| 7 | Cross-doc | **plan.md:415** still says "Next.js + shadcn frontend"; v1's audit table missed this occurrence. **plan.md:445** still says "Open the README results table on screen" but v1 silently shifts the close shot to a `/results` Next.js route. | §7 audit table extended to flag both lines; v2 §7 D15 explicitly rewrites L415; v2 §8 close-beat replaces L445 ("Open the README results table on screen" → "Cut to `/results` route — three-track table on near-black surface"). |
| 8 | Devpost | **AI-disclosure surface widens** to cover Claude-generated design copy in `claude-design-output/`. v1 didn't address. | §12 row 526 ("AI-generated-content disclosure per Devpost rules") rewritten to enumerate (a) Gemini for agent reasoning, (b) Claude for design-system copy and brand strings in `design/claude-design-output/`. |
| 9 | Devpost | **Backup Phoenix screenshot deck** needs to cover the landing + `/results` states. v1 didn't extend it. | §12 row 527 rewritten to include landing + `/results` screenshots in the backup deck. |
| 10 | Implementation | **`design/tokens.test.ts` in CI** is aspirational — `.github/workflows/tests.yml` runs only pytest; no Node step. | §12 + §7 D17 add an explicit step: *"Add a Node check to `.github/workflows/tests.yml`: `node --test --experimental-strip-types design/tokens.test.ts` (~15 min)."* |
| 11 | Implementation | **FastAPI `StaticFiles` mount** needs an import + a route ordering check + a Dockerfile `COPY` of `design/`. ~30 min understates: realistic ~45-60 min with rebuild + smoke test. | §7 D17 / §11 update the estimate to 45-60 min and name the exact lines (`from fastapi.staticfiles import StaticFiles`, `app.mount("/marketing", StaticFiles(directory="design/claude-design-output/ui_kits/marketing", html=True), name="marketing")` registered AFTER all other routes, plus `COPY design/claude-design-output/ /app/design/claude-design-output/` in `Dockerfile`). |
| 12 | Implementation | **`/results` route is net-new** — no `app/results/`, no data pipeline. v1's 2h is tight. | §7 D18 effort revised to **3-4h** with explicit note: route reads from `ma_gatekeeper/scripts/eval_*.py` JSON outputs that already exist; if piping is more than expected, render a static markdown-style table instead (cheaper, demo-equivalent). |
| 13 | Cross-doc | **Pre-existing D17 vs D18 Reflector pre-seed drift** in plan.md (v3 §6.4 says "48h before recording = D17"; §7 D18 says "48h Reflector pre-seed begins"). Not introduced by v1, but v1 is the right moment to fix. | v2 §7 D17 PM line adds: *"48h Reflector pre-seed begins (per §6.4 — D17, not D18; v3 had a 24h-off drift)."* §7 D18 line drops the same claim. |
| 14 | Cross-doc | **`/results` route + landing page** need to be in the existing §11 "Dead Cloud Run URL during judging" `min-instances=1` mitigation. | §11 row updated: *"min-instances=1 covers all three surfaces on the same Cloud Run service (`/marketing`, `/review`, `/results`)."* |
| 15 | Devpost | **Arize judges want Phoenix front-and-center** — moving the first Phoenix moment to 0:35 (v1's flow) is late for the Arize-track judging rubric. | v2 §8 flow: the cmd+click→Phoenix moment is the **0:00-0:03 cold-open**, not the 1:50-2:05 climax. The climax shot becomes "watch the agent close 5 deals in 90s with Phoenix-trace mode visible." Phoenix is the wedge from frame 1. |
| 16 | Hostile juror | **PDF 2px underline** on its own doesn't read at thumbnail scale. | §9 adds a **2px lane-color tick at the line-number rail** for each underlined clause — costs nothing (rail exists), reads at thumbnail scale, brand-legal. |

Net effect: v2 is **honest about Three.js scope, optimizes for the Devpost juror's real behavior, fixes the broken grep, locks the schema mapping, and closes 3 silent plan.md drift bugs**. The brand still ships; it just stops fighting the medium.

---

### v2 → v3 patches (Round-3 fresh red-team)

| # | Finding | Fix |
|---|---|---|
| R3-1 | **`/review` "mid-SSE-stream with a deal pre-loaded" is unimplemented.** `app/page.tsx:42-43` initializes `dealId = null`, no `useSearchParams`, no autostart. v2 staked the Hosted-URL win on this but never specced it. | §7 D15 PM scope adds: *"Add `?deal=X&autostart=1` query-param handling to `app/page.tsx` (~1h): on mount, if `searchParams.has("autostart")`, skip the deal picker and call the existing `runReview(dealId)` handler. The Hosted Project URL becomes `/review?deal=NVDA-MLNX-2024&autostart=1`."* §4 effort table picks up a +1h line. |
| R3-2 | **Static `hero-b.html` fallback will 404 on its CSS.** Line 1 of the file is `<link rel="stylesheet" href="../../colors_and_type.css">`; under `app.mount("/marketing", StaticFiles(directory=".../ui_kits/marketing"))` the relative path resolves to `/colors_and_type.css` — not served. Fallback ships broken type. | §7 D17 mount line revised: mount the **parent** directory so the relative `../../` resolves correctly: `app.mount("/dso", StaticFiles(directory="design/claude-design-output", html=True), name="dso")` and route `/marketing` → `/dso/ui_kits/marketing/hero-b.html` via a redirect, OR rewrite the `<link>` to absolute `/dso/colors_and_type.css` at build time. v3 picks the parent-mount approach (simpler, no file edit). |
| R3-3 | **0:00-0:03 Phoenix cold-open is contextless.** A juror sees raw Phoenix UI with no anchor — risk of parsing it as "generic observability dashboard" rather than "auditability proof." | §8 timing shifts: **0:00-0:01** shows the `/review` Block-finding row in `bg-surface` with the cursor mid-cmd+click ("`¹ BLOCK 0.42`" on screen, oxblood left-edge bar visible); **0:01-0:04** Phoenix fills the screen. The 1-second product frame primes the juror to read the Phoenix dashboard as "the trace behind that BLOCK." 4s total cold-open. |
| R3-4 | **Footnote markers `¹²³` double up with `BLOCK 0.42` and read as priority-ordered ("first finding").** Brand register permits taxonomy glyphs (`*` `†` `‡` `§`) per `claude-design-output/README.md` §Punctuation — those read as *taxonomy*, not order. | §9 product surface + §8 demo flow + the schema-mapping rule swap markers: **`†` = Block, `‡` = Escalate, `§` = Auto-Clear** (legal-doc-typographic taxonomy convention, no priority-order collision). `claude-design-output/README.md` line 62 explicitly permits these glyphs. |
| R3-5 | **Tailwind sweep grep misses inline filled-lane tints.** `findings-pane.tsx:55` ships `bg-lane-clear/15` post-D14-PM-migration — a filled colored row background, explicitly banned by v2 §9. v2's two-pass grep doesn't flag it (no `rounded`, no `bg-blue`, no `shadow`). | §12 brand-QA adds a **third grep pass**: `rg -nP '\bbg-lane-(block\|escalate\|clear)(/\d+)?\b' ma_gatekeeper/frontend/{app,components}` — returns zero matches after D15 AM sweep. §7 D15 AM sweep extended to fix this row (replace tint with the 4px left-edge bar marker). |

All five are now baked into the §7 / §8 / §9 / §12 sections below.

---

## 1. Plan.md sections that touch the website (v2 audit table — 2 lines added vs v1)

| § | Section | Touches website? | Disposition |
|---|---|---|---|
| 0 | Executive summary | indirectly | KEEP; add one clause |
| 3.2 | What "wins the demo" | yes — cmd+click climax | KEEP; reframe (the climax is now the cold-open, not the close) |
| 4.1 | Stack — Frontend row | yes — Next.js + shadcn + Tailwind + Streamlit | REWRITE |
| 4.1 | Stack — Observability row | indirectly | KEEP |
| **7 — line 415** | **D15 inline mention of "Next.js + shadcn frontend"** | **yes — missed by v1** | **EDIT (drop "shadcn")** |
| **7 — line 419** | **D19 pre-recording detail** | yes — light edit | LIGHT EDIT |
| 7 | D14 PM / D15 / D16 / D17 / D18 | yes — entire build | REWRITE |
| 7 | Slip-protection | yes — Streamlit fallback | REWRITE |
| **8 — line 445** | **"Open the README results table on screen"** | **yes — missed by v1** | **EDIT (→ `/results`)** |
| 8 | Demo flow (all beats) | yes | RE-STORYBOARD |
| 9 | UI/UX | yes — entire section | FULL REWRITE |
| 10 | Extensions | no | KEEP |
| 11 | Risks (iframe, Streamlit, Next.js slip, Vertex quota, Cloud Run URL) | yes — 5 rows | EDIT + ADD 4 new |
| 12 | Submission checklist | yes — 5+ rows | ADD 6 new; FIX grep; FIX AI disclosure; EXTEND backup deck |
| 14 | Offline / on-prem | no | KEEP |
| 15 | Citations | yes — design refs | ADD 4 entries |

---

## 2. Proposed rewrites — section by section (v2, post Round-2)

### §3.2 — "What wins the demo" (reframed for the cold-open)

Replace the closing sentence with:

> *The opening shot of the demo video is the cmd+click→Phoenix moment itself — a 2-3 second cold-open of a Block-lane finding click-through landing on the live Phoenix trace, before any context. The rest of the video exists to explain that shot, not to set it up. The surrounding chrome — review surface, Phoenix evidence column, eventual brand close — is Documentary Brutalism per [`design/SOURCE_OF_TRUTH.md`](design/SOURCE_OF_TRUTH.md): court-margin rule, footnote markers, lane labels as type. The visual register is a wedge against "another red/green AI dashboard," but the wedge lands second; the auditability proof lands first.*

---

### §4.1 — Stack table, Frontend row (v2, shadcn-honest)

**Proposed:**

> *Next.js (App Router) + Tailwind extending `design/tokens.ts` (Documentary Brutalism palette — surface near-black, ink + champagne / oxblood / ivory luxury accents, Instrument Serif + Space Grotesk + Geist Mono). **shadcn/ui never adopted** — the existing review app is hand-rolled Tailwind, which aligns with the brand's no-rounded-pill / no-card-frame non-negotiables; Radix primitives pulled à la carte only if a dialog or popover lands on the critical path. Three surfaces share the same Tailwind config and CSS variables: `/review` (working product, the Hosted Project URL target), `/marketing` (landing page, the demo-video closer + Devpost description-link target), `/results` (eval results, the demo-video close shot). Brand QA gated by `design/tokens.test.ts` invariants in CI (Node step added to `.github/workflows/tests.yml`). If Phoenix iframe embed is ugly per D1-D2 validation, the right-pane fallback is a custom trace-card rendered against `colors_and_type.css`. **Streamlit fallback removed** — if Next.js slips past D17, fallback is a static `hero-b.html` served via FastAPI `StaticFiles` mount on `agent/server.py` (~45-60 min including Dockerfile `COPY` + rebuild + smoke test). Three.js dependency: `hero-scene.js` is 1534 LOC of bespoke WebGL (three@0.160.0); v2 ships an **SVG-with-depth fallback as the primary** marketing-page composition, with the WebGL scene as a D16 PM stretch goal only if AM is clean.*

---

### §7 — Timeline (v2 rewrites)

**D14 PM (new line — this session, prerequisite work; v2 corrects v1's claim that the Tailwind sweep is "already done"):**

> *Design-token migration applied to `design/tokens.ts`, `tailwind.config.ts`, `app/globals.css`, `app/layout.tsx`; legacy specs banner-marked SUPERSEDED; `tokens.test.ts` invariants extended (no warm-clay, no brand-blue, `border-radius: 0` globally, one easing only). **Tailwind class sweep TO BE RUN at start of D15** — v1 claimed it was already done; v2 is honest that two real violations remain at `components/findings-pane.tsx:61` (`"rounded px-1.5..."`) and `components/deal-picker.tsx:25` (`"rounded border..."`), surfaced by the corrected brand-QA grep. The sweep is 1-2h of mechanical work and is the first thing D15 does.*

**D15 (v3 — sweep + shell + sync + deep-link autostart):**

> *Morning: Tailwind class sweep — fix `findings-pane.tsx:61` (`rounded` chip), `findings-pane.tsx:55` (`bg-lane-clear/15` filled-tint — `[v3]` net-new find, swap for the 4px left-edge bar marker), `deal-picker.tsx:25` (`rounded`), and any siblings the corrected three-pass grep surfaces. Afternoon: Next.js review-app shell at `/review`. All chrome conforms to Documentary Brutalism: `bg-surface text-ink`; left court-margin hairline; line numbers down the PDF pane; **lane labels as uppercase mono** (`mono-foot` 11px, `text-ink-muted`) with **score in `mono-badge` 14px** alongside and a **taxonomy footnote-marker prefix** (`[v3]` markers swapped from `¹²³` to `† ‡ §` to avoid the priority-order collision with "Block"): **`†` = Block, `‡` = Escalate, `§` = Auto-Clear**, mapped to `GatekeeperDecision.lane` (post-routing); pre-routing rows show no marker. **2px lane-color left-edge bar per row** — the 200ms color signal; the taxonomy marker is the second-read disambiguator. **No rounded chips, no filled colored row backgrounds, no shadows.** PDF viewer (`react-pdf`) underlines clauses with a **2px stroke** in lane color sitting 2px below the glyph baseline (hover/selected thickens to 4px in 200ms); a **2px lane-color tick at the line-number rail** mirrors each underlined clause for thumbnail-scale legibility. **PDF↔trace bidirectional sync** wired (Parser bbox from D4 + judge span attrs from D7); if D4 bbox is incomplete, scope to forward-direction only. **`[v3]` Deep-link autostart: add `?deal=X&autostart=1` query-param handling to `app/page.tsx` (~1h) — on mount, if `searchParams.has("autostart")`, skip the deal picker and call the existing `runReview(dealId)` handler. The Hosted Project URL becomes `/review?deal=NVDA-MLNX-2024&autostart=1` so a juror lands on a streaming agent mid-flight, not on the empty picker.** EOD spot-check against `claude-design-output/preview/cmp-doc-chrome.html`, `cmp-cta.html`, `cmp-footnote.html`. **Replaces plan.md:415 "Next.js + shadcn frontend" wording — shadcn never adopted.***

**D16 (v2 — landing page + SSE, honest about Three.js):**

> *Morning (motion-budget capped): stand up the marketing landing page at `/marketing` as a Next.js route group (`app/(marketing)/page.tsx`). **Primary path is the SVG-with-depth dimensional fallback** from `claude-design-output/README.md` §The dimensional layer — line-number rail + ochre stamp + Newsreader 200/800 paired headline + footer band carry the composition; visually credible at thumbnail scale, no WebGL dependency, no jank risk. Copy strings locked verbatim from `claude-design-output/README.md` §Content fundamentals. Footnote ¹ on "sourced" resolves in the footer band citing Arize Phoenix. Primary CTA `Try the demo →` links to `/review`. **AM noon checkpoint**: if SVG variant is green by noon, optional stretch is **porting `hero-scene.js` (1534 LOC of Three.js)** to React-lifecycle-safe canvas — explicitly framed as stretch only, 10-16h of real work normally, do NOT block landing-page ship on it. **Hosted Project URL points to `/review`, not `/marketing`** — landing is for the demo video + Devpost description; the working agent is what jurors click. Afternoon: SSE streaming from Cloud Run. Below-the-fold sections explicitly scoped OUT.*

**D17 (v3 — hardening + noon GO/NO-GO + CI fix + relative-CSS-safe mount):**

> *Hardening: PDF parse failures fall back to Document AI Layout Parser; rate limiting on demo passcode; quota safeguards. **48h Reflector pre-seed begins here** (corrects pre-existing plan.md:418 D18-PM drift — §6.4 says 48h before recording = D17, not D18). **Brand-QA pass on both surfaces** — run all THREE grep passes (`[v3]` third pass added to catch inline filled-lane tints v2's two-pass form missed): `rg -nP '\bbg-blue\b|\bshadow-(?!none\b)' ma_gatekeeper/frontend/{app,components}` AND `rg -n '\brounded\b' ma_gatekeeper/frontend/{app,components} | rg -v 'rounded-none'` AND `rg -nP '\bbg-lane-(block|escalate|clear)(/\d+)?\b' ma_gatekeeper/frontend/{app,components}`. All three must return zero matches. **Add Node CI step** to `.github/workflows/tests.yml`: `node --test --experimental-strip-types design/tokens.test.ts` (~15 min). Side-by-side comparison with `claude-design-output/preview/colors-accents.html`, `cmp-cta.html`, `cmp-doc-chrome.html`. **Explicit noon GO/NO-GO**: if landing page + SSE aren't both green by 12:00, fire static-HTML fallback at noon. `[v3]` **The static fallback mount uses the PARENT directory so `hero-b.html`'s relative `<link rel="stylesheet" href="../../colors_and_type.css">` resolves correctly**: `from fastapi.staticfiles import StaticFiles`; `app.mount("/dso", StaticFiles(directory="design/claude-design-output", html=True), name="dso")` registered after all other routes in `agent/server.py`; plus a one-line redirect handler `/marketing` → `/dso/ui_kits/marketing/hero-b.html`. (`[v3]` correction — v2's `app.mount("/marketing", StaticFiles(directory=".../ui_kits/marketing"))` would resolve the relative CSS path to `/colors_and_type.css`, which is unserved, so the fallback would have shipped with broken type.) `COPY design/claude-design-output/ /app/design/claude-design-output/` added to `Dockerfile`; rebuild + smoke-test (~45-60 min total). Product UI never falls back to Streamlit.*

**D18 (v2 — eval + `/results` route, no pre-seed line):**

> *Final eval run; results table renders into the README **and** into a `/results` Next.js route on the near-black surface, **footnote anchored to the Block-recall number resolves within the same 100vh** per composition rule 8. `/results` reads from `ma_gatekeeper/scripts/eval_*.py` JSON outputs (existing); if piping is more than expected, render a static markdown-style table instead — demo-equivalent. Effort ~3-4h (revised up from v1's 2h). Rehearse demo end-to-end at least twice, including the new 0:00-0:03 cmd+click cold-open and the 2:45-3:00 brand-close bookend.*

**D19 (v2 — cold-open recording):**

> *Record demo. **0:00-0:03 is the cmd+click→Phoenix cold-open** (working-agent proof from frame 1); brand-hero bookend at 2:45-3:00. Pre-record fallback for the EDGAR fetch segment. Pre-load Phoenix in a split-screen second window so the cmd+click reveal is instant.*

**D20 (v2 — submission with honest URL routing):**

> *Submit. Verify **Hosted Project URL points to `/review`** (working app with a deal pre-loaded in mid-SSE-stream — hostile-juror's specific recommendation). Devpost description's first link points to `/marketing` so jurors who *want* presentation can click through; jurors who don't see the agent on the click. README has all three surfaces linked.*

**D21:** unchanged.

**Slip-protection (v2):**

- D9 calibration / D12 Reflector / D14 cron rows: unchanged.
- **D16 AM motion-budget**: if SVG-with-depth doesn't ship by noon → static-HTML fallback fires (skip the Next.js route group entirely).
- **D17 noon GO/NO-GO**: if landing page or SSE aren't green → static-HTML lift at `/marketing` via FastAPI `StaticFiles` (~45-60 min). Review app at `/review` ships as-is.
- **Streamlit fallback is OFF.** No path back.
- **WebGL stretch is OFF the critical path.** The Three.js port (4-6h v1 estimate → 10-16h honest estimate) is a D16 PM stretch only.

---

### §8 — Demo flow (v2, cold-open-led)

| Time | Beat | What's on screen |
|---|---|---|
| **0:00-0:01** | **Product context frame** *(`[v3]` new — Round-3 red-team said the v2 0:00 Phoenix-only cold-open is contextless)* | `/review` Block-finding row in `bg-surface` with the cursor mid-cmd+click. Visible on screen: `† BLOCK 0.42 NVDA-MLNX change-of-control` with the oxblood 2px left-edge bar. 1 second primes the juror to read what comes next as "the trace behind that BLOCK." |
| **0:01-0:04** | **THE MOMENT** *(was 0:00-0:03 in v2)* | Phoenix dashboard fills the screen showing the trace, cited span, hallucination evaluator output, judge reasoning, score that crossed τ. **3 seconds of held context with no voiceover.** This IS the wedge. |
| 0:04-0:08 | **Title card** | *"M&A Gatekeeper — every flag, sourced. Every verdict, traced. Every span, clickable."* on near-black surface, taxonomy footnote `†` anchored to "sourced" resolves to a 14px mono line citing Arize Phoenix. Brand register registered without burning a marketing-hero shot. |
| 0:08-0:23 | **Problem** | Potomac Law quote; deal-volume + diligence-cost overlay. |
| 0:23-0:38 | **Architecture** | One diagram, 3 callouts: Gemini 3 + ADK, Phoenix tracing, MCP self-improvement loop. |
| 0:38-1:50 | **Live demo** | Pick a deal from the allow-list ("five pre-indexed deals" voiceover per §5.5 — locked language unchanged). Findings stream in via SSE as court-document entries: 2px lane-color left-edge bar (200ms recognition) + `† BLOCK 0.42` (Geist Mono, taxonomy-glyph second-read disambiguation per `[v3]` swap from `¹²³`) + Space Grotesk body summary. PDF clauses underlined 2px in lane color with line-number-rail ticks. Cmd+click another Block → Phoenix opens in a second window (hold 4-5s, shorter than v1's 8-10s because the cold-open already did the heavy lift). |
| 1:50-2:30 | **Self-improvement loop** | Phoenix Experiments tab. Pre-seeded delta per §6.4 (D17 pre-seed). Auto-promotion event visible. |
| 2:30-2:45 | **Numbers** | Cut to `/results` route — three-track table on near-black surface (MAUD-MCQ / CUAD-Spans / Internal-30), footnote `*` on the Block-recall number resolves within the same 100vh per composition rule 8. |
| 2:45-3:00 | **Brand close (bookend)** | Cut to the marketing landing at `/marketing` — line-number rail, ochre "M&A SOURCED" stamp, Newsreader 200/800 headline. Final card: GitHub + Hosted URL (`/review`) + Phoenix URL. The brand lands here, not at 0:00 — closer not opener. |

(This **replaces plan.md:445** — the "Open the README results table on screen" line at 2:45-3:00 in the v3 plan is now superseded by "Cut to `/marketing` brand-close bookend" plus the new 2:30-2:45 `/results` shot.)

---

### §9 — UI/UX (v2 full rewrite)

Replace the entire current §9 with:

> **Aesthetic register:** Documentary Brutalism. Source of truth: [`design/SOURCE_OF_TRUTH.md`](design/SOURCE_OF_TRUTH.md) → [`design/claude-design-output/README.md`](design/claude-design-output/README.md) → [`source/design.md`](design/claude-design-output/source/design.md) → [`colors_and_type.css`](design/claude-design-output/colors_and_type.css). Brand non-negotiables (no rounded corners, no shadows, no blue, no system-ui, no centered hero, mono ligatures off, one easing only, one accent per surface in ≤3 placements, footnote markers load-bearing, em-dashes load-bearing, 88px display floor) enforced by `design/tokens.ts` + `design/tokens.test.ts` and apply to **all three** surfaces below.
>
> **Accent palette in use.** M&A luxury palette extension (`champagne` / `champagne-deep` / `champagne-soft` / `oxblood` / `ivory`) defined in `colors_and_type.css` lines 30-35 is the lived palette. The README's original four (`vermillion` / `highlighter` / `ochre` / `cyan-ink`) remain as legacy. Each surface picks one accent and uses it in at most three placements.
>
> **Working surface (`/review`) — the Hosted Project URL target**
>
> Three-pane review layout. Single accent: champagne.
>
> - **Left pane — PDF viewer (`react-pdf`).** Clauses underlined with a **2px stroke** in lane color (oxblood = Block, champagne = Escalate, no decoration = Auto-Clear), sitting 2px below the glyph baseline. Hover / selection thickens to 4px in 200ms `cubic-bezier(0.16, 1, 0.3, 1)`. **Plus**: a **2px lane-color tick at the line-number rail** mirrors each underlined clause, so the lane-color signal reads at thumbnail scale even when the PDF underline is sub-pixel after H.264 downsampling.
> - **Center pane — findings list.** Each finding renders as a court-document entry:
>   - **2px lane-color left-edge bar** in the gutter — the 200ms color signal a Devpost juror parses on first glance (hostile-juror critic insisted; brand-compliant per `claude-design-output/README.md` §Backgrounds *"depth through overlap, scale, or a single hairline rule"*).
>   - **Taxonomy footnote-marker prefix**, mapped to `GatekeeperDecision.lane` (post-routing): `†` = Block, `‡` = Escalate, `§` = Auto-Clear. (`[v3]` swapped from `¹²³` — numeric markers double up with "Block" as priority-order and risk parsing as "first finding." Taxonomy glyphs `† ‡ §` read as classification, not order — and `claude-design-output/README.md` line 62 explicitly permits them as load-bearing document marks.) Pre-routing rows (only `RiskFinding.severity` known) render markerless until the SSE frame that delivers the lane assignment arrives.
>   - **Lane label** in uppercase Geist Mono (`mono-foot` 11px, `text-ink-muted`).
>   - **Score** in `mono-badge` 14px alongside (`BLOCK 0.42`).
>   - **One-line summary** in Space Grotesk body.
>   - **Hairline rule** below — no card frame.
>   - **Selected row**: the left-edge bar thickens to 4px; no background tint (filled backgrounds banned).
> - **Right pane — Phoenix evidence column.** Either the Phoenix iframe or a custom trace-card rendered against `colors_and_type.css`. Court-margin hairline down the left edge. **Phoenix span ID gets architectural placement as a vertical mono column down the right-pane left margin** (mirroring `hero-a.html`'s span-ID rail).
>
> **Differentiating interaction (unchanged):** PDF↔trace bidirectional sync, with forward-only degrade if D4 bbox incomplete.
>
> **Header.** Deal name on the left in `display-sm` Instrument Serif. τ value visible as a footnote-style mono label (`mono-foot` 11px), not as a chip. **Status string in sentence case**, `body-sm` Space Grotesk.
>
> **Mid-SSE-stream initial state.** Per hostile-juror recommendation: the `/review` URL loads with a deal pre-selected and 2-3 findings already streamed in, so a juror who clicks the Hosted Project URL lands on a working agent mid-flight, not on an empty deal picker. Cold-loaded state is reachable via the deal-picker, but the default landing is mid-stream.
>
> **Marketing surface (`/marketing`) — demo-video closer + Devpost description link**
>
> One 100vh hero, no nav, no footer-with-links, no logo strip, no testimonials. **Primary composition is SVG-with-depth dimensional fallback** per `claude-design-output/README.md` §The dimensional layer (line-number rail + ochre stamp + Newsreader 200/800 + footer band). Warm-paper surface, doc ID `EX-2.1 / 2026-06-08 / 1 of 312` top-right, vertical court-margin hairline at 80px, ochre "M&A SOURCED" stamp. Single accent: ochre, in three placements: stamp, footnote-resolution rule, primary-CTA underline-hover state. Footnote ¹ on "sourced" resolves in the footer band. Primary CTA *Try the demo →* (underlined type, 6-8px arrow translate on hover); secondary CTA *Watch the 60-second demo* (underlined small text inline — not a button). Phoenix span ID bottom-left as tracking number. **WebGL Three.js variant from `hero-scene.js` (1534 LOC) is a D16 PM stretch goal only**, never blocks ship.
>
> **Results surface (`/results`) — demo-video close-shot at 2:30-2:45**
>
> Single 100vh table on near-black surface (`bg-surface text-ink`). Three rows: MAUD-MCQ accuracy vs baseline; CUAD-Spans token-F1 + P@R=0.8; Internal-30 5-fold-CV held-out Block-recall + 95% Wilson LB + 95% paired-bootstrap CI. Footnote `*` on the Block-recall number resolves within the same viewport (composition rule 8). No nav, no footer.
>
> **Motion.** One easing only: `cubic-bezier(0.16, 1, 0.3, 1)`. Two durations: 200ms (hover/interaction), 800ms (entry). `prefers-reduced-motion: reduce` honored.
>
> **Forbidden in all three surfaces:** mesh gradients, aurora, glassmorphism, noise overlays, raster imagery, Lottie, Rive, post-processing bloom, particle systems, autoplay video, emoji (including ✓ and →-as-icon), shadcn-default rounded chips, system blue, filled colored row backgrounds.

---

### §11 — Risks (v2 — 5 edits + 4 new rows)

**Edit existing rows:**

- *Phoenix iframe embed looks bad* → Plan B is now the custom trace-card rendered against `colors_and_type.css`, not a generic-Tailwind card.
- *Next.js slips past D17* → Streamlit fallback REMOVED. Replaced with: "static `hero-b.html` lift at `/marketing` via FastAPI `StaticFiles` mount + `COPY design/` in `Dockerfile` (~45-60 min); review app at `/review` ships as-is."
- *Dead Cloud Run URL during judging* → mitigation extended: *"min-instances=1 covers all three surfaces on the same Cloud Run service (`/marketing`, `/review`, `/results`)."*

**Add four new rows (v2 — was 3 in v1):**

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| **Three.js `hero-scene.js` port overruns the brief's complexity budget (~1534 LOC of bespoke WebGL)** `[v4]` | High | Low | **SVG-with-depth fallback is the primary path; WebGL is a D16 PM stretch only**. Honest estimate 10-16h, not 4-6h; treat as out-of-scope unless landing-page core ships clean by D16 noon. |
| **Landing page slips, working agent still ships at `/review`** `[v4]` | Medium | Low | D17 noon GO/NO-GO; FastAPI `StaticFiles` mount serving `hero-b.html` at `/marketing` (~45-60 min, concrete deploy path). The working-agent demo doesn't depend on the landing page (it's only the demo-video closer + a Devpost description link). |
| **Brand drift between three surfaces** `[v4]` | Medium | Medium | Single `design/tokens.ts` import on all three; `tokens.test.ts` invariants in CI (Node step added to `.github/workflows/tests.yml`); brand QA on D17 cross-references `claude-design-output/preview/*.html` cards. |
| **PDF↔trace sync degrades to forward-only because D4 bbox extraction was incomplete** `[v4]` | Medium | Medium | If Parser bbox population is missing on >10% of clauses, scope to forward-direction only and document in README. Never block ship on reverse sync. |

---

### §12 — Submission checklist (v2 — 6 new rows + 2 fixes + grep corrected)

**Add:**

- [ ] `[v4]` **Hosted Project URL points to `/review`** (working agent with a deal pre-loaded mid-stream — first thing a juror sees is the agent at work, not a marketing page; first link in the Devpost *description* points to `/marketing` for jurors who want the brand)
- [ ] `[v4]` **Landing page deployed at `/marketing` on the same Cloud Run service** (FastAPI `StaticFiles` mount on `agent/server.py` for the static fallback path; Next.js route group for the primary path)
- [ ] `[v4]` **Results page deployed at `/results` on the same Cloud Run service** (referenced from the demo video close shot at 2:30-2:45)
- [ ] `[v4]` **Hero matches `claude-design-output/ui_kits/marketing/hero-b.html`** within brand-QA tolerance (line numbers, court-margin rule, Newsreader 200/800 paired, ochre stamp, SVG-with-depth or Three.js dimensional layer)
- [ ] `[v4]` **Locked copy strings present verbatim** on `/marketing` AND in demo-video title card: hero tagline, sub-line, conservative-stats line, primary CTA, secondary CTA, Phoenix span-ID format
- [ ] `[v4]` **`design/tokens.test.ts` invariants pass in CI on the submission commit** — concrete CI step in `.github/workflows/tests.yml`: `node --test --experimental-strip-types design/tokens.test.ts`

**Fix existing rows:**

- [v3 row 526 — AI-generated-content disclosure] → rewrite to: *"AI-generated-content disclosure per Devpost rules — covers (a) Gemini extensively for agent reasoning, (b) Claude for design-system copy and brand strings in `design/claude-design-output/`."*
- [v3 row 527 — Backup Phoenix screenshot deck] → extend to: *"Backup deck includes Phoenix dashboard states, `/marketing` landing screenshot, `/review` mid-stream screenshot, `/results` table screenshot — covers all three surfaces in case Cloud Run is cold or any Next.js route group fails during judging."*

**Brand-QA grep (corrected v3 — three passes, tested against today's tree):**

- [ ] `[v4]` Run pass A: `rg -nP '\bbg-blue\b|\bshadow-(?!none\b)' ma_gatekeeper/frontend/{app,components}` returns zero matches
- [ ] `[v4]` Run pass B: `rg -n '\brounded\b' ma_gatekeeper/frontend/{app,components} | rg -v 'rounded-none'` returns zero matches (today flags `findings-pane.tsx:61` and `deal-picker.tsx:25`; sweep is the first thing D15 does)
- [ ] `[v4]` Run pass C `[v3 new]`: `rg -nP '\bbg-lane-(block|escalate|clear)(/\d+)?\b' ma_gatekeeper/frontend/{app,components}` returns zero matches (today flags `findings-pane.tsx:55` — the `bg-lane-clear/15` selected-row tint that the v2 two-pass grep missed; sweep is the first thing D15 AM does, replacing the tint with the 4px left-edge bar marker)

---

### §15 — Source citations (v2 — 4 design entries)

Add under new "Design system" subhead:

- `design/SOURCE_OF_TRUTH.md` — short index of locked brand decisions.
- `design/claude-design-output/README.md` — long-form design system.
- `design/claude-design-output/source/design.md` — original creative brief (authoritative).
- `design/claude-design-output/colors_and_type.css` — canonical CSS for the M&A luxury palette extension.

---

## 3. Out-of-scope (unchanged from v1) — deliberately

- No new product-UI features beyond the v3 plan.
- No A/C hero variants (only B is shipped and the SVG fallback is the primary).
- No motion-heavy animations beyond `hero-b.html`'s SVG-with-depth fallback; the Three.js scene is stretch-only.
- No mobile-optimized landing beyond `@media (max-width: 768px)`.
- No copy beyond the locked strings.

---

## 4. Estimated effort (solo, pessimistic — v2 honest estimates)

| Plan.md edit | Effort |
|---|---|
| §3.2 + §4.1 + §11 + §12 + §15 text edits | 50 min |
| §7 D14 PM + D15-D21 rewrites + slip-protection | 40 min |
| §8 demo-flow re-storyboard | 25 min |
| §9 UI/UX full rewrite | 50 min |
| Brand-QA grep correction + CI hook step | 40 min |
| **Total plan.md update work** | **~3.5 hours** |

Implementation work (v2 — honest):

| New work introduced | Effort | Day | Risk |
|---|---|---|---|
| Tailwind class sweep on product UI (`findings-pane.tsx:61` + `deal-picker.tsx:25` + siblings) | 1-2h | D15 AM | Low — mechanical grep |
| `/review` shell + lane-color left-edge bars + taxonomy markers (`† ‡ §`) + sentence-case status + PDF rail ticks | 4-5h | D15 PM | Low |
| `[v3]` `?deal=X&autostart=1` deep-link handler in `app/page.tsx` | 1h | D15 PM | Low |
| `/marketing` landing — SVG-with-depth primary | 4-6h | D16 AM | Medium |
| `/marketing` landing — Three.js stretch | 10-16h | D16 PM (stretch only, not on critical path) | High — explicitly out of scope unless landing ships clean by D16 noon |
| SSE streaming | 3-4h | D16 PM | Low |
| `/results` route reading existing eval JSON | 3-4h | D18 | Low |
| FastAPI `StaticFiles` mount + Dockerfile `COPY` (fallback path) | 45-60 min | D17 PM (only if noon GO/NO-GO fires) | Low |
| Brand-QA CI hook (Node step in `.github/workflows/tests.yml`) | 15 min | D17 | Low |
| Brand-QA on submission commit | 1h | D20 | Low |

---

## 5. Open questions for the user (v2 — resolved or refined)

1. ~~Demo-video framing — does the 0:00-0:05 landing-page hero opening replace one of the existing intro beats, or stretch the video to 3:05?~~ → **Resolved by Round-2 critics**: opening is now 0:00-0:03 cmd+click cold-open; brand-hero is a 2:45-3:00 bookend.
2. ~~Hosted Project URL — should the Devpost "Hosted Project URL" point to `/` (the marketing landing) or to `/review` (the working product)?~~ → **Resolved**: `/review`. Devpost convention + hostile juror both flag `/` as an unforced error.
3. **Dimensional-layer authority** — v2 ships the SVG-with-depth variant by default; the Three.js port is an explicit D16 PM stretch only. **Authorized to make this call autonomously, or do you want explicit sign-off?**
4. **`/results` data piping** — `/results` reads from `ma_gatekeeper/scripts/eval_*.py` JSON outputs. If the piping turns out non-trivial, v2 falls back to a static markdown-style table rendered server-side. **OK to use either fallback at builder discretion?**
5. **`/marketing` vs `/about` for the route name** — `/marketing` is honest about the surface's intent; `/about` is conventional. **Preference?**

---

*End of v2 draft. Two rounds of red-team applied. Awaiting user sign-off before mutating `plan.md`.*
