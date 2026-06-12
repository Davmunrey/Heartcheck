# Axis — Plan completo a producto 100%

> Plan de ejecución detallado (2026-06-12). Complementa el alto nivel de
> [`ROADMAP_2026.md`](ROADMAP_2026.md). Indexado en [`MASTER_DOCS.md`](MASTER_DOCS.md).

## Qué significa "100%"

Axis al 100% = un **copiloto de ECG B2B desplegado, clínicamente creíble,
conforme y mantenible**, con design partners usándolo sobre casos reales y un
camino claro a clientes de pago. No es "todas las features imaginables" — es
**cada dimensión por encima del umbral de producto serio**.

## Scorecard del estado actual

| Dimensión | Hoy | Meta 100% |
|-----------|-----|-----------|
| UX/Diseño | 90% — web editorial, app pulida, una URL | mobile + a11y + i18n completos |
| Producto/flujos | 70% — analyze + historial + billing | detalle de análisis, PDF web, equipos |
| Modelo ML | 55% — señal AUROC 0.88; foto heurística | AUROC ≥0.92 + validación externa |
| Deploy/Ops | 60% — Supabase live, artefactos listos | en producción + observabilidad + backups |
| Ingeniería | 65% — ml-api 15 tests; web 2 | cobertura crítica + CI gates |
| Seguridad | 60% — OWASP hardening, RLS | pentest + RLS probada + rate-limit prod |
| Compliance | 25% — disclaimers, retención | DPA/BAA, SOC2, SaMD scoping |
| GTM/Negocio | 30% — pricing, landing | design partners + analítica + onboarding |

## Workstreams

### WS1 · Producto & UX (90% → 100%)
- **Detalle de análisis**: vista `/analyze/[id]` que lee `result_json` (findings, AUROC, traza). Hoy el historial sólo lista.
- **PDF desde la web**: botón "Informe PDF" en el resultado (el endpoint `/api/v1/reports/pdf` existe).
- **Estados completos**: loading/empty/error en todas las páginas (hecho en analyze/dashboard; faltan onboarding, settings).
- **Accesibilidad (WCAG AA)**: foco visible (token `--focus`), labels, contraste, navegación teclado, `aria-*`.
- **i18n**: ES/EN togglable (hay `education` i18n en API; falta en web).
- **Mobile (Flutter)**: rebrand Axis + E2E contra el API + paridad de flujo.
- *Aceptación:* a11y audit AA, mobile beta funcional, detalle+PDF en web.

### WS2 · Modelo ML clínico-grado (55% → 100%)
- **Pretrain a escala**: CODE-15 (345k) / MIMIC-IV-ECG (800k) → fine-tune; objetivo **macro-AUROC ≥0.92**, subir HYP/MI (hoy débiles).
- **Validación externa**: holdout de un dataset no visto; reportar por-clase.
- **Calibración + abstención conformal** por clase (parcialmente esbozado).
- **Foto**: o entrenar un modelo real de imagen (no heurístico) o mantenerlo explícito como triage (ya etiquetado).
- **Model card** actualizada + versionado de checkpoints.
- *Aceptación:* AUROC validado externo, model card publicada, abstención activa.

### WS3 · Deploy & Operaciones (60% → 100%)
- **Producción** (en curso): Render (ml-api, blueprint listo) + Vercel (web) + Supabase (migrado). Faltan: conectar Render + envs Vercel + dominio.
- **Observabilidad**: Sentry (hay hook) + métricas Prometheus (`/metrics`) → dashboard + alertas.
- **Backups + DR**: Supabase PITR, runbook de restore.
- **CI/CD**: deploy automático por rama, preview URLs, smoke tests post-deploy.
- *Aceptación:* prod estable bajo un dominio, alertas, backups probados.

