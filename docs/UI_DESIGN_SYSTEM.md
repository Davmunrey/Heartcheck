# Sistema visual de Axis

Axis tiene **una sola superficie web**: la app Next.js en [`apps/web`](../apps/web)
(landing pública + producto autenticado, todo bajo la misma URL). El ML API
([`apps/ml-api`](../apps/ml-api)) es un **servicio interno** sin cara visible —
su landing/consola heredada (`web_public/`) redirige a la app cuando
`HEARTSCAN_WEB_APP_URL` está configurado. Ya no hay "dos pieles".

## Fuente de verdad

| Qué | Dónde |
|-----|-------|
| Tokens + Tailwind v4 `@theme` | [`apps/web/app/globals.css`](../apps/web/app/globals.css) |
| Fuentes (next/font) | [`apps/web/app/layout.tsx`](../apps/web/app/layout.tsx) |
| Logo + header/footer | [`apps/web/app/(public)/_components/site-header.tsx`](../apps/web/app/(public)/_components/site-header.tsx) |
| Brand book de referencia | `~/Downloads/ECGs Copilot 3/` (`assets/axis.css`, Brand Book, mockups) |

`docs/BRAND.md` es la guía de marca; este documento es la implementación.

## Color

Editorial: claro, alto contraste, plano, **cuadrado** (`--r: 0`), bordes gruesos
(`--bw: 2px`). **Azul = producto/UI · Rojo = señal (la traza ECG).**

| Semántica | Token | Valor |
|-----------|-------|-------|
| Fondo papel | `--paper` / `--paper-2` | `#F4F6FA` / `#E9EDF4` |
| Superficie | `--surface` | `#FFFFFF` |
| Tinta | `--ink` / `--ink-2` / `--ink-3` | `#0B1A2B` / `#46586E` / `#8493A6` |
| Marca (azul) | `--brand` / `--brand-strong` / `--brand-bright` | `#1B5FD9` / `#0E3E9B` / `#3D7BFF` |
| Señal (rojo) | `--signal` / `--signal-700` | `#E5202A` / `#C20D17` |
| Estado OK/Warn/Crit | `--ok` / `--warn` / `--crit` | `#138A5E` / `#B97D00` / `#D2363B` |
| Lienzo oscuro (visor ECG/hero) | `--scope` / `--scope-2` | `#060B14` / `#0B121E` |

Se generan utilidades Tailwind por `@theme` (`bg-brand`, `text-ink`,
`border-line`, `text-signal`, `bg-scope`…). **Nunca** hardcodear hex; usar tokens.

## Tipografía

| Rol | Familia | Token / utilidad |
|-----|---------|------------------|
| Display (h1–h3) | **Archivo Black** | `--font-display` / `font-display` |
| Subtítulos (h4–h5) | Archivo (600–900) | `--font-head` / `font-head` |
| Cuerpo | Hanken Grotesk | `--font-sans` (body por defecto) |
| Mono / datos | Geist Mono | `--font-mono` / `font-mono` |

Los headings usan Archivo Black vía `@layer base` en `globals.css`.

## Reglas

1. **Voz**: misma terminología en toda la app (Analizar, Beta, FAQ, Resultado,
   Disclaimer).
2. **Disclaimers**: visibles en el flujo de análisis; nunca eliminarlos. Axis es
   apoyo a la decisión clínica, probabilístico, con revisión humana, **no
   diagnóstico**.
3. **Accesibilidad**: contraste AA mínimo; foco visible siempre (`--focus`);
   objetivos táctiles ≥44px.
4. **Animaciones**: respetar `prefers-reduced-motion: reduce`.
5. **Geometría**: cuadrado por defecto; pills sólo para avatares/puntos de estado.

## Clerk

El `appearance` de `ClerkProvider` (en `layout.tsx`) hereda la marca:
`colorPrimary #1B5FD9`, `borderRadius 0`, fuente Hanken Grotesk.
