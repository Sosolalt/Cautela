"""Populate Phoenix's TRACE surface from local, bypassing the Cloud Run backend.

Why this exists: the demo's cmd+click "money moment" reveals a review's full
Phoenix span tree (parser -> classifier fan-out -> evaluators -> the three
annotations). As of 2026-06-10 that surface is EMPTY because (a) the deployed
`/review-by-deal` can't fetch any demo deal (it grabs the *latest* 8-K, but the
mergers are 2022-24), and (b) a `/review` that did run on Cloud Run emitted 0
spans. This script sidesteps BOTH: it turns on Phoenix tracing locally and runs
the real review pipeline (`agent.server._stream_findings`) on a LOCAL contract
file via your Vertex ADC, so genuine agent spans export straight to phoenix-prod.

It does NOT call or modify the `ma-gatekeeper` Cloud Run service. It touches:
your local filesystem, Vertex (Gemini quota), and phoenix-prod (span export).
Spans are namespaced to project `ma-gatekeeper-local` by default so they don't
muddy the backend owner's debugging of the *deployed* service's own export.

Env (same Vertex ADC as the `--live` eval runs; defaults filled for phoenix-prod):
  GOOGLE_GENAI_USE_VERTEXAI=TRUE GOOGLE_CLOUD_PROJECT=... GOOGLE_CLOUD_LOCATION=global
  GEMINI_MODEL=gemini-3.1-pro-preview
  PHOENIX_COLLECTOR_ENDPOINT (default: phoenix-prod) PHOENIX_API_KEY (any non-empty)

Usage:
  python -m scripts.trace_review_local --contract /tmp/test_contract.txt --mime text/html
  python -m scripts.trace_review_local --contract data/edgar/raw/exxon_pioneer.htm
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

DEFAULT_PHOENIX = "https://phoenix-prod-eqxulvtmha-uc.a.run.app"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", required=True, help="Local contract file (.htm/.txt/.pdf).")
    ap.add_argument("--mime", default=None,
                    help="Override mime. Default: application/pdf for .pdf, else text/html.")
    ap.add_argument("--project", default="ma-gatekeeper-local",
                    help="Phoenix project name to namespace these spans under.")
    ap.add_argument("--max-bytes", type=int, default=120_000,
                    help="Truncate large contracts to bound Vertex cost (0 = no truncation).")
    args = ap.parse_args(argv)

    # Tracing config MUST be set before importing the agent (register reads env).
    base = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", DEFAULT_PHOENIX).rstrip("/")
    os.environ.setdefault("PHOENIX_API_KEY", "local-trace")  # phoenix-prod is no-auth; any non-empty value is fine

    # CRITICAL: register() defaults to the gRPC exporter on :4317, which a
    # Cloud-Run-hosted Phoenix CANNOT receive (Cloud Run serves only HTTPS/443).
    # That gRPC:4317 default is exactly why spans never landed (local AND the
    # deployed backend). Force the HTTP/OTLP exporter to the `/v1/traces`
    # endpoint on 443 instead. The same fix is what the backend's
    # `agent/instrumentation.py` needs for its spans to reach phoenix-prod.
    from phoenix.otel import register

    register(
        project_name=args.project,
        endpoint=f"{base}/v1/traces",  # HTTP OTLP on 443, not gRPC:4317
        auto_instrument=True,
    )
    print(f"[tracing] project={args.project} -> {base}/v1/traces (HTTP OTLP)")

    path = Path(args.contract)
    data = path.read_bytes()
    mime = args.mime or ("application/pdf" if path.suffix.lower() == ".pdf" else "text/html")
    # Only truncate text-like inputs: slicing a PDF's raw bytes corrupts its
    # structure (Gemini rejects "document has no pages"). For PDFs, pass a
    # smaller file instead of relying on --max-bytes.
    if args.max_bytes and len(data) > args.max_bytes:
        if mime.startswith("text/"):
            print(f"[input] truncating {len(data)} -> {args.max_bytes} bytes to bound cost")
            data = data[: args.max_bytes]
        else:
            print(f"[input] {len(data)} bytes > max-bytes but mime={mime} is binary; "
                  "NOT truncating (would corrupt). Pass a smaller file if cost matters.")
    print(f"[input] {path.name} ({len(data)} bytes, mime={mime})")

    # Contained runtime override (local-only; does NOT edit the committed
    # agent code): the classifier fan-out in agent/agents.py hardcodes
    # model="gemini-3-flash", which 404s in this project/region. Wrap
    # build_root_agent to rewrite any such sub-agent to GEMINI_MODEL so the
    # pipeline completes and emits a FULL trace. (The real backend fix is a
    # one-line change at agents.py:100 — reported separately.)
    valid_model = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")
    import agent.agents as _agents
    _orig_build = _agents.build_root_agent

    def _patched_build():
        root = _orig_build()

        def _fix(node):
            m = getattr(node, "model", None)
            if isinstance(m, str) and m == "gemini-3-flash":
                try:
                    node.model = valid_model
                except Exception as e:  # pydantic-frozen etc.
                    print(f"[override] could not rewrite model on {getattr(node,'name','?')}: {e}")
            for sub in getattr(node, "sub_agents", None) or []:
                _fix(sub)

        _fix(root)
        return root

    _agents.build_root_agent = _patched_build  # _stream_findings imports this lazily at call time

    from agent.server import _stream_findings

    async def run() -> int:
        events = 0
        findings = 0
        async for raw in _stream_findings(data, mime):
            events += 1
            line = raw.decode("utf-8", "replace").strip()
            # Surface the structurally interesting events; skip verbose agent_output text.
            for key in ('"event": "start"', '"event": "error"', '"event": "done"',
                        '"event": "finding"', '"lane"'):
                if key in line:
                    if '"event": "finding"' in line or '"lane"' in line:
                        findings += 1
                    print(line[:240])
                    break
        print(f"[stream] consumed {events} events, ~{findings} finding/lane events")
        return events

    n = asyncio.run(run())

    # Force-flush the span processor so spans actually leave the process before exit.
    flushed = False
    try:
        from opentelemetry import trace as _t
        tp = _t.get_tracer_provider()
        if hasattr(tp, "force_flush"):
            tp.force_flush()
            flushed = True
        if hasattr(tp, "shutdown"):
            tp.shutdown()
    except Exception as e:  # pragma: no cover
        print(f"[flush] warning: {e}")
    print(f"[flush] span flush {'OK' if flushed else 'SKIPPED (no provider)'}")
    print(f"[done] {n} events. Check phoenix-prod for project '{args.project}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
