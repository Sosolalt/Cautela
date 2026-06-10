# syntax=docker/dockerfile:1
#
# Multi-stage build for the Cautela Next.js 14 frontend, targeting Cloud Run.
#
# IMPORTANT — BUILD CONTEXT IS THE MONOREPO ROOT, NOT ma_gatekeeper/frontend.
# The frontend's tailwind.config.ts imports design tokens from
# `../../design/tokens` (resolves to <repo-root>/design/tokens.ts, a sibling of
# ma_gatekeeper/). That path escapes the frontend directory, so a build context
# rooted at frontend/ cannot see design/ and `next build` fails with
# "Cannot find module '../../design/tokens'". Building from the repo root keeps
# design/ as the single source of truth (design/ is owned by another track and
# must not be edited or duplicated). All COPY paths below are therefore relative
# to the repo root. Deploy with the context set to the repo root and this
# Dockerfile selected explicitly (see cautela-frontend deploy command /
# cloudbuild.yaml in this directory).
#
# CRITICAL — NEXT_PUBLIC_* are inlined at BUILD time:
# Next.js bakes NEXT_PUBLIC_* env vars into the browser bundle during
# `next build`. Cloud Run runtime `--set-env-vars` does NOT reach the client
# bundle. So every NEXT_PUBLIC_* value is taken as a build ARG and promoted to
# ENV *before* `next build` (the `builder` stage). Pass them via Cloud Build
# substitutions (cloudbuild.yaml) or `docker build --build-arg ...`.

# Pinned to ma_gatekeeper/frontend/.nvmrc (20.11.1); -slim keeps the image small.
ARG NODE_VERSION=20.11.1

# ---- deps: install from the lockfile -----------------------------------------
FROM node:${NODE_VERSION}-slim AS deps
WORKDIR /app
COPY ma_gatekeeper/frontend/package.json ma_gatekeeper/frontend/package-lock.json ./
RUN npm ci

# ---- builder: compile the app with NEXT_PUBLIC_* inlined ---------------------
FROM node:${NODE_VERSION}-slim AS builder
WORKDIR /app

# Build-time public config. Baked into the client bundle here; CANNOT be changed
# at Cloud Run runtime. Defaults are safe placeholders for `docker build` smoke
# tests; real values are supplied as --build-arg / Cloud Build substitutions.
ARG NEXT_PUBLIC_API_BASE="http://localhost:8080"
ARG NEXT_PUBLIC_DEMO_PASSCODE=""
ARG NEXT_PUBLIC_PHOENIX_URL=""
ARG NEXT_PUBLIC_PHOENIX_PROJECT=""
ARG NEXT_PUBLIC_PHOENIX_TRACE_URL=""

ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE} \
    NEXT_PUBLIC_DEMO_PASSCODE=${NEXT_PUBLIC_DEMO_PASSCODE} \
    NEXT_PUBLIC_PHOENIX_URL=${NEXT_PUBLIC_PHOENIX_URL} \
    NEXT_PUBLIC_PHOENIX_PROJECT=${NEXT_PUBLIC_PHOENIX_PROJECT} \
    NEXT_PUBLIC_PHOENIX_TRACE_URL=${NEXT_PUBLIC_PHOENIX_TRACE_URL} \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

COPY --from=deps /app/node_modules ./node_modules
# The frontend app lives at /app. Its tailwind.config.ts imports
# `../../design/tokens`, which from /app/tailwind.config.ts resolves to
# /design/tokens (two `..` from /app clamp at the filesystem root). So we place
# the sibling design/ token source at /design to mirror the on-disk monorepo
# layout (design/ is owned by another track and copied in verbatim, not edited).
COPY design/ /design/
COPY ma_gatekeeper/frontend/ ./
# Fail fast if the design tokens didn't make it into the context.
RUN test -f /design/tokens.ts || (echo "FATAL: /design/tokens.ts missing — build context must be the monorepo root" && exit 1)
RUN npm run build

# ---- runner: minimal standalone server ---------------------------------------
FROM node:${NODE_VERSION}-slim AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 \
    HOSTNAME=0.0.0.0

RUN groupadd --system --gid 1001 nodejs \
    && useradd --system --uid 1001 --gid nodejs nextjs

# Standalone output ships its own minimal node_modules + server.js.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
# public/ holds the pdfjs worker copied in by the prebuild step.
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 8080

# server.js is emitted by Next standalone output and respects PORT + HOSTNAME.
CMD ["node", "server.js"]
