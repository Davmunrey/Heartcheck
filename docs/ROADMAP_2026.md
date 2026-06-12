# Axis — Audit & Roadmap 2026/27

> Snapshot del **2026-06-12**. Auditoría del estado real + MVP + roadmap anual.
> Indexado en [`MASTER_DOCS.md`](MASTER_DOCS.md).

## Auditoría — estado por área

| Área | Estado | Notas |
|------|--------|-------|
| Web (Next.js) | 🟢 Sólido | 12 páginas, `next build` ✓ 18 routes, rebrand ECGs Copilot 3, **una sola URL** |
| Auth (Clerk) | 🟢 Funciona E2E | login → analyze → resultado verificado; **org-opcional** (`HEARTSCAN_REQUIRE_ORGANIZATION`) |
| ML · 12-lead signal | 🟡 Real, medio | `/api/v1/analyze/signal`, `ecg_27class`, **AUROC 0.88**, 28 clases; HYP débil |
| ML · foto | 🔴 Heurístico | `checkpoint_loaded:false`, modelo foto sin entrenar — es heurística, no CNN |
| Billing (Stripe) | 🟡 Implementado, dormido | checkout/portal/webhook + Clerk webhook codificados; faltan claves + Supabase service-role |
| Persistencia / audit trail | 🟡 Tabla lista, sin escribir→**en curso** | `analyses` existe (migración + RLS); el dashboard la lee; falta el write (gap A, en progreso) |
| Tests | 🟡 Desbalanceado | ml-api 15 archivos; web 2 |
| Mobile (Flutter) | 🟡 Scaffold | 20 archivos Dart; sin E2E verificado ni rebrand |
| Infra/deploy | 🟡 Deploy-ready, sin desplegar | `next.config` rewrite `/ml-api` same-origin, `vercel.json`, Dockerfiles, migraciones Supabase |
| Seguridad/compliance | 🟡 Pre-clínico | OWASP endurecido (CSP/HSTS/headers); sin DPA/BAA/SOC2; hard-case storage off |

**El punto exacto:** producto funcional E2E en local con marca pulida y una URL.
No desplegable como negocio aún por: (1) persistencia/audit trail, (2) el valor
real es la **señal 12-lead (AUROC 0.88)**, no la foto (heurística) — y el
marketing vende "sube una foto", (3) sin desplegar. Billing listo pero apagado.

## MVP — "copiloto de ECG 12-lead para equipos clínicos (beta)"

Lidera con la **señal** (modelo creíble); la foto = *triage experimental*.

**Ya funciona:** sign-up → subir señal/foto → lectura calibrada 27-clases +
estado green/yellow/red → PDF → org-opcional → cuotas día (`usage_service`).

**Gap para beta desplegable (prioridad):**
1. 🔴 Persistir análisis (`analyses` write + historial dashboard) — *gap A, en curso*.
2. 🔴 Desplegar la URL única (Vercel + ml-api privado + Supabase) — *gap C*.
3. 🟡 UX señal-first + honestidad foto-vs-señal.
4. 🟡 Gate de trial (ya hay `canAnalyze`); Stripe se enciende con claves.
5. 🟡 Consentimiento + retención de imagen opt-in.

→ **~1 semana de trabajo enfocado** para beta desplegable.

## Roadmap anual (Q3 2026 → Q2 2027)

### Q3 2026 — MVP beta en producción
- Persistencia + audit trail; historial real en dashboard.
- Deploy single-URL (Vercel + ml-api privado + Supabase), dominio + HTTPS + secretos.
- UX señal-first; consentimiento/retención.
- Encender Stripe (trial→Pro); 1–3 **design partners** clínicos (beta cerrada).
- **Salida:** 3 equipos analizando casos reales/semana.

### Q4 2026 — Modelo grado-clínico + confianza
- Pretrain CODE-15 (345k) / MIMIC (800k) → fine-tune; objetivo **AUROC ≥0.92** macro; subir HYP/MI.
- Harness de validación externa + abstención conformal + calibración por clase.
- Mobile beta (rebrand + E2E).
- **Salida:** AUROC validado en dataset externo + model card publicada.

### Q1 2027 — Enterprise & compliance
- DPA/BAA, camino SOC 2, RBAC fino, hard-case storage con consentimiento (AES-GCM).
- Integración EHR/FHIR (export estructurado); API para integradores.
- Estrategia regulatoria SaMD (CE/FDA) — *decision-support*, no diagnóstico.
- **Salida:** primer contrato de pago + revisión legal/seguridad.

### Q2 2027 — Escala
- Hardening multi-tenant; billing por uso; panel admin/observabilidad.
- Modelo v2 (multi-fuente, 500Hz) + pilotos → conversión a pago.
- **Salida:** MRR inicial + pilotos en producción.

## Riesgos / supuestos
- **Modelo foto** no es clínicamente creíble: no posicionar como diagnóstico.
- **Compliance** es el cuello de botella para uso clínico real (no técnico).
- Persistencia de PHI exige consentimiento + cifrado antes de guardar imágenes.
