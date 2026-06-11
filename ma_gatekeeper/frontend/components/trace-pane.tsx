"use client";

import clsx from "clsx";
import { useEffect, useRef, useState } from "react";

import type { GatekeeperDecision, Lane, RiskFinding, Tag } from "@/lib/types";
import {
  fetchTraceSummary,
  formatDuration,
  phoenixTraceUrlResolved,
  type TraceSummary,
} from "@/lib/phoenix";

// Human-written legal explainer — deterministic, never model output, so it
// can't hallucinate in front of a reviewer. Explains the RISK CATEGORY in
// plain terms; the deal-specific detail stays in the findings-pane explanation.
// Record<Tag, …> so a newly-added Tag fails the build until it's explained here.
const PLAIN_ENGLISH: Record<Tag, string> = {
  change_of_control:
    "A “change of control” clause sets what happens when the company is taken over. Here the merger itself counts as a change of control, switching on special consents, rights, or payments that only fire when ownership changes hands.",
  mac:
    "A “Material Adverse Effect” clause is the buyer’s escape hatch: if something seriously damages the business before closing, the buyer can walk away. The carve-outs decide what counts — pandemics and market-wide downturns are usually excluded.",
  accelerated_vesting:
    "“Accelerated vesting” means employees’ unvested stock and options pay out immediately at closing instead of over time. “Single-trigger” means the deal alone sets it off — the buyer has to fund that payout.",
  anti_assignment:
    "An “anti-assignment” clause blocks transferring the contract or its rights to someone else without consent. In a merger it can require the counterparty’s sign-off for the deal to carry the contract over.",
  exclusivity:
    "An “exclusivity” / no-shop clause bars the seller from shopping the deal to other buyers for a set window, locking the parties together while they close.",
  ip_assignment:
    "An “IP assignment” clause governs who owns the intellectual property being transferred — decisive when the deal’s value is the technology or patents.",
  non_compete:
    "A “non-compete” clause restricts the seller or key people from starting or joining a competing business for a period after the deal.",
  none:
    "This clause was flagged for review based on its risk language; see the finding detail for the specific obligation.",
};

// Plain-language meaning of the routing lane — directly answers “does a flag
// mean the lawyers made a mistake?” (no — it’s a triage signal).
const LANE_MEANING: Record<Lane, string> = {
  escalate: "Flagged for a human to review — a “look here” signal, not an error.",
  block: "High-severity — would hard-stop the deal pending review.",
  auto_clear: "Standard, low-risk language — cleared automatically.",
};

interface Props {
  traceId: string | null;
  /** Selected finding + decision, for the instant (no-fetch) "This finding"
   *  block. Optional so the pane still renders on traceId alone. */
  finding?: RiskFinding | null;
  decision?: GatekeeperDecision | null;
}

/**
 * Phoenix trace pane.
 *
 * The full Phoenix SPA is illegible in this ~25%-width column (its global
 * nav + span tree + annotations editor are fixed-min-width chrome), so we
 * DON'T embed it here. Instead we pay off the hero's promised
 * "Phoenix trace · Verdict" card with a compact in-app summary — status,
 * latency, span count, the clause this verdict concerns — and a primary CTA
 * that opens the FULL trace in Phoenix in its own tab, where it's actually
 * readable.
 *
 * Demo reveal (plan §8): clicking a finding updates `finding`/`decision`/
 * `traceId` synchronously, so the "This finding" + header blocks snap to the
 * new verdict on the SAME frame as the PDF highlight and the findings-row
 * bar — no fetch on the critical path. The enriched stats (status/latency/
 * spans) arrive a beat later via the same-origin `/phoenix-api` proxy and are
 * cached by trace_id so a re-click is instant. Fetches are AbortController-
 * cancelled on rapid finding switches (mirrors review/page.tsx).
 */
