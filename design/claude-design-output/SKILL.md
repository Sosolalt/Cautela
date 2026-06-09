---
name: ma-gatekeeper-design
description: Use this skill to generate well-branded interfaces and assets for M&A Gatekeeper, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping in the Documentary Brutalism aesthetic register.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick orientation

This brand is **M&A Gatekeeper** — a multi-agent legal contract review tool. The locked aesthetic register is **Documentary Brutalism**: the design behaves like a piece of legal evidence, not a marketing page about it. There is one canonical source of truth: `source/design.md`. Treat that file as authoritative; everything else in this skill explains and applies it.

Before designing anything in this brand, internalize these non-negotiables:

- **No blue, no purple-pink gradient, no Inter, no Roboto, no system-ui.**
- **No `border-radius` above 0. No `box-shadow`. No card frame around hero compositions.**
- **No centered hero stack. No row-of-buttons CTA block.**
- **One accent color per surface, used in at most three places.**
- **Display ≥ 88px when used as a headline. Display↔body contrast ≥ 5.5×.**
- **Mono ligatures globally off** (`font-feature-settings: "liga" 0, "calt" 0`).
- **No emoji. No icon font in marketing surfaces.**
- **Em-dash (`—`, U+2014) is load-bearing.** Not `--`. Not `-`.

Open the `preview/` cards to see these rules rendered. Open the three `ui_kits/marketing/hero-*.html` files to see the rules applied at full scale across three defensibly-different aesthetic moves.

## What you'll find here

- `README.md` — content fundamentals, visual foundations, iconography, index.
- `source/design.md` — the original creative brief. The authoritative source.
- `colors_and_type.css` — CSS custom properties. Drop into any page.
- `assets/` — wordmark (HTML + SVG), stamp mark (SVG).
- `preview/` — atomic design system cards (colors, type, spacing, components, brand).
- `ui_kits/marketing/` — three hero variants (A/B/C) with a switcher.
- `SKILL.md` — this file.
