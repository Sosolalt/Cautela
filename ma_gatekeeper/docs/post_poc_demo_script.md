# Post-POC demo composition — §12 "Run Reflector now" cut

A second demo cut, separate from the locked 3-minute recording in
[`demo_script.md`](demo_script.md). This one is the post-POC enterprise
narrative: the **agent fixes itself** sequence that
POST_HACKATHON_BACKLOG.md §12 calls out as "the ONE demo moment that
beats 90% of the field."

Runtime: **≤90 seconds**, end-to-end. Re-shoots as a standalone clip
after the locked recording lands; does NOT modify the locked recording.
Phoenix MCP recursion is the differentiator (the Arize-juror critique
explicitly named this).

This document is the script for that second cut. Beat timings are
**designed, not measured** — stopwatch-rehearse before the re-shoot,
same discipline as the locked demo.

---

## What this clip proves (one sentence each)

1. The HITL "wrong" flag closes the loop — partner feedback becomes
   training signal automatically.
2. The Reflector LoopAgent is a first-class ADK construct that calls
   **Phoenix MCP** for its own past traces inside the loop body.
3. The promotion gate is the same paired-bootstrap CI + frozen-fold
   non-regression rule used by the cron — no looser gate for the
   on-demand path.
4. The auto-PR closes the audit-trail loop: every promotion has a
   linkable commit hash + diff.

If a juror asks "did you just rename the cron?", the answer is the
Phoenix MCP `list_traces` call inside `agent/reflector_loop.py:147-189`
(`_call_mcp_list_traces`) — that's the recursion the cron didn't have.

---

## Voiceover (Python-counted at synthesis time)

Word counts via `len(text.split())`; pace 150 wpm.

| Line | Words | Spoken | VO text |
|------|-------|--------|---------|
| L1 | 14 | 5.6 s | "Yesterday this clause was Escalate. Partner marked it Wrong. Watch the agent fix itself." |
| L2 | 16 | 6.4 s | "One click. The Reflector LoopAgent spawns. Each iteration queries Phoenix MCP for its own past failures." |
| L3 | 14 | 5.6 s | "Phoenix observing the agent that uses Phoenix to improve the agent Phoenix is observing." |
| L4 | 10 | 4.0 s | "Candidate prompt. Paired-bootstrap on the regression set. Frozen-fold non-regression check." |
| L5 | 10 | 4.0 s | "Confidence interval lower bound positive. Held-out fold within epsilon. Auto-promoted." |
| L6 | 13 | 5.2 s | "Same deal. Re-run the finding. Now Block. Trace cites the new prompt version." |

**Total VO**: 77 words / **30.8 s spoken** at 150 wpm.

**Remaining budget**: ~60 s for visual beats — LoopAgent spawn hold,
sub-trace cascade, prompt diff hold, CI bar fill, AUTO-PROMOTED flash,
PR-open click, re-run reveal. Spec cap: 90 s end-to-end.

---

## Beat table

Times are designed; rehearse on D-1 before the re-shoot. The reference
artifact under recording is `frontend/components/reflector-loop-button.tsx`
mounted at the bottom of the FindingsPane.

