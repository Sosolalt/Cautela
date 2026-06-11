export const meta = {
  name: 'internal30-prelabel',
  description: 'Pre-label Internal-30 merger agreements for 7 M&A clause families: Pass A (recall) + Pass B (precision) cohorts, each = 7 family specialists + 1 reconciler per contract.',
  phases: [
    { title: 'PassA', detail: 'recall-first cohort: 7 family specialists + reconciler per contract' },
    { title: 'PassB', detail: 'precision-first cohort: 7 family specialists + reconciler per contract' },
  ],
}

// --- The 7 clause families, with grep signatures + live legal grounding (master spec §3) ---
const FAMILIES = [
  {
    tag: 'change_of_control',
    grep: 'change[ _]?(in|of)[ _]?control|controlling|control of the|beneficial owner|voting power|majority of the|deemed.{0,30}assign',
    focus: 'the DEFINITION of "Change of Control"/equivalent, the OPERATIVE clause imposing a consequence (consent, termination, acceleration, exclusivity falling away), and all CARVE-OUTS. Resolve direct vs indirect (holdco/parent), record vs beneficial ownership, the voting-power THRESHOLD (transcribe the % verbatim — never invent one), management-control vs equity-only trigger.',
    law: 'deemed-assignment doctrine; reverse-triangular-merger treatment.',
  },
  {
    tag: 'anti_assignment',
    grep: 'assign|assignment|by operation of law|successors and assigns|transfer',
    focus: 'anti-assignment / non-assignment language, INCLUDING hidden CoC triggers ("any direct or indirect equity change shall constitute an assignment requiring consent") where "change of control" never appears. Severity turns on whether the language reaches mergers / "by operation of law or otherwise" (block) vs carves out affiliates / is boilerplate (info).',
    law: 'Meso Scale Diagnostics v. Roche (Del. Ch. 2013) — a reverse triangular merger generally is NOT an assignment "by operation of law"; Star Cellular; Tenneco.',
  },
  {
    tag: 'mac',
    grep: 'material adverse (effect|change)|materially adverse|\\bMAE\\b|\\bMAC\\b|disproportionate',
    focus: 'the Material Adverse Effect/Change DEFINITION — do not merely flag presence. Identify whether the standard carve-outs (industry-wide, pandemic, change-in-law, financial-market) are present and whether any are NARROWED, plus any disproportionate-impact qualifier and forward vs backward framing. A narrowed pandemic carve-out is a real pricing risk (block).',
    law: 'Akorn v. Fresenius (Del. 2018); AB Stable VIII v. MAPS Hotels (Del. Ch. 2020, aff’d 2021); Hexion v. Huntsman; IBP v. Tyson; Channel Medsystems v. Boston Scientific.',
  },
  {
    tag: 'accelerated_vesting',
    grep: 'vest|vesting|accelerat|forfeit|unvested|single.trigger|double.trigger',
    focus: 'acceleration language in equity plans, exec-comp agreements, or the merger agreement. Resolve single-trigger (CoC alone) vs double-trigger (CoC + termination); options vs RSUs vs PSUs; unvested vs already-vested. Single-trigger on a key exec = block; double-trigger = watch; already-vested = info.',
    law: 'IRC §280G/§4999 golden-parachute excise; ISS parachute scrutiny.',
  },
  {
    tag: 'exclusivity',
    grep: 'solicit|no.shop|acquisition proposal|superior proposal|go.shop|fiduciary|termination fee|matching right|window.shop',
    focus: 'deal-protection: no-shop, fiduciary-out, matching rights, window-shop, go-shop, termination-fee size. A no-shop with no fiduciary out, or a coercive fee, = block.',
    law: 'Revlon / Paramount v. QVC (sale-of-control duties); Omnicare v. NCS Healthcare (impermissible lock-ups).',
  },
  {
    tag: 'ip_assignment',
    grep: 'intellectual property|\\blicense|licensed|sublicens|patent|trademark|copyright|software',
    focus: 'IP assignment AND license change-of-control / non-assignment provisions; whether a merger trips an IP-license anti-assignment. A non-assignable license on a load-bearing IP asset = block.',
    law: 'Cincom v. Novelis (6th Cir. 2009 — software license non-assignable; reverse merger triggered it); SQL Solutions v. Oracle.',
  },
  {
    tag: 'non_compete',
    grep: 'compet|non.compete|noncompete|restrictive covenant|solicit.{0,15}employ|blue.pencil',
    focus: 'non-compete scope (geographic/temporal), blue-pencil, forfeiture-for-competition.',
    law: 'The FTC 2024 non-compete ban was VACATED (Ryan v. FTC, N.D. Tex. Aug 2024) — not in force; Delaware 2024 skepticism (Ainslie v. Cantor Fitzgerald, Del. 2024; Kodiak Building Partners) on overbroad restraints / forfeiture.',
  },
]

