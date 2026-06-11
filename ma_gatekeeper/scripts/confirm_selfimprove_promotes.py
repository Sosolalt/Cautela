#!/usr/bin/env python3
"""Confirm the Reflector self-improve loop reaches a REAL AUTO-PROMOTED — BEFORE recording.

Runs the ACTUAL promotion gate against the deployed Phoenix datasets and prints
whether `should_promote` fires with margin. Because the experiment is
deterministic (fixed prompt tags `production`/`candidate` + bootstrap seed=42),
a PASS here means the recorded run will reproduce AUTO-PROMOTED *identically* —
that is the whole point of confirming before you spend a take.

This script does NOT change any logic; it just exercises
`reflector._run_experiment_pairwise` + `reflector.should_promote`, so it tests
whatever per-example metric is currently in-tree. Run it BEFORE the metric
re-point (expect FAIL — faithfulness saturates) and AFTER (expect PASS).

PREREQS (local dev box):
  - GCP creds for Vertex (same as the eval scripts): `source .venv/bin/activate`.
  - Phoenix reachable. The direct Cloud Run URL is unreachable from the dev box,
    so run the bridge and point the client at it:
        python /tmp/phx_bridge.py &                 # 127.0.0.1:9971 -> {frontend}/phoenix-api/*
        export PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:9971
  - The `cross_reference` prompt seeded (production=weak / candidate=strong) and
    the datasets present — already true on deployed Phoenix.

COST: runs the pairwise experiment once over regressions-v1 (20) + fold-5 (15),
both prompt tags = ~70 agent calls. Eval runs on Flash → ~€0.3-0.5. `--full`
also runs the entire LoopAgent (≈2x cost) and asserts the streamed
`auto_promoted` event the UI shows.

USAGE (from the ma_gatekeeper/ dir):
    python -m scripts.confirm_selfimprove_promotes            # gate check
    python -m scripts.confirm_selfimprove_promotes --full     # + full-loop event check

Exit 0 = promotes with margin (safe to record). Exit 1 = does NOT (don't record yet).
"""
from __future__ import annotations

import argparse
import asyncio
import os

# CI lower bound must clear this (not just barely > 0) to be "comfortably" promoting.
MARGIN = float(os.environ.get("CONFIRM_CI_LB_MARGIN", "0.02"))


def _client():
    from phoenix.client import Client

    return Client()


def check_gate() -> bool:
    import numpy as np  # noqa: F401  (kept explicit so a missing dep fails loudly here)

    from agent import reflector

    ep = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "(unset)")
    print(f"→ Phoenix endpoint: {ep}")
    client = _client()

    print("→ Pairwise experiment on regressions-v1 (production vs candidate)…")
    reg_cand, reg_prod = reflector._run_experiment_pairwise(
        client,
        dataset_name="regressions-v1",
        prompt_name="cross_reference",
        tags=("production", "candidate"),
    )
    print("→ Pairwise experiment on the frozen fold-5…")
    f5_cand, f5_prod = reflector._run_experiment_pairwise(
        client,
        dataset_name=reflector._FROZEN_HELD_OUT,
        prompt_name="cross_reference",
        tags=("production", "candidate"),
    )

    n_reg = min(len(reg_cand), len(reg_prod))
    if n_reg == 0:
        print(
            "✗ FAIL: regression experiment returned 0 aligned examples — "
            "seed/dataset/prompt-tag problem (or Phoenix unreachable). Cannot promote."
        )
        return False

    reg_cand, reg_prod = reg_cand[:n_reg], reg_prod[:n_reg]
    reg_deltas = reg_cand - reg_prod
    n_f5 = min(len(f5_cand), len(f5_prod))
    f5_cand, f5_prod = f5_cand[:n_f5], f5_prod[:n_f5]

    promote, diag = reflector.should_promote(
        regression_deltas=reg_deltas,
        fold5_candidate_scores=f5_cand,
        fold5_production_scores=f5_prod,
    )

    ci_lb = float(diag["regression_ci_lb"])
    print("\n── GATE DIAGNOSTICS ────────────────────────────────")
    print(f"  regression candidate mean  : {float(reg_cand.mean()):.4f}")
    print(f"  regression production mean : {float(reg_prod.mean()):.4f}")
    print(f"  regression mean delta      : {float(reg_deltas.mean()):+.4f}  (n={n_reg})")
    print(f"  regression CI lower bound  : {ci_lb:+.4f}   (must be > {MARGIN})")
    print(f"  fold-5 candidate mean      : {float(diag['fold5_candidate_mean']):.4f}")
    print(f"  fold-5 production mean     : {float(diag['fold5_production_mean']):.4f}")
    print(f"  fold-5 non-regression ok   : {bool(diag['fold5_non_regression_ok'] > 0.5)}")
    print(f"  → should_promote           : {promote}")
    print("────────────────────────────────────────────────────")

    if promote and ci_lb > MARGIN:
        print(
            f"\n✓ PASS — gate fires with margin (CI_LB {ci_lb:+.4f} > {MARGIN}). "
            "Deterministic (seed=42) → the recorded run will AUTO-PROMOTE."
        )
        return True
    if promote:
        print(
            f"\n⚠ BORDERLINE — promotes but CI_LB {ci_lb:+.4f} only just clears 0 "
            f"(< margin {MARGIN}). Strengthen the metric/gap BEFORE recording."
        )
        return False
    print(
        f"\n✗ FAIL — gate does NOT promote (CI_LB {ci_lb:+.4f}). "
        "Either the metric re-point isn't applied yet, or the candidate isn't "
        "measurably better on the scored axis."
    )
    return False


async def check_full_loop() -> bool:
    from agent.reflector_loop import run_reflector_loop

    lookback = int(os.environ.get("REFLECTOR_LOOP_LOOKBACK_HOURS", "720"))
    print(f"\n→ Running the FULL LoopAgent (lookback={lookback}h): list_traces → experiment → gate → promote…")
    kinds: list[str] = []
    async for evt in run_reflector_loop(lookback_hours=lookback):
        kind = getattr(evt, "kind", None)
        if kind is None and isinstance(evt, dict):
            kind = evt.get("kind")
        if kind:
            kinds.append(kind)
            print(f"    • {kind}")
    promoted = "auto_promoted" in kinds
    if promoted:
        print("\n✓ PASS — the loop streamed `auto_promoted` (the badge the UI shows).")
    else:
        print(f"\n✗ FAIL — loop ended WITHOUT `auto_promoted`. Saw: {', '.join(kinds) or '(no events)'}")
    return promoted


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--full",
        action="store_true",
        help="Also run the entire LoopAgent and assert the streamed auto_promoted event (≈2x cost).",
    )
    args = ap.parse_args()

    print("⚠ Makes real Vertex + Phoenix calls (~€0.3-0.5; --full ≈2x). Ctrl-C to abort.\n")
    gate_ok = check_gate()
    if args.full:
        loop_ok = asyncio.run(check_full_loop())
        gate_ok = gate_ok and loop_ok

    print("\n" + ("=== READY TO RECORD ✅ ===" if gate_ok else "=== NOT READY — do not record yet ❌ ==="))
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
