# Art Direction Plan — M&A Gatekeeper

> **Goal**: ship a landing page that earns an unprompted "wow" from the Devpost jury — and that a corporate counsel could forward to their partners without embarrassment.
> **Surface**: marketing landing page (the pitch) with an embedded `/reflect` console — see §"Resolved decisions" for the embed strategy.
> **Vibe**: *Playful & confident hackathon-native* — Resend / Clerk / Cal.com lane, sharpened toward the Mercury / Ramp / Stripe Press register for serious-money credibility.
> **Budget**: ~1 week of focused execution after this plan is approved.
> **Hackathon**: Google Cloud Rapid Agent Hackathon — Arize partner track. Deadline **2026-06-11**.

---

## 0. The central tension (read this first)

The **content** is enterprise legal-tech: auditable M&A contract review, Fortune-500 GC-grade trust, "click into every span." The **vibe we picked** is playful, color-forward, motion-rich, personality-first.

That mismatch is not a bug. **Resend, Clerk, Trigger.dev, Cal.com, Mercury, Ramp, and Linear all do exactly this** — serious infra wrapped in design that signals craft, taste, and confidence. Done deliberately it reads as *"the team that built this loves their work."* Done sloppily it reads as *"a legal tool that doesn't know what it is."*

Every decision below must answer one question: **does this make a serious tool feel inevitable and fun, or does it make a serious tool feel unserious?** The Art Director (see §3) has veto power on anything that fails that test.

### 0.1 Composition rule — where playful lives, where serious owns

The tension is resolved not by averaging but by **assigning domains**. Each component of the page belongs to one register, not both.

| Register | Domain |
|---|---|
| **Serious owns** | macro grid, typographic hierarchy, color *system* (not accent), numbers section, "What this is not" honesty block, FAQ answers, the moneymoment trace card, footer credits. These do not joke. |
| **Playful lives in** | micro-interactions, hover states, accent color usage, the easter egg in the footer, the 404, microcopy in loading states, the OG image wit. |

If a component reads as both, the Art Director picks one and rewrites until it commits. **"Tasteful and weird" is the goal**; "tasteful and safe" is the failure mode.

---

## Phase 0 — Tooling reconnaissance (do this FIRST, before any design work)

Before agents start drawing pixels, we spend half a day mapping the meta-tools. Skipping this is how teams ship work that a better Claude skill could have done in a third of the time. **Hard cap: one calendar day total** for Phase 0 — if MCP installs reveal missing capabilities, work without them rather than slip Day 1.

### 0.1 Claude skills audit

Run an inventory pass against the skills available in this environment. Specifically validate or rule out:

| Skill | Why it might matter | Verdict to confirm |
|-------|---------------------|-------------------|
| `expert-review-loop` | Iterative multi-reviewer convergence on the design plan + the built page. **Use it twice**: once on this plan, once on the staged build before video recording. | **Adopt** |
| `verify` | Drive the deployed site in a browser to catch jank that doesn't show up in code review. | **Adopt for final pass** |
| `simplify` | After motion/animation lands, review for code reuse and bundle bloat. | **Adopt before launch** |
| `run` | Standard "launch the dev server and look at it" loop during build. | **Adopt** |
| `project-log` | Already in use (`PROJECT_LOG.md`). Continue logging design decisions there. | **Continue** |
| `init` / `update-config` / `keybindings-help` / `fewer-permission-prompts` | Harness setup, not design. | **Skip** |
| `loop` / `schedule` | No recurring task here — one-shot build. | **Skip** |
| `security-review` / `review` | Will run before deploy of the live `/reflect` route, not the marketing page. | **Defer** |
| `claude-api` | Marketing site does not call the Anthropic SDK. | **Skip** |

### 0.2 Plugin / MCP server reconnaissance

The supervisor agent (§3) opens its first session with this checklist:

1. **List currently-installed MCP servers** — what's already wired up that we can reuse?
2. **Search for design-relevant MCP servers** that could be added cheaply:
   - **Figma MCP** — if we want to round-trip from Figma to code (only worth it if someone on the team actually opens Figma).
   - **Image generation MCPs** (Imagen/DALL-E/Midjourney) — for hero imagery, OG cards, illustrative spot art.
   - **Browser-driving MCPs** (Playwright/Chrome DevTools MCP) — for screenshotting competitor sites into the inspiration board, and for the final QA pass.
   - **Lottie / Rive MCPs** — if we go that route for vector motion.
3. **Search for community Claude Code plugins** focused on UI/frontend:
   - shadcn/ui registry helpers, Tailwind class-merge linters, Framer Motion snippet libraries, accessibility audit plugins.
4. **Decide what's worth installing.** Bias toward installing zero — every plugin is cognitive overhead. Install only what removes a friction we've already felt.

**Deliverable**: `design/TOOLING.md` — a one-page table of "tool, what it does for us, decision (use / skip), and why." This becomes the canonical list for the rest of the project.

### 0.3 Reference asset libraries to bookmark (not install)

These are external libraries we'll **pull patterns from** rather than depend on:

