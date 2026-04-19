# ADR 002 — Plan de facturación Stripe (no implementado todavía)

- Estado: **Aceptado como plan**, sin implementación.
- Fecha: 2026-04-18.
- Decisores: equipo HeartScan.

## Contexto

[`docs/SAAS_WEB_ROADMAP.md`](../SAAS_WEB_ROADMAP.md) contempla planes Free / Pro / Team y Stripe como pasarela de pago. El backend ya tiene cuotas por usuario ([`Settings.beta_daily_analysis_quota`](../../apps/ml-api/app/core/config.py)) y JWT ([`apps/ml-api/app/api/routes/auth.py`](../../apps/ml-api/app/api/routes/auth.py)), pero ningún concepto de plan ni webhook.

## Decisión

Cuando se priorice la monetización, integrar Stripe siguiendo este esquema:

1. **Modelo de datos**: tabla `subscriptions` (`user_id`, `stripe_customer_id`, `stripe_subscription_id`, `plan`, `status`, `current_period_end`).
2. **Endpoints**:
   - `POST /api/v1/billing/checkout` → crea sesión de Stripe Checkout.
   - `POST /api/v1/billing/portal` → URL del Customer Portal.
   - `POST /api/v1/billing/webhook` → recibe `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`. Verificación HMAC obligatoria con `STRIPE_WEBHOOK_SECRET`.
3. **Cuotas**: `beta_daily_analysis_quota` se reemplaza por una función `quota_for_plan(user)`. Free conserva el actual; Pro multiplica; Team es por workspace.
4. **Feature flags**: middleware que adjunta `request.state.plan` y deniega features Pro/Team con `403` claro.
5. **Secrets**: `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` en gestor de secretos; nunca en el repo. Alinear con [`docs/SECURITY_PROGRAM.md`](../SECURITY_PROGRAM.md).

## Consecuencias

- Aumenta superficie de ataque: cualquier endpoint público adicional (especialmente el webhook) necesita rate limiting, validación HMAC y respuestas idempotentes.
- Cambia el modelo de soporte (reembolsos, downgrades, sincronización con Stripe).
- Bloqueante: requiere entidad legal para emitir facturas.

## Alternativas descartadas

- **Paddle / Lemon Squeezy**: simplifican IVA pero acoplan a vendor MoR. Reservado para reconsideración cuando se concrete jurisdicción.
- **Build-it-ourselves**: no aporta valor.

## Trabajo futuro

Cuando se priorice, abrir issue con:
- Diseño detallado del webhook idempotente.
- Tests de integración con `stripe-mock` o `stripe-cli listen`.
- Plan de migración de usuarios beta a planes pagos.
