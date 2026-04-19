# Sistema visual de HeartScan

HeartScan tiene **dos superficies web con propósitos distintos**, y por tanto **dos pieles**. La decisión es explícita y se documenta para evitar drift.

## Superficies y pieles

| Superficie | Audiencia | Tema | Tokens |
|------------|-----------|------|--------|
| Landing/SaaS pública (`web_public/`) | Visitantes, prospectos, usuarios autenticados en producción | Claro, alta densidad de contenido editorial | [`web_public/static/saas.css`](../web_public/static/saas.css) |
| SPA Vite (`web/`) | Desarrolladores, beta-testers, integradores; eventual modo “laboratorio” | Oscuro, focalizado en el flujo de análisis | [`web/src/index.css`](../web/src/index.css) + [`web/src/App.css`](../web/src/App.css) |

Marca compartida: nombre **HeartScan**, símbolo `♡`, mismo lenguaje (es-ES por defecto), mismo disclaimer médico, misma jerarquía Beta.

## Tokens compartidos (referencia)

Aunque cada hoja define los suyos, los **valores semánticos** se mantienen alineados:

| Semántica | Landing (`saas.css`) | SPA (`App.css`/`index.css`) |
|-----------|----------------------|-----------------------------|
| Color marca primario | `#1565c0` | `#4f8dff` (mejor contraste sobre fondo oscuro) |
| Verde (estado OK) | `#34a853` | `#4ade80` |
| Amarillo (alerta media) | `#f9ab00` | `#fbbf24` |
| Rojo (atención) | `#ea4335` | `#f87171` |
| Radio mediano | `12–16px` | `14px` |
| Foco visible | `box-shadow: 0 0 0 3px rgba(...)` | igual con tono accent |
| Tamaño táctil mínimo | `44px` | `44px` |

## Reglas

1. **Voz**: misma terminología (Analizar, Beta, FAQ, Resultado, Disclaimer). El SPA puede explicar más que la landing pero no introducir términos nuevos sin actualizar la landing y la web estática.
2. **Disclaimers**: visibles en todas las superficies; nunca eliminarlos del flujo de análisis.
3. **Accesibilidad**: contraste AA mínimo en texto principal; foco visible siempre; objetivos táctiles ≥44px en zonas críticas.
4. **Animaciones**: respetar `prefers-reduced-motion: reduce`.
5. **Modo oscuro**: la SPA es siempre oscura (es entorno de trabajo). La landing es clara para SEO/marketing y porque transmite tono médico/serio.
6. Antes de unificar tokens en un único paquete (`@heartscan/tokens` o similar), bloquear el drift con esta tabla; cualquier nuevo color o radio se añade aquí primero.

## Cambios futuros

- Si en algún momento se decide migrar a Flutter Web como única superficie pública, retirar `web_public/` y reescribir esta tabla.
- Si la SPA pasa a producción para usuarios finales, considerar exponer un selector light/dark con `prefers-color-scheme` y mantener los nuevos tokens claros aquí.
