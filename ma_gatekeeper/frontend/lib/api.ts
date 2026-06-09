// Typed client for the FastAPI server in agent/server.py.
//
// The /review and /review-by-deal endpoints are passcode-gated via the
// `X-Demo-Passcode` HEADER (never the query string — see server.py and
// SRE review round-A). Reading the passcode from NEXT_PUBLIC_DEMO_PASSCODE
// is fine for the demo since the gate is "make scrapers pay attention,"
// not authentication; the security-sensitive route is /reflect which is
// OIDC-protected and not callable from the browser at all.

import type {
  Deal,
  PortfolioReport,
  ReflectorLoopSseFrame,
  SseEvent,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";
const PASSCODE = process.env.NEXT_PUBLIC_DEMO_PASSCODE ?? "";

function headers(extra: HeadersInit = {}): HeadersInit {
  return { "X-Demo-Passcode": PASSCODE, ...extra };
}

export async function fetchAllowList(): Promise<Deal[]> {
  const res = await fetch(`${API_BASE}/allow-list`, { headers: headers() });
  if (!res.ok) throw new Error(`/allow-list ${res.status}`);
  const body = (await res.json()) as { deals: Deal[] };
  return body.deals;
}

/**
 * Fix 7 — fetch the Portfolio Analyst report.
 *
 * One Gemini 3 Pro call across all 30 Internal-30 contracts (mock-default
 * in dev; PORTFOLIO_LIVE=1 on the server flips to the live Vertex path).
 * Sync JSON response, NOT SSE — the output is one structured object.
 */
export async function fetchPortfolioReport(): Promise<PortfolioReport> {
  const res = await fetch(`${API_BASE}/portfolio`, {
    method: "POST",
    headers: headers(),
  });
  if (!res.ok) throw new Error(`/portfolio ${res.status}`);
  return (await res.json()) as PortfolioReport;
}

/**
 * §11 Build #3 / §12 — stream events from the Reflector LoopAgent.
 *
 * Triggers one on-demand LoopAgent run on the server (the "Run Reflector now"
 * button) and yields per-iteration sub-trace events via SSE. Same fetch +
 * ReadableStream pattern as streamReviewByDeal (EventSource cannot carry
 * the X-Demo-Passcode header). `dealId` is optional — when present the
 * server surfaces it on every event payload so the panel can show which
 * deal triggered the loop.
 */
export async function streamReflectorLoop(
  dealId: string | null,
  onEvent: (frame: ReflectorLoopSseFrame) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/reflect/loop`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ deal_id: dealId }),
    signal,
  });
  if (!res.ok) throw new Error(`/reflect/loop ${res.status}`);
  if (!res.body) throw new Error("/reflect/loop returned empty body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const frameDelim = /\r?\n\r?\n/;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    while (true) {
      const match = frameDelim.exec(buffer);
      if (!match) break;
      const frame = buffer.slice(0, match.index);
      buffer = buffer.slice(match.index + match[0].length);
      const line = frame.split(/\r?\n/).find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice("data: ".length);
      try {
        onEvent(JSON.parse(payload) as ReflectorLoopSseFrame);
      } catch (err) {
        onEvent({
          event: "error",
          stage: "frontend_sse_parse",
          message: `bad reflector-loop SSE frame: ${(err as Error).message}; ${payload.slice(0, 80)}`,
        });
      }
    }
  }
}

/**
 * Stream review events for a deal via SSE. EventSource doesn't support
 * custom headers, so we use fetch + a ReadableStream reader. Caller passes
 * an `onEvent` callback and (optionally) an AbortSignal to cancel.
 */
export async function streamReviewByDeal(
  dealId: string,
  onEvent: (event: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/review-by-deal`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ deal_id: dealId }),
    signal,
  });
  if (!res.ok) throw new Error(`/review-by-deal ${res.status}`);
  if (!res.body) throw new Error("/review-by-deal returned empty body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  // SSE delimiter is "\n\n" per spec, but proxies may rewrite to
  // "\r\n\r\n"; accept either with a regex split. Cloud Run preserves
  // "\n\n" but third-party reverse proxies (e.g. through Cloudflare,
  // ngrok) sometimes don't.
  const frameDelim = /\r?\n\r?\n/;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    while (true) {
      const match = frameDelim.exec(buffer);
      if (!match) break;
      const frame = buffer.slice(0, match.index);
      buffer = buffer.slice(match.index + match[0].length);
      const line = frame.split(/\r?\n/).find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice("data: ".length);
      try {
        onEvent(JSON.parse(payload) as SseEvent);
      } catch (err) {
        // Fail loud — a malformed SSE frame is the round-A "demo looks clean
        // when it's actually broken" failure mode (server.py line 240).
        onEvent({
          event: "error",
          stage: "frontend_sse_parse",
          message: `bad SSE frame: ${(err as Error).message}; ${payload.slice(0, 80)}`,
        });
      }
    }
  }
}