- **Aceternity UI** (https://ui.aceternity.com/) — animated hero patterns, spotlight, sparkles, wavy backgrounds. Permissive copy-paste.
- **Magic UI** (https://magicui.design/) — marquees, animated beams, terminal animations, number tickers.
- **shadcn/ui** (https://ui.shadcn.com/) — already in the stack via `components/ui` convention. Foundation, not flourish.
- **Motion Primitives** (https://motion-primitives.com/) — Framer Motion presets.
- **Cult UI** (https://www.cult-ui.com/) — premium-feeling component variants.
- **React Bits** (https://www.reactbits.dev/) — text effects (decrypt, scramble, gradient sweeps).
- **Eldora UI / Syntax UI** — additional pattern libraries to cherry-pick from.

The Frontend Architect (§3) maintains a "borrowed patterns" registry so we never end up with the *exact* same hero as every other 2026 Awwwards entry.

### 0.4 Scaffold cleanup (Day-1 prerequisite, before Phase 5)

The existing `ma_gatekeeper/frontend/` Next 14.2.5 scaffold ships with lane colors (`#16a34a / #eab308 / #dc2626`) in `tailwind.config.ts` that **contradict §5.1**'s palette. Cleanup tasks owned by the Frontend Architect on Day 1:

1. Upgrade Next 14.2.5 → 15 (or pin 14.2.5 and document in `STACK.md`).
2. Tear out lane-color hex codes from `tailwind.config.ts` — they'll be re-derived from `tokens.ts` after §5.1 commits.
3. Audit `react-pdf` / `pdfjs-dist` imports — these are heavy and belong dynamically-imported inside `/reflect`, not the marketing route. If they bleed into the marketing bundle, the perf budgets (§6.2) collapse on Day 7.
4. Confirm or set `X-Frame-Options` / `frame-ancestors` posture for the `/reflect` route — required regardless of mock-vs-iframe outcome (see §"Resolved decisions").

---

## Phase 1 — Inspiration mining

A team of motion-first frontend developers without a moodboard ships a generic site. We build the moodboard before we write a line of code.

### 1.1 Award sites to mine, with what to steal from each

**Awwwards (https://www.awwwards.com/)**
- Filter: Site of the Day, last 12 months, category = Technology / SaaS / Tools.
- Mine: scroll choreography, hero composition, color systems used by *serious* tools.

**SiteInspire (https://www.siteinspire.com/)**
- Filter: Type = Application / Corporate, Style = Minimal / Typographic.
- Mine: layout grids, typographic restraint that still feels alive.

**Godly (https://godly.website/)**
- Filter: Web3, AI, Dev Tools.
- Mine: oversized typography, brutalist-but-warm color, micro-interaction taxonomy.

**Lapa Ninja (https://www.lapa.ninja/)**
- Mine: landing page section anatomy — we need a vocabulary of hero / feature / proof / pricing / CTA patterns.

**Httpster (https://httpster.net/)**, **Land-Book (https://land-book.com/)**, **Refero (https://refero.design/)** — secondary scrapers, used to widen the funnel after the primary three.

### 1.2 Specific reference sites — hand-picked for *our* tension

The Art Director starts the team with these as the canonical reference set. Each is annotated with the **one thing we're stealing**. Curated to lean *away* from the Twitter-designer starter pack and *toward* the serious-money register that matches our buyer.

| Site | Steal this |
|------|-----------|
| **mercury.com** | Closest single analog to our tension — serious financial software with warm, confident color and grown-up restraint. Study how they avoid feeling "fintech bro." |
| **ramp.com** | Financial seriousness with personality. The proof you can be playful and credible *to a CFO* in the same paragraph. |
| **stripe.com/press** (Stripe Press) | Editorial seriousness next to motion craft. The lane the M&A reader respects without trying. |
| **resend.com** | Serious infra + playful illustration. Hero typography rhythm. Inline live code that *feels* alive. |
| **clerk.com** | Color-forward without losing trust. Component spotlights on scroll. |
| **trigger.dev** | Pipeline visualization that *feels* like the product. Closest analog to our agent topology. |
| **modal.com** | Dev-infra clarity. Their "show the thing working" patterns translate directly to our demo embed. |
| **retool.com** | Enterprise legibility done without enterprise drabness. |
| **linear.app** | The most copied site of the era — we look but do *not* copy. We steal: cmd-K vocabulary, dark/light parity, the calm. |
| **vercel.com** (current) | Monospace numbers, charts as art, dark gradient hero. |
| **cal.com** | Personality in microcopy. Confident open-source vibe. |
| **railway.app** | The "play with it in the hero" pattern. |
| **cursor.com** | Showing AI traces as the hero. Closest semantic match to our Phoenix-trace-as-art idea. |
| **anthropic.com** | Editorial restraint, color blocking. Reminder that "wow" doesn't require maximalism. |
| **phoenix.arize.com** | Direct competitor surface. We must look intentional next to it — *not* like a worse version of it. |
| **thebrowser.company/act-ii** + Browser Company memos | Long-form scroll choreography with editorial restraint. Pacing reference. |

**Removed from prior draft**: rauchg.com / leerob.io (personal-engineer sites — taste-bait but wrong register for an M&A pitch); arc.net (great but explicitly "not imitable in a week" — pulls the team toward scope it can't ship).

### 1.3 Anti-references — clichés we reject (not techniques)

What we reject is the *cliché*, not the underlying technique. A gradient is not the problem — *the purple-to-pink AI-startup gradient* is. A 3D hero is not the problem — *the rotating brain of glowing dots* is. Precision matters here so we don't talk the team out of a real differentiator.

- The off-the-shelf **Spline blob hero** with no semantic tie to the product.
- The **purple-to-pink "AI" gradient** that every YC W24 site uses — generic *because* it has no relationship to the brand.
- The **glowing-dot 3D brain** and any other "AI = neurons" visual metaphor.
- **Powered-by-GPT-X badges** and other "we wrapped an API" tells.
- **Stock-illustration crowds** of diverse abstract people pointing at laptops.
- **Carousel heroes** that hide the message behind a slide transition.
- **Word-by-word fade-in-with-blur** headlines that take 4 seconds to read.
- **Fake testimonial cards** with no-name "Partner, AmLaw 50" attributions.

### 1.4 Premium techniques worth an explicit debate

These are the moves that, *done well*, separate a top-10% hackathon page from a Site of the Day. Each is high-ceiling and high-risk — the team debates them deliberately in Phase 5, with a written go/no-go, not stumbles into them.

**The semantic-justification rule** (applies to gradient AND 3D AND any custom illustration)

Before any prototype begins, the Art Director writes a **one-paragraph semantic justification** tying the chosen element to M&A specifically — not to "AI" generically. If the paragraph reads as applicable to any AI startup, the element is rejected and the next candidate is tried. This is the single edit that prevents generic drift. Same rule for every load-bearing visual.

*Worked example* (candidate #2, the contract stack): *"M&A diligence is the act of reading paper — exhibits, indentures, side letters, redlines. Our agent's only job is to read that paper and surface what a partner has to sign off on. The hero is a physical-feeling stack of contracts because that is the literal artifact of the work; the spans glow because that is the moment a flag becomes a decision. This image could not belong to a chatbot, a code assistant, or a generic AI tool — it can only belong to a tool that exists to read deal documents."* If a justification cannot match this concreteness, the candidate is rejected.

**Gradients — on our palette, with intent**

A gradient in the locked deep-forest-emerald palette (see §5.1) with a warm-clay accent kiss is *brand-building*, not cliché. Candidate uses:

- A **mesh gradient backdrop** behind the hero — slow-drifting, low-saturation, reads as ambient depth rather than wallpaper. **Hard constraints**: gradient angles drawn from {15°, 165°, 345°} only (no 90° horizontal, no 45° "designer default"); two stops max, both within the green family; opacity ≤ 0.4 where it sits behind copy; **mesh never placed directly under headline text** (CLS + readability); **no radial-spotlight-from-top-center** (the YC W24 tell).
- A **text gradient** on a single hero word (one viewport, never two) — used for the noun we want to own ("audit trail" or "gatekeeper"), not for decoration.
- A **gradient border** on the audit-trail card / Block-verdict badge — a quiet way to make the moneymoment glow.
- A **scroll-driven gradient shift** behind the agent-pipeline section — color literally shifts as the user scrolls from Parser to RiskJudge, signaling the journey.

Forbidden: full-bleed `from-purple-500 to-pink-500`; conic gradients used as "wow," not as meaning; gradient text on more than one element per viewport.

**3D — earned by the M&A semantics, not borrowed from the AI template**

A 3D hero is a real opportunity *if* it visualizes something specific to M&A or to our agent. Generic = death. On-theme = differentiator. Candidates evaluated:

1. **The agent pipeline in 3D** — Parser → Classifier → CrossRef → RiskJudge → Router → Reporter as connected 3D nodes. Risk: looks like every DAG tool ever (Trigger.dev, Inngest, Modal all have this). Even with document-shaped nodes, it lands as "another DAG."
2. **A 3D stack of contracts with floating risk annotations** — *recommended primary*. The actual artifact of M&A made dimensional. A merger agreement, an exhibit, an indenture; spans of text glow as the RiskJudge "reads" them; Block findings float out as cards. Highest on-theme score, no competitor entry can ship the same thing because their product isn't "read the paper." **Doubles as the moneymoment** — kills two birds.
3. **A 3D Phoenix trace** — the call graph of one real review, rendered as a tree of span boxes. Most product-true but illegible without onboarding — fails the 10-second test.
4. **Two corporate entities merging** — geometric shapes converging through the pipeline. Cinematic but corporate-stock-risk.
5. **Editorial typographic hero — no 3D at all** — *legitimate fifth choice*. Oversized type, one moving element, Mercury/Stripe-Press lane. Highest taste ceiling, lowest execution risk, hardest to do well. **Default if no team member has shipped R3F before** (see kill-switch below).

**Tool options for whichever 3D direction wins**:
- **React Three Fiber + drei** — best React integration, full Three.js power. Requires prior R3F experience.
- **Spline** — fastest to prototype, but pulls in heavy runtime; viable only for simple scenes.
- **Rive** — 2.5D vector with brilliant interactivity, much smaller bundle than Three. Excellent for candidate #2 if we can live without true 3D camera.
- **Lottie** — pure 2D depth illusion. Cheapest in bundle and skill. Fallback if 3D proof-of-concept fails.

**R3F prerequisite check**: If no agent on the team has shipped R3F before, skip directly to candidate #5 (no 3D) or use Rive for #2. Do **not** spend Day 3 on a first-time R3F learning curve.

**Hard kill-switch on 3D**: Frontend Architect allocates **one builder to a 3D proof-of-concept by EOD Day 3**. If by Day 4 morning it doesn't already pass the Art Director's "wow on first viewing" test, **kill it** and fall back to a 2D version of the same metaphor. 3D that almost-works is *worse* than 2D that fully-works.

**Scroll storytelling**

A scroll-driven sequence where the agent pipeline animates as the user scrolls (think Apple product pages, Stripe Sessions, the Linear changelog). Built with GSAP ScrollTrigger or Framer Motion `useScroll`. Most impressive single technique we could land — and the one that performs best in the Devpost video (motion synced to scroll = built-in choreography). Strongly recommended for the agent-pipeline section. **Day-4 mobile gate**: if the scroll-jacked sequence doesn't feel right on a 375px viewport, fall back to triggered Framer reveals.

**Other high-craft techniques to consider**

- **View Transitions API** for page-to-section morphs (cheap, modern, low risk).
- **WebGL shaders for the hero backdrop** — a quiet noise/grain shader that gives the dark mode depth (one file, ~50 lines, huge payoff vs. flat black).
- **Variable font axes animated on hover** — typography that *moves*, a craft signal.
- **A real-time-feeling counter** for the demo (e.g., "47 clauses parsed in 12.3s" ticking up) — looks expensive, costs nothing.

**Deliverable**: `design/INSPIRATION.md` — embedded screenshots (via browser MCP if installed, otherwise URLs + 1-line annotations), grouped by *what we're stealing*, not by *site*. Organized: Typography / Color / Motion / Composition / Voice.

### 1.5 The "agent topology as art" hunt

Our product's killer visual is the agent pipeline (Parser → Classifier → CrossRef → RiskJudge → Router → Reporter, with the nightly Reflector loop). The Art Director runs a focused sub-hunt for:

- Pipeline / DAG / flow visualizations done with taste (Pipedream, n8n, Trigger.dev, Inngest, Temporal, Modal, Dagster).
- Animated graph diagrams (D3 force, Cytoscape gallery, ReactFlow examples).
- Particle/flow-line motion (the SVG-path-stroke-dashoffset trick, animated beams).

Note: per §1.4, candidate #2 (contract stack) is the recommended hero, not the pipeline DAG. The pipeline still appears in the "How it works" section but does not own the hero.

---

## Phase 2 — Voice, message, and information architecture

Design without a message is decoration. Before pixel work, the **Copy Lead** (§3) writes the page first, in plain text.

### 2.1 Message stack

- **Tagline (working candidate)**: *"M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from."*
  - Removes the prior "judge" ambiguity (parsed by GCs as Article-III judge).
  - Removes the "survives a deposition" framing that *itself* raised a malpractice flag (implying tool output is being introduced as evidence).
  - Front-loads the Arize Phoenix integration that the partner-track judges score on.
  - Names the artifact (clause-level sourcing) and the audit posture without overpromising the legal weight.
  - Copy Lead's job in Phase 2 is to A/B against ≥3 alternatives and lock one in `COPY.md`. Other candidates: *"Contract review with an audit trail your partners can click into — every flag back to its clause, every verdict back to its Phoenix span."* / *"M&A contract review: every flag sourced, every verdict traced."*
- **Hero sub-line (load-bearing — must communicate the conservative-stats wedge in 10 seconds)**: *"Wilson lower bounds, frozen held-out fold, paired-bootstrap CI gates. We report the worst case, not the best."*
- **Three pillars** the page must communicate:
  1. **Sourced** — every decision links to its Phoenix span; every flag links to the clause it came from. Not a black box.
  2. **Honest** — Wilson lower bound, frozen held-out fold, no cherry-picked metrics. *We brag about being conservative.*
  3. **Self-improving** — nightly Reflector loop with paired-bootstrap CI gates and a non-regression check on a frozen fold.

### 2.2 Section anatomy

1. **Nav** — wordmark (see §5.6), single CTA ("Try the demo"), unobtrusive.
2. **Hero** — tagline + sub-line + primary CTA + secondary CTA ("Watch 60s demo"). Visual: candidate #2 from §1.4 (or fallback #5 — editorial typographic hero). *Phoenix appears in the sub-line, not just in the footer logo wall.*
3. **The problem** — *Monday-morning board call. Exhibit 2.1 hit Friday 6pm. Three associates, two paralegals, one MAC clause nobody has read.* Visceral, partner-POV, with one striking number. (Prior draft framed this from the junior associate's POV — GCs identify with the partner who signs the opinion letter, not the associate who got the file.)
4. **How it works** — the agent pipeline, expanded interactively. Hover a node, see what it does + its real prompt.
5. **The audit trail (the moneymoment)** — see §6.4. Dedicated subsection treatment, dedicated motion budget, dedicated review gate. 1.5 viewports of vertical space. Includes both the trace AND a "click any span" interaction. **This is where the page is won or lost.**
6. **What this is not** — *GC-trust-builder*. A five-bullet honesty block. Each bullet has a *concrete* answer in `COPY.md` — placeholder text is not acceptable; this is the section a GC screenshots to forward to InfoSec, and vague language kills the procurement.
   - **Not legal advice.** Output is a triage aid; sign-off remains with counsel.
   - **Not trained on your documents.** Inference-only; no fine-tuning or retention beyond the session.
   - **Not a substitute for partner sign-off.** The Router emits a recommendation; the partner emits the decision.
   - **Data handling — required fields locked in `COPY.md`**: (a) processing region (Cloud Run region + zone), (b) retention TTL in hours, (c) who holds the encryption keys (customer-supplied vs. Google-managed), (d) deletion-on-request path and SLA.
   - **Security posture — required fields locked in `COPY.md`**: SOC 2 status (e.g. *"Type II in progress, target [date]"*), pen-test status (*"scheduled / completed by [firm]"*), and whether the report is shareable under NDA. This is the "what we will commit to do, on a date" layer that converts the honesty block from a defensive crouch into a credible posture.
   - **Trust-packet items for the future `/security` sub-page** (called out here so a GC reader who clicks through sees the trail isn't ending): subprocessor list (Google Cloud, model provider, Phoenix host), breach-notification SLA, GDPR Art. 28 / DPA posture for EU deals. Not required on the landing page itself, but referenced as "downloadable trust-packet — request via [email]" so the page doesn't dead-end at the honesty block.

   *Voluntary scope-limitation is the single strongest signal a GC reader looks for. Tools that won't say what they're not are hiding something.*
7. **The honest numbers** — two-layer presentation:
   - **Top layer (plain English for the GC reader)**: "We report the worst-case accuracy, not the best. We held out a third of the data and never looked at it. The nightly improvement loop has to pass a paired-bootstrap test against the frozen set before it can ship."
   - **Expandable "show the math" panel**: Wilson lower bound, 5-fold CV, calibration plot, paired-bootstrap CI. For the technical judges.
8. **The self-improving loop** — Reflector cron animated as a loop with the gate that blocks regression. Phoenix trace IDs visible on the gate output.
9. **Try it** — the demo (5 pre-indexed deals). See §"Resolved decisions" for embed strategy.
10. **Built on / Where it lives** — *restructured*. Lead with the **deployment story** that the architecture actually supports today (Cloud Run region + zone, retention TTL in hours, no training-set usage, key-management posture, BAA-equivalent status). Do *not* claim "your data stays in your project" — the current architecture is single-tenant Cloud Run, not per-customer GCP projects; a GC catches that claim in five seconds. The defensible version reads as *"documents are processed in [region], not retained beyond [N] hours, and never used to train any model."* Logos come *after* the story, with **Arize Phoenix annotated as "open-source observability"** so a GC who Googles it doesn't read it as a startup dependency risk.
11. **FAQ / objections** — *GC objections*, not dev-Twitter objections. **Hard requirement**: draft answers (not just questions) land in `COPY.md` by Day-2 EOD and are reviewed by the GC-persona before Day-3 build starts. Weak answers ("we take privilege seriously") invert the section — the team signals they don't understand the question. Day-6 pre-merge gate: GC-persona legal review pass.
    - **Privilege**: does using this waive work-product? Where is the data processed; who can subpoena the logs?
    - **Standard of care / malpractice**: if I rely on a Block call and miss a MAC, who is on the hook?
    - **Confidentiality / data residency**: are deal docs training future models? BAA-equivalent posture?
    - **Model continuity**: if Google deprecates Gemini 3 mid-deal, what happens?
    - **Conflicts**: if opposing counsel uses the same tool, does that create issues?
    - (Dev-audience FAQs — "is this a wrapper?" / "why not GPT?" — get a single collapsed line at the bottom, not their own block.)
12. **Devpost demo-scope paragraph** — the required disclosure from `README.md` ("hosted demo runs against a curated list of five recent 8-K/Ex 2.1 merger filings, pre-validated to surface at least one change-of-control, anti-assignment, or MAC-related finding so the agent has something interesting to do on camera. The filings are fetched live from EDGAR via the EdgarTools MCP server at demo time.") — included in `COPY.md` from Day 1, not surprised on Day 6.
13. **Footer** — credits, license, hackathon attribution, one easter egg, build SHA + model pin (see §7.3).

### 2.3 Voice rules

- **Specific over abstract.** "Exhibit 2.1 hit Friday 6pm" > "complex legal documents."
- **Numbers over adjectives.** "Wilson 95% LB" > "highly accurate."
- **Quiet humor allowed.** One footer easter egg, one 404 page. **No console.log easter egg** — for a serious legal tool, a "hi judge 👋" in DevTools is the exact cue that flips a GC's verdict from "real" to "hackathon project cosplaying as software." See §7.3 for the replacement.
- **No marketing-bro words.** Ban list:
  - General: *revolutionize, unleash, supercharge, leverage, robust, seamless.*
  - **Legal-tech specific** (worse for our audience): *AI-powered, trusted by, next-generation, enterprise-grade, purpose-built, human-in-the-loop, co-pilot, transform your practice, white-glove.*
- **Never claim "trusted by [logos]" without named, real users.** Implying customers you don't have reads as a lie the moment a GC clicks to verify.

**Deliverable**: `design/COPY.md` — full page copy, written before any visual design. Includes the Devpost demo-scope paragraph (§2.2 #12). Reviewed by `expert-review-loop` with reviewers Skeptic / GC / Hackathon Judge.

---

## Phase 3 — The agent team

A flat "spawn five agents and average their output" pattern produces mush. We use a structured team with explicit roles, deliverables, and one final decision-maker.

### 3.1 Roles

**Supervisor / Creative Director** (one agent, persistent across the project)
- Owns this plan and `PROJECT_LOG.md` entries for the design track.
- Spawns specialists, reviews deliverables against §0's central tension.
- Has **veto power** on any decision. Does not write code directly.
- Triggers `expert-review-loop` at the two checkpoints (post-plan, pre-launch).

**Art Director** (persistent)
- Owns the moodboard, color palette, type system, motion principles.
- Reviews at **section-completion checkpoints** (not per-component) — see §3.2 bottleneck fix.
- Maintains a **"forbidden patterns" list** to prevent generic drift.

**Frontend Architect** (persistent)
- Owns the tech stack, repo layout, build/deploy pipeline, scaffold cleanup (§0.4).
- Sets and enforces performance budgets (§6.2).
- Reviews every PR for bundle bloat and re-renders.

**Motion Designer** (persistent)
- Owns animation choreography across the page — *the* multiplier for the Devpost video.
- Picks the animation library (§4.3).
- Maintains animation timing system (easings, durations, stagger, scroll constants, page-load choreography — see §4.3 expanded).

**Copy Lead** (persistent)
- Owns `COPY.md`, voice rules, FAQ answers, error/loading microcopy, the Devpost demo-scope paragraph, the OG image text.

**Component Builders** (2–3, ephemeral, spawned per section)
- Implement sections from the approved spec **within pre-approved tokens** (§5.5). They ship to merge without per-PR Art Director review as long as no token is violated and no novel pattern is introduced. Escalate only on token-violations or novel patterns.

**QA / Perf agent** (ephemeral, spawned for the polish pass)
- Lighthouse, axe-core, real-device check, dark mode parity, reduced-motion fallback.
- Reports against the perf budgets set by the Frontend Architect.

### 3.2 How they collaborate

```
Supervisor
  ├── Phase 0 tooling + scaffold cleanup → Frontend Architect (owns)
  ├── Phase 1 inspiration mining  →  Art Director (owns), Copy Lead (assists)
  ├── Phase 2 message/IA          →  Copy Lead (owns), Art Director (reviews)
  ├── Phase 4 stack + animation   →  Frontend Architect (owns) + Motion Designer (consult)
  ├── Phase 5 design system       →  Art Director (owns) + Motion Designer
  │   └── Output: tokens.ts + SYSTEM.md. After this, Builders ship within tokens.
  ├── Phase 6 build               →  Frontend Architect coordinates Component Builders
  │   └── Each SECTION (not component): spec → build → AD section-review (≤1/day) → Motion Designer pass → merge
  └── Phase 7+8 polish            →  QA agent + expert-review-loop (final gate)
```

**Bottleneck fix**: Prior draft had AD reviewing every component, which serializes a parallel team. AD reviews **at section-completion only**, max 1/day. Component-level decisions are owned by Builders within the locked token system. Builders escalate **only** on token-violations or novel patterns not covered by §5.5.

**Parallelism rule**: Component Builders run in parallel *only* on independent sections (hero, FAQ, footer can build at once; problem-section and how-it-works share a visual language so they're sequential).

**Handoff rule**: every handoff includes a written spec — never "the previous agent's output should be self-explanatory." Each spec answers: what does this section communicate, what does it look like, how does it move, what are the edge cases (mobile, reduced-motion, dark mode, slow connection).

### 3.3 Decision-making

- **Reversible decisions**: any agent can make them. Move fast.
- **Hard-to-reverse design decisions** (color system, typography, animation language, framework): require Art Director + Supervisor sign-off, captured in `PROJECT_LOG.md`.
- **Disagreements**: written 1-paragraph position from each side → Supervisor decides. No endless back-and-forth.

---

## Phase 4 — Tech stack

### 4.1 Framework — committed: extend the existing Next app (option A)

**Decision (made in Round-A review by the Frontend Architect reviewer)**: Marketing at `/`, product console at `/console`, one Next 15 app, one deploy, shared design tokens. Rationale:

1. Scaffold already exists (`ma_gatekeeper/frontend/`, Next 14.2.5 to upgrade).
2. `/reflect` lives in the same Next app — same-origin makes iframe auth survive Safari ITP.
3. One repo = one design-tokens source-of-truth (no workspace-package divergence by Day 6).
4. Vercel deploy is one click; OG image generation via `@vercel/og` is native.

**Astro-standalone is the fallback**, triggered if: Day-4 hero LCP measured on emulated mobile exceeds 2.8s and cannot be brought under by code-splitting. In that case, marketing splits to a standalone Astro site at the apex domain, with `/reflect` moving to `app.subdomain` — but this is a Day-4 recovery option, not a kickoff debate.

**Day-2 EOD lock**: Frontend Architect confirms the decision (or invokes the fallback rationale) in `STACK.md` by EOD Day 2. After that, the framework decision is closed.

| Rejected alternative | Why |
|----------------------|------|
| SvelteKit 2 | Context-switch out of React; smaller ecosystem for the borrowed component patterns. |
| Remix / RR v7 | No clear advantage over Next; smaller marketing-page ecosystem. |
| Plain Vite + React | Rebuilds what Next gives us free; bad use of hackathon hours. |

### 4.2 Styling

**Tailwind CSS** — already in repo, fast iteration, tokens via config. **Adopted.**

Art Director enforces a **design tokens layer** (`tokens.ts` + `tailwind.config.ts` extension) — one source of truth for color, spacing, radii, shadows, type scale. Arbitrary `text-[17px]` / hex codes scattered through components = PR rejection.

### 4.3 Animation

This is the make-or-break for the "wow." Motion Designer drives.

| Library | Use when |
|---------|----------|
| **Framer Motion (motion/react)** | Default for component-level animation, scroll-triggered reveals, layout animations. **Adopt as primary.** |
| **GSAP + ScrollTrigger** | **One** scoped use: the hero scroll-jacked sequence (candidate #2 contract-stack OR the pipeline scroll-story). Not used elsewhere. Bundle cost ~45KB gz justified only by that single scene. |
| **Rive** | If candidate #2 (contract stack) ships as 2.5D rather than R3F. Excellent interactivity, much smaller bundle than Three. **Rive XOR R3F, never both.** |
| **R3F + three + drei** | Only if a team member has shipped R3F before AND the Day-3 prototype passes the Day-4 gate. Bundle cost: 150KB+ floor, often 400KB+. Code-split behind interaction or fold. |
| **Lottie** | Fallback if 3D dies. Not a fourth library in addition — only ships if R3F/Rive don't. |
| **CSS-only (Tailwind animate, View Transitions API)** | Hover states, simple reveals. **Prefer over JS where possible** for bundle size. |

**Animation principles** (Motion Designer codifies before any motion is written, recorded in `SYSTEM.md`):

*Timing primitives*
- One easing function (`easeOutExpo` or `cubic-bezier(0.16, 1, 0.3, 1)`). One.
- Three durations: 150ms (micro), 400ms (component), 800ms+ (hero). No others.
- Stagger constant: 60ms between children. No others.

*Scroll constants*
- Section "enters" at scroll-progress 0.1 of its own bounding box (not pixel offsets).
- Section "completes" at scroll-progress 0.6.
- Re-trigger on re-entry: yes for hero only, no elsewhere.

*Page-load choreography*
- 0ms: layout, fonts, static content paint.
- 200ms: hero copy fade-in (single 400ms duration).
- 600ms: hero visual begins motion.
- 1400ms: hero motion lands; idle/loop state begins.
- The first 2s define the entire video's first impression — owned by Motion Designer, signed off by Supervisor.

*Orchestration rules*
- Parallel animations on the same viewport: max two simultaneous, both completing within 800ms.
- Sequential animations: stagger by 200ms minimum (perceptible separation).
- Hero idle/loop: subtle, ≤5% canvas movement, ≥4s loop period. Must not compete with user scroll.

*Universal*
- `prefers-reduced-motion` honored everywhere. Not optional.
- Hover effects are **enhancement, not load-bearing** — the page must read as alive on a Devpost video that never hovers.

### 4.4 Supporting tech

- **TypeScript** — non-negotiable.
- **Biome or ESLint + Prettier** — pick one, configure once, never touch again.
- **shadcn/ui** — for primitives (button, dialog, tabs). Customized to our tokens.
- **Image strategy** — Next/Image; AVIF + WebP; never raw PNG above the fold.
- **Fonts** — self-host via `next/font`. See §5.2 for pairing thesis.
- **Deploy** — Vercel.
- **Analytics** — Plausible or Vercel Analytics. Default: skip unless we care about jury-traffic numbers post-submission.
- **OG image generation** — `@vercel/og`. **Adopt** — link previews on Devpost / Twitter / LinkedIn matter for the judge's first impression. **Kill-switch**: if not done by Day-6 noon, ship a static PNG.

**Deliverable**: `design/STACK.md` — Frontend Architect's written confirmation of §4.1, the styling/animation choices, scaffold-cleanup verification.

---

## Phase 5 — Design system

Art Director owns. Locked before any section is built.

### 5.1 Color — committed: deep forest emerald (one direction, not a shortlist)

**Locked palette direction**: **deep forest emerald** as the primary brand color. Rationale (the M&A semantic story, which is the protection against generic drift): *old-money law firm wood paneling and the green of money — not the green of crypto, not the green of dev tools, not the green of wellness apps.* Closer to Loro Piana green than to Linear green. Deeper, less saturated than the typical infra-green default.

- **Primary**: a single deep forest emerald in the `#0E3D2E` – `#0E5D4A` range. The Art Director picks one specific shade and ships it; "candidates to triangulate between" is not a commitment. The 5-second test (*"does this look like software you'd let near a $2B deal?"*) is the gate.
- **Background**: dark mode default. Not `#000`; a near-black with the same cool green undertone (e.g. `#0A0F0E` or `#0B1311`). Light mode is parity, not afterthought — investors land on this site on a bright laptop and we look composed in both.
- **Accent — warm clay** — a *desaturated terracotta*, not an orange. Target the `#C97B3F` / `#D89060` range; if it starts reading as "Substack orange," the saturation is too high — pull it back toward brown-clay before shipping. The single signal accent. Used **once per visible viewport, no exceptions**. This is the most distinctive token in the palette — protect it. It belongs on: a single CTA per viewport, the Block-tier risk verdict, the auto-promotion gate passing.
- **Signal-green is demoted** from a primary candidate to a 5%-of-canvas **state color only** — used to signal "Clear" verdicts and successful checks. Not a brand color. (Round-A reviewer feedback: signal-green as primary reads "GitHub Actions for lawyers" — wrong register.)
- **Functional neutrals**: borders, surfaces, hover states drawn from a neutral scale that has the *same* slight cool tint as the background — so the page feels of-a-piece, not "neutrals + a brand color stuck on."
- **Risk-lane colors** (product semantics that show in the audit-trail section and demo): green-family (low-sat signal green) for Clear, amber for Escalate, a desaturated brick red for Block. Calibrated to coexist with the brand palette without screaming.

**Constraint**: the Art Director writes the M&A semantic story for the chosen primary in two sentences and pins it to `SYSTEM.md`. If the sentences would apply to any non-blue infra tool, the choice is rejected and re-picked.

### 5.2 Typography — committed: editorial serif display + neutral sans body + warm mono

**Pairing thesis**: one of two lanes, picked before any type lands on the page. The plan recommends **lane A**.

**Lane A — editorial serif display + neutral sans body + warm mono** (Mercury / Stripe Press lane):
- *Display*: a serif with editorial weight at large sizes — Migra, Tobias, Söhne Schmal, GT Sectra, Tiempos Headline. Pulls the page toward "law review" without trying. **This is the single biggest move toward GC credibility.**
- *Body*: a neutral sans — Inter Variable, Söhne, or Geist. Variable axes preferred.
- *Mono*: Berkeley Mono (paid) or JetBrains Mono. Used for agent names, numbers, Phoenix span IDs, code snippets.

**Lane B — all-sans, variable axes, mono numerals** (Vercel / Linear lane):
- Available but explicitly *not* the recommendation, because it produces a page that reads as "infra tool" rather than "tool for serious money." Choose this only if Lane A's display serif feels off-register with the chosen forest-emerald direction.

**Lane A risk**: the editorial serif at body weights reads as "boring corporate law firm." Mitigation: serif is locked to **display weights only** (headlines, the moneymoment number, section openers); body and UI text live in the neutral sans. The warm-clay accent (§5.1) plus the playful micro-interactions (§0.1) prevent the page from reading as a 1998 white-shoe firm site.

**Type scale**: 8 sizes, golden-ratio adjacent. No arbitrary `text-[17px]` in components.

**Lock date**: Lane A vs B chosen by **Day-2 EOD**, locked in `SYSTEM.md`. Wordmark (§5.6) depends on this choice and cannot start until it's settled.

### 5.3 Motion language

Defined in §4.3 — locked here. Includes timing primitives, scroll constants, page-load choreography, orchestration rules.

### 5.4 Iconography

Lucide as the default. Custom illustrations only for: the agent topology diagram, the Reflector loop diagram, the 404 page. Everything else uses the system icons.

### 5.5 Component primitives

Built once, used everywhere: Button (3 variants), Card, Badge, Dialog, Tabs, Code (with copy), Annotated-Number (tooltip on hover explaining the stat), Trace-Span (the moneymoment building block — see §6.4). Each component has hover + focus + disabled + loading states defined. After the primitives ship, Builders ship to merge without per-PR AD review (see §3.2).

**Repo layout for shared components**:
- `frontend/components/ui/` — shadcn primitives + customized tokens. Shared between marketing and product.
- `frontend/components/marketing/` — landing-page-only sections.
- `frontend/components/console/` — `/reflect`-only components. Kept out of the marketing route bundle via dynamic imports.

### 5.6 Wordmark (new — promoted to a real deliverable)

The wordmark is load-bearing in five places: nav, footer, favicon, OG image, video title card. A wordmark that reads "ran out of time" sinks all five.

**Phase-5 deliverable**, owned by Art Director, **half-day budget**, locked by Day-3 EOD. Default direction: wordmark only (no full logo lockup needed for hackathon) — set in the Lane-A display serif at one weight, locked spacing, paired with a single mark only if it earns its place. **Kill-switch**: if not locked by Day-3 EOD, ship as Lane-A display serif at 600 weight with letter-spacing tuned — never "in the body font" or it reads as TBD.

**Deliverable**: `design/SYSTEM.md` — tokens, type scale, motion constants, icon rules, wordmark spec. Plus `design/tokens.ts` (the literal source of truth imported by the app).

---

## Phase 6 — Build choreography

Frontend Architect coordinates. Component Builders execute in parallel where dependencies allow.

### 6.1 Order of operations (with explicit cut-lines)

Effective throughput assumed: ~1.5 dev-equivalents. Day 5 is now the **moneymoment day** — pulled out of the prior overloaded list per Round-A findings.

| Day | Must-ship | Nice-to-have | Cut-trigger |
|-----|-----------|--------------|-------------|
| **1** | Phase 0 tooling audit (capped); scaffold cleanup §0.4; inspiration board started; **iframe gates (a–f) run as a single 90-minute timeboxed spike** with yes/no output (defer to mock if any gate red); OIDC-in-iframe survival test under Safari ITP | INSPIRATION.md fully sorted by what-we-steal | OIDC-in-iframe spike unresolved by EOD → iframe permanently off the table; any Day-1 item still open at EOD → drop nice-to-have |
| **2** | COPY.md draft (tagline + sub-line + all section copy + Devpost demo-scope paragraph + **GC-FAQ draft answers** reviewed by GC-persona + **D18 Reflector pre-seed disclosure**); STACK.md (Phase 4 lock); **Typography Lane A vs B locked** (§5.2); **Hero candidate locked (#2 contract-stack vs #5 editorial)** (§1.4) so Day-3 base layout has a target; wordmark direction chosen; iframe go/no-go re-confirmed | FAQ answers GC-persona-reviewed (vs. just drafted) | If COPY.md tagline not locked → escalate to Supervisor before Day 3; typography not locked → wordmark slips, cascade fail |
| **3** | tokens.ts + SYSTEM.md locked; wordmark locked; hero base layout (no motion yet); 3D prototype (if pursued) | "What this is not" section copy reviewed by GC-persona | Wordmark not locked → ship default (display serif at 600); 3D prototype not "wow" → kill, fall back to candidate #5 |
| **4** | Hero motion choreography (lead Motion Designer); Problem + How-it-works sections | Mobile fallback for scroll-jacked hero; framework Astro-fallback evaluation (only if LCP > 2.8s) | Hero motion not landing by EOD → strip to Framer reveals; Day-4 scroll-jacked mobile gate failed → fallback |
| **5** | **Moneymoment (sole focus)** — audit-trail subsection with trace card, span-click interaction, motion choreography. See §6.4. | Begin numbers section | Moneymoment not at v1 by EOD → cut everything else from Day 6 to protect it |
| **6** | Numbers section (two-layer); "What this is not" (with concrete data-handling + security-posture answers — no placeholders); Reflector loop section (static SVG if animation at risk); Built-on/Where-it-lives; FAQ (GC-persona legal-review pre-merge gate); footer | Animated Reflector loop; OG image (static fallback ready at noon) | Reflector animation not on track by noon → ship static SVG; OG not done by noon → ship static PNG; **at noon if behind: Built-on collapses to single logo strip (no deployment-story narrative this round) AND FAQ collapses to top-3 questions only** — moneymoment polish takes priority |
| **7** | Polish pass; `expert-review-loop` final round; `verify` browser check; perf budget enforcement; Devpost video recording; deploy | 404 page; favicon | Anything still un-polished after lunch → cut from scope, do not slip the recording |

**Scope freeze**: at Day 5 EOD the §2.2 section list is **frozen**. No additions accepted, only cuts. This is the written defense against the inevitable Day-5 pressure to add pricing / testimonials / "one more 3D thing" / comparison-vs-Harvey-Kira.

**Kill-switches summary** (in addition to §1.4 3D, §1.4 scroll-jacked-on-mobile, §4.4 OG, §5.6 wordmark):
- **Framework choice**: Day-2 EOD lock — defaults to §4.1's committed (A) Next-extended. Astro fallback only on §4.1 LCP trigger.
- **OIDC-in-iframe survival** (§Resolved decisions): Day-1 EOD spike. If unresolved, iframe permanently off the table — mock-only, no more deliberation.
- **Typography Lane A/B** (§5.2): Day-2 EOD. Lane-A fallback if the chosen editorial serif fails to license/load cleanly: Söhne or Inter Display at display weights instead, body and mono unchanged — never the body font at 600 weight as a wordmark stand-in.
- **Phoenix trace animation** (§2.2 #5 / §6.4): Day-5 morning gate — if iframe still mocked AND the animation is not feeling right, ship the moneymoment as a designed static "play" card with the trace pre-rendered, not a live animation.
- **Reflector animation** (§2.2 #8): Day-6 noon gate — static SVG fallback.
- **OG image** (§4.4): Day-6 noon gate — static PNG fallback.
- **Day-6 pile-up cut**: at Day-6 noon, if Reflector animation has eaten time, Built-on collapses to a single logo strip and FAQ collapses to top-3 questions.

### 6.2 Performance budgets (set by Frontend Architect)

Round-A reviewer flagged the prior 150KB-gz target as fiction once Framer + GSAP + R3F enter the picture. Revised to realistic + enforceable:

- **LCP** < 2.4s on emulated mobile (Next App Router realistic ceiling with the chosen stack; sub-1.8s only if we ship Astro-fallback).
- **CLS** < 0.05.
- **JS above-the-fold (landing route)** < 180KB gz. The iframe, the 3D scene, and `/reflect`'s `react-pdf` imports are **all code-split / lazy-mounted / dynamically-imported below the fold**.
- **Total landing-route JS (including lazy-loaded)** < 350KB gz.
- **Lighthouse** ≥ 90 across all four. (95 only on Astro-fallback. 90 is the gate that doesn't lie.)
- **`prefers-reduced-motion`** path tested.
- **First contentful paint without JS executing** — text-readable, layout-stable.

Frontend Architect enforces these with a **mechanical CI check**, not vibes: `size-limit` (or `next-bundle-analyzer` threshold) wired into the PR pipeline gates 180KB above-fold and 350KB route-total. **LCP methodology**: Lighthouse mobile preset on Moto G4 emulation profile, measured against the deployed Vercel preview, three-run median. "Sub-2.4s" with no methodology named is a vibe; with this protocol it's a number. Budget violation = no merge. Pick *two* of {motion-heavy hero / R3F / live iframe} — all three breaks the budget.

### 6.3 Hero section is special

The hero is 40% of the visual impact. We allocate **two full days** to it alone:
- Day 3: structure, copy placement, base layout.
- Day 4: motion choreography (animated topology or candidate #2), polish, mobile fallback.

Motion Designer leads, Art Director reviews each iteration, Supervisor signs off on the final.

### 6.4 The moneymoment section is also special (new)

The audit-trail section (§2.2 #5) is the page's single strongest argument. The prior draft buried it in a list. Now it gets parity with the hero:

- **Dedicated day**: Day 5 (sole focus — no other section work that day).
- **Vertical real estate**: 1.5 viewports minimum.
- **Required interactions**: a "play" sequence that auto-runs on scroll-into-view, AND a hover/click on any span that surfaces the underlying prompt/response/eval verdict.
- **Dedicated motion budget**: separate from §4.3 constants for this section only — Motion Designer signs off on a per-frame timing sheet.
- **Dedicated review gate**: Art Director + Motion Designer + Supervisor co-review at Day 5 EOD, before merge.
- **The gesture (v0 — to be sharpened on Day 5)**: as the user scrolls into the section, the trace card "unfurls" span-by-span — each span fading in left-to-right like a redline draft being read; the RiskJudge span lights with the warm-clay accent (§5.1) at the moment a Block verdict resolves; on hover/click, the lit span lifts ~8px off the surface and reveals the underlying prompt + Phoenix span ID + eval verdict in a side card. The unfurl-then-lift sequence is the specific weird-but-tasteful gesture that distinguishes this section from "another animated card."
- **Engineered screenshot frame**: one specific frame designed to be screenshot-worthy as a still — composed of: (a) the **Wilson-LB recall headline number** (e.g. "0.94 Wilson 95% LB" rendered in the Lane-A display serif at maximum scale), (b) the Block verdict badge in warm clay, (c) the Phoenix span ID rendered in mono just below as a small craft-signal. The Art Director draws this frame on paper before any animation lands. This is what a Devpost juror captures and remembers.
- **Fallback** (if iframe is mocked, per §"Resolved decisions"): the moneymoment ships as a designed playback of a *real* recorded review — recording is fine, fakery is not.

---

## Phase 7 — Polish for the Devpost video

The video is the artifact the jury actually watches. We design the scroll for it.

### 7.0 Video script + storyboard (new — must lock before §7.1 capture work)

Per Round-A reviewer, the prior draft confused *capture settings* with *video production*. The video needs a written shot list before anyone presses Record.

**Locked structure for a ~2:30 video** (Copy Lead + Supervisor own; Motion Designer maps timing to scroll choreography):

| Time | Beat | What's on screen | Narration |
|------|------|------------------|-----------|
| 0:00–0:05 | **The hook** | Hero frame with tagline + Phoenix span ID visible | One line, voice-over: the differentiator in one sentence. |
| 0:05–0:30 | **The problem** | Problem section — Monday morning board call vignette | Set the partner-POV stakes. |
| 0:30–1:25 | **The moneymoment** *(rebalanced — 55s)* | Audit-trail playback (§6.4) — trace unfurls span-by-span, RiskJudge span lights, span clicked, prompt + Phoenix span ID + eval verdict revealed; engineered screenshot frame held for ~2s | "Every flag is sourced to the clause. Every verdict links to its Phoenix trace." |
| 1:25–1:55 | **The honest numbers** | Two-layer numbers section, "show the math" expand | "We report the worst case. The improvement loop has to beat a frozen held-out set." |
| 1:55–2:15 | **The self-improving loop** | Reflector animation + the gate visualizing | The Arize partner-track wedge. Phoenix MCP visible on screen. |
| 2:15–2:30 | **The CTA** | Demo dropdown, 5 deals visible, deploy URL in lower third | "Live at [domain]. Five real deals. Click any verdict." |

Copy Lead locks the narration script in `COPY.md` by Day 2 EOD. Re-cut after the moneymoment lands on Day 5.

### 7.1 Scroll choreography

- The page must "perform" with a steady scroll input — no section requires user interaction to reveal its payload.
- Hero auto-plays its motion within 2s of load, then loops subtly (per §4.3 orchestration rules).
- Pipeline section auto-runs once on first scroll into view; user can re-trigger by hovering.
- Numbers count up on scroll-into-view.
- Audit-trail section "play" auto-triggers on scroll-in.

### 7.2 Capture pass

- Record at 1440p minimum, 60fps. Devpost compresses; we start high.
- Use a clean Chrome profile (no extensions, no zoom).
- Pre-load all fonts and images before recording.
- Two takes minimum: one scroll-only (for B-roll), one with cursor (for "they really built this").
- Narration recorded separately (clean audio), mixed in post against the storyboard timing.

### 7.3 The deployed live page

Because the jury *might* click through:
- Hover states matter — make them earn their keep (per §0.1, this is where "playful" lives).
- The demo embed must work first try, with the 5 pre-indexed deals visible immediately.
- 404 and error states are designed, not Next-default.
- **Console signal — engineering discipline, not jokes**. Replace the prior console.log easter egg with a one-line build/model annotation:
  ```js
  console.info('build: %s · model-pin: gemini-3-pro-2026-04 · evals: design/EVALS.md · csp: strict', BUILD_SHA);
  ```
  A GC who opens DevTools is *auditing* the tool, not high-fiving. This reads as engineering rigor; the prior "hi judge 👋" read as juvenile.

---

## Phase 8 — QA, accessibility, sign-off

QA agent + `expert-review-loop` run the final gate.

### 8.1 Accessibility

- All interactive elements keyboard-reachable.
- Color contrast ≥ 4.5:1 for body text, 3:1 for large text.
- Motion respects `prefers-reduced-motion`.
- Screen-reader labels for icon-only buttons.
- Skip-to-content link.
- `axe-core` clean.

### 8.2 Cross-environment

- Chrome, Safari, Firefox. Latest 2 versions.
- iPhone (Safari), Android (Chrome) — at least one real device, not just emulator.
- Slow 3G throttled — page is usable within 3s.
- Dark mode AND light mode — both reviewed by Art Director.

### 8.3 Final review loop

`expert-review-loop` with reviewers:
- **Hackathon Judge persona** — "would this make me stop scrolling?"
- **Skeptical M&A Counsel / GC persona** — "do I trust this with a real deal?"
- **Senior Frontend Engineer** — "is this technically tight or held together with vibes?"
- **Accessibility Auditor** — "does this work for everyone?"

Iterate until all four return VALIDATED.

---

## Resolved decisions

- **Framework** — **(A) Extend existing Next.js app at 14.2.5→15**. Marketing at `/`, console at `/console`. Astro-standalone is the Day-4 fallback only if hero LCP exceeds 2.8s and cannot be brought under by code-splitting. See §4.1.
- **Domain**: user is sourcing a custom domain before launch. **Day 7 blocker** — Frontend Architect tracks; if not pointed by Day 6, fall back to `*.vercel.app` rather than slip launch.
- **Demo embed** — **designed-mock is the base case, shipped Day 5–6**. Per `PROJECT_LOG.md`, the product-track `/reflect` frontend lands ~June 5 (design-Day-14), well after the design build-out. Planning the marketing page against a surface that doesn't exist would have been broken from Day 1.
  - **Base case (default plan)**: The audit-trail section ships as a designed mock of `/reflect`, built to be visually indistinguishable from the live surface and recorded for the Devpost video. The "Try it" section links to the deployed `/reflect` when it exists; until then, links to a "preview" notice with the demo-scope paragraph.
  - **Upside swap**: if `/reflect` does land iframe-ready by design-Day-6, swap the embed in. **Day-1 EOD Frontend Architect confirms**: (a) same-origin embed (works because both surfaces live in the same Next app per §4.1), (b) `X-Frame-Options` / `frame-ancestors` set on the FastAPI server.py to allow the marketing origin, (c) OIDC flow survives iframe under Safari ITP (test before commitment), (d) mobile fallback — static screenshot + "open in new tab" CTA below 768px, (e) skeleton + warm-ping to mask Cloud Run cold-start latency, (f) loading/error/timeout states designed.
  - **Recording**: the Devpost video is shot against whichever variant is live by Day-7 morning. The mock is built to be recording-quality regardless.
- **Color** — **deep forest emerald primary + warm clay accent + signal-green-as-state-only**. See §5.1.

**Two user-locked items were updated based on Round-A reviewer findings**; both flagged separately to the user before applying:
1. The iframe-by-Day-5 commitment was found to be mathematically blocked by the product timeline (PROJECT_LOG fact-check, not opinion). Rewritten to mock-as-base.
2. The framework deferral was found by the Frontend Architect reviewer (who would be the deciding agent) to be theater — the scaffold has half-decided. Rewritten to commit-to-A with Astro fallback trigger.

## Open questions still to clarify

These don't block kickoff but the Supervisor resolves them in week 1:

1. **Video length target** (~2:30 default, see §7.0). User preference adjusts the scroll-to-end pacing.

(Wordmark was promoted from this list to §5.6 as a real deliverable.)

---

## What this plan deliberately does *not* include

- A full visual mockup — generated *during* Phase 5 with the agent team.
- A line-by-line component list — Component Builders write those specs themselves during build, within the locked token system.
- A copy-paste tech config — Frontend Architect writes that in `STACK.md` after Day-2 EOD confirmation.

The plan is the **rules of the game**, not the moves.

---

## Deliverables produced by this plan (all under `design/`)

```
design/
  PLAN.md            # this file
  TOOLING.md         # Phase 0 output
  INSPIRATION.md     # Phase 1 output (with screenshots)
  COPY.md            # Phase 2 output — full copy + Devpost demo-scope paragraph + video narration script
  STACK.md           # Phase 4 confirmation
  SYSTEM.md          # Phase 5 — tokens, type, motion, wordmark
  tokens.ts          # source of truth, imported by the app
  REVIEW_NOTES.md    # expert-review-loop outputs at each checkpoint
```

When you approve this plan, the Supervisor agent's first move is Phase 0. Nothing visual happens before then.
