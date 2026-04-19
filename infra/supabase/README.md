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

2. **Clerk ↔ Supabase (imprescindible para que `auth.jwt()` vea tu token)** — Flujo recomendado por la plataforma:
   - En Clerk: [Connect with Supabase](https://dashboard.clerk.com/setup/supabase) (ajusta claims compatibles con Supabase).
   - En Supabase: **Authentication → Sign In / Third Party → Add provider → Clerk** (o [Third-party auth](https://supabase.com/docs/guides/auth/third-party/clerk) en la doc). Sustituye `/_/auth/third-party` en la URL del dashboard por el ID de tu proyecto.

3. **JWT template `supabase` en Clerk** — Nombre exacto **`supabase`**, con claim **`org_id`** (organización activa). Lo usa [`apps/web/lib/supabase/server.ts`](../../apps/web/lib/supabase/server.ts) vía `getToken({ template: 'supabase' })`. Detalle: [`docs/AUTH_CLERK.md`](../../docs/AUTH_CLERK.md).

4. **Probar** — `pnpm dev` desde la raíz del monorepo (o `pnpm --filter web dev`). Opcional: ejecutar comprobaciones RLS desde [`tests/rls.sql`](./tests/rls.sql).
