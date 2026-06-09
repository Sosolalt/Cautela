# Design — Source of Truth

> **Updated 2026-06-08.** This file supersedes the prior phase docs (`PLAN.md`, `INSPIRATION.md`, `STACK.md`, `SYSTEM.md`, `COPY.md`, `TOOLING.md`, `REVIEW_NOTES.md`). Those files are kept for audit-trail value only and carry a `> SUPERSEDED` banner; do not read them as design guidance.

---

## Where the brand lives now

The canonical design system is in **`design/claude-design-output/`**. It was generated end-to-end by the `claude design` workflow and is the only place that defines the brand going forward.

Read order on cold pickup:

1. **`design/claude-design-output/README.md`** — content fundamentals, visual foundations, iconography, composition rules.
2. **`design/claude-design-output/source/design.md`** — the authoritative original creative brief. Treat as last word in any disagreement.
3. **`design/claude-design-output/colors_and_type.css`** — CSS custom properties for the locked palette / type / spacing / motion tokens. Drop into any page.
4. **`design/claude-design-output/ui_kits/marketing/`** — hero variants showing the rules applied at full scale.
5. **`design/claude-design-output/preview/`** — atomic system cards (one rule per card).

---

## What the brand is now

**Documentary Brutalism.** The landing page behaves like a piece of legal evidence, not a marketing page about it. Three lineages, in priority order:

1. **Court-filing aesthetic** — line numbers down the left edge, document IDs in the corner, footnote markers on specific headline words, vertical court-margin rules. Asymmetric, rail-aligned, never centered.
2. **Editorial brutalism / Swiss-press maximalism** — typography allowed to be enormous (88px floor; 216px ceiling). Display↔body weight contrast ≥ 8×. Hanging punctuation. Words bleeding off viewport edges intentionally.
3. **Terminal / telemetry surfaces** — the Phoenix span ID is *evidence*, not a label. Architectural placement only.

### The locked non-negotiables

- **No blue, no purple-pink gradient, no warm-clay (`#B86F3D`).** No Inter, no Roboto, no system-ui.
- **`border-radius: 0` globally. `box-shadow: none` globally.** No card frame around hero compositions.
- **No centered hero stack. No row-of-buttons CTA block.**
- **One accent color per surface, used in at most three placements.**
- **Display ≥ 88px floor when used as a headline. Display↔body contrast ≥ 5.5×.**
- **Mono ligatures globally off** (`font-feature-settings: "liga" 0, "calt" 0`).
- **No emoji. No icon font in marketing surfaces.** The `→` arrow inside CTA labels is the only permitted glyph, set as type.
- **Em-dash (`—`, U+2014) is load-bearing.** Not `--`. Not `-`.
- **One easing only:** `cubic-bezier(0.16, 1, 0.3, 1)`. Two durations: `200ms` (hover/interaction), `800ms` (entry).
- **Forbidden:** mesh gradients, aurora, glassmorphism, noise overlays, raster imagery, Lottie, Rive, post-processing bloom, particle systems, autoplay video.
- **`prefers-reduced-motion: reduce`** is honored.

### Locked palette

| Token | Hex | Use |
|---|---|---|
| `--surface` | `#0B0B0C` | near-black, slightly warm. NEVER `#000000` |
| `--surface-alt` | `#F4F2EC` | warm paper. One variant maximum |
| `--ink` | `#ECECEA` | high-contrast text on dark |
| `--ink-muted` | `#8A8A86` | secondary text, line numbers |
| `--ink-faint` | `#54534F` | rules, borders, document chrome |
| `--accent-champagne` | `#C9A961` | polished brass — primary luxury accent |
| `--accent-champagne-deep` | `#9C7E3F` | aged brass — shadow/secondary |
| `--accent-champagne-soft` | `#E0CB94` | champagne highlight |
| `--accent-oxblood` | `#8B2635` | refined red — replaces vermillion / replaces the forbidden warm-clay |
| `--accent-ivory` | `#E8DDC4` | warm contrast tone |

Legacy Documentary-Brutalism accents kept for back-compat: `--accent-vermillion` (`#E63D2F`), `--accent-highlighter` (`#F0E040`), `--accent-ochre` (`#C28A2C`), `--accent-cyan-ink` (`#2BD4D9`). Use sparingly; the M&A luxury palette above is the default.

### Locked typography

| Role | Family stack |
|---|---|
| Display | `Instrument Serif` → `Newsreader` → Georgia |
| Body / UI | `Space Grotesk` → `Inter Tight` (plain Inter is forbidden) |
| Mono | `Geist Mono` → `IBM Plex Mono` (ligatures off) |

