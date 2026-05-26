# Inspiration Board

> Phase 1 deliverable per `design/PLAN.md` §1.
> **Owner**: Art Director (Copy Lead assists on §Voice).
> **Locked**: 2026-05-24 (v2 — fully populated, organized by *what we're stealing*, not by site, per PLAN §1.4).
> **Asset capture**: this revision ships *URLs + annotations only* per PLAN §1.4's stated fallback ("if Playwright MCP not installed, URLs + 1-line annotations are acceptable"). If the user later approves Playwright MCP install (TOOLING.md §2.4), the Art Director runs the screenshot pass into `design/screenshots/{typography,color,motion,composition,voice}/` using the file convention documented at the bottom of this file.

---

## How to read this document

- **Each section is named for what we're stealing**, not for a site or technique. A single reference site appears in multiple sections when it teaches multiple lessons.
- **Each entry** has: (source, URL, the specific thing to steal in one sentence, and either a *use here →* applied target inside our build or a *reject because →* note explaining why we're rejecting an adjacent cliché).
- **Anti-references** are folded in at the bottom of each section, not segregated to a separate page — so the contrast is visible at the point of decision.
- **The §1.4 semantic-justification rule** is in force: any visual borrowed for a load-bearing surface (hero / moneymoment / agent-pipeline) must survive a one-paragraph M&A-specific justification before it ships. The notes flag this where it applies.

---

## §Typography

The single biggest lever for the §0.1 "serious owns" register. PLAN §5.2 Lane A (editorial serif display + neutral sans body + warm mono) is the recommended path. References below build the case and provide concrete patterns.

### What we're stealing

- **Stripe Press — https://press.stripe.com** — Editorial serif at oversized hero scale, paired with a neutral sans for chrome. The serif is *load-bearing*, not decorative. *Use here →* hero tagline (PLAN §2.1) in Lane-A display serif, body in Inter; this is the GC-credibility move that distinguishes us from a generic dev-infra page.
- **anthropic.com** — Restrained typographic scale, generous whitespace, the *one* hero word doing the work instead of three. The page reads as "we have nothing to prove." *Use here →* hero copy length cap; resist the urge to put the sub-line at hero-size weight.
- **Mercury — https://mercury.com** — Display serif for headlines coexisting with a clean sans for product copy. Proof that the editorial-serif-display lane works for a serious-money product and doesn't tip into "1998 white-shoe firm." *Use here →* directly addresses the PLAN §5.2 Lane-A risk callout (corporate-law-firm failure mode). Study how Mercury's body-paragraph density keeps the page modern.
- **Linear — https://linear.app** — Variable-axis Inter at body, monospace numerals for "calm." Mono numerals as a *craft signal*. *Use here →* mono for agent names, Phoenix span IDs, the §6.4 Wilson-LB headline number. JetBrains Mono (or Berkeley Mono if the user funds Option A) is the locked candidate.
- **Vercel — https://vercel.com** — Mono numerals in dashboard charts, treated as art. Proof the mono-as-craft pattern survives at the marketing-page register. *Use here →* §2.2 #7 "honest numbers" section — Wilson LB, fold size, CI width all in mono.
- **Cursor — https://cursor.com** — Trace/log text shown as a *typographic composition*, not as developer chrome. The terminal-style block reads as deliberate design, not a screenshot. *Use here →* §6.4 audit-trail moneymoment — the trace card is typography, not a chart.
- **resend.com** — Headline rhythm: a short verb-noun headline followed by a longer concrete sentence. The rhythm makes the page feel *spoken*, not *marketed*. *Use here →* PLAN §2.1 tagline + sub-line cadence (Copy Lead's job in Phase 2).
- **cal.com** — Personality in microcopy at typographic scale — buttons, labels, empty states have written voice without breaking the type system. *Use here →* loading-state and error-state copy in `COPY.md`; resist the marketing-bro words (PLAN §2.3 ban list).

### Reject because

- **Word-by-word fade-in-with-blur headlines** (common on Awwwards SOTD entries): 4-second readability tax kills the 10-second hero test PLAN §6.4 requires. Reject as a pattern even when borrowing from sites that use it.
- **All-uppercase oversized hero** (Awwwards default): reads as brutalism cosplay on an M&A surface; loses the editorial register.
- **The "thin display sans" wordmark** (rauchg.com / leerob.io lane, explicitly removed from PLAN §1.2): correct register for a personal engineer site, wrong for an M&A pitch.

---

## §Color

PLAN §5.1 locks deep forest emerald + warm clay accent + signal-green-as-state-only. References below build the case and show how serious colors can *carry* a page without sliding into either crypto-green or corporate-drab.

### What we're stealing

- **Mercury — https://mercury.com** — Mineral-rich, brand-distinct color (their pinks/peaches) that *does not* read as fintech-bro. The lesson: a confident accent is a brand-moat, but the saturation must be tuned low. *Use here →* warm-clay accent (PLAN §5.1) at the *desaturated terracotta* level — if it starts reading as Substack orange, pull it back toward brown-clay. This is the most distinctive token in our palette; protect it. **anchor-candidate (verify via Playwright):** Mercury's peach/clay accents commonly sample in the `#F4D4BE` – `#E8B89A` band — that's the *upper saturation ceiling* we stay below, not the target. Our warm-clay target sits ~30% darker + ~20% less saturated → **proposed token `--accent-clay: #B86F3D`**, mid-range of PLAN §5.1's `#C97B3F`–`#D89060` band, deliberately *one step warmer* than Anthropic clay so it carries the §0.1 "playful lives in accent" load. *(Added Round-2 — AD Round-1 finding: anchor row b.)*
- **Stripe Press — https://press.stripe.com** — Restraint: the page is mostly off-white + black + one quiet color block per spread. *Use here →* light-mode parity for our build — dark mode is our default but the light pass must look this composed, not like a forced inversion. **anchor-candidate (verify via Playwright):** Stripe Press body background is ~`#FAFAF7` (warm-paper white, not `#FFF`); body text ~`#1A1A1A` (not pure black). Our light-mode background = `#FBFAF5` (slightly warmer to coexist with the clay accent), body = `#0E1311` (matches dark-mode background as inversion-color so the eye perceives parity).
- **anthropic.com** — Sage / clay / cream palette that proves "warm earth tones for a serious AI lab" is a viable lane. Adjacent to our forest-emerald direction but not identical. *Use here →* sanity check for our risk-lane color calibration (PLAN §5.1: green-family low-sat for Clear, amber for Escalate, desaturated brick red for Block) — Anthropic shows these can coexist with a brand palette without screaming. **anchor-candidate (verify via Playwright):** Anthropic sage commonly samples ~`#C4B996`; their clay ~`#C9956D`. **Proposed primary forest-emerald token `--brand-primary: #0F4A38`** — mid-range of PLAN §5.1's `#0E3D2E`–`#0E5D4A` band, cooler than Anthropic sage, deeper than Linear infra-green, passes 4.5:1 contrast on `#0B1311` dark-mode background. *(Added Round-2 — AD Round-1 finding: anchor row a — this is the single hex pick that unblocks `tokens.ts` row-1.)*
- **Linear — https://linear.app** — Dark mode that is *not `#000`*. Their near-black has a slight cool tint that gives depth without losing legibility. *Use here →* PLAN §5.1's `#0A0F0E` / `#0B1311` direction. The neutrals scale must share the brand's cool green undertone. **anchor-candidate:** Linear's near-black is ~`#08090A` with a cool-blue tint. Ours: `#0B1311` (cool-green tint to match `--brand-primary` undertone). Neutrals scale derived: `--neutral-900: #0B1311 / -800: #14201C / -700: #1E2D27 / -600: #2D3F37 / -500: #4A5F55 / -400: #7A8F83 / -300: #A8B8AE / -200: #D2DCD5 / -100: #ECEFEC / -50: #F4F6F3` — each step holds the cool-green undertone Linear holds cool-blue.
- **Vercel — https://vercel.com** — Dark gradient hero with one accent color earning its place. *Use here →* PLAN §1.4's mesh-gradient backdrop in our locked palette, at the constrained angles {15°, 165°, 345°} and ≤0.4 opacity.
- **trigger.dev** — Pipeline visualizations where color encodes state (running / queued / failed) without using the universal red/yellow/green. *Use here →* §6.4 trace-card span lighting — the RiskJudge span lights in warm-clay (not red) at the Block moment; signal-green stays demoted to 5%-of-canvas state per PLAN §5.1.

### Reject because

- **Purple-to-pink "AI" gradient** (every YC W24 site): explicitly anti-referenced in PLAN §1.3 — generic *because* it has no relationship to the brand. Reject even on otherwise-good sites.
- **Conic gradients used as "wow"** (Linear's earlier work; many Spline-hero pages): conic gradients in our palette are permitted only if they encode meaning (e.g. scroll-progress through the pipeline). Decorative conics = no.
- **Full-bleed `from-purple-500 to-pink-500`** (Tailwind starter-template tell): hard ban.
- **Substack orange / WeWork mango** for our accent: warm clay must stay *brown-clay-shifted*, not orange-shifted. PLAN §5.1 cross-reference.
- **GitHub Actions signal-green as primary** (Round-A reviewer finding from PLAN review): reads "GitHub Actions for lawyers" — wrong register.

---

## §Motion

PLAN §4.3 defines the locked motion grammar (one easing, three durations, 60ms stagger, scroll constants). References below show that grammar in deployed form so we don't reinvent it.

### What we're stealing

- **Stripe Press — https://press.stripe.com** (book detail pages) — Scroll choreography that *paces* a long-form page without scroll-jacking. The reader stays in control; the page rewards attention. *Use here →* PLAN §7.1 scroll-only video capture pass — the page must perform on a steady scroll input, no required hover.
  - *gesture-spec:* native browser scroll, no `scroll-snap`, no `position: sticky` hijack. Section reveals via `IntersectionObserver` at `threshold: 0.1`, fade-in 400ms `cubic-bezier(0.16,1,0.3,1)`, opacity 0 → 1 + translateY 12px → 0. Stagger child elements 60ms.
- **Browser Company — Act II memo (https://thebrowser.company/act-ii)** — Long-form scroll choreography with editorial restraint. Pacing reference: how much vertical real estate to give each beat. *Use here →* §6.4 moneymoment gets 1.5 viewports per PLAN; the surrounding sections must breathe, not crowd it.
  - *gesture-spec:* min-height per section: hero 100vh, problem 80vh, how-it-works 100vh, **moneymoment 150vh**, numbers 80vh, loop 80vh, CTA 60vh. Inter-section padding: 96px desktop / 64px mobile.
- **Apple — Mac Pro / Vision Pro product pages** — Scroll-driven 3D / cross-fade sequences synced to scroll-progress, not pixel-offset. The "section enters at 0.1 of bounding box, completes at 0.6" pattern (PLAN §4.3) comes from this lane. *Use here →* the §6.4 trace-unfurl sequence (per-span left-to-right fade-in).
  - *gesture-spec:* GSAP `ScrollTrigger` with `pin: true` for the §6.4 section, `scrub: 1` (1-second smoothing), `start: "top top"`, `end: "+=150%"` (1.5-viewport pin). Per-span reveal mapped to `scrollProgress` 0.0–0.6 (12 spans → progress step 0.05 each), with the RiskJudge span "lighting" (background fade to `--accent-clay`, 240ms `ease-out`) triggered at progress 0.55. **Verify via Playwright** which Apple page is the exact precedent (Vision Pro `/airpods-pro` or Mac Pro `/mac-pro/2023` — both use this pattern).
- **resend.com** — Inline live-data demos (the email-render preview) that *feel* alive without being interactive. Hover-as-enhancement, not hover-as-load-bearing. *Use here →* PLAN §4.3 rule: "hover is enhancement, not load-bearing — the page must read as alive on a Devpost video that never hovers."
  - *gesture-spec:* idle loop on the hero visual — translateY oscillation ±4px over 4.2s `ease-in-out`, infinite, no pause; opacity unchanged. Hover *additionally* triggers a 120ms scale 1.0 → 1.02 lift; the idle loop continues underneath.
- **cursor.com** — Trace/agent-step animations on the homepage that show progress through a sequence. Closest semantic match to our agent-pipeline section (§2.2 #4). *Use here →* "How it works" section — hover a node, see what it does + its real prompt.
  - *gesture-spec:* per-node entry: opacity 0 → 1 + translateX -8px → 0, 400ms, stagger 60ms between siblings, single-trigger on scroll-progress 0.15. Hover-node: scale 1.0 → 1.03, 200ms; tooltip fade-in 240ms with prompt text revealed via Framer `layoutId` morph from a placeholder skeleton.
- **trigger.dev** — Pipeline node visualizations with subtle motion (pulse on active, edge-stroke animation between nodes). *Use here →* "How it works" pipeline; **avoid** using the same gesture on the hero per PLAN §1.4 (we deliberately do NOT lead with a DAG hero).
  - *gesture-spec:* node-active pulse: scale 1.0 → 1.04 → 1.0, 600ms `ease-in-out`, infinite, 2s pause between iterations; edge-stroke: `stroke-dasharray: 8 4`, `stroke-dashoffset` animated 0 → -240 over 1800ms linear, single-trigger at scroll-progress 0.15 of section bbox. **One pulse cycle visible in the Devpost video; do not loop on top of user scroll.**
- **Linear — https://linear.app** — Cmd-K palette open/close, layout-animated. The calmest possible micro-interaction. *Use here →* hover states for the navigation; the registered "feels expensive" sensation comes from layout-correct animation, not from added flourish.
  - *gesture-spec:* cmd-K panel: opacity 0 → 1 + scale 0.96 → 1.0, 200ms `cubic-bezier(0.16,1,0.3,1)`, Framer `AnimatePresence` for exit. Nav hover: underline reveal via `transform-origin: left` scaleX 0 → 1, 200ms, no color change.
- **Magic UI / Aceternity** (pattern libraries, not destinations) — The animated-beam SVG pattern and the number-ticker pattern. *Use here →* §6.4 "47 clauses parsed in 12.3s" real-time-feeling counter (PLAN §1.4); animated beams between pipeline nodes if it adds meaning, not decoration.
  - *gesture-spec:* number-ticker: `useSpring` with `stiffness: 60, damping: 18`, duration ~1800ms to settle, mono numerals (no layout shift mid-tick), trigger on scroll-progress 0.2. Animated-beam: SVG path `<path stroke-dasharray="100% 100%" stroke-dashoffset="100%" />` animated to 0 over 1400ms `ease-out`, single-trigger.

### Reject because

- **Carousel heroes** (Adobe / Salesforce / most enterprise-stack sites): hide the message behind a slide transition. PLAN §1.3 anti-reference. Reject even when borrowing from sites that use them.
- **Scroll-jacked hero on mobile <768px**: PLAN §4.3 + §6.1 Day-4 gate. If the gesture doesn't feel right on a 375px viewport, fall back to triggered Framer reveals.
- **"Infinite scroll" parallax** (Squarespace template default): no semantic meaning; performance tax for vibes.
- **Spline blob auto-rotating in the hero**: PLAN §1.3 — generic and decorative. The §1.4 semantic-justification rule kills this on contact.

---

## §Composition

Where the page *lives* on a 1440px desktop and a 375px phone — grid, hierarchy, real estate.

### What we're stealing

- **Stripe Press — https://press.stripe.com** — Macro grid restraint; the page never feels crowded, the eye always knows where to land. Section openers have *space*. *Use here →* PLAN §2.2 section anatomy — give each section its own vertical breath; the §6.4 moneymoment gets 1.5 viewports, but the surrounding sections must also breathe.
- **Mercury — https://mercury.com** — Feature blocks at large vertical scale, each one a single-message section. Resist the temptation to pack two ideas into one viewport. *Use here →* §2.2 #3 (the problem), #5 (the moneymoment), #7 (the honest numbers) — each is a single-message section in our build.
- **modal.com** — "Show the thing working" in the hero. The product is the proof, not the screenshot. *Use here →* whether candidate #2 (contract stack) or candidate #5 (editorial typographic) wins, the hero must *show* the act of reading contracts, not describe it.
- **Linear — https://linear.app** — Cmd-K vocabulary, dark/light parity, the calm. The composition reads as a *tool*, not as a marketing site cosplaying as a product. *Use here →* the §2.2 #9 "Try it" section — the demo must feel like the product, not like a marketing widget.
- **retool.com** — Enterprise legibility done without enterprise drabness. Big legible numbers, generous padding, no cramped tables. *Use here →* §2.2 #7 honest-numbers two-layer presentation (plain English on top, "show the math" expand below).
- **railway.app** — The "play with it in the hero" pattern (their deploy-from-template flow visible above the fold). *Use here →* PLAN §6.4 — the audit-trail "play" sequence auto-runs on scroll-into-view, no user interaction required for the first beat.
- **Stripe — https://stripe.com/sessions** (Sessions pages) — Long-form editorial layouts that still read as Stripe-brand. Proof that personality can coexist with very long forms. *Use here →* PLAN §2.2 has 12 sections — risk is the page reading as a tower of dossiers. Sessions pages show how to keep a long page composed.

### §6.4 engineered screenshot frame — composition spec *(added Round-2 — AD Round-1 finding: row d)*

The single frame PLAN §6.4 names as the screenshot a Devpost juror remembers. Composed by overlaying patterns from three references — this is a lift the AD draws **on paper before any animation lands**:

- **Macro frame**: Stripe Press book-detail page composition — generous left/right padding (12% of viewport each side on desktop), single-column, vertical rhythm anchored to display-serif headline + small editorial chrome below.
- **The hero number**: oversized Wilson-LB recall (e.g. `0.94`) in **Lane-A display serif at 240px desktop / 96px mobile** (Stripe Press book-title scale), tracking `-0.02em`. Below: `"Wilson 95% lower bound"` in 16px mono (`--font-mono`), `--neutral-500` color, 24px gap from the headline.
- **The Block verdict badge**: warm-clay pill (`--accent-clay: #B86F3D` background, `--neutral-50` text), 48px height, 24px horizontal padding, label `"BLOCK"` in 14px mono uppercase tracked +0.08em. Positioned 64px below the mono attribution line, **left-aligned with the number's `0` digit, not centered** — this is the weird-but-tasteful left-edge alignment that distinguishes the frame from a generic stats-card.
- **Phoenix span ID**: rendered in 12px mono, `--neutral-400`, format `phoenix:span:7f3a-...` (truncated with ellipsis if >24ch), positioned 16px below the Block badge, monospaced and *deliberately small* — the "craft signal" PLAN §6.4 names.
- **Background**: `--neutral-900` (`#0B1311`) in dark mode, `--neutral-50` in light. **No card, no border, no shadow** — the composition lives in negative space, not in a contained surface. This is the §0.1 "tasteful + weird" move: every other competitor wraps this in a card; we don't.

### Reject because

- **Three-column "features" grids of icon+headline+blurb** (every B2B SaaS landing page since 2016): generic and uninformative; the §1.4 semantic-justification rule kills these on contact.
- **Hero with hero-image-right + copy-left** (Atlassian / generic enterprise default): wastes the moneymoment-equivalent real estate; a 50/50 split signals "we have nothing distinctive to show."
- **Comparison-vs-Harvey-Kira table**: explicit Day-5 scope-freeze cut (PLAN §6.1) — adding a comparison table is the kind of late addition the freeze defends against.
- **Pricing section on a hackathon submission**: not in scope; would invert the §2.2 #6 "what this is not" honesty block by implying we have a product to sell.

---

## §Voice

Copy-side inspiration. Copy Lead owns Phase 2 / `COPY.md`; this section is *assist* — vocabulary the message stack pulls from.

### What we're stealing

- **anthropic.com** — Restrained, declarative, evidence-anchored. No marketing-bro words; each claim is testable. *Use here →* PLAN §2.3 voice rules — "specific over abstract," "numbers over adjectives." Anthropic's site is the closest existing-product proof of the register we want.
- **cal.com** — Quiet humor in microcopy without sliding into Twitter-designer cosplay. The page is friendly; the *product* is serious. *Use here →* footer easter egg, 404 page, loading-state microcopy. Bounded humor — PLAN §0.1 "playful lives in micro-interactions."
- **Mercury — https://mercury.com** — Voice that signals "we know who you are" to a CFO without flattery. Specific verbs, named integrations, no aspirational claims. *Use here →* PLAN §2.2 #6 "What this is not" honesty block — direct, fielded, sourced. No "we take privilege seriously" placeholder weakness (PLAN §2.2 #11 Day-2 GC review gate).
- **stripe.com/privacy + stripe.com/docs/security** — Fielded, declarative security-posture prose. Cadence: *verb · subject · region · retention-number · custodian*, fragmented into three-beat sentences with no marketing modifiers. Example template: *"Stripe processes cardholder data in PCI-DSS Level 1 environments in us-east-1, us-west-2, and eu-west-1. Data is retained for the term of the Services Agreement plus 7 years."* *(Added Round-2 — Copy Lead Round-1 finding: this is the cadence anchor for the §2.2 #6 honesty block; Mercury voice does not reach `us-central1` posture, Stripe's privacy/security docs do.)* *Use here →* PLAN §2.2 #6 five required fields (region+zone / TTL hours / key-holder / deletion SLA / SOC2 status) — write each in the three-beat fragment cadence. **Replace** "we take privacy seriously"-shaped sentences with `[Region]. [Number]. [Custodian].` fragments. Also the cadence anchor for §2.2 #11 GC-FAQ drafted answers — the answers read as Stripe-doc fragments, not Mercury-style aspirational marketing prose.
- **Stripe Press — https://press.stripe.com** — Editorial: authors-and-quotes voice rather than marketing-blurb voice. *Use here →* §2.2 #3 problem vignette ("Exhibit 2.1 hit Friday 6pm. Three associates, two paralegals, one MAC clause nobody has read.") reads as reportage, not as a feature ad.
- **resend.com** — Confident first-person plural without arrogance ("We send email."). Short declarative sentences. *Use here →* hero sub-line ("We report the worst case, not the best.") — PLAN §2.1 tagline candidate already in this register.
- **trigger.dev** — Honest technical voice; documentation-quality prose on the marketing page. *Use here →* §2.2 #7 "show the math" expand panel — the technical-judge layer of the honest-numbers section.

### Reject because

- **"Trusted by [logos] we don't have"** (universal SaaS default): PLAN §2.3 hard ban — implying customers you don't have is a lie a GC catches in five seconds.
- **The marketing-bro ban list** (PLAN §2.3): *revolutionize / unleash / supercharge / leverage / robust / seamless* (general) + *AI-powered / trusted by / next-generation / enterprise-grade / purpose-built / human-in-the-loop / co-pilot / transform your practice / white-glove* (legal-tech specific). Reproduced here so the Copy Lead has them in front of them while writing.
- **Console.log easter eggs** ("hi judge 👋"): PLAN §2.3 + §7.3 — juvenile for a serious legal tool; replaced with build-SHA + model-pin + eval-link as engineering-discipline signal.

---

## §1.5 — Agent-topology-as-art sub-hunt

Per PLAN §1.5. This is *not* a hero candidate (PLAN §1.4 recommends candidate #2 contract-stack instead) — these references inform the **§2.2 #4 "How it works"** section.

### What we're stealing

- **trigger.dev** — DAG visualization with subtle node-active pulse + animated edge-stroke between connected nodes. The closest competitor analog to our Parser → Classifier → CrossRef → RiskJudge → Router → Reporter topology. *Use here →* per-node hover reveals the agent's real prompt (PLAN §2.2 #4 "Hover a node, see what it does + its real prompt").
  - *gesture-spec:* see §Motion trigger.dev row above (same spec applies — pulse 600ms ease-in-out / edge-stroke dashoffset 0 → -240 / 1800ms / single-trigger at scroll-progress 0.15).
- **Inngest** — Pipeline visualization with clear retry/branch semantics shown as compositional shape, not as labels. *Use here →* the Reflector loop (PLAN §2.2 #8) — show the gate that blocks regression as a visual *element*, not as a tooltip.
  - *gesture-spec:* gate visualization: open-state = `stroke-dasharray` continuous, closed-state = dashed gap rendered as a 2px×24px `<rect>` blocking the path; transition 200ms `ease-out`. The Reflector loop arrow-head plays a **single** 360° rotation over 1800ms `ease-in-out` on scroll-into-view (single-trigger at scroll-progress 0.15), then holds static. **No infinite loop** — PLAN §4.3 orchestration rule (hover/loop must not compete with user scroll); FA Round-2 finding corrected.
- **Modal — https://modal.com** — Dev-infra clarity in their function-graph visualizations. *Use here →* sanity-check our pipeline diagram against the cleanest infra-tool reference for legibility-without-decoration.
  - *gesture-spec:* node sizing — 12px node radius, 1.5px stroke, no fill on inactive nodes (only stroke); active state = filled with `--brand-primary` at 8% opacity backdrop. **[verify exact px values via Playwright]**
- **Temporal / Dagster** — Step-execution traces shown as a vertical timeline with span widths proportional to duration. *Use here →* PLAN §6.4 moneymoment trace-card — the spans have *widths*, not just labels. (Phoenix's own trace UI uses this; copy the legibility, not the chrome.)
  - *gesture-spec:* span row height 32px desktop / 24px mobile, horizontal gap 4px between spans. Span width = `(duration_ms / total_ms) * track_width`, with a 24px-min so sub-50ms spans remain clickable. Active-span highlight: `box-shadow: 0 2px 8px rgba(184, 111, 61, 0.18)` (`--accent-clay` at 18%), lift translateY 0 → -8px on click per PLAN §6.4 named gesture.
- **ReactFlow / Cytoscape gallery** — Reference implementations of node-edge graphs in React; pattern library, not destination. *Use here →* **patterns to study, NOT runtime dependency.** Our pipeline has 6 fixed nodes + 1 loop = ~7 SVG elements hand-positioned; importing ReactFlow (~80KB gz) for a 7-element static graph violates PLAN §6.2 budget for zero gain. **Implementation = raw SVG + Framer Motion for the per-node entry stagger** (FA Round-2 finding corrected — keeps the "pick two of {Framer, GSAP, raw-SVG}" budget intact).
  - *implementation-note:* hand-positioned `<g>` nodes inside a parent `<svg viewBox="0 0 800 320">`, dots-background as a separate `<pattern>` element (`<pattern id="dots" patternUnits="userSpaceOnUse" width="20" height="20"><circle cx="1" cy="1" r="1" fill="var(--neutral-600)" /></pattern>` — gives the cursor.com-style texture at zero JS cost).
- **SVG-path-stroke-dashoffset trick / animated beams** (Magic UI primitive) — Flow lines between nodes that animate as data "moves." *Use here →* edge animation on the pipeline diagram, scoped to scroll-into-view single-trigger (PLAN §4.3 orchestration rules).
  - *gesture-spec:* `<path d="M[node1] C[control1] [control2] [node2]" stroke="url(#beam-gradient)" stroke-width="1.5" stroke-dasharray="240 240" stroke-dashoffset="240" />` animated to `stroke-dashoffset="0"` over 1800ms `ease-out`. Gradient stop: `0% transparent → 30% --brand-primary → 70% --brand-primary → 100% transparent` — creates the moving-pulse illusion without a JS animation loop.

### Reject because

- **3D rotating DAG** (Inngest's older marketing site briefly tried this): looks like every DAG tool ever; PLAN §1.4 candidate #1 ("agent pipeline in 3D") was explicitly rejected on this basis. Even with document-shaped nodes, it lands as "another DAG."
- **The "glowing dots" agent-network visualization** (every AI-multi-agent vendor): maps to PLAN §1.3 "AI = neurons" anti-reference. Reject on sight.
- **D3 force-directed graph that auto-arranges**: looks impressive; reads as "we don't know what shape our system is." Our pipeline has a *fixed* shape; show that shape.

---

## §Direct-competitor reality check

PLAN §1.2 calls out one site as the "look intentional next to it" reference. This is its own row because the comparison is load-bearing.

- **phoenix.arize.com** — Direct competitor surface, also the observability layer we *integrate with*. We must look (a) intentional next to it, (b) not like a worse version of it, (c) not so different that we look like we don't understand the lane. *Use here →* the Phoenix logo appears on our page in the §2.2 #10 "Built on / Where it lives" section as **"open-source observability"** (PLAN §2.2 #10 — defends against a GC reading it as a startup-dependency risk). Our trace-card visualization in §6.4 deliberately echoes Phoenix's span legibility while sitting in our own type and color system.

---

## §Asset-capture convention (when Playwright MCP lands)

Per PLAN §1.4 and the Round-A Art Director ask. If the user approves the Playwright MCP install (TOOLING.md §2.4), the Art Director runs the capture pass with this convention:

- **Directory**: `design/screenshots/<category>/` — one of `typography/`, `color/`, `motion/`, `composition/`, `voice/`. (Directories seeded today; `.gitkeep` placeholder in each.)
- **Filename**: `<site-slug>-<descriptor>.png` — e.g. `mercury-hero.png`, `stripe-press-book-page.png`, `linear-cmdk.png`. Lowercase, hyphen-separated, no spaces.
- **Embed**: under the matching entry in this file, as `![mercury hero](screenshots/typography/mercury-hero.png)` with a one-line caption that *re-states* what we're stealing, so the screenshot is captioned with intent, not with description.
- **Capture targets**: 2–5 per site (hero / scroll-mid / micro-interaction / type detail / dark-light parity if relevant). ~30 sites total (16 hand-picked §1.2 + ~14 from the §1.1 funnel + Awwwards/SiteInspire mining) → ~80-120 captures. Manual capture is feasible but slow; Playwright cuts it ~10×.

The mining pass is the Art Director's **Day-2 morning** action. This document is the runway; the screenshots fill in the existing structure rather than replace it.

---

## §The five weird lifts *(added Round-2 — AD Round-1 central-tension finding)*

The Round-1 AD review correctly flagged that the v2 doc was **tasteful + safe** — it canonized the same eight reference sites every serious-money startup cites, without naming a single *weird* lift, which is the §0.1 failure mode. One weird lift per category, named here so the §0.1 tension is *operational*, not declarative:

- **§Typography weird lift** → *Stripe Press abuses its serif at book-cover scale* — see https://press.stripe.com/poor-charlies-almanack and similar book detail pages. The display serif at 200px+ is **the weird move**: it stops being type and becomes texture. *Use here →* the §6.4 Wilson-LB recall number rendered at 240px desktop is *our* version of this. Without this lift, we render the number at a polite 96px and lose the screenshot frame's punch.
- **§Color weird lift** → *Anthropic's deliberate refusal of any blue* on a research-AI surface where every competitor (OpenAI, Mistral, DeepSeek, xAI) defaults to it. The absence is the statement. *Use here →* we refuse signal-blue entirely (PLAN §5.1 already commits to this; the weird-lift reframing is "the blue we don't use is part of the brand"). One sentence in §SYSTEM.md: *"`--brand-blue` is not defined."*
- **§Motion weird lift** → *Cursor.com's deliberate slowness on the trace block* — agent steps reveal at a pace slower than the user expects, forcing them to *read*. The non-snappy timing is the weird move; it signals confidence. *Use here →* the §6.4 unfurl runs at 1800ms total per span (not the 400ms the §4.3 micro-default would suggest), pacing the juror's attention to the moneymoment.
- **§Composition weird lift** → *Browser Company Act II memo's full-bleed paragraph blocks at body-text size* — single-column, no max-width cap, paragraph text spanning 100% of viewport width. Every typography textbook forbids this; the memo does it deliberately for the editorial-essay register. *Use here →* the §2.2 #11 GC-FAQ answers — render the longest answer in a full-bleed single column (max-width capped only on >1440px desktop to stay under 75ch). Reads as memo, not as marketing FAQ.
- **§Voice weird lift** → *trigger.dev's homepage having a debugging anecdote in the hero copy* — they tell a *story* about catching a bug, not a feature list. The willingness to be specific about a real failure is the weird move. *Use here →* the §2.2 #3 problem vignette ("Exhibit 2.1 hit Friday 6pm. Three associates, two paralegals, one MAC clause nobody has read.") is *our* version. Copy Lead pushes this further: name a *specific* clause type a real GC has actually been burned by, not a generic MAC-clause reference.

If a Phase-5 token decision or Phase-2 copy line doesn't include at least one weird lift per category surface it appears on, the AD section-completion review rejects it. The §0.1 tension is now testable, not aspirational.

---

## §Anti-references (reproduced from PLAN §1.3 inline so they're in front of the AD during mining)

Reject the **cliché**, not the underlying technique:

- Off-the-shelf Spline blob hero with no semantic tie.
- Purple-to-pink "AI" gradient.
- Glowing-dot 3D brain / "AI = neurons" visual metaphor.
- Powered-by-GPT-X badges.
- Stock-illustration crowds of diverse abstract people pointing at laptops.
- Carousel heroes that hide the message.
- Word-by-word fade-in-with-blur headlines (4-second readability tax).
- Fake testimonial cards with no-name "Partner, AmLaw 50" attributions.

Plus the tooling-layer rejections from TOOLING.md §7 (Vercel/Next templates wholesale, AI copy generators for `COPY.md`, stock icon packs as primary iconography, marketplace Lottie packs, shadcn Blocks wholesale, "Made with AI" badges).

If a reference site uses any of these and you feel the pull, write a one-line *why it works there but not here* note rather than re-using it.

---

## §Hand-off to Phase 2 (Copy Lead) and Phase 5 (Design System)

- **Copy Lead** picks up the §Voice section directly as input to `COPY.md`. The Mercury / Stripe Press / anthropic.com voice anchors collapse the "find the register" search.
- **Art Director (Phase 5)** carries the §Typography / §Color / §Motion observations directly into `SYSTEM.md` and `tokens.ts` — the Lane-A serif candidate (Fraunces under Option B per TOOLING.md §6), the deep-forest-emerald + warm-clay palette, the locked one-easing/three-durations motion grammar.
- **Frontend Architect** uses §Motion as the source for the Framer / GSAP / Rive split decisions in `STACK.md` (Day-2 EOD).
- **Component Builders** (Phase 6) consult §Composition for section anatomy decisions inside the locked token system.

This document is the *what to steal* registry. It does not re-litigate the *whether to steal* decisions made in PLAN §1.4 — those are closed (candidate #2 contract-stack as primary hero, candidate #5 editorial typographic as Day-4 fallback; signal-green demoted to 5% state; warm clay as desaturated terracotta).
