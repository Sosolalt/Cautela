# Kickoff prompt — Internal-30 annotation workflow

> **How to use:** open a fresh Claude Code conversation **in this repo**
> (`ma_gatekeeper/`) and paste everything in the fenced block below as your
> first message. It is self-contained: it tells that conversation to author and
> run a multi-agent **Workflow** that produces the two pre-label passes, the
> reconciled gold set, the κ number, and the human-review packet.
>
> **Prerequisite:** run the fetch first, in *this* conversation or that one:
> ```bash
> export SEC_EDGAR_USER_AGENT="hugo.majerczyk@proton.me MA-Gatekeeper"
> python -m scripts.fetch_internal30          # populates data/edgar/*.txt + manifest.json
> ```
> The word **ultracode** is included in the prompt on purpose — it opts that
> conversation into the Workflow tool. Leave it in.

---

```text
ultracode

You are going to author and RUN a multi-agent Workflow that pre-labels the
Internal-30 calibration merger agreements for the 7 M&A clause families, so that
two human M&A attorneys only have to double-check the output. This is an honest
human-in-the-loop pipeline: the agents pre-label, the humans are the annotators
of record. Do not skip the design doc.

READ FIRST (in this order), and treat them as binding:
  1. docs/internal30_annotation_cohort.md   — the master spec. Roles, the 3-cohort
     topology (Cohort A recall-first, Cohort B precision-first + independent,
     Adjudication cohort), per-clause-family legal grounding, severity rubric,
     the integrity rules, and the required README disclosure. Follow it exactly.
  2. scripts/annotate.py                     — the PrelabelSpan schema and the
     `kappa` subcommand your output must be byte-compatible with. Note
     `_coerce_span` HARD-FAILS on a bad tag, bad severity, or an offset where
     contract_text[char_start:char_end] != text.
  3. data/edgar/manifest.json                — the contracts to label. Each row's
     `text_path` (data/edgar/<deal_id>.txt) is the CANONICAL offset anchor.
     Verify each file's sha256 matches `text_sha256` before labeling it.

THE 7 TAGS: change_of_control, anti_assignment, mac, accelerated_vesting,
exclusivity, ip_assignment, non_compete. Severity ∈ {info, watch, block} per the
rubric in the master spec. Tag/severity vocab is closed — out-of-vocab fails the load.

CRITICAL IMPLEMENTATION RULE — offsets are computed, never guessed.
LLMs cannot count characters reliably. So your span-producing agents must return
each span as { clause_id, span_text (VERBATIM, copied character-for-character
from the .txt), suggested_tag, suggested_severity, confidence, trigger_language,
explanation } — WITHOUT char_start/char_end. Then a DETERMINISTIC step grounds each
span against the canonical .txt.

  Use a LENGTH-PRESERVING normalized search — this is mandatory, not optional. The
  contracts contain non-breaking spaces (U+00A0) and curly quotes/dashes
  (' ' " " – —). Agents habitually "clean" these to ASCII when quoting, so a naive
  indexOf MISSES real spans and silently drops them (verified on the actual files).
  Fix: build a normalizer that maps each of those characters 1-to-1 to its ASCII
  equivalent ( ->space, ' '->', " "->", –—->-) — every substitution is a single
  char so OFFSETS ARE UNCHANGED. Then:
      norm = s => s.replace(/ /g,' ').replace(/[''']/g,"'").replace(/[""]/g,'"').replace(/[–—]/g,'-')
      start = norm(contract_text).indexOf(norm(span_text))   // first occurrence
      if start < 0:  DROP the span, count it "ungrounded" (NEVER invent an offset)
      else:
          char_start = start; char_end = start + span_text.length
          text = contract_text.slice(char_start, char_end)   // store the ORIGINAL .txt
                                                              // substring, NOT the agent's
                                                              // cleaned quote
  Storing the original substring keeps `contract_text[char_start:char_end] == text`
  true against the raw .txt, so scripts/annotate.py:_coerce_span passes. This mirrors
  the _parse_live_spans pattern in scripts/eval_cuad_spans.py. Log the dropped count
  per contract — a high drop rate means an agent paraphrased instead of quoting; that
  is a bug to fix, not to hide.

WORKFLOW SHAPE (use the Workflow tool):
  Phase "PassA" and Phase "PassB" run as a pipeline over the manifest's contracts.
  For each contract, each pass = a cohort:
    - Fan out 7 family-specialist agents (one per tag). Each reads data/edgar/<deal_id>.txt
      and returns ONLY its family's spans (verbatim span_text + metadata, no offsets),
      having self-checked per the master spec's triple-check.
    - A reconciler agent merges the 7 specialists' spans, de-dupes overlaps, resolves
      neighbor-family conflicts, and returns the cohort's span list for that contract.
    - Cohort A uses the recall-first framing; Cohort B uses the precision-first framing
      and must NOT see Cohort A's output (independence is what makes κ meaningful).
  Then a deterministic grounding step turns each pass into PrelabelSpan rows and writes:
      data/internal30/prelabels.jsonl     (Pass A)
      data/internal30/prelabels_b.jsonl   (Pass B)
  Phase "Adjudicate": an adjudication cohort aligns A↔B per contract (match on overlapping
  char ranges, Jaccard ≥ 0.5), buckets each span agree / tag-disagreement / solo-A / solo-B,
  and writes:
      data/internal30/reconciled_gold.jsonl
      data/internal30/human_review_packet.md   (decisions-needed first, then low-conf
                                                 agrees, then high-conf agrees collapsed
                                                 with an explicit sample rate — see master
                                                 spec §6; target ~5–15 min/contract for the
                                                 human).

USE A STRUCTURED-OUTPUT SCHEMA for the span-producing agents so every returned span
has exactly the fields above and nothing else.

INTEGRITY (non-negotiable — the master spec §2/§7 has the full list):
  - Label ONLY from the provided .txt. Several deals are famous; ignore everything you
    "know" about them. A span exists only if it is verbatim in the file.
  - Never fabricate a number, section id, or trigger phrase. Quote or omit.
  - Confidence must be calibrated, not generous; borderline spans get low confidence so
    the humans look at them first.
  - Do not hedge or disclaim on the grounds that you are an AI — produce partner-grade
    legal analysis.

WHEN DONE:
  1. Run:  python -m scripts.annotate kappa data/internal30/prelabels.jsonl data/internal30/prelabels_b.jsonl
     and report the κ number.
  2. Sanity-check that both .jsonl files load through scripts/annotate.py without a
     _coerce_span failure (the offset invariant must hold for every row).
  3. Print a short summary: spans per contract, agree/disagree/solo counts, ungrounded-drop
     counts, the κ value, and where the human-review packet is.
  4. Remind me (the operator) that κ here is agent–agent agreement (expected high, NOT human
     inter-annotator reliability), and that the gold set's credibility comes from my two M&A
     friends working through human_review_packet.md in Argilla, per the disclosure in the
     master spec §9.

Before you spawn the workflow, show me: the contract count from the manifest, the per-pass
agent count you'll spawn, and a one-line confirmation that you read the master spec. Then run it.
```

---

### Notes for *you* (the operator) before you paste it

- **Cost/scale.** ~16 contracts × 2 passes × (7 specialists + 1 reconciler) ≈ **256 labeling
  agents**, plus the adjudication cohort. That's a large but bounded run (the Workflow tool
  caps concurrency and total agents). It is the right tool for this; just know it's a real burn.
- **These agents are Claude, not Gemini.** The Vertex/`gemini-3.1-pro-preview` env from §5 is
  irrelevant here — the cohort runs on the Workflow's Claude subagents, and offset grounding is
  plain code. Nothing to export.
- **Run the fetch first.** If `data/edgar/manifest.json` is missing, the workflow has nothing to
  read. Two deals (`amazon_irobot`, `mid2025_clean_comparable`) are TODOs in the manifest — either
  fill their sources in `scripts/fetch_internal30.py` or let the run proceed on the 14 it has.
- **Then the humans.** Hand `data/internal30/human_review_packet.md` + the Argilla import
  (`reconciled_gold.jsonl`) to your two M&A friends. Their accept/correct pass is what makes the
  gold set real; κ is just the disclosed procedural footnote.
