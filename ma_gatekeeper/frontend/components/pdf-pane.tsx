"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { GatekeeperDecision, Lane, RiskFinding } from "@/lib/types";

interface Row {
  finding: RiskFinding;
  decision: GatekeeperDecision;
}

interface Props {
  dealId: string | null;
  rows: Row[];
  selectedFindingId: string | null;
  onSelect: (clauseId: string) => void;
}

// pdfjs's PDFPageProxy / PageViewport types aren't re-exported by react-pdf's
// public surface in 9.1.1, so we declare the *narrow* shape we actually call
// against — `view`, `getViewport({scale})`, and the viewport's coord-conversion
// helpers. Source: https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib.PDFPageProxy.html
// (PDFPageProxy.view, getViewport) and the PageViewport class
// (convertToViewportPoint, convertToPdfPoint). Using `unknown` + a guarded cast
// per the spec's "narrow `unknown` not wholesale `any`" rule.
interface PageViewportLike {
  width: number;
  height: number;
  convertToViewportPoint(x: number, y: number): [number, number];
  convertToPdfPoint(x: number, y: number): [number, number];
}
interface PdfPageProxyLike {
  view: [number, number, number, number];
  getViewport(params: { scale: number }): PageViewportLike;
}

const RENDER_SCALE = 1;

// Match the lane-tinted overlay to the FindingsPane's per-row signal so the
// PDF highlight and the list row share their lane's hue. /30 alpha keeps the
// clause text readable underneath while still being unmistakably highlighted.
const LANE_OVERLAY: Record<Lane, string> = {
  auto_clear: "bg-lane-clear/30",
  escalate:   "bg-lane-escalate/30",
  block:      "bg-lane-block/30",
};

/**
 * PDF viewer pane. react-pdf is loaded dynamically (it pulls pdfjs which
 * requires a browser environment) so SSR doesn't choke during `next build`.
 *
 * Bidirectional sync (plan §9, D15):
 *   - Forward: when `selectedFindingId` changes, jump to `finding.page` and
 *     overlay a lane-tinted highlight on `finding.pdf_bbox`.
 *   - Reverse: click anywhere on the page; if the click lands inside any
 *     finding's bbox on the current page, call `onSelect(clause_id)` and the
 *     parent surface drives FindingsPane + TracePane via the shared setter.
 *
 * Both directions key off `page` + `pdf_bbox` already populated by Phase 6.6
 * server-side join (agent/server.py v9, §4.3 trace_id precedent).
 */
