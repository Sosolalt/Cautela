/**
 * design/tokens.ts — code mirror of `design/claude-design-output/colors_and_type.css`.
 *
 * 2026-06-08 — revalued for the Documentary Brutalism design system. The brand
 * has shifted from "modern SaaS / cool-green / warm-clay" to "Documentary
 * Brutalism / champagne+oxblood / warm-paper-on-near-black." The single
 * source-of-truth is now:
 *
 *   design/SOURCE_OF_TRUTH.md           ← short index
 *   design/claude-design-output/README.md   ← long-form rules
 *   design/claude-design-output/source/design.md   ← authoritative brief
 *   design/claude-design-output/colors_and_type.css ← CSS-side mirror of this file
 *
 * Any value drift between `colors_and_type.css` and this file is a bug — fix
 * this file to match the CSS, not the other way round.
 *
 * Export shape preserved from v2 (same keys: `accent-clay`, `brand-primary`,
 * `text-interactive`, `lane-clear`, etc.) so `tailwind.config.ts` and the
 * existing component classes continue to compile. Values have been remapped:
 *
 *   brand-primary       #0F4A38 (forest)  → #9C7E3F (champagne-deep)
 *   accent-clay         #B86F3D (warm-clay — now FORBIDDEN) → #8B2635 (oxblood)
 *   text-interactive    #4A9D7E (signal-green) → #C9A961 (champagne)
 *   focus-ring          #4A9D7E → #C9A961
 *   link-color          #4A9D7E → #C9A961
 *   lane-clear          #4D936F → #E0CB94 (champagne-soft)
 *   lane-escalate       #C49A3A → #C9A961 (champagne)
 *   lane-block          aliases to accent-clay (= oxblood)
 *   neutral-50..900     cool-green ramp → warm-paper → near-black ramp
 *   fontFamily.display  Fraunces → Instrument Serif / Newsreader
 *   fontFamily.body     Inter    → Space Grotesk / Inter Tight
 *   fontFamily.mono     JetBrains Mono → Geist Mono / IBM Plex Mono
 *
 * Imported by:
 *   - ma_gatekeeper/frontend/tailwind.config.ts
 *   - ma_gatekeeper/frontend/app/globals.css (mirrored as :root custom properties)
 *
 * Brand-level invariants enforced by `design/tokens.test.ts`:
 *   - `brand-blue` is never exported (the system's "no blue" non-negotiable).
 *   - `accent-warm-clay` (`#B86F3D`) is never exported under any key.
 *   - `lane-block` aliases to `accent-clay` (single hex for the severe lane).
 *   - `border-radius` is `0` globally (Documentary-Brutalism non-negotiable).
 *   - One easing only: `cubic-bezier(0.16, 1, 0.3, 1)`.
 */

// Single source for the oxblood hex — shared by `accent-clay` and `lane-block`.
// `design/tokens.test.ts` asserts the two keys stay structurally identical.
const ACCENT_OXBLOOD_HEX = "#8B2635";

// Forbidden under brand non-negotiables — kept here as a const NOT exported, so
// a grep for "B86F3D" in this file lands on the explicit ban, not on a live
// token. Re-introducing this value as an export would violate the brand.
// const ACCENT_WARM_CLAY_FORBIDDEN = "#B86F3D";

