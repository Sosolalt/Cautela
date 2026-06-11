"use client";

/**
 * Fix 7 — Portfolio Analyst pane (1M-context cross-deal cluster view).
 *
 * Layout:
 *
 *   ┌───────────────────────────────┬────────────────────┐
 *   │  compact 6-col grid of 30      │  Plain-language     │
 *   │  deal tiles — the 22 "standard"│  explainer + the    │
 *   │  deals are de-emphasized to a  │  pattern legend +   │
 *   │  neutral fill so the deviating │  the outlier        │
 *   │  clusters + the vermillion     │  "review this first"│
 *   │  OUTLIER pop at a glance        │  callout            │
 *   └───────────────────────────────┴────────────────────┘
 *
 * The story has to land for a NON-EXPERT juror in one glance: most deals
 * share the same safe template (grey), a handful deviate (colored), and one
 * is dangerously exposed (the pulsing vermillion outlier). All 30 tiles + the
 * legend fit without scrolling.
 *
 * Cluster colors are pulled from `tailwind.config.ts` Documentary-Brutalism
 * palette — NO new colors, NO new fonts.
 */

import clsx from "clsx";
import { useEffect, useState } from "react";

import { fetchPortfolioReport } from "@/lib/api";
import { phoenixTraceUrlResolved } from "@/lib/phoenix";
import type { PortfolioCluster, PortfolioReport } from "@/lib/types";

