"use client";

interface Props {
  traceId: string | null;
}

/**
 * Phoenix trace pane. Default is an iframe pointed at the self-hosted
 * Phoenix instance — the D1 iframe-validation decision (HANDOFF.md)
 * determines whether we keep this or fall back to a custom trace-card.
 *
 * The cmd+click reveal moment in the demo (plan §8) depends on this
 * iframe ALREADY having the trace loaded when the user clicks a finding,
 * so the URL must update synchronously with selectedFindingId — no
 * waiting on a separate fetch.
 */
export function TracePane({ traceId }: Props) {
  const base = process.env.NEXT_PUBLIC_PHOENIX_URL;

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

  // Default matches .env.example so a missing override doesn't 404 on
  // the project's actual Phoenix project name. `||` rather than `??` so
  // that an empty-string env var (the shape `.env.example` ships) also
  // falls through to the default — `??` only catches null/undefined and
  // the iframe `src` would otherwise render the bare template literal.
  const project = process.env.NEXT_PUBLIC_PHOENIX_PROJECT || "ma-gatekeeper";
  // Phoenix's deep-link URL has changed between minor releases — older
  // builds use `/projects/<id>/traces/<traceId>`, recent builds use
  // `/projects/<id>/spans?traceId=...`. The override is exposed via
  // env so D1 iframe-validation can pin the right form without
  // touching this component.
  const template =
    process.env.NEXT_PUBLIC_PHOENIX_TRACE_URL ||
    `${base}/projects/${project}/traces/${traceId}`;
  const src = template
    .replace("{base}", base)
    .replace("{project}", project)
    .replace("{traceId}", traceId);
  return (
    <div className="flex h-full flex-col">
      <TracePaneHeader label="Phoenix trace · Verdict" traceId={traceId} />
      <iframe
        key={traceId}
        title="Arize Phoenix trace"
        src={src}
        loading="lazy"
        className="w-full flex-1 border-0 bg-surface"
        // `allow-forms` is required for Phoenix's in-iframe filter/search UI
        // during the cmd+click reveal moment; without it the controls
        // silently fail. `allow-popups-to-escape-sandbox` lets Phoenix's
        // own deep-links open outside our sandbox attribute set.
        sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms"
      />
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
