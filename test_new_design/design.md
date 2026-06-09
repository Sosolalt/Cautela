# DESIGN.md — M&A Gatekeeper Hero, Creative Liberation Pass

> **For**: Claude Design (Opus 4.7), via claude.ai web.
> **Output**: 2–3 standalone HTML files (`hero-a.html`, `hero-b.html`, `hero-c.html`) saved to this directory. One full-viewport hero per file. Dark surface, no nav, no footer, no other sections. Each variant must be a **defensibly different aesthetic register** — not three color swaps of the same composition.
> **Read this entire document end-to-end before composing.** It is the only authoritative source for this generation. There is no other brief, no other tokens file, no other spec to consult.

---

## 0. Why this brief exists (read this first or you will default to safe)

The instruction is not "make a nice landing page." A *competent* B2B SaaS hero — dark surface, muted brand color, a warm secondary accent, an editorial serif at ~96px, Inter for body, mono for code, a left-aligned copy block with an illustration on the right, two CTAs in a horizontal row — is the safe centroid every model converges on when asked to design "a serious B2B landing page." It pattern-matches. It is also generic. **It is the negative example for this brief.**

If your draft converges on any of: left-copy with right-illustration / two-CTAs-in-a-row / centered hierarchy / soft-radius card frames / muted "tasteful" neutrals / a polite 24px-inset frame — you have failed the brief before saving the file. The whole point of this pass is to refuse those defaults.

Your target is the population of websites that show up on Awwwards' Site Of The Day, Httpster, Godly, Minimalgallery — pages where the *composition itself* is the design choice, where a juror's eye is forced into a path the designer authored, where typography is allowed to be enormous or microscopic without apology, where one color carries the entire emotional load, where the layout breaks a grid intentionally because the grid had nothing more to say.

A useful reference for the energy: **aircenter.space** — note how it commits to one aesthetic register and lets typography, negative space, and a single chromatic move do everything. Note that it would feel *wrong* if it were "more balanced." Carry that conviction.

You are designing for a Devpost juror who has seen 200 hackathon submissions this week, every single one of which uses a purple-to-pink gradient and a centered headline above a CTA. You have five seconds to make them stop scrolling. Compose accordingly.

---

## 1. The aesthetic register — DOCUMENTARY BRUTALISM

Commit to one register and own it. The locked register for this pass is **Documentary Brutalism** — a hybrid that treats the landing page as if it were *itself* a piece of legal evidence. Not a marketing page *about* contracts: a page that *behaves like a contract*.

The visual language draws from three lineages, in this order of priority:

1. **The court-filing aesthetic** — line numbers down the left edge, document IDs in the corner, an effective date stamp, footnote markers (`¹` `²` `³`) attached to specific words in the headline, a vertical rule that runs the full height of the viewport. Page elements are *positioned* the way legal documents are positioned: nothing centered, everything aligned to a structural rail.
2. **Editorial brutalism / Swiss-press maximalism** — typography that is allowed to be enormous (200px+ if it earns it). Words that *bleed off* the viewport edge intentionally. Hanging punctuation. A type system where the contrast between display and supporting text is at least 8× (not the polite 2×–3× Stripe-Press contrast).
3. **Terminal / telemetry surfaces** — the Phoenix span ID is not decoration; it is *evidence*. It deserves architectural placement, not "small mono label near the illustration." Consider letting a span ID run as a column of monospace text down a margin, as a footer band across the viewport, or as the literal anchor the headline is annotated *back to*.

If you find yourself reaching for "modern minimal" or "clean dashboard SaaS" — you are in the wrong register. Stop, re-read this section, restart.

### 1.1 What this register *forbids*

These are not preferences. These are scope kills.

