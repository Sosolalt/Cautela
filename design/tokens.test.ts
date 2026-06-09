/**
 * design/tokens.test.ts — Documentary-Brutalism invariant guard.
 *
 * Runs via Node's built-in test runner — zero deps.
 *   node --test --experimental-strip-types design/tokens.test.ts
 * On Node 22+ the flag is unnecessary (TS stripping is enabled by default).
 *
 * Each assertion converts a brand non-negotiable from comment-only to
 * enforceable:
 *
 *   1. `brand-blue` is never exported (the brand's "no blue" non-negotiable).
 *   2. `accent-warm-clay` (#B86F3D) is never exported under any key (the
 *      prior accent is now explicitly forbidden).
 *   3. `lane-block` aliases to `accent-clay` (single hex for the severe lane).
 *   4. Gradient angle whitelist preserved for back-compat.
 *   5. WCAG 4.5:1 contrast: text-interactive (champagne) on surface (near-black).
 *   6. WCAG 4.5:1 contrast: lane-clear (champagne-soft) on surface.
 *   7. WCAG 4.5:1 contrast: lane-escalate (champagne) on surface.
 *   8. Filled-badge inverse: text-on-accent-clay (ivory) on accent-clay (oxblood).
 *   9. Filled-badge inverse: text-on-lane-clear (ink-paper) on lane-clear.
 *  10. Filled-badge inverse: text-on-lane-escalate (ink-paper) on lane-escalate.
 *  11. neutral-500 and neutral-500-decorative are distinct (decorative demoted).
 *  12. borderRadius is locked at 0 globally (Documentary-Brutalism non-negotiable).
 *  13. Exactly one easing exported (the brand's "one easing only" non-negotiable).
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  borderRadius,
  colors,
  easePrimary,
  gradientAngles,
  transitionTimingFunction,
} from "./tokens.ts";

// ---------------------------------------------------------------------------
// WCAG 2.1 relative luminance + contrast (formula per W3C TR-WCAG21 §1.4.3).
// ---------------------------------------------------------------------------
function luminance(hex: string): number {
  const rgb = hex.slice(1).match(/.{2}/g)!.map(h => parseInt(h, 16) / 255);
  const [r, g, b] = rgb.map(c => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(fg: string, bg: string): number {
  const lFg = luminance(fg), lBg = luminance(bg);
  return (Math.max(lFg, lBg) + 0.05) / (Math.min(lFg, lBg) + 0.05);
}

// ---------------------------------------------------------------------------
// Brand-level invariants.
// ---------------------------------------------------------------------------

test("brand-blue is deliberately undefined (no-blue non-negotiable)", () => {
  assert.ok(!("brand-blue" in colors), "brand-blue must not exist as a color token");
});

test("warm-clay #B86F3D is never exported (the prior accent is now forbidden)", () => {
  const banned = "#B86F3D";
  for (const [key, value] of Object.entries(colors)) {
    assert.notEqual(
      value.toUpperCase(),
      banned,
      `color token \`${key}\` is set to the forbidden warm-clay value ${banned}`,
    );
  }
});

test("lane-block aliases to accent-clay (single hex for the severe lane)", () => {
  assert.equal(colors["lane-block"], colors["accent-clay"]);
});

test("gradient angles whitelist preserved for back-compat", () => {
  assert.deepEqual([...gradientAngles], ["15deg", "165deg", "345deg"]);
});

// ---------------------------------------------------------------------------
// WCAG 4.5:1 contrast guards (text on dark surface).
// ---------------------------------------------------------------------------

test("text-interactive passes WCAG 4.5:1 small-text on neutral-900 surface", () => {
  const ratio = contrast(colors["text-interactive"], colors["neutral-900"]);
  assert.ok(ratio >= 4.5, `text-interactive contrast ${ratio.toFixed(2)}:1 fails 4.5:1`);
});

test("lane-clear passes WCAG 4.5:1 small-text on neutral-900 surface", () => {
  const ratio = contrast(colors["lane-clear"], colors["neutral-900"]);
  assert.ok(ratio >= 4.5, `lane-clear contrast ${ratio.toFixed(2)}:1 fails 4.5:1`);
});

test("lane-escalate passes WCAG 4.5:1 small-text on neutral-900 surface", () => {
  const ratio = contrast(colors["lane-escalate"], colors["neutral-900"]);
  assert.ok(ratio >= 4.5, `lane-escalate contrast ${ratio.toFixed(2)}:1 fails 4.5:1`);
});

test("neutral-500 and neutral-500-decorative are distinct (decorative demotion)", () => {
  assert.notEqual(colors["neutral-500"], colors["neutral-500-decorative"]);
});

// ---------------------------------------------------------------------------
// Filled-badge inverse contrast — glyph must pass 4.5:1 on its filled bg.
// ---------------------------------------------------------------------------

test("text-on-accent-clay passes WCAG 4.5:1 on accent-clay (filled Block badge)", () => {
  const ratio = contrast(colors["text-on-accent-clay"], colors["accent-clay"]);
  assert.ok(ratio >= 4.5, `text-on-accent-clay contrast ${ratio.toFixed(2)}:1 fails 4.5:1`);
});

test("text-on-lane-clear passes WCAG 4.5:1 on lane-clear (filled Clear badge)", () => {
  const ratio = contrast(colors["text-on-lane-clear"], colors["lane-clear"]);
  assert.ok(ratio >= 4.5, `text-on-lane-clear contrast ${ratio.toFixed(2)}:1 fails 4.5:1`);
});

test("text-on-lane-escalate passes WCAG 4.5:1 on lane-escalate (filled Escalate badge)", () => {
  const ratio = contrast(colors["text-on-lane-escalate"], colors["lane-escalate"]);
  assert.ok(ratio >= 4.5, `text-on-lane-escalate contrast ${ratio.toFixed(2)}:1 fails 4.5:1`);
});

// ---------------------------------------------------------------------------
// Documentary-Brutalism structural invariants.
// ---------------------------------------------------------------------------

test("borderRadius is locked at 0 for every key (Documentary-Brutalism non-negotiable)", () => {
  for (const [key, value] of Object.entries(borderRadius)) {
    assert.equal(value, "0", `borderRadius.${key} = "${value}" violates the locked 0-radius rule`);
  }
});

test("exactly one easing is exported (the brand's `one easing only` rule)", () => {
  const easings = Object.values(transitionTimingFunction);
  assert.equal(easings.length, 1, `expected 1 easing, got ${easings.length}`);
  assert.equal(easings[0], easePrimary);
  assert.equal(easePrimary, "cubic-bezier(0.16, 1, 0.3, 1)");
});
