"use client";

interface Props {
  /**
   * Phoenix UI path to embed, relative to NEXT_PUBLIC_PHOENIX_URL. Defaults to
   * the project board. For the Reflector auto-promotion climax, point this at
   * the Experiments/datasets view (e.g. "/datasets") so the judge sees the
   * Phoenix-native prompt-version + experiment runs — the un-fakeable proof.
   */
  path?: string;
  /** Header label shown above the embed. */
  label?: string;
}

/**
 * Embeds a full Arize Phoenix board (project traces, or the Experiments view)
 * as a direct cross-origin <iframe>. This works because the self-hosted
 * phoenix-prod sends NO `X-Frame-Options` and NO CSP `frame-ancestors`
 * (verified 2026-06-10) — so framing is not blocked.
 *
 * Companion to <TracePane> (which embeds a single trace): <PhoenixBoard> is for
 * the wider board surface — the demo's auto-promotion money-moment lives in
 * Phoenix's own Experiments view, and showing it natively here is the strongest
 * "the observability is real, not a mock" signal for an Arize judge.
 *
 * Native data fetching (a bespoke trace-card) can instead hit the same-origin
 * `/phoenix-api/*` proxy wired in next.config.mjs (defeats Phoenix's missing
 * CORS headers); this component intentionally embeds the real Phoenix UI for
 * authenticity rather than re-rendering it.
 */
export function PhoenixBoard({
  path = `/projects/${process.env.NEXT_PUBLIC_PHOENIX_PROJECT || "ma-gatekeeper"}`,
  label = "Arize Phoenix",
}: Props) {
  const base = process.env.NEXT_PUBLIC_PHOENIX_URL;

  if (!base) {
    return (
      <div className="flex h-full flex-col">
        <PhoenixBoardHeader label={label} />
        <div className="flex flex-1 items-center justify-center p-6 text-center font-mono text-xs leading-relaxed text-ink-muted">
          <span>
            Set <code className="text-ink-muted">NEXT_PUBLIC_PHOENIX_URL</code> to
            your self-hosted Phoenix base URL to embed the board.
          </span>
        </div>
      </div>
    );
  }

  const src = `${base}${path}`;
  return (
    <div className="flex h-full flex-col">
      <PhoenixBoardHeader label={label} />
      <iframe
        title="Arize Phoenix board"
        src={src}
        loading="lazy"
        className="w-full flex-1 border-0 bg-surface"
        sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms"
      />
    </div>
  );
}

function PhoenixBoardHeader({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-between border-b border-hairline px-4 py-2">
      <span className="font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
        {label}
      </span>
    </div>
  );
}
