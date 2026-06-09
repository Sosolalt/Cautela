# Hero Integration Plan — port the Documentary-Brutalism WebGL hero into the Next.js frontend

**Goal:** Take the finished, animated Three.js hero that currently lives as a standalone vanilla page
(`design/claude-design-output/ui_kits/marketing/hero-b.html` + `hero-scene.js`) and make it the live
landing surface of the product app (`ma_gatekeeper/frontend`), with the page-flip → verdict-dot →
trace-line → verdict-card animation running inside `next dev`.

**Acceptance:** `/` renders the hero, the 7s animation loop runs, `Try the demo →` routes into the
existing review tool, `npm run typecheck` adds no new errors, and the existing review/portfolio routes
still work.

---

## 0. Ground truth (verified against the code, not assumed)

- **Scene tech:** `hero-scene.js` is 1,534 lines of an IIFE using a **global `THREE`** (loaded via
  `unpkg.com/three@0.160.0` CDN in `hero-b.html:370`). **Core three only** — no OrbitControls / loaders /
  EffectComposer / addons. All `THREE.*` symbols used exist in three 0.160.
- **DOM contract — the scene reads exactly three elements by id, plus four classes inside the third:**
  - `#three-canvas` (the WebGL canvas) — `hero-scene.js:13`
  - `#trace-line` (an `<svg><line>`) — `hero-scene.js:14`
  - `#span-anchor` (the verdict card) — `hero-scene.js:15`, and inside it
    `.id`, `.clause`, `.tag`, `.ci` — `hero-scene.js:1304-1307` (it rewrites their text during the loop).
- **Lifecycle the scene sets up:** `requestAnimationFrame(tick)` loop (`:1533`), `window.resize`
  listener (`:1514`), a `ResizeObserver` on the canvas (`:1520`), `document.fonts.ready` callback
  (`:1523`), `renderer.setPixelRatio(min(dpr,2))` (`:78`), and a debug global `window.__hero`.
- **No teardown exists** — no `cancelAnimationFrame`, no `removeEventListener`, no `renderer.dispose()`.
- **`reactStrictMode: true`** in `next.config.mjs` → effects run **twice** in dev. Without a guard +
  teardown this leaks a second WebGL context and stacks a second RAF loop.
- **Reduced motion (corrected):** the scene reads `reduced` at `:16` but only uses it in **one** place
  (`:1442`, `else if (!reduced)`) to skip the camera-breathing parallax. **There is NO static-frame path** —
  the page-flip / dot / trace-line / verdict-card and the RAF reschedule (`:1450`, `:1533`) all run
  unconditionally. A genuine reduced-motion path must be **added** as sanctioned new work (see §2.6); it is
  not "kept."
- **Token mismatch (must fix):** the hero CSS references `var(--accent-vermillion)`, `var(--font-body)`,
  `var(--font-display-news)`, `var(--font-mono)`. The frontend `app/globals.css` `:root` defines the
  surface/ink/champagne/oxblood tokens **but NOT** `--accent-vermillion` or any `--font-*` family vars.
  The source of those is `design/claude-design-output/colors_and_type.css:38,44-48`.
- **Fonts:** already `@import`-ed in `app/globals.css:12` (Newsreader 200/400/800, Space Grotesk,
  Geist Mono, IBM Plex Mono). No new font work needed.
- **CSS-module footgun:** the scene does `spanAnchor.querySelector('.id'|'.clause'|'.tag'|'.ci')`.
  A CSS Module would hash those class names → `querySelector` returns null → animation half-breaks.
  → the hero stylesheet **must keep those class names un-hashed** (global CSS, namespaced under a root
  class), not a `*.module.css`.
- **Routes today:** `app/page.tsx` (review tool), `app/portfolio/page.tsx`. Only one internal link
  exists: `app/page.tsx:103 href="/portfolio"`. Moving the tool off `/` touches almost nothing.
- **Pre-existing, out-of-scope:** `next build` is already broken by the pdfjs ESM worker (unrelated to
  the hero). `tsc --noEmit` already reports 3 errors in `tailwind.config.ts` (readonly tuples from
  `as const`). This plan must not add new errors but does not fix those. Demo path is `next dev`.

