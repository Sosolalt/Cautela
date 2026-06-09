# Internal-30 Deal Bank — Source Material for D5–D9 Annotation

## 0. Split rule — Calibration vs. Narrative (read first)

The Internal-30 source pool is **split into two non-overlapping sets** with different epistemic roles. This split is methodology-defining: violating it invalidates every recall number this project reports.

**Why the split exists.** Gemini 3 Pro's training cutoff is **2025-01-01** per the official Google DeepMind model card. Every famous busted-deal precedent we initially considered for the held-out fold (Akorn/Fresenius, AB Stable/MAPS, Tiffany/LVMH, BMS/Celgene CVR, Hexion/Huntsman, IBP/Tyson, Channel Medsystems, Forescout/Advent, SQL Solutions v. Oracle, Meso Scale v. Roche, Cincom v. Novelis, PPG v. Guardian) is dated **before** that cutoff, and each is saturated in publicly indexed law-firm alerts (Skadden, Cleary, Jones Day, Cooley, Cadwalader, V&E, Weil, Milbank, Akin, Hogan Lovells, Faegre, ABA Business Law Today, Harvard CGI), Wikipedia, Quimbee, casebooks, and student outlines. The probability that Gemini 3 Pro has memorized the load-bearing clause language and the court's reasoning is effectively 1. Reporting "recall" on those cases would measure pretraining recall, not the agent's reasoning over the contract. That is a retrieval check on memorized content, not an evaluation.

**The rule.**

1. **Calibration-N** = deals whose **load-bearing public event** (the document the agent must surface — judgment, arbitration award, consent order, close 8-K, merits-stage docket filing) is dated **AFTER 2025-01-01**. Calibration-N drives **every reported recall number** (cluster-bootstrap 95% LB headline, Wilson LB exploratory per-finding-IID cross-check, fold-5 held-out recall, τ_h / τ_f sweep). The 5 allow-listed Bucket-A deals are kept in Calibration-N as the live demo path but are **explicitly flagged** so reported recall on them is reported **separately** as "demo-path recall," never aggregated into the held-out recall headline.
2. **Narrative-10** = famous pre-cutoff precedent cases. Used **only** in demo voiceover, illustrative captions, and methodology framing ("the agent flags the same clause Strine pointed at in IBP/Tyson"). **Never** in metrics. Every Narrative-10 cell carries the caption: *Famous precedent — illustrative use only; NOT in reported recall metrics.*
3. **No padding.** If post-cutoff supply is short we name the set honestly (Calibration-17, Calibration-12) and explain the gap. We do not move pre-cutoff deals into Calibration-N to hit a round number.
4. **Audit hook.** Any deal added to Calibration-N must cite a primary-source URL (EDGAR, courts.delaware.gov, justice.gov, ftc.gov, ec.europa.eu, ICC, FRB, OCC) **with a filing/decision date string of the form YYYY-MM-DD that is strictly greater than 2025-01-01** in the row. A reviewer can grep the date column and reject any row that fails.

**Internal-30 in the PROJECT_LOG TL;DR** = Calibration-N ∪ Narrative-10 as a *source pool*. The "30" was always a rough headcount; only Calibration-N enters metrics. Current counts: **Calibration-17** (12 post-cutoff + 5 demo-path) + **Narrative-12** = source pool of 29 distinct deals/cases. *Effective count is Calibration-16 until the §1A row 12 TBD "mid-2025 clean comparable" is filled; conservative floor is Calibration-13 if the three borderline rows (Tapestry/Capri, Amazon/iRobot, Adobe/Figma) are also rejected.* The PROJECT_LOG TL;DR phrasing "Internal-30" is preserved for continuity; this document is the authoritative breakdown.

---

## 1. Calibration-17 — held-out / metric-bearing set

All recall numbers reported by this project (fold-5 held-out, full-set cluster-bootstrap 95% LB headline, full-set Wilson LB as exploratory per-finding-IID cross-check, τ_h / τ_f calibration) are computed over Calibration-17. The two sub-groups below differ in *role*, not in *eligibility*: both are part of the metric base, but demo-path recall is reported as a **separate line** from held-out recall, never aggregated.

