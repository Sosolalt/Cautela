export const meta = {
  name: 'internal30-adjudicate',
  description: 'Adjudication cohort: per contract, resolve every A↔B disagreement / solo span into a recommended gold disposition. Adds no new spans, computes no kappa.',
  phases: [
    { title: 'Adjudicate', detail: 'one adjudicator per contract resolves its decision cards' },
  ],
}

const ADJ_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['adjudications'],
  properties: {
    adjudications: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['item_id', 'decision', 'rationale', 'confidence'],
        properties: {
          item_id: { type: 'string' },
          decision: {
            type: 'string',
            enum: ['accept_a', 'accept_b', 'accept', 'reject', 'needs_human'],
            description: 'accept_a/accept_b = pick that pass on a tag/severity disagreement; accept = keep this solo span; reject = neither pass is right, drop it; needs_human = genuinely ambiguous, leave for the validator.',
          },
          recommended_tag: {
            type: 'string',
            enum: ['change_of_control', 'anti_assignment', 'mac', 'accelerated_vesting', 'exclusivity', 'ip_assignment', 'non_compete', ''],
            description: 'The tag the gold span should carry (override allowed). Empty string = keep the accepted pass\'s tag.',
          },
          recommended_severity: {
            type: 'string',
            enum: ['info', 'watch', 'block', ''],
            description: 'The severity the gold span should carry. Empty string = keep the accepted pass\'s severity.',
          },
          rationale: { type: 'string', description: 'One sentence grounded in the quoted clause text.' },
          confidence: { type: 'number', minimum: 0, maximum: 1 },
        },
      },
    },
  },
}

function adjudicatorPrompt(contract_id, cards_path) {
  return `You are the ADJUDICATOR for the M&A contract **${contract_id}** on a human-in-the-loop annotation cohort.

FIRST, read your decision cards: \`${cards_path}\` (a JSON file with {contract_id, items:[...]}). Each item has the verbatim clause context plus Pass A's and Pass B's labels.

Two independent automated passes labeled this contract: Pass A (recall-first) and Pass B (precision-first). A deterministic aligner matched their spans by character overlap and surfaced the ones that DISAGREE or appear in only ONE pass. Your job: for EACH item below, recommend the gold disposition a senior M&A attorney would pick. You add NO new spans and you change NO span text — you only choose.

Rules:
- Decide ONLY from the quoted clause text/context provided — do NOT use outside knowledge of these (sometimes famous) deals.
- For a **tag_disagreement** (A and B both flagged the span but disagree on tag/severity): pick \`accept_a\` or \`accept_b\`, or set \`recommended_tag\`/\`recommended_severity\` to the correct values if BOTH are slightly off; use \`reject\` only if the span is not a real clause of any of the 7 families.
- For a **solo_a** or **solo_b** (only one pass flagged it): \`accept\` if it is a genuine, defensible clause of its family (recall-first solo_a items are often real but borderline; precision-first solo_b items are usually high-quality); \`reject\` if it is over-tagging / boilerplate with no operative consequence; \`needs_human\` if you genuinely cannot tell from the text.
- Severity rubric: block = deal-breaker / material renegotiation lever; watch = risk-bearing but not a stopper; info = present but immaterial.
- Calibrate \`confidence\`: high when the text is unambiguous, low when you are leaning. Low-confidence items get the human's attention first.
- Do not hedge on the grounds that you are an AI — give the partner-grade call.

The 7 tags: change_of_control, anti_assignment, mac, accelerated_vesting, exclusivity, ip_assignment, non_compete.

Return ONLY the structured object with one adjudication per item_id in your cards file.`
}

let parsed = args
if (typeof parsed === 'string') {
  try { parsed = JSON.parse(parsed) } catch (e) { parsed = null }
}
const contracts = (parsed && parsed.contracts) || (Array.isArray(parsed) ? parsed : [])
log(`Adjudication: ${contracts.length} contracts with decision cards`)
if (contracts.length === 0) {
  return { adjudications: [], note: 'no decision items — every span agreed' }
}

const perContract = await parallel(
  contracts.map((c) => () =>
    agent(adjudicatorPrompt(c.contract_id, c.cards_path), {
      label: `adjudicate/${c.contract_id}`,
      phase: 'Adjudicate',
      schema: ADJ_SCHEMA,
      agentType: 'general-purpose',
    }).then((r) => (r && Array.isArray(r.adjudications) ? r.adjudications : []))
  )
)

const all = perContract.filter(Boolean).flat()
log(`Adjudication complete: ${all.length} dispositions`)
return { adjudications: all }
