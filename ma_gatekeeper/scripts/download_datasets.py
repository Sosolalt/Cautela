"""Download CUAD + MAUD; pull a small EDGAR sample for the held-out slice.

Run once at the start of D5 to seed the annotation pipeline.

  python -m scripts.download_datasets --out data/

Outputs:
  data/cuad/    - SQuAD-format JSON + 510 PDFs from theatticusproject/cuad
  data/maud/    - 152 merger agreements from theatticusproject/maud
  data/edgar/   - 10 hand-picked recent 8-K Ex 2.1 filings for held-out eval
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

_LOG = logging.getLogger(__name__)


def download_cuad(out: Path) -> None:
    """Pull CUAD from HuggingFace (`theatticusproject/cuad-qa`).

    Span-level CoC + Anti-Assignment labels. Plan §5.1.
    """
    from datasets import load_dataset  # type: ignore
    out.mkdir(parents=True, exist_ok=True)
    ds = load_dataset("theatticusproject/cuad-qa", trust_remote_code=True)
    ds.save_to_disk(str(out))
    _LOG.info("CUAD saved to %s", out)


def download_maud(out: Path) -> None:
    """Pull MAUD (`theatticusproject/maud` if mirrored, else Zenodo).

    92 ABA deal-point MCQ over 152 merger agreements. Plan §5.1.
    """
    out.mkdir(parents=True, exist_ok=True)
    try:
        from datasets import load_dataset  # type: ignore
        ds = load_dataset("theatticusproject/maud", trust_remote_code=True)
        ds.save_to_disk(str(out))
        _LOG.info("MAUD saved to %s via HuggingFace", out)
        return
    except Exception as exc:
        _LOG.warning("HF load failed (%s); falling back to Zenodo zip", exc)
    # Zenodo fallback - download URL is https://zenodo.org/records/7500064
    import urllib.request
    url = "https://zenodo.org/records/7500064/files/maud_v1.zip"
    urllib.request.urlretrieve(url, out / "maud_v1.zip")
    _LOG.info("MAUD zip saved to %s", out / "maud_v1.zip")


def sample_edgar(out: Path, *, n: int = 10) -> None:
    """Pull a small sample of recent 8-K Ex 2.1 filings via EdgarTools.

    Plan §5.5 - this seeds the EDGAR held-out evaluation slice. The 5
    *demo* deals are a separate curated set (allow-list in server.py).
    """
    from edgar import set_identity, get_filings  # type: ignore
    # SEC requires a real contact email in the User-Agent. Read it from
    # SEC_EDGAR_USER_AGENT (same env var the server + verify_allow_list use)
    # so it's configurable without editing code.
    identity = os.environ.get("SEC_EDGAR_USER_AGENT", "hugo.majerczyk@proton.me")
    set_identity(identity)
    filings = get_filings(form="8-K", filing_date="2025-06-01:2026-04-30")
    out.mkdir(parents=True, exist_ok=True)
    saved = 0
    for f in filings:
        attachments = getattr(f, "attachments", None)
        if not attachments:
            continue
        ex2 = next((a for a in attachments if "2.1" in (getattr(a, "exhibit_number", "") or "")), None)
        if not ex2:
            continue
        target = out / f"{f.accession_no}_ex21.pdf"
        try:
            ex2.download(target)
            saved += 1
        except Exception as exc:
            _LOG.warning("Failed to download %s: %s", f.accession_no, exc)
        if saved >= n:
            break
    _LOG.info("Saved %d EDGAR Ex 2.1 filings to %s", saved, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/")
    parser.add_argument("--skip-cuad", action="store_true")
    parser.add_argument("--skip-maud", action="store_true")
    parser.add_argument("--skip-edgar", action="store_true")
    args = parser.parse_args()
    base = Path(args.out)
    if not args.skip_cuad:
        download_cuad(base / "cuad")
    if not args.skip_maud:
        download_maud(base / "maud")
    if not args.skip_edgar:
        sample_edgar(base / "edgar")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
