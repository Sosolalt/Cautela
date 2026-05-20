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
# thresholds.json is bind-mounted via Cloud Run config (or shipped with
# the image once D9 calibration is done). Glob keeps build working
# either way; BuildKit handles no-match gracefully.
COPY thresholds.json* ./

# Cloud Run injects $PORT at runtime; honor it via sh form.
# Use a non-root user (USER 1000) per Cloud Run security guidance.
RUN useradd -u 1000 -m runner
USER 1000

EXPOSE 8080
CMD ["sh", "-c", "uvicorn agent.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
