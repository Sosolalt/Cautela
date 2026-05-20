"""Generate the adversarial slice + run the leakage audit (plan §5.3).

For 5 MAUD-base contracts, prompt Gemini to inject one seeded violation
(narrow a MAE carve-out, swap "reasonable best efforts" for "commercially
reasonable efforts", add a holdco-only CoC trigger).

Then run a discriminator (Gemini 3 Flash with a "real vs synthetic" prompt)
on 200-token windows to compute AUC. Ship if AUC < 0.6; caveat if
0.6 <= AUC < 0.7; **redo** if AUC >= 0.7.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

_LOG = logging.getLogger(__name__)

PERTURBATIONS = [
    {
        "name": "narrow_mac_carveout_pandemic",
        "instruction": (
            "In the MAE/MAC definition, REMOVE the carve-out that excepts "
            "pandemic / epidemic / public-health emergencies from material "
            "adverse effect. Preserve all other carve-outs verbatim."
        ),
    },
    {
        "name": "rbe_to_cre_swap",
        "instruction": (
            'In every operative covenant, replace "reasonable best efforts" '
            'with "commercially reasonable efforts". Preserve numbering and '
            "definitions exactly."
        ),
    },
    {
        "name": "holdco_only_coc",
        "instruction": (
            "Modify the change-of-control definition so it triggers ONLY on "
            "direct shareholder changes (not indirect / holdco / parent). "
            "This is the trap that misses real deals."
        ),
    },
    {
        "name": "remove_anti_assignment_consent",
        "instruction": (
            "Remove the consent requirement from the anti-assignment clause "
            "while keeping the surface phrase 'change of control' intact "
            "in the definitions. The buyer would falsely believe consent "
            "is needed."
        ),
    },
    {
        "name": "weaken_no_shop_fiduciary_out",
        "instruction": (
            "Broaden the fiduciary-out exception to the no-shop covenant "
            "such that the seller could shop the deal under less stringent "
            "conditions than the original."
        ),
    },
]


def perturb_contract(text: str, perturbation: dict) -> str:
    """Use Gemini 3 Pro to apply a single perturbation."""
    # Real impl uses google-genai with a careful system prompt; pseudocode
    # for the scaffold.
    return text


def leakage_audit(
    real_texts: list[str],
    perturbed_texts: list[str],
    *,
    window_tokens: int = 200,
    n_samples: int = 200,
    seed: int = 42,
) -> float:
    """Discriminator AUC: can a held-out LLM tell perturbed from real?

    Returns AUC. < 0.6 = clean; 0.6-0.7 = caveat; >= 0.7 = redo.
    """
    rng = np.random.default_rng(seed)
    # Sample windows from each, score "synthetic-ness" via discriminator
    # LLM, then compute AUC against the (real=0, synthetic=1) label.
    # Pseudocode shape; full implementation hooked up D13.
    return 0.5  # placeholder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-dir", default="data/maud", help="MAUD base contracts")
    parser.add_argument("--out-dir", default="data/perturbed")
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    real_texts: list[str] = []
    perturbed_texts: list[str] = []

    bases = sorted(in_dir.glob("*.txt"))[: args.n]
    for base_path, perturbation in zip(bases, PERTURBATIONS):
        original = base_path.read_text()
        perturbed = perturb_contract(original, perturbation)
        out = out_dir / f"{base_path.stem}__{perturbation['name']}.txt"
        out.write_text(perturbed)
        meta = out_dir / f"{base_path.stem}__{perturbation['name']}.meta.json"
        meta.write_text(json.dumps({
            "base": str(base_path),
            "perturbation": perturbation,
            "ground_truth": "block",  # all 5 perturbations create a Block-tier risk
        }, indent=2))
        real_texts.append(original)
        perturbed_texts.append(perturbed)

    auc = leakage_audit(real_texts, perturbed_texts)
    _LOG.info("Leakage AUC = %.3f", auc)
    if auc >= 0.7:
        raise SystemExit(
            f"FAIL: leakage AUC = {auc:.3f} >= 0.7. Discard and re-do "
            f"perturbations with subtler edits (plan §5.3 v3 bar)."
        )
    elif auc >= 0.6:
        _LOG.warning("CAVEAT: leakage AUC = %.3f in [0.6, 0.7). README must note.", auc)
    else:
        _LOG.info("CLEAN: leakage AUC = %.3f < 0.6, ship without caveat.", auc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
