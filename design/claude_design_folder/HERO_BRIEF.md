# Hero Brief — M&A Gatekeeper Landing Page

> **Audience for this brief**: Claude Design (Anthropic Labs, Opus 4.7).
> **Generated for**: Hugo / `devpost/arize_project` / M&A Gatekeeper.
> **Date**: 2026-05-27 (Day 4 of 18; Devpost deadline 2026-06-11).
> **Output expected**: 2-3 static HTML hero variants saved to this directory as `hero-v1.html`, `hero-v2.html`, `hero-v3.html`.
> **Read this brief end-to-end before composing.** It is the only authoritative source for the variants; reading the codebase fills in the design-system details.

---

## 1. What you're being asked to do (the headline)

Generate **2-3 standalone HTML hero variants** for the M&A Gatekeeper landing page hero section. The hero is the above-the-fold composition the Devpost juror sees in the first 5 seconds. Each variant is a single HTML file that renders the hero at full-viewport scale, using the locked design tokens and locked copy verbatim.

**You are NOT generating the production code.** The production stack is Next.js 14.2.5 + Framer Motion + GSAP (locked in `design/STACK.md`). The HTML you output is a **visual specification** that downstream Component Builders will translate into the production stack. Your job is to settle the composition / proportions / hierarchy / accent placement so the Builders implement against a converged target.

**Success = the hero variants make it easy for a human to pick one and move on to building.** Each variant should be a distinct, defensible direction — not a near-identical color swap. Aim for three real options that materially differ in proportion or emphasis (see §7).

---

## 2. Project context (one paragraph — enough to compose)

