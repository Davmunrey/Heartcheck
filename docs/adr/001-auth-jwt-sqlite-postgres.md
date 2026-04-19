# ADR 001: Autenticación JWT y persistencia SQLite / Postgres

## Estado

Aceptado.

## Contexto

La beta requiere sustituir una API key global por identidad por usuario, cuotas diarias y trazabilidad mínima sin depender aún de un IdP externo obligatorio.

## Decisión

- Autenticación con **JWT** (HS256) emitido tras `POST /api/v1/auth/login`, validado en rutas protegidas.
- Usuarios y uso diario en **SQLAlchemy** con **SQLite** por defecto en desarrollo y **Postgres** en Docker / producción (`HEARTSCAN_DATABASE_URL`).
- Compatibilidad opcional con **`X-API-Key`** cuando `HEARTSCAN_ALLOW_LEGACY_API_KEY=true` (desactivar en producción).

## Consecuencias

- Migraciones manuales o `create_all` en arranque (MVP); valorar Alembic si el esquema crece.
- Rotación de `JWT_SECRET_KEY` invalida sesiones existentes; documentar ventana de mantenimiento.
- IdP gestionado (Clerk, Auth0, Supabase Auth) puede sustituir emisión de JWT en una fase posterior sin cambiar el contrato Bearer del cliente.
