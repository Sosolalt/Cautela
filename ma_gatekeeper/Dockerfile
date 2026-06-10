FROM python:3.12-slim

WORKDIR /app

# Most legal/data-room deps ship manylinux wheels and need NO system libs:
# - pymupdf, pdfplumber, pandas, numpy, matplotlib, pydantic, fastapi.
# So we install only ca-certificates for HTTPS. Slim base image stays slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Layer caching: install deps before copying app code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ agent/
COPY scripts/ scripts/
# thresholds.json (router cut-offs) is REQUIRED at runtime by
# Thresholds.from_json in the /review path — a missing file raises
# FileNotFoundError on every review. It is shipped in the image. Pair it
# with requirements.txt (always present) in the COPY so the legacy Cloud
# Build docker builder doesn't fail: Cloud Build does NOT use BuildKit, so
# a no-match glob as the SOLE source errors with "no source files were
# specified". With requirements.txt present the glob is safely optional.
COPY requirements.txt thresholds.json* ./

# citation_map.json (8.8K, hand-curated primary-source citations, Phase 10)
# is read at runtime by agent/citation_linker.py from /app/data/. It degrades
# gracefully if absent (lookups return None) but the demo then loses the
# citation-linkage feature, so ship it. data/ is otherwise excluded.
COPY data/citation_map.json data/citation_map.json

# Cloud Run injects $PORT at runtime; honor it via sh form.
# Use a non-root user (USER 1000) per Cloud Run security guidance.
RUN useradd -u 1000 -m runner
USER 1000

EXPOSE 8080
CMD ["sh", "-c", "uvicorn agent.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
