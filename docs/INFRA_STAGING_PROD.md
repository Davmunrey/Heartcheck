# Infraestructura: staging y producción

## Entornos

- **Staging**: datos no reales; misma topología que producción con secretos distintos.
- **Production**: `HEARTSCAN_ENV=production`, `HEARTSCAN_ALLOW_LEGACY_API_KEY=false`, JWT y base de datos gestionados.

Variables clave (prefijo `HEARTSCAN_`):

| Variable | Staging / Prod |
|----------|----------------|
| `DATABASE_URL` | Postgres gestionado (URL `postgresql+psycopg2://...`) |
| `JWT_SECRET_KEY` | Secreto largo, rotado según política interna |
| `API_KEY` | Solo si legado activo; desactivar en prod |
| `ALLOW_LEGACY_API_KEY` | `false` en prod |
| `SENTRY_DSN` | Proyecto Sentry de prod o staging |
| `CORS_ORIGINS` | Orígenes explícitos del front (no `*`) |

## Docker Compose (desarrollo / pruebas locales)

Desde `infra/`:

```bash
docker compose up --build
```

Esto levanta **Postgres 16**, **Redis** (opcional para futuros límites distribuidos / colas) y la **API** en `http://localhost:8000`. Ajusta `POSTGRES_PASSWORD` y `HEARTSCAN_JWT_SECRET_KEY` en el entorno o en un archivo `.env` no versionado.

## HTTPS y secretos

- Termina TLS en el balanceador (AWS ALB, Cloud Run con certificado gestionado, Fly.io, Caddy, etc.) o detrás de un reverse proxy (nginx, Traefik).
- Secretos en el proveedor (GitHub Actions secrets, Doppler, Vault, parámetros del PaaS). Nunca en el repositorio.

## Redis

Redis está incluido en Compose para pruebas locales. El rate limiting actual (`slowapi`) es por proceso; para límites coordinados entre réplicas, valorar backend Redis compartido o gateway con cuotas (documentar en ADR si se implementa).

## Orquestación

Para cargas mayores, el mismo contenedor `apps/ml-api/Dockerfile` puede desplegarse en **Cloud Run**, **ECS/Fargate**, **Fly.io**, **Railway** o **Kubernetes**, con Postgres administrado y variables de entorno inyectadas por la plataforma.