export const colors = {
  // ---------- BRAND (decorative, never small-text) ----------
  // Champagne-deep — aged-brass shadow tier. Use for logo wash, OG card,
  // brand-surface moments. Fails 4.5:1 on near-black for small body text.
  "brand-primary": "#9C7E3F",

  // ---------- PRIMARY STAMP / SEVERE ACCENT ----------
  // Oxblood — the "legal-red stamp on the document." Replaces the prior
  // warm-clay accent (which is now explicitly forbidden by the brand).
  // Used as a FILL, not as small body text on the dark surface.
  "accent-clay": ACCENT_OXBLOOD_HEX,

  // ---------- INTERACTIVE (champagne) ----------
  // Champagne #C9A961 clocks ~8.6:1 against the #0B0B0C surface — passes
  // 4.5:1 small-text and 3:1 large-text. Used for link, focus ring, hover.
  "text-interactive": "#C9A961",
  "focus-ring":       "#C9A961",
  "link-color":       "#C9A961", // dark-mode default; light-mode swap in globals.css

  // ---------- TEXT-ON-FILLED ----------
  // Dark glyph on light champagne tones; light glyph on oxblood.
  // Contrast verified by `design/tokens.test.ts`.
  "text-on-accent-clay":   "#E8DDC4", // ivory on oxblood
  "text-on-lane-clear":    "#1A1916", // ink-paper on champagne-soft
  "text-on-lane-escalate": "#1A1916", // ink-paper on champagne
  "text-on-lane-block":    "#E8DDC4", // ivory on oxblood (aliases via lane-block)

  // ---------- NEUTRALS — warm-paper → near-black ramp ----------
  // Anchored to the locked surface (#0B0B0C) and ink (#ECECEA / #8A8A86 / #54534F)
  // tokens in colors_and_type.css. Numeric keys preserved so existing
  // `bg-neutral-{50..900}` / `text-neutral-*` calls continue to resolve.
  "neutral-50":  "#F4F2EC", // surface-alt (warm paper, lightest surface)
  "neutral-100": "#ECEBE3", // paper variant
  "neutral-200": "#D6D2C5", // mid-light paper
  "neutral-300": "#B6B2A6", // ink-paper-faint
  "neutral-400": "#8A8A86", // ink-muted (the dark/light bridge)
  "neutral-500": "#6C6A63", // ink-paper-muted — passes 4.5:1 on bg-paper for body text
  "neutral-600": "#54534F", // ink-faint (rules, borders, document chrome on dark)
  "neutral-700": "#3D3C39", // mid-dark
  "neutral-800": "#1A1916", // ink-paper / ink-dim adjacent
  "neutral-900": "#0B0B0C", // surface — near-black, slightly warm. NEVER #000000.

  // Decorative-only chrome tone — borders / dividers at ≥18px ONLY. Fails 4.5:1.
  "neutral-500-decorative": "#54534F",

  // Light-mode parity (full inversion documented in claude-design-output/README.md).
  "bg-paper":   "#F4F2EC",
  "text-paper": "#1A1916",
  "neutral-500-light": "#6C6A63",

  // ---------- RISK LANES — semantic state-only ----------
  // Re-mapped onto the M&A luxury palette. `lane-block` aliases to accent-clay
  // (= oxblood) so the severe accent stays single-source.
  "lane-clear":    "#E0CB94", // champagne-soft — passes 4.5:1 on near-black surface
  "lane-escalate": "#C9A961", // champagne — passes 4.5:1 on near-black surface
  "lane-block":    ACCENT_OXBLOOD_HEX,

  // ---------- DOCUMENTARY-BRUTALISM ACCENTS (extended palette) ----------
  // New keys mirror `claude-design-output/colors_and_type.css`. Prefer these
  // over the legacy aliases above when writing new components.
  "surface":              "#0B0B0C",
  "surface-alt":          "#F4F2EC",
  "ink":                  "#ECECEA",
  "ink-muted":            "#8A8A86",
  "ink-faint":            "#54534F",
  "ink-dim":              "#2A2A28",
  "ink-paper":            "#1A1916",
  "ink-paper-muted":      "#6C6A63",
  "ink-paper-faint":      "#B6B2A6",
  "accent-champagne":      "#C9A961", // primary luxury accent
  "accent-champagne-deep": "#9C7E3F", // shadow/secondary
  "accent-champagne-soft": "#E0CB94", // highlight
  "accent-oxblood":        ACCENT_OXBLOOD_HEX,
  "accent-ivory":          "#E8DDC4",
  // Legacy Documentary-Brutalism accents kept for back-compat; use sparingly.
  "accent-vermillion":     "#E63D2F",
  "accent-highlighter":    "#F0E040",
  "accent-ochre":          "#C28A2C",
  "accent-cyan-ink":       "#2BD4D9",

  // State primitives.
  "skeleton-base": "#1A1916", // = neutral-800; pulses to neutral-700 at --opacity-skeleton
} as const;