### WS4 · Compliance & Regulatorio (25% → 100%) — *cuello de botella real*
- **Privacidad**: DPA + BAA, consentimiento de retención de imagen (toggle), borrado ("delete my data" — helper SQL existe).
- **SOC 2**: política, controles, evidencia (Vanta-style).
- **SaMD**: scoping CE/FDA como *decision-support* (no diagnóstico); intended use, gestión de riesgo ISO 14971, IEC 62304.
- **Auditoría**: cadena de audit_log inmutable (migración existe) verificada.
- *Aceptación:* DPA/BAA firmables, ruta SOC2 iniciada, intended-use documentado.

### WS5 · Ingeniería & Calidad (65% → 100%)
- **Tests web** (hoy 2 archivos): historial (`history.ts`), tenancy/billing fallback, server actions, webhooks. Objetivo cobertura crítica.
- **Tests ml-api** (15): mantener; añadir el camino Clerk org-opcional + persistencia.
- **E2E**: Playwright del flujo login→analyze→historial (resolver el flake de upload headless).
- **Tipos/contratos**: regenerar `@heartscan/api-client` desde el OpenAPI en CI.
- *Aceptación:* CI con gates (lint+types+tests+build) verde; E2E del happy path.

### WS6 · Seguridad (60% → 100%)
- **RLS probada**: correr `infra/supabase/tests/rls.sql` contra prod-like; verificar aislamiento por tenant.
- **Rate-limiting** en prod (slowapi configurado) + abuso/cuotas.
- **Secret hygiene**: rotación, no defaults en prod (guard existe), CSP ya endurecida.
- **Pentest** del flujo auth + análisis + webhooks (Svix verificado).
- *Aceptación:* pentest sin críticos, RLS verde, rate-limit activo.

### WS7 · Go-to-market (30% → 100%)
- **Design partners**: 3 equipos clínicos en beta cerrada; loop de feedback.
- **Analítica de producto**: PostHog/funnel (signup→primer análisis→retención).
- **Onboarding**: primer-uso guiado (subir ECG de ejemplo, ver informe).
- **Docs públicas**: API reference, "cuándo NO usarlo", seguridad/compliance one-pager.
- *Aceptación:* 3 partners activos, funnel medido, onboarding < 5 min al primer análisis.

## Timeline por trimestre

- **Q3 2026 — Beta en producción:** WS3 (deploy) + WS1 (detalle/PDF/estados) + WS5 (tests críticos) + WS7 (1–3 design partners). *Salida:* 3 equipos analizando casos reales/semana.
- **Q4 2026 — Confianza clínica:** WS2 (pretrain→AUROC≥0.92, validación externa) + WS1 (mobile beta, a11y, i18n) + WS6 (pentest, RLS). *Salida:* AUROC externo + mobile beta.
- **Q1 2027 — Enterprise & compliance:** WS4 (DPA/BAA, SOC2, SaMD scoping) + WS3 (observabilidad/DR) + integración EHR/FHIR. *Salida:* primer contrato de pago.
- **Q2 2027 — Escala:** WS7 (GTM, pilotos→pago) + WS2 (modelo v2) + hardening multi-tenant/billing por uso. *Salida:* MRR inicial.

## Próximas 2 semanas (sprint concreto)

1. **Cerrar el deploy** (WS3): Render connect + 4 secrets → Vercel envs + dominio → smoke test prod.
2. **Detalle de análisis + PDF en web** (WS1): `/analyze/[id]` + botón informe.
3. **Tests críticos** (WS5): `history.ts`, tenancy, billing fallback; E2E del happy path.
4. **Consentimiento de retención** (WS4): toggle "guardar imagen" + no guardar por defecto.
5. **Onboarding primer-uso** (WS7): ECG de ejemplo + CTA en dashboard vacío (parcial).

## Riesgos & dependencias
- **Compliance es el cuello de botella** para uso clínico real (no es técnico) — empezar SaMD/DPA pronto.
- **Modelo a escala** depende de descargar CODE-15/MIMIC (lento) + GPU.
- **Deploy** depende de cuentas/secretos del usuario (Render/Vercel).
- **No sobre-prometer la foto**: heurística; mantener el etiquetado honesto (hecho).