### 1A. Post-cutoff core (12 deals — load-bearing event after 2025-01-01)

| Deal | Load-bearing event | Event date | Primary doc | Documented stress / clause |
|---|---|---|---|---|
| **HPE / Juniper — DOJ Final Judgment** | DOJ settlement: divest Instant On WLAN + auction-license Mist AI source | **2025-06-28** | [Juniper 8-K Ex 99.1](https://www.sec.gov/Archives/edgar/data/0001043604/000119312525154400/d912160dex991.htm) · [merger agreement accession 000119312524005659](https://www.sec.gov/Archives/edgar/data/1043604/000119312524005659/) | Regulatory-efforts §6.x divestiture-cap language — DOJ remedy proves cap mattered |
| **Chevron / Hess close — Stabroek JOA arbitration cleared** | ICC arbitration ruling for Chevron/Hess on Stabroek ROFR | **2025-07-18** | [Chevron close 8-K (Jul 18 2025)](https://www.sec.gov/Archives/edgar/data/93410/000095014225001949/eh250652625_8k.htm) · [Chevron close press release Ex 99.1](https://www.sec.gov/Archives/edgar/data/93410/000095014225001949/eh250652625_ex9901.htm) · [V&E Stabroek analysis](https://www.velaw.com/insights/the-stabroek-joa-arbitration-is-it-time-to-revisit-joa-change-in-control-provisions/) · [Chevron/Hess merger agreement 8-K (Oct 2023)](https://www.sec.gov/Archives/edgar/data/93410/000095014223002670/eh230413259_8k-agmt.htm) | JOA ROFR + CoC definition + assignment clause — turns on whether parent-level merger = "indirect" transfer of participating interest. Cross-clause reasoning. **Note on URL fix**: the prior draft cited `eh250651090_8k.htm` (404). Replaced with the verified close 8-K `eh250652625_8k.htm` from the same accession 000095014225001949. |
| **Albertsons v. Kroger — Chancery merits docket** | Post-cutoff Chancery merits briefing + Kroger counterclaims (complaint Dec 11 2024 is pre-cutoff and excluded) | **2025-01-21** (Harvard CGI practice-points post-cutoff) and forward | [Harvard CGI 2025-01-21 — Practice Points (Fried Frank)](https://corpgov.law.harvard.edu/2025/01/21/practice-points-arising-from-albertsons-claims-against-kroger-for-breach-of-their-merger-agreement/) · [Kroger/Albertsons merger agreement Ex 2.1](https://www.sec.gov/Archives/edgar/data/56873/000110465922108671/tm2227942d1_ex2-1.htm) · [Kroger 8-K + $600M fee dispute](https://www.sec.gov/Archives/edgar/data/56873/000110465924127669/tm2427516d10_8k.htm) · [FTC Part 3 complaint](https://www.ftc.gov/system/files/ftc_gov/pdf/d9428_2310004krogeralbertsonsp3complaintpublic.pdf) | $600M parent termination fee + asymmetric efforts covenant — being litigated post-cutoff in Albertsons v. Kroger merits docket |
| **Synopsys / Ansys close** | FTC consent + closing | **2025-07-17** | [Synopsys/Ansys merger Ex 2.1](https://www.sec.gov/Archives/edgar/data/883241/000119312524008120/d720113dex21.htm) · [Synopsys close 8-K Ex 99.1 (accession 000114036125026139, filed 2025-07-17)](https://www.sec.gov/Archives/edgar/data/883241/000114036125026139/ef20051970_ex99-1.htm) | Routine FTC divestiture covenant + closing CPs |
| **Paramount / Skydance close** | Closing of merger after final regulatory approvals | **2025-08-07** | [Paramount Skydance Corp 8-K12B (close)](https://www.sec.gov/Archives/edgar/data/0002041610/000119312525175046/d841914d8k12b.htm) · [Paramount Global DEFM14C (2025-02)](https://www.sec.gov/Archives/edgar/data/0000813828/000119312525026059/d813356ddefm14c.htm) · [original merger Ex 2.1](https://www.sec.gov/Archives/edgar/data/813828/000119312524177535/d860362dex21.htm) | 45-day go-shop + matched-bid language — Ellison/Bronfman competing bids exploited go-shop. Closing 8-K12B verifies final amendment landscape. |
| **Capital One / Discover close** | Federal Reserve + OCC approval Apr 18 2025; close May 18 2025 | **2025-05-18** | [Discover 8-K (Federal Reserve approval, 2025-04)](https://www.sec.gov/Archives/edgar/data/0001393612/000119312525085812/d948842dex991.htm) · [Capital One 8-K (close, 2025-05)](https://www.sec.gov/Archives/edgar/data/0000927628/000119312525122059/d934475dex991.htm) · [original Ex 2.1](https://www.sec.gov/Archives/edgar/data/927628/000119312524042826/d780383dex21.htm) | Bank-regulatory CPs + Reg-Y interchange-fee carve-outs; close conditions tested through post-cutoff approval cycle |
| **Mars / Kellanova — EC final approval** | European Commission unconditional approval (last regulatory hurdle) | **2025-12-08** | [Mars/Kellanova Ex 2.1](https://www.sec.gov/Archives/edgar/data/0000055067/000119312524200233/d884455dex21.htm) · [EC press release IP/25/2938 — Commission approves Mars acquisition of Kellanova](https://ec.europa.eu/commission/presscorner/detail/en/ip_25_2938) · [Kellanova newsroom 2025-12-08 (date-anchor)](https://newsroom.kellanova.com/2025-12-8-MARS-RECEIVES-FINAL-REGULATORY-APPROVAL-AND-MOVES-TO-CLOSE-ACQUISITION-OF-KELLANOVA) | EC Phase-II merger-control CP + Outside Date interaction — the deal's last regulatory hurdle cleared post-cutoff |
| **Tapestry / Capri walk** | $8.5B deal abandoned after FTC PI; relevant post-cutoff event is the residual Outside Date / fee true-up trail | **2025-02-10** (Outside Date) | [Tapestry/Capri Ex 2.1](https://www.sec.gov/Archives/edgar/data/1530721/000119312523208278/d532594dex21.htm) · [FTC complaint Apr 2024](https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-moves-block-tapestrys-acquisition-capri) · [Tapestry Answer (cites contract)](https://www.ftc.gov/system/files/ftc_gov/pdf/610552.2024.05.06_tapestry_answer_public_record.pdf) | Outside Date (Feb 10 2025) + weak regulatory-efforts covenant. Outside Date itself is post-cutoff; load-bearing because that's the clause that ran the clock. |
| **JetBlue / Spirit ticking-fee trail** | Post-walk ticking-fee dispute and Spirit Ch. 11 trail (Spirit filed Nov 2024, emerged 2025) | **2025-03-12** (Spirit Ch. 11 emergence) | [JetBlue/Spirit Ex 2.1](https://www.sec.gov/Archives/edgar/data/1158463/000119312522204208/d319514dex21.htm) · [DOJ complaint](https://www.justice.gov/atr/case-document/file/1573131/dl) | $2.50/share prepayment + $0.10/month ticking fee — the rare ticking-fee mechanism re-litigated in post-walk disputes |
| **Amazon / iRobot fee mechanics post-walk** | $94M RTF paid; iRobot 2025 going-concern disclosures cite the residual covenant trail | **2025** (iRobot 10-K going-concern, post-cutoff) | iRobot Aug 2022 8-K (CIK 1159167) · [iRobot termination 8-K](https://www.sec.gov/Archives/edgar/data/0001159167/000119312524017523/d741198d8k.htm) · [Termination Agt with fee mechanics](https://www.sec.gov/Archives/edgar/data/0001159167/000119312524017523/d741198dex101.htm) | $94M RTF + EC merger-control CP. Note: termination agreement itself is Jan 2024 (pre-cutoff); included because the **iRobot going-concern fallout** is the post-cutoff signal the agent must explain. Borderline — flag explicitly. |
| **Adobe / Figma post-mortem (CMA final report)** | CMA Phase 2 final report post-cutoff; $1B RTF fully paid; treated as comparative baseline | **2025** (CMA closing notice) | [Adobe/Figma Ex 2.1](https://www.sec.gov/Archives/edgar/data/796343/000114036122033413/ny20005310x2_ex2-1.htm) · [CMA Phase 2 provisional](https://assets.publishing.service.gov.uk/media/6565c3e262180b000dce82c1/Summary_of_provisional_findings_pdfa.pdf) | $1B RTF + weak regulatory commitment language. Borderline — included only because CMA closing trail is post-cutoff; flag explicitly. |
| **Mid-2025 clean comparable** (negative-class slot) | TBD — pick a mid-2025 mid-cap close 8-K with no FTC/DOJ/EC/CMA action via EDGAR full-text search at annotation time | post-2025-01-01 required | EDGAR search at annotation time | Closed without contractual stress — calibrates false-positive rate against τ_f |

### 1B. Demo-path deals (5 deals — DEMO-PATH, recall reported separately)

These five are pre-cutoff and therefore **not held-out clean**. They remain in Calibration-17 because they **are** the frontend demo path — the agent has to work on them live. Their recall is reported as a **separate line** ("demo-path recall, n=5") in every metrics table, never aggregated into the held-out recall headline.

| Deal | EDGAR Ex 2.1 | Documented stress | Demo angle | Flag |
|---|---|---|---|---|
| **Microsoft / Activision** | [tm223212d3_ex2-1.htm](https://www.sec.gov/Archives/edgar/data/718877/000110465922005154/tm223212d3_ex2-1.htm) | CMA blocked Apr 2023, reversed Oct 2023 after Ubisoft cloud-rights divestiture ([gov.uk/cma](https://www.gov.uk/cma-cases/microsoft-slash-activision-blizzard-merger-inquiry)); tiered RTF escalator $2B→$4.5B; closed 5 days before max-tier trigger | Article VIII RTF escalator + hell-or-high-water carve-out in §6.x antitrust covenant | **[DEMO-PATH — recall reported separately, not held-out]** |
| **Pfizer / Seagen** | [d467472dex21.htm](https://www.sec.gov/Archives/edgar/data/1060736/000119312523068474/d467472dex21.htm) | FTC Second Request 14 Jul 2023; remedy = irrevocable Bavencio royalty donation to AACR | MAE pandemic/regulatory carve-outs + antitrust-efforts §6.3 | **[DEMO-PATH — recall reported separately, not held-out]** |
| **Cisco / Splunk** | [tm2326347d1_ex2-1.htm](https://www.sec.gov/Archives/edgar/data/1353283/000110465923102594/tm2326347d1_ex2-1.htm) | EU Phase I unconditional Mar 2024; heavy executive-retention + double-trigger CoC | §2.4/§2.5 equity-treatment exhibit — accelerated vesting payout buried in schedule | **[DEMO-PATH — recall reported separately, not held-out]** |
| **ExxonMobil / Pioneer** | [d417986dex21.htm](https://www.sec.gov/Archives/edgar/data/1038357/000119312523253935/d417986dex21.htm) | FTC consent order May 2024 banning Scheffield from XOM board ([ftc.gov](https://www.ftc.gov/news-events/news/press-releases/2024/05/ftc-order-bans-former-pioneer-ceo-exxon-board-seat-exxon-pioneer-deal)); reopened Jul 2025 | Post-closing director-designation covenant — the exact clause the FTC complaint targeted | **[DEMO-PATH — recall reported separately, not held-out]** |
| **HPE / Juniper (signing)** | [d107225dex21.htm](https://www.sec.gov/Archives/edgar/data/1043604/000119312524005659/d107225dex21.htm) | Signing-side regulatory-efforts language; pair with the post-cutoff DOJ Final Judgment row in 1A for the cross-time delta | Regulatory-efforts §6.x divestiture-cap language at signing vs. as enforced | **[DEMO-PATH — recall reported separately, not held-out]** |

### Calibration count statement

**Calibration-17 = 12 post-cutoff core + 5 demo-path = 17.** *Effective count is Calibration-16 until row 12 ("Mid-2025 clean comparable") is filled at annotation time — that row is a TBD placeholder and should not be silently counted in any pre-annotation metric.* The original "20" target was not met because:
- Truly post-cutoff M&A with publicly indexed contractual-stress evidence is scarce in the 2025-01-01 → annotation-date window.
- Padding with pre-cutoff deals would defeat the entire purpose of the split.
- Three of the 12 core rows (Tapestry/Capri walk Outside-Date trail, Amazon/iRobot going-concern fallout, Adobe/Figma CMA closing notice) are borderline post-cutoff — flagged inline. If a reviewer rejects all three **and** row 12 is unfilled, the conservative floor is **Calibration-13** (8 core + 5 demo-path); if row 12 is filled but the three borderline rows are rejected, the floor is **Calibration-14** (9 core + 5 demo-path).

---

## 2. Narrative-10 — illustrative / demo-voiceover only

**Every cell below carries the caption: *Famous precedent — illustrative use only; NOT in reported recall metrics.* These deals do not enter cluster bootstrap (headline), Wilson LB (exploratory cross-check), fold-5 recall, or any τ calibration.** They exist to give the demo a vocabulary ("the same clause Strine pointed at in IBP/Tyson," "the Akorn fact pattern") and to seed the annotator's few-shot prompts. Twelve are listed; we call the section "Narrative-10" because the name has stuck in the project log — the extra two are kept as bench-warmers in case one drops out during annotation.

| Case / Deal | Public doc | Court opinion | Load-bearing clause | Caption |
|---|---|---|---|---|
| **Akorn / Fresenius** (2017→2018) | [ex2-1.htm](https://www.sec.gov/Archives/edgar/data/0000003116/000095015717000499/ex2-1.htm) | [Laster Ch. opinion](https://courts.delaware.gov/Opinions/Download.aspx?id=279250) · [Supreme Ct affirm](https://courts.delaware.gov/Opinions/Download.aspx?id=282110) | §3.18 Regulatory Compliance reps + MAE definition lacking industry-wide carve-out; §5.1 Ordinary Course | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **AB Stable / MAPS** (Anbang→Mirae) | filed under seal — see opinion appendix | [Laster Ch. opinion](https://courts.delaware.gov/Opinions/Download.aspx?id=314220) · DE Supreme Ct affirm Dec 2021 | §5.1 Ordinary Course is INDEPENDENT of MAE carve-outs; "ordinary course" = historical/customary | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **Tiffany / LVMH** (Nov 2019) | [d840067dex21.htm](https://www.sec.gov/Archives/edgar/data/0000098246/000119312519299997/d840067dex21.htm) | Settled at $131.50; LVMH counterclaim filing | §3.1 MAE carve-out for "general economic conditions"; §5.1 Ordinary Course lacks pandemic-response exception | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **BMS / Celgene CVR** | [tv510358_ex2-1.htm](https://www.sec.gov/Archives/edgar/data/816284/000114420419000539/tv510358_ex2-1.htm) | [SDNY summary](https://www.skadden.com/-/media/files/publications/2023/05/inside-the-courts/in-re-bristolmyers-squibb-company-cvr-securities-litigation.pdf) | CVR "diligent efforts" + hard FDA-approval milestone (Liso-cel 12/31/2020) with NO force-majeure / regulatory-delay extension. **$6.4 billion forfeited to Celgene CVR holders after Liso-cel approval came 36 days late (Feb 5 2021 vs. Dec 31 2020 milestone) — figures per Skadden SDNY summary.** | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **Hexion / Huntsman** (2008) | [Huntsman EDGAR Jul 2007 8-Ks](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001307954&type=8-K&dateb=20071231) | [Lamb Ch. Sept 2008](https://courts.delaware.gov/Opinions/Download.aspx?id=112500) | MAE comparing target to industry-wide benchmarks shifts burden; "knowing & intentional breach" uncapped by RTF | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **IBP / Tyson** (2001, Strine — foundational MAE) | [IBP 425s](https://www.sec.gov/Archives/edgar/data/0000052477/000010049301500021/ibp425_081301final.htm) | [Strine 789 A.2d 14 (Del. Ch. opinion PDF)](https://courts.delaware.gov/OPINIONS/download.aspx?ID=2530) — *replaces broken Leagle 403* | MAE requires "durationally-significant" harm to long-term earnings power | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **Channel Medsystems / Boston Scientific** | [ss160924_8k.htm](https://www.sec.gov/Archives/edgar/data/0000885725/000094787119000976/ss160924_8k.htm) | [Bouchard Ch. Dec 2019](https://courts.delaware.gov/Opinions/Download.aspx?id=299480) | MAE "reasonably be expected to" forward-looking standard; reps without fraud/integrity backstop | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **Forescout / Advent** (Feb 2020, pandemic MAE walked) | [tm206949d4_ex99-1.htm](https://www.sec.gov/Archives/edgar/data/0001145057/000110465920012197/tm206949d4_ex99-1.htm) | Settled — repriced $33→$29 | MAE *explicitly* allocates COVID-19 risk to buyer | *Famous precedent — illustrative use only; NOT in reported recall metrics.* (Inverse beat: agent says "don't invoke MAE here.") |
| **Cincom Systems v. Novelis** (6th Cir. 2009) | [FindLaw](https://caselaw.findlaw.com/court/us-6th-circuit/1397941.html) | 581 F.3d 431 | "non-exclusive and nontransferable" — internal restructure through forward merger killed the license | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **SQL Solutions v. Oracle** (N.D. Cal. 1991, unreported) | [Harvard CorpGov summary](https://corpgov.law.harvard.edu/2013/03/13/delaware-court-rules-on-reverse-triangular-mergers-and-anti-assignment-provisions/) | unreported | Software anti-assignment with no explicit CoC clause — RTM triggered it because acquirer was a direct competitor | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **Meso Scale v. Roche** (Del. Ch. 2013, 62 A.3d 62) | [FindLaw](https://caselaw.findlaw.com/court/de-court-of-chancery/1625367.html) | VC Parsons | "assigned by operation of law or otherwise" — RTM is NOT assignment by operation of law. Pair with SQL Solutions. | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |
| **PPG v. Guardian** (6th Cir. 1979, 597 F.2d 1090) | [law.resource.org](https://law.resource.org/pub/us/case/reporter/F2/597/597.F2d.1090.77-3167.77-3166.html) | foundational | Patent license "non-assignable and non-transferable"; forward merger terminated despite state merger statutes | *Famous precedent — illustrative use only; NOT in reported recall metrics.* |

Tronox excluded (no narrative wedge that the above 12 don't already cover).

---

## 3. Selection rule

**Calibration-N selection (auditable, keyed off 2025-01-01 cutoff):**

A deal is eligible for Calibration-N if and only if **at least one** of the following holds:

(a) The deal's **load-bearing public event** — defined as the court judgment, arbitration award, consent order, close 8-K, EC/CMA/DOJ/FTC final decision, Chancery merits-stage filing, or termination 8-K that the agent must surface to be scored correct — has a **document date** strictly **after 2025-01-01**. The row must cite the URL and date string inline so a reviewer can grep-verify.

(b) The deal is one of the **5 allow-listed Bucket-A demo-path deals** (MSFT/ATVI, PFE/Seagen, CSCO/SPLK, XOM/Pioneer, HPE/JNPR-signing). These are kept because the frontend demo runs against them; their row is flagged `[DEMO-PATH — recall reported separately, not held-out]` and their recall is **never aggregated** into the held-out recall headline.

A deal is **ineligible** for Calibration-N (and belongs in Narrative-10 instead) if its load-bearing event predates 2025-01-01 and it is not on the demo-path allow-list. Famous precedent cases (Akorn, AB Stable, IBP/Tyson, etc.) fail this test by construction.

**Padding is forbidden.** If the Calibration-N count falls short of the original Internal-30 target, name the set honestly (Calibration-17, Calibration-14, Calibration-12) and document the gap. Do not move pre-cutoff deals across.

**Narrative-10 selection.** Famous, well-litigated pre-cutoff cases that give the demo voiceover a clause-level vocabulary. No metric role. No size target (we have 12 listed, called Narrative-10 for project-log continuity).

---

## 4. Annotation bootstrap (saves the 15–25h of human-loop work)

Per Bucket E research, pull these three before annotation begins so the LLM-assist has strong priors:

1. **ACORD** ([HF `theatticusproject/acord`](https://huggingface.co/datasets/theatticusproject/acord)) — 126K graded query-clause pairs across 9 categories including **Change of Control, Indemnification, Limitation of Liability**. Same Atticus license/format as CUAD. Use as zero-shot retriever; only spot-check top-k.
2. **LEDGAR** ([github](https://github.com/dtuggener/LEDGAR_provision_classification), LexGLUE subset 80K/100-label) — silver labels on CoC, anti-assignment, indemnification, non-compete, termination. Few-shot prompt bank + negative-mining pool.
3. **ABA Deal Points Studies** ([landing](https://www.americanbar.org/groups/business_law/about/committees/mergers-and-acquisitions/deal-points/), 2024 Public Target + 2025 Private Target) — frequency distributions per deal-point; use as priors for LLM-annotator calibration. MAUD only covers the 2021 Public Target study.

**Skip**: ContractNLI (NDAs, wrong type), LexGLUE harness (redundant if you pull LEDGAR), Pile of Law (NC license, demo-unsafe). LegalBench-RAG optional as published retrieval baseline.

---

## 5. Fold-5 (held-out, frozen for Reflector non-regression)

**Fold-5 is a strict subset of Calibration-17.** No Narrative-10 case may appear in Fold-5. This replaces the prior fold-5 list (Akorn, AB Stable, BMS/Celgene, Stabroek, Kroger, Forescout) — five of those six were Narrative-10 cases and would have made fold-5 recall a memorization check.

**Recommended Fold-5 (6 deals):**

1. **HPE / Juniper — DOJ Final Judgment** (2025-06-28) — clean post-cutoff regulatory remedy
2. **Chevron / Hess — Stabroek JOA arbitration cleared** (2025-07-18) — cross-clause CoC reasoning, post-cutoff
3. **Albertsons v. Kroger — Chancery merits docket** (2025-01-21+) — live merits-stage signal, post-cutoff briefing
4. **Synopsys / Ansys close** (2025-07-17) — clean post-cutoff FTC consent + close
5. **Mars / Kellanova — EC final approval** (2025-12-08) — clean post-cutoff EC Phase-II
6. **ExxonMobil / Pioneer** (demo-path, **flagged**) — kept for one demo-path cell in fold-5 so the held-out fold also runs the live demo deal; recall on this row is reported **separately** in the fold-5 table, not aggregated with the other five.

Rows 1–5 carry the held-out recall headline. Row 6 is reported as "demo-path recall in fold-5, n=1" on a separate line, never summed in.

---

## 6. Sources

Primary: sec.gov · courts.delaware.gov · ftc.gov · justice.gov · ec.europa.eu · gov.uk/cma-cases · federalreserve.gov · occ.gov · ICC.
Secondary: Harvard CorpGov Forum · ABA Business Law · Skadden / Davis Polk / V&E client notes (cited inline above where they were the only public surface).
Model card cutoff source: Google DeepMind, Gemini 3 Pro model card, training cutoff 2025-01-01.
