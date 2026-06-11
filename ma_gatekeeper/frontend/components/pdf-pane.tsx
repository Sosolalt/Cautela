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

// ---------------------------------------------------------------------------
// HTML-exhibit highlighter (the common case — EDGAR Ex 2.1 is almost always
// HTML, which has no pages/pdf_bbox, so the PDF overlay path can't engage).
//
// We OWN the document bytes before they become a blob: URL, so we splice a
// tiny self-contained highlighter into the HTML and create the blob from the
// modified source. The frame runs under `sandbox="allow-scripts"` — scripts
// only, NEVER `allow-same-origin`, so the frame stays in an opaque origin and
// can't reach back into the app. Coordination is one-way postMessage:
//
//   parent → frame : { source:"cautela", type:"highlight", texts:[...] }
//   frame  → parent: { source:"cautela-frame", type:"ready" }
//
// The frame builds a flat text index of the document once, then for each
// candidate string (verbatim cited span first, then clause_text) does a
// whitespace-tolerant regex match, shortening word-by-word until it lands —
// converting "exact clause or nothing" into "scrolls to the right passage".
// It draws non-destructive overlay bands from the matched Range's client rects
// (no DOM surgery — legacy EDGAR <font>/nested-table markup must not be
// re-serialized) and smooth-scrolls the first rect to center.
//
// SECURITY INVARIANT: the iframe `sandbox` attr below is the literal string
// "allow-scripts" with no "allow-same-origin". Do not add it.
const HIGHLIGHTER_SNIPPET = `
<style id="cautela-hl-style">
  ::selection{background:rgba(230,61,47,0.28)}
  .cautela-band{position:absolute;background:rgba(230,61,47,0.18);border-left:3px solid #E63D2F;box-shadow:0 0 0 1px rgba(230,61,47,0.28) inset;pointer-events:none;z-index:2147483646}
</style>
<script>
(function(){
  var bands=[]; var idx=null;
  function clearBands(){ for(var i=0;i<bands.length;i++){ var b=bands[i]; if(b.parentNode) b.parentNode.removeChild(b); } bands=[]; }
  function esc(s){ return s.replace(/[-[\\]{}()*+?.,\\\\^$|#\\s]/g, "\\\\$&"); }
  function buildIndex(){
    if(!document.body) return {nodes:[],starts:[],text:""};
    var walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    var nodes=[], starts=[], text=""; var n;
    while((n=walker.nextNode())){
      var p=n.parentNode; if(!p) continue;
      var nm=p.nodeName; if(nm==="SCRIPT"||nm==="STYLE") continue;
      starts.push(text.length); nodes.push(n); text+=n.nodeValue;
    }
    return {nodes:nodes, starts:starts, text:text};
  }
  function locate(ix, pos){
    var lo=0, hi=ix.nodes.length-1, ans=0;
    while(lo<=hi){ var mid=(lo+hi)>>1; if(ix.starts[mid]<=pos){ans=mid;lo=mid+1;} else {hi=mid-1;} }
    return {node:ix.nodes[ans], offset:pos-ix.starts[ans]};
  }
  function draw(s,e){
    var a=locate(idx,s), b=locate(idx,e);
    var range=document.createRange();
    try{
      range.setStart(a.node, Math.min(a.offset, a.node.nodeValue.length));
      range.setEnd(b.node, Math.min(b.offset, b.node.nodeValue.length));
    }catch(err){ return false; }
    var rects=range.getClientRects();
    if(!rects.length) return false;
    var sx=window.scrollX||window.pageXOffset||0, sy=window.scrollY||window.pageYOffset||0;
    for(var i=0;i<rects.length;i++){
      var r=rects[i]; if(r.width<1||r.height<1) continue;
      var band=document.createElement("div");
      band.className="cautela-band";
      band.style.left=(r.left+sx-2)+"px";
      band.style.top=(r.top+sy-1)+"px";
      band.style.width=(r.width+4)+"px";
      band.style.height=(r.height+2)+"px";
      document.body.appendChild(band); bands.push(band);
    }
    var first=rects[0];
    if(first){ try{ window.scrollTo({top:first.top+sy-(window.innerHeight/2), left:0, behavior:"smooth"}); }catch(e2){ window.scrollTo(0, first.top+sy-120); } }
    return bands.length>0;
  }
  function tryOne(raw){
    var words=String(raw||"").trim().split(/\\s+/);
    words=words.slice(0,14);
    if(words.length<3) return false;
    var escd=words.map(esc);
    for(var len=escd.length; len>=3; len--){
      var re;
      try{ re=new RegExp(escd.slice(0,len).join("\\\\s+"), "i"); }catch(e){ continue; }
      var m=re.exec(idx.text);
      if(m){ if(draw(m.index, m.index+m[0].length)) return true; }
    }
    return false;
  }
  function onMsg(ev){
    var d=ev.data;
    if(!d || d.source!=="cautela" || d.type!=="highlight") return;
    clearBands();
    if(!idx) idx=buildIndex();
    if(!idx.text) return;
    var list=d.texts||[];
    for(var t=0;t<list.length;t++){ if(tryOne(list[t])) break; }
  }
  function announce(){ try{ parent.postMessage({source:"cautela-frame", type:"ready"}, "*"); }catch(e){} }
  window.addEventListener("message", onMsg);
  if(document.readyState==="complete"||document.readyState==="interactive"){ announce(); }
  else { document.addEventListener("DOMContentLoaded", announce); }
  window.addEventListener("load", announce);
})();
</script>
`;

