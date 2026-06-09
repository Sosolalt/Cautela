/**
 * design/tokens.ts — source of truth for the M&A Gatekeeper design system.
 *
 * v2 revision: 2026-05-27 — cohort must-fix list applied (WCAG contrast fixes,
 * focus-state tokens, layout primitives, light-mode parity, new primitives).
 * See design/SYSTEM.md §DELTA-v2.
 *
 * Imported by:
 *   - ma_gatekeeper/frontend/tailwind.config.ts (extends colors, spacing, fontFamily,
 *     fontSize, lineHeight, letterSpacing, borderRadius, transitionTimingFunction,
 *     transitionDuration, screens, minHeight, maxWidth, opacity)
 *   - ma_gatekeeper/frontend/app/globals.css (CSS variable declarations on :root and
 *     [data-theme="light"])
 *
 * Locked by Art Director on 2026-05-26 per design/SYSTEM.md.
 * v2 revision pending Supervisor sign-off on the brand vs. interactive color split
 * (design/SYSTEM.md §Architectural decision).
 * Do not edit token values without an AD section-review escalation per design/PLAN.md §3.3.
 *
 * Weird-lift enforcement (SYSTEM.md §Color / INSPIRATION.md §Five-weird-lifts):
 *   - `brand-blue` is deliberately NOT exported. If a Component Builder writes
 *     `border-brand-blue`, the Tailwind class will not resolve and the build fails.
 *   - No `.stat-card` preset is exported. The §6.4 moneymoment lives in negative
 *     space (Card `naked` variant — composition over preset, INSPIRATION §0.1).
 */

/**
 * Color tokens — SYSTEM.md §Color (PLAN §5.1).
 * Dark-mode anchored cool-green-tinted neutrals; warm-clay single accent;
 * risk lanes scoped to ≤5% canvas (clear/escalate) with block aliased to accent-clay.
 *
 * Theme convention (Round-2 R2 resolution):
 *   The design system is DARK-DEFAULT. Per PLAN §5.1 "Background: dark mode default
 *   … Light mode is parity, not afterthought." Root surfaces in `app/layout.tsx`
 *   render `bg-neutral-900 text-neutral-50` with no `data-theme` attribute set;
 *   light-mode parity ships as an opt-in `<html data-theme="light">` override
 *   that swaps the `--link-color` (and, in Phase-6 polish, the `:root` neutrals)
 *   via globals.css. Components that need a light surface inside the dark page
 *   (e.g. the existing review-app panes) set `bg-white` explicitly on themselves.
 *
 * v2 architectural split (SYSTEM.md §Architectural decision — pending Supervisor sign-off):
 *   - `brand-primary` is DECORATIVE ONLY (logo wash, OG card, brand-surface moments).
 *     Fails 4.5:1 — must NEVER appear as body text, link, focus ring, or text-on-dark.
 *   - `text-interactive` / `focus-ring` / `link-color` carry every text/focus surface
 *     that previously leaned on `brand-primary`. Verified ≥4.5:1 on `neutral-900`.
 */
// Single source for the warm-clay hex — shared by `accent-clay` and `lane-block`
// per SYSTEM.md §Color decision (no fourth hue for the block lane).
// `design/tokens.test.ts` asserts the two keys stay structurally identical.
const ACCENT_CLAY_HEX = "#B86F3D";

// Staged escape hatch — ~25% darker clay for the Block-Escalate visual collision case
// per SYSTEM.md §18 polish item. NOT exported by default; uncomment to swap accent-clay
// in a one-line change if Day-5 review surfaces the collision.
// const ACCENT_CLAY_DARK_HEX = "#8B5430";