- **No centered hero composition.** Center alignment is the default of every generated landing page; this composition refuses it. Use left-edge, right-edge, baseline-aligned-to-rail, asymmetric — anything but center.
- **No two-CTAs-in-a-row block at the bottom of a copy stack.** If you ship CTAs as a horizontal row of buttons below a paragraph, you have produced the same hero as 100,000 other sites. Find a different placement: inline within a sentence, anchored to a line number, as a footer ribbon, as a single dominant action with the secondary as a small underlined text link elsewhere.
- **No card or framed container around the hero composition.** Negative space is the frame. The dark surface *is* the canvas. Borders, soft-radius wrappers, drop shadows, gradient halos — all banned.
- **No "illustration on the side."** If a visual artifact appears, it must be *load-bearing* — load-bearing typography, document-mark, or the §4.7 dimensional element treated as architecture (a 3D contract page that *is* the composition, not a polite right-side companion). No stylized stack-as-decoration.
- **No soft radius anywhere.** `border-radius: 0` globally. The only curved geometry permitted is a hand-drawn-feeling stroke (e.g., an SVG circle that looks marked, not generated). Pills, rounded buttons, capsule chips — all banned.
- **No shadow stack.** Flat. If depth is needed, achieve it with overlap, scale, or a single hairline rule. Soft drop shadows are the AI-slop tell.
- **No glassmorphism, no mesh gradient, no aurora, no noise-overlay-as-texture-shortcut.** These are pattern-matched defaults; using them is failure.
- **No "AI-powered" badge, no "Now with Claude" stamp, no "Try Free" pill, no logo strip.** This product does not market its model and has no trust-by logos.

### 1.2 What this register *requires*

- **One single accent color does all chromatic work.** Choose one (see §4.2). Use it for at most three discrete elements in the viewport. Anywhere else, the page is monochrome on the dark surface.
- **Typography contrast ≥ 8×.** If your supporting text is 16px, your display can be 128px or 200px — not 32px. The hierarchy must read instantly even at 10% zoom.
- **At least one element bleeds, overflows, or anchors to an edge.** A word that runs past the right edge. A line number column flush to the left viewport edge. A footer rule that touches both sides. Refuse the "10% inset frame" instinct.
- **The Phoenix span ID earns architectural placement.** Not a 14px label tucked under an illustration. Make it count.
- **A footnote / annotation mark appears on the headline.** At least one word in the hero tagline carries a `¹` `²` `³` superscript, and the footnote it references appears somewhere on the same viewport — at the bottom, in a margin, anywhere it reads as a document mark.

---

## 2. The product, in one paragraph (do not redesign around this — design *through* it)

M&A Gatekeeper is a multi-agent system that reviews merger agreements — 312-page legal documents that hit a partner's desk on Friday evening with a Monday-morning board call deadline. Six agents read the contract, flag risky clauses, and trace every verdict back to the underlying telemetry span in Arize Phoenix. The wedge: *every flag is sourced to the clause it came from; every verdict links to its Phoenix trace.* The audience is an M&A General Counsel (skeptical, deposition-aware) and a Devpost juror (5-second first read). The submission is a hackathon entry; the page is demo-only — no signup, no pricing, no testimonials.

The *attitude* the page must project: this tool was built by people who have read merger agreements. It is precise the way contract drafting is precise. It is unimpressed with itself. It refuses to use a single piece of generic SaaS-marketing vocabulary because the audience would see through it instantly.

---

## 3. Locked copy — render verbatim, no paraphrase

These strings are signed off. Do not rewrite, retitle, "improve cadence," shorten, or split. Render exactly:

### 3.1 Hero tagline

> Every flag, sourced. Every verdict, traced. Every span, clickable.

- The three beats are period-separated fragments. They are load-bearing as a *cadence*; do not change punctuation.
- At least one beat should carry a footnote marker (`¹` etc.) — your choice which one, and what the footnote says (see §3.5).

### 3.2 Anchor sub-line

> M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.

- The em-dash (`—`, U+2014) is load-bearing. Not a hyphen. Not `--`.

### 3.3 Conservative-stats line

> Wilson lower bounds. Frozen held-out fold. Paired-bootstrap CI gates. We report the worst case, not the best.