---

## 1. Dependencies

1. Add to `ma_gatekeeper/frontend/package.json`:
   - `"three": "0.160.0"` (pinned **exact** to the version the scene was authored against).
   - `"@types/three": "^0.160.0"` in `devDependencies`.
2. `npm install` in `ma_gatekeeper/frontend`.
3. No `next.config.mjs` change expected — three 0.160 core is consumed as a normal ESM dep. Leave
   `transpilePackages` (react-pdf/pdfjs-dist) untouched. (If a parse error on `three` surfaces, the
   fallback is adding `"three"` to `transpilePackages` — but do not pre-emptively add it.)

## 2. Port the scene — `components/hero/hero-scene.ts`

Mechanical wrap, **not** a rewrite. Do not touch the animation math, geometry, easing, or timing.

1. Copy `hero-scene.js` → `components/hero/hero-scene.ts`. Add `// @ts-nocheck` as line 1 (1,534 lines of
   untyped three code; typing it is out of scope and would risk behavior changes).
2. Replace the global `THREE` dependency with `import * as THREE from "three";` at top.
3. Convert the top-level IIFE `(() => { … })()` into an exported function:
   `export function initHeroScene(opts: { canvas, svgLine, spanAnchor }): () => void`.
   - Replace the three `document.getElementById(...)` reads (`:13-15`) with the passed-in `opts.*`.
   - Keep every other `document.createElement('canvas')` (texture/shadow scratch canvases) as-is.
4. **Add teardown — requires two SANCTIONED edits inside the loop tail** (these are the *only* edits
   permitted to the scene body; the animation math/geometry/easing stay byte-for-byte):
   - **Capture the RAF id.** Both `requestAnimationFrame(tick)` calls currently **discard** their return
     value — the reschedule at `hero-scene.js:1450` and the boot at `:1533`. Rewrite both to
     `rafId = requestAnimationFrame(tick)` against a module-scoped `let rafId`. Without this the loop is
     un-cancellable and StrictMode re-leaks a second RAF. This is explicitly carved out of the
     "do not touch the body" rule.
   - Return a `dispose()` that:
     - `cancelAnimationFrame(rafId)`.
     - `window.removeEventListener('resize', resize)`.
     - `resizeObserver?.disconnect()`.
     - **Set a `disposed` flag** checked by the `document.fonts.ready.then(refreshRects)` callback (`:1523`)
       so a late font-load after unmount can't touch a torn-down renderer. (`refreshRects` reads
       `renderer`/canvas rects → guard it: `if (disposed) return;`.)
     - `renderer.dispose()` + traverse `scene` disposing geometries/materials, dispose all `CanvasTexture`s,
       then `renderer.forceContextLoss()`. (Safe because the component hands each mount a *fresh* canvas —
       see §5.3 — so a force-lost context is never reused.)
     - clean up the debug globals. The scene only *assigns* `window.__hero` (`:1532`) and `window.__L`
       (`:145`) (plus `window.__dbgCam` inside an unreached branch); `__freeze`/`__pose`/`__rotFull`/
       `__tuckAmp` are read-only external tuning hooks it never sets. **Preferred fix:** gate the
       `__hero`/`__L` assignment sites behind `process.env.NODE_ENV !== 'production'` so nothing leaks in
       prod; deleting them in `dispose()` is the fallback.
5. Leave the `reduced` parallax branch at `:1442` intact.
6. **Add a real reduced-motion path (new work, sanctioned).** When `reduced` is true, the scene must NOT
   loop: render exactly one resolved frame and stop. Implementation: locate the time source `tick` reads
   (the elapsed-time/clock value driving the loop), and when `reduced`, pin it to a fixed phase inside the
   **verdict-hold window** (per the scene's own header timeline this is ~`t = 4.0s` of the 7s `LOOP`, after
   `page-flip → dot → line` and before `fade & reset`), run the per-frame draw **once**, and `return`
   before the `rafId = requestAnimationFrame(tick)` reschedule. Result: a static frame showing the flipped
   page + trace line + verdict card — the same end-state the reference screenshot captures.
   **Placement precision:** `tick` recomputes `t` near its top (`:1336`) and may override it via the
   `window.__freeze` hook (`:1337`). Do NOT pin `t` literally at the very top of `tick` — `:1336` would
   clobber it. Pin it **after** that recompute by reusing the existing `__freeze` semantics (set the freeze
   value to the verdict-hold phase), and gate the `:1450` reschedule on `!reduced`, so the loop draws
   exactly one frame and stops. Keep the diff minimal.

