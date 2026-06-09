import type { Config } from "tailwindcss";

import {
  borderRadius,
  breakpoints,
  colors as tokenColors,
  containerMaxWidth,
  fontFamily,
  fontSize,
  gradientAngles,
  opacity,
  sectionMinHeight,
  spacing,
  transitionDuration,
  transitionTimingFunction,
} from "../../design/tokens";

// Risk-lane semantics — `lane.block` aliases to accent-clay (= oxblood) so the
// severe-lane accent stays single-source per the Documentary-Brutalism brand.
const lane = {
  clear:    tokenColors["lane-clear"],
  escalate: tokenColors["lane-escalate"],
  block:    tokenColors["accent-clay"],
} as const;

// Flat camelCase tokens — exposed as Tailwind classes (`bg-brandPrimary`,
// `text-accentChampagne`, etc.). New components should prefer the
// Documentary-Brutalism names (`surface`, `ink`, `accentChampagne*`,
// `accentOxblood`, `accentIvory`); the legacy names are preserved for
// back-compat with existing classes in app/page.tsx and the review panes.
const flatColors = {
  // Legacy (back-compat — revalued under the hood).
  brandPrimary:        tokenColors["brand-primary"],
  accentClay:          tokenColors["accent-clay"],
  bgPaper:             tokenColors["bg-paper"],
  textPaper:           tokenColors["text-paper"],
  textInteractive:     tokenColors["text-interactive"],
  focusRing:           tokenColors["focus-ring"],
  linkColor:           tokenColors["link-color"],
  textOnAccentClay:    tokenColors["text-on-accent-clay"],
  textOnLaneClear:     tokenColors["text-on-lane-clear"],
  textOnLaneEscalate:  tokenColors["text-on-lane-escalate"],
  textOnLaneBlock:     tokenColors["text-on-lane-block"],
  skeletonBase:        tokenColors["skeleton-base"],
  neutral500Decorative: tokenColors["neutral-500-decorative"],
  neutral500Light:     tokenColors["neutral-500-light"],

  // Documentary-Brutalism (preferred — mirrors claude-design-output/colors_and_type.css).
  surface:              tokenColors["surface"],
  surfaceAlt:           tokenColors["surface-alt"],
  ink:                  tokenColors["ink"],
  inkMuted:             tokenColors["ink-muted"],
  inkFaint:             tokenColors["ink-faint"],
  inkDim:               tokenColors["ink-dim"],
  inkPaper:             tokenColors["ink-paper"],
  inkPaperMuted:        tokenColors["ink-paper-muted"],
  inkPaperFaint:        tokenColors["ink-paper-faint"],
  accentChampagne:      tokenColors["accent-champagne"],
  accentChampagneDeep:  tokenColors["accent-champagne-deep"],
  accentChampagneSoft:  tokenColors["accent-champagne-soft"],
  accentOxblood:        tokenColors["accent-oxblood"],
  accentIvory:          tokenColors["accent-ivory"],
  accentVermillion:     tokenColors["accent-vermillion"],
  accentHighlighter:    tokenColors["accent-highlighter"],
  accentOchre:          tokenColors["accent-ochre"],
  accentCyanInk:        tokenColors["accent-cyan-ink"],
} as const;

// Overrides Tailwind's default `neutral` palette (same keys `50..900`); the
// 10-step ramp now runs warm-paper (50) → near-black (900) per the
// Documentary-Brutalism palette. Existing `bg-neutral-*` calls in
// `app/page.tsx` / `findings-pane.tsx` / `pdf-pane.tsx` / `deal-picker.tsx` /
// `trace-pane.tsx` continue to resolve, but read warmer now than the prior
// cool-green-tinted ramp.
const neutral = {
  "50":  tokenColors["neutral-50"],
  "100": tokenColors["neutral-100"],
  "200": tokenColors["neutral-200"],
  "300": tokenColors["neutral-300"],
  "400": tokenColors["neutral-400"],
  "500": tokenColors["neutral-500"],
  "600": tokenColors["neutral-600"],
  "700": tokenColors["neutral-700"],
  "800": tokenColors["neutral-800"],
  "900": tokenColors["neutral-900"],
} as const;

// Gradient angle whitelist — PLAN §1.4. The reducer-built map is advisory until
// `eslint-plugin-tailwindcss` lands the arbitrary-value-rejection rule (SYSTEM.md
// §Token-spec follow-up); JIT `bg-[linear-gradient(45deg,...)]` still resolves today.
const gradientImages = gradientAngles.reduce<Record<string, string>>((acc, angle) => {
  const key = `gradient-${angle.replace("deg", "")}`;
  acc[key] = `linear-gradient(${angle}, var(--tw-gradient-stops))`;
  return acc;
}, {});

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    // Breakpoints land under `extend.screens` (NOT `theme.screens`) so Tailwind's
    // defaults (`2xl`, etc.) remain available for any unlisted key — `md: 768px`
    // in our token map matches Tailwind's default md breakpoint AND PLAN §6.1's
    // mobile hero scroll-jacking cutoff, so the override is identity at that key.
    // Spec considered `theme.screens` (full replace) for cleaner semantics, but
    // `extend.screens` is the safer call since Tailwind's `2xl: 1536px` is still
    // useful for the §15 OG-image layout and 4K landing-page chrome.
    extend: {
      colors: {
        // Spread the raw kebab-case design tokens FIRST so kebab class names
        // (`text-ink-muted`, `border-ink-faint`, `bg-accent-vermillion`, …)
        // actually resolve. The codebase writes kebab throughout, but
        // `flatColors` only exposed camelCase (`text-inkMuted`), so every
        // multi-word color class (ink-muted / ink-faint / ink-dim / every
        // accent-*) was a SILENT no-op — it fell back to inherited color. This
        // was masked on the old white theme; the dark re-theme exposes it. The
        // camelCase aliases from `flatColors` still layer on top.
        ...tokenColors,
        ...flatColors,
        neutral,
        lane,
      },
      fontFamily,
      fontSize,
      spacing,
      borderRadius,
      transitionTimingFunction,
      transitionDuration,
      backgroundImage: gradientImages,
      // Layout primitives (v2 — SYSTEM.md §Token-spec).
      // `min-h-moneymoment` / `min-h-hero` etc. resolve via these keys.
      minHeight: sectionMinHeight,
      maxWidth: containerMaxWidth,
      // Breakpoints extend Tailwind defaults — see comment above.
      screens: breakpoints,
      // State primitives (v2 — SYSTEM.md §Token-spec).
      // `opacity-disabled` / `opacity-skeleton` resolve via these keys.
      opacity,
    },
  },
  plugins: [],
};

export default config;