- Render this somewhere on the viewport. It does not need to sit immediately below the sub-line; you may treat it as a footnote, a margin annotation, or a footer band. *Place it where it tells the truth that the headline is being honest about.*

### 3.4 The CTAs

- **Primary**: `Try the demo →` (arrow is `→`, U+2192, not `->`)
- **Secondary**: `Watch the 60-second demo`

You may not omit either. You may radically re-place them. The horizontal-row-of-buttons composition is forbidden (§1.1). Acceptable placements: inline within a footnote sentence (e.g., the footnote *is* the CTA); anchored to a line number; as a single dominant action with the secondary as small underlined inline text; as a footer ribbon spanning the viewport with the secondary as a margin note.

### 3.5 The Phoenix span ID — the craft signal

> `phoenix:span:7f3a-c2b1-9d04-…`

- JetBrains Mono OR whatever monospace you choose (see §4.3), with `font-feature-settings: "liga" 0, "calt" 0` so the `--` does not fuse into an em-dash glyph. **Test this in your output by inspecting the rendered glyph.**
- Minimum 14px. May go larger if your composition treats the ID as architecture (see §1).

### 3.6 Footnote(s)

You will invent one or two short footnote strings to anchor the superscript marker(s) on the headline. Suggested content (pick one, or write your own in the same register):

- `¹ Verdicts traced via Arize Phoenix. Span IDs link to live telemetry.`
- `¹ Six agents. Parser, Classifier, Cross-Ref, Risk Judge, Router, Reporter.`
- `² Held out from the calibration fold. We do not test on training data.`

The footnote text is *part of the design*. Treat it as type.

---

## 4. Tokens — prescriptive on what must be precise, liberated on aesthetic choice

### 4.1 Surface

```
--surface: #0B0B0C   /* near-black, very slightly warm. NOT #000000 — pure black reads as cheap. */
```

Optional alternate surface if your variant is doing something architecturally different:

```
--surface-alt: #F4F2EC  /* warm paper — only if you are committing to the "page is a court filing" register on a light field. ONE variant maximum may use this; the other two must be on --surface dark. */
```

### 4.2 Pick ONE accent — and commit, once, per viewport

Warm clay (`#B86F3D`) and any similar muted-tasteful-orange tone is **forbidden**. Choose ONE of the following, and use it for **at most three discrete elements** in the viewport:

```
--accent-vermillion:  #E63D2F   /* high-saturation legal-red; the "stamp on the document" energy */
--accent-highlighter: #F0E040   /* chemical yellow; the "marker on the risky clause" energy */
--accent-ochre:       #C28A2C   /* deep ochre / aged document gold; the "archival" energy */
--accent-cyan-ink:    #2BD4D9   /* terminal cyan; the "this is telemetry" energy — use with surface only, never on alt */
```

Each variant should pick a *different* one if you are doing all three variants. Do not blend two accents in a single viewport. Do not desaturate the chosen accent to be polite — render it at full saturation.

### 4.3 Typography — escape the default trinity

The pattern-matched default for "serious B2B" is Fraunces or similar / Inter / JetBrains Mono. Refuse that stack. The constraints:

- **Display** must be one of these three families (all on Google Fonts, no auth needed):
  - **PP Editorial New** — if available; if not, fall back to **Instrument Serif** or **Tenor Sans**
  - **Redaction** (the Forest Stearns / Titus Kaphar typeface) — bonus aesthetic match for the "legal evidence" register
  - **GT Sectra** alternative: **Newsreader** (Google Fonts) at weights 200 and 800 paired (extreme weight contrast)
  - Acceptable substitution: **Fraunces** *only* if used at weight 900 + opsz 144 at 200px+ (re-purposed at a scale that earns it)
- **Body / UI** must NOT be Inter, NOT be Roboto, NOT be Arial, NOT be system-ui. Choose one of:
  - **PP Neue Montreal** (or **Space Grotesk** as Google-Fonts substitute)
  - **GT America** (or **Geist** as Google-Fonts substitute)
  - **Söhne** (or **Inter Tight** as Google-Fonts substitute — yes Inter Tight is allowed; the plain Inter is not, because it pattern-matches to generic SaaS)