export const colors = {
  // Brand (decorative-only — SYSTEM.md §Architectural decision).
  // TODO: Playwright field-verify #0F4A38 against #0B1311 — decorative tier only (1.89:1).
  "brand-primary": "#0F4A38",

  // TODO: Playwright field-verify #B86F3D vs Mercury peach #F4D4BE saturation ceiling.
  "accent-clay": ACCENT_CLAY_HEX,

  // Interactive — passes WCAG 4.5:1 on --neutral-900 (verified ≥4.5:1).
  // TODO: Playwright field-verify #4A9D7E against #0B1311 for 4.5:1 small-text.
  "text-interactive": "#4A9D7E",
  "focus-ring":       "#4A9D7E",
  "link-color":       "#4A9D7E", // dark-mode default; light-mode uses brand-primary via globals.css

  // Text-on-filled tokens — dark glyph on every filled badge.
  // Round-2 contrast fix: the v1 light-on-clay pairing (#F4F6F3 on #B86F3D) clocked
  // 3.59:1 and failed 4.5:1 — the exact failure mode that triggered the Round-2
  // SYSTEM revision. Dark text restores compliance:
  //   text-on-accent-clay   #0B1311 on #B86F3D  → 4.82:1  (PASS)
  //   text-on-lane-clear    #0B1311 on #4D936F  → 5.13:1  (PASS)
  //   text-on-lane-escalate #0B1311 on #C49A3A  → 7.20:1  (PASS)
  //   text-on-lane-block    #0B1311 on #B86F3D  → 4.82:1  (PASS, aliases to accent-clay)
  // Guarded by tokens.test.ts Round-2 R2 filled-badge inverse tests.
  "text-on-accent-clay":   "#0B1311",
  "text-on-lane-clear":    "#0B1311",
  "text-on-lane-escalate": "#0B1311",
  "text-on-lane-block":    "#0B1311", // aliases to text-on-accent-clay (lane-block aliases to accent-clay)

  // Neutrals (cool-green-tinted, dark-mode anchored).
  "neutral-50":  "#F4F6F3",
  "neutral-100": "#ECEFEC",
  "neutral-200": "#D2DCD5",
  "neutral-300": "#A8B8AE",
  "neutral-400": "#7A8F83", // mono span-ID, passes 4.5:1 small-text
  "neutral-500": "#8A9E94", // v2: lightened from #4A5F55 to pass 4.5:1 on neutral-900
  // Decorative-only — FAILS 4.5:1. Borders/dividers/non-text chrome at ≥18px ONLY.
  // DO NOT use for body text. The Round-1 #4A5F55 value preserved here for chrome reuse.
  "neutral-500-decorative": "#4A5F55",
  "neutral-600": "#2D3F37",
  "neutral-700": "#1E2D27",
  "neutral-800": "#14201C",
  "neutral-900": "#0B1311",

  // Light-mode parity (full inversion documented in SYSTEM.md §Color → Light-mode neutral parity).
  "bg-paper":   "#FBFAF5",
  "text-paper": "#0E1311",
  "neutral-500-light": "#5A6F65", // light-mode equivalent of --neutral-500, passes 4.5:1 on bg-paper

  // Risk lanes — state-only, ≤5%-of-canvas max for clear/escalate.
  // `lane-block` aliases to accent-clay via the shared const so the §6.4
  // moneymoment can reuse the warm accent without diverging (SYSTEM.md §Color decision).
  // TODO: Playwright field-verify #4D936F against #0B1311 for 4.5:1 small-text.
  "lane-clear":    "#4D936F", // v2: lightened from #3F7A5A to pass 4.5:1 on neutral-900
  "lane-escalate": "#C49A3A",
  "lane-block":    ACCENT_CLAY_HEX,

  // State primitives (v2).
  "skeleton-base": "#1E2D27", // = neutral-700; pulses to neutral-600 at --opacity-skeleton
} as const;

// Deliberately undefined — INSPIRATION.md §Five-weird-lifts §Color.
// If a builder writes `border-brand-blue`, the class does not resolve and the build fails.
// DO NOT add a `brand-blue` key to the `colors` export above.
// export const brandBlue = undefined; // (do not add this export)

/**
 * Focus & state tokens — SYSTEM.md §Color → Focus & interactive tokens (v2).
 * Outline-based focus ring (NOT box-shadow) so it survives reduced-motion via the
 * scoped `:where(:focus-visible)` allowlist in globals.css.
 */
export const focusRing = {
  color:  "var(--focus-ring-color)", // resolves to text-interactive in :root
  width:  "2px",
  offset: "2px",
  style:  "solid" as const,
} as const;

