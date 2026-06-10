"use client";

/**
 * Fix 7 — Portfolio Analyst pane (1M-context cross-deal cluster view).
 *
 * Layout (demo_script.md 1:55-2:05 beat):
 *
 *   ┌───────────────────────────────┬────────────────────┐
 *   │  5x6 grid of 30 deal cells    │  Cluster legend +  │
 *   │  cluster-colored after agent  │  outlier callout   │
 *   │  call returns                 │                    │
 *   └───────────────────────────────┴────────────────────┘
 *
 * The grid IS the visual — at 1080p / 720p juror playback the four
 * cluster colors light up in <0.5s and the outlier pulses. Voiceover:
 * "One Gemini 3 Pro call. Eight hundred thousand tokens. Thirty
 * contracts. The agent finds four MAE-carveout clusters and flags deal
 * seventeen as the outlier."
 *
 * Cluster colors are pulled from `tailwind.config.ts` Documentary-
 * Brutalism palette (`accent-champagne`, `accent-oxblood`,
 * `accent-ivory`, `accent-vermillion`) — NO new colors, NO new fonts.
 */

import clsx from "clsx";
import { useEffect, useState } from "react";

import { fetchPortfolioReport } from "@/lib/api";
import type { PortfolioCluster, PortfolioReport } from "@/lib/types";

// Build a Phoenix deep-link URL using the same env-driven shape as
// trace-pane.tsx. Earlier this rendered as a bare `/phoenix/traces/{id}`
// path which 404'd to the Next app itself instead of the Phoenix host.
function phoenixTraceUrl(traceId: string): string | null {
  const base = process.env.NEXT_PUBLIC_PHOENIX_URL;
  if (!base) return null;
  const project = process.env.NEXT_PUBLIC_PHOENIX_PROJECT || "ma-gatekeeper";
  const template =
    process.env.NEXT_PUBLIC_PHOENIX_TRACE_URL ||
    `${base}/projects/${project}/traces/${traceId}`;
  return template
    .replace("{base}", base)
    .replace("{project}", project)
    .replace("{traceId}", traceId);
}

// Cluster index → Tailwind background class. Pulled from the
// Documentary-Brutalism palette in tailwind.config.ts.
// `bg-accent-champagne-soft` is the lighter shade for grid cells; the
// legend chip uses the full saturation. If the analyst ever returns
// >4 clusters, indices ≥4 fall back to a neutral wash so the grid
// degrades gracefully (the demo line names FOUR clusters; a >4 result
// is a wedge to investigate, not a render bug).
// Light fills (champagne, ivory) pair with DARK ink (`text-ink-paper`); dark
// fills (oxblood, vermillion) pair with light ink. Using `text-ink` (light) on
// the light fills rendered the deal-id labels near-invisible (≤1.9:1) once the
// kebab color classes started resolving — so pair each fill with its readable ink.
const CLUSTER_TINT: ReadonlyArray<string> = [
  "bg-accent-champagne text-ink-paper",
  "bg-accent-oxblood text-neutral-50",
  "bg-accent-ivory text-ink-paper",
  // Vermillion is a hard fill for 10px text either way; dark ink-paper (4.25:1)
  // beats light neutral-50 (3.70:1). The deal_id is also a title-tooltip, so the
  // label is redundant-by-design — but take the better contrast.
  "bg-accent-vermillion text-ink-paper",
];
const CLUSTER_LEGEND: ReadonlyArray<string> = [
  "bg-accent-champagne",
  "bg-accent-oxblood",
  "bg-accent-ivory",
  "bg-accent-vermillion",
];

const FALLBACK_TINT = "bg-ink-dim text-ink-muted";

interface Props {
  /** Optional pre-supplied report — bypass the fetch (for screenshot capture / Storybook). */
  initialReport?: PortfolioReport | null;
}