- **Mono** must NOT be JetBrains Mono. Choose one of:
  - **Berkeley Mono** (commercial; OK to fall back to)
  - **JetBrains Mono** *only if* used at an unusual weight (300 or 800) so it reads differently than the default
  - **Geist Mono** (Google Fonts)
  - **IBM Plex Mono** (Google Fonts)

Pick one stack per variant. Each variant should use a *different* display family from the others.

### 4.4 Scale

- Display can go up to **216px** if your composition earns it. The minimum display size for the hero tagline is **88px** desktop; below that, you have under-committed.
- Body sits at 16px–18px.
- Mono sits at 14px–16px for the span ID *or* may be re-scaled up to 24px–32px if you are treating it as architecture (§1).
- Contrast between display and body must be ≥ 5.5× (so 88px display ↔ 16px body is the floor; 144px display ↔ 18px body is honest).

### 4.5 Spacing

8px baseline grid. No half-grid offsets. Margins from the viewport edge can be flush (0px) or generous (96px+); the polite 24px inset is the safe-default — try to avoid it.

### 4.6 Motion (optional in the static HTML)

If you include CSS transitions:
- One easing only: `cubic-bezier(0.16, 1, 0.3, 1)`.
- Two durations only: `200ms` (hover) and `800ms` (entry, if any).
- `transition-all` is banned. Specify properties.
- Forbidden: word-by-word fade-in-with-blur on the headline. Forbidden: typewriter effect on the span ID. Forbidden: floating particles or parallax noise.
- Optional and *encouraged*: a subtle text-shift on hover of the footnote-marked word (e.g., the underline thickens, the superscript briefly rotates a degree). One small interaction is more memorable than ten generic ones.

### 4.7 The dimensional layer — required, not optional

A flat HTML/CSS hero will not produce a site-of-the-day-grade result. The compositions that show up on Awwwards and Godly almost universally carry a **dimensional element** — a WebGL canvas, a Three.js scene, an SVG with depth, a CSS-3D-transform stack. This is the move that separates "an editorial landing page" from "a piece of design engineering."

**Each variant MUST include exactly one dimensional element.** Not three. Not zero. One — placed where it does the most work for that variant's compositional move. Render budget: must hold 60fps on a 2020 MacBook Air. No more than ~6KB of Three.js scene code (CDN-imported library doesn't count against this); no more than ~200 vertices total. Anything bigger and you have made an installation, not a hero.

The dimensional element must be **load-bearing to the concept**, not decoration:
- It is not "a floating cube in the background."
- It is not "particles drifting across the screen."
- It is not "a generated mesh-gradient mesh."
- It IS the contract page itself, or the headline word, or the span-ID column, or the line-numbered rail — rendered as the dimensional artifact.

Pick ONE of these techniques per variant:

**(i) Three.js minimal scene (via CDN, `three@0.160` or current).** A single object — typically a `PlaneGeometry` textured with a contract-page motif, or extruded text geometry of one headline word, or a thin-rectangle stack approximating the document pile. Lit with one directional light + ambient. Rotates slowly on Y-axis (full revolution ≥ 30s), OR responds to mouse position with subtle lerped tilt (max ±8°). Material: `MeshBasicMaterial` with the accent color, OR `MeshStandardMaterial` with low metalness / high roughness. No PBR textures, no environment maps, no postprocessing. The whole scene fits in ~150 lines of inline JS.

**(ii) CSS 3D transforms — "fake 3D from 2D".** No `<canvas>`, no WebGL. Pure `transform: perspective(1200px) rotateX(...) rotateY(...)` stacks. Best fit: an isometric or perspective-tilted contract-page stack made of 3–4 absolutely-positioned divs, each with its own transform and a small Y-offset, producing a parallax pile. Mouse-move on the parent updates the `--mouse-x` / `--mouse-y` CSS variables that the children read for a subtle parallax. Cheaper, more reliable, more compositional control. The "2D rendered as 3D" register from the aircenter.space reference.