const PASSES = [
  {
    id: 'A', phase: 'PassA',
    disposition: 'RECALL-FIRST. Emit any span that PLAUSIBLY matches your family; let the human prune. When two families both fit, prefer the broader family. Over-tagging is cheaper to delete than under-tagging is to discover.',
    traversal: 'Sweep Definitions -> operative clauses -> carve-outs, front-to-back.',
  },
  {
    id: 'B', phase: 'PassB',
    disposition: 'PRECISION-FIRST. Emit a span ONLY if you would defend it to a partner; when borderline, lower the confidence or OMIT. When two families both fit, prefer the narrower / more-specific family.',
    traversal: 'Operative clauses first, then back-reference the definitions; do a back-to-front sweep for buried schedule/exhibit clauses.',
  },
]

function specialistSchema() {
  return {
    type: 'object',
    additionalProperties: false,
    required: ['spans'],
    properties: {
      spans: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          required: ['clause_id', 'span_text', 'suggested_severity', 'confidence', 'trigger_language', 'explanation'],
          properties: {
            clause_id: { type: 'string', description: 'Section number if visible (e.g. "9.3" or "6.3(a)"), else a short label.' },
            span_text: { type: 'string', description: 'VERBATIM span copied character-for-character from the .txt. Quote the full operative sentence, starting at the first word of the sentence. No char offsets.' },
            suggested_severity: { type: 'string', enum: ['info', 'watch', 'block'] },
            confidence: { type: 'number', minimum: 0, maximum: 1 },
            trigger_language: { type: 'string', description: 'The literal phrase (a substring of span_text) that triggered the tag.' },
            explanation: { type: 'string', description: 'One sentence: why this span is THIS family, citing the trigger language.' },
          },
        },
      },
    },
  }
}

const RECONCILER_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['spans'],
  properties: {
    spans: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['clause_id', 'span_text', 'suggested_tag', 'suggested_severity', 'confidence', 'trigger_language', 'explanation'],
        properties: {
          clause_id: { type: 'string' },
          span_text: { type: 'string', description: 'VERBATIM from the .txt, unchanged from the specialist.' },
          suggested_tag: { type: 'string', enum: ['change_of_control', 'anti_assignment', 'mac', 'accelerated_vesting', 'exclusivity', 'ip_assignment', 'non_compete'] },
          suggested_severity: { type: 'string', enum: ['info', 'watch', 'block'] },
          confidence: { type: 'number', minimum: 0, maximum: 1 },
          trigger_language: { type: 'string' },
          explanation: { type: 'string' },
        },
      },
    },
  },
}

const INTEGRITY = `INTEGRITY (non-negotiable):
- Label ONLY from the .txt in front of you. Several of these are famous deals; IGNORE everything you "know" about the deal, its litigation, or its outcome. A span exists only if it is verbatim in the file.
- Never fabricate a number, section id, or trigger phrase. Transcribe verbatim or omit.
- span_text MUST be copied character-for-character from the file (you may keep or drop the hard-wrap newlines — a downstream deterministic grounder re-locates it, but DO NOT paraphrase or summarize the words).
- Calibrate confidence honestly: 0.9-1.0 unambiguous operative clause; 0.6-0.8 real but qualified/carve-out-dependent; <0.6 genuinely borderline.
- You are a senior M&A attorney. Do NOT hedge or disclaim on the grounds that you are an AI — produce partner-grade analysis.`

