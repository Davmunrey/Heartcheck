# Distribución beta: web, iOS y Android

## Web

- Dominio propio con **HTTPS** (TLS en el balanceador o proxy).
- Estáticos y `app.html` servidos por la API en desarrollo; en producción se puede poner un **CDN** delante o un bucket + mismo dominio con rutas `/` y `/app`.

## Builds Flutter

Si el proyecto aún no tiene carpetas de plataforma, generarlas una vez en `apps/mobile/`:

```bash
flutter create . --platforms=web,android,ios --project-name heartscan
```

Desde `apps/mobile/` (tras `flutter pub get` y `flutter gen-l10n`):

```bash
flutter build web --release
flutter build apk --release
flutter build appbundle --release
flutter build ios --release
```

Asegurar que las URLs del API y CORS coinciden con `HEARTSCAN_CORS_ORIGINS`.

## iOS (TestFlight)

1. Cuenta **Apple Developer Program**.
2. App Store Connect: crear app, rellenar **privacidad** y clasificación de salud según el posicionamiento legal acordado.
3. Archivar en Xcode, subir build, abrir prueba interna/externa **TestFlight**.

## Android (Play closed testing)

1. Play Console: crear app, formulario **Data safety** y política de contenido de salud.
2. Pista **interna** o **cerrada** con lista de testers.
3. Subir AAB desde `build/app/outputs/bundle/release/`.

## Versionado

- Mantener `version` en `apps/mobile/pubspec.yaml` alineada con tags Git y notas de release para beta testers.

## Checklist de prelanzamiento (release mayor)

Marcar cada ítem antes de promover a TestFlight/Play o exponer un dominio público:

### Backend / API
- [ ] `pytest` verde en `apps/ml-api/` (incluye `test_meta.py`, `test_auth.py`, `test_analyze.py`, `test_reports.py`).
- [ ] `HEARTSCAN_API_KEY`, `HEARTSCAN_JWT_SECRET_KEY` y `POSTGRES_PASSWORD` rotados con valores de alta entropía.
- [ ] `HEARTSCAN_ALLOW_LEGACY_API_KEY=false` en producción.
- [ ] `HEARTSCAN_CORS_ORIGINS` con orígenes explícitos (sin `*`).
- [ ] Imágenes Docker reconstruidas y escaneadas (`docker scout cves` o equivalente).
- [ ] Modelo cargado (`/api/v1/meta` devuelve `checkpoint_loaded: true`) o decisión explícita de seguir con baseline.

### Observabilidad
- [ ] `HEARTSCAN_SENTRY_DSN` configurado.
- [ ] Dashboards Grafana (5xx, p95 `/api/v1/analyze`, CPU/memoria) cargados.
- [ ] Alertas activas según [`docs/OBSERVABILITY.md`](OBSERVABILITY.md) y [`docs/prometheus/alerts.example.yml`](prometheus/alerts.example.yml).
- [ ] Monitor externo (UptimeRobot/Better Stack) apuntando a `/health`.

### Seguridad
- [ ] [`docs/SECURITY_PROGRAM.md`](SECURITY_PROGRAM.md) revisado y actualizado.
- [ ] `pip-audit` / `npm audit` sin CVE críticos sin justificar.
- [ ] [`docs/runbooks/incident.md`](runbooks/incident.md) leído por el on-call.
- [ ] Pentest externo o, como mínimo, escaneo automatizado documentado.

### Carga
- [ ] `K6_API_URL=... K6_API_KEY=... K6_SAMPLE_IMAGE=... k6 run scripts/k6/smoke.js` cumple los `thresholds`.

### Producto / legal
- [ ] Disclaimer médico y políticas (`docs/PRIVACY.md`, `docs/legal/`) actualizadas.
- [ ] Consentimientos en flujos de subida si se almacenan imágenes.
- [ ] Versión y notas de release publicadas (`apps/mobile/pubspec.yaml`, tag Git).
