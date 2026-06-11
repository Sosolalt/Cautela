// Shared Phoenix helpers.
//
//  - `buildPhoenixTraceUrl` / `phoenixTraceUrlResolved` build the deep-link to
//    the full Phoenix trace UI. CRITICAL: the `/projects/<X>` path needs
//    Phoenix's OPAQUE node id (e.g. "UHJvamVjdDo1"), resolved at runtime via
//    `resolvePhoenixProjectId` — passing the human project name 404s with
//    "Unknown node: <name>". This is the canonical copy; the per-component
//    duplicates (portfolio-pane, reflector-loop-button) were removed.
//  - `fetchTraceSummary` reads a COMPACT trace summary (status / latency /
//    span count / top spans) client-side via the SAME-ORIGIN `/phoenix-api`
//    rewrite (next.config.mjs: `/phoenix-api/:path*` -> `{phoenix}/v1/:path*`).
//    No auth, no CORS — the proxy is same-origin. This powers the in-app
//    trace card so the col-span-3 pane never has to embed Phoenix's full SPA.
//
// Cost ($) is deliberately NOT fetched here: it is a Phoenix trace-level
// aggregate, not a root-span field, and a fabricated figure in front of an
// M&A reviewer is worse than none. Cost lives one click away behind the CTA.

export interface TraceSpanDigest {
  name: string;
  ms: number | null;
}

export interface TraceSummary {
  status: string | null; // root span status_code, e.g. "OK"
  statusMessage: string | null;
  latencyMs: number | null; // root end_time - start_time
  spanCount: number;
  spans: TraceSpanDigest[]; // top-N by duration
}

/**
 * Build the full-Phoenix-UI deep-link for a trace, or null when unconfigured.
 *
 * `projectId` MUST be Phoenix's OPAQUE node id (e.g. "UHJvamVjdDo1"), obtained
 * from `resolvePhoenixProjectId`. Phoenix's `/projects/<X>` route resolves <X>
 * as a node id, NOT the human project name — passing the name 404s with
 * "Unknown node: <name>". When `projectId` is omitted we fall back to the name
 * env (still 404-prone; only for the brief pre-resolution window).
 */
export function buildPhoenixTraceUrl(
  traceId: string,
  projectId?: string | null,
): string | null {
  const base = process.env.NEXT_PUBLIC_PHOENIX_URL;
  if (!base) return null;
  const project =
    projectId ?? (process.env.NEXT_PUBLIC_PHOENIX_PROJECT || "ma-gatekeeper");
  const template = process.env.NEXT_PUBLIC_PHOENIX_TRACE_URL;
  return template
    ? template
        .replace("{base}", base)
        .replace("{project}", project)
        .replace("{traceId}", traceId)
    : `${base}/projects/${project}/traces/${traceId}`;
}

/**
 * Resolve Phoenix's opaque project node id (cached promise, shared with the
 * summary fetch). Exposed so components that build MANY links (e.g. the
 * Reflector event log) can resolve once and build synchronously.
 */
export function resolvePhoenixProjectId(): Promise<string | null> {
  return resolveProjectId();
}

/**
 * Convenience: resolve the opaque project id, then build the deep-link. Use
 * for single links (TracePane CTA, Portfolio header). Null when unconfigured.
 *
 * Intentionally takes NO AbortSignal: the project-id lookup is a shared,
 * cached, once-per-session request that MUST NOT be cancelled by a caller's
 * per-request controller (doing so resolved it to null → links fell back to
 * the human project name → Phoenix "Unknown node").
 */
export async function phoenixTraceUrlResolved(
  traceId: string,
): Promise<string | null> {
  const base = process.env.NEXT_PUBLIC_PHOENIX_URL;
  if (!base) return null;
  const pid = await resolvePhoenixProjectId();
  return buildPhoenixTraceUrl(traceId, pid);
}

/** Human-coarse duration: "820ms" / "4.1s" / "6m 32s". */
export function formatDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