## 3. Hero styles — `components/hero/hero.css` (global, namespaced)

1. Copy the `<style>` block from `hero-b.html:16-304` into `components/hero/hero.css`.
2. **Namespace, don't modularize.** Wrap the rules under a root class `.hero-stage` (the `<main>` gets
   `className="hero-stage"`). Scope the `html,body{overflow:hidden}` rule away — the hero is one route, not
   the whole app; replace it with
   `.hero-stage { position: relative; height: 100vh; width: 100vw; overflow: hidden; background: var(--surface); }`.
   The `background: var(--surface)` is **load-bearing, not cosmetic**: the renderer is created with
   `alpha:true` + `setClearColor(0x000000, 0)` (`hero-scene.js:77,80`) — the canvas is **transparent** and
   composites over whatever is behind it. The source relied on `colors_and_type.css`'s
   `html,body{background:var(--surface)}`, which §3.3 drops. `layout.tsx:20` already paints
   `body bg-surface`, so this is belt-and-braces, but make the near-black backdrop explicit on `.hero-stage`
   so the hero can never composite over white. Keep
   `.id/.clause/.tag/.ci/#span-anchor/#trace-line/#three-canvas` selectors **verbatim** (scene depends on
   them). Import it with `import "./hero.css";` from the client component (global import, no hashing).
3. Drop the `../../colors_and_type.css` `<link>` — tokens come from `globals.css` (see §4).

## 4. Tokens — extend `app/globals.css` `:root`

Add the vars the hero CSS references that are currently missing (values from `colors_and_type.css`). The
hero stylesheet actually consumes **four**: `--accent-vermillion`, `--font-body`, `--font-display-news`,
`--font-mono`. `--font-display` is added for token parity (other design surfaces use it) but is **not**
referenced by hero-b — include it or omit it, harmless either way. The `--ink` / `--ink-muted` / `--ink-faint`
vars the hero also uses are **already present** in `globals.css:23-26` — do not redeclare.
```
--accent-vermillion: #E63D2F;
--font-display-news: 'Newsreader', 'Instrument Serif', Georgia, serif;   /* used by hero */
--font-body:         'Space Grotesk', 'Inter Tight', system-ui, sans-serif; /* used by hero */
--font-mono:         'Geist Mono', 'IBM Plex Mono', ui-monospace, monospace; /* used by hero */
--font-display:      'Instrument Serif', 'Newsreader', Georgia, serif;   /* parity only, not used by hero */
```
Additive only — no existing token is changed, so the review/portfolio panes are unaffected.

## 5. React component — `components/hero/hero.tsx` (`"use client"`)

1. JSX mirrors the `<main class="stage">` scaffolding from `hero-b.html:307-357`: `.canvas-wrap` (empty —
   see §5.3 for why the canvas is NOT in JSX), `.trace-svg` > `<line id="trace-line">`, `.doc-id`, `.text`
   (kicker / headline / sub / ctas), `#span-anchor` (label / `.id` / `.meta` with `.clause`/`.tag`/`.ci`).
   Root `<main className="hero-stage">`.
