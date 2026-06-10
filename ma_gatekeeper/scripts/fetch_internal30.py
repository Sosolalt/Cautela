"""Fetch the Calibration-17 EX-2.1 merger agreements into `data/edgar/` for §6.

This populates the source corpus the annotation cohort (see
`docs/internal30_annotation_cohort.md`) labels. Per deal it writes:

  data/edgar/raw/<deal_id>.htm   — raw EX-2.1 bytes, exactly as SEC served them
                                   (provenance; never edited)
  data/edgar/<deal_id>.txt       — canonical UTF-8 plain-text extraction.
                                   **THIS is the offset anchor.** Every gold
                                   span's char_start/char_end must satisfy
                                   `text[char_start:char_end] == span_text`
                                   against THIS file (the loader
                                   `scripts/annotate.py:_coerce_span` enforces
                                   it). Both annotation cohorts AND the Argilla
                                   import must index this same .txt.
  data/edgar/manifest.json       — deal_id -> provenance + text_sha256 so the
                                   offsets are reproducible and auditable.

SCOPE — Calibration-17 only (the metric-bearing merger agreements). The
Narrative-12 famous-precedent cases (Akorn, AB Stable, IBP/Tyson, Meso Scale,
Cincom, ...) are **deliberately excluded**: they are pre-2025-01-01 and
saturated in training data, so annotating them into the calibration / kappa
gold set would reintroduce exactly the contamination the deal-bank split exists
to prevent (see `docs/internal30_deal_bank.md` §0). They are illustrative-only.

SEC etiquette: a descriptive User-Agent with contact info is REQUIRED on every
request (SEC 403s anonymous traffic). We read it from SEC_EDGAR_USER_AGENT —
the same env var `scripts/verify_allow_list.py` uses — and self-rate-limit
under SEC's 10 req/s guidance.

Usage:
  export SEC_EDGAR_USER_AGENT="hugo.majerczyk@proton.me MA-Gatekeeper"
  python -m scripts.fetch_internal30                 # all deals -> data/edgar/
  python -m scripts.fetch_internal30 --list          # show the plan, fetch nothing
  python -m scripts.fetch_internal30 --only synopsys_ansys
  python -m scripts.fetch_internal30 --out data/edgar
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import html
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

_LOG = logging.getLogger("fetch_internal30")

# Politeness: SEC asks for <= 10 req/s. We make a couple of requests per deal,
# so a small fixed delay keeps us comfortably under that.
_REQUEST_DELAY_SEC = 0.3
_TIMEOUT_SEC = 60


@dataclasses.dataclass(frozen=True)
class Deal:
    """One Calibration-17 deal whose EX-2.1 merger agreement we fetch.

    `ex21_url` is the pinned exhibit URL from the deal bank (preferred — it
    pins the EXACT document, which a re-resolved "latest filing" lookup could
    drift away from). When only (cik, accession) are known, leave `ex21_url`
    None and the fetcher resolves the EX-2.1 document from the accession's
    index.json. When even the accession is unknown, leave both None and the
    deal is reported as a TODO for the operator rather than silently skipped.
    """

    deal_id: str
    label: str
    set_: str  # "demo_path" | "calibration_core"
    cik: str
    accession: str | None
    ex21_url: str | None
    note: str = ""


# ---------------------------------------------------------------------------
# The Calibration-17 corpus. URLs are the pinned EX-2.1 exhibits transcribed
# from docs/internal30_deal_bank.md §1A / §1B. HPE/Juniper appears once: the
# post-cutoff "DOJ Final Judgment" row and the demo-path "signing" row share
# the SAME merger agreement (accession 000119312524005659), so it is one
# contract, listed under demo_path.
# ---------------------------------------------------------------------------
DEALS: tuple[Deal, ...] = (
    # --- 1B. Demo-path (5) -------------------------------------------------
    Deal("msft_activision", "Microsoft / Activision Blizzard (2023)", "demo_path",
         "718877", "000110465922005154",
         "https://www.sec.gov/Archives/edgar/data/718877/000110465922005154/tm223212d3_ex2-1.htm"),
    Deal("pfizer_seagen", "Pfizer / Seagen (2023)", "demo_path",
         "1060736", "000119312523068474",
         "https://www.sec.gov/Archives/edgar/data/1060736/000119312523068474/d467472dex21.htm"),
    Deal("cisco_splunk", "Cisco / Splunk (2024)", "demo_path",
         "1353283", "000110465923102594",
         "https://www.sec.gov/Archives/edgar/data/1353283/000110465923102594/tm2326347d1_ex2-1.htm"),
    Deal("exxon_pioneer", "ExxonMobil / Pioneer Natural Resources (2024)", "demo_path",
         "1038357", "000119312523253935",
         "https://www.sec.gov/Archives/edgar/data/1038357/000119312523253935/d417986dex21.htm"),
    Deal("hpe_juniper", "HPE / Juniper Networks (2024 signing; 2025 DOJ FJ)", "demo_path",
         "1043604", "000119312524005659",
         "https://www.sec.gov/Archives/edgar/data/1043604/000119312524005659/d107225dex21.htm"),
    # --- 1A. Post-cutoff core (pinned EX-2.1 available) --------------------
    Deal("albertsons_kroger", "Kroger / Albertsons (2022; merits docket 2025)", "calibration_core",
         "56873", "000110465922108671",
         "https://www.sec.gov/Archives/edgar/data/56873/000110465922108671/tm2227942d1_ex2-1.htm"),
    Deal("synopsys_ansys", "Synopsys / Ansys (close 2025-07-17)", "calibration_core",
         "883241", "000119312524008120",
         "https://www.sec.gov/Archives/edgar/data/883241/000119312524008120/d720113dex21.htm"),
    Deal("paramount_skydance", "Paramount / Skydance (close 2025-08-07)", "calibration_core",
         "813828", "000119312524177535",
         "https://www.sec.gov/Archives/edgar/data/813828/000119312524177535/d860362dex21.htm"),
    Deal("capitalone_discover", "Capital One / Discover (close 2025-05-18)", "calibration_core",
         "927628", "000119312524042826",
         "https://www.sec.gov/Archives/edgar/data/927628/000119312524042826/d780383dex21.htm"),
    Deal("mars_kellanova", "Mars / Kellanova (EC approval 2025-12-08)", "calibration_core",
         "55067", "000119312524200233",
         "https://www.sec.gov/Archives/edgar/data/0000055067/000119312524200233/d884455dex21.htm"),
    Deal("tapestry_capri", "Tapestry / Capri (Outside Date 2025-02-10)", "calibration_core",
         "1530721", "000119312523208278",
         "https://www.sec.gov/Archives/edgar/data/1530721/000119312523208278/d532594dex21.htm",
         note="Borderline post-cutoff (deal-bank flags it)."),
    Deal("jetblue_spirit", "JetBlue / Spirit (Ch.11 emergence 2025-03-12)", "calibration_core",
         "1158463", "000119312522204208",
         "https://www.sec.gov/Archives/edgar/data/1158463/000119312522204208/d319514dex21.htm"),
    Deal("adobe_figma", "Adobe / Figma (CMA final report 2025)", "calibration_core",
         "796343", "000114036122033413",
         "https://www.sec.gov/Archives/edgar/data/796343/000114036122033413/ny20005310x2_ex2-1.htm",
         note="Borderline post-cutoff (deal-bank flags it)."),
    # --- 1A. Post-cutoff core (accession known, EX-2.1 doc resolved at run) -
    Deal("chevron_hess", "Chevron / Hess (Stabroek JOA arbitration 2025-07-18)", "calibration_core",
         "93410", "000095014223002670",
         "https://www.sec.gov/Archives/edgar/data/93410/000095014223002670/eh230413259_ex0201.htm",
         note="EX-2.01 in Chevron's merger-agreement 8-K (named ex0201, not ex2-1)."),
    # --- 1A. Unresolved — operator must supply before fetch ----------------
    Deal("amazon_irobot", "Amazon / iRobot (going-concern fallout 2025)", "calibration_core",
         "1159167", None, None,
         note="TODO: deal bank gives no EX-2.1 accession. Find the iRobot Aug-2022 "
              "merger-agreement 8-K accession and add it, or drop (borderline)."),
    Deal("mid2025_clean_comparable", "Mid-2025 clean comparable (negative class)", "calibration_core",
         "", None, None,
         note="TODO: pick a mid-2025 mid-cap close 8-K with NO FTC/DOJ/EC/CMA action "
              "via EDGAR full-text search, then add its CIK + EX-2.1 URL here."),
)


# ---------------------------------------------------------------------------
# HTML -> canonical text
# ---------------------------------------------------------------------------
class _TextExtractor(HTMLParser):
    """Minimal, dependency-free HTML -> text.

    EX-2.1 exhibits are self-contained HTML (often EDGAR/word-export markup).
    We drop <script>/<style>, turn block-level tags into newlines so clause
    boundaries survive, and unescape entities. Stdlib-only so this never fails
    on a missing optional dependency. Eyeball one .txt before the full burn
    (the docstring on main() says so) — extraction quality is the one thing
    worth a human glance, because every gold offset indexes this output.
    """

    _BLOCK = {
        "p", "br", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6",
        "table", "section", "article", "td",
    }
    _DROP = {"script", "style", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._suppress = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in self._DROP:
            self._suppress += 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._DROP and self._suppress:
            self._suppress -= 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._suppress:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        # Collapse runs of blank lines and trailing spaces, but DO NOT touch
        # intra-line spacing (offsets must stay stable & legible).
        lines = [ln.rstrip() for ln in raw.splitlines()]
        out: list[str] = []
        blank = 0
        for ln in lines:
            if ln.strip():
                blank = 0
                out.append(ln)
            else:
                blank += 1
                if blank <= 1:
                    out.append("")
        return "\n".join(out).strip() + "\n"


def _html_to_text(raw: bytes) -> str:
    parser = _TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return html.unescape(parser.text())


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _get(url: str, user_agent: str) -> bytes:
    """GET with the SEC-required User-Agent header. Raises on non-200."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:  # noqa: S310
        body = resp.read()
    time.sleep(_REQUEST_DELAY_SEC)
    return body


