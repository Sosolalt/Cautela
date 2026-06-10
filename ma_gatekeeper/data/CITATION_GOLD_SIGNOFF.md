# Citation Gold (`citation-gold-v1`) — Sign-off & Audit Trail

Audit trail for `data/citation_gold_v1.jsonl`, the held-out evaluation set the
citation layer is graded against (`scripts/eval_citation_gold.py`). Mirrors
`data/CITATION_MAP_SIGNOFF.md`. Per `docs/GROUNDTRUTH_PLAN.md` T1.1.

**What this gold is — and is NOT.** It is an LLM-counsel-curated set of
clause→controlling-authority pairs used to grade (a) the deterministic
`citation_map.json` and (b) the internal LLM proposer. It is **NOT** a
second human annotator's labels and it is **NOT** "non-circular by sourcing"
in the old sense. Its independence comes from being **deliberately divergent**:
it contains rows whose controlling authority is, *by construction*, outside the
map's tag/jurisdiction universe, so the map **can and does miss for a real
reason** — see the off-map rows below.

**Signer (hackathon scope):** `ma-counsel-persona` — the same M&A-counsel
persona (LLM agent + WebFetch) that curated the map. Every off-map `citation`
added in the de-circularization pass was confirmed against a **fetched primary
page** (recorded below); unfetchable candidates were **dropped, not guessed**
(hard constraint — UK § 979 / `legislation.gov.uk` is JS-gated and was dropped).

**Verification date:** 2026-06-09. **commit_sha:** `staged-uncommitted` — the
user owns all git operations.

---

## Schema

Each line is one JSON object:

```
{"input": {"clause_text": "...", "tag": "<map tag>"},
 "output": {"citation": "...", "citation_kind": "statute|case_law", "source": "<url>", "supports": "..."},
 "metadata": {"deal_id": "...", "fold": <int>, "jurisdiction": "<one of the map's 5>", "off_map": <bool>, "source": "<url>"}}
```

* `metadata.jurisdiction` is **gold-provided** (added to *every* row in this
  pass). It is the hint `lookup_citation(input.tag, jurisdiction_hint=...)`
  receives. **It is NOT agent-extracted** — do not read a map hit as "the agent
  inferred New York." Agent-side governing-law extraction is the separate
  server path (`normalize_jurisdiction`), graded elsewhere.
* `metadata.off_map = true` marks a **de-circularization** row whose
  controlling authority is outside the map's universe for that tag. The eval
  asserts each such row resolves to `None` **or a genuinely different
  authority** (never a citation-form artifact).

## How the two map numbers are computed (honest framing)

* **`map_recall` (recall@1)** — does `lookup_citation(tag, jurisdiction)`
  return the gold authority as its **single best answer**? On the 40 in-map
  rows this is **28/40 today**. The 12 "misses" are rows where the controlling
  authority **is in the map for that tag** but is not the canonical first entry
  (e.g. gold wants `§ 271` asset-sale or `§ 2-210`, the map's canonical
  `change_of_control`/`anti_assignment` answer is `§ 251`/`§ 9-406`).
* **`map_coverage` (contains-anywhere)** — does **any** map entry for that tag
  carry the gold authority? **40/40 by construction** — this is *coverage,
  primary-source-verified, NOT earned accuracy.*
* The **gap** between the two (28 vs 40) is the honest `candidates[0]` /
  single-best-answer story, reported as a number rather than hidden.
* **Case-law form-normalisation** rescues case-law rows whose gold short form
  (`Akorn … (Del. Ch. 2018)`) differs from the map's parallel-cite long form;
  these count as hits and the count is surfaced as `n_form_mismatch`.
* **Off-map:** the map correctly returns None/different for **5/5** off-map
  rows — reported as a separate line so it is never confused with in-map
  coverage.

---

## Off-map rows added in the de-circularization pass (each WebFetch-verified)

| deal_id | tag | gold authority | primary_source_url | fetched? | resolves to |
|---|---|---|---|---|---|
| OFFMAP-APPRAISAL-DE | change_of_control | 8 Del. C. § 262 (appraisal) | https://delcode.delaware.gov/title8/c001/sc09/index.html | ✅ § 262 listed in Subch. IX | map → § 251 (different authority) |
| OFFMAP-DRULPA-LP | change_of_control | 6 Del. C. § 17-211 (DRULPA LP merger) | https://delcode.delaware.gov/title6/c017/sc02/index.html | ✅ "§ 17-211. Merger and consolidation" | map → § 251 (corporate, not LP) |
| OFFMAP-NY-ASSIGN | anti_assignment | N.Y. Gen. Oblig. Law § 13-101 (transfer of claims) | https://www.nysenate.gov/legislation/laws/GOB/13-101 | ✅ title "Transfer of claims" | NY hint → None (fail-closed; map is UCC-only) |
| OFFMAP-NY-APPRAISAL | change_of_control | N.Y. Bus. Corp. Law § 623 (dissenters' rights) | https://www.nysenate.gov/legislation/laws/BSC/623 | ✅ "Procedure to enforce shareholder's right to receive payment for shares" | map → § 902 (merger plan, not appraisal) |
| OFFMAP-DISGUISE-COC | anti_assignment | 8 Del. C. § 251 (hidden CoC via equity-transfer-as-assignment) | https://delcode.delaware.gov/title8/c001/sc09/index.html | ✅ (same § 251 page as the map) | DE hint → None (tagged on surface form; map's anti_assignment is UCC) |

These exercise three distinct miss modes: **wrong-section-same-tag** (§ 262,
§ 17-211, § 623), **jurisdiction fail-closed** (NY anti-assignment), and
**tag-disguise** (a CoC clause classified `anti_assignment`).

## In-map rows (40)

The original 40 rows are unchanged except for the added `metadata.jurisdiction`
/ `metadata.source` / `metadata.off_map=false` keys. Their `source` URLs were
verified during the map sign-off (`CITATION_MAP_SIGNOFF.md`). One provenance
caveat carried over from that file:

* **AB Stable rows** cite the Delaware Supreme Court reporter `268 A.3d 198
  (Del. 2021)` with a `source` pointing at the **Justia copy of the Court of
  Chancery 2020 opinion** — a **secondary** source. This matches the map's
  honestly-relabelled `primary_source = law.justia.com (secondary)`. Pointing
  both at the real `courts.delaware.gov` Supreme Court PDF is a clean follow-up.
  The case-law form-normaliser keys on the party-name caption, so the gold's
  short form and the map's parallel-cite long form score as the same case
  regardless of the reporter that leads each string.

## Dropped (NOT shipped — correctness-first)

* **UK § 979 (Companies Act 2006 squeeze-out)** — `legislation.gov.uk` returns
  empty via WebFetch (JS-gated). Dropped per GROUNDTRUTH_PLAN rather than cited
  from memory.
* **HSR sub-threshold exemption** — too close to the map's existing `§ 18a`
  entry to read as a clean off-map miss; dropped in favour of the cleaner
  appraisal / DRULPA / fail-closed rows above.
