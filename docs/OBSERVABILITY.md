# Observabilidad (beta)

## Logs

- Salida **JSON estructurada** (`app/core/logging.py`) en stdout; en producción redirigir al agregador (CloudWatch, Datadog, Grafana Loki, etc.).
- No registrar cuerpos de imagen ni base64 de archivos.

## Errores

- **Sentry**: configurar `HEARTSCAN_SENTRY_DSN` en el API. Filtrar PII en el panel Sentry si se amplían los eventos.

## Métricas

- Endpoint **`/metrics`** (Prometheus): latencias y contadores de análisis.
- En Grafana Cloud o stack propio: paneles para tasa 5xx, latencia p95 de `/api/v1/analyze`, uso de CPU/memoria del contenedor.

## Alertas sugeridas

- Ratio HTTP 5xx &gt; 1 % durante 5 minutos.
- Latencia p95 del histograma de análisis por encima del umbral acordado.
- Healthcheck externo fallando (ver abajo).

## Uptime externo

Configurar un monitor (UptimeRobot, Better Stack, Pingdom, etc.) contra:

- `GET https://<host>/health` cada 1–5 minutos.

## Runbooks

- [Incidentes y caídas del API](runbooks/incident.md)
