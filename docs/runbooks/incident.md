# Runbook: incidente en el API HeartScan

## Síntomas

- Monitor externo en rojo sobre `/health`.
- Picos de 5xx o latencia en `/metrics` / dashboard.
- Informes de usuarios beta (canal de soporte).

## Comprobaciones rápidas (orden)

1. **Estado del contenedor / servicio** en la plataforma (restarts, OOM, CPU).
2. **Postgres**: conectividad, conexiones saturadas, disco lleno.
3. **Logs** recientes: errores de aplicación, trazas Sentry.
4. **Despliegue reciente**: revertir imagen a la etiqueta anterior si coincide temporalmente con el incidente.

## Rollback

1. Desplegar la imagen Docker anterior etiquetada en el registro.
2. Confirmar `/health` y una petición autenticada a `POST /api/v1/analyze` en staging antes de repetir en prod.

## Secretos

Si se sospecha fuga de `JWT_SECRET_KEY` o `API_KEY`: rotar en el almacén de secretos, redeploy, y forzar nuevos inicios de sesión (JWT).

## Comunicación

- Actualizar página de estado interna o aviso breve a beta testers según el SLA acordado.
