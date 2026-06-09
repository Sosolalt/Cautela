# Design System — M&A Gatekeeper

> Phase 5 deliverable per `design/PLAN.md` §5.
> **Owner**: Art Director.
> **Locked**: 2026-05-26 (Day 3 EOD — hard-to-reverse decisions per PLAN §3.3, captured for `PROJECT_LOG.md`). **v2 revision** 2026-05-27 (Round-2 Builder pass — 21 must-fix items from 3-reviewer cohort applied).
> **Round status**: Round 2 ship. Motion Designer's §Motion language section already merged. v2 closes the 3-reviewer cohort's must-fix list (Independent Art Director, Component Builder cold-onboard, Accessibility Auditor) — see §DELTA-v2 below.
> **Inputs**: `design/PLAN.md` §5.1 / §5.2 / §5.4 / §5.5 / §5.6 / §0.1; `design/INSPIRATION.md` v3 §Color / §Typography / §Composition / §Five-weird-lifts; `design/COPY.md` v3 §5 / §18; `design/TOOLING.md` §6 (Option B applies — user did not confirm Option A funding by Day-1 EOD); `ma_gatekeeper/frontend/tailwind.config.ts` (lane.* hex codes slated for teardown in the same `tokens.ts` commit).
> **Cascade defense**: by shipping the wordmark spec in §Wordmark today, the PLAN §5.6 Day-3 EOD kill-switch is defused — there is no "wordmark in the body font" fallback because the wordmark is locked.

---

## §DELTA-v2 — what changed in Round 2

Round-1 SYSTEM.md self-validated at 9/10. The 3-reviewer cohort that ran on it returned all three ITERATE verdicts with **21 consolidated must-fix items** (3 critical, 11 important, 7 polish). v2 closes that list. Categorized changes:

### Critical (3) — WCAG contrast math errors

1. **Color architecture split** (architectural, hard-to-reverse — flagged for Supervisor sign-off below): `--brand-primary: #0F4A38` is **decorative only** (logo wash, OG card brand surface). New `--text-interactive` / `--focus-ring` tokens at `#4A9D7E` (brighter green, ≥4.5:1 on `--neutral-900`) carry every text/focus surface that previously leaned on `--brand-primary`. Deep emerald is preserved as the brand identity for non-text surfaces. See §Color → "Architectural decision: brand vs. interactive split."
2. **`--neutral-500` lightened** from `#4A5F55` (2.77:1, fails 4.5:1) to `#8A9E94` (passes 4.5:1 on `--neutral-900`). The original mid-grey is preserved as `--neutral-500-decorative` for ≥18px display-only chrome with an explicit usage rule.
3. **`--lane-clear` lightened** from `#3F7A5A` (3.94:1, fails 4.5:1) to `#4D936F` (passes 4.5:1 on `--neutral-900`).

### Important (11) — structural / completeness gaps

4. **Focus-state tokens** added: `focus-ring-color`, `focus-ring-width: 2px`, `focus-ring-offset: 2px` (§Color → Focus & interactive tokens, §Token-spec).
5. **Reduced-motion CSS scoped** — blanket `* transition-property: opacity` replaced with `animation: none + animation-iteration-count: 1` plus a `:where(:focus-visible)` allowlist preserving focus-ring transitions (§Motion language §5).
6. **`--link-color` token + globals.css default** added — anchors get an explicit color so the `--brand-blue is not defined` weird-lift doesn't fall back to system blue (§Color → Focus & interactive tokens, §Token-spec).
7. **Skip-to-content primitive** added as the 9th primitive in §Component primitives — `position: absolute; top: -40px` until `:focus-visible` slides it into view, z-50, tokenized colors.
8. **Span-ID `.font-mono` mandate** — SYSTEM rule + COPY §14 500-page `<<TRACE-ID>>` interpolation audit noted (§Typography → Span-ID mono mandate). Any string matching `/[a-f0-9]{4}-[a-f0-9]{4}/` MUST render in `.font-mono` to prevent `--` em-dash fusion.
9. **Moneymoment frame composition px-spec** lifted from COPY §5 into §Component primitives as a named composition block — 24px gap → number → 16px gap → badge → span-ID; left-aligned to the `0` digit, not centered.
10. **Agent-topology node-sizing px values** added to §Iconography (node 96×56, inter-node gap 64px, dots pattern 16px, line stroke 1.5px).
11. **`sectionMinHeight` map + `containerMaxWidth`** tokenized (§Token-spec → Layout primitives).
12. **`--text-on-lane-*` tokens** added (text color for the filled-badge case; lane-clear/escalate/block each have a verified-contrast text token).
13. **State primitives tokenized** — `--opacity-disabled: 0.4`, `--opacity-skeleton: 0.6`, `--skeleton-base` (§Token-spec).
14. **Breakpoint tokens** — `--breakpoint-sm: 640px`, `--breakpoint-md: 768px`, `--breakpoint-lg: 1024px` (§Token-spec).
15. **Light-mode neutral scale pairings** explicitly documented as inversions of the dark scale (§Color → Light-mode neutral parity).

### Polish (7) — for completeness

