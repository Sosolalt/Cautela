"use client";

import clsx from "clsx";

import type { CitationRef, GatekeeperDecision, Lane, RiskFinding } from "@/lib/types";
import { ReflectorLoopButton } from "./reflector-loop-button";

interface Row {
  finding: RiskFinding;
  decision: GatekeeperDecision;
}

interface Props {
  rows: Row[];
  status: "idle" | "streaming" | "done" | "error";
  selectedFindingId: string | null;
  onSelect: (id: string) => void;
  // §12 — current deal slug, forwarded to the Reflector LoopAgent button so
  // the streamed events can correlate with the open deal pane. Optional;
  // when null the button still runs (loop picks "last failing finding").
  dealId?: string | null;
}

const LANE_LABEL: Record<Lane, string> = {
  auto_clear: "Auto-clear",
  escalate: "Escalate",
  block: "Block",
};

// Lane chip — full-saturation backgrounds + matching `text-on-lane-*` ramps
// from design/tokens.ts. The earlier `bg-lane-clear/10 text-lane-clear` shape
// was tuned for a near-black surface; on the bg-white findings pane it washed
// out to ~1.5:1 contrast and read as off-palette beige. Full lane fill with the
// paired ink token is the brand-correct chip per SOURCE_OF_TRUTH.
const LANE_CLASS: Record<Lane, string> = {
  auto_clear: "bg-lane-clear text-ink-paper",
  escalate: "bg-lane-escalate text-ink-paper",
  block: "bg-lane-block text-neutral-50",
};

// Dependency-free arrow-up-right glyph (lucide-react is not a project dep).
// 12px, currentColor — the Phoenix span-link affordance per STATUTE_LAYER §4.1.
function SpanLinkGlyph() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </svg>
  );
}

// CitationRow — the user-facing citation surface (STATUTE_LAYER.md §4.1).
// Renders ONLY the deterministic, primary-source-verified CitationRef. Statute
// and case-law both render here, differentiated by the citation_kind badge.
// Deliberately uses no banned verbs (thinks/suggests/agrees/...) — the LLM
// proposer does not exist on this surface.
function CitationRow({ citation }: { citation: CitationRef }) {
  const kindLabel = citation.citation_kind.replace("_", " ");
  return (
    <div className="mt-1.5 border-t border-ink-dim pt-1.5">
      <div className="flex items-center gap-2">
        <span className="font-display text-[14px] font-semibold leading-tight text-ink">
          {citation.citation}
        </span>
        <span className="bg-ink-dim px-1 py-0.5 font-mono text-[11px] uppercase tracking-wide text-ink-muted">
          {kindLabel}
        </span>
        <span
          aria-hidden="true"
          className="inline-block h-2 w-2 shrink-0 bg-accent-champagne"
        />
        <span className="bg-accent-champagne/20 px-1 py-0.5 font-mono text-[11px] text-ink">
          {citation.jurisdiction}
        </span>
        <span className="ml-auto text-ink-muted" title="View Phoenix trace">
          <SpanLinkGlyph />
        </span>
      </div>
      <div className="mt-0.5 text-[10px] text-ink-muted">
        verified against {citation.primary_source} · {citation.verified_date}
      </div>
    </div>
  );
}

export function FindingsPane({ rows, status, selectedFindingId, onSelect, dealId }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-ink-faint px-3 py-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-muted">Findings</span>
        <span className="font-mono text-[11px] text-ink-faint">
          {status === "streaming" ? "streaming…" : `${rows.length} finding${rows.length === 1 ? "" : "s"}`}
        </span>
      </div>
      <ul className="flex-1 divide-y divide-ink-dim overflow-y-auto">
        {rows.map(({ finding, decision }) => {
          const selected = finding.clause_id === selectedFindingId;
          return (
            <li key={finding.clause_id}>
              <button
                type="button"
                onClick={() => onSelect(finding.clause_id)}
                className={clsx(
                  "block w-full border-l-4 border-transparent px-3 py-2 text-left text-sm transition-colors hover:bg-ink-dim",
                  // Selected-row affordance — a 4px vermillion left-edge bar (the
                  // hero's flag accent, carried through so "flag = vermillion"
                  // pays off here) + a subtle ink wash. The transparent
                  // left-border reserves the 4px so selecting doesn't shift layout.
                  selected && "border-accent-vermillion bg-ink-dim",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={clsx(
                      "px-1.5 py-0.5 text-xs font-medium",
                      LANE_CLASS[decision.lane],
                    )}
                  >
                    {LANE_LABEL[decision.lane]}
                  </span>
                  <span className="font-mono text-xs text-ink-muted">{finding.tag}</span>
                </div>
                <div className="mt-1 line-clamp-2 text-ink">
                  {finding.explanation || finding.clause_text.slice(0, 160)}
                </div>
                <div className="mt-1 font-mono text-xs text-ink-muted">
                  judge={finding.judge_score.toFixed(2)} · τ={decision.threshold_applied.toFixed(2)}
                </div>
                {finding.citation_ref ? (
                  <CitationRow citation={finding.citation_ref} />
                ) : null}
              </button>
            </li>
          );
        })}
        {rows.length === 0 && status !== "streaming" && (
          <li className="px-3 py-8 text-center font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
            Select a deal to start a review
          </li>
        )}
      </ul>
      <ReflectorLoopButton dealId={dealId ?? null} />
    </div>
  );
}
