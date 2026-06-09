// TS mirror of ma_gatekeeper/agent/schemas.py. Keep in sync.
//
// We don't auto-generate from Pydantic because the agent server emits these
// via SSE as JSON strings — runtime validation happens on the parse side
// (lib/api.ts) when we json.parse each SSE frame.

export type Tag =
  | "change_of_control"
  | "anti_assignment"
  | "mac"
  | "accelerated_vesting"
  | "exclusivity"
  | "ip_assignment"
  | "non_compete"
  | "none";

export type Severity = "info" | "watch" | "block";
export type Lane = "auto_clear" | "escalate" | "block";

export interface Clause {
  id: string;
  section_path: string[];
  text: string;
  page: number;
  char_start: number;
  char_end: number;
  pdf_bbox: [number, number, number, number] | null;
}

// Citation-linkage layer (design/STATUTE_LAYER.md §2.2 / §4.1). User-facing
// citation only — statute OR case-law. Mirrors agent/schemas.py:CitationRef.
// NOTE: the backend's internal eval-only linker fields deliberately have NO TS
// mirror here — they must never exist on the wire (Guard #3, enforced by
// tests/test_no_eval_leak.py + tests/test_frontend_type_sync.py). Do not add them.
export interface CitationRef {
  citation: string;
  citation_kind: "statute" | "case_law" | "regulation";
  jurisdiction: string;
  uri: string | null;
  rationale: string;
  verified_date: string; // ISO date (YYYY-MM-DD), the map-commit verification date
  primary_source: string;
}

export interface RiskFinding {
  clause_id: string;
  clause_text: string;
  tag: Tag;
  severity: Severity;
  judge_score: number;
  cited_spans: string[];
  cited_spans_text: string;
  explanation: string;
  // OTel trace id (32-char lowercase hex), or null when the server
  // emitted the finding outside an active OTel context (NoOp tracer,
  // unit test, etc.). The trace pane gates on this — null hides the
  // iframe. Name matches W3C OTel, not the vendor.
  trace_id: string | null;
  // Optional — populated once the server threads `page` + `pdf_bbox`
  // from the Clause onto the emitted RiskFinding (plan §7 D15 task).
  // Typed now so the future server change is checked, not cast-through.
  page?: number;
  pdf_bbox?: [number, number, number, number] | null;
  // Deterministic, primary-source-verified citation for Block-tier findings.
  // Null when the clause tag has no map entry (e.g. accelerated_vesting).
  citation_ref?: CitationRef | null;
}

export interface GatekeeperDecision {
  // INVARIANT: finding_id === the RiskFinding's clause_id (Router emits
  // it that way — see agent/router.py). The UI keys rows by clause_id;
  // if this invariant is ever broken on the server, the trace pane will
  // load against the wrong finding silently. Belt-and-braces: page.tsx
  // also looks up rows by clause_id, not finding_id.
  finding_id: string;
  lane: Lane;
  threshold_applied: number;
}

export interface Deal {
  id: string;
  name: string;
  filing: string;
  cik: string;
}

// ---------------------------------------------------------------------------
// Fix 7 — Portfolio Analyst (mirrors agent/schemas.py:PortfolioReport).
// ---------------------------------------------------------------------------

export interface PortfolioCluster {
  cluster_id: string;
  name: string;
  theme: string;
  member_deal_ids: string[];
  representative_clause_excerpt: string;
  why_distinct: string;
}

export interface PortfolioOutlier {
  deal_id: string;
  why: string;
}

export interface PortfolioReport {
  clusters: PortfolioCluster[];
  outliers: PortfolioOutlier[];
  trace_id: string | null;
}

// SSE frame variants emitted by /review and /review-by-deal.
export type SseEvent =
  | { event: "start" }
  | { event: "agent_output"; author: string; text: string }
  | { event: "finding"; finding: RiskFinding; decision: GatekeeperDecision }
  | { event: "error"; stage: string; message: string }
  | { event: "done"; n_findings: number };

// ---------------------------------------------------------------------------
// §11 Build #3 / §12 — Reflector-as-LoopAgent (mirrors agent/schemas.py).
// ---------------------------------------------------------------------------

export type ReflectorLoopEventKind =
  | "loop_started"
  | "iteration_started"
  | "mcp_traces_listed"
  | "candidate_generated"
  | "experiment_complete"
  | "frozen_fold_check"
  | "iteration_complete"
  | "auto_promoted"
  | "no_promotion"
  | "error";

export interface ReflectorLoopEvent {
  kind: ReflectorLoopEventKind;
  iteration: number | null;
  trace_id: string | null;
  payload: Record<string, unknown>;
}

// SSE frame wrapper emitted by /reflect/loop. The server wraps each
// `ReflectorLoopEvent` with an `event: "reflector_loop"` discriminator
// (see _stream_reflector_loop_events in agent/server.py), then closes
// with `event: "done"` or surfaces an `event: "error"` on stream-level
// failures.
export type ReflectorLoopSseFrame =
  | ({ event: "reflector_loop" } & ReflectorLoopEvent)
  | { event: "error"; stage: string; message: string }
  | { event: "done"; n_events: number };
