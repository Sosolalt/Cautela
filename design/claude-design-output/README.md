# M&A Gatekeeper — Design System

> Documentary Brutalism. Legal evidence as landing page. Telemetry as architecture.

---

## What this is

This design system documents the visual + content language for **M&A Gatekeeper** — a multi-agent system that reviews merger agreements (312-page legal documents that land on a partner's desk Friday evening with a Monday-morning board call). Six agents read the contract, flag risky clauses, and trace every verdict back to the underlying telemetry span in **Arize Phoenix**. Every flag is sourced to the clause it came from; every verdict links to its Phoenix trace.

The product is a hackathon submission (Devpost). The audience is two-headed:
1. An **M&A General Counsel** — skeptical, deposition-aware, has read merger agreements her whole career.
2. A **Devpost juror** — has seen 200 submissions this week, every one of which uses a purple-pink gradient and a centered headline.

The brand exists to **refuse both default audiences' defaults**. It is not "modern minimal SaaS." It is not "AI-startup splash." It is a piece of design engineering that behaves like a piece of legal evidence.

---

## Source materials

- **`source/design.md`** — the canonical brief for the hero variants, authored as the original creative direction. Every rule in this system comes from there. **Treat that file as the source of truth; this README is the indexed/explained version.**
- The codebase given was a single design brief (`test_new_design/design.md`). There is no product code, Figma file, or running app to import — the brand is established by this brief and its locked tokens.

---

## Index

| File | Purpose |
|---|---|
| `README.md` | This file. Start here. |
| `SKILL.md` | Agent-skill front-matter — load this design system as a skill in Claude Code. |
| `colors_and_type.css` | CSS custom properties for color, type, scale, spacing. Drop into any page. |
| `source/design.md` | Original creative brief. Authoritative. |
| `fonts/` | Font references (Google Fonts links — see notes). |
| `assets/` | Logos, marks, illustrations. |
| `preview/` | Card files that populate the Design System tab. |
| `ui_kits/marketing/` | UI kit for the hackathon marketing site (the three hero variants + shared primitives). |

---

## Content fundamentals

The voice exists to project one attitude: **this tool was built by people who have read merger agreements**. It is precise the way contract drafting is precise. It is unimpressed with itself. It will not use a single piece of generic SaaS-marketing vocabulary because the audience would see through it instantly.

### Tone

- **Forensic, not friendly.** No exclamation marks. No "we're so excited to announce." No "✨ AI-powered."
- **Concrete, not aspirational.** "Cluster-bootstrap 95% lower bound — contracts as the IID unit. Wilson 95% LB as an exploratory per-finding-IID cross-check. Frozen held-out fold." not "industry-leading accuracy."
- **First-person plural, sparingly.** "We report the worst case, not the best." Used to signal a stance, not to be chummy.
- **Second person is for the auditor**, not the user. "Every flag, sourced. Every verdict, traced." The reader is being shown evidence, not addressed as a friend.

### Casing

- **Sentence case** for headlines and UI labels. Not Title Case. Not ALL CAPS (with one exception: §A document IDs and tracking labels, which carry small-caps legal-form gravity).
- **Lowercase mono** for telemetry identifiers (`phoenix:span:7f3a-c2b1-…`).
- **No marketing capitalization** of common nouns. "merger agreements," not "Merger Agreements."

### Punctuation

- **Em-dashes (`—`, U+2014)** are load-bearing. Not hyphens, not `--`. They mark the kind of legal-prose tightening that defines this brand's voice.
- **Period-separated fragments** carry cadence: *Every flag, sourced. Every verdict, traced. Every span, clickable.*
- **Footnote markers** (`¹` `²` `³`) anchored to specific headline words. These are document marks, not decoration.
- **No emoji.** Never. Not even ✓. Not even →.
  - **Exception:** the `→` arrow is permitted *inside CTA labels* (`Try the demo →`), as type, not iconography. Use U+2192, not `->`.

### Vocabulary — say / don't say

| Say | Don't say |
|---|---|
| flag, verdict, source, trace, span, clause | insight, recommendation, finding, takeaway |
| six agents | "AI assistant," "copilot," "agent swarm" |
| frozen held-out fold | "validated on our test set" |
| cluster-bootstrap 95% LB (Wilson as exploratory cross-check) | "high accuracy" |
| 312 pages, Monday morning | "save time," "be productive" |
| Phoenix trace, span ID | "audit log," "explainability" |
| sourced, traced, clickable | "transparent," "explainable" |

### Example copy (verbatim — sign-off locked, do not paraphrase)

> **Hero tagline:** Every flag, sourced. Every verdict, traced. Every span, clickable.
>
> **Anchor sub-line:** M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.
>
> **Conservative stats line:** Cluster-bootstrap 95% lower bound — contracts as the IID unit. Wilson 95% LB retained as an exploratory per-finding-IID cross-check. Frozen held-out fold. We report the worst case, not the best.
>
> **Primary CTA:** `Try the demo →`
> **Secondary CTA:** `Watch the 60-second demo`

### Footnote register

Footnotes are *part of the design* — treat them as type. Sample footnote bodies (any of these, or write in the same register):

- `¹ Verdicts traced via Arize Phoenix. Span IDs link to live telemetry.`
- `¹ Six agents. Parser, Classifier, Cross-Ref, Risk Judge, Router, Reporter.`
- `² Held out from the calibration fold. We do not test on training data.`

---

## Visual foundations

The locked aesthetic register is **Documentary Brutalism** — the landing page behaves like a piece of legal evidence, not a marketing page about it.

### The three lineages (priority order)

1. **Court-filing aesthetic.** Line numbers down the left edge. Document IDs in the corner (`EX-2.1 / 2026-05-27 / 1 of 312`). Effective-date stamps. Footnote markers on specific headline words. A vertical rule at the court margin. Nothing is centered; everything aligns to a structural rail.
2. **Editorial brutalism / Swiss-press maximalism.** Typography allowed to be enormous (200px+ when earned). Words bleeding off the viewport edge intentionally. Hanging punctuation. Display↔body weight contrast at least **8×** — not the polite 2–3× Stripe-Press contrast.
3. **Terminal / telemetry surfaces.** The Phoenix span ID is *evidence*, not a label. It gets architectural placement — a column down a margin, a footer band, the anchor the headline cites *back to*.

### Color — one accent does all chromatic work

The page is monochrome on a near-black surface, with **one** accent appearing in **at most three discrete places** per viewport. Picking a second accent is a brand-level violation.

```
--surface:        #0B0B0C   /* near-black, slightly warm. NEVER #000000 */
--surface-alt:    #F4F2EC   /* warm paper. One variant maximum may use this. */
--ink:            #ECECEA   /* high-contrast text on dark surface */
--ink-muted:      #8A8A86   /* secondary text, line numbers */
--ink-faint:      #54534F   /* rules, borders, document chrome */
```

The four locked accents (pick **one** per surface):

```
--accent-vermillion:  #E63D2F   /* legal-red — "stamp on the document" */
--accent-highlighter: #F0E040   /* chemical yellow — "marker on the clause" */
--accent-ochre:       #C28A2C   /* archival gold — "aged document" */
--accent-cyan-ink:    #2BD4D9   /* terminal cyan — "this is telemetry" — dark surface only */
```

**Forbidden colors.** Blue (any temperature — link blue, steel blue, indigo, navy). Purple-pink AI gradient. Warm-clay orange (`#B86F3D` and its cousins). Desaturated "tasteful" accents — when an accent appears, it runs at full saturation or not at all.

### Typography — escape the default trinity

The default for "serious B2B" is Fraunces / Inter / JetBrains Mono. **This brand refuses that stack.**

| Role | Allowed families |
|---|---|
| Display | **PP Editorial New** → fallback **Instrument Serif** · **Newsreader** (200 + 800 paired) · **Redaction** · Fraunces *only* at weight 900 + opsz 144 at 200px+ |
| Body / UI | **PP Neue Montreal** → fallback **Space Grotesk** · **Geist** · **Inter Tight** (plain Inter is forbidden) |
| Mono | **Berkeley Mono** · **Geist Mono** · **IBM Plex Mono** · JetBrains Mono *only* at weight 300 or 800 |

**Mono ligatures are off, globally.** `font-feature-settings: "liga" 0, "calt" 0` on every mono element. The Phoenix span ID's `--` must render as two literal hyphens, not an em-dash.

**Scale.**
- Display floor: **88px** desktop. Ceiling: **216px**. Anything below 88px and you have under-committed.
- Body: 16–18px.
- Mono: 14–16px for inline IDs; 24–32px when treated as architecture (margin column, footer band).
- Display↔body contrast ≥ **5.5×** (so 88/16 is the floor; 144/18 is honest).

### Spacing

- **8px baseline grid.** No half-grid offsets.
- Viewport-edge margins are either **flush (0px)** or **generous (96px+)**. The polite 24px inset is the safe default — avoid it.
- Mobile horizontal padding: 20px (5 × 4).

### Radii

- **`border-radius: 0` globally.** Square corners only. Pills, capsule chips, rounded buttons — all banned.
- The only curved geometry permitted is a **hand-drawn-feeling** stroke (SVG circle that looks marked, not generated).

### Shadows

- **None.** Flat composition. Depth is achieved through **overlap, scale, or a single hairline rule** — never with `box-shadow`.

### Backgrounds, gradients, textures

- **No mesh gradients, no aurora, no glassmorphism, no noise-overlay-as-texture-shortcut.** These are pattern-matched defaults.
- **No raster image.** SVG, CSS, `<canvas>` (WebGL / shader), and Three.js are the only permitted visual primitives.
- The dark surface *is* the canvas. Negative space frames the composition; no card/container does.

### Hover & press states

- **Hover** on type marks: the **underline thickens** OR the **superscript rotates a degree**. Never a color shift, never an opacity fade, never a scale-up.
- **Hover** on the primary CTA: the arrow `→` translates 4–8px right with `200ms cubic-bezier(0.16, 1, 0.3, 1)`. The text does not move.
- **Press**: a hairline appears beneath the element (the "selected" mark). No shrink, no shadow press.

### Motion

- **One easing only:** `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Two durations:** `200ms` (hover/interaction), `800ms` (entry).
- `transition: all` is banned — specify properties.
- **Forbidden:** word-by-word headline fade-in-with-blur, typewriter on the span ID, floating particles, parallax noise, autoplay video, Lottie, Rive, post-processing bloom.
- **`prefers-reduced-motion: reduce` must be honored.** The static composition reads as composed without motion.

### The dimensional layer (required, one per surface)

Every hero composition ships with **exactly one** dimensional element. It is **load-bearing to the concept**, not decoration. Pick one of four techniques per variant:

1. **Three.js minimal scene** — single object, ~150 lines of inline JS, ≤6KB scene code, ≤200 vertices. `MeshBasicMaterial` in accent color OR `MeshStandardMaterial` with low metalness / high roughness. No PBR, no env maps, no postprocessing.
2. **CSS 3D transforms** — `perspective(1200px) rotateX/Y`. Best fit: an isometric 3–4-layer contract-page stack with mouse-parallax via CSS custom properties.
3. **Shader-driven `<canvas>`** — single fragment shader ≤60 lines of GLSL. Use cases: drifting noise field tinted in accent, scan-line, halftone of a single contract page materializing over a 20s cycle.
4. **SVG-with-depth** — overlapping shapes + careful opacity grading + one subtle `@keyframes` or `<animate>`. Mouse parallax updates SVG `transform` attributes.

**Forbidden dimensional moves.** Particle systems. Mesh-gradient meshes. Floating geometric primitives without compositional purpose. 3D logos / buttons / icons. Glassmorphism. Bloom, lens flare, chromatic aberration, film grain, god rays.

### Composition rules (the non-negotiables)

1. **No centered hero stack.** Asymmetric or rail-aligned only.
2. **No two-buttons-in-a-row CTA block.** Re-place the CTAs — inline in a footnote sentence, anchored to a line number, footer ribbon, single dominant action.
3. **No card or framed container around the hero.** Negative space is the frame.
4. **No nav, no footer, no wordmark inside the hero.** The hero owns 100vh.
5. **No social proof, trusted-by, testimonials, press mentions.**
6. **At least one element bleeds, overflows, or anchors to an edge.**
7. **The Phoenix span ID gets architectural placement** — never a 14px label tucked under an illustration.
8. **At least one footnote marker appears on the headline**, and its footnote resolves on the same viewport.

---

## Iconography

This brand has **no icon system** in the conventional sense. Iconography is what other brands use to dress up empty space; Documentary Brutalism uses type, line numbers, and document chrome instead.

What is permitted:

- **The `→` arrow** (U+2192) inside CTA labels. As type, not as an icon — it inherits the type color and weight.
- **Document marks rendered in CSS/SVG**: line-number columns, vertical court-margin rules, document-ID tracking numbers, footnote superscripts, redaction blocks, page-number bottom-right marks.
- **Footnote markers** `¹` `²` `³` `*` `†` — Unicode, set in the body font, anchored to specific words.

What is forbidden:

- **No emoji.** Never.
- **No icon font / Lucide / Heroicons / Feather** in hero or marketing surfaces. (A future product UI may justify a system, in which case the closest match would be **Geist Icons** at 1.5px stroke — but this hasn't shipped yet; flag any introduction.)
- **No 3D extruded icons, no 3D logo, no skeuomorphic glyphs.**
- **No "stylized illustration"** — illustration-as-decoration is forbidden. If a visual artifact appears, it is *load-bearing* (a contract page rendered as architecture, a span-ID column as evidence) — never decoration.

> **Substitution flag — fonts.** The brief calls for PP Editorial New, PP Neue Montreal, Berkeley Mono — all commercial. This system uses their Google Fonts substitutes (**Instrument Serif / Newsreader**, **Space Grotesk / Inter Tight**, **Geist Mono / IBM Plex Mono**) which are documented in `colors_and_type.css`. If the commercial families become licensed, swap the `--font-display`, `--font-body`, `--font-mono` custom properties and the page picks them up. **Ask the user for licensed font files to upgrade fidelity.**

---

## Caveats & open questions

- **No product UI exists yet.** The brief specifies the *marketing* surface only — the hero. The product (the actual agent dashboard, contract reader, Phoenix trace viewer) has no design context. The UI kit in this system covers the marketing-site hero variants; a product UI kit would need a separate brief.
- **Commercial fonts substituted with Google Fonts.** See substitution flag above.
- **No logo / wordmark.** The brief explicitly forbids a wordmark inside the hero. There is no canonical logotype on file. A wordmark, if commissioned, should be set in the chosen display family at full caps or sentence case, no symbol mark.
- **No imagery, no photography, no illustration.** Intentional — see Visual Foundations. Backgrounds carry no raster assets.

---

## Quick start

```html
<link rel="stylesheet" href="colors_and_type.css">
<style>
  body { background: var(--surface); color: var(--ink); margin: 0; }
  * { border-radius: 0; }
  .mono { font-feature-settings: "liga" 0, "calt" 0; }
</style>
```

Then read `source/design.md` end-to-end before composing anything for the brand. There is no shortcut.
