# HeartScan — Programa de seguridad

> Documento operativo. Resume el modelo de amenazas, los controles aplicados, las dependencias auditables y las verificaciones que el equipo se compromete a ejecutar.

## 1. Modelo de amenazas (resumen)

### Activos a proteger

| Activo | Por qué importa |
|--------|------------------|
| Imágenes de ECG subidas | Datos de salud potenciales (no PHI por defecto, pero pueden serlo). |
| Cuentas y emails | PII; acceso a cuotas y futura facturación. |
| Tokens JWT | Vector de impersonación. |
| Pesos del modelo (`HEARTSCAN_MODEL_PATH`) | Propiedad intelectual + vector de RCE si se carga sin `weights_only`. |
| Secretos: `HEARTSCAN_API_KEY`, `HEARTSCAN_JWT_SECRET_KEY`, `STRIPE_*`, `POSTGRES_PASSWORD` | Acceso completo al sistema. |
| Logs y métricas | Pueden filtrar información si se loguea sin filtros. |

### Actores y vectores

| Actor | Vector típico | Mitigación |
|-------|---------------|-----------|
| Atacante anónimo | Fuerza bruta de login, flooding `/analyze`, fuzzing de uploads | Rate limit (slowapi), validación magic-byte, JWT obligatorio en producción. |
| Usuario autenticado malicioso | Subir contenido tóxico (zip-bomb, polyglot), abusar cuotas, escalar a otros tenants | `max_upload_bytes`, `beta_daily_analysis_quota`, validación de tipo, ausencia de tenancy compartida hoy. |
| Atacante de cadena de suministro | Paquete pip/npm comprometido | `pip-audit`, `npm audit`, pin estrictos, `bcrypt<4` documentado. |
| Insider/operador | Acceso a logs, BDD | Logs sin PII, secretos en gestor externo, principio de mínimo privilegio. |
| Atacante de modelo | Checkpoint malicioso (pickle RCE) | `torch.load(weights_only=True)` por defecto, alternativa explícita y auditada (`HEARTSCAN_ALLOW_UNSAFE_TORCH_LOAD`). |
| Browser-based | XSS, CSRF, exfiltración via CORS | `SecurityHeadersMiddleware` con CSP estricta para estáticos, CORS restringido en producción, `frame-ancestors 'none'`. |

### Superficie expuesta

| Endpoint | Método | Auth | Notas |
|----------|--------|------|-------|
| `/health` | GET | — | Solo `status`. |
| `/api/v1/meta` | GET | — | Versión de pipeline/modelo. Sin secretos. |
| `/api/v1/auth/register` | POST | — | Rate limited 10/min. |
| `/api/v1/auth/login` | POST | — | Rate limited 20/min. |
| `/api/v1/analyze` | POST | Bearer JWT o `X-API-Key` (legacy) | Rate limit 120/min, magic-byte check, cuota diaria. |
| `/api/v1/reports/pdf` | POST | Bearer JWT o `X-API-Key` | Reutiliza `AnalysisResponse`. |
| `/api/v1/education` | GET | — | Contenido estático (YAML). |
| `/metrics` | GET | — (recomendado proteger) | Considerar bind interno o auth. |

## 2. Controles aplicados (código actual)

- **Auth**:
  - Hash bcrypt vía `passlib`; `bcrypt<4` pinneado para evitar regresión silenciosa.
  - JWT HS256 con secreto en variable; tiempos de expiración configurables.
  - `_api_key_matches` usa `hmac.compare_digest` (mitigación timing).
- **Auto-defensa de despliegue**: `_refuse_insecure_production_defaults` aborta el arranque si `HEARTSCAN_ENV=production` con secretos por defecto, JWT débil o CORS `*`.
- **CORS**: cuando `HEARTSCAN_CORS_ORIGINS=*`, `allow_credentials=False` (cumple spec).
- **Cabeceras**: [`SecurityHeadersMiddleware`](../apps/ml-api/app/middleware/security_headers.py) añade `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` y CSP estricta en `/docs` y estáticos.
- **Rate limiting**: `slowapi` por IP, en `/analyze`, `/auth/login`, `/auth/register`.
- **Cuotas**: `beta_daily_analysis_quota` por usuario.
- **Uploads**: `max_upload_bytes`, validación de magic bytes (`PNG/JPEG/WebP`), respuesta `415` específica.
- **Errores genéricos**: handler global devuelve `request_id` y mensaje neutro; los detalles van al log.
- **Modelo**: `torch.load(weights_only=True)` por defecto; opt-in inseguro explícito.

## 3. Cadena de suministro y CI

- Dependencias Python: [`apps/ml-api/requirements.txt`](../apps/ml-api/requirements.txt) con rangos acotados; `bcrypt<4` justificado por compatibilidad con `passlib`.
- Dependencias Node: [`web/package.json`](../web/package.json), versiones fijas mayores.
- Recomendaciones para el pipeline (no ejecutadas aquí, pendiente del CI elegido):
  - `pip install pip-audit && pip-audit -r apps/ml-api/requirements.txt`
  - `npm audit --omit=dev` en `web/`
  - Escaneo de secretos en PR (`gitleaks`, `trufflehog`).
  - Build de imágenes Docker desde tags fijos, con `docker scout cves` o `trivy image`.
  - Bloquear merge si CVE crítico no tiene excepción documentada.
- SBOM: generar con `syft .` (Python) y `cyclonedx-npm` para web cuando se acerque GA.

## 4. Operación y respuesta a incidentes

- **Logs estructurados** (`structlog`) en stdout; nunca cuerpos de imagen ni `Authorization`.
- **Sentry** opcional vía `HEARTSCAN_SENTRY_DSN`; revisar filtros antes de enviar PII.
- **Alertas** sugeridas en [`docs/OBSERVABILITY.md`](OBSERVABILITY.md) (5xx, p95, healthcheck).
- **Runbook** de incidente: [`docs/runbooks/incident.md`](runbooks/incident.md).
- **Rotación de secretos**: documentada en este doc; ejecutar tras pentest, tras salida de empleado o tras detección de fuga.

## 5. Verificación externa

- **Pentest** anual o antes de un lanzamiento mayor; alcance: API, autenticación, abuso de uploads, cabeceras, dependencias.
- **Programa de divulgación responsable**: alias `security@heartscan.example` con SLA público de 72 h para ack y 30 días para fix de bugs medios.
- **Bug bounty** opcional cuando el producto justifique el coste (p. ej. usuarios pagados o B2B firmando DPAs).

## 6. Limitaciones honestas

- HeartScan **no** es un dispositivo médico ni pretende serlo.
- Los controles aquí descritos reducen riesgo, **no garantizan invulnerabilidad**.
- Cualquier despliegue que se aleje de las defaults (CORS, claves, modelo) debe documentarse en una revisión de cambios y actualizar este documento.