export function PdfPane({ dealId, rows, selectedFindingId, onSelect }: Props) {
  const [Doc, setDoc] = useState<typeof import("react-pdf") | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  // The active page's viewport is cached so the click handler can run
  // `convertToPdfPoint` without re-querying pdfjs. Re-set on every
  // `onRenderSuccess`; cleared on page change to avoid using a stale
  // viewport against a freshly-rendered (different-page) canvas.
  const [viewport, setViewport] = useState<PageViewportLike | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    import("react-pdf").then((mod) => {
      if (cancelled) return;
      // pdfjs worker setup — required by react-pdf >= 7. Pin to the same
      // pdfjs-dist version as package.json or the worker mismatch crashes
      // silently with "API/Worker version mismatch."
      // pdfjs-dist 4.x ships ESM-only workers (`pdf.worker.min.mjs` /
      // `pdf.worker.mjs`) — there is no `.min.js` build in this version.
      // We serve the version-matched worker as a static asset from /public
      // (copied there by the `copy-pdf-worker` build step in package.json).
      // The previous `new URL("pdfjs-dist/build/pdf.worker.min.mjs",
      // import.meta.url)` form made webpack emit the worker as an asset and
      // then run it through Terser, which crashes on the worker's ESM
      // `import`/`export` syntax ("cannot be used outside of module code") —
      // breaking `next build`. A static /public path sidesteps the bundler
      // entirely and keeps the API/Worker versions pinned together.
      mod.pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
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

  // Forward direction — page scroll. The overlay re-renders automatically on
  // the next `onRenderSuccess` once pdfjs paints the new page; we don't try
  // to draw it eagerly against the old viewport.
  useEffect(() => {
    if (!selected) return;
    const page = selected.finding.page;
    if (typeof page === "number" && page !== pageNumber) {
      setPageNumber(page);
    }
  }, [selected, pageNumber]);

  // Drop the cached viewport whenever the page changes — until pdfjs fires
  // the next `onRenderSuccess` with the new page's viewport, no overlay /
  // click-hit-test should run against the stale one.
  useEffect(() => {
    setViewport(null);
  }, [pageNumber]);

  const handleRenderSuccess = useCallback((page: unknown) => {
    // Narrow the proxy to the shape we use. pdfjs types are external; this
    // guard keeps the surface honest without leaking `any` into the file.
    if (
      typeof page === "object" &&
      page !== null &&
      "getViewport" in page &&
      typeof (page as { getViewport: unknown }).getViewport === "function"
    ) {
      const vp = (page as PdfPageProxyLike).getViewport({ scale: RENDER_SCALE });
      setViewport(vp);
    }
  }, []);

  // Reverse direction — page click → finding lookup. Translates the page-
  // relative CSS-pixel click into PDF coordinates via the cached viewport,
  // then finds the smallest-bbox hit on the current page (tie-broken by
  // clause_id so successive renders pick the same finding deterministically).
  const handlePageClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (!viewport) return;
      const wrap = pageWrapRef.current;
      if (!wrap) return;
      const rect = wrap.getBoundingClientRect();
      const cssX = event.clientX - rect.left;
      const cssY = event.clientY - rect.top;
      // pdfjs handles the PDF↔CSS y-axis flip internally — do NOT subtract
      // from viewport.height ourselves, that's the source-of-truth bug
      // pattern called out in the spec.
      const [pdfX, pdfY] = viewport.convertToPdfPoint(cssX, cssY);

      const hits = rows.filter(({ finding }) => {
        if (finding.page !== pageNumber) return false;
        const bbox = finding.pdf_bbox;
        if (!bbox) return false;
        // bbox = [x0, y0, x1, y1] in PDF coords. The server may emit either
        // order; normalize so a producer that swaps min/max doesn't blow up
        // the hit test.
        const xLo = Math.min(bbox[0], bbox[2]);
        const xHi = Math.max(bbox[0], bbox[2]);
        const yLo = Math.min(bbox[1], bbox[3]);
        const yHi = Math.max(bbox[1], bbox[3]);
        return pdfX >= xLo && pdfX <= xHi && pdfY >= yLo && pdfY <= yHi;
      });

      if (hits.length === 0) return;

      // Most-specific match first (smaller area = tighter bbox), then
      // lexicographic clause_id to keep selection deterministic across
      // re-renders / overlapping-bbox edge cases.
      hits.sort((a, b) => {
        const areaA = bboxArea(a.finding.pdf_bbox);
        const areaB = bboxArea(b.finding.pdf_bbox);
        if (areaA !== areaB) return areaA - areaB;
        return a.finding.clause_id.localeCompare(b.finding.clause_id);
      });
      onSelect(hits[0].finding.clause_id);
    },
    [viewport, rows, pageNumber, onSelect],
  );

  // Forward-direction overlay rectangle, computed in CSS px from the cached
  // viewport. Re-computes whenever `viewport`, `selected`, or `pageNumber`
  // changes — i.e. on every page render and every selection change.
  const overlay = useMemo(() => {
    if (!viewport || !selected) return null;
    const finding: RiskFinding = selected.finding;
    const decision: GatekeeperDecision = selected.decision;
    if (finding.page !== pageNumber) return null;
    const bbox = finding.pdf_bbox;
    if (!bbox) return null;
    const lane: Lane = decision.lane;

    // Convert BOTH corners then take min/max — PDF y-origin is bottom-left,
    // CSS y-origin is top-left, so `convertToViewportPoint` flips y and the
    // raw two outputs are no longer "top-left then bottom-right". Min/max
    // normalizes regardless of flip direction.
    const [vx0, vy0] = viewport.convertToViewportPoint(bbox[0], bbox[1]);
    const [vx1, vy1] = viewport.convertToViewportPoint(bbox[2], bbox[3]);
    const left = Math.min(vx0, vx1);
    const top = Math.min(vy0, vy1);
    const width = Math.abs(vx1 - vx0);
    const height = Math.abs(vy1 - vy0);
    return {
      style: { left, top, width, height },
      className: LANE_OVERLAY[lane],
    };
  }, [viewport, selected, pageNumber]);

  if (!dealId) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
        Select a deal to load its 8-K Exhibit 2.1 filing
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
  // Match lib/api.ts's API_BASE default — earlier this defaulted to "" which
  // silently hit the Next app origin (/filing/<id> → 404) instead of the
  // FastAPI host. Same default keeps the PDF pane and the SSE client aligned
  // when NEXT_PUBLIC_API_BASE is unset locally.
  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";
  const passcode = process.env.NEXT_PUBLIC_DEMO_PASSCODE ?? "";
  const pdfFile = {
    url: `${apiBase}/filing/${dealId}`,
    httpHeaders: { "X-Demo-Passcode": passcode },
    withCredentials: false,
  };

  return (
    <div ref={containerRef} className="h-full overflow-y-auto bg-surface">
      <div className="sticky top-0 z-10 border-b border-ink-faint bg-surface px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
        {dealId} · page {pageNumber}
      </div>
      {Doc ? (
        <Doc.Document file={pdfFile} onLoadError={(e) => console.warn("pdf load", e)}>
          {/* The rendered filing stays a real white document — it floats,
              centered, on the near-black pane so it reads as evidence-on-a-desk. */}
          <div className="flex justify-center p-4">
          {/* `position: relative` anchors the absolute overlay AND scopes the
              click handler to the rendered page region only — clicking the
              chrome above doesn't fire a reverse-lookup. */}
          <div
            ref={pageWrapRef}
            className="relative inline-block"
            onClick={handlePageClick}
          >
            <Doc.Page
              pageNumber={pageNumber}
              renderTextLayer
              renderAnnotationLayer={false}
              scale={RENDER_SCALE}
              onRenderSuccess={handleRenderSuccess}
            />
            {overlay && (
              <div
                aria-hidden
                className={`pointer-events-none absolute ${overlay.className}`}
                style={overlay.style}
              />
            )}
          </div>
          </div>
        </Doc.Document>
      ) : (
        <div className="p-6 font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">Loading PDF viewer…</div>
      )}
    </div>
  );
}

function bboxArea(bbox: [number, number, number, number] | null | undefined): number {
  if (!bbox) return Number.POSITIVE_INFINITY;
  return Math.abs(bbox[2] - bbox[0]) * Math.abs(bbox[3] - bbox[1]);
}