M&A Gatekeeper is a multi-agent AI system that reviews M&A merger agreements (the 312-page Exhibit 2.1 documents that hit a partner's desk on Friday evening with a Monday-morning board call deadline). Six agents — Parser, Classifier, Cross-Ref, Risk Judge, Router, Reporter — read the contract, flag risky clauses, and trace every verdict back to its underlying Phoenix span (Arize Phoenix is the observability backend). The product's wedge: **every flag is sourced to the clause it came from; every verdict links to its Phoenix trace**. The audience for the landing page is the M&A General Counsel (sophisticated, skeptical, deposition-aware) AND the Devpost juror (5-second first read, technical and design judges). Submission: Google Cloud Rapid Agent Hackathon — Arize partner track.

**Tone**: enterprise legal-tech CONTENT with playful color-forward motion-rich VIBE. The central tension (PLAN §0): *does this make a serious tool feel inevitable and fun, or does it make a serious tool feel unserious?* Playful lives in micro-interactions, hover states, accent placement. Serious owns macro grid, typography, color system, numbers, honesty block. If a composition reads as both, pick one and commit.

---

## 3. Hard constraints — DO NOT violate any of these

These are locked decisions logged in `PROJECT_LOG.md` per PLAN §3.3 hard-to-reverse-decision protocol. Violating them invalidates the variant. If a constraint forces an aesthetic compromise, **honor the constraint and document the compromise in a code comment** at the top of the HTML file — do not silently work around.

### 3.1 Color — the brand-vs-interactive split (Supervisor-signed 2026-05-27)

- **`--brand-primary: #0F4A38`** (deep forest emerald) is **DECORATIVE ONLY**. It carries the brand identity at decorative tier (logo wash, OG card brand surface, ONE brand-surface moment per section). It **MUST NEVER** appear as body text, link color, focus ring, or text-on-dark interactive surface. It fails WCAG 4.5:1 (1.89:1 on `--neutral-900`); using it for text is the contrast lie this constraint defends against. **Maximum ~5% of viewport.**
- **`--text-interactive: #4A9D7E`** (brighter accessible green, ≥4.5:1 verified) carries **every** text/focus/link/button-outline surface that previously leaned on brand. Use this for the Phoenix span ID overlay color if it sits on dark.
- **`--accent-clay: #B86F3D`** (desaturated warm clay) is **the single accent**. **Used once per visible viewport, no exceptions.** Primary CTA background, the `BLOCK` verdict badge — never both in the same viewport. Above the fold, the accent lands on the primary CTA only (the `BLOCK` badge lives in the moneymoment section, far below the fold).
- **Risk-lane colors** (`--lane-clear`, `--lane-escalate`, `--lane-block`) are STATE-ONLY and scoped to ≤5% canvas. **Do not put any lane color above the fold** — they belong to the §6.4 moneymoment section, not the hero.
- **`--brand-blue` is DELIBERATELY NOT DEFINED**. Every M&A-adjacent enterprise tool (Kira, Litera, Harvey, ContractPodAI, iManage) defaults to a steel-blue or indigo primary; we refuse it entirely. The hero must not contain any blue. The absence is the statement.
- **Forbidden palettes**: purple-pink AI gradient (`from-purple-500 to-pink-500`), generic mesh-gradient-generator outputs, Substack-orange accent drift, GitHub-Actions signal-green primary. **None of these survive.**

### 3.2 Typography — Lane A locked, Option B foundries

- **Display**: Fraunces Variable, weight 600, optical-size axis enabled (`opsz` 80 for hero tagline, `opsz` 90 for wordmark, `opsz` 96 for the moneymoment number).
- **Body**: Inter Variable, weights 400 (body) / 500 (UI chrome) / 600 (button labels).
- **Mono**: JetBrains Mono Variable, ligatures OFF globally (`font-feature-settings: "liga" 0, "calt" 0`). Critical reason: if ligatures stay on, `phoenix:span:7f3a--c2b1` renders as `phoenix:span:7f3a—c2b1` (em-dash glyph fusion on `--`), and the juror reads "typographic flourish" instead of "real span ID."
- **Span-ID mandate**: any string matching `/[a-f0-9]{4}-[a-f0-9]{4}/` MUST render in `.font-mono`. The hero overlay span ID is the canonical case.

### 3.3 Theme — dark default, not light

The design system is **dark-default** per PLAN §5.1 ("Background: dark mode default … Light mode is parity, not afterthought"). The hero renders on `--neutral-900` (`#0B1311`) with `--neutral-50` (`#F4F6F3`) as the default body text. **Do not generate a light-mode hero variant.** All three variants ship on the dark surface. Light-mode parity is a Phase-6 polish concern, not your concern here.

### 3.4 Motion language — three durations, one easing

If your variants include any animation hints (CSS transitions on hover states, etc.), they MUST use only:
- **Easing**: one. `cubic-bezier(0.16, 1, 0.3, 1)` (≈ `easeOutExpo`).
- **Durations**: three. `150ms` (hover/focus/tooltip), `400ms` (section reveal/card lift), `800ms` (hero entry, full-viewport composition).
- **Stagger**: one. `60ms` between siblings.
- **Hero idle loop** (if any): `translateY ±4px over 4200ms ease-in-out`, infinite. ≤5% canvas movement. Never compete with scroll.

Forbidden: word-by-word fade-in-with-blur headlines (the AI-startup tell), carousel transitions, scroll-jacked mobile hero (mobile gets triggered Framer reveals only — see §8 mobile constraint), `transition-all` (specify the property).

### 3.5 Composition — negative space is the design

The §6.4 moneymoment is the page's most-screenshot-worthy frame; it lives in negative space with **no card, no border, no shadow** (PLAN §0.1 weird-but-tasteful rule). The hero inherits this discipline — **do not wrap the hero composition in a card, do not add a border around the contract stack, do not drop-shadow the typography**. The hero composition lives in negative space against `--neutral-900`. Single accent (warm clay on the primary CTA) is the only color "moment."

---

## 4. The locked copy — render verbatim, do not rewrite

Copy is locked in `design/COPY.md` v3.1 §2 (Hero) and §17 (open placeholders). Render the text as below; do not paraphrase, retitle, or "improve" the copy. The cadence-led tagline and the editorial sub-line are both load-bearing, both signed off, both preserved verbatim.

### 4.1 Hero tagline (display serif, 96px desktop / 56px mobile, single line on desktop, 1-2 lines mobile)

> **Every flag, sourced. Every verdict, traced. Every span, clickable.**

Cadence: three-beat fragments, period-separated. Render as a single visual unit (one paragraph element), not three separate lines. Desktop: one line if your viewport math allows; if not, break after "traced." (never after a beat-internal comma).

### 4.2 Anchor sub-line (display serif, 40px desktop / 28px mobile, REGULAR weight — sits between hero tagline and the conservative-stats sub-line)

> M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.

Cadence: Stripe Press editorial prose — single editorial sentence with mid-em-dash. The em-dash is **load-bearing**: it's the editorial-prose tell. Render as an actual `—` (em-dash, U+2014), not a hyphen, not `--`.

### 4.3 Conservative-stats sub-line (neutral sans, 24px desktop / 18px mobile, mono numerals where present — color `--neutral-300`)

> Wilson lower bounds. Frozen held-out fold. Paired-bootstrap CI gates. We report the worst case, not the best.

Cadence: four-beat declarative fragments. Smaller scale than the anchor sub-line; secondary information layer.

### 4.4 Primary CTA

> Try the demo →

Warm-clay (`--accent-clay: #B86F3D`) filled button. Text color `--text-on-accent-clay: #0B1311` (dark glyph on filled clay, 4.82:1 verified). Arrow is `→` (U+2192, not `->`). 48px height, 24px horizontal padding, `--text-body` size, `--font-body` 600 weight.

### 4.5 Secondary CTA

> Watch the 60-second demo

Ghost button (transparent background, `--text-interactive` text, `--neutral-600` border on hover). Same height as primary; appears to the right of primary at desktop, below primary at mobile.

### 4.6 Hero visual overlay copy (the Phoenix span ID — the craft signal)

One Phoenix span ID in **JetBrains Mono Variable, 14px minimum, no tracking, color `--text-interactive`** or `--neutral-300` depending on background:

> `phoenix:span:7f3a-c2b1-9d04-…`

This is the craft signal per INSPIRATION §Typography: the juror sees "this is a real ID from a real telemetry backend," not "this is a marketing illustration." The 14px floor is the spec (12px is too small at 1440p video capture; smaller and the glyph fuses; the 12px mono token is for inline span IDs in body copy elsewhere). Position: overlaid on the contract stack illustration at a location where it visually attaches to one specific clause (the BLOCK-verdict clause).

### 4.7 What's NOT in the hero (do not add)

- No wordmark in the hero composition — the wordmark lives in §1 Nav (above the hero), not inside it.
- No nav itself — your hero is the section below the nav, not the full above-the-fold page. Assume a 64px-tall nav sits above your composition; design within the remaining viewport.
- No "trusted by" logo strip — explicitly killed by PLAN §1.3 anti-references.
- No badge banner ("AI-powered" / "now with Claude" / etc.) — explicitly killed.
- No social-proof testimonial — explicitly killed (no fake quotes; no real-customer quotes pre-launch).
- No "Get started free" / "Sign up" — there is no signup; the product is demo-only for hackathon scope.

---

## 5. The locked design system — summary (full spec lives in the codebase files)

For the hex codes, type scale, motion primitives, and composition rules in their canonical form, **read `design/tokens.ts` and `design/SYSTEM.md` in the codebase**. This brief summarizes the load-bearing values you need to compose the hero; the codebase files are the source of truth if anything contradicts.

### 5.1 Color tokens for the hero (subset)

```
--neutral-900: #0B1311  ← hero background (dark default)
--neutral-50:  #F4F6F3  ← default body text on dark
--neutral-300: #A8B8AE  ← secondary text (conservative-stats sub-line color)
--neutral-400: #7A8F83  ← mono span-ID color (alt to text-interactive)
--neutral-500: #8A9E94  ← tertiary chrome / attribution

--brand-primary:    #0F4A38  ← DECORATIVE ONLY (logo wash, ≤5% viewport)
--text-interactive: #4A9D7E  ← all interactive text/links/focus (4.51:1 verified)
--accent-clay:      #B86F3D  ← single accent — primary CTA only above the fold
--text-on-accent-clay: #0B1311  ← dark glyph on filled clay (4.82:1)

--focus-ring-color:  var(--text-interactive)  ← 2px solid outline on :focus-visible
--focus-ring-width:  2px
--focus-ring-offset: 2px
```

### 5.2 Type scale for the hero (subset)

```
--text-hero-tagline:  96px / 56px mobile, line-height 1.05, tracking -0.01em, Fraunces 600 opsz 80
                      ← hero tagline ("Every flag, sourced…")
--text-hero-sub:      56px / 36px mobile, line-height 1.1,  tracking -0.01em, Fraunces 600 opsz 56
                      ← used elsewhere (§3, §7); NOT used in the hero
--text-display-md:    32px / 24px mobile, line-height 1.15, tracking -0.005em, Fraunces 600 opsz 32
                      ← section openers (not used in the hero)
--text-body-lg:       24px / 18px mobile, line-height 1.5, Inter 400
                      ← conservative-stats sub-line
--text-body:          16px,             line-height 1.55, Inter 400
                      ← button labels, base body
--text-mono-overlay:  14px,             line-height 1.4, JetBrains Mono 400 no tracking
                      ← hero span-ID overlay (the craft signal)

Anchor sub-line spec (no named token — explicit values from COPY §2):
  40px / 28px mobile, line-height 1.1, tracking -0.01em, Fraunces 600 REGULAR WEIGHT
  ← Note: "regular weight" per COPY §2 means the 400 weight if Fraunces 600 is too heavy
    at this scale; pick whichever foundry weight makes the editorial sub-line read as
    sub-line not as a second headline. The hero tagline must remain the dominant beat.
```

### 5.3 Spacing scale (8px base)

```
spacing.1   = 4px    spacing.5  = 24px   spacing.12 = 96px
spacing.2   = 8px    spacing.6  = 32px   spacing.16 = 128px
spacing.3   = 12px   spacing.8  = 48px   spacing.20 = 192px
spacing.4   = 16px   spacing.10 = 64px   spacing.24 = 240px
```

Gap conventions you'll need:
- 24px (`spacing.5`) gap between tagline and anchor sub-line
- 16px (`spacing.4`) gap between anchor sub-line and conservative-stats sub-line
- 32px (`spacing.6`) gap between copy block and CTA row
- 16px (`spacing.4`) gap between primary CTA and secondary CTA (desktop)

### 5.4 Composition rules

- **No card, no border, no shadow** on the hero composition. Negative space against `--neutral-900`.
- **Single accent per viewport**: warm clay (`--accent-clay`) on the primary CTA. Nowhere else in the hero.
- **Left-edge alignment** is the §0.1 weird-but-tasteful rule — for the moneymoment number, the `0` digit anchors the left edge (not centered). For the hero, copy left-aligned is the default; the contract stack composition can be left-or-right depending on variant.
- **Container max-width**: `1440px` (the hero is the "wide" container). Horizontal padding 12% of viewport on desktop (PLAN §6.4 frame spec).
- **Above-fold height**: 100vh per the `sectionMinHeight.hero` token. The hero must compose within one viewport on desktop; mobile can spill slightly if the CTA stack pushes it.

### 5.5 Motion hints (optional — for the HTML preview only)

If you include CSS transitions or animations in the HTML:
- Hover states on the CTA buttons: 200ms background luminance shift, `--ease-primary`.
- Hero idle loop (if applied to the contract stack): `translateY ±4px over 4200ms ease-in-out infinite`.
- No scroll-triggered animations in the static HTML (those are Framer Motion / GSAP territory in production; the static HTML is a still composition).
- `prefers-reduced-motion: reduce` honored — wrap any idle loop in the `@media` block per SYSTEM §Motion language §5.

---

## 6. The locked hero direction — candidate #2 (contract-stack)

`design/STACK.md` v2 §Hero candidate lock locks the hero to **candidate #2: contract-stack via Framer-orchestrated SVG**. Composition:

- **3–4 layered contract pages**, the top page partially fanned to reveal the page beneath. The stack reads as "the partner's actual reading pile" — Exhibit 2.1 + exhibits + indentures by reference.
- **Selective highlights on the top page**: 2-3 representative clauses subtly highlighted to indicate the agents have read them.
  - One clause gets the **BLOCK verdict badge** treatment in the production version (warm-clay pill, 48px height, 14px mono uppercase tracked +0.08em label `BLOCK`).
  - BUT — per §3.1 single-accent rule — **only one accent moment per viewport**. The hero's accent moment is the primary CTA, not the contract stack. So in the hero static composition, the BLOCK badge on the clause is rendered in a MUTED form (e.g., a thin warm-clay underline, or a small `--text-interactive` dot, or a numeric annotation `[1]` in mono). The full warm-clay BLOCK pill ships in the §6.4 moneymoment section below the fold, not here.
- **Phoenix span ID overlay** (14px mono, `--text-interactive` color) attaches to the BLOCK-verdict clause on the top page. This is the craft signal — the juror's eye lands on `phoenix:span:7f3a-c2b1-…` and registers "real telemetry."
- **The stack does not animate in the static HTML** — for the Component Builders, the stack will be Framer-orchestrated with a hero idle loop and per-clause hover reveals. In your static HTML, hint at the idle with a subtle vertical offset, but the composition is a still.
- **No 3D, no R3F, no Lottie, no Rive**: the stack is SVG-suggestive in your HTML (CSS-transformed page elements, or actual `<svg>` with hand-positioned page rectangles). Bundle math is locked at ~5KB markup + ~35KB Framer; do not introduce dependencies your HTML implies the production build can't ship.
- **Hover affordance (CSS only in the preview)**: hovering a highlighted clause lifts it ~8px and reveals the Phoenix span ID inline. This is the moneymoment foreshadowing — what happens here in hover-affordance form happens in the §6.4 section as the moneymoment proper.

**Day-5 fallback**: if Day-4 mobile measurement shows the SVG-orchestrated stack blowing the LCP/jank budget on iOS Safari, the production hero falls back to candidate #5 (editorial typographic, no SVG illustration). This fallback is NOT your concern; you generate variants of candidate #2. The Component Builders handle the fallback at build time.

---

## 7. The three variants — each must be a distinct direction

Generate three variants that materially differ in proportion or emphasis. Color/type/copy stay locked across all three; what changes is the spatial composition and what carries the visual weight.

### Variant 1 — Baseline (the locked direction, safe centre)

The most direct expression of STACK §Hero candidate lock. Copy left-aligned (taking roughly 55-60% of the horizontal viewport), contract stack right-aligned (40-45%). Stack is a moderate fan (3 pages visible, top page tilted ~4° clockwise from base). 2 clauses highlighted on the top page; the BLOCK-verdict clause has the Phoenix span ID overlay attached via a thin connecting line. Primary CTA + secondary CTA on a horizontal row below the copy block. Hierarchy:

1. Hero tagline (96px)
2. Anchor sub-line (40px) — 24px gap below tagline
3. Conservative-stats sub-line (24px) — 16px gap below anchor
4. CTA row (48px height) — 32px gap below stats

The variant the Component Builders will pick if no one objects. **This is the "did we get it right?" baseline.**

### Variant 2 — Editorial typographic dominance

Typography carries 80% of the visual weight; the contract stack shrinks to a small attestation in a corner (~20% of viewport area). Copy can extend further left and breathe. The hero tagline gets MORE vertical real estate — perhaps the cadence-led three beats render with deliberate line breaks ("Every flag, sourced." / "Every verdict, traced." / "Every span, clickable." each on its own line in display serif). The Phoenix span ID overlay attaches to a tiny stack icon, not to a full illustrated stack. CTA row stays the same.

This variant tests: **does the copy alone carry the hero?** It's the closest static-HTML approximation to the candidate #5 perf-recovery fallback (editorial typographic). If the team likes V2 better than V1, that's signal that the contract-stack illustration is doing less work than locked-in, and the Day-5 fallback to candidate #5 becomes a positive choice not a perf-recovery retreat.

### Variant 3 — Stack-forward dramatic

The contract stack dominates the viewport (60-65% of horizontal area), copy compressed to the left rail (~35-40%). Stack has more drama: 4 pages visible, deeper fan (top page tilted ~8°), one clause clearly visible mid-page with the muted BLOCK indicator, the Phoenix span ID overlay larger (16px instead of 14px) and more visually prominent. The conservative-stats sub-line may move below the CTA row to give the copy block tighter top-to-bottom rhythm. The stack itself suggests depth — slight Y-axis perspective on the lower pages, opacity grade from top (100%) to bottom (~85%) as the pages recede.

This variant tests: **does the visual carry the hero, or does it become noisy?** It's the highest-craft, highest-risk variant — if the stack reads as impressive and inevitable, V3 wins. If it reads as overwrought or distracts from the copy, V1 wins by elimination.

---

## 8. Mobile constraint — 375px viewport must work

PLAN §6.1 Day-4 mobile gate: the hero on a 375px viewport must feel right. This is the gate that fires today (2026-05-27) if the scroll-jacked hero doesn't work on mobile.

For each variant, **also render the 375px-viewport composition** — either as a separate HTML file (`hero-v1-mobile.html`) or as a `@media (max-width: 768px)` block inside the desktop file. Mobile rules:

- Hero tagline drops to 56px (the `--text-hero-tagline` mobile value).
- Anchor sub-line drops to 28px.
- Conservative-stats sub-line drops to 18px.
- Contract stack: shrinks to ~80% horizontal width, sits ABOVE the copy block (vertical stack), not beside it. Or for V2/V3 dramatic, the stack can drop to a thin attestation strip beneath the CTAs.
- CTA row: primary stacks on top of secondary (vertical), not side-by-side.
- **No scroll-jacking on mobile** — the hero scrolls naturally. If the production version has any scroll-pinned hero behavior, mobile gets the fallback: triggered Framer reveals only.
- Horizontal padding: 24px (`spacing.5`) instead of 12% of viewport. Mobile prefers fixed padding over percent.

The mobile gate is **PASS** if a juror scrolling on an iPhone at the Devpost judging URL feels the same "this is composed, this is alive" impression as desktop. The gate is **FAIL** if mobile reads as a desktop layout crammed into 375px.

---

## 9. What NOT to do — explicit forbidden list

Even when the variant direction tempts you toward one of these, refuse:

1. **No purple-pink AI gradient** — the marketing-bro tell. Banned at the token layer.
2. **No system blue anywhere** — the `--brand-blue` weird-lift is the absence of blue. Do not let `<a>` fall back to system blue (the `globals.css` rule prevents this in production; in your HTML, set `<a>` color explicitly).
3. **No wordmark or nav inside the hero composition** — those live above the hero.
4. **No "AI-powered" / "Now with Claude" badge** — the product does not market the model.
5. **No fake quotes / "trusted by" logo strip / social-proof** — the §6 honesty block does this work later; the hero stays clean.
6. **No carousel** — PLAN §1.3 anti-reference. No slide indicators, no `<` `>` arrows, no auto-rotation.
7. **No word-by-word fade-in with blur on the tagline** — the AI-startup tell. Tagline reads as a single composed beat.
8. **No `transition-all`** — specify the property (`transition-opacity`, `transition-transform`).
9. **No mono ligatures** — set `font-feature-settings: "liga" 0, "calt" 0` on every mono element. Otherwise the Phoenix span ID em-dash fuses.
10. **No `--brand-primary` (#0F4A38) for text or focus surfaces** — the contrast lie this constraint defends against. If you find yourself reaching for deep emerald on text, use `--text-interactive` (#4A9D7E) instead.
11. **No second accent in the viewport** — single-accent rule. Warm clay on the CTA, and only there in the hero.
12. **No `.stat-card` class / box / preset** — the hero composes in negative space. SYSTEM.md §Component primitives §Card `naked` variant is the only sanctioned "card" for hero-tier composition (no border, no background, no shadow).
13. **No raster image for the contract stack** — the production version is SVG. Your HTML can use CSS-positioned `<div>`s with `border` + `background` to approximate, or actual inline `<svg>`. No PNG/JPG.
14. **No invented copy** — render §4 verbatim. If you find yourself rewriting "Every flag, sourced" into "Source every flag" or "Every flag is sourced", stop. The cadence-led form is signed off.
15. **No light-mode variant** — dark-default only (§3.3).
16. **No new tokens** — if you need a color/spacing/type value not in §5, the constraint failed and the design system needs a new token decision (escalate, don't invent).

---

## 10. Output format — what to save where

Save each variant as a complete, standalone HTML file in this directory:

```
design/claude-design-output/
  HERO_BRIEF.md             ← this file (do not modify)
  hero-v1.html              ← Variant 1 (baseline)
  hero-v2.html              ← Variant 2 (editorial typographic)
  hero-v3.html              ← Variant 3 (stack-forward dramatic)
  hero-v1-mobile.html       ← Variant 1 at 375px (or include @media in v1.html)
  hero-v2-mobile.html       ← Variant 2 at 375px (or include @media in v2.html)
  hero-v3-mobile.html       ← Variant 3 at 375px (or include @media in v3.html)
  NOTES.md                  ← (optional) your notes on the variant trade-offs
```

Each HTML file is a complete document with:
- `<head>` containing the `<link>` to self-hosted fonts (Fraunces, Inter, JetBrains Mono) — use Google Fonts `<link>` for the preview (production uses `next/font`, but for the preview Google Fonts is fine).
- A `<style>` block with the locked color tokens declared as CSS custom properties on `:root`, with `font-feature-settings` set on the mono stack.
- The hero composition in semantic HTML (`<header>` or `<section>` for the hero, `<h1>` for the tagline, `<p>` for sub-lines, `<button>` for CTAs — accessibility-coherent markup, since Component Builders translate from your structure).
- A subtle inline note at the top of the file (HTML comment) explaining the variant's intent in one sentence (e.g., `<!-- Variant 1: baseline. Copy left, stack right, two highlighted clauses. -->`).

**Do not include**: the wordmark, the nav, any section below the hero (footer / how-it-works / etc.). Your output is the hero section alone, occupying one full viewport.

---

## 11. Success criteria — how to know a variant is good

A variant ships if:

1. **The 5-second juror stop**: a Devpost judge scanning fast knows in 5 seconds (a) what the product does, (b) what makes it credible (the Phoenix span ID overlay does this), (c) what action to take (the primary CTA).
2. **Contrast verification**: every text element passes WCAG 4.5:1 against its background. The locked tokens guarantee this if you use them correctly; the gate is "did you reach for `--brand-primary` for text by accident."
3. **Single-accent honored**: warm clay appears once and only once in each viewport (primary CTA only). No second accent.
4. **No banned palettes**: no blue anywhere, no purple-pink, no signal-green primary.
5. **Mono ligatures off**: the Phoenix span ID renders with literal `-` characters, not em-dashes. Test by viewing the HTML in Chrome and inspecting the span-ID glyph.
6. **The composition lives in negative space**: no card around the hero, no border around the stack, no drop-shadow on the typography. The macro discipline holds.
7. **Mobile composition reads as composed, not cramped**: the 375px variant feels like a deliberate mobile design, not a desktop layout shrunk.
8. **The variant is distinct from the other two**: if V2 and V3 are near-identical to V1 with minor tweaks, the variant exploration failed. Each variant must be defensible as a real direction.

A variant FAILS if it violates any §9 forbidden item, any §3 hard constraint, or any §4 copy verbatim rule. Document failures as comments at the top of the HTML; do not silently work around.

---

## 12. Files in this codebase you should consume

When pointing at the codebase, prioritize these in order. Tier 1 is mandatory; Tier 2 strongly recommended; Tier 3 helpful for context.

### Tier 1 — must read (the source of truth)

- **`design/tokens.ts`** — the canonical color, type, spacing, motion, focus, layout primitives. If a value in §5 of this brief contradicts `tokens.ts`, trust `tokens.ts`. This is the file the production build imports.
- **`design/SYSTEM.md`** — the design system spec. Sections to prioritize: §Color (especially "Architectural decision — brand vs. interactive color split"), §Typography (especially "Span-ID mono mandate" and the Type scale table), §Component primitives (Button + Card + Badge variants the hero uses), §Motion language §1-§5.
- **`design/COPY.md`** §0, §1, §2, §17, §18 — the locked hero copy verbatim and the cross-references that anchor it.

### Tier 2 — strongly recommended

- **`design/STACK.md`** §Hero candidate lock, §Motion library split, §Perf budgets, §Borrowed-patterns registry — explains why candidate #2 is the locked direction, what motion library will animate your composition in production, and what bundle math the Builders will hold to.
- **`design/PLAN.md`** §0 (central tension), §0.1 (weird-but-tasteful), §1.3 (anti-references), §1.4 (hero candidate lock), §5.1 (color thesis), §6.1 (kill-switches / Day-4 mobile gate) — the load-bearing thesis decisions all variants must honor.
- **`design/HANDOFF.md`** — the current-state snapshot. Phase status grid + hard-to-reverse decisions list. If anything seems contradictory, the HANDOFF tells you what shipped most recently.

### Tier 3 — helpful for context

- **`ma_gatekeeper/frontend/app/layout.tsx`** — shows how the dark-default applies at the React layout level (`bg-neutral-900 text-neutral-50`).
- **`ma_gatekeeper/frontend/app/globals.css`** — shows the `:root` CSS custom property declarations and the `:focus-visible` + `a { color }` rules. The production rules your HTML should mirror.
- **`ma_gatekeeper/frontend/tailwind.config.ts`** — shows how `tokens.ts` is wired into Tailwind. Your HTML doesn't need Tailwind, but understanding the wiring helps you know what classnames the Builders will use.

### Files to deliberately SKIP

- **`design/REVIEW_NOTES.md`** — audit-trail noise; doesn't affect the hero composition.
- **`design/TOOLING.md`** — internal process / tooling decisions; not visual.
- **`design/INSPIRATION.md`** — useful but verbose. If you read it, focus on §Five-weird-lifts and §Composition; skip the full reference site list. *Better: use Claude Design's web-capture tool on one or two of the cited reference sites if INSPIRATION names specific URLs you want to ground against.*
- **`design/tokens.test.ts`** — the test file that verifies `tokens.ts` invariants; not needed for composition. The rules are in SYSTEM.md.
- **`PROJECT_LOG.md`** — audit trail; reading the HANDOFF instead is more efficient.
- **`ma_gatekeeper/agent/*`**, **`ma_gatekeeper/tests/*`**, **`ma_gatekeeper/scripts/*`** — backend / eval / scripts; nothing visual.

---

## 13. Reference: where the variants you produce will go in the larger workflow

After you produce the three variants (and their mobile renderings):

1. The human (Hugo) opens each in a browser and picks one — V1 / V2 / V3 — or asks for one more iteration with a specific direction.
2. The picked variant is documented in `design/claude-design-output/hero-CHOSEN.md` — a one-page markdown explaining which variant was chosen and why.
3. The `design-team` Supervisor agent is invoked to dispatch Phase 6 — its Step-2 dispatch plan includes the picked Claude Design variant as a written-spec input to the Component Builders.
4. The Component Builders (via the `feature-build-loop` skill) translate the static HTML composition into the production stack: Next.js 14.2.5 + Framer Motion (for the contract-stack orchestration and per-clause hover reveals) + the locked tokens + the locked copy. Your HTML is the visual target; the production code is its translation, not a copy.
5. The Reviewer cohort (goal-alignment + code-quality + bug-hunter) grades the production implementation; the Art Director does section-completion review; the Supervisor closes Phase 6 §6.1 hero subsection at Step 3 reconciliation.

Your variants live or die by step 4's outcome: did the Component Builders produce a production hero that *feels* like the variant you composed? If yes, your spec was load-bearing. If the production hero drifts from your composition, the design-team will surface the drift at Step 3 reconciliation and either fix the production code or revise the spec.

**You are not asked to anticipate step 4.** Your job ends at step 1: three defensible static variants saved to disk.

---

## 14. One final note — the central tension

Per PLAN §0: the content is enterprise legal-tech; the vibe is playful, color-forward, motion-rich. Every choice answers: *does this make a serious tool feel inevitable and fun, or does it make a serious tool feel unserious?*

For the hero specifically, playful lives in:
- The single warm-clay accent on the CTA — the one moment of personality on the dark surface.
- The Phoenix span ID overlay — the craft signal that says "we trace this for real."
- The contract stack illustration's subtle hover affordance (in production: the per-clause lift; in your static HTML: the visual hint of it).

Serious owns:
- The macro grid and the negative-space discipline.
- The Fraunces display serif at 96px — editorial gravity, not blog-default.
- The cadence-led tagline — three-beat fragments, period-separated, no marketing softness.
- The conservative-stats sub-line — "We report the worst case, not the best" is the voice of a tool that has been deposed.

If a variant reads as both serious AND unserious in different places, pick one register for that variant and commit. Don't half-commit.

---

**End of brief. Save your variants. Pick three real directions. Compose.**
