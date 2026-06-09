"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

import { initHeroScene } from "./hero-scene";
import "./hero.css";

/**
 * Marketing hero — the Documentary-Brutalism WebGL dossier.
 *
 * Ported from design/claude-design-output/ui_kits/marketing/hero-b.html.
 * The DOM scaffolding lives in JSX; the Three.js scene (hero-scene.ts) is
 * attached in an effect. The `<canvas>` is created imperatively per mount
 * (NOT in JSX) so every StrictMode/route remount gets a fresh WebGL context —
 * a canvas whose context was force-lost in dispose() must never be reused.
 *
 * The scene drives the verdict card's text fields (.id/.clause/.tag/.ci) itself
 * via querySelector on #span-anchor, so those class names are kept and the
 * initial values below are only a pre-paint seed.
 */
export default function Hero() {
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const svgLineRef = useRef<SVGLineElement>(null);
  const spanAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wrap = canvasWrapRef.current;
    const svgLine = svgLineRef.current;
    const spanAnchor = spanAnchorRef.current;
    if (!wrap || !svgLine || !spanAnchor) return;

    // Fresh canvas per mount → fresh GL context (StrictMode-safe).
    const canvas = document.createElement("canvas");
    canvas.id = "three-canvas";
    canvas.setAttribute("aria-hidden", "true");
    wrap.appendChild(canvas);

    const dispose = initHeroScene({ canvas, svgLine, spanAnchor });

    return () => {
      dispose();
      canvas.remove();
    };
  }, []);

  return (
    <main className="hero-stage">
      {/* WebGL canvas mounts here (created in the effect). */}
      <div className="canvas-wrap" ref={canvasWrapRef} />

      {/* SVG hairline overlay — dot → Phoenix trace anchor. */}
      <svg className="trace-svg" aria-hidden="true">
        <line id="trace-line" ref={svgLineRef} x1="0" y1="0" x2="0" y2="0" />
      </svg>

      {/* Doc ID — top-right */}
      <div className="doc-id">
        <div>
          <span className="num">EX-2.1</span> / 2026-05-27
        </div>
        <div>
          <span className="num">1</span> of <span className="num">312</span>
        </div>
        <div className="effective">
          EFFECTIVE 2026-05-27
          <br />
          HELD-OUT FOLD · FROZEN
        </div>
      </div>

      {/* Typography zone */}
      <div className="text">
        <div className="kicker">M&amp;A · Contract review · Multi-agent</div>
        <h1 className="headline">
          <span className="l1">Every flag,</span>
          <br />
          <span className="l2">sourced.</span>
          <br />
          <span className="l3">
            Every verdict, <span className="solid">traced.</span>
          </span>
        </h1>
        <p className="sub">
          <span className="muted">
            M&amp;A contract review where every verdict links to its Phoenix trace —
          </span>{" "}
          and every flag is sourced to the clause it came from.
        </p>
        <div className="ctas">
          <Link className="cta-primary" href="/review">
            <span>Try the demo</span>
            <span className="arrow">→</span>
          </Link>
          {/* Secondary "Watch the 60-second demo" CTA removed — there is no
              video asset yet, and a visibly-dead control next to the live CTA
              reads worse than a single confident action. Re-add as a real
              <a href="…"> once the demo video URL exists. */}
        </div>
      </div>

      {/* PHOENIX TRACE overlay — bottom-right. Text fields are seeds; the scene
          rewrites .id/.clause/.tag/.ci per chapter during the loop. Decorative,
          so it is hidden from assistive tech (the per-loop text rewrites would
          otherwise spam screen readers via aria-live). */}
      <div className="span-anchor" id="span-anchor" ref={spanAnchorRef} aria-hidden="true">
        <div className="label">Phoenix trace · Verdict</div>
        <div className="id">phoenix:span:1a4b-d2c0-7e93-0f12</div>
        <div className="meta">
          <span className="clause">Clause 1.4(b)</span>
          <span className="tag">Adverse effect</span>
          <span className="ci">Cluster-bootstrap LB · 0.91</span>
        </div>
      </div>
    </main>
  );
}