// Deliberately undefined — the brand's "no blue" non-negotiable. If a builder
// writes `border-brand-blue`, the class does not resolve and the build fails.
// Do NOT add a `brand-blue` key to the `colors` export above.

/**
 * Focus & state tokens — outline-based focus ring (NOT box-shadow) so it
 * survives reduced-motion via the scoped `:where(:focus-visible)` allowlist
 * in globals.css.
 */
export const focusRing = {
  color:  "var(--focus-ring-color)", // resolves to text-interactive (champagne) in :root
  width:  "2px",
  offset: "2px",
  style:  "solid" as const,
} as const;

export const opacity = {
  disabled: 0.4,
  skeleton: 0.6,
} as const;

/**
 * Font families — Documentary Brutalism stack.
 *
 *   Display : Instrument Serif (PP Editorial New substitute) + Newsreader
 *   Body/UI : Space Grotesk     (PP Neue Montreal substitute) + Inter Tight
 *   Mono    : Geist Mono        (Berkeley Mono substitute)    + IBM Plex Mono
 *
 * Plain Inter is forbidden. Fraunces is permitted only at weight 900 + opsz 144
 * at 200px+ — for the standard body/UI stack, use Space Grotesk.
 */
export const fontFamily = {
  display: ['"Instrument Serif"', '"Newsreader"', "Georgia", "serif"],
  body:    ['"Space Grotesk"', '"Inter Tight"', "system-ui", "sans-serif"],
  mono:    ['"Geist Mono"', '"IBM Plex Mono"', "ui-monospace", "monospace"],
} as const;

/**
 * Type scale — Documentary Brutalism display floor/ceiling.
 *
 * Each entry is `[size, line-height, letter-spacing]` at desktop values.
 *
 *   display-xxl 216px — maximum-commitment
 *   display-xl  144px — honest display
 *   display-lg  112px
 *   display-md   88px — FLOOR. anything below = under-committed
 *   display-sm   64px — sub-display only
 *
 * Display ↔ body contrast must stay ≥ 5.5× (88/16 = 5.5× is the floor;
 * 144/18 = 8× is honest). Mobile (≤768px) drops the ceiling to 88px.
 */
export const fontSize = {
  // Documentary-Brutalism scale (new — prefer these).
  "display-xxl":          ["216px", "0.88", "-0.035em"],
  "display-xl":           ["144px", "0.92", "-0.030em"],
  "display-lg":           ["112px", "0.94", "-0.020em"],
  "display-md":           ["88px",  "0.96", "-0.020em"],
  "display-sm":           ["64px",  "1.00", "-0.015em"],

  // Mobile display overrides — used inside `md:` breakpoint utilities.
  "display-xxl-mobile":   ["88px",  "1.00", "-0.020em"],
  "display-md-mobile":    ["56px",  "1.02", "-0.015em"],

  // Legacy hero-* keys preserved so existing components keep compiling.
  // These map to the new scale; new components should use `display-*` instead.
  "hero-display":         ["216px", "0.88", "-0.035em"],
  "hero-display-mobile":  ["88px",  "1.00", "-0.020em"],
  "hero-tagline":         ["88px",  "0.96", "-0.020em"],
  "hero-sub":             ["56px",  "1.10", "-0.015em"],

  // Body + mono — unchanged shape, refined values to match colors_and_type.css.
  "body-lg":              ["18px",  "1.45", "0"],
  "body":                 ["16px",  "1.50", "0"],
  "body-sm":              ["14px",  "1.45", "0"],

  "mono-arch":            ["32px",  "1.10", "-0.01em"], // span ID as architecture
  "mono-arch-sm":         ["24px",  "1.10", "0"],
  "mono-attribution":     ["16px",  "1.40", "0"],
  "mono-badge":           ["14px",  "1.20", "+0.08em"],
  "mono-span":            ["14px",  "1.40", "0"], // inline span-ID in body copy
  "mono-overlay":         ["14px",  "1.40", "0"], // §2 hero overlay span-ID
  "mono-foot":            ["11px",  "1.40", "+0.04em"], // line numbers, doc IDs (uppercase)

  "small":                ["14px",  "1.50", "0"],
  "micro":                ["12px",  "1.40", "+0.02em"],
} as const;

