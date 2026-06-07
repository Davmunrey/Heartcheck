# Axis — Brand & Identity

**Axis** is the product name for the clinical ECG copilot (formerly "HeartScan").
Positioning: a clinical decision-support copilot — probabilistic, human-in-the-loop,
**non-diagnostic**. Editorial voice: stark, flat, square, thick borders, big type.

> Naming rule: **"Axis"** is the user-facing product name (UI copy, docs, disclaimers,
> page titles). Internal code identifiers are intentionally left unchanged —
> the Python package stays `heartscan_ml`, the env prefix stays `HEARTSCAN_`,
> and the npm workspace stays `@heartscan/web`. Renaming those is a separate,
> risky refactor with no functional benefit; the brand lives in the strings users see.

## Core idea

- **Blue = product / UI** (the copilot).
- **Red = signal** (the patient's ECG trace · the scalpel).

## Design tokens

Canonical source: [`apps/web/app/globals.css`](../apps/web/app/globals.css)
(`:root` + Tailwind v4 `@theme`). Reference brand book assets live outside the
repo under `~/Downloads/ECGs Copilot/` (Brand Book, axis.css, mockups).

| Token | Value | Use |
|-------|-------|-----|
| `--paper` | `#F4F6FA` | app / marketing background |
| `--surface` | `#FFFFFF` | cards, panels |
| `--ink` | `#0B1A2B` | primary text / structure (near-black navy) |
| `--ink-2` / `--ink-3` | `#46586E` / `#8493A6` | secondary / muted text |
| `--brand` | `#1B5FD9` | product blue (primary actions, UI) |
| `--brand-strong` / `--brand-bright` | `#0E3E9B` / `#3D7BFF` | hover / accent |
| `--signal` | `#E5202A` | ECG red (the trace, alerts) |
| `--scope` | `#060B14` | dark ECG-viewer / hero canvas |
| `--ok` / `--warn` / `--crit` | `#138A5E` / `#B97D00` / `#D2363B` | API `green`/`yellow`/`red` status |

Tailwind utilities are generated for these via `@theme` (e.g. `bg-brand`,
`text-ink`, `border-line`, `text-signal`).

### Type

| Role | Family |
|------|--------|
| Display | Archivo Black |
| Headings | Archivo (600–900) |
| Body | Hanken Grotesk |
| Mono / data | Geist Mono |

### Geometry

Square by default (`--r: 0`); pills only for avatars/status dots. Standard
interactive border weight `--bw: 2px`.

## Applying the brand

- **Web** ([`apps/web`](../apps/web)): tokens in `globals.css`; product name "Axis"
  across landing, copilot, pricing, security, FAQ, dashboard and `layout.tsx`
  metadata (title/OpenGraph/Twitter + `themeColor`).
- **API** ([`apps/ml-api`](../apps/ml-api)): user-facing disclaimers and `/api/v1/meta`
  copy say "Axis".
- **Docs**: prose refers to the product as "Axis".

When adding UI, use the tokens above (never hard-code hex); keep the square,
high-contrast, big-type editorial style.
