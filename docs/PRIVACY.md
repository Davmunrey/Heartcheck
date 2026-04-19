# Privacidad (borrador para beta)

> Este documento es un **borrador interno** que orienta el comportamiento por defecto del producto. No sustituye la política pública que firmará el equipo legal antes de cada lanzamiento (ver [`docs/legal/DRAFT_NOTICE.md`](legal/DRAFT_NOTICE.md)).

## Principios

1. **Minimización**: el backend **no almacena** las imágenes de ECG por defecto. Solo se procesan en memoria para devolver `AnalysisResponse`.
2. **Datos personales** (email, contraseña hasheada con bcrypt) se guardan únicamente porque la cuota y el JWT lo requieren ([`apps/ml-api/app/db/models.py`](../apps/ml-api/app/db/models.py)).
3. **Transparencia**: el usuario sabe qué se envía (foto + cabeceras) y qué se devuelve (clase, BPM aproximado, mensaje educativo, disclaimer).
4. **Sin perfilado clínico**: el producto es informativo/educativo. No se construyen historiales clínicos.

## Datos que se procesan

| Dato | Origen | Almacenamiento | Retención |
|------|--------|----------------|-----------|
| Imagen ECG | Cliente (multipart) | Solo memoria del proceso | Liberada al terminar la petición |
| Cabeceras (`X-API-Key`, `Authorization`, `Accept-Language`) | Cliente | No persistidas | — |
| Email + hash de contraseña | Registro | `users` | Hasta baja del usuario |
| Conteo diario por usuario | Sistema | `usage` | Rota cada día |
| Logs estructurados | App | Stdout / agregador | Según política del agregador (recomendado ≤ 30 días, sin PII) |
| Métricas Prometheus | App | `/metrics` | Definido por la pila Grafana |

## Cuándo se almacenan imágenes

Hoy: **nunca**. Si en el futuro se añade “historial en la nube” como opt-in:

- Consentimiento explícito en UI (no checkbox preseleccionado).
- Cifrado en reposo (KMS) y en tránsito (TLS).
- Retención máxima documentada y eliminación a petición.

## Derechos del usuario

- **Acceso**: el usuario puede pedir copia de su email, fecha de creación y conteos asociados.
- **Borrado**: endpoint o proceso operativo para eliminar usuario y registros asociados.
- **Portabilidad**: exportación JSON de los mismos datos.

Estas acciones aún no tienen endpoint público; deben ejecutarse manualmente por el equipo de soporte hasta su implementación.

## Sub-encargados

Si se contratan servicios externos (Sentry, Stripe, proveedor de email, hosting), añadir lista pública con país, finalidad y base jurídica antes de exponer producción.

## Disclaimer médico

HeartScan **no** es un dispositivo médico ni sustituye una valoración clínica. Cualquier resultado debe ir acompañado del disclaimer servido por el backend (ver `analysis_pipeline.DISCLAIMER_*`).