**(iii) Shader-driven `<canvas>` — fragment-shader background.** A single `<canvas>` covers the viewport (or one quadrant of it). A fragment shader writes one of: a slow-drifting noise field tinted in the accent color (the "telemetry surface" register); a scan-line pattern that subtly drifts (the "redaction camera" register); a halftone of a single contract page that materializes and dematerializes over a 20s cycle. Shader is ≤ 60 lines of GLSL. No three.js for this option — a raw `WebGL2RenderingContext` with one program. Use `gl-matrix` only if absolutely needed (usually not).

**(iv) SVG-with-depth (the lowest-risk option).** A single inline `<svg>` that uses overlapping shapes, careful opacity grading, and one subtle `<animate>` or CSS `@keyframes` rotation to *imply* depth without actual WebGL or CSS 3D. The depth lives in the composition — a stack of rectangles slightly offset, a fold-shadow rendered as a darker triangle, a page-curl rendered as a Bézier. Mouse parallax via JS that updates SVG `transform` attributes.

### 4.8 Mapping technique to variant (the recommendation, not a lock)

- **Variant A (type as architecture)**: technique (i) Three.js — extruded `TextGeometry` of one headline word, rendered as a 3D object that the rest of the headline is in conversation with. OR technique (ii) — the headline word given perspective tilt via CSS 3D.
- **Variant B (court filing)**: technique (ii) CSS 3D — an isometric stack of 3–4 contract-page divs, mouse-parallax. The "page itself as a 3D object" register. The line-numbered rail wraps around the stack on one edge.
- **Variant C (terminal evidence)**: technique (iii) shader-canvas — a fragment-shader scan-line or noise field tinted in the accent, with the span-ID architecture composed *over* it. The shader IS the telemetry surface.

You may swap the technique→variant mapping if your composition has a better idea — but **every variant ships with one dimensional element**, no exceptions. A flat HTML hero is the safe default this brief refuses.

### 4.9 Dimensional layer — what is forbidden

- **No floating particle systems.** Banned regardless of technique. The particle-cloud-on-dark-bg is the AI-startup tell.
- **No mesh gradient meshes.** No `<canvas>` rendering a smooth color-blob mesh gradient. That's the marketing-LLM tell.
- **No "purple sphere floating in space."** No abstract geometric primitives floating with no compositional purpose.
- **No glassmorphism / frosted glass.** Banned in §1.1; reiterated here for the 3D pass.
- **No post-processing bloom, lens flare, chromatic aberration, film grain, or god-rays.** The aesthetic is documentary, not cinematic-marketing.
- **No 3D logos, no 3D buttons, no 3D icons.** Don't extrude the wordmark. Don't extrude the arrow on the CTA. Dimensional moves are reserved for the load-bearing object (the page, the headline word, the surface).
- **No autoplay video, no `<video>` background, no Lottie, no Rive.** Same energy ban — the moves that feel like a startup splash page.
- **Honor `prefers-reduced-motion: reduce`.** Wrap any animation loop in `@media (prefers-reduced-motion: no-preference)`. The static composition must still read as composed without motion.

---

## 5. The non-negotiable rules (these always apply, every variant)

