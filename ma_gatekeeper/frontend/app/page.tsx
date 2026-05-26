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
            setErrorMessage(`${event.stage}: ${event.message}`);
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
      <header className="flex items-center justify-between border-b border-neutral-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold tracking-tight">
          M&amp;A Due Diligence Gatekeeper
        </h1>
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
        <div className="border-b border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
          {errorMessage}
        </div>
      )}

      <div className="grid flex-1 grid-cols-12 overflow-hidden">
        <section className="col-span-5 overflow-y-auto border-r border-neutral-200 bg-white">
          <PdfPane dealId={dealId} rows={rows} selectedFindingId={selectedFindingId} />
        </section>
        <section className="col-span-4 overflow-y-auto border-r border-neutral-200 bg-white">
          <FindingsPane
            rows={rows}
            status={status}
            selectedFindingId={selectedFindingId}
            onSelect={setSelectedFindingId}
          />
        </section>
        <section className="col-span-3 overflow-hidden bg-white">
          <TracePane
            traceId={
              selectedFindingId
                ? rows.find((r) => r.finding.clause_id === selectedFindingId)?.finding
                    .trace_id ?? null
                : null
            }
          />
        </section>
      </div>
    </main>
  );
}
