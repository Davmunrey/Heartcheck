# ADR 003 — Monorepo layout (npm workspaces + Turborepo)

## Status

Accepted

## Context

The project ships a FastAPI ML API, a Next.js web app, Flutter mobile, and shared TS packages.

## Decision

- Use **npm workspaces** at the repository root (`apps/*`, `packages/*`).
- Use **Turborepo** (`turbo`) for orchestrating `build` / `dev` with filters (e.g. `@heartscan/web`).
- Python ML API and training code stay in `apps/ml-api` and top-level `ml/` respectively.

## Consequences

- Single `package-lock.json` at the root; Vercel project root is typically `apps/web` with install from repo root (`cd ../.. && npm install` in `apps/web/vercel.json`).
