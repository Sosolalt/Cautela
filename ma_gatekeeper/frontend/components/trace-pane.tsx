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
      <div className="p-4 text-sm text-neutral-500">
        Set <code className="font-mono">NEXT_PUBLIC_PHOENIX_URL</code> to your
        self-hosted Phoenix base URL to enable the trace pane.
      </div>
    );
  }

  if (!traceId) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center text-sm text-neutral-500">
        Select a finding to load its Phoenix trace.
      </div>
    );
  }

  // Default matches .env.example so a missing override doesn't 404 on
  // the project's actual Phoenix project name.
  const project = process.env.NEXT_PUBLIC_PHOENIX_PROJECT ?? "ma-gatekeeper";
  // Phoenix's deep-link URL has changed between minor releases — older
  // builds use `/projects/<id>/traces/<traceId>`, recent builds use
  // `/projects/<id>/spans?traceId=...`. The override is exposed via
  // env so D1 iframe-validation can pin the right form without
  // touching this component.
  const template =
    process.env.NEXT_PUBLIC_PHOENIX_TRACE_URL ??
    `${base}/projects/${project}/traces/${traceId}`;
  const src = template
    .replace("{base}", base)
    .replace("{project}", project)
    .replace("{traceId}", traceId);
  return (
    <iframe
      key={traceId}
      title="Arize Phoenix trace"
      src={src}
      className="h-full w-full border-0"
      sandbox="allow-scripts allow-same-origin allow-popups"
    />
  );
}
