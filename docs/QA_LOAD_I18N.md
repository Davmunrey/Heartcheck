# QA: E2E, carga e i18n (beta)

## Pruebas automatizadas

- **Backend**: `pytest` en CI (`.github/workflows/ci.yml`).
- **Flutter**: `flutter analyze`, `flutter test`, `flutter gen-l10n` en CI.

## Humo de carga (k6)

Requisitos: [k6](https://k6.io/) instalado y API accesible.

```bash
export K6_API_URL=https://staging.example.com
k6 run scripts/k6/smoke.js
```

Extender el script para subir imágenes solo en entornos controlados (evitar abuso en producción pública).

## E2E

Para flujos web críticos (landing → login → análisis), valorar Playwright o similar apuntando a staging con credenciales de prueba.

## i18n

- Cadenas en `apps/mobile/lib/l10n/`; ejecutar `flutter gen-l10n` tras cambios.
- Revisar textos legales en `web_public/legal/` con asesoría local.

## Accesibilidad (WCAG 2.1 AA — checklist breve)

- Contraste texto/fondo en landing y `app.html`.
- Foco visible en botones y enlaces; orden de tabulación lógico.
- Etiquetas en formularios (email, contraseña, archivo).
- Mensajes de error comprensibles (API devuelve `error_code`).
