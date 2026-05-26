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

// SSE frame variants emitted by /review and /review-by-deal.
export type SseEvent =
  | { event: "start" }
  | { event: "agent_output"; author: string; text: string }
  | { event: "finding"; finding: RiskFinding; decision: GatekeeperDecision }
  | { event: "error"; stage: string; message: string }
  | { event: "done"; n_findings: number };