| t (s) | Visual | Voiceover | On-screen caption (≤8 words) |
|------:|--------|-----------|------------------------------|
|  0:00 | FindingsPane open on a 5-allow-list deal; yesterday's Escalate-lane finding visible; HITL "wrong" flag already toggled (set up off-camera) | L1 (5.6 s) | — |
|  0:08 | Operator hovers `Run Reflector now` button; presses | — | — |
|  0:10 | Button label flips to "Reflector running…"; status panel below the findings list begins streaming `loop_started` event | L2 (6.4 s) | "LoopAgent spawned (iteration 1 of max 3)" |
|  0:18 | `iteration_started` → `mcp_traces_listed` appears with trace count; the `trace` link is clickable and opens Phoenix in a second window (pre-loaded so it lands instantly) | L3 (5.6 s) | "Phoenix MCP list_traces with hitl_wrong filter" |
|  0:25 | `candidate_generated` appears; brief hold on the candidate-excerpt preview (the synthesized prompt diff) | — | "Candidate generated from introspected failure spans" |
|  0:31 | `experiment_complete` lands with `CI lower = +0.142`; status panel renders the CI as a text line (no chart lib — Documentary-Brutalism palette only) | L4 (4.0 s) | "Paired-bootstrap CI lower bound = +0.142" |
|  0:38 | `frozen_fold_check` lands with `Δ=0.020 (ε=0.030)`; the inequality `0.020 < 0.030` is visually true on hold | L5 (4.0 s) | "Frozen fold-5 delta within epsilon (0.020 < 0.030)" |
|  0:45 | Terminal `auto_promoted` event arrives; the AUTO-PROMOTED chip flashes (champagne-soft `bg-lane-clear` on neutral-50 text); `PR` link visible | — | "Auto-promoted. PR staged. Iteration 1 of max 3." |
|  0:50 | Operator clicks `PR` link; opens auto-generated PR description in a new tab — diff + diagnostics; cut back to FindingsPane on the same deal | — | — |
|  1:05 | Re-trigger the same finding (cmd+click on the row that was Escalate at 0:00); SSE returns a new RiskFinding with `lane = block` and a `trace_id` that resolves to the new prompt version | L6 (5.2 s) | "Now Block — trace cites new prompt version" |
|  1:20 | End on the Phoenix trace pane showing the new prompt-version citation; chip "auto_promoted" still visible on screen | — | — |
|  1:25 | Fade to brand bookend (matches the locked recording's closing) | — | — |
|  1:30 | END | — | — |

---

## Fallbacks

| Failure mode | Cut-in trigger | Fallback action |
|--------------|---------------|-----------------|
| Phoenix MCP cold-start: first `mcp_traces_listed` does not arrive within 4 s of `loop_started` | hold operator's `Run Reflector now` press for 4 s; if still no event, cut to a pre-recorded LoopAgent run of the same deal | use the canonical pre-recorded capture from D-1 rehearsal that shows the full sequence; re-merge on the AUTO-PROMOTED flash |
| `auto_promoted` never fires (gate rejects every candidate) | after 3 iterations elapse with `no_promotion` terminal: cut to operator narration "the gate held — that's the conservative-stats wedge" | continue to brand bookend; this is an honest beat, not a failure beat |
| `gh pr create` fails (e.g. CLI not installed in recording env) | `auto_promoted` event arrives with `auto_pr_url: null` but `staged_diff` populated | UI renders "would-PR" badge instead of "PR"; operator reads L5 same way; the "PR link click" beat at 0:50 is replaced with showing the `staged_diff` text in-place |
| Re-trigger at 1:05 returns Escalate instead of Block (prompt regression on this specific deal) | seen on the FindingsPane refresh | cut to a different allow-list deal known to flip from Escalate→Block on the new prompt (pre-validated during D-1 rehearsal) |

---

## What this clip is NOT

- Not a replacement for the locked 3-minute recording. The locked
  recording has the conservative-stats narrative + the BMS/Celgene cold
  open; this clip is the post-POC enterprise close-loop story.
- Not a UI design pass. The button + status panel are minimal — bare
  button, text-line event log. Documentary-Brutalism palette only,
  Tailwind utility classes only, no new fonts, no new tokens.
- Not the §11 Build #1 (IssuesList + .docx) or §11 Build #2
  (Jurisdiction DSL) cuts. Those are separate post-POC builds and
  recordings.

---

## Codebase anchors

- LoopAgent body: `ma_gatekeeper/agent/reflector_loop.py`
  - HARD-GATE MCP call: `_call_mcp_list_traces` (lines 147-189)
  - Per-iteration body: `_run_one_iteration` (lines 300-427)
  - Public async generator for SSE: `run_reflector_loop` (line 562)
- Endpoint: `ma_gatekeeper/agent/server.py`
  - `POST /reflect/loop` — passcode-gated, mirrors `/portfolio` posture
- UI: `ma_gatekeeper/frontend/components/reflector-loop-button.tsx`
  - Mounted inside `findings-pane.tsx`
- E2E test: `ma_gatekeeper/tests/test_reflector_loop_demo_e2e.py`
  - Asserts the streamed event order in the table above
- Unit tests: `ma_gatekeeper/tests/test_reflector_loop.py`
  - HARD-GATE assertion: `test_loop_body_calls_mcp_list_traces_per_iteration`
  - Locked-surface assertion: `test_reflector_locked_surface_unchanged`