export function PortfolioPane({ initialReport = null }: Props) {
  const [report, setReport] = useState<PortfolioReport | null>(initialReport);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(initialReport === null);

  useEffect(() => {
    if (initialReport) return;
    let cancelled = false;
    fetchPortfolioReport()
      .then((r) => {
        if (cancelled) return;
        setReport(r);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [initialReport]);

  // Build a flat deal_id -> cluster index lookup. Outliers map to -1.
  // Ordering: cluster members in declaration order, then outliers, then
  // any deals returned by neither (shouldn't happen per the
  // mutual-exclusion test, but the renderer is defensive).
  const dealCells = buildCells(report);

  return (
    <main className="flex h-full w-full flex-col bg-surface text-ink">
      <header className="flex items-center justify-between border-b border-ink-faint px-4 py-3">
        <div className="flex items-baseline gap-6">
          <div>
            <h1 className="font-display text-2xl tracking-tight">
              Portfolio Analyst
            </h1>
            <p className="font-mono text-xs text-ink-muted">
              One Gemini 3 Pro call — 30 contracts — cross-deal MAE clustering
            </p>
          </div>
          {/* Cross-route nav matching /review's rail. */}
          <nav className="flex items-baseline gap-4 font-mono text-[11px] uppercase tracking-[0.18em]">
            <a
              href="/review"
              className="text-ink-muted no-underline transition-colors hover:text-accent-vermillion"
            >
              ← Review
            </a>
            <span className="text-accent-vermillion">Portfolio</span>
          </nav>
        </div>
        {report?.trace_id &&
          (() => {
            const href = phoenixTraceUrl(report.trace_id);
            if (!href) return null;
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="font-mono text-xs underline"
              >
                trace {report.trace_id.slice(0, 8)}…
              </a>
            );
          })()}
      </header>

      {error && (
        <div className="border-b border-accent-oxblood bg-accent-oxblood/25 px-4 py-2 text-sm font-mono text-accent-ivory">
          /portfolio: {error}
        </div>
      )}

      <div className="grid flex-1 grid-cols-12 overflow-hidden">
        {/* 30-cell grid (5 cols × 6 rows on lg; collapses on narrow). */}
        <section className="col-span-8 overflow-y-auto border-r border-ink-faint p-4">
          <div className="grid grid-cols-5 gap-2">
            {loading
              ? Array.from({ length: 30 }, (_, i) => (
                  <div
                    key={i}
                    className="aspect-square motion-safe:animate-pulse bg-ink-dim"
                  />
                ))
              : dealCells.map((cell) => (
                  <DealCell key={cell.deal_id} cell={cell} />
                ))}
          </div>
        </section>

        {/* Cluster legend + outlier callout. */}
        <aside className="col-span-4 overflow-y-auto p-4">
          {report ? (
            <ClusterLegend report={report} />
          ) : (
            <p className="font-mono text-xs text-ink-muted">
              {loading ? "loading portfolio report…" : "no report"}
            </p>
          )}
        </aside>
      </div>
    </main>
  );
}

interface DealCellModel {
  deal_id: string;
  cluster_index: number; // -1 = outlier, -2 = uncovered (shouldn't happen)
  is_outlier: boolean;
}

function buildCells(report: PortfolioReport | null): DealCellModel[] {
  if (!report) return [];
  const cells: DealCellModel[] = [];
  report.clusters.forEach((c, idx) => {
    c.member_deal_ids.forEach((deal_id) => {
      cells.push({ deal_id, cluster_index: idx, is_outlier: false });
    });
  });
  report.outliers.forEach((o) => {
    cells.push({ deal_id: o.deal_id, cluster_index: -1, is_outlier: true });
  });
  return cells;
}

function DealCell({ cell }: { cell: DealCellModel }) {
  const tint = cell.is_outlier
    ? "bg-surface ring-2 ring-accent-oxblood text-ink"
    : cell.cluster_index >= 0 && cell.cluster_index < CLUSTER_TINT.length
      ? CLUSTER_TINT[cell.cluster_index]
      : FALLBACK_TINT;

  return (
    <div
      className={clsx(
        "flex aspect-square flex-col justify-end p-2",
        "transition-colors duration-300",
        tint,
        // Outlier cells pulse via Tailwind's built-in animation — the
        // 1s pulse cadence is the visual hook for the voiceover at
        // demo_script.md 1:55-2:05.
        cell.is_outlier && "motion-safe:animate-pulse",
      )}
      title={
        cell.is_outlier
          ? `outlier: ${cell.deal_id}`
          : `cluster ${cell.cluster_index + 1}: ${cell.deal_id}`
      }
    >
      <span className="font-mono text-[10px] leading-tight">
        {cell.deal_id}
      </span>
    </div>
  );
}

function ClusterLegend({ report }: { report: PortfolioReport }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-display text-lg">
          {report.clusters.length} MAE-carveout cluster
          {report.clusters.length === 1 ? "" : "s"}
        </h2>
        <p className="font-mono text-xs text-ink-muted">
          {report.outliers.length} outlier
          {report.outliers.length === 1 ? "" : "s"} flagged
        </p>
      </div>

      <ul className="space-y-3">
        {report.clusters.map((cluster, idx) => (
          <LegendRow key={cluster.cluster_id} cluster={cluster} index={idx} />
        ))}
      </ul>

      {report.outliers.length > 0 && (
        <div className="border-t-2 border-accent-oxblood pt-3">
          <h3 className="font-display text-base text-accent-oxblood">
            Outliers
          </h3>
          <ul className="mt-2 space-y-2">
            {report.outliers.map((o) => (
              <li key={o.deal_id} className="text-sm">
                <span className="font-mono text-xs">{o.deal_id}</span>
                <p className="mt-1 text-ink-muted">{o.why}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function LegendRow({
  cluster,
  index,
}: {
  cluster: PortfolioCluster;
  index: number;
}) {
  const swatch =
    index >= 0 && index < CLUSTER_LEGEND.length
      ? CLUSTER_LEGEND[index]
      : "bg-neutral-400";
  return (
    <li className="text-sm">
      <div className="flex items-center gap-2">
        <span className={clsx("inline-block h-3 w-3", swatch)} aria-hidden />
        <span className="font-medium">{cluster.name}</span>
        <span className="font-mono text-xs text-ink-muted">
          n={cluster.member_deal_ids.length}
        </span>
      </div>
      <p className="mt-1 text-ink-muted">{cluster.theme}</p>
    </li>
  );
}