If commercial families (PP Editorial New, PP Neue Montreal, Berkeley Mono) become licensed, swap the `--font-display` / `--font-body` / `--font-mono` custom properties and the page picks them up.

### Locked scale (desktop)

| Token | Px | Notes |
|---|---|---|
| `--size-display-xxl` | 216 | maximum-commitment display |
| `--size-display-xl` | 144 | honest display |
| `--size-display-lg` | 112 | |
| `--size-display-md` | 88 | display floor |
| `--size-display-sm` | 64 | sub-display only |
| Body | 16–18 | |
| Mono inline | 14–16 | |
| Mono architectural | 24–32 | margin column, footer band, span ID treated as evidence |

Mobile (≤768px) drops the display ceiling to 88px and the floor to 56px.

### Locked copy

Voice anchors (do not paraphrase):

- **Hero tagline:** *Every flag, sourced. Every verdict, traced. Every span, clickable.*
- **Anchor sub-line:** *M&A contract review where every verdict links to its Phoenix trace — and every flag is sourced to the clause it came from.*
- **Conservative stats line:** *Cluster-bootstrap 95% lower bound — contracts as the IID unit. Wilson 95% LB retained as an exploratory per-finding-IID cross-check. Frozen held-out fold. We report the worst case, not the best.*
- **Primary CTA:** `Try the demo →`
- **Secondary CTA:** `Watch the 60-second demo`

Vocabulary discipline:

| Say | Don't say |
|---|---|
| flag, verdict, source, trace, span, clause | insight, recommendation, finding, takeaway |
| six agents | "AI assistant," "copilot," "agent swarm" |
| frozen held-out fold | "validated on our test set" |
| cluster-bootstrap 95% LB (Wilson as exploratory cross-check) | "high accuracy" |
| 312 pages, Monday morning | "save time," "be productive" |
| Phoenix trace, span ID | "audit log," "explainability" |
| sourced, traced, clickable | "transparent," "explainable" |

Sentence case for headlines and UI labels. Em-dashes are load-bearing. No emoji ever. Footnote markers (`¹` `²` `³`) anchored to specific headline words are part of the design — treat them as type.

---

## How this maps to the code

`design/tokens.ts` is the code-level source-of-truth, derived from `claude-design-output/colors_and_type.css`. Tailwind (`ma_gatekeeper/frontend/tailwind.config.ts`) extends from `design/tokens.ts`; `app/globals.css` declares matching CSS custom properties on `:root`. Any value drift between `colors_and_type.css` and `tokens.ts` is a bug — fix `tokens.ts` to match the CSS, not the other way round.

Existing token keys (`accent-clay`, `brand-primary`, `lane-clear`, etc.) have been **revalued, not renamed**, to absorb the new palette without a full Tailwind-class rename pass:

| Old key | Old value | New value | Brand role |
|---|---|---|---|
| `brand-primary` | `#0F4A38` (forest) | `#9C7E3F` (champagne-deep) | decorative-only luxury accent |
| `accent-clay` | `#B86F3D` (warm clay — FORBIDDEN) | `#8B2635` (oxblood) | primary stamp/severe accent |
| `text-interactive` / `focus-ring` / `link-color` | `#4A9D7E` (signal-green) | `#C9A961` (champagne) | interactive surfaces |
| `lane-clear` | `#4D936F` (signal-green) | `#E0CB94` (champagne-soft) | safe/clear lane |
| `lane-escalate` | `#C49A3A` (signal-yellow) | `#C9A961` (champagne) | escalate lane |
| `lane-block` | aliases to `accent-clay` | aliases to `accent-clay` (= oxblood) | block lane |
| `neutral-50..900` | cool-green-tinted | warm-paper-to-near-black ramp | text + surfaces |

The structural keys are preserved so legacy components keep compiling. New components should prefer the M&A luxury palette names (`accent-champagne*`, `accent-oxblood`, `accent-ivory`, `surface`, `ink*`) once they are added to `tokens.ts`.

---

## What to do next

If you are working on the **landing page**, work from `claude-design-output/` directly — its hero variants, preview cards, and `colors_and_type.css` are production-ready and self-contained.

If you are working on the **product UI** (`ma_gatekeeper/frontend/`), import from `design/tokens.ts` as before; the values have shifted but the API hasn't. Migrate `bg-neutral-*` and `text-neutral-*` calls only when you touch the file for another reason — no global rename pass is required.

If you are writing **copy**, re-read the Voice & Cadence section of `claude-design-output/README.md` and the locked headline/sub-line/CTA strings. Do not paraphrase the locked strings.

If you are unsure whether the new system covers your case, the question to ask is: *does it pass the "documentary brutalism" sniff test — would this read as legal evidence, or as a marketing surface dressed up to look serious?* If the latter, you are fighting the brand.
