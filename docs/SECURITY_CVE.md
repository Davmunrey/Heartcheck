# Gestión de vulnerabilidades (CVE)

> Este documento se centra en el **proceso** de CVE y rotación. Los **controles aplicados** y el modelo de amenazas viven en [`docs/SECURITY_PROGRAM.md`](SECURITY_PROGRAM.md).

## Escaneo continuo

- **Dependabot** (ver `.github/dependabot.yml`) abre PRs semanales para dependencias pip, Actions y Docker.
- **pip-audit** se ejecuta en CI sobre `apps/ml-api/requirements.txt` antes de tests.
- **npm audit** (`web/`) en CI antes del build.
- Escaneo de imágenes Docker (`trivy image` o `docker scout cves`).
- Escaneo de secretos en pull requests (`gitleaks`).

## Proceso manual ante CVE críticos

1. Reproducir con `pip-audit` / aviso del proveedor.
2. Actualizar la dependencia acotada en `requirements.txt` o subir el límite superior si la corrección está en una versión compatible.
3. Ejecutar `pytest` y pruebas de humo del análisis de imagen.
4. Desplegar en staging y validar `/health`, `/api/v1/analyze`, auth.
5. Nota: **PyTorch** y **OpenCV** pueden tener CVE con parches en versiones mayores; documentar excepciones aceptadas y plazo de actualización.

## Excepciones documentadas

| Paquete | Versión | Razón | Revisar |
|---------|---------|-------|---------|
| `bcrypt` | `<4` | Compatibilidad obligada con `passlib 1.7.x` (no expone `__about__` en `bcrypt>=4`); migrar cuando passlib publique 2.x o se mueva a argon2. | Cada release mayor. |

## Secretos

Rotar `HEARTSCAN_API_KEY`, `HEARTSCAN_JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, claves de Stripe (cuando se integren) y credenciales de base de datos según la política del equipo tras incidentes, salida de personal o rotación programada (mínimo cada 90 días en producción).

El backend rechaza arrancar en producción con secretos por defecto: ver `_refuse_insecure_production_defaults` en [`apps/ml-api/app/main.py`](../apps/ml-api/app/main.py).