export function TracePane({ traceId, finding = null, decision = null }: Props) {
  const base = process.env.NEXT_PUBLIC_PHOENIX_URL;
  const [summary, setSummary] = useState<TraceSummary | null>(null);
  const [loading, setLoading] = useState(false);
  // CTA href is resolved async: the Phoenix deep-link needs the opaque project
  // node id (the human name 404s "Unknown node"), so we resolve it at runtime
  // (cheap — the project-id promise is cached + shared with the summary fetch).
  const [href, setHref] = useState<string | null>(null);
  const inflight = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!base || !traceId) {
      setSummary(null);
      setLoading(false);
      setHref(null);
      return;
    }
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;
    let cancelled = false;
    setSummary(null);
    setLoading(true);
    fetchTraceSummary(traceId, controller.signal)
      .then((s) => {
        if (cancelled) return;
        setSummary(s);
        setLoading(false);
      })
      .catch(() => {
        // AbortError (user moved on) or any unexpected shape: degrade to the
        // CTA-only state, never throw.
        if (cancelled) return;
        setLoading(false);
      });
    phoenixTraceUrlResolved(traceId)
      .then((u) => {
        if (!cancelled) setHref(u);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [base, traceId]);

  if (!base) {
    return (
      <div className="flex h-full flex-col">
        <TracePaneHeader label="Phoenix trace" />
        <div className="flex flex-1 items-center justify-center p-6 text-center font-mono text-xs leading-relaxed text-ink-muted">
          <span>
            Set <code className="text-ink-muted">NEXT_PUBLIC_PHOENIX_URL</code> to
            your self-hosted Phoenix base URL to enable the trace pane.
          </span>
        </div>
      </div>
    );
  }

  if (!traceId) {
    return (
      <div className="flex h-full flex-col">
        <TracePaneHeader label="Phoenix trace" />
        <div className="flex flex-1 items-center justify-center p-6 text-center font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
          Select a finding to load its Phoenix trace
        </div>
      </div>
    );
  }

  const isError = summary?.status != null && summary.status !== "OK";

  return (
    <div className="flex h-full flex-col">
      <TracePaneHeader label="Phoenix trace · Verdict" traceId={traceId} />

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          {/* Verdict strip — status is the hero element. */}
          <div className="flex items-center gap-3 border-b border-ink-faint px-3 py-3">
            <StatusPill loading={loading} status={summary?.status ?? null} isError={isError} />
            <div className="flex flex-col">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-muted">
                Status
              </span>
              <span className="font-mono text-[11px] text-ink-muted">root span</span>
            </div>
          </div>

          {isError && summary?.statusMessage && (
            <div className="border-b border-ink-faint px-3 py-2 font-mono text-[11px] leading-snug text-accent-oxblood">
              {summary.statusMessage}
            </div>
          )}

          {/* Stat grid. */}
          <div className="grid grid-cols-2 border-b border-ink-faint">
            <Stat
              label="Latency"
              loading={loading}
              value={summary ? formatDuration(summary.latencyMs) : null}
              className="border-r border-ink-faint"
            />
            <Stat
              label="Spans"
              loading={loading}
              value={summary ? String(summary.spanCount) : null}
            />
          </div>

          {/* This finding — instant, from props; echoes the hero card meta row. */}
          {finding && (
            <div className="border-b border-ink-faint px-3 py-3">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-muted">
                This finding
              </span>
              <div className="mt-1 text-sm text-ink">
                <span className="font-mono">{finding.clause_id}</span>
                <span className="text-ink-muted"> · {finding.tag}</span>
              </div>
              <div className="mt-0.5 font-mono text-xs text-ink-muted">
                judge {finding.judge_score.toFixed(2)}
                {decision && (
                  <>
                    {" · "}
                    <span title="threshold">τ {decision.threshold_applied.toFixed(2)}</span>
                  </>
                )}
              </div>
            </div>
          )}

          {/* In plain English — deterministic, non-expert explainer for the
              selected finding's risk category + routing lane. No LLM, no fetch. */}
          {finding && (
            <div className="border-b border-ink-faint px-3 py-3">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-muted">
                In plain English
              </span>
              <p className="mt-1 text-sm leading-relaxed text-ink">
                {PLAIN_ENGLISH[finding.tag]}
              </p>
              {decision && (
                <p className="mt-2 font-mono text-[11px] leading-snug text-ink-muted">
                  {LANE_MEANING[decision.lane]}
                </p>
              )}
            </div>
          )}

          {/* Span breakdown — a flat "what ran" digest, not Phoenix's tree. */}
          {summary && summary.spans.length > 0 && (
            <div className="border-b border-ink-faint px-3 py-3">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-muted">
                Span breakdown
              </span>
              <ul className="mt-1.5 space-y-1">
                {summary.spans.map((s, i) => (
                  <li
                    key={`${s.name}-${i}`}
                    className="flex items-baseline justify-between gap-2 font-mono text-xs"
                  >
                    <span className="truncate text-ink" title={s.name}>
                      ▸ {s.name}
                    </span>
                    <span className="shrink-0 text-ink-muted">{formatDuration(s.ms)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Trace not yet indexed (OTel export lag / off the first page). */}
          {!loading && !summary && (
            <div className="border-b border-ink-faint px-3 py-3 font-mono text-[11px] leading-snug text-ink-muted">
              Trace not yet indexed — open the full trace in Phoenix.
            </div>
          )}
        </div>

        {/* Primary CTA — always rendered once a trace_id exists, independent of
            the summary fetch, so the reviewer is never stranded. */}
        {href && (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col gap-0.5 border-t border-ink-faint bg-accent-vermillion px-3 py-3 text-ink-paper no-underline transition-colors hover:bg-transparent hover:text-accent-vermillion focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-vermillion"
          >
            <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.18em]">
              <ArrowUpRight />
              Open full trace in Phoenix
            </span>
            <span className="font-mono text-[10px] normal-case tracking-normal opacity-80">
              {traceId.slice(0, 8)}… · opens new tab
            </span>
          </a>
        )}
      </div>
    </div>
  );
}

/**
 * Trace-pane chrome — a mono, uppercase header with a vermillion status dot,
 * deliberately echoing the hero's `.span-anchor` "Phoenix trace · Verdict"
 * card so the demo's payoff surface matches the landing page that promised it.
 */
function TracePaneHeader({ label, traceId }: { label: string; traceId?: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-ink-faint px-3 py-2 font-mono text-[11px] uppercase tracking-[0.18em] text-accent-vermillion">
      <span className="inline-block h-1.5 w-1.5 shrink-0 bg-accent-vermillion" aria-hidden />
      <span>{label}</span>
      {traceId && (
        <span className="ml-auto truncate normal-case tracking-normal text-ink-muted">
          {traceId.slice(0, 12)}…
        </span>
      )}
    </div>
  );
}

function StatusPill({
  loading,
  status,
  isError,
}: {
  loading: boolean;
  status: string | null;
  isError: boolean;
}) {
  if (loading) {
    return <span className="h-7 w-16 motion-safe:animate-pulse bg-ink-dim" aria-hidden />;
  }
  if (!status) {
    return (
      <span className="inline-flex items-center bg-ink-dim px-2 py-1 font-mono text-xs text-ink-muted">
        —
      </span>
    );
  }
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-1 font-mono text-xs uppercase tracking-wide",
        isError ? "bg-accent-oxblood text-neutral-50" : "bg-ink-dim text-ink",
      )}
    >
      <span
        className={clsx("inline-block h-1.5 w-1.5", isError ? "bg-neutral-50" : "bg-accent-vermillion")}
        aria-hidden
      />
      {status}
    </span>
  );
}

function Stat({
  label,
  value,
  loading,
  className,
}: {
  label: string;
  value: string | null;
  loading: boolean;
  className?: string;
}) {
  return (
    <div className={clsx("px-3 py-3", className)}>
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-muted">
        {label}
      </div>
      {loading ? (
        <div className="mt-1 h-5 w-12 motion-safe:animate-pulse bg-ink-dim" aria-hidden />
      ) : (
        <div className="mt-0.5 font-mono text-base text-ink">{value ?? "—"}</div>
      )}
    </div>
  );
}

// Dependency-free arrow-up-right glyph (lucide-react is not a project dep);
// matches the SpanLinkGlyph used in findings-pane.tsx.
function ArrowUpRight() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </svg>
  );
}
