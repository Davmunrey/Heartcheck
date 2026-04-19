# ADR 005 — Split deployment: Next.js on Vercel, ML API on Fly.io

## Status

Accepted

## Context

The inference stack (PyTorch, OpenCV, large checkpoints) does not fit Vercel Functions limits.

## Decision

- **Vercel** hosts the Next.js App Router app (`apps/web`).
- **Fly.io** (or similar) hosts the FastAPI ML service (`apps/ml-api`), built from the Dockerfile.
- The browser never talks to Fly directly for HTML; Next.js server actions call the ML API using server-side secrets.

## Consequences

- Two URLs: app (Vercel) and API (Fly). CORS on the ML API must list the Vercel origin(s).
- Internal authentication uses `X-Internal-Token` plus Clerk JWT validation on the ML API.