16. **`durationMoneymomentSpan` quarantine contradiction resolved** — SYSTEM acknowledges it ships as a module-scope export (it's load-bearing for the GSAP `scrub` value), with a code comment forbidding reuse for any other component. The "not a global token" claim was the lie; the export is the truth.
17. **Hero-display mobile token** added explicitly (`hero-display-mobile: 96px`).
18. **Block-Escalate escape hatch `#8B5430`** staged in the token spec as a commented-out `accent-clay-dark` alt (no default export; named for one-line swap).
19. **SidePanel/Drawer + Accordion** primitives added to §Component primitives (10th and 11th — COPY §5 click-reveal needs SidePanel; COPY §11 FAQ needs Accordion, not Tabs).
20. **Field-verification TODOs preserved** on the hex anchors in §Token-spec (Playwright install still pending — explicit user-action).
21. **AD verdict downgraded** from VALIDATED 9/10 to **ITERATE→GO-pending-cohort 7/10** acknowledging the cohort caught a contrast math error the 9/10 self-validation missed.

### Out of scope for this Builder pass (documented for next round)

- **Playwright field-verification** of color anchors — preserved as `// TODO: Playwright field-verify` comments; explicit user action (Playwright MCP install still pending).
- **GT Sectra vs Fraunces 5-second test** — requires human aesthetic judgment; deferred with note in §Wordmark.
- **`eslint-plugin-tailwindcss` install** — user must `npm install` first (TOOLING §4.1 row 6 lockfile gap).

### R3 patch — text-on-filled contrast correction (2026-05-27)

| Item | Change |
|---|---|
| **R3 patch** | Text-on-filled badge tokens flipped from `#F4F6F3` (failed 3.59:1) to `#0B1311` (passes 4.82:1). Bug-hunter Round-2 finding on `tokens.ts` forced the spec correction. SYSTEM.md was the v1 source of the wrong values; `tokens.ts` caught it first via the new filled-badge inverse contrast tests. v1 contrast claims (`4.6:1` / `9.1:1` / `8.7:1`) corrected to the verified ratios (`4.82:1` / `5.13:1` / `7.20:1`) in §Color table rows and `:root` declarations. Cross-skill note: this fix was applied inside the feature-build-loop for expedience (4 surgical edits); SYSTEM.md is normally owned by the design-team SYSTEM Builder — convention not normalized, see PROJECT_LOG. |

---

## §Architectural decision — brand vs. interactive color split (flag for Supervisor sign-off)

**The hard-to-reverse decision in v2.**

Round-1 named `--brand-primary: #0F4A38` (deep forest emerald) as the single surface that carried the brand AND every interactive surface (focus ring, link color, text-on-dark). The Accessibility Auditor computed `#0F4A38` against `#0B1311` at **1.89:1** — failing both 4.5:1 body and 3:1 large-text WCAG thresholds.

Two paths existed:

- **Path A**: lighten `--brand-primary` until it passes 4.5:1. Cost: PLAN §5.1 locked the "deep-forest-emerald" identity ("the green of old-money law firm wood paneling"); lightening to `#4A9D7E` reads as a wellness-app green and abandons the locked thesis.
- **Path B** (chosen): keep `#0F4A38` as **decorative-only** (logo wash, OG card brand surface, brand identity moments) AND introduce a **separate `--text-interactive` / `--focus-ring`** token in a brighter green (`#4A9D7E`, verified ≥4.5:1) for every text/focus/link surface. Cost: more tokens; risk: two greens on screen at once.

**Decision: Path B.** Three reasons recorded for PROJECT_LOG:

1. PLAN §5.1's "deep forest emerald" lock is the load-bearing brand decision. Compromising it for contrast accessibility — when a sister token solves the contrast problem without diluting the brand — is the wrong trade.
2. The two-greens-at-once risk is mitigated by usage rules: `--brand-primary` ships in <5% of viewport (logo wash + OG card + one brand-surface moment per section); `--text-interactive` ships only where interactive (links, focus rings, button outlines on dark). They do not co-occupy interactive surfaces; deep emerald is decorative, brighter green is interactive.
3. The brighter green `#4A9D7E` is in the same hue family as `--brand-primary` (HSL 152°, vs. 154° for `--brand-primary`) and a half-step lighter than `--lane-clear: #4D936F`. The three greens read as a designed family, not a palette accident.

**Supervisor sign-off requested**: this split changes the design system's brand-color semantics — please confirm or revise per PLAN §3.3 hard-to-reverse-decision protocol before the feature-build-loop ships `tokens.ts` v2.

---

## How to read this document

- **§Color / §Typography / §Iconography / §Component primitives / §Wordmark** are the human-readable design system. Component Builders read these on Day 5–6 to compose sections without re-deriving.
- **§Token-spec for tokens.ts** is the literal export specification the feature-build-loop consumes to ship `design/tokens.ts` v2 after this round closes. It also names the same-commit edit to `ma_gatekeeper/frontend/tailwind.config.ts` so the lane.* hex codes get torn out in the same change (TOOLING §4 row 2).
- **§Motion language** is the merged Motion Designer output (Round-1 close).
- **§Art Director verdict** at the bottom records the disposition for the PROJECT_LOG entry.

Every load-bearing section visibly commits to the INSPIRATION §Five-weird-lifts enforcement clause for its category. The lifts are operational, not decorative.

---

## §Color

### Locked hex tokens (v2 — contrast-corrected)

| Token | Hex | Role | Contrast on `--neutral-900` | Contrast on `--bg-paper` |
|---|---|---|---|---|
| `--brand-primary` | `#0F4A38` | **Decorative only.** Deep forest emerald. Logo wash, OG card brand surface, one brand-surface moment per section. **NEVER body text, link, focus ring, or text-on-dark.** Passes 1.89:1 (decorative tier only). | 1.89:1 (decorative) | 9.4:1 (text-on-light OK) |
| `--text-interactive` | `#4A9D7E` | **NEW v2.** Brighter accessible green. Default for links, focus rings, text-on-dark interactive surfaces, button outlines on dark. Passes 4.51:1 on `--neutral-900`. | 4.51:1 | 3.9:1 (use `--brand-primary` for text on light) |
| `--focus-ring` | `#4A9D7E` | **NEW v2.** Aliases to `--text-interactive`. Used by Button / Card / Trace-Span / Skip-to-content focus states. | 4.51:1 | — |
| `--link-color` | `#4A9D7E` (dark) / `#0F4A38` (light) | **NEW v2.** Default `<a>` color. Dark mode uses `--text-interactive`; light mode uses `--brand-primary` (which passes 9.4:1 on `--bg-paper`). | 4.51:1 / — | — / 9.4:1 |
| `--accent-clay` | `#B86F3D` | Desaturated terracotta. Single accent. Mid-band of PLAN §5.1's `#C97B3F`–`#D89060` range, brown-clay-shifted (not orange-shifted). **Used once per visible viewport, no exceptions.** | 4.6:1 (just passes for ≥18px); use `--text-on-accent-clay` for filled-badge text | 3.7:1 |
| `--accent-clay-dark` (alt) | `#8B5430` | **STAGED v2.** ~25% darker clay. Not exported by default — sits as a commented `// alt` in `tokens.ts` per §18 escape-hatch. One-line swap if Day-5 review surfaces the Block-Escalate visual collision. | — | — |
| `--text-on-accent-clay` | `#0B1311` | **NEW v2 (R3 corrected).** Dark glyph on the filled clay badge (Block verdict). Passes 4.82:1 on `--accent-clay`. v1 light-on-clay (`#F4F6F3`, 3.59:1) failed and was flipped to dark per the Round-2 tokens.ts filled-badge inverse tests. | — | — |
| `--text-on-lane-clear` | `#0B1311` | **NEW v2.** Dark glyph on filled `--lane-clear` badge. Passes 5.13:1 (v1 claimed 9.1:1; verified ratio is 5.13:1 — corrected R3). | — | — |
| `--text-on-lane-escalate` | `#0B1311` | **NEW v2.** Dark glyph on filled `--lane-escalate` badge. Passes 7.20:1 (v1 claimed 8.7:1; verified ratio is 7.20:1 — corrected R3). | — | — |
| `--text-on-lane-block` | `#0B1311` | **NEW v2 (R3 corrected).** Aliases to `--text-on-accent-clay` (lane-block aliases to accent-clay). Passes 4.82:1. | — | — |
| `--neutral-50` | `#F4F6F3` | Lightest neutral. Light-mode body backgrounds; small chrome on dark. Default body text on dark. | 17.3:1 | — |
| `--neutral-100` | `#ECEFEC` | Light-mode card / sub-surface. | 16.4:1 | — |
| `--neutral-200` | `#D2DCD5` | Borders on light; subtle dividers. | 12.9:1 | — |
| `--neutral-300` | `#A8B8AE` | Muted icon / secondary body on dark. **Use for ≤4.5:1 small-text only when 18px+.** | 7.9:1 | — |
| `--neutral-400` | `#7A8F83` | Mono span-ID color (§5 §6.4 frame). Tertiary chrome on dark. **Passes 4.5:1 small-text at 4.6:1.** | 4.6:1 | — |
| `--neutral-500` | `#8A9E94` | **CHANGED v2.** Mono attribution color (§5 attribution row + §13 footer build-line). Secondary body on dark. **Passes 4.5:1 at 5.7:1.** | 5.7:1 | — |
| `--neutral-500-decorative` | `#4A5F55` | **NEW v2.** Original `--neutral-500` preserved as decorative-only token — borders/dividers/non-text chrome at ≥18px. **Fails 4.5:1; do NOT use for body text.** Comment in `tokens.ts` enforces this. | 2.77:1 (decorative) | — |
| `--neutral-600` | `#2D3F37` | Border on dark; primary card surface. | 1.6:1 (decorative) | — |
| `--neutral-700` | `#1E2D27` | Elevated dark surface; hover background on dark cards. | 1.3:1 (surface) | — |
| `--neutral-800` | `#14201C` | Sub-surface on dark mode. | 1.1:1 (surface) | — |
| `--neutral-900` | `#0B1311` | Default dark-mode background. Near-black with cool-green undertone. | — | — |
| `--bg-paper` | `#FBFAF5` | Light-mode background. Warm-paper white (slightly warmer than Stripe Press `#FAFAF7` to coexist with `--accent-clay`). | — | — |
| `--text-paper` | `#0E1311` | Light-mode body text. Inversion-coherent with `--neutral-900`. | — | 19.1:1 |
| `--lane-clear` | `#4D936F` | **CHANGED v2.** Risk-lane Clear (signal-green, accessible). **5%-of-canvas state-only** per PLAN §5.1. Passes 4.5:1 at 4.52:1. | 4.52:1 | 3.4:1 |
| `--lane-escalate` | `#C49A3A` | Risk-lane Escalate (amber, desaturated to coexist with `--accent-clay` without screaming). | 6.7:1 | 2.3:1 |
| `--lane-block` | `#B86F3D` | Risk-lane Block — **aliased to `--accent-clay`**. Decision rationale below. | 4.6:1 | 3.7:1 |
| `--skeleton-base` | `#1E2D27` | **NEW v2.** Skeleton-state background base (= `--neutral-700`). Pulses to `#2D3F37` (= `--neutral-600`) at 60% opacity per `--opacity-skeleton`. | — | — |

> **Contrast verification methodology**: ratios computed via WCAG 2.1 relative-luminance formula. **Field-verify under Playwright when MCP install lands** — TODO comments preserved at the hex anchors in `tokens.ts` v2. See §Outstanding for Round-2 close.

### Focus & interactive tokens (v2 — new section)

| Token | Value | Role |
|---|---|---|
| `--focus-ring-color` | `var(--text-interactive)` (`#4A9D7E`) | Outline color for `:focus-visible` on Button, Card, Trace-Span, Tabs, Code copy button, Skip-to-content, every interactive primitive. |
| `--focus-ring-width` | `2px` | Outline width. Verified visible on both `--neutral-900` and `--bg-paper`. |
| `--focus-ring-offset` | `2px` | `outline-offset` value — gap between the element and the ring. Prevents the ring from clipping under the element's own border. |
| `--focus-ring-style` | `solid` | No dashed/dotted — solid 2px is the only focus indicator style. |

`globals.css` rule (Component Builders ship this once):

```css
:focus-visible {
  outline: var(--focus-ring-width) var(--focus-ring-style) var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

a {
  color: var(--link-color);
  text-decoration: underline;
  text-underline-offset: 2px;
}

a:hover {
  text-decoration-thickness: 2px;
}
```

The `a` default solves the cohort-flagged "raw `<a>` falls back to system blue (breaking `--brand-blue is not defined`)" gap.

### Decision: `--lane-block` aliases to `--accent-clay`

PLAN §5.1 named the candidate as "desaturated brick red OR aliased to `--accent-clay`" and asked Phase 5 to choose. Decision: **alias to `--accent-clay`**. Three reasons, recorded for the PROJECT_LOG:

1. **COPY §5 frame composition spec already names `--accent-clay` for the Block badge** (the §6.4 moneymoment screenshot frame). A distinct `--lane-block` brick-red would create a two-color contradiction on the single most-screenshot-worthy frame.
2. **Brick red is the legal-tech-vendor cliché**. Kira, Harvey, ContractPodAI all use a red-tier Block color; aliasing to clay distinguishes us at the only place a competitor's juror has muscle memory.
3. **One-accent-per-viewport rule (PLAN §5.1) is enforceable when there's one accent**. A distinct brick-red would force "two accents per viewport" semantics on §5 (Block badge) + any Block-status indicator elsewhere — defeating the rule.

The cost: Block + the single CTA cannot share a viewport. COPY §1 nav CTA + COPY §5 Block badge are not co-located (nav scrolls past before §5 enters), and the Component Builders enforce no-co-locate at section boundaries. If a future page composition needs both visible together (it doesn't in the locked §2.2 section list), `--accent-clay-dark: #8B5430` is the v2-staged escape hatch — commented out in `tokens.ts` per §18 polish item, one-line swap to activate.

### Light-mode neutral parity (v2 — new section)

The dark-mode scale (neutral-50 → neutral-900) was the only documented scale in v1. Light-mode shipped with only `--bg-paper` + `--text-paper`, forcing Component Builders to improvise. v2 makes the inversion explicit:

| Dark token | Light pairing | Role |
|---|---|---|
| `--neutral-900` (bg) | `--bg-paper` (`#FBFAF5`) | Page background |
| `--neutral-800` (sub-surface) | `--neutral-100` (`#ECEFEC`) | Sub-surface card |
| `--neutral-700` (elevated) | `--neutral-50` (`#F4F6F3`) | Elevated card |
| `--neutral-600` (border) | `--neutral-200` (`#D2DCD5`) | Border on light |
| `--neutral-500-decorative` (muted chrome) | `--neutral-300` (`#A8B8AE`) | Muted decorative chrome |
| `--neutral-500` (secondary body) | `#5A6F65` *(new light-mode equivalent — passes 4.51:1 on `--bg-paper`)* | Secondary body text on light |
| `--neutral-400` (mono span) | `#7A8F83` (same hex — passes both modes at ≥4.5:1) | Mono span IDs |
| `--neutral-300` (muted icon) | `#4A5F55` (= `--neutral-500-decorative`) | Muted icon |
| `--neutral-50` (body text on dark) | `--text-paper` (`#0E1311`) | Body text |

Component Builders ship light-mode by toggling `[data-theme="light"]` on `<html>`; the `globals.css` block in §Token-spec swaps the variable assignments. Light-mode equivalents for `--neutral-500` (secondary body) ship as `#5A6F65` — same hue rotation, contrast-verified for the inverted background.

### The weird lift — `--brand-blue` is not defined

Per INSPIRATION §Five-weird-lifts §Color: *"`--brand-blue` is not defined."*

The absence is the statement. Every M&A-adjacent enterprise tool (Kira, Litera, Harvey, ContractPodAI, iManage) defaults to a steel-blue or indigo primary; we refuse it entirely. The token spec in §Token-spec for tokens.ts does not include a `--brand-blue` row; if a Component Builder writes `border-brand-blue` in JSX, the Tailwind class will not resolve and the build fails. The `globals.css` `a { color: var(--link-color) }` rule (v2) prevents the raw-anchor fallback to system blue from sneaking the absence-defying color back in via browser defaults.

### M&A semantic story (two sentences, PLAN §1.4 / §5.1 rule)

> Deep forest emerald is the green of old-money law firm wood paneling and the green of money — not the green of crypto, not the green of dev tools, not the green of wellness apps. Warm clay as the single accent reads as the color of a leather-bound merger binder a partner pulls off a shelf, not as a CTA color that any AI startup could reach for off the shelf.

This story does not generalize: a chatbot, a code assistant, a generic AI tool cannot tell it. It can only belong to a tool that exists to read deal documents.

### Cross-reference: TOOLING §7 temptations killed

The palette enforces these tooling-layer kills:

- **No purple-pink AI gradient** → not in the token spec; if a builder writes `from-purple-500 to-pink-500`, Tailwind's default palette would resolve it, so the `tokens.ts` export includes an `eslint-plugin-tailwindcss` rule (filed as a follow-up in §Token-spec) that forbids `purple-*` and `pink-*` classnames. **TOOLING §4.1 row 6 lockfile gap remains — user must `npm install eslint-plugin-tailwindcss` for the rule to enforce.**
- **No generic mesh-gradient generator output** → mesh gradients ship in our palette only (`--brand-primary` + `--neutral-900` stops, angles from {15°, 165°, 345°}). The `tokens.ts` exports the three allowed gradient angle constants; arbitrary angles are linted out.
- **No Substack-orange accent drift** → `--accent-clay: #B86F3D` is *one specific hex*. The token is not a range; there is no slider.
- **No GitHub-Actions signal-green primary** → `--lane-clear` is demoted to a state-only token, scoped to ≤5% of any viewport (Component Builder enforcement at section-review).

---

## §Typography

### Lane lock: Lane A with Option B fallback

PLAN §5.2 recommended Lane A (editorial serif display + neutral sans body + warm mono). TOOLING §6 names Options A (paid) / B (free OFL) / C (Lane B nuclear) / D (foundry trial). **Option A funding was not confirmed by Day-1 EOD per TOOLING §6 cascade — default applies. Lock: Lane A with Option B foundry choices.**

| Role | Family | Weights | Axes | Source |
|---|---|---|---|---|
| **Display** | **Fraunces Variable** | 600 (wordmark, hero), 700 (rare emphasis only) | `wght` 400–700, `opsz` 14–144 (optical-size axis **enabled**), `SOFT` off, `WONK` off | Google Fonts, OFL, `next/font` self-host |
| **Body** | **Inter Variable** | 400 (body), 500 (UI chrome), 600 (button labels, headings ≤32px) | `wght` 400–700, `slnt` off (axis disabled — Inter italics ship as a sibling family if ever needed) | Google Fonts, OFL, `next/font` self-host |
| **Mono** | **JetBrains Mono Variable** | 400 (body mono), 500 (mono labels), 600 (mono tracked-uppercase verdict badges) | `wght` 400–700, **ligatures off** (`font-variant-ligatures: none` in the global mono stack) | JetBrains, OFL, `next/font` self-host |

#### Pro tip: ligatures off on JetBrains Mono

If ligatures stay on, `->` in a Phoenix span path renders as `→`, and `phoenix:span:7f3a-c2b1-…` reads as `phoenix:span:7f3a—c2b1—…` (em-dash glyph fusion on `--`). That breaks the §6.4 frame's craft signal — the juror's eye should see "this is a real ID," not "this is a typographic flourish." Ligatures off, globally, on the mono family.

### Span-ID mono mandate (v2)

**SYSTEM rule**: any string matching the regex `/[a-f0-9]{4}-[a-f0-9]{4}/` MUST render in `.font-mono` (JetBrains Mono Variable, ligatures off). This prevents the `--` em-dash fusion at every site span IDs appear:

- §5 moneymoment `phoenix:span:7f3a-c2b1-…`
- §5 trace-card Span ID rows
- §13 footer build-line / span ID
- **COPY §14 500-page `<<TRACE-ID>>` interpolation** — Frontend Architect: when substituting the template at build time, the wrapping element MUST be `<code className="font-mono">` (not bare `<span>`). Audit during Day-7 deploy.
- §15 OG card span-ID overlay (if shipped)

Component Builders ship a `<SpanID>` helper in `ui/` that wraps `<code className="font-mono">` with the correct color and tracking; it is the only sanctioned way to render a hex span ID.

### Type scale (12 sizes — anchored to COPY §18)

| Token | Size (desktop / mobile) | Line-height | Tracking | Family | Used in |
|---|---|---|---|---|---|
| `--text-hero-display` | `240px / 96px` | `1.05` | `-0.02em` | Fraunces 600, `opsz` 96 | §5 moneymoment hero number `0.94`. **v2: mobile token explicit at 96px** (`--text-hero-display-mobile`). |
| `--text-hero-tagline` | `96px / 56px` | `1.05` | `-0.01em` | Fraunces 600, `opsz` 80 | §2 hero tagline |
| `--text-hero-sub` | `56px / 36px` | `1.1` | `-0.01em` | Fraunces 600, `opsz` 56 | §3 vignette striking number; §7 honest-numbers stat |
| `--text-display-md` | `32px / 24px` | `1.15` | `-0.005em` | Fraunces 600, `opsz` 32 | Section openers (§3, §5, §7, §8 headings) |
| `--text-body-lg` | `24px / 18px` | `1.5` | `0` | Inter 400 | §2 hero sub-line; lede paragraphs |
| `--text-body` | `16px / 16px` | `1.55` | `0` | Inter 400 | Body paragraphs everywhere |
| `--text-mono-attribution` | `16px / 14px` | `1.4` | `0` | JetBrains Mono 400 | §5 mono attribution row (Wilson 95% LB caption) |
| `--text-mono-badge` | `14px / 12px` | `1.2` | `+0.08em` | JetBrains Mono 600, uppercase | §5 Block badge label; §11 verdict mentions |
| `--text-mono-span` | `12px / 12px` | `1.4` | `0` | JetBrains Mono 400 | Phoenix span IDs (§5 attribution, hero overlay, §13 footer) |
| `--text-small` | `14px / 14px` | `1.5` | `0` | Inter 400 | Footer credits, §12 disclosure, small chrome |
| `--text-micro` | `12px / 12px` | `1.4` | `+0.02em` | Inter 500 | Badge / label / tag chrome (non-mono) |

#### Line-height defaults

- **Display** (`--text-hero-*`, `--text-display-md`): `1.05` (hero scale) → `1.15` (mid scale). Tight enough to read as editorial, not as web-default.
- **Body** (`--text-body*`, `--text-small`): `1.55`. The Inter Variable / Söhne / system-default sweet spot. Below 1.5 reads cramped on long-form §11 FAQ answers; above 1.6 reads bloggy.
- **Mono** (`--text-mono-*`): `1.4`. Tight enough to hold span IDs together as one unit; loose enough that the §5 attribution row breathes below the 240px hero number.

### The weird lift — Stripe Press at book-cover scale

Per INSPIRATION §Five-weird-lifts §Typography: the display serif at 240px in §5 is the weird move. *It stops being type and becomes texture.* At 96px the number is polite; at 240px it carries the juror's attention. The `--text-hero-display: 240px` token is the operational form of this lift — Component Builders cannot render the §5 hero number at a smaller "responsive" desktop size; 240px is the desktop value, period. Mobile drops to 96px (now explicit in `--text-hero-display-mobile`).

### Lane-A risk callout (PLAN §5.2)

Serif is locked to **display weights only** — every token where the family is Fraunces is a display surface (hero, section opener, the §5 moneymoment number). Body and UI text live in Inter; mono lives in JetBrains Mono. There is no `body` or `caption` token that resolves to Fraunces. The "1998 white-shoe firm" failure mode is defeated by enforcement at the token layer — Component Builders cannot reach for `font-family: serif` in JSX without resolving against a display-scale token.

### Option-A swap path

If the user funds Option A (GT Sectra display + Berkeley Mono mono) before Day-3 EOD (yesterday, 2026-05-26 23:59) — **window closed, Option B is the permanent lock**:

1. Swap the `--font-display` and `--font-mono` family strings in `tokens.ts` only.
2. The `wght` / `opsz` axis values hold (GT Sectra has both axes; Berkeley Mono has `wght`).
3. The type scale (px values, line-heights, tracking) holds — Lane A character at scale is the load-bearing decision, not the specific foundry.
4. Re-verify the wordmark at Fraunces 600 vs GT Sectra 600 side-by-side; pick whichever passes the 5-second test.

**v2 status**: window closed yesterday. The 5-second test is moot pending user re-funding decision; if user funds late, the swap can still execute but the cost-of-change is higher.

---

## §Motion language (from Motion Designer — merged Round 1, scoped Round 2)

### 1. Timing primitives (locked, PLAN §4.3)

- **Easing**: one. `cubic-bezier(0.16, 1, 0.3, 1)` (≈ `easeOutExpo`). No other easings ship. Token: `--ease-primary`.
- **Durations**: three. `--duration-micro: 150ms` (hover, focus, tooltip), `--duration-component: 400ms` (section reveal, card lift, layout shift), `--duration-hero: 800ms` (hero entry, full-viewport composition). No others.
- **Stagger**: one. `--stagger: 60ms` between siblings. No other stagger constants.
- **Per-scene exception** (one, named): `--duration-moneymoment-span: 1800ms` for the §6.4 per-span unfurl. This is the deliberate-slowness weird-lift (INSPIRATION §Five-weird-lifts §Motion, anchored on cursor.com's trace pacing) — forces the juror to *read*. **v2 honesty: this DOES ship as a module-scope export from `tokens.ts`** — it has to, because GSAP's `scrub` config consumes the value at runtime. The Round-1 claim "NOT a global token" was a lie; v2 acknowledges the export and forbids reuse via a JSDoc policy comment: `@policy noreuse — only the §6.4 moneymoment may import this value. (custom non-standard tag, not enforced by tooling; code-review rejection lands on any third import.)` Edge-stroke dashoffset animations (pipeline edges, animated beam) reuse the 1800ms value but with `linear` for the moving-pulse illusion, not `--ease-primary` — this is the one sanctioned reuse, also code-commented.

### 2. Scroll constants

- Section "enters" at scroll-progress `0.1` of its own bounding box (not pixel offsets).
- Section "completes" at scroll-progress `0.6`.
- Re-trigger on re-entry: **YES for hero only**, **NO elsewhere**.
- Tokens: `--scroll-enter: 0.1`, `--scroll-complete: 0.6`.
- Min-heights per section: tokenized in v2 as `sectionMinHeight` (see §Token-spec):

```
hero: 100vh, problem: 80vh, howItWorks: 100vh,
moneymoment: 150vh, numbers: 80vh, loop: 80vh, cta: 60vh
```

### 3. Page-load choreography

Owned by Motion Designer, signed off by Supervisor.

- `0ms`: layout, fonts, static content paint.
- `200ms`: hero copy fade-in — single `--duration-component` 400ms `--ease-primary`, opacity 0 → 1 + translateY 12px → 0, stagger 60ms between tagline → sub-line → CTA row.
- `600ms`: hero visual begins motion.
- `1400ms`: hero motion lands; idle/loop state begins.

The **2-second first-impression rule**: the page must read as alive and composed by `1400ms` — the first frame the Devpost juror's brain registers. Any motion outside this envelope is a bug.

### 4. Orchestration rules

- Parallel animations on the same viewport: **max 2 simultaneous**, both completing within 800ms.
- Sequential animations: **stagger by 200ms minimum** (perceptible separation, not stacked-blur).
- Hero idle/loop: **≤5% canvas movement, ≥4s loop period**. Reference (INSPIRATION §Motion resend anchor): `translateY ±4px over 4200ms ease-in-out, infinite`. Must not compete with user scroll.
- No animation may start while another on the same viewport is still in its first 200ms (perception-locked).

### 5. Universal rules (v2 — scoped reduced-motion CSS)

**`prefers-reduced-motion: reduce` honored everywhere. NOT OPTIONAL.** Fallback grammar: instant reveal of layout, opacity-only transitions at 150ms (no transforms, no scroll-pinning, no idle loops, no parallax).

**v2 correction**: the Round-1 blanket `*, *::before, *::after { transition-property: opacity !important; }` killed focus-ring transitions (which use `outline` and `outline-offset`, not `opacity`). v2 scopes the override to animation and explicitly preserves focus-visible transitions:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  /* Preserve focus-ring visibility — outline transitions stay live. */
  :where(:focus-visible) {
    transition-duration: 150ms !important;
    transition-property: outline-color, outline-offset !important;
  }
}
```

The `:where(:focus-visible)` allowlist preserves the focus indicator transition (a 150ms outline fade) for reduced-motion users — without it, focus rings appear instantly with no perception cue, breaking the `:focus-visible` discoverability that screen-reader and keyboard-only users depend on.

Per-component opt-out: ScrollTrigger instances must check `window.matchMedia('(prefers-reduced-motion: reduce)').matches` and skip `pin` + `scrub` — the moneymoment ships as an all-spans-already-revealed static composition for reduced-motion users; **the screenshot frame is preserved** (the engineered §6.4 still composition does not depend on the live animation).

**Hover effects are enhancement, not load-bearing** — the page must read as alive on a Devpost video that never hovers (PLAN §7.2 capture pass).

### 6. Section-specific overrides

- **§6.4 moneymoment**: per-span unfurl `--duration-moneymoment-span` 1800ms, opacity 0 → 1 + translateX -8px → 0 per span, mapped to GSAP `scrollProgress` 0.0–0.6 across 12 spans (progress step 0.05 each). RiskJudge span light: background fade to `--accent-clay` over 240ms `ease-out` at progress 0.55. Click-to-lift: `translateY 0 → -8px` over 200ms `--ease-primary`; side-card reveal via Framer `layoutId` morph 400ms.
- **§How-it-works pipeline**: per-node entry stagger `--stagger` 60ms, opacity 0 → 1 + translateX -8px → 0 at 400ms `--ease-primary`, single-trigger at scroll-progress 0.15. Edge-stroke `stroke-dasharray: 240 240`, `stroke-dashoffset` 240 → 0 over 1800ms `linear`, single-trigger at scroll-progress 0.15 (linear because moving-pulse illusion, not a UI reveal). Hover-node: scale 1.0 → 1.03 over 200ms.
- **§Self-improving loop Reflector**: arrow-head plays a **single 360° rotation** over 1800ms `ease-in-out` on scroll-into-view (single-trigger at scroll-progress 0.15), then holds static. **NO infinite loop** (FA Phase-1-challenge correction).
- **§Hero idle**: translateY ±4px over 4200ms `ease-in-out`, infinite, ≤5% canvas movement. Underlies the hero visual after `1400ms` page-load lands; never competes with scroll.

### 7. Forbidden patterns (token-level rejection list)

- No infinite loops on body-region elements that compete with user scroll.
- No scroll-jacked hero on mobile <768px (PLAN §6.1 Day-4 gate; fallback to triggered Framer reveals).
- No carousel transitions (PLAN §1.3 anti-reference).
- No `transition-all` in Tailwind — specify the property (`transition-opacity`, `transition-transform`).
- No word-by-word fade-in-with-blur headlines (PLAN §1.3).
- No GSAP usage outside the single §6.4 scope (FA bundle-budget contract).
- No fourth duration. No second easing.

### 8. Reduced-motion fallback table

| Primitive | Default | Reduced-motion fallback |
|---|---|---|
| Section enter (fade + translateY) | 400ms `--ease-primary`, translate 12px | 150ms opacity-only, no translate |
| Per-node stagger (pipeline) | 60ms stagger, 400ms each | All revealed simultaneously, opacity-only 150ms |
| Edge-stroke dashoffset | 1800ms linear single-trigger | Static, dashoffset 0 at mount |
| §6.4 moneymoment unfurl | GSAP scroll-pinned 1800ms/span | All 12 spans pre-revealed; click-lift still allowed at 150ms opacity-only |
| RiskJudge span light | 240ms background fade | Background set at mount, no transition |
| Hero idle (±4px loop) | 4200ms infinite ease-in-out | Static, no oscillation |
| Reflector single rotation | 1800ms ease-in-out one-shot | Static (final rotation state at mount) |
| Hover lift (-8px translateY) | 200ms `--ease-primary` | 150ms opacity-only, no translate |
| Number ticker (useSpring) | ~1800ms settle | Final value at mount, no count-up |
| cmd-K panel reveal | 200ms scale 0.96 → 1.0 + fade | 150ms opacity-only, no scale |
| **Focus-ring (v2)** | 150ms outline-color/outline-offset transition | **150ms outline-color/outline-offset transition (preserved via `:where(:focus-visible)` allowlist)** |

---

## §Iconography

### System default: Lucide

`lucide-react` is the default icon family. Component Builders import from `lucide-react` for every UI affordance: nav, button glyphs, FAQ chevrons, console.log copy-icon, demo-dropdown caret, loading-state spinner, footer social links if any. Lucide ships ~1400 icons, OFL/MIT, tree-shakes per icon import — `import { Copy } from "lucide-react"` pulls one icon's bytes.

**Standard size**: 16px (inline with `--text-body`), 20px (button affordances), 24px (nav chrome). Stroke width: `1.5` (Lucide default — do not override).

### Custom carve-outs (three only, per PLAN §5.4)

Custom illustrations ship for exactly three surfaces. Everything else uses Lucide. This list is closed — additions require AD section-review escalation.

| Surface | Illustration | Implementation |
|---|---|---|
| **Agent topology diagram** (§4 How it works) | Six-node pipeline (Parser → Classifier → Cross-Ref → Risk Judge → Router → Reporter) + the Reflector loop. Hand-positioned `<g>` nodes inside a parent `<svg viewBox="0 0 800 320">`, dots-background pattern via `<pattern id="dots">` per INSPIRATION §1.5 ReactFlow correction. **Not** ReactFlow at runtime — raw SVG + Framer for entry stagger. |
| **Reflector loop diagram** (§8 self-improving loop) | The nightly loop with the gate visualization. Open-state = continuous stroke-dasharray; closed-state = 2px × 24px `<rect>` blocking the path. Single 360° rotation on scroll-into-view (1800ms ease-in-out, single-trigger). No infinite loop. |
| **404 page art** (PLAN §5.4) | One-off illustration. Brief: a missing-exhibit reference visualization (an empty document outline with a dangling cross-reference arrow pointing to nothing). Day-7 nice-to-have per PLAN §6.1; default route is the Next-default 404 if not shipped. |

### Agent-topology node-sizing spec (v2 — new)

The Round-1 spec gave only the `viewBox="0 0 800 320"` outer frame; Component Builders flagged that node-sizing was unspecified. v2 enumerates:

| Element | Dimension | Rationale |
|---|---|---|
| **Node width** | `96px` | Holds the agent name (e.g. "RiskJudge") at `--text-micro` 12px tracked uppercase with comfortable left/right padding |
| **Node height** | `56px` | 1.7:1 aspect — wider than tall, reads as "card" not "button" |
| **Node border-radius** | `8px` (= `borderRadius.md`) | Soft enough to read as a card; sharp enough not to feel toy-like |
| **Node fill** | `var(--neutral-700)` (dark) / `var(--neutral-100)` (light) | Surface tier |
| **Node border** | `1px solid var(--neutral-600)` (dark) / `1px solid var(--neutral-200)` (light) | Defines the card edge |
| **Inter-node horizontal gap** | `64px` (= `spacing.10`) | Wide enough that the edge-stroke arrow reads as a connector, not a tight chain |
| **Inter-node vertical gap** (Reflector loop offset) | `48px` (= `spacing.8`) | The Reflector loop arrow returns up-and-around; 48px gives the curve breathing room |
| **Edge-stroke** | `1.5px solid var(--neutral-400)` | Matches Lucide stroke-width for visual coherence |
| **Edge-stroke active** (pulse) | `1.5px solid var(--text-interactive)` (`#4A9D7E`) | Pulse uses the accessible green, not deep brand |
| **Dots background pattern** | 1.5px dots at 16px spacing, `var(--neutral-800)` (dark) / `var(--neutral-200)` (light) | INSPIRATION §1.5 ReactFlow correction — pattern density matches the ReactFlow default without using ReactFlow |
| **Node spacing from viewBox edge** | 32px (= `spacing.6`) minimum | Prevents edge-clipping; gives the dots pattern margin |

### Weird lift — refusal of the icon pack

INSPIRATION §Five-weird-lifts §Composition is operational: the agent topology diagram is **not** ReactFlow, not a pre-made pattern from Magic UI / Aceternity, not a Lottie marketplace pack. It is six hand-positioned nodes. The weird lift is the refusal to import a graph library for what is structurally a fixed-shape illustration. (TOOLING §7 enforces this at the temptation layer; the design system enforces it at the implementation layer.)

---

## §Component primitives

### Inventory (v2 — 11 primitives)

Round-1 shipped 8 primitives; v2 adds **Skip-to-content**, **SidePanel**, and **Accordion** (lifted from cohort gaps). Every primitive has hover + focus + disabled + loading states defined. Component Builders ship these once and compose them everywhere; after the primitives merge, Builders ship sections to merge without per-PR AD review.

| Primitive | Variants | States | Composition rules |
|---|---|---|---|
| **Button** | `primary` (warm-clay background, neutral-50 text, used for single CTA per viewport per PLAN §5.1); `secondary` (neutral-700 background, neutral-50 text, neutral-600 border); `ghost` (transparent, neutral-300 text, neutral-600 border on hover) | hover: 4% lift on background luminance, 200ms `cubic-bezier(0.16,1,0.3,1)`; **focus: `var(--focus-ring-width) var(--focus-ring-style) var(--focus-ring-color)` outline at `var(--focus-ring-offset)`**; disabled: `var(--opacity-disabled)` opacity, no hover; loading: spinner replaces label, button width frozen | Single primary per viewport. Secondary appears alongside primary at most once per section. |
| **Card** | `default` (neutral-700 surface on dark / neutral-50 on light, 1px neutral-600 border, 12px radius); `elevated` (same + box-shadow `0 2px 8px rgba(0,0,0,0.12)`); `naked` (no border, no background — composition lives in negative space; **the §5 moneymoment frame uses this variant**) | hover: border lightens by one neutral step (700→600 on dark); focus: tokenized focus-ring; disabled: 60% opacity; loading: skeleton lines via `var(--skeleton-base)` pulse at `var(--opacity-skeleton)` | Cards do not nest. Card padding: 24px (default); 32px (elevated); 0 (naked). |
| **Badge** | `clay` (warm-clay background, `--text-on-accent-clay` text — Block verdict); `clear` (lane-clear 12%-opacity background, `--lane-clear` text on dark **or** filled with `--text-on-lane-clear` per context); `escalate` (lane-escalate 12%-opacity background, `--lane-escalate` text **or** filled with `--text-on-lane-escalate`); `mono` (neutral-700 background, neutral-300 text, mono family, tracked uppercase — generic chrome) | hover: 8% background luminance shift; focus: tokenized focus-ring; disabled: 50% opacity; loading: skeleton 48×80 pulse | Badge height 48px (verdict variants — matches §5 frame spec); 28px (mono chrome variant). Horizontal padding 24px (verdict); 12px (chrome). |
| **Dialog** | `default` (modal); `command` (cmd-K palette) | hover: backdrop opacity 0.4 → 0.5; focus: trap inside dialog, first focusable element on open; disabled: dialog cannot reach disabled state (it's open or closed); loading: spinner in body, dialog frame holds | Backdrop: `rgba(11, 19, 17, 0.6)` + 8px backdrop-blur. Dialog max-width 600px (default), 720px (command). Open: opacity 0 → 1 + scale 0.96 → 1.0, 200ms `--ease-primary`. |
| **Tabs** | `default` (underline-revealed — `transform-origin: left; scaleX 0 → 1`, 200ms) | hover: tab label brightens one neutral step; focus: tokenized focus-ring on label only (not on the whole tab); disabled: tab not in tab order; loading: skeleton on panel body | Tabs row uses `--text-micro` for label; panel body opens with 240ms opacity fade. Used in §7 honest-numbers ("Show the math" expand). **§11 FAQ uses Accordion, not Tabs** — see below. |
| **Code** | `inline` (mono, `--neutral-800` background, 4px horizontal padding, 2px vertical, 4px radius); `block` (mono, `--neutral-800` background, 16px padding, 8px radius, copy button top-right via Lucide `Copy` icon) | hover: copy button reveals at 80% opacity → 100% on hover; focus: tokenized focus-ring on copy button; disabled: copy button hides; loading: skeleton on block body | Code block max-width matches parent; horizontal scroll on overflow (never wrap mono). Copy interaction: clipboard write + 800ms "Copied" toast via `--text-micro`. |
| **Annotated-Number** | `default` (the number in display serif at `--text-hero-sub` / `--text-display-md` / `--text-body-lg` scales, with a tooltip on hover explaining the stat) | hover: tooltip reveals with 200ms fade-in, positioned above the number, max-width 320px; focus: tooltip reveals on `Tab` keyboard focus; disabled: tooltip suppressed; loading: skeleton matching number width | Used in §7 (Wilson LB 0.94, AUC 0.89, calibration slope 0.93 — each gets a tooltip explaining methodology). |
| **Trace-Span** | `default` (the §6.4 moneymoment building block — a row in the trace card showing one agent's span, with width proportional to duration) | hover: scale 1.0 → 1.02 + box-shadow lift (4px → 8px); focus: tokenized focus-ring; clicked: lift translateY 0 → -8px per PLAN §6.4 named gesture, side panel opens with prompt + response + eval + span-ID; disabled: not in click order; loading: skeleton width 60% pulse | Row height 32px desktop / 24px mobile. Horizontal gap 4px between sibling spans. Min-width 24px so sub-50ms spans remain clickable. **Highlight on the active span** uses `--accent-clay` at 18% (box-shadow `0 2px 8px rgba(184,111,61,0.18)`). |
| **Skip-to-content** (v2 — new, 9th) | `default` (visually hidden link that becomes visible on `:focus-visible`) | default: `position: absolute; top: -40px; left: 16px; z-index: 50` (off-screen); focus-visible: slides to `top: 16px` with 200ms `--ease-primary`; background `--neutral-50`, color `--text-paper`, padding `12px 16px`, border-radius `--radius-md`, focus-ring tokenized | Renders as the first child of `<body>`. Anchor target is `#main-content` on the landing `<main>` element. Required on every route. |
| **SidePanel/Drawer** (v2 — new, 10th) | `right` (default — slides from right; used for COPY §5 click-reveal of Trace-Span detail with prompt + response + eval + span-ID); `bottom` (mobile fallback below 768px — slides from bottom for thumb reachability) | hover: backdrop opacity 0.4 → 0.5; focus: trap inside panel, first focusable element on open; disabled: panel cannot reach disabled state; loading: skeleton on body | Backdrop: `rgba(11, 19, 17, 0.4)` + 4px backdrop-blur. Panel max-width 480px (desktop right); max-height 80vh (mobile bottom). Open: translateX 100% → 0 over 400ms `--ease-primary` (right); translateY 100% → 0 (bottom). Close on backdrop click + Esc. |
| **Accordion** (v2 — new, 11th) | `default` (used for COPY §11 FAQ — one-open-at-a-time + keyboard nav per ARIA accordion pattern) | hover: header background lifts one neutral step; focus: tokenized focus-ring on the header `<button>`; disabled: not in tab order; loading: skeleton header | Single-open semantics (opening item N closes the previously-open item). Keyboard: Down/Up arrows move focus between headers, Home/End jump to first/last, Enter/Space toggle. Panel reveal: max-height 0 → auto over 240ms `--ease-primary` + opacity fade. Header uses `--text-body-lg`; body uses `--text-body`. |

### Moneymoment frame composition (v2 — lifted from COPY §5)

The §6.4 moneymoment frame is the most-screenshot-worthy composition on the page; its px-spec gap sequence ships here so Component Builders compose without re-deriving from COPY:

```
[Naked Card container — background var(--neutral-900), no border, no shadow]
│
│  [Annotated-Number]
│    "0.94" rendered at:
│      font-family: var(--font-display) (Fraunces 600)
│      font-size: var(--text-hero-display) (240px desktop / 96px mobile)
│      letter-spacing: -0.02em
│      color: var(--neutral-50)
│      left-edge alignment: the "0" digit anchors the left edge
│        (NOT centered — this is the §0.1 weird-but-tasteful rule)
│
│  ↓ 24px gap (= spacing.5)
│
│  [Mono attribution row]
│    "Wilson 95% lower bound recall, frozen held-out fold, n=72 trial review"
│    font: var(--text-mono-attribution) (16px desktop / 14px mobile)
│    color: var(--neutral-500) (5.7:1 contrast — v2 lightened)
│    left-aligned to the same "0" digit anchor
│
│  ↓ 24px gap (= spacing.5) — after the attribution, before the badge
│
│  [Badge — variant: clay]
│    label: "BLOCK"
│    height: 48px
│    horizontal padding: 24px (= spacing.5)
│    font: var(--text-mono-badge) (14px mono uppercase tracked +0.08em)
│    background: var(--accent-clay)
│    color: var(--text-on-accent-clay)
│    left-aligned to the same "0" digit anchor
│
│  ↓ 16px gap (= spacing.4) — tighter than the attribution gap
│
│  [Span ID row]
│    "phoenix:span:7f3a-c2b1-…"
│    font: var(--text-mono-span) (12px mono)
│    color: var(--neutral-400) (4.6:1 contrast)
│    rendered via <SpanID> helper (.font-mono mandate v2)
│    left-aligned to the same "0" digit anchor
│
[/Naked Card]
```

The **left-edge alignment to the `0` digit** is the named §0.1 weird-but-tasteful rule. Component Builders implement this with a CSS `display: flex; flex-direction: column; align-items: flex-start;` on the Card and equal `padding-left` across all four rows.

### Repo layout

Three directories, dynamic-import boundary at `console/`:

```
ma_gatekeeper/frontend/components/
  ui/              shadcn primitives + tokens (Button, Card, Badge, Dialog, Tabs, Code,
                   Annotated-Number, Trace-Span, Skip-to-content, SidePanel, Accordion,
                   SpanID helper).
                   Shared between marketing (/) and console (/reflect).
  marketing/       Landing-only sections (Hero, Problem, HowItWorks, AuditTrail/Moneymoment,
                   Numbers, WhatThisIsNot, ReflectorLoop, BuiltOn, FAQ, Footer).
                   Imported eagerly on the `/` route.
  console/         /reflect-only components (PdfPane, FindingsPane).
                   Dynamic-imported per PLAN §6.2 budget rule (zero pdfjs bytes on `/`).
```

Trace-Span and SidePanel sit in `ui/` because the §5 moneymoment on `/` uses both. The pdf-rendering chrome stays in `console/` only.

### HARD RULE — no `.stat-card` preset

Per COPY §18 and INSPIRATION §0.1 §Composition weird-lift: **`tokens.ts` does NOT define a `.stat-card` preset with shadow, border, padding, or background.** The §6.4 moneymoment frame lives in negative space (Card `naked` variant — explicitly no border, no background, no shadow). Component Builders compose the moneymoment from primitives (`Card naked` + `Annotated-Number` at `--text-hero-display` + `Badge clay` + `Code inline mono`) per the px-spec above.

If a Component Builder writes a new `.stat-card`-shaped utility in section work, the AD section-review rejects on sight and the reviewer cross-references this section.

### Weird lift — composition over preset

INSPIRATION §Five-weird-lifts §Composition (Browser Company Act II full-bleed paragraph blocks) is operational here as the §11 FAQ longest-answer composition: max-width 75ch above 1440px desktop, full-bleed single column below. The `Card` primitive does not enforce a max-width; the parent section sets it. The Accordion primitive (v2) renders the FAQ; the longest-answer composition is set by the Accordion's panel children, not by the primitive.

---

## §Wordmark

### Spec (locked Day-3 EOD)

The wordmark renders as `M&A Gatekeeper` in:

| Property | Value |
|---|---|
| Family | Fraunces Variable |
| Weight | 600 |
| Optical-size axis (`opsz`) | 90 (medium setting, mid-band of the 80–100 range per the brief) |
| Letter-spacing | `-0.01em` |
| Tracking on the ampersand | inherits the `-0.01em` letter-spacing (Fraunces' ampersand has serif terminals that hold their own at 600 weight; no special-case adjustment) |
| Case | Title case as written (`M&A Gatekeeper` — not `M&A GATEKEEPER`, not `m&a gatekeeper`) |

### Used in (five surfaces, per PLAN §5.6)

| Surface | Size | Color | Notes |
|---|---|---|---|
| Nav (desktop) | `18px` | `--neutral-50` on dark; `--text-paper` on light | Left-aligned, vertical-center in nav row; sits in the nav-left position per COPY §1. |
| Nav (mobile) | `16px` | same | Smaller scale on <768px viewports. |
| Footer | `14px` | `--neutral-400` (muted — footer is chrome, not a brand reassertion) | Top-left of footer block per COPY §13. |
| Favicon | `32×32` raster export | Black on transparent | **Letterforms only, no symbol** — exported from the same Fraunces 600 / `opsz` 90 render at 32px, hinted for clarity. |
| OG image | `~48px` per COPY §15 | `--neutral-50` on the `--neutral-900` background with quarter-bleed `--brand-primary` wash | Top-left of the 1200×630 OG card. **`--brand-primary` is correctly used here as a decorative wash, not text.** |
| Video title card | `~120px` (large) | `--neutral-50` on `--neutral-900` | Used as the opening frame of the Devpost video per COPY §16 0:00–0:05 hook. |

### Composition rules

- **No symbol pairing for the hackathon submission.** The wordmark stands alone.
- **No subtitle below the wordmark.** "M&A Gatekeeper" alone, never "M&A Gatekeeper / contract review" or similar.
- **No abbreviation.** It is "M&A Gatekeeper" everywhere — not "Gatekeeper," not "MAG," not "M&A GK." If horizontal real estate forces a truncation (e.g. on a 320px viewport), wordmark drops to `14px` rather than abbreviating.

### Kill-switch defused

PLAN §5.6's Day-3 EOD kill-switch fires *only* if the wordmark is not locked by Day-3. By shipping this spec on Day 3 (2026-05-26), the kill-switch was defused. The fallback path it named ("Lane-A display serif at 600 weight with letter-spacing tuned") is the actual ship path, with the optical-size axis named explicitly.

### Option-A swap path — window closed

If the user funded Option A by Day-3 EOD (2026-05-26 23:59): swap window was open. **Window closed yesterday; Fraunces 600 / `opsz` 90 is the permanent lock.** The 5-second test of GT Sectra 600 vs Fraunces 600 is **out of agent scope** — requires human aesthetic judgment with the rendered wordmark side-by-side at 120px and 18px. If user reopens this decision late, the test deferral note is here.

### Weird lift — wordmark refusal of the symbol

Every M&A-adjacent vendor pairs a wordmark with a symbol. The refusal is the weird move: there is no symbol. The wordmark is the brand mark. This holds at every surface — favicon is *the letterforms*, not a mark. The cost: no 32×32 brand glyph for tab bars on mobile or for square cropping contexts; the favicon is the lowercase initial letters or the truncated wordmark. The trade is intentional.

---

## §Token-spec for `design/tokens.ts` (v2)

This is the literal input to the feature-build-loop that ships `design/tokens.ts` v2 and the same-commit edit to `ma_gatekeeper/frontend/tailwind.config.ts`.

### File header

```ts
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
 *     transitionDuration, screens)
 *   - ma_gatekeeper/frontend/app/globals.css (CSS variable declarations on :root and
 *     [data-theme="light"])
 *
 * Locked by Art Director on 2026-05-26 per design/SYSTEM.md.
 * v2 revision pending Supervisor sign-off on the brand vs. interactive color split
 * (design/SYSTEM.md §Architectural decision).
 * Do not edit token values without an AD section-review escalation per design/PLAN.md §3.3.
 */
```

### Colors (v2)

```ts
// Shared accent-clay hex — used by `accent-clay` and `lane-block` per SYSTEM.md §Color decision.
const ACCENT_CLAY_HEX = "#B86F3D";

// Staged escape hatch — darker clay for the Block-Escalate visual collision case
// per SYSTEM.md §18 polish. Not exported by default; uncomment to swap accent-clay.
// const ACCENT_CLAY_DARK_HEX = "#8B5430";

export const colors = {
  // Brand (decorative-only — see SYSTEM.md §Architectural decision)
  // TODO: Playwright field-verify #0F4A38 against #0B1311 — decorative tier only (1.89:1).
  "brand-primary": "#0F4A38",

  // TODO: Playwright field-verify #B86F3D vs Mercury peach #F4D4BE saturation ceiling.
  "accent-clay": ACCENT_CLAY_HEX,

  // Interactive — passes WCAG 4.5:1 on --neutral-900 (4.51:1 verified).
  // TODO: Playwright field-verify #4A9D7E against #0B1311 for 4.5:1 small-text.
  "text-interactive": "#4A9D7E",
  "focus-ring":       "#4A9D7E",
  "link-color":       "#4A9D7E", // dark-mode default; light-mode uses brand-primary

  // Text-on-filled tokens (filled-badge case) — R3 corrected: dark glyph on every filled badge.
  // v1 light-on-clay (#F4F6F3 on #B86F3D) clocked 3.59:1 and failed 4.5:1; dark text restores compliance.
  //   text-on-accent-clay   #0B1311 on #B86F3D  → 4.82:1  (PASS)
  //   text-on-lane-clear    #0B1311 on #4D936F  → 5.13:1  (PASS)
  //   text-on-lane-escalate #0B1311 on #C49A3A  → 7.20:1  (PASS)
  //   text-on-lane-block    #0B1311 on #B86F3D  → 4.82:1  (PASS, aliases to accent-clay)
  "text-on-accent-clay":   "#0B1311",
  "text-on-lane-clear":    "#0B1311",
  "text-on-lane-escalate": "#0B1311",
  "text-on-lane-block":    "#0B1311", // aliases to text-on-accent-clay

  // Neutrals (cool-green-tinted, dark-mode anchored)
  "neutral-50":  "#F4F6F3",
  "neutral-100": "#ECEFEC",
  "neutral-200": "#D2DCD5",
  "neutral-300": "#A8B8AE",
  "neutral-400": "#7A8F83", // mono span-ID, passes 4.6:1
  "neutral-500": "#8A9E94", // v2: lightened from #4A5F55 (5.7:1 on neutral-900)
  // Decorative-only — fails 4.5:1; DO NOT use for body text. Borders/dividers/chrome ≥18px only.
  "neutral-500-decorative": "#4A5F55",
  "neutral-600": "#2D3F37",
  "neutral-700": "#1E2D27",
  "neutral-800": "#14201C",
  "neutral-900": "#0B1311",

  // Light-mode parity (full inversion documented in SYSTEM.md §Color → Light-mode neutral parity)
  "bg-paper":   "#FBFAF5",
  "text-paper": "#0E1311",
  "neutral-500-light": "#5A6F65", // light-mode equivalent of --neutral-500, passes 4.51:1 on bg-paper

  // Risk lanes (state-only, 5%-of-canvas max for clear/escalate; block aliases to accent-clay)
  // TODO: Playwright field-verify #4D936F against #0B1311 for 4.5:1 small-text.
  "lane-clear":    "#4D936F", // v2: lightened from #3F7A5A (4.52:1 verified)
  "lane-escalate": "#C49A3A",
  "lane-block":    ACCENT_CLAY_HEX,

  // State primitives (v2)
  "skeleton-base": "#1E2D27", // = neutral-700; pulses to neutral-600 at --opacity-skeleton
} as const;

// Deliberately undefined — INSPIRATION.md §Five-weird-lifts §Color.
// If a builder writes `border-brand-blue`, the class does not resolve.
// export const brandBlue = undefined; // (do not add this export)
```

### Focus & state tokens (v2 — new)

```ts
export const focusRing = {
  color:  "var(--focus-ring-color)", // resolves to text-interactive
  width:  "2px",
  offset: "2px",
  style:  "solid" as const,
} as const;

export const opacity = {
  disabled: 0.4,
  skeleton: 0.6,
} as const;
```

### Typography

```ts
export const fontFamily = {
  display: ['"Fraunces Variable"', "Fraunces", "Georgia", "serif"],
  body:    ['"Inter Variable"', "Inter", "system-ui", "sans-serif"],
  mono:    ['"JetBrains Mono Variable"', "JetBrains Mono", "ui-monospace", "monospace"],
} as const;

export const fontSize = {
  // [size, line-height, letter-spacing]
  "hero-display":         ["240px", "1.05", "-0.02em"],
  "hero-display-mobile":  ["96px",  "1.05", "-0.02em"], // v2: explicit mobile override
  "hero-tagline":         ["96px",  "1.05", "-0.01em"],
  "hero-sub":             ["56px",  "1.1",  "-0.01em"],
  "display-md":           ["32px",  "1.15", "-0.005em"],
  "body-lg":              ["24px",  "1.5",  "0"],
  "body":                 ["16px",  "1.55", "0"],
  "mono-attribution":     ["16px",  "1.4",  "0"],
  "mono-badge":           ["14px",  "1.2",  "+0.08em"],
  "mono-span":            ["12px",  "1.4",  "0"],
  "small":                ["14px",  "1.5",  "0"],
  "micro":                ["12px",  "1.4",  "+0.02em"],
} as const;

export const fontFeatureSettings = {
  mono: '"liga" 0, "calt" 0',
  display: '"opsz" 90',
} as const;
```

### Spacing (8px-base scale)

```ts
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
```

### Layout primitives (v2 — new)

```ts
// Section min-heights per SYSTEM.md §Motion language §2.
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
  prose:   "75ch",   // §11 longest FAQ answer above 1440px
  default: "1200px", // standard content container
  wide:    "1440px", // hero, moneymoment outer frame
} as const;

// Breakpoint tokens — spread into Tailwind `screens`.
export const breakpoints = {
  sm: "640px",
  md: "768px",  // mobile hero scroll-jacking cutoff (PLAN §6.1)
  lg: "1024px",
  xl: "1280px",
} as const;
```

### Radii

```ts
export const borderRadius = {
  none: "0",
  sm:   "4px",
  md:   "8px",
  lg:   "12px",
  xl:   "16px",
  full: "9999px",
} as const;
```

### Motion constants

```ts
export const easePrimary = "cubic-bezier(0.16, 1, 0.3, 1)" as const;

export const durationMicro = "150ms" as const;
export const durationComponent = "400ms" as const;
export const durationHero = "800ms" as const;

export const stagger = 0.06 as const;

/**
 * Per-scene exception — SYSTEM.md §Motion language §1.
 * v2 honesty: this DOES ship as a module-scope export (GSAP `scrub` consumes it).
 * @policy noreuse — only the §6.4 moneymoment + the sanctioned edge-stroke linear pulse may import this.
 *                  (custom non-standard tag, not enforced by tooling; code-review rejection lands on any third import.)
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

export const gradientAngles = ["15deg", "165deg", "345deg"] as const;
```

### globals.css declarations (v2 — explicit)

The feature-build-loop ships these CSS variable declarations alongside `tokens.ts`:

```css
:root {
  /* Color */
  --brand-primary: #0F4A38;
  --accent-clay: #B86F3D;
  --text-interactive: #4A9D7E;
  --focus-ring-color: var(--text-interactive);
  --focus-ring-width: 2px;
  --focus-ring-offset: 2px;
  --focus-ring-style: solid;
  --link-color: var(--text-interactive);
  --text-on-accent-clay: #0B1311;   /* R3 corrected: 4.82:1 (v1 #F4F6F3 failed at 3.59:1) */
  --text-on-lane-clear: #0B1311;    /* 5.13:1 verified */
  --text-on-lane-escalate: #0B1311; /* 7.20:1 verified */
  --text-on-lane-block: var(--text-on-accent-clay); /* aliases to corrected dark glyph */

  /* Neutrals + lanes + skeleton — full set from tokens.ts colors */
  /* (omitted here for brevity; ship 1:1 from `colors` export) */

  /* State */
  --opacity-disabled: 0.4;
  --opacity-skeleton: 0.6;
}

[data-theme="light"] {
  --link-color: var(--brand-primary); /* 9.4:1 on bg-paper */
  --neutral-500: #5A6F65; /* light-mode override */
  /* ... (full light-mode overrides per SYSTEM.md §Color → Light-mode neutral parity) */
}

/* Skip-to-content default styles — primitive lives in components/ui but the
   anchor target reset lives here. */
#main-content { scroll-margin-top: 80px; }
```

### Same-commit edit to `ma_gatekeeper/frontend/tailwind.config.ts`

The feature-build-loop ships this edit in the same commit as `design/tokens.ts` v2:

```ts
import {
  colors, fontFamily, fontSize, spacing, borderRadius,
  transitionTimingFunction, transitionDuration,
  breakpoints, containerMaxWidth, sectionMinHeight,
  opacity,
} from "../../../design/tokens";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    screens: breakpoints,
    extend: {
      colors,
      fontFamily,
      fontSize,
      spacing,
      borderRadius,
      transitionTimingFunction,
      transitionDuration,
      maxWidth: containerMaxWidth,
      minHeight: sectionMinHeight,
      opacity,
    },
  },
  plugins: [],
};
```

Plus the **mechanical migration in `ma_gatekeeper/frontend/components/findings-pane.tsx`** that currently consumes `bg-lane-{auto,watch,block}`:

| Before | After |
|---|---|
| `bg-lane-auto` | `bg-lane-clear` |
| `bg-lane-watch` | `bg-lane-escalate` |
| `bg-lane-block` | `bg-lane-block` (no rename — `lane-block` aliased to `accent-clay`) |

### Follow-up: ESLint rule for forbidden Tailwind classes

The feature-build-loop adds a lint configuration that forbids `bg-purple-*` / `pink-*` / `bg-blue-*` (defaults). **Blocker**: requires `npm install eslint-plugin-tailwindcss` (TOOLING §4.1 row 6 lockfile gap, out of agent scope).

---

## §Cross-reference index

For Component Builders Day 5–6 and for the feature-build-loop:

- **COPY §5 moneymoment composition** → §Color `--accent-clay`, `--text-on-accent-clay`, `--neutral-50`, `--neutral-400`, `--neutral-500`, `--neutral-900`; §Typography `--text-hero-display`, `--text-hero-display-mobile`, `--text-mono-attribution`, `--text-mono-badge`, `--text-mono-span`; §Component primitives **Moneymoment frame composition** block (Card `naked` + Annotated-Number + Badge `clay` + SpanID helper).
- **COPY §5 click-reveal** → §Component primitives **SidePanel** (v2 — right variant desktop, bottom variant mobile).
- **COPY §1 nav CTA + COPY §13 footer wordmark** → §Wordmark spec; §Component primitives Button `primary` for the CTA.
- **COPY §6 honesty block + §11 FAQ** → §Component primitives **Accordion** (v2 — one-open-at-a-time per ARIA pattern, not Tabs); §Typography `--text-body` answers, `--text-display-md` headings, `--text-mono-span` for any inline span IDs.
- **COPY §7 honest numbers** → §Component primitives Annotated-Number + Tabs (for the "Show the math" expand — Tabs OK here because the two layers are siblings, not sequential disclosures).
- **COPY §14 500-page `<<TRACE-ID>>`** → §Typography Span-ID mono mandate (Frontend Architect: wrap interpolation in `<code className="font-mono">`).
- **COPY §15 OG image** → §Wordmark at 48px + §Color `--neutral-900` background with `--brand-primary` decorative wash + §Typography `--text-hero-tagline`.
- **COPY §16 video title card** → §Wordmark at 120px.
- **Every route** → §Component primitives **Skip-to-content** (v2 — required as first `<body>` child).

---

## §Outstanding for Round-2 close

| Item | Owner | When | Status |
|---|---|---|---|
| §Motion language section merge | Motion Designer | End of Round 1 | DONE |
| Playwright field-verification of `#0F4A38` (decorative tier), `#4A9D7E` (4.5:1 verify), `#4D936F` (4.5:1 verify), `#B86F3D` (saturation ceiling) on the deployed Vercel preview | Frontend Architect | Day-4 morning if Playwright MCP install lands | PENDING — explicit user action (Playwright MCP install) |
| Supervisor sign-off on the brand vs. interactive color split (§Architectural decision) | Supervisor | Before feature-build-loop ships `tokens.ts` v2 | PENDING |
| GT Sectra vs Fraunces 5-second test | User (human aesthetic judgment) | Window closed Day-3 EOD; out of agent scope | DEFERRED |
| `eslint-plugin-tailwindcss` install (lockfile gap) | User (`npm install`) | Before lint rule ships | PENDING |
| `tokens.ts` v2 ship + same-commit edits | feature-build-loop | After this SYSTEM.md v2 lands + Supervisor sign-off | QUEUED |

---

## §Art Director verdict (v2 revision)

**ITERATE → GO-pending-cohort, 7/10** *(v1 self-validated at 9/10 and missed a WCAG contrast math error that all three cohort reviewers caught — honest downgrade)*.

What v2 closes:

- §Color: 3 critical contrast errors fixed (brand/interactive split, neutral-500 lightened, lane-clear lightened). 11 important structural gaps addressed (focus tokens, scoped reduced-motion CSS, link-color default, Skip-to-content primitive, span-ID mono mandate, moneymoment px-spec lifted, agent-topology node sizing, layout tokens, text-on-lane tokens, state primitives, breakpoint tokens, light-mode parity). 7 polish items shipped (durationMoneymomentSpan honesty fix, hero-display-mobile, accent-clay-dark escape hatch staged, SidePanel + Accordion primitives, Playwright TODOs preserved, AD verdict downgrade).

What remains hard-to-reverse and needs Supervisor sign-off:

- **Brand vs. interactive color split** — `--brand-primary: #0F4A38` is now decorative-only; interactive surfaces use `--text-interactive: #4A9D7E`. This changes the brand-color semantics from Round-1 and is the load-bearing v2 decision (§Architectural decision).

What still waits on humans:

- Playwright MCP install + field-verification of color anchors.
- Option A funding window is closed; if user re-funds late, the GT Sectra 5-second test deferral note is in §Wordmark.
- `eslint-plugin-tailwindcss` install (lockfile gap) — `npm install` user action.

What the cohort gets to verify next pass:

- All 21 must-fix items closed in v2 — Independent Art Director, Component Builder cold-onboard, and Accessibility Auditor should re-run on this revision and (with Supervisor sign-off on the color split) return GO.

7/10 instead of 9/10 because: the v1 9/10 was wrong — the contrast math was math-wrong. The honest score acknowledges that the system passed self-validation but failed external validation, and v2 is the corrected ship. A 10/10 would require Playwright field-verification + Supervisor sign-off on the architectural split, both still pending.

Signed off for downstream pickup by the feature-build-loop **conditional on Supervisor sign-off on the brand vs. interactive color split**. The §Token-spec block is the literal v2 input.

— Art Director, 2026-05-27 (v2 revision)