/**
 * Opacity primitives — SYSTEM.md §Token-spec state primitives (v2).
 * `disabled` for the Button/Card disabled state; `skeleton` for loading pulses.
 */
export const opacity = {
  disabled: 0.4,
  skeleton: 0.6,
} as const;

/**
 * Font families — SYSTEM.md §Typography (Lane A locked with Option B foundries).
 * Display = Fraunces Variable; Body = Inter Variable; Mono = JetBrains Mono Variable.
 */
export const fontFamily = {
  display: ['"Fraunces Variable"', "Fraunces", "Georgia", "serif"],
  body:    ['"Inter Variable"', "Inter", "system-ui", "sans-serif"],
  mono:    ['"JetBrains Mono Variable"', "JetBrains Mono", "ui-monospace", "monospace"],
} as const;

/**
 * Type scale — SYSTEM.md §Typography Type scale (anchored to COPY §18).
 * Each entry is [size, line-height, letter-spacing] at desktop values.
 * Mobile responsive overrides applied via Tailwind md:/lg: utilities in components.
 * v2: `hero-display-mobile` added as an explicit 96px override for the §6.4 moneymoment.
 */
export const fontSize = {
  "hero-display":         ["240px", "1.05", "-0.02em"],
  "hero-display-mobile":  ["96px",  "1.05", "-0.02em"], // v2: explicit mobile override
  "hero-tagline":         ["96px",  "1.05", "-0.01em"],
  "hero-sub":             ["56px",  "1.1",  "-0.01em"],
  "display-md":           ["32px",  "1.15", "-0.005em"],
  "body-lg":              ["24px",  "1.5",  "0"],
  "body":                 ["16px",  "1.55", "0"],
  "mono-attribution":     ["16px",  "1.4",  "0"],
  "mono-badge":           ["14px",  "1.2",  "+0.08em"],
  // `mono-span` (12px, no tracking) is for inline span-ID references in body copy ONLY.
  // For the §2 hero span-ID overlay (video-capture surface) use `mono-overlay` (14px)
  // so the glyph string stays legible at 1440p — `mono-badge` carries +0.08em uppercase
  // tracking that disfigures a raw span ID like `phoenix:span:7f3a--c2b1`.
  "mono-span":            ["12px",  "1.4",  "0"],
  "mono-overlay":         ["14px",  "1.4",  "0"], // v2: §2 hero overlay span-ID — 14px for 1440p video legibility, no tracking
  "small":                ["14px",  "1.5",  "0"],
  "micro":                ["12px",  "1.4",  "+0.02em"],
} as const;

/**
 * Font-feature settings — SYSTEM.md §Typography pro tip.
 * Mono ligatures off globally so phoenix span IDs like `phoenix:span:7f3a--c2b1`
 * do not fuse `--` into an em-dash glyph. Display carries the optical-size axis
 * default (opsz 90 = wordmark scale; hero number overrides to opsz 96 inline).
 */
export const fontFeatureSettings = {
  mono: '"liga" 0, "calt" 0',
  display: '"opsz" 90',
} as const;

/**
 * Spacing scale — SYSTEM.md §Token-spec (8px base; named keys map to
 * the multiplier convention `1` = 4px, `2` = 8px, etc.).
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
  "12":  "96px",
  "16":  "128px",
  "20":  "192px",
  "24":  "240px",
} as const;

/**
 * Layout primitives — SYSTEM.md §Token-spec Layout primitives (v2).
 * `sectionMinHeight` is consumed by Tailwind's `minHeight` extend so sections
 * can write `min-h-moneymoment` instead of arbitrary `min-h-[150vh]`.
 */
export const sectionMinHeight = {
  hero:        "100vh",
  problem:     "80vh",
  howItWorks:  "100vh",
  moneymoment: "150vh",
  numbers:     "80vh",
  loop:        "80vh",
  cta:         "60vh",
} as const;

/**
 * Container max-widths — SYSTEM.md §Token-spec Layout primitives (v2).
 * `prose` is the §11 longest-FAQ-answer cap above 1440px; `wide` is the hero
 * and moneymoment outer frame; `default` is the standard content container.
 */
