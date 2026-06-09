# UI Kit — Marketing site

The hackathon submission has **one surface**: the marketing hero. The brief specifies three defensibly-different aesthetic variants (A, B, C). Each is a complete standalone hero in 100vh; nothing else exists on the page (no nav, no footer-with-links, no logo strip, no testimonials).

## Files

| File | Variant | Aesthetic register | Accent | Display | Dimensional technique |
|---|---|---|---|---|---|
| `hero-a.html` | A | Type as architecture | vermillion | Instrument Serif | SVG-with-depth (extruded glyph) |
| `hero-b.html` | B | Court filing | ochre | Newsreader 200/800 | CSS 3D (page stack) |
| `hero-c.html` | C | Terminal evidence | cyan-ink | Newsreader 800 + Geist Mono | Fragment shader (scan-line + noise) |
| `index.html` | — | Switcher | — | — | iframes the three variants |

## How they share

- All three load `../../colors_and_type.css` for tokens (no token duplication).
- All three render the **locked verbatim copy** from `source/design.md` §3:
  - Hero tagline: *Every flag, sourced. Every verdict, traced. Every span, clickable.*
  - Sub-line: *M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.*
  - Stats: *Cluster-bootstrap 95% lower bound — contracts as the IID unit. Wilson 95% LB retained as an exploratory per-finding-IID cross-check. Frozen held-out fold. We report the worst case, not the best.*
  - CTAs: `Try the demo →` (primary), `Watch the 60-second demo` (secondary)
  - Phoenix span: `phoenix:span:7f3a-c2b1-9d04-…`
- All three carry **one footnote marker** on the headline and resolve its body somewhere on the same viewport.
- All three honor `prefers-reduced-motion: reduce`.

## How they differ

Each variant *commits* to its register and refuses to hedge:

- **A — Type as architecture.** Pure typography. Headline at 216px ceiling, right-anchored, bleeds left. Span ID runs as a vertical mono column down the left margin. Footnote ¹ on "sourced," resolved as a footer band. SVG-with-depth glyph fills the top-right quadrant — six offset clipped layers tracking the cursor.
- **B — Court filing.** On warm paper (`--surface-alt: #F4F2EC`). Line numbers 01–28 down the left edge. Doc ID `EX-2.1 / 2026-05-27 / 1 of 312` top-right. Effective-date stamp. Vertical court-margin hairline at 80px. Phoenix span ID treated as the document's tracking number, bottom-left. Newsreader 200 + 800 paired on the headline. CSS 3D stack: four contract pages, perspective-tilted, parallax on mouse move; an ochre "M&A SOURCED" stamp lands on the top page.
- **C — Terminal evidence.** Dark surface. Phoenix span ID is the *architectural* element — runs as a 36px mono band across the bottom of the viewport, bookended by trace metadata and a verdict line. Headline sits in conversation *with* the span ID, not above it. Fragment shader on the right half: scan-line + low-freq noise tinted cyan-ink, mouse-halo. Three cyan placements maximum: span ID, footnote marker, CTA underline.

## Component inventory (factored across the three files)

Inline in each variant — the brief is so opinionated about per-variant composition that abstracting them into shared components would dilute the move. Each file is short enough (~250 lines incl. CSS) to read end-to-end:

- **Line-number rail** (B) — `<div class="lineno">` populated with two-digit padded numbers.
- **Court margin** (A, B) — 1px hairline at 96px / 80px.
- **Doc ID** (all) — top-right mono uppercase tracking number.
- **Headline + footnote marker** (all) — `<sup>` rotated -6° to -8° on hover.
- **Primary CTA** — underlined type with `→` that translates 6–8px right on hover. Never a filled rectangle button.
- **Secondary CTA** — underlined small text inline within a sentence (A) or beside primary (B, C) — **never** as a second button in a row.
- **Span ID** — A: vertical column / B: bottom-left tracking number / C: 36px architectural band.
- **Footer band** — stats line + footnote resolution + sometimes secondary CTA.
- **Dimensional layer** — variant-specific (SVG / CSS 3D / WebGL shader).

## What this kit deliberately does not include

- **No nav, footer, logo strip, social proof, testimonials, pricing.** Killed by §1.1 / §5.15 of the brief.
- **No "Try Free" pill, no "Now with Claude" badge.** Killed by §1.1.
- **No icon system.** The brand uses type + document marks instead — see `../../README.md` § Iconography.
- **No product UI.** The brief covers the marketing surface only; the actual agent dashboard / contract reader / Phoenix trace viewer has no design context and is out of scope.

## Notes & caveats

- **Fonts are Google Fonts substitutes** for the commercial families locked in the brief (Instrument Serif/Newsreader for PP Editorial New; Space Grotesk/Inter Tight for PP Neue Montreal/Söhne; Geist Mono/IBM Plex Mono for Berkeley Mono). Swap the `--font-display/body/mono` custom properties in `colors_and_type.css` once licensed.
- **The WebGL shader** in variant C may not render in headless screenshot environments. Variant C's static composition reads as composed without the shader running (the span band, headline, and surface carry it).
- **Mobile** — every variant ships a `@media (max-width: 768px)` reflow. Mobile is a *deliberate mobile composition*, not a desktop crammed into 375px.
