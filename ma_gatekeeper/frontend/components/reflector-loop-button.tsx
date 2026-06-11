"use client";

// §11 Build #3 / §12 — "Run Reflector now" button + status panel.
//
// Minimal functional UI per dispatch spec: bare button + a small panel
// underneath that renders the streamed SSE events from /reflect/loop in
// arrival order. No new fonts, no new tokens, no animation beyond what
// Documentary-Brutalism already exposes via design/tokens.ts. Styles
// stay inside existing Tailwind utility classes + the project's
// lane-* / neutral-* / accent-* token families.

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";

import { streamReflectorLoop } from "@/lib/api";
import { buildPhoenixTraceUrl, resolvePhoenixProjectId } from "@/lib/phoenix";
import type {
  ReflectorLoopEvent,
  ReflectorLoopSseFrame,
} from "@/lib/types";

interface Props {
  dealId: string | null;
}

type RunStatus = "idle" | "running" | "done" | "error";

// Render the kind label that the partner reads off-screen during the demo.
const KIND_LABEL: Record<ReflectorLoopEvent["kind"], string> = {
  loop_started: "LoopAgent spawned",
  iteration_started: "iteration started",
  mcp_traces_listed: "Phoenix MCP list_traces",
  candidate_generated: "candidate prompt generated",
  experiment_complete: "Phoenix Experiment complete",
  frozen_fold_check: "frozen-fold non-regression check",
  iteration_complete: "iteration complete",
  auto_promoted: "AUTO-PROMOTED",
  no_promotion: "no candidate passed gate",
  error: "error",
};

function formatPayloadHint(evt: ReflectorLoopEvent): string {
  const p = evt.payload;
  switch (evt.kind) {
    case "mcp_traces_listed":
      return typeof p.trace_count === "number"
        ? `${p.trace_count} trace${p.trace_count === 1 ? "" : "s"}`
        : "";
    case "experiment_complete":
      return typeof p.ci_lower_bound === "number"
        ? `CI lower = ${(p.ci_lower_bound as number).toFixed(3)}`
        : "";
    case "frozen_fold_check": {
      const d = p.fold5_delta;
      const eps = p.epsilon_fold5;
      if (typeof d === "number" && typeof eps === "number") {
        return `Δ=${d.toFixed(3)} (ε=${eps.toFixed(3)})`;
      }
      return "";
    }
    case "candidate_generated":
      return typeof p.candidate_prompt_version === "string"
        ? String(p.candidate_prompt_version)
        : "";
    case "auto_promoted": {
      const v = p.prompt_version;
      const pr = p.auto_pr_url;
      if (typeof pr === "string" && pr) return `PR: ${pr}`;
      if (typeof v === "string") return `version ${v}`;
      return "";
    }
    default:
      return "";
  }
}

