"use client";

import type { Deal } from "@/lib/types";

interface Props {
  deals: Deal[];
  value: string | null;
  onChange: (id: string) => void;
  disabled?: boolean;
}

/**
 * Curated 5-deal dropdown — NOT an open ticker box (plan §5.5).
 *
 * The voiceover line on D19 must say "five pre-indexed deals" (the
 * pre-commitment from PROJECT_LOG.md "Current norm > Pre-commitments
 * locked in"). The control deliberately reads "Pre-indexed deal" to keep
 * the demo claim and the UI label aligned.
 */
export function DealPicker({ deals, value, onChange, disabled }: Props) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-neutral-600">Pre-indexed deal</span>
      <select
        className="rounded border border-neutral-300 bg-white px-2 py-1 text-sm disabled:opacity-50"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || deals.length === 0}
      >
        <option value="" disabled>
          {deals.length === 0 ? "Loading…" : "Select a deal"}
        </option>
        {deals.map((deal) => (
          <option key={deal.id} value={deal.id}>
            {deal.name} ({deal.filing})
          </option>
        ))}
      </select>
    </label>
  );
}
