# HeartScan SaaS Ecosystem

Estado: arquitectura producto + base implementada. Uso clínico real requiere
validación clínica, legal, privacidad, seguridad, regulación, contrato hospital.

## Superficie producto

- Landing enterprise: `/`
- ECG copilot: `/copilot`
- Seguridad/compliance: `/security`
- Pricing/trial: `/pricing`
- Enterprise: `/enterprise`
- Console: `/dashboard`
- Copilot upload: `/analyze`
- Billing org: `/settings/billing`

## Modelo comercial

- Trial: 7 días por organización Clerk.
- Clinic: cuota mensual para clínicas.
- Hospital: cuota mayor, audit/compliance/SLA.
- Enterprise: contrato, SSO, VPC/on-prem, validación local.

Variables:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_CLINIC`
- `STRIPE_PRICE_HOSPITAL`
- `NEXT_PUBLIC_APP_URL`

## Seguridad mínima

- Tenant boundary: Clerk Organizations.
- Data boundary: Supabase RLS por `auth.jwt() ->> 'org_id'`.
- Storage: bucket privado `ecg-uploads`, ruta `{org_id}/{uuid}`.
- Audit: `audit_log` append-only + hash chain.
- Billing webhook: verificación HMAC Stripe.
- Clerk webhook: Svix signature.
- Upload: límite 10 MB, allowlist MIME en UI, API debe validar bytes.
- Logs: no PHI ni imagen base64.
- Retención: helpers SQL de purge/soft-delete.

## Workflow orchestration

Recomendación: Temporal cuando haya producción multi-hospital.

Regla:

- Workflows = decisiones deterministas.
- Activities = DB/API/storage/payment/ML/notifications.
- Activities idempotentes con `request_id`/`stripe_event_id`.

### ECGAnalysisWorkflow

1. `ReserveQuotaActivity`
2. `StoreUploadActivity`
3. `QualityGateActivity`
4. `RunInferenceActivity`
5. `GenerateReportActivity`
6. `WriteAuditActivity`
7. Esperar signal opcional `DoctorReviewSubmitted`
8. `QueueFeedbackActivity`

Compensaciones:

- Si falla storage posterior a cuota: `ReleaseQuotaActivity`.
- Si falla reporte: análisis queda `needs_retry`, no pierde upload.

### TrialLifecycleWorkflow

1. `CreateCompanyActivity`
2. `StartTrialActivity`
3. Timer 7 días.
4. Si no `SubscriptionActiveSignal`, marcar `trial_expired`.
5. `NotifyOwnerActivity`.

### BillingWorkflow

1. `CreateCheckoutSessionActivity`
2. Esperar Stripe webhook/signal.
3. `UpsertSubscriptionActivity`
4. `WriteBillingEventActivity`
5. `WriteAuditActivity`

Idempotencia:

- Stripe: `stripe_event_id` unique.
- Checkout: `client_reference_id = org_id`.
- Analyses: `request_id` unique lógico.

## Gate clínico

No mostrar “diagnóstico definitivo”.

Mensajes permitidos:

- “AI assist”
- “probabilidad”
- “requires clinician review”
- “no sustituye valoración clínica”

Bloquear:

- “100%”
- “diagnóstico automático”
- “apto para decisión médica sin revisión”

## Próximo hardening

- Stripe webhook tests con payload firmado.
- RLS integration tests contra Supabase local.
- Security headers CSP estricta.
- DPA/BAA templates.
- SOC2 evidence checklist.
- Temporal worker repo/package.
- Red-team upload fuzzing.