def _resolve_ex21_url(cik: str, accession: str, user_agent: str) -> str:
    """Find the EX-2.1 document URL inside an accession via its index.json.

    EDGAR exposes a per-accession manifest at
    .../Archives/edgar/data/<cik>/<accession_no_dashes>/index.json whose
    `directory.item[]` lists each document with a `type`. We pick the item
    whose type is EX-2.1 (falling back to a filename heuristic).
    """
    acc = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
    index = json.loads(_get(f"{base}/index.json", user_agent))
    items = index.get("directory", {}).get("item", [])
    # NOTE: index.json's `type` field is the row ICON (e.g. "text.gif"), not the
    # SEC document type — useless for matching. We match on filename instead.
    # EX-2.1 exhibits surface under many filename spellings: ex2-1, ex2_1, ex21,
    # dex21, dex2-1, ex0201, ex2.01. This regex catches "ex" + optional sep +
    # optional leading 0 + "2" + optional sep + optional 0 + "1", e.g. ex0201.
    ex21 = re.compile(r"ex[-_]?0?2[-_.]?0?1")
    for it in items:
        name = str(it.get("name", "")).lower()
        if name.endswith((".htm", ".html")) and ex21.search(name):
            return f"{base}/{it['name']}"
    raise LookupError(f"no EX-2.1 document found in accession {accession} (cik {cik})")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def _fetch_one(deal: Deal, out_dir: Path, user_agent: str) -> dict | None:
    """Fetch one deal; return its manifest row, or None if it's a TODO/failure."""
    if deal.ex21_url is None and deal.accession is None:
        _LOG.warning("SKIP %s — %s", deal.deal_id, deal.note or "no source")
        return None

    url = deal.ex21_url
    if url is None:
        _LOG.info("resolve %s — EX-2.1 from accession %s", deal.deal_id, deal.accession)
        url = _resolve_ex21_url(deal.cik, deal.accession or "", user_agent)

    _LOG.info("fetch  %s <- %s", deal.deal_id, url)
    raw = _get(url, user_agent)
    text = _html_to_text(raw)

    raw_path = out_dir / "raw" / f"{deal.deal_id}.htm"
    text_path = out_dir / f"{deal.deal_id}.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    text_path.write_text(text, encoding="utf-8")

    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    _LOG.info("  ok %s — %d chars text (sha256 %s…)", deal.deal_id, len(text), text_sha[:12])
    return {
        "deal_id": deal.deal_id,
        "label": deal.label,
        "set": deal.set_,
        "cik": deal.cik,
        "accession": deal.accession,
        "source_url": url,
        "raw_path": str(raw_path.relative_to(out_dir.parent.parent)) if out_dir.is_absolute() else str(raw_path),
        "text_path": str(text_path),
        "text_sha256": text_sha,
        "text_len": len(text),
        "note": deal.note,
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Fetch Calibration-17 EX-2.1s for §6 annotation.")
    ap.add_argument("--out", default="data/edgar", help="Output directory (default: data/edgar).")
    ap.add_argument("--only", default=None, help="Fetch a single deal_id.")
    ap.add_argument("--list", action="store_true", help="Print the fetch plan and exit (no network).")
    args = ap.parse_args(argv)

    deals = DEALS
    if args.only:
        deals = tuple(d for d in DEALS if d.deal_id == args.only)
        if not deals:
            print(f"unknown deal_id {args.only!r}. Known: {[d.deal_id for d in DEALS]}", file=sys.stderr)
            return 2

    if args.list:
        print(f"{'deal_id':<26} {'set':<17} {'source'}")
        for d in deals:
            src = d.ex21_url or (f"resolve@{d.accession}" if d.accession else "TODO — no source")
            print(f"{d.deal_id:<26} {d.set_:<17} {src}")
        ready = sum(1 for d in deals if d.ex21_url or d.accession)
        print(f"\n{ready}/{len(deals)} deals fetchable; {len(deals) - ready} are operator TODOs.")
        return 0

    ua = os.environ.get("SEC_EDGAR_USER_AGENT")
    if not ua:
        print("SEC_EDGAR_USER_AGENT not set — SEC will 403 every request.", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    failures: list[str] = []
    for deal in deals:
        try:
            row = _fetch_one(deal, out_dir, ua)
            if row is not None:
                rows.append(row)
        except (urllib.error.URLError, LookupError, OSError) as exc:
            _LOG.error("FAIL %s — %s", deal.deal_id, exc)
            failures.append(f"{deal.deal_id}: {exc}")

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"deals": rows}, indent=2) + "\n", encoding="utf-8")
    _LOG.info("wrote %d deals to %s", len(rows), manifest_path)

    todos = [d.deal_id for d in deals if not (d.ex21_url or d.accession)]
    if todos:
        _LOG.warning("operator TODOs (no source yet): %s", ", ".join(todos))
    if failures:
        print("\nFAILURES:", file=sys.stderr)
        for f in failures:
            print(f"  ! {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