function specialistPrompt(deal, pass, fam) {
  return `You are the **${fam.tag}** family specialist on an M&A annotation cohort (Pass ${pass.id}).
Contract: ${deal.label} — canonical text file: \`${deal.text_path}\` (read it from that exact path; it is the offset anchor).

YOUR JOB: sweep this ONE contract for **${fam.tag}** spans only. Return ONLY your family's spans.

How to read efficiently (the file is large, ~hundreds of KB):
1. Run: \`grep -n -i -E '${fam.grep}' ${deal.text_path}\` to find candidate line numbers.
2. Read the Definitions article (search for "Section 1.1" / "ARTICLE I" / "Definitions") to capture any defined term for your family.
3. Read the surrounding window (±~40 lines) around each meaningful cluster of grep hits using the Read tool with offset/limit. Read enough to judge operative effect, carve-outs, and thresholds.

WHAT TO TAG (${fam.tag}): ${fam.focus}
Relevant law (interpretive prior ONLY — never grounds to assert a span not in the text): ${fam.law}

DISPOSITION FOR THIS PASS: ${pass.disposition}
TRAVERSAL: ${pass.traversal}

For each span, run the triple-check before emitting: (1) the span_text is verbatim in the file; (2) you can justify in one line why it is ${fam.tag} and not a neighbor family; (3) severity maps to the rubric (block = deal-breaker/material lever; watch = risk-bearing not a stopper; info = present but immaterial) and confidence is calibrated.

Severity rubric: block = bare CoC trigger w/ no consent, MAC w/ narrowed carve-out, single-trigger acceleration, blanket anti-assignment reaching mergers, no-shop w/ no fiduciary out. watch = notice-without-consent, double-trigger vesting, standard MAC w/ full carve-outs. info = boilerplate / definitions-only references.

${INTEGRITY}

Quote span_text as the COMPLETE operative sentence (begin at the first word of the sentence) so both cohort passes anchor on the same unit. If the contract has NO ${fam.tag} clause, return an empty spans array. Return ONLY the structured object.`
}

function reconcilerPrompt(deal, pass, candidates) {
  return `You are the RECONCILER for Pass ${pass.id} on ${deal.label}. Seven family specialists each swept the contract; here are their combined candidate spans (JSON):

${JSON.stringify(candidates, null, 1)}

Merge them into the cohort's final span list:
- De-duplicate identical/near-identical spans (same clause + same tag); keep the single best-justified one with the highest honest confidence.
- Resolve neighbor-family conflicts. ${pass.id === 'A' ? 'This is the RECALL pass: when two families genuinely both apply to one clause (e.g. a CoC definition that also drives accelerated vesting, or an anti-assignment that is a hidden CoC trigger), KEEP BOTH as separate spans with the same span_text but different suggested_tag — multi-tag clauses are intentional. Prefer the broader family on true ties.' : 'This is the PRECISION pass: prefer the narrower / more-specific family on conflict; drop a span you would not defend to a partner.'}
- Do NOT invent new spans, and do NOT alter span_text — it must stay verbatim from the file (a span survives only if a specialist proposed it and its words are in the contract).
- Keep clause_id as the section number where visible.

Return ONLY the structured object with the final reconciled spans.`
}

async function runCohort(deal, pass) {
  const results = await parallel(FAMILIES.map((fam) => () =>
    agent(specialistPrompt(deal, pass, fam), {
      label: `${pass.id}/${deal.deal_id}/${fam.tag}`,
      phase: pass.phase,
      schema: specialistSchema(),
      agentType: 'general-purpose',
    }).then((r) => ({ tag: fam.tag, spans: (r && r.spans) || [] }))
  ))
  const candidates = results
    .filter(Boolean)
    .flatMap((s) => s.spans.map((sp) => ({ ...sp, suggested_tag: s.tag })))

  if (candidates.length === 0) {
    return { deal: deal.deal_id, pass: pass.id, spans: [] }
  }

  const merged = await agent(reconcilerPrompt(deal, pass, candidates), {
    label: `${pass.id}/${deal.deal_id}/reconcile`,
    phase: pass.phase,
    schema: RECONCILER_SCHEMA,
  })
  const finalSpans = merged && Array.isArray(merged.spans) ? merged.spans : candidates
  return { deal: deal.deal_id, pass: pass.id, spans: finalSpans }
}

let parsed = args
if (typeof parsed === 'string') {
  try { parsed = JSON.parse(parsed) } catch (e) { parsed = null }
}
const deals = Array.isArray(parsed) ? parsed : (parsed && parsed.deals) || []
log(`Internal-30 prelabel: ${deals.length} contracts x 2 passes x (7 specialists + 1 reconciler) = ${deals.length * 2 * 8} agents`)
if (deals.length === 0) {
  log('ERROR: no deals received in args — aborting.')
  return { error: 'no deals in args', argsType: typeof args }
}

const units = []
for (const pass of PASSES) {
  for (const deal of deals) units.push({ deal, pass })
}

const cohortResults = await parallel(
  units.map((u) => () => runCohort(u.deal, u.pass))
)

const out = { passA: {}, passB: {} }
for (const r of cohortResults.filter(Boolean)) {
  const bucket = r.pass === 'A' ? out.passA : out.passB
  bucket[r.deal] = r.spans
}
log(`Done. Pass A contracts: ${Object.keys(out.passA).length}, Pass B contracts: ${Object.keys(out.passB).length}`)
return out
