# Supabase — qué va en GitHub

Este directorio es lo que **sí** se versiona en el repositorio (sin secretos).

| Contenido | Uso |
|-----------|-----|
| [`migrations/`](./migrations/) | SQL para aplicar en el editor SQL del proyecto Supabase (o `supabase db push` si usas CLI). |
| [`tests/rls.sql`](./tests/rls.sql) | Comprobaciones manuales de RLS; ver también `docs/SUPABASE_SCHEMA.md`. |

## Qué no va en GitHub

- Claves `anon`, `service_role`, ni URL con credenciales.
- Copias locales de `.env` / `.env.local` (están en `.gitignore`).

Configuración de entornos y checklist: [`docs/DEPLOYMENT.md`](../../docs/DEPLOYMENT.md), integración Clerk + JWT template `supabase`: [`docs/AUTH_CLERK.md`](../../docs/AUTH_CLERK.md).

## Checklist (tras `NEXT_PUBLIC_SUPABASE_*` en `apps/web/.env.local`)

1. **Migración SQL** — En Supabase: **SQL Editor → New query**, pega el contenido completo de [`migrations/20250419120000_heartscan_multitenant.sql`](./migrations/20250419120000_heartscan_multitenant.sql) y **Run**. Crea tablas, RLS, políticas de Storage y el bucket `ecg-uploads`.  
   También puedes aplicarla con la CLI de Supabase o el MCP del proyecto; si ya existen las tablas, verás errores de “policy already exists” y puedes ignorar la repetición.

2. **Plantilla JWT `supabase` en Clerk** — Idempotente desde la raíz del repo (usa `CLERK_SECRET_KEY` en `apps/web/.env.local`):

   ```bash
   ./scripts/ensure_clerk_jwt_template_supabase.sh
   ```

   Crea la plantilla **`supabase`** con claims `org_id`, `org_role`, `org_slug` (shortcodes `{{org.*}}`). Requiere **Organizations** en Clerk y un usuario en una organización para que `org_id` no venga vacío.

3. **Clerk ↔ Supabase (imprescindible para que PostgREST valide el JWT de Clerk)** — Solo en el dashboard (no automatizable por API aquí); flujo recomendado:
   - En Clerk: [Connect with Supabase](https://dashboard.clerk.com/setup/supabase) (ajusta claims compatibles con Supabase).
   - En Supabase: **Authentication → Sign In / Third Party → Add provider → Clerk** (o [Third-party auth](https://supabase.com/docs/guides/auth/third-party/clerk) en la doc). Sustituye `/_/auth/third-party` en la URL del dashboard por el ID de tu proyecto. Pega el **dominio Clerk** que te indica Clerk (suele ser `*.clerk.accounts.dev`).

   El cliente Next.js usa [`apps/web/lib/supabase/server.ts`](../../apps/web/lib/supabase/server.ts) con `getToken({ template: 'supabase' })`. Más detalle: [`docs/AUTH_CLERK.md`](../../docs/AUTH_CLERK.md).

4. **Probar** — `pnpm dev` desde la raíz del monorepo (o `pnpm --filter web dev`). Opcional: ejecutar comprobaciones RLS desde [`tests/rls.sql`](./tests/rls.sql).

## Automatización (sin clics en el dashboard)

| Paso | Cómo |
|------|------|
| Plantilla JWT `supabase` en Clerk | [`scripts/ensure_clerk_jwt_template_supabase.sh`](../../scripts/ensure_clerk_jwt_template_supabase.sh) (usa `CLERK_SECRET_KEY`) |
| Third-party Clerk en Supabase (issuer + JWKS) | [`scripts/ensure_supabase_clerk_third_party.py`](../../scripts/ensure_supabase_clerk_third_party.py) — requiere [`SUPABASE_ACCESS_TOKEN`](https://supabase.com/dashboard/account/tokens) (PAT con permisos de auth) en `apps/web/.env.local` |
| Ambos | `./scripts/bootstrap_clerk_supabase.sh` |

**CI:** workflow manual [`.github/workflows/clerk-supabase-integrations.yml`](../../.github/workflows/clerk-supabase-integrations.yml) (`workflow_dispatch`) con secretos `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_ACCESS_TOKEN`.

La **migración SQL** sigue siendo un paso aparte (editor SQL, CLI o pipeline que ejecute el `.sql`).
