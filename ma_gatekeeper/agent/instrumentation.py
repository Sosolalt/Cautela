"""OpenInference / Phoenix tracing setup.

Implements Hook 1 of plan §6.1. Verified against arize-phoenix-otel docs:
  - `phoenix.otel.register(project_name=, auto_instrument=True,
    set_global_tracer_provider=False)` — kwargs are exact.
  - `auto_instrument=True` discovers any installed
    `openinference-instrumentation-*` package and instruments it.

Important caveat (Arize-reviewer flagged): `set_global_tracer_provider=False`
does NOT fully isolate ADK's traces from Cloud Run's default tracer
provider — ADK uses the global provider too, so spans from ADK still
land on whichever provider was registered globally. The kwarg DOES
prevent us from accidentally replacing a global provider that another
library already set up. In production we accept the global registration
(Phoenix becomes THE provider) and verify in the dashboard that ADK
spans show up. Set the env `PHOENIX_NO_ISOLATE=1` to skip the kwarg.

Reference: https://arize.com/docs/phoenix/tracing/how-to-tracing/setup-tracing/setup-tracing-python
"""
from __future__ import annotations

import os


def init_tracing(project_name: str = "ma-gatekeeper") -> None:
    """Initialize Phoenix tracing.

    Requires (Cloud Run injects via Secret Manager):
      PHOENIX_COLLECTOR_ENDPOINT  e.g. https://phoenix.example.com
      PHOENIX_API_KEY             px_live_...
    """
    if not os.environ.get("PHOENIX_API_KEY"):
        # In dev without Phoenix, no-op so tests still run.
        return

    from phoenix.otel import register
    isolate = os.environ.get("PHOENIX_NO_ISOLATE") != "1"
    register(
        project_name=project_name,
        auto_instrument=True,
        set_global_tracer_provider=not isolate,
    )