// Cluster index → tile fill. Index 0 (the "standard" majority, 22/30) is a
// NEUTRAL fill so it recedes as the baseline; the deviating clusters (1-3) get
// saturated palette colors so they pop against the grey field. The single
// OUTLIER gets vermillion (the brand's "flag" color) + a pulse, handled
// separately in DealCell.
const CLUSTER_TINT: ReadonlyArray<string> = [
  "bg-ink-dim text-ink-muted", // 0 — standard / baseline (de-emphasized)
  "bg-accent-champagne text-ink-paper", // 1 — pandemic shifted
  "bg-accent-ivory text-ink-paper", // 2 — judgment-based
  "bg-accent-oxblood text-neutral-50", // 3 — separate back-door exit
];
// Legend swatches mirror the tile fills. The neutral baseline chip gets a
// hairline border so it's visible against the dark panel.
const CLUSTER_LEGEND: ReadonlyArray<string> = [
  "bg-ink-dim border border-ink-faint",
  "bg-accent-champagne",
  "bg-accent-ivory",
  "bg-accent-oxblood",
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
  // Resolved async — the Phoenix deep-link needs the opaque project node id
  // (the human name 404s "Unknown node"); resolvePhoenixProjectId is cached.
  const [traceHref, setTraceHref] = useState<string | null>(null);

  useEffect(() => {
    const tid = report?.trace_id;
    if (!tid) {
      setTraceHref(null);
      return;
    }
    let cancelled = false;
    phoenixTraceUrlResolved(tid).then((u) => {
      if (!cancelled) setTraceHref(u);
    });
    return () => {
      cancelled = true;
    };
  }, [report?.trace_id]);

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

  const dealCells = buildCells(report);

  return (
    <main className="flex h-full w-full flex-col bg-surface text-ink">
      <header className="flex items-center justify-between border-b border-ink-faint px-4 py-3">
        <div className="flex items-baseline gap-6">
          <div>
            <h1 className="font-display text-2xl tracking-tight">Portfolio Analyst</h1>
            <p className="font-mono text-xs text-ink-muted">
              One Gemini 3 Pro call reads all 30 contracts at once — grouped by how each
              deal&apos;s &ldquo;walk-away&rdquo; clause is written
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
        {report?.trace_id && traceHref && (
          <a
            href={traceHref}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-xs underline"
          >
            trace {report.trace_id.slice(0, 8)}…
          </a>
        )}
      </header>

      {error && (
        <div className="border-b border-accent-oxblood bg-accent-oxblood/25 px-4 py-2 text-sm font-mono text-accent-ivory">
          /portfolio: {error}
        </div>
      )}

      <div className="grid flex-1 grid-cols-12 overflow-hidden">
        {/* Compact 30-tile grid. */}
        <section className="col-span-8 flex flex-col overflow-y-auto border-r border-ink-faint p-4">
          <p className="mb-3 max-w-prose text-sm leading-relaxed text-ink-muted">
            Each tile is one of the 30 contracts, colored by its walk-away-clause pattern.{" "}
            <span className="text-ink-muted">Grey is the safe standard</span> (most deals);
            colored tiles deviate; the pulsing{" "}
            <span className="text-accent-vermillion">vermillion</span> tile is the lone
            outlier.
          </p>
          <div className="grid grid-cols-6 gap-1.5">
            {loading
              ? Array.from({ length: 30 }, (_, i) => (
                  <div
                    key={i}
                    className="min-h-[64px] motion-safe:animate-pulse bg-ink-dim"
                  />
                ))
              : dealCells.map((cell) => <DealCell key={cell.deal_id} cell={cell} />)}
          </div>
        </section>

        {/* Plain-language explainer + pattern legend + outlier callout. */}
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
    ? "bg-accent-vermillion text-ink-paper"
    : cell.cluster_index >= 0 && cell.cluster_index < CLUSTER_TINT.length
      ? CLUSTER_TINT[cell.cluster_index]
      : FALLBACK_TINT;

  return (
    <div
      className={clsx(
        "flex min-h-[64px] flex-col justify-end gap-0.5 border border-ink-faint p-1.5",
        "transition-colors duration-300",
        tint,
        // The outlier spans two columns and pulses so it is unmistakable
        // against the grey baseline — the visual payoff of the whole view.
        cell.is_outlier && "col-span-2 ring-1 ring-ink-paper motion-safe:animate-pulse",
      )}
      title={
        cell.is_outlier
          ? `outlier: ${cell.deal_id}`
          : `pattern ${cell.cluster_index + 1}: ${cell.deal_id}`
      }
    >
      {cell.is_outlier && (
        <span className="font-mono text-[9px] font-semibold uppercase tracking-[0.12em]">
          ⚠ Outlier
        </span>
      )}
      <span className="font-mono text-[10px] leading-tight">{cell.deal_id}</span>
    </div>
  );
}

function ClusterLegend({ report }: { report: PortfolioReport }) {
  return (
    <div className="space-y-5">
      {/* What this shows — the non-expert primer. */}
      <div className="space-y-2">
        <h2 className="font-display text-lg">What this shows</h2>
        <p className="text-sm leading-relaxed text-ink-muted">
          Every merger contract has a &ldquo;walk-away&rdquo; clause — lawyers call it the{" "}
          <span className="text-ink">Material Adverse Effect</span> (MAE) — the rule that
          decides when a buyer is allowed to cancel the deal. Cautela read all 30 contracts
          in a single pass and grouped them by how that clause is written.
        </p>
        <p className="text-sm leading-relaxed text-ink-muted">
          Most follow the same safe pattern; a few deviate in specific ways; one is
          dangerously exposed. Reviewing deals one at a time, you would never spot this
          pattern across a whole portfolio — that is the point.
        </p>
      </div>

      {/* Counts. */}
      <div className="border-t border-ink-faint pt-4">
        <h3 className="font-display text-base">
          {report.clusters.length} pattern
          {report.clusters.length === 1 ? "" : "s"} across 30 deals
        </h3>
        <p className="font-mono text-xs text-ink-muted">
          {report.outliers.length} deal{report.outliers.length === 1 ? "" : "s"} fit no
          pattern
        </p>
      </div>

      <ul className="space-y-3">
        {report.clusters.map((cluster, idx) => (
          <LegendRow key={cluster.cluster_id} cluster={cluster} index={idx} />
        ))}
      </ul>

      {report.outliers.length > 0 && (
        <div className="border-t-2 border-accent-vermillion pt-3">
          <h3 className="font-display text-base text-accent-vermillion">
            Review {report.outliers.length === 1 ? "this one" : "these"} first
          </h3>
          <ul className="mt-2 space-y-2">
            {report.outliers.map((o) => (
              <li key={o.deal_id} className="text-sm">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 bg-accent-vermillion" aria-hidden />
                  <span className="font-mono text-xs">{o.deal_id}</span>
                </div>
                <p className="mt-1 leading-relaxed text-ink-muted">{o.why}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function LegendRow({ cluster, index }: { cluster: PortfolioCluster; index: number }) {
  const swatch =
    index >= 0 && index < CLUSTER_LEGEND.length ? CLUSTER_LEGEND[index] : "bg-neutral-400";
  return (
    <li className="text-sm">
      <div className="flex items-baseline gap-2">
        <span className={clsx("mt-1 inline-block h-3 w-3 shrink-0", swatch)} aria-hidden />
        <span className="font-medium">{cluster.name}</span>
        <span className="ml-auto whitespace-nowrap font-mono text-xs text-ink-muted">
          {cluster.member_deal_ids.length} deals
        </span>
      </div>
      <p className="mt-1 leading-relaxed text-ink-muted">{cluster.theme}</p>
    </li>
  );
}
