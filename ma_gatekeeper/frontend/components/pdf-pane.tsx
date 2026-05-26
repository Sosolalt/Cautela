"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { GatekeeperDecision, RiskFinding } from "@/lib/types";

interface Row {
  finding: RiskFinding;
  decision: GatekeeperDecision;
}

interface Props {
  dealId: string | null;
  rows: Row[];
  selectedFindingId: string | null;
}

/**
 * PDF viewer pane. react-pdf is loaded dynamically (it pulls pdfjs which
 * requires a browser environment) so SSR doesn't choke during `next build`.
 *
 * Bidirectional sync: when `selectedFindingId` changes, scroll to the page
 * carrying that finding (lookup via `finding.page` from the schema), and
 * — once `pdf_bbox` is wired through the SSE stream — overlay a yellow
 * highlight on those coordinates. The highlight rendering is intentionally
 * a stub here so the spine compiles before D15; finishing it is a 1-day
 * lookup task per plan §7 D15 (bbox is already populated upstream).
 */
export function PdfPane({ dealId, rows, selectedFindingId }: Props) {
  const [Doc, setDoc] = useState<typeof import("react-pdf") | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    import("react-pdf").then((mod) => {
      if (cancelled) return;
      // pdfjs worker setup — required by react-pdf >= 7. Pin to the same
      // pdfjs-dist version as package.json or the worker mismatch crashes
      // silently with "API/Worker version mismatch."
      // Use the .min.js worker (NOT .mjs) — pdfjs-dist v4's ESM worker
      // breaks under Next 14's webpack5 url-loader for a subset of
      // bundler configs (open issue in the react-pdf tracker). The
      // .min.js path is unambiguous.
      mod.pdfjs.GlobalWorkerOptions.workerSrc = new URL(
        "pdfjs-dist/build/pdf.worker.min.js",
        import.meta.url,
      ).toString();
      setDoc(mod);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = useMemo(
    () => rows.find((r) => r.finding.clause_id === selectedFindingId),
    [rows, selectedFindingId],
  );

  useEffect(() => {
    // RiskFinding currently doesn't carry a `page` field — the page lives
    // on the Clause it cites. D15 task: thread `page` through the SSE
    // stream alongside `pdf_bbox`. Until then we no-op and let the user
    // page through manually.
    if (!selected) return;
    const page = (selected.finding as unknown as { page?: number }).page ?? 1;
    setPageNumber(page);
  }, [selected]);

  if (!dealId) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-sm text-neutral-500">
        Select a deal to load its 8-K Exhibit 2.1 filing.
      </div>
    );
  }

  // /filing/{deal_id} returns the original EDGAR Ex 2.1 artifact with
  // its real Content-Type — almost always `text/html` (3/3 sampled
  // 2024 8-Ks), occasionally `application/pdf`. The frontend rewrite
  // (separate UX work) will branch on the response's Content-Type
  // and render react-pdf or a sandboxed iframe accordingly. Until
  // then this pane still tries the PDF path; an HTML response will
  // trigger onLoadError and the user sees the empty state.
  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";
  const passcode = process.env.NEXT_PUBLIC_DEMO_PASSCODE ?? "";
  const pdfFile = {
    url: `${apiBase}/filing/${dealId}`,
    httpHeaders: { "X-Demo-Passcode": passcode },
    withCredentials: false,
  };

  return (
    <div ref={containerRef} className="h-full overflow-y-auto">
      <div className="border-b border-neutral-200 px-3 py-2 text-sm text-neutral-700">
        {dealId} · page {pageNumber}
      </div>
      {Doc ? (
        <Doc.Document file={pdfFile} onLoadError={(e) => console.error("pdf load", e)}>
          <Doc.Page pageNumber={pageNumber} renderTextLayer renderAnnotationLayer={false} />
        </Doc.Document>
      ) : (
        <div className="p-6 text-sm text-neutral-500">Loading PDF viewer…</div>
      )}
    </div>
  );
}
