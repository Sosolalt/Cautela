"use client";

import clsx from "clsx";

import type { GatekeeperDecision, Lane, RiskFinding } from "@/lib/types";

interface Row {
  finding: RiskFinding;
  decision: GatekeeperDecision;
}

interface Props {
  rows: Row[];
  status: "idle" | "streaming" | "done" | "error";
  selectedFindingId: string | null;
  onSelect: (id: string) => void;
}

const LANE_LABEL: Record<Lane, string> = {
  auto_clear: "Auto-clear",
  escalate: "Escalate",
  block: "Block",
};

const LANE_CLASS: Record<Lane, string> = {
  auto_clear: "bg-lane-auto/10 text-lane-auto",
  escalate: "bg-lane-watch/15 text-yellow-800",
  block: "bg-lane-block/15 text-lane-block",
};

export function FindingsPane({ rows, status, selectedFindingId, onSelect }: Props) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-neutral-200 px-3 py-2 text-sm">
        <span className="font-medium text-neutral-700">Findings</span>
        <span className="text-xs text-neutral-500">
          {status === "streaming" ? "streaming…" : `${rows.length} finding${rows.length === 1 ? "" : "s"}`}
        </span>
      </div>
      <ul className="flex-1 divide-y divide-neutral-100 overflow-y-auto">
        {rows.map(({ finding, decision }) => {
          const selected = finding.clause_id === selectedFindingId;
          return (
            <li key={finding.clause_id}>
              <button
                type="button"
                onClick={() => onSelect(finding.clause_id)}
                className={clsx(
                  "block w-full px-3 py-2 text-left text-sm hover:bg-neutral-50",
                  selected && "bg-blue-50",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={clsx(
                      "rounded px-1.5 py-0.5 text-xs font-medium",
                      LANE_CLASS[decision.lane],
                    )}
                  >
                    {LANE_LABEL[decision.lane]}
                  </span>
                  <span className="font-mono text-xs text-neutral-500">{finding.tag}</span>
                </div>
                <div className="mt-1 line-clamp-2 text-neutral-800">
                  {finding.explanation || finding.clause_text.slice(0, 160)}
                </div>
                <div className="mt-1 text-xs text-neutral-500">
                  judge={finding.judge_score.toFixed(2)} · τ={decision.threshold_applied.toFixed(2)}
                </div>
              </button>
            </li>
          );
        })}
        {rows.length === 0 && status !== "streaming" && (
          <li className="px-3 py-6 text-center text-sm text-neutral-500">
            Select a deal to start a review.
          </li>
        )}
      </ul>
    </div>
  );
}