// Phoenix's REST project id is an opaque base64 string (e.g. "UHJvamVjdDo1"),
// NOT the human project name — so we resolve it once per session and cache it.
// The promise itself is cached so concurrent finding-clicks don't fan out N
// identical /projects calls; on failure the cache is cleared so a later click
// can retry.
let _pidPromise: Promise<string | null> | null = null;

interface ProjectRow {
  name: string;
  id: string;
}

function resolveProjectId(): Promise<string | null> {
  if (_pidPromise) return _pidPromise;
  const name = process.env.NEXT_PUBLIC_PHOENIX_PROJECT || "ma-gatekeeper";
  // NOT abortable on purpose: this shared, cached lookup must always run to
  // completion. Passing a caller's AbortController signal here let one
  // aborted request (a fast finding-switch during streaming) cancel the
  // shared fetch → it resolved null → deep-links 404'd on the project name.
  _pidPromise = fetch("/phoenix-api/projects")
    .then((r) => (r.ok ? r.json() : null))
    .then((j: { data?: ProjectRow[] } | null) => {
      const row = j?.data?.find((p) => p.name === name);
      return row?.id ?? null;
    })
    .catch(() => {
      _pidPromise = null; // allow retry on a later selection
      return null;
    });
  return _pidPromise;
}

// In-session cache of summaries by trace_id. Tiny objects; unbounded is fine
// for a demo session, and it is what makes a re-clicked finding's card snap in
// with zero fetch (the demo reveal beat).
const _summaryCache = new Map<string, TraceSummary>();

interface RawSpan {
  context?: { trace_id?: string };
  name?: string;
  parent_id?: string | null;
  start_time?: string;
  end_time?: string;
  status_code?: string;
  status_message?: string;
}

function spanMs(s: RawSpan): number | null {
  if (!s.start_time || !s.end_time) return null;
  const ms = new Date(s.end_time).getTime() - new Date(s.start_time).getTime();
  // Clamp clock-skew negatives to null rather than show a negative latency.
  return Number.isFinite(ms) && ms >= 0 ? ms : null;
}

/**
 * Fetch a compact summary for one trace. Returns null (a benign empty state,
 * never a throw) when the trace isn't indexed yet, the project can't be
 * resolved, or Phoenix returns an unexpected shape — callers fall through to
 * the "open in Phoenix" CTA, which has no REST dependency.
 */
export async function fetchTraceSummary(
  traceId: string,
  signal?: AbortSignal,
): Promise<TraceSummary | null> {
  const cached = _summaryCache.get(traceId);
  if (cached) return cached;

  const pid = await resolveProjectId();
  if (!pid) return null;

  // limit=500 to raise the odds the wanted trace is on the first page of a
  // busy project; if it still isn't present we treat it as "not yet indexed"
  // rather than paging aggressively from the browser.
  const res = await fetch(`/phoenix-api/projects/${pid}/spans?limit=500`, {
    signal,
  });
  if (!res.ok) return null;
  const json: { data?: RawSpan[] } = await res.json();
  const all = json?.data ?? [];
  const spans = all.filter((s) => s.context?.trace_id === traceId);
  if (spans.length === 0) return null; // OTel export lag / off the first page

  // Root span = the parentless one; if several, earliest start_time; if none,
  // earliest span overall so status/latency still render.
  const parentless = spans.filter((s) => !s.parent_id);
  const pool = parentless.length ? parentless : spans;
  const root = pool
    .slice()
    .sort((a, b) => (a.start_time ?? "").localeCompare(b.start_time ?? ""))[0];

  const top = spans
    .map((s) => ({ name: s.name ?? "span", ms: spanMs(s) }))
    .sort((a, b) => (b.ms ?? 0) - (a.ms ?? 0))
    .slice(0, 5);

  const summary: TraceSummary = {
    status: root?.status_code ?? null,
    statusMessage: root?.status_message || null,
    latencyMs: root ? spanMs(root) : null,
    spanCount: spans.length,
    spans: top,
  };
  _summaryCache.set(traceId, summary);
  return summary;
}
