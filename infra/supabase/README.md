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
