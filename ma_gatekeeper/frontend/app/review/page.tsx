"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { DealPicker } from "@/components/deal-picker";
import { FindingsPane } from "@/components/findings-pane";
import { PdfPane } from "@/components/pdf-pane";
import { TracePane } from "@/components/trace-pane";
import { fetchAllowList, streamReviewByDeal } from "@/lib/api";
import type {
  Deal,
  GatekeeperDecision,
  RiskFinding,
  SseEvent,
} from "@/lib/types";

interface Row {
  finding: RiskFinding;
  decision: GatekeeperDecision;
}

/**
 * Three-pane review surface (plan §7 D15):
 *
 *   ┌───────────┬───────────┬───────────┐
 *   │  PDF      │ Findings  │  Phoenix  │
 *   │ react-pdf │  list     │  trace    │
 *   └───────────┴───────────┴───────────┘
 *
 * State shared across panes is just the selected finding id; that one
 * value drives bidirectional sync:
 *   - Click a finding in the center pane -> PDF jumps + Phoenix iframe
 *     navigates to the trace.
 *   - (D15 extension) Click a clause in the PDF -> reverse-lookup against
 *     `findings.find(f => f.clause_id === clauseId)` then setSelected.
 *
 * Bidirectional sync is feasible because `Clause.pdf_bbox` is populated
 * at parse time (agent/agents.py D4) and the bbox rides on the
 * RiskFinding via the cited_spans_text path (schemas.py).
 */
export default function ReviewPage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [dealId, setDealId] = useState<string | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "streaming" | "done" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // Holds the AbortController for an in-flight review so a re-selection
  // cancels the previous stream and we never race a stale finding into
  // `setRows` after the user has moved on.
  const inflight = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchAllowList()
      .then(setDeals)
      .catch((err) => setErrorMessage(`/allow-list: ${(err as Error).message}`));
  }, []);

  const startReview = useCallback(async (id: string) => {
    // Cancel any previous stream before starting a new one.
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;

    setRows([]);
    setSelectedFindingId(null);
    setStatus("streaming");
    setErrorMessage(null);

    try {
      await streamReviewByDeal(
        id,
        (event: SseEvent) => {
          if (event.event === "finding") {
            setRows((prev) => [...prev, { finding: event.finding, decision: event.decision }]);
          } else if (event.event === "error") {
            // The per-finding clause→provenance join miss is NON-FATAL — the
            // finding still streams and renders in full; only the optional PDF
            // highlight pin is dropped. Don't surface it as a red banner (it
            // read as a failure on the demo). Genuine pipeline errors (other
            // stages) still show.
            if (event.stage !== "join_clause_to_finding") {
              setErrorMessage(`${event.stage}: ${event.message}`);
            }
          } else if (event.event === "done") {
            setStatus("done");
          }
        },
        controller.signal,
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") return; // user moved on
      setErrorMessage((err as Error).message);
      setStatus("error");
    }
  }, []);

  useEffect(() => () => inflight.current?.abort(), []);

  return (
    <main className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-ink-faint px-4 py-3">
        <div className="flex items-baseline gap-5">
          {/* Wordmark → hero. Kept as an <h1> for the document outline /
              screen readers; the inner <a> carries the nav. Vermillion on
              hover mirrors the cross-route links beside it. Leaving the page
              aborts any in-flight stream via the existing unmount cleanup. */}
          <h1 className="font-display text-xl tracking-tight text-ink">
            <a
              href="/"
              className="text-ink no-underline transition-colors hover:text-accent-vermillion"
            >
              Cautela
            </a>
          </h1>
          {/* Cross-route nav in the hero's editorial register (mono, uppercase,
              vermillion on hover). Fix 7 — Portfolio Analyst route. */}
          <nav className="flex items-baseline gap-4 font-mono text-[11px] uppercase tracking-[0.18em]">
            <span className="text-accent-vermillion">Review</span>
            <a
              href="/portfolio"
              className="text-ink-muted no-underline transition-colors hover:text-accent-vermillion"
            >
              Portfolio →
            </a>
          </nav>
        </div>
        <DealPicker
          deals={deals}
          value={dealId}
          onChange={(id) => {
            if (!id || id === dealId) return; // same deal — no-op
            setDealId(id);
            void startReview(id);
          }}
          disabled={status === "streaming"}
        />
      </header>

      {errorMessage && (
        <div
          role="alert"
          className="border-b border-accent-oxblood bg-accent-oxblood/25 px-4 py-2 text-sm font-mono text-accent-ivory"
        >
          {errorMessage}
        </div>
      )}

      <div className="grid flex-1 grid-cols-12 overflow-hidden">
        <section className="col-span-5 overflow-y-auto border-r border-ink-faint">
          <PdfPane
            dealId={dealId}
            rows={rows}
            selectedFindingId={selectedFindingId}
            onSelect={setSelectedFindingId}
          />
        </section>
        <section className="col-span-4 overflow-y-auto border-r border-ink-faint">
          <FindingsPane
            rows={rows}
            status={status}
            selectedFindingId={selectedFindingId}
            onSelect={setSelectedFindingId}
            dealId={dealId}
          />
        </section>
        <section className="col-span-3 overflow-hidden">
          {(() => {
            const selected = selectedFindingId
              ? rows.find((r) => r.finding.clause_id === selectedFindingId) ?? null
              : null;
            return (
              <TracePane
                traceId={selected?.finding.trace_id ?? null}
                finding={selected?.finding ?? null}
                decision={selected?.decision ?? null}
              />
            );
          })()}
        </section>
      </div>
    </main>
  );
}
