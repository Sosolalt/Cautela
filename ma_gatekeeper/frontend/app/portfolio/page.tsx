"use client";

/**
 * Fix 7 — Portfolio Analyst route (`/portfolio`).
 *
 * Mounted as a separate top-level route rather than a tab inside
 * `/review` because the Portfolio Analyst is a SEPARATE capability with
 * its own endpoint (`/portfolio`, server.py) and its own view. The
 * `/review` route stays focused on the per-contract three-pane surface
 * (PDF + findings + Phoenix trace); the `/portfolio` route stays focused
 * on the cross-deal cluster surface. Both surfaces share the same
 * design tokens and the same passcode-gated API client.
 *
 * Demo-script anchor: docs/demo_script.md 1:55-2:05 beat.
 */

import { PortfolioPane } from "@/components/portfolio-pane";

export default function PortfolioRoute() {
  return (
    <main className="h-full">
      <PortfolioPane />
    </main>
  );
}