1. **No blue anywhere.** Not link blue, not steel blue, not indigo, not navy. The product's category default is blue (Kira, Litera, Harvey, ContractPodAI all use it). Refusing blue is a brand-level statement. If your `<a>` tags would default to system blue, override them explicitly.
2. **No purple-pink AI gradient.** Specifically: `from-purple-500 to-pink-500` and any visual cousin. This is the marketing-LLM tell.
3. **No Inter, no Roboto, no Arial, no system-ui** for body text. See §4.3.
4. **No `border-radius` above 0.** Square corners only.
5. **No soft drop shadows.** Flat composition.
6. **No card or framed container around the hero.** Negative space frames it.
7. **No centered hero stack.** Composition is asymmetric or rail-aligned.
8. **No two-buttons-in-a-row CTA block.** Re-place the CTAs (§3.4).
9. **Mono ligatures OFF.** `font-feature-settings: "liga" 0, "calt" 0` on every mono element. The Phoenix span ID's `--` must render as two literal hyphens, not an em-dash.
10. **Render the locked copy verbatim** (§3). One footnote marker on the headline minimum.
11. **One accent color per variant**, used in at most three places per viewport.
12. **The page is dark-default** on `--surface`, with one *optional* variant allowed on `--surface-alt`.
13. **No wordmark, no nav, no footer-with-links** inside the hero composition. The hero owns 100vh; nothing else exists on the page.
14. **No raster image.** No PNG/JPG/WEBP. SVG, CSS, `<canvas>` (WebGL / shader), and Three.js (via CDN) are all permitted and *one dimensional element is required per variant* — see §4.7.
15. **No social-proof / trusted-by / testimonial / press-mentions** — explicitly killed by the product's scope.

---

## 6. The composition is open — here is what you decide

Within the constraints above, **the composition is yours**. You are not being given a layout to fill in. Explicitly refused: left-copy with right-illustration, vertical hierarchy with a CTA row at the bottom, and any other composition that reads as the SaaS-landing-page default. Decide:

- **Where the hero tagline lives.** Top? Center-right with hanging punctuation? Diagonal? Anchored to a line-numbered rail down the left edge? Broken across the viewport with one beat per zone?
- **What carries the visual weight.** Pure typography (V-A) versus typography-plus-document-architecture (V-B) versus an unexpected third move (V-C — surprise me).
- **Where the Phoenix span ID is placed.** Margin column? Footer band? Underneath one word of the headline as a citation? Replacing the conventional "headline + sub-line" relationship entirely?
- **Where the CTAs land.** §3.4 forbids the row-of-buttons composition; that leaves you many options. Make a choice that *reads as designed*, not as a default.
- **How (and whether) the document/contract idea appears visually.** It does not need to. The headline + sub-line + span ID + footnotes may carry the entire composition. If a visual document artifact appears, it must read as a *real document mark* (line numbers, redaction blocks, stamp, signature rule, page number) — not as a stylized stack illustration.
- **How the footnote(s) are placed.** A traditional footer row? Inline marginalia in a column? A diagonal annotation with a hand-drawn arrow? A single line at the absolute bottom-left, set in 12px mono?

---

## 7. Three variants — each commits to one move

Produce three variants. Each must be a real, defensible direction, not a color swap.

### Variant A — "Type as architecture"

Pure typography carries the composition. No document mark, no illustration. The hero tagline is rendered at maximum scale your viewport math allows (160–216px on desktop). Hierarchy is achieved entirely through type weight, scale, and edge alignment. The Phoenix span ID may sit as a column of mono text down the left or right margin. The footnote(s) anchor to specific words in the headline and resolve in a footer band or marginalia. One accent color, three placements maximum.

**Pick**: PP Editorial New / Instrument Serif (display), accent: vermillion or highlighter.

### Variant B — "The page is a court filing"

Treat the hero as if it were a literal piece of legal evidence. Line numbers down the left edge (visible, set in 11px mono, neutral grey, every line numbered 1–24 or however many lines the composition produces). A document ID in the top-right corner (e.g., `EX-2.1 / 2026-05-27 / 1 of 312`). A vertical hairline rule down the left at ~64px from the edge (the "court margin"). The headline lives in the body column, anchored to the rail. The Phoenix span ID is treated as the document's tracking number — bottom-left, set in mono, carrying the document-ID gravity. **This is the variant that may use `--surface-alt` (warm paper) if you want to commit to it fully; otherwise dark.**

**Pick**: Newsreader 200/800 or Redaction (display), accent: ochre or vermillion.

### Variant C — "Terminal evidence"