// Splice the highlighter in just before </body> (or append if the legacy
// markup has no closing body tag). Done on the parent side so the only thing
// that crosses into the opaque-origin frame is inert HTML + our own script.
function injectHighlighter(rawHtml: string): string {
  const lower = rawHtml.toLowerCase();
  const at = lower.lastIndexOf("</body>");
  if (at === -1) return rawHtml + HIGHLIGHTER_SNIPPET;
  return rawHtml.slice(0, at) + HIGHLIGHTER_SNIPPET + rawHtml.slice(at);
}

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

  // Document-kind detection. /filing/{dealId} returns the original EDGAR
  // Ex 2.1 with its real Content-Type — almost always text/html, occasionally
  // application/pdf. We fetch it once (the endpoint needs the passcode header,
  // so we can't just point an <iframe src> at it), branch on the type, and hand
  // a same-origin blob: URL to either react-pdf (pdf) or a sandboxed iframe
  // (html). HTML filings have no pages/pdf_bbox, so the bbox-highlight path
  // simply doesn't engage for them — the pane still shows the full document.
  const [filing, setFiling] = useState<{
    kind: "loading" | "html" | "pdf" | "error";
    url: string | null;
  }>({ kind: "loading", url: null });

  // HTML-highlighter coordination. `frameReady` flips when the injected
  // in-frame script posts its "ready" handshake; until then a selection that
  // arrives early is held and replayed by the post-effect once ready.
  const htmlFrameRef = useRef<HTMLIFrameElement>(null);
  const [frameReady, setFrameReady] = useState(false);

  useEffect(() => {
    if (!dealId) {
      setFiling({ kind: "loading", url: null });
      return;
    }
    let cancelled = false;
    let objUrl: string | null = null;
    setFiling({ kind: "loading", url: null });
    const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";
    const passcode = process.env.NEXT_PUBLIC_DEMO_PASSCODE ?? "";
    fetch(`${apiBase}/filing/${dealId}`, {
      headers: { "X-Demo-Passcode": passcode },
    })
      .then(async (res) => {
        const ct = (res.headers.get("content-type") ?? "").toLowerCase();
        const isPdf = ct.includes("pdf");
        if (isPdf) {
          const blob = await res.blob();
          if (cancelled) return;
          objUrl = URL.createObjectURL(blob);
          setFiling({ kind: "pdf", url: objUrl });
        } else {
          // HTML branch: read the source, splice in the highlighter, and build
          // the blob from the modified bytes so finding-clicks can scroll +
          // highlight the cited passage inside the otherwise-opaque iframe.
          const raw = await res.text();
          if (cancelled) return;
          const blob = new Blob([injectHighlighter(raw)], { type: "text/html" });
          objUrl = URL.createObjectURL(blob);
          setFiling({ kind: "html", url: objUrl });
        }
      })
      .catch(() => {
        if (!cancelled) setFiling({ kind: "error", url: null });
      });
    return () => {
      cancelled = true;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [dealId]);

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

  // Each new filing URL mounts a fresh iframe — drop the ready flag until the
  // new frame re-announces, so we don't post into the previous document.
  useEffect(() => {
    setFrameReady(false);
  }, [filing.url]);

  // Listen for the frame's one-way "ready" handshake. The frame is opaque-
  // origin (sandbox=allow-scripts only) so we can't read into it; we only
  // accept the inert ready ping and gate posting on it.
  useEffect(() => {
    function onMessage(ev: MessageEvent) {
      const data = ev.data as { source?: string; type?: string } | null;
      if (data && data.source === "cautela-frame" && data.type === "ready") {
        setFrameReady(true);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  // Forward direction for HTML filings: post the selected finding's cited text
  // (verbatim span first, then clause_text as fallback) into the frame, which
  // scrolls + highlights it. Empty payload (no selection) clears the highlight.
  useEffect(() => {
    if (filing.kind !== "html" || !frameReady) return;
    const win = htmlFrameRef.current?.contentWindow;
    if (!win) return;
    const texts = selected
      ? [selected.finding.cited_spans_text, selected.finding.clause_text].filter(
          (t): t is string => typeof t === "string" && t.trim().length > 0,
        )
      : [];
    win.postMessage({ source: "cautela", type: "highlight", texts }, "*");
  }, [filing.kind, frameReady, selected]);

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

  const headerLabel =
    filing.kind === "pdf" ? `${dealId} · page ${pageNumber}` : `${dealId} · Exhibit 2.1`;

  return (
    <div ref={containerRef} className="h-full overflow-y-auto bg-surface">
      <div className="sticky top-0 z-10 border-b border-ink-faint bg-surface px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
        {headerLabel}
      </div>

      {filing.kind === "loading" && (
        <div className="p-6 font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
          Loading filing…
        </div>
      )}

      {filing.kind === "error" && (
        <div className="p-6 font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
          Could not load the filing.
        </div>
      )}

      {/* HTML EDGAR exhibit (the common case): render the real document in a
          scripts-only sandboxed blob iframe. HTML filings have no pages/pdf_bbox,
          so instead of the PDF bbox overlay we splice a postMessage highlighter
          into the source (injectHighlighter) — clicking a finding scrolls the
          frame to the cited passage and draws a vermillion band. sandbox is
          "allow-scripts" with NO allow-same-origin: the frame stays opaque-origin
          and cannot reach back into the app. */}
      {filing.kind === "html" && filing.url && (
        <iframe
          ref={htmlFrameRef}
          title={`${dealId} Exhibit 2.1`}
          src={filing.url}
          sandbox="allow-scripts"
          className="h-[calc(100%-2.5rem)] min-h-[70vh] w-full border-0 bg-white"
        />
      )}

      {filing.kind === "pdf" && filing.url && (
        Doc ? (
          <Doc.Document file={filing.url} onLoadError={(e) => console.warn("pdf load", e)}>
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
        )
      )}
    </div>
  );
}

function bboxArea(bbox: [number, number, number, number] | null | undefined): number {
  if (!bbox) return Number.POSITIVE_INFINITY;
  return Math.abs(bbox[2] - bbox[0]) * Math.abs(bbox[3] - bbox[1]);
}
