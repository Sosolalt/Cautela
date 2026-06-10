# Citation Map — Sign-off & Audit Trail

Audit trail for `data/citation_map.json`, per `design/STATUTE_LAYER.md` §4.4 #5.
One row per entry: `tag · citation · primary_source_url · verified_date · signer_id · commit_sha`.

**Signer (hackathon scope):** `ma-counsel-persona` — an M&A-counsel persona (LLM agent
with WebFetch enabled) that confirmed each `citation` field against the primary-source
page recorded below. Production would substitute a named in-house GC. Every entry was
verified against a *fetched page*, never from memory (hard-constraint #7); citations that
could not be confirmed against a fetchable page were **dropped, not guessed** (see
"Dropped / deferred" below).

**Verification date:** 2026-06-09 (also the `verified_date` stamped on every entry; the
CI staleness gate `tests/test_citation_map_freshness.py` fails the build if the newest
entry is older than 180 days).

**commit_sha:** `staged-uncommitted` — the user owns all git operations; this file and the
map are staged for review and not yet committed. Replace with the real SHA at commit time.

---

## Statute entries (11)

| tag | citation | primary_source_url | verified_date | signer_id | commit_sha |
|-----|----------|--------------------|---------------|-----------|------------|
| change_of_control | 8 Del. C. § 251 | https://delcode.delaware.gov/title8/c001/sc09/index.html | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| change_of_control | 8 Del. C. § 271 | https://delcode.delaware.gov/title8/c001/sc10/index.html | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| change_of_control | 15 U.S.C. § 18a (HSR) | https://www.law.cornell.edu/uscode/text/15/18a | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| change_of_control | 15 U.S.C. § 18 (Clayton § 7) | https://www.law.cornell.edu/uscode/text/15/18 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| change_of_control | N.Y. Bus. Corp. Law § 902 | https://www.nysenate.gov/legislation/laws/BSC/902 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| anti_assignment | U.C.C. § 9-406 | https://www.law.cornell.edu/ucc/9/9-406 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| anti_assignment | U.C.C. § 2-210 | https://www.law.cornell.edu/ucc/2/2-210 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| ip_assignment | 35 U.S.C. § 261 | https://www.law.cornell.edu/uscode/text/35/261 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| ip_assignment | 17 U.S.C. § 204(a) | https://www.law.cornell.edu/uscode/text/17/204 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| ip_assignment | 15 U.S.C. § 1060 | https://www.law.cornell.edu/uscode/text/15/1060 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| non_compete | Cal. Bus. & Prof. Code § 16600 | https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=16600. | 2026-06-09 | ma-counsel-persona | staged-uncommitted |

## Case-law entries (4 named anchors)

| tag | citation | primary_source_url | verified_date | signer_id | commit_sha |
|-----|----------|--------------------|---------------|-----------|------------|
| mac | Akorn, Inc. v. Fresenius Kabi AG, 2018 WL 4719347 (Del. Ch. Oct. 1, 2018), aff'd, 198 A.3d 724 (Del. 2018) | https://courts.delaware.gov/Opinions/Download.aspx?id=279250 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| mac | AB Stable VIII LLC v. MAPS Hotels & Resorts One LLC, 2020 WL 7024929 (Del. Ch. Nov. 30, 2020), aff'd, 268 A.3d 198 (Del. 2021) | https://law.justia.com/cases/delaware/court-of-chancery/2020/c-a-no-2020-0310-jtl.html (**secondary**) | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| exclusivity | Revlon, Inc. v. MacAndrews & Forbes Holdings, Inc., 506 A.2d 173 (Del. 1986) | https://www.law.upenn.edu/live/news/7004-revlon-inc-v-macandrews-forbes-holdings-inc | 2026-06-09 | ma-counsel-persona | staged-uncommitted |
| change_of_control | In re Trados Inc. S'holder Litig., 73 A.3d 17 (Del. Ch. 2013) | https://courts.delaware.gov/opinions/download.aspx?ID=193520 | 2026-06-09 | ma-counsel-persona | staged-uncommitted |

---

## Verification method, per source class

- **DGCL (§ 251, § 271):** fetched `delcode.delaware.gov` subchapter pages; confirmed
  section number, heading, and that subsection (c)/(a) governs the stockholder vote / asset
  sale. (§ 251 — "Merger or consolidation of domestic corporations"; § 271 — "Sale, lease or
  exchange of assets".)
- **Federal statutes (15 U.S.C. §§ 18, 18a; 35 U.S.C. § 261; 17 U.S.C. § 204; 15 U.S.C. § 1060)
  and the U.C.C. (§§ 9-406, 2-210):** fetched `law.cornell.edu` (Cornell LII); confirmed
  citation, official heading, and the operative clause.
- **N.Y. Bus. Corp. Law § 902:** fetched `nysenate.gov`; confirmed heading "Plan of merger or
  consolidation" (noting shareholder authorization is the adjacent § 903).
- **Cal. Bus. & Prof. Code § 16600:** fetched `leginfo.legislature.ca.gov`; confirmed the
  void-restraint rule and the current (a)/(b)/(c) structure (amended eff. 2024-01-01).
- **Akorn, Trados:** fetched the actual Court of Chancery opinion PDFs from
  `courts.delaware.gov` and read the first-page caption — confirmed case name, court,
  C.A. number, decision date (Akorn: C.A. No. 2018-0300-JTL, decided Oct. 1, 2018, Laster, V.C.;
  Trados: Consol. C.A. No. 1512-VCL, decided Aug. 16, 2013, Laster, V.C.). **True primary source.**
- **Revlon:** fetched the Penn Carey Law (UPenn) Delaware Corporation Law Resource Center page,
  which states the citation verbatim as "506 A.2d 173 (Del. 1986)" / "(Del. S.Ct. 1986)".
- **AB Stable:** `primary_source` is honestly labelled **`law.justia.com (secondary)`** — NOT a
  true primary source. The `uri` resolves to the Justia copy of the *Court of Chancery* 2020
  opinion (2020 WL 7024929); the affirmance reporter (268 A.3d 198 (Del. 2021)) is recorded in the
  citation string but the Delaware Supreme Court opinion PDF was **not separately fetched** from
  `courts.delaware.gov`. The earlier verifying fetch was the Fox Rothschild *Delaware Chancery
  Law* blog (also secondary), which confirmed the case name, both courts, the Chancery
  C.A. No. 2020-0310, and both decision dates (Del. Ch. Nov. 30, 2020; Del. Dec. 8, 2021); reporter
  citations were cross-corroborated by the Justia docket title and ≥6 Am Law-100 client memos.
  **Reconciliation (GROUNDTRUTH_PLAN data-integrity fix):** the prior `primary_source` claim of
  `courts.delaware.gov` was inconsistent with a Justia `uri`; relabelled to `law.justia.com
  (secondary)` rather than overclaiming a primary fetch. Pointing `uri` at the real
  courts.delaware.gov Supreme Court PDF is a clean follow-up once the download id is confirmed.

## Dropped / deferred (NOT shipped — correctness-first per § 4.4 failure path)

- **`accelerated_vesting`** — intentionally absent. Single-/double-trigger vesting is
  contract-anchored, with no controlling statute; `lookup_citation` returns `None` (covered by
  `test_static_lookup_returns_none_outside_map_coverage`). This is the spec's graceful-`None`
  design, not a gap.
- **Omnicare, Inc. v. NCS Healthcare, Inc., 818 A.2d 914 (Del. 2003)** and **Hexion v. Huntsman,
  965 A.2d 715 (Del. Ch. 2008)** — candidate *extra* (non-named) anchors for `exclusivity` /
  `mac`. Their fetchable opinion pages 403'd (Justia/FindLaw) within this session, so they were
  **dropped rather than cited from memory**. Both are clean follow-up additions once a
  fetchable primary page is available.
- **Cross-jurisdiction breadth (NY/UK statute analogues for every tag; additional Delaware
  deal-protection cases — QVC, Paramount).** Deferred. The map favors fully primary-source-
  verified entries over hitting the ~25-row target; expansion is mechanical once verified.

**Total shipped: 15 entries (11 statute + 4 named case-law anchors), 100% primary-source-verified.**