/**
 * Font-feature settings — mono ligatures off globally so the Phoenix span ID
 * `phoenix:span:7f3a--c2b1` does NOT fuse `--` into an em-dash glyph.
 */
export const fontFeatureSettings = {
  mono: '"liga" 0, "calt" 0',
  display: '"opsz" 90',
} as const;

/**
 * Spacing scale — 8px baseline grid. Named keys map to the multiplier
 * convention `1` = 4px, `2` = 8px, etc. Viewport-edge margins are flush (0px)
 * or generous (96px+); the polite 24px inset is the safe-default to avoid.
 */
export const spacing = {
  "0":   "0",
  "1":   "4px",
  "2":   "8px",
  "3":   "12px",
  "4":   "16px",
  "5":   "24px",
  "6":   "32px",
  "8":   "48px",
  "10":  "64px",
  "12":  "96px",   // generous edge margin (Documentary-Brutalism flush-or-96+ rule)
  "16":  "128px",
  "20":  "192px",
  "24":  "240px",
} as const;

export const sectionMinHeight = {
  hero:        "100vh",
  problem:     "80vh",
  howItWorks:  "100vh",
  moneymoment: "150vh",
  numbers:     "80vh",
  loop:        "80vh",
  cta:         "60vh",
} as const;

export const containerMaxWidth = {
  prose:   "75ch",
  default: "1200px",
  wide:    "1440px",
} as const;

export const breakpoints = {
  sm: "640px",
  md: "768px",
  lg: "1024px",
  xl: "1280px",
} as const;

/**
 * Border-radius — locked at 0 globally per the brand's non-negotiable.
 * Legacy keys preserved so existing components keep compiling, but every
 * value resolves to "0" so any `rounded-*` utility paints a square corner.
 * If a component genuinely needs a radius, it is violating the brand —
 * remove the radius, do not raise these values.
 */
export const borderRadius = {
  none: "0",
  sm:   "0",
  md:   "0",
  lg:   "0",
  xl:   "0",
  full: "0",
} as const;

/**
 * Motion easing — ONE easing only. Documentary-Brutalism non-negotiable.
 */
export const easePrimary = "cubic-bezier(0.16, 1, 0.3, 1)" as const;

/**
 * Motion durations — locked at TWO primitives by the brand:
 *
 *   durationMicro      200ms — hover, focus, interaction
 *   durationHero       800ms — entry, full-viewport composition
 *
 * `durationComponent` (400ms) is preserved as an alias for back-compat with
 * existing component code, but the brand spec recognizes only 200/800. New
 * components should use Micro (200ms) or Hero (800ms) directly.
 */
export const durationMicro = "200ms" as const;
export const durationComponent = "400ms" as const; // legacy — prefer durationMicro/durationHero
export const durationHero = "800ms" as const;

/**
 * Stagger — 60ms between siblings, expressed as Framer Motion's
 * `staggerChildren` seconds value.
 */
export const stagger = 0.06 as const;

/**
 * Per-scene exception preserved for the §6.4 moneymoment per-span unfurl.
 * GSAP `scrub` consumes the value at runtime. Single sanctioned reuse is the
 * §How-it-works pipeline edge-stroke pulse (must code-comment the reuse).
 */
export const durationMoneymomentSpan = "1800ms" as const;

export const scrollEnter = 0.1 as const;
export const scrollComplete = 0.6 as const;

export const transitionTimingFunction = {
  default: easePrimary,
} as const;

export const transitionDuration = {
  micro:     durationMicro,
  component: durationComponent,
  hero:      durationHero,
} as const;

/**
 * Gradient angles — kept for back-compat with the legacy `bg-gradient-*`
 * utilities baked into Tailwind config. The new brand explicitly forbids
 * mesh gradients, aurora, and noise overlays as background treatments;
 * any new use of these utilities is a brand violation. New components
 * should leave this array unconsumed.
 */
export const gradientAngles = ["15deg", "165deg", "345deg"] as const;