2. Refs: `canvasWrapRef` (the `.canvas-wrap` div), `svgLineRef`, `spanAnchorRef`.
3. **Fresh canvas per mount — this is the StrictMode/WebGL fix (resolves the canvas-reuse hazard).** Do NOT
   put `<canvas>` in JSX. React reuses the same canvas DOM node across StrictMode unmount→remount; a canvas
   whose context was `forceContextLoss()`-ed in cleanup is not guaranteed a fresh context on the second
   `new THREE.WebGLRenderer({canvas})`, which can blank the hero in dev — the exact env the demo runs in.
   Instead, in `useEffect`:
   - `const canvas = document.createElement("canvas"); canvas.id = "three-canvas";
     canvasWrapRef.current.appendChild(canvas);` — each mount gets a brand-new GL context.
   - `const dispose = initHeroScene({ canvas, svgLine: svgLineRef.current, spanAnchor: spanAnchorRef.current });`
   - cleanup: `dispose(); canvas.remove();` — the discarded canvas (and its force-lost context) is GC'd; the
     remount builds a fresh one. No init-guard ref needed because only one canvas is ever live at a time;
     add a `useRef(false)` guard only if a leak still appears under testing (§8.4).
   - Bail if any ref is null.
   (The scene reads the inner `.id/.clause/.tag/.ci` itself via `querySelector` on the passed `spanAnchor` —
   keep those classNames un-hashed per §3.)
4. Wire CTAs: `Try the demo →` → `/review` (Next `<Link>`); `Watch the 60-second demo` → `#` for now
   (no video asset committed — leave as inert anchor, note in PR).

## 6. SSR boundary — `app/page.tsx`

1. Three.js / canvas must not SSR. Make `app/page.tsx` a thin server component that renders the hero via
   `next/dynamic` with `{ ssr: false }`:
   `const Hero = dynamic(() => import("@/components/hero/hero"), { ssr: false });`
   (A `"use client"` component alone would still attempt SSR of the markup; `ssr:false` avoids the canvas
   flash and any window access during render.)
2. Optional loading fallback: a static dark `.hero-stage` block so there's no layout jump.

## 7. Move the review tool to `/review`

1. Move current `app/page.tsx` (the three-pane `ReviewPage`) → `app/review/page.tsx` (unchanged content).
2. The hero becomes the new `app/page.tsx` (§6).
3. `app/portfolio/page.tsx` unchanged. The only internal link (`/portfolio` at old `page.tsx:103`) moves
   with the file and still resolves.
4. Grep `docs/` and `README` for hardcoded **bare-root URL** references to the review tool
   (`localhost:3000/` with nothing after the slash, or "open the app at /") and update those to `/review`.
   **Do not** rewrite `/review` strings that are API endpoint paths — `docs/devpost.md:114` and `README.md:68`
   already say `/review` meaning the backend route, not the front-end URL; leave them. The front-end
   demo-script (`docs/demo_script.md`) is the one to check for a bare-root link.

## 8. Verification (the GO bar)

1. `npm run typecheck` → **no new errors** vs. the pre-existing 3 in `tailwind.config.ts`.
2. `npx next dev` → `GET /` returns **200**, `GET /review` **200**, `GET /portfolio` **200**.
3. Visual: drive the running dev server with the globally-available Playwright (v1.60) headless Chromium —
   load `/`, wait ~3.5s (past the flip+dot+line into the verdict-hold window), screenshot, and confirm the
   paper stack + vermillion trace line + Phoenix verdict card render (matches the user's reference frame).
4. Mount/unmount sanity (StrictMode + leak): hard-reload `/` (StrictMode double-mounts), then navigate
   `/` → `/review` → `/`. Confirm in DevTools that exactly **one** `<canvas>` is live under `.canvas-wrap`
   and there is **no** "Too many active WebGL contexts" / "WebGL context lost" console warning (proves the
   §5.3 fresh-canvas + §2.4 dispose path is correct).
5. Reduced-motion (validates the §2.6 path that this plan ADDS): emulate `prefers-reduced-motion: reduce`,
   load `/`, and confirm a **single static resolved frame** renders (flipped page + trace line + verdict
   card) with no RAF loop running (no repaint churn in the Performance panel) and no thrown error.

## 9. Out of scope (explicitly not doing here)

- Fixing the pre-existing `next build` pdfjs-worker failure (separate issue; demo runs on `next dev`).
- Fixing the pre-existing `tailwind.config.ts` `as const` typecheck errors.
- Porting hero variants A and C (only B — the reference screenshot — is requested).
- Committing/pushing (user handles git).

## 10. Rollback

All changes are additive or moves: revert by restoring `app/page.tsx` from `app/review/page.tsx`,
deleting `components/hero/`, removing the `three` dep and the 5 added `:root` vars. No existing component
is edited in place except `globals.css` (additive) — low blast radius.