export const containerMaxWidth = {
  prose:   "75ch",   // §11 longest FAQ answer above 1440px
  default: "1200px", // standard content container
  wide:    "1440px", // hero, moneymoment outer frame
} as const;

/**
 * Breakpoint tokens — SYSTEM.md §Token-spec Layout primitives (v2).
 * `md: 768px` matches Tailwind's default md breakpoint AND PLAN §6.1's mobile
 * hero scroll-jacking cutoff. Spread into Tailwind `theme.extend.screens` (not
 * `theme.screens`) so Tailwind's defaults remain available for any unlisted key.
 */
export const breakpoints = {
  sm: "640px",
  md: "768px",  // mobile hero scroll-jacking cutoff (PLAN §6.1)
  lg: "1024px",
  xl: "1280px",
} as const;

/**
 * Border-radius scale — SYSTEM.md §Token-spec / §Component primitives Card
 * (Card default = 12px = `lg`).
 */
export const borderRadius = {
  none: "0",
  sm:   "4px",
  md:   "8px",
  lg:   "12px",
  xl:   "16px",
  full: "9999px",
} as const;

/**
 * Motion easing — SYSTEM.md §Motion language §1 (PLAN §4.3).
 * One easing only. Named `easePrimary` per the locked nomenclature.
 */
export const easePrimary = "cubic-bezier(0.16, 1, 0.3, 1)" as const;

/**
 * Motion durations — SYSTEM.md §Motion language §1 (PLAN §4.3).
 * Three primitives. Named `durationMicro` / `durationComponent` / `durationHero`
 * per the locked nomenclature.
 */
export const durationMicro = "150ms" as const;     // hover, focus, tooltip
export const durationComponent = "400ms" as const; // section reveal, card hover, tab transition
export const durationHero = "800ms" as const;      // hero entry, full-viewport composition

/**
 * Stagger constant — SYSTEM.md §Motion language §1 (PLAN §4.3).
 * 60ms between siblings, expressed as the Framer Motion `staggerChildren` seconds value.
 */
export const stagger = 0.06 as const;

/**
 * Per-scene exception — SYSTEM.md §Motion language §1.
 *
 * The §6.4 moneymoment per-span unfurl deliberately lives at 1800ms
 * (INSPIRATION §Five-weird-lifts §Motion). It DOES ship as a module-scope export
 * because GSAP's `scrub` config consumes the value at runtime — the Round-1 claim
 * that "it is not a global token" was the lie this v2 honesty correction fixes.
 *
 * @policy noreuse — (custom non-standard tag, not enforced by tooling.)
 *            Only the §6.4 moneymoment may import this value for component motion.
 *            The single sanctioned reuse is the edge-stroke `linear` pulse on the
 *            §How-it-works pipeline (SYSTEM.md §Motion language §6) — that import
 *            must also code-comment the reuse. A code-review rejection lands on
 *            any third import.
 */
export const durationMoneymomentSpan = "1800ms" as const;

/**
 * Scroll progress constants — SYSTEM.md §Motion language §2.
 * Section enters at scrollProgress 0.1 of its own bounding box; completes at 0.6.
 */
export const scrollEnter = 0.1 as const;
export const scrollComplete = 0.6 as const;

/**
 * Tailwind-compatible aliases for easing and durations — SYSTEM.md §Token-spec.
 * These objects are spread into `tailwind.config.ts` so utilities like
 * `ease-default`, `duration-component` resolve at build time.
 */
export const transitionTimingFunction = {
  default: easePrimary,
} as const;

export const transitionDuration = {
  micro:     durationMicro,
  component: durationComponent,
  hero:      durationHero,
} as const;

/**
 * Gradient angle whitelist — PLAN §1.4 / SYSTEM.md §Token-spec.
 * Mesh gradients ship with these three angles only. Whitelist is advisory until
 * `eslint-plugin-tailwindcss` lands the arbitrary-value-rejection rule
 * (SYSTEM.md §Token-spec follow-up); Tailwind JIT `bg-[linear-gradient(45deg,...)]`
 * still resolves today.
 */
export const gradientAngles = ["15deg", "165deg", "345deg"] as const;