export function ReflectorLoopButton({ dealId }: Props) {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [events, setEvents] = useState<ReflectorLoopEvent[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const logRef = useRef<HTMLOListElement | null>(null);

  // Cancel any in-flight stream on unmount so a late setEvents / setStatus
  // after the component is gone doesn't crash with the React-18 set-on-
  // unmounted warning. Mirrors the page.tsx pattern.
  useEffect(() => () => abortRef.current?.abort(), []);

  // Resolve Phoenix's opaque project node id once (cached promise, shared with
  // the trace pane) so the per-event "trace" links use the id, not the human
  // name — the name 404s with "Unknown node".
  const [phoenixPid, setPhoenixPid] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    resolvePhoenixProjectId().then((p) => {
      if (!cancelled) setPhoenixPid(p);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const onClick = useCallback(async () => {
    if (status === "running") return;
    setEvents([]);
    setErrorMsg(null);
    setStatus("running");
    const ctl = new AbortController();
    abortRef.current = ctl;
    try {
      await streamReflectorLoop(
        dealId,
        (frame: ReflectorLoopSseFrame) => {
          if (frame.event === "reflector_loop") {
            // Strip the discriminator before storing.
            const { event: _ignore, ...evt } = frame;
            setEvents((prev) => [...prev, evt as ReflectorLoopEvent]);
          } else if (frame.event === "error") {
            setErrorMsg(`${frame.stage}: ${frame.message}`);
          } else if (frame.event === "done") {
            setStatus((s) => (s === "error" ? "error" : "done"));
          }
        },
        ctl.signal,
      );
      // If we exit without an explicit `done` frame, settle on "done" so the
      // UI doesn't sit on "running" forever — and don't paint a red "error"
      // badge for a stream that completed quietly (the bug here flipped
      // successful no-promotion runs to error at the climax moment).
      setStatus((s) => (s === "running" ? "done" : s));
    } catch (err) {
      // User-initiated cancel (unmount, navigation) is not an error.
      if ((err as Error).name === "AbortError") return;
      setErrorMsg((err as Error).message);
      setStatus("error");
    }
  }, [dealId, status]);

  // Auto-scroll the event log so the most recent frame is always visible —
  // the AUTO-PROMOTED row is the climax beat and must not scroll off-screen
  // when 6+ events have streamed.
  useEffect(() => {
    const el = logRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [events.length, errorMsg]);

  const promotedEvent = events.find((e) => e.kind === "auto_promoted");
  const noPromotionEvent = events.find((e) => e.kind === "no_promotion");
  // AUTO-PROMOTED is the demo climax stamp. The earlier `bg-lane-clear
  // text-neutral-50` shape was ~1.5:1 contrast (champagne-soft #E0CB94 under
  // warm-paper #F4F2EC ink) and read as a faded chip on stream. Champagne-deep
  // with paper-white ink stamps hard at 1080p.
  const badge = promotedEvent
    ? { label: "AUTO-PROMOTED", cls: "bg-accent-champagne-deep text-neutral-50" }
    : noPromotionEvent
      ? { label: "NO PROMOTION", cls: "bg-ink-dim text-ink-muted" }
      : null;

  return (
    <div className="border-t border-ink-faint bg-ink-dim/30 px-3 py-3 text-sm">
      {/* Distinct self-improvement panel — deliberately boxed off + captioned so
          it never reads as the review's run trigger (the review auto-starts on
          deal select). This is the Phoenix self-optimization loop: it tunes the
          judge from eval traces and auto-promotes a better prompt. */}
      <div className="mb-2 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-ink-faint">
        Self-improvement · Phoenix
      </div>
      <div className="flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={onClick}
          disabled={status === "running"}
          className={clsx(
            "border border-accent-vermillion bg-transparent px-4 py-1.5 font-mono text-xs uppercase tracking-[0.14em] text-accent-vermillion transition-colors",
            "hover:bg-accent-vermillion hover:text-surface disabled:cursor-not-allowed disabled:opacity-60",
          )}
        >
          {status === "running" ? "Self-improving…" : "Self-improve now"}
        </button>
        {badge && (
          <span
            className={clsx(
              "px-2 py-0.5 font-mono text-xs",
              badge.cls,
            )}
          >
            {badge.label}
          </span>
        )}
      </div>
      {(events.length > 0 || errorMsg) && (
        <ol
          ref={logRef}
          className="mt-2 max-h-48 space-y-1 overflow-y-auto font-mono text-xs"
        >
          {events.map((evt, idx) => {
            const hint = formatPayloadHint(evt);
            const trace = evt.trace_id;
            const traceHref = trace ? buildPhoenixTraceUrl(trace, phoenixPid) : null;
            return (
              <li key={idx} className="flex items-baseline gap-2 text-ink-muted">
                <span className="w-6 text-right text-ink-faint">
                  {evt.iteration !== null ? `#${evt.iteration}` : ""}
                </span>
                <span className="flex-1">
                  <span className="text-ink">{KIND_LABEL[evt.kind]}</span>
                  {hint && <span className="ml-2 text-ink-muted">{hint}</span>}
                </span>
                {traceHref && evt.kind === "iteration_started" && (
                  <a
                    href={traceHref}
                    target="_blank"
                    rel="noreferrer"
                    className="underline"
                  >
                    trace
                  </a>
                )}
                {evt.kind === "auto_promoted" &&
                  typeof evt.payload.auto_pr_url === "string" &&
                  evt.payload.auto_pr_url && (
                    <a
                      href={String(evt.payload.auto_pr_url)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-ink-muted underline hover:text-ink"
                    >
                      PR
                    </a>
                  )}
              </li>
            );
          })}
          {errorMsg && (
            <li className="text-lane-block">error: {errorMsg}</li>
          )}
        </ol>
      )}
    </div>
  );
}