The Phoenix span ID is treated as architecture, not annotation. It runs as a large mono band — either across the top, across the bottom, or as a vertical column — at 24–48px scale. The headline sits in relationship *to* the span ID, not above it. The dark surface dominates; the accent is a single high-saturation point. The whole composition reads as if you opened a terminal and the contract review was happening live. No skeuomorphism — no fake terminal window chrome — just the spirit of a telemetry surface composed at design-grade.

**Pick**: GT Sectra alt / Newsreader 800 + Geist Mono, accent: cyan-ink or highlighter.

---

## 8. Mobile — 375px viewport must also work

For each desktop variant, include a `@media (max-width: 768px)` block in the same file that reflows the composition. Rules:

- Display drops to 56–72px (whatever preserves your hierarchy ratio).
- Edge bleeds and rail alignments stay; what was a vertical margin column on desktop may become a stacked footer band on mobile.
- The CTAs stay re-placed (§3.4) — do not "fix" them back into a button row on mobile.
- Horizontal padding: 20px (`spacing.5` minus a touch).

Mobile reads as a deliberate mobile composition, not a desktop crammed into 375px.

---

## 9. Output format

Save three files in this directory:

```
test_new_design/
  design.md                ← this file (do not modify)
  hero-a.html              ← Variant A (type as architecture)
  hero-b.html              ← Variant B (court filing)
  hero-c.html              ← Variant C (terminal evidence)
  notes.md                 ← optional: 3–5 lines per variant explaining your choices
```

Each HTML file:
- Complete standalone document.
- `<head>` includes `<link>` to Google Fonts for the chosen stack.
- `<style>` block declares the tokens as CSS custom properties on `:root`, sets `font-feature-settings: "liga" 0, "calt" 0` on the mono stack, sets `border-radius: 0` globally on `*`, sets `body { background: var(--surface); color: var(--text); margin: 0; }`.
- Semantic HTML: `<header>` or `<section>` for the hero, `<h1>` for the tagline, `<p>` for sub-lines, `<a>` or `<button>` for CTAs.
- One HTML comment at the top declaring the variant's intent in a single sentence, e.g. `<!-- Variant B: court-filing register. Line-numbered left rail, document ID top-right, span ID as document tracking number bottom-left. Accent: ochre on the footnote marker only. -->`

---

## 10. Success — how to know you got it right

A variant ships if **all** of these are true:

1. A Devpost juror scrolling past would *stop* on it. The composition is unusual enough that "scroll past" is not automatic.
2. The locked copy (§3) is rendered verbatim, with at least one footnote marker on the headline.
3. The Phoenix span ID appears, renders with literal `-` not `—`, and is placed *architecturally* (not as a forgotten small label).
4. One accent color appears in at most three places. No second accent.
5. No blue, no purple-pink gradient, no Inter, no Roboto, no system-ui, no soft radius, no drop shadow, no card frame, no centered hero stack, no row-of-buttons CTA block.
6. Exactly one §4.7 dimensional element is present, load-bearing, and runs at 60fps in Chrome on a 2020 MacBook Air.
7. The composition reads as *one register, fully committed* — not a compromise between two safer ones.
8. The three variants are meaningfully different (different accent, different type stack, different compositional move, different §4.7 dimensional technique). Not three palette swaps of the same layout.
9. The mobile composition reads as deliberately designed for 375px, not as a desktop layout shrunk.

A variant fails if it violates any §5 non-negotiable rule, any §3 copy-verbatim rule, or — most importantly — if it reads as a safe generic-SaaS hero (the kind §0 names as the negative example).

---

## 11. One final instruction — think before you compose

Before writing any HTML: spend a moment composing in your head. Where does the headline live? What is the first thing the eye lands on? Where does it go second? What is the single accent doing in that path? Is the composition asymmetric in a way that *feels intentional*, or is it asymmetric because you couldn't decide?

If a sentence of internal reasoning would read as "I'll center this and add a button row below" — discard that draft. The default is the enemy. The brief is the constraint *against* the default.

Compose. Save three files. Make the juror stop scrolling.

**End of brief.**
