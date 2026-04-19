# Aviso sobre documentos legales

Los HTML en `web_public/legal/` y los markdown en este directorio son **borradores orientativos** para desarrollo y beta. **No constituyen asesoramiento legal.** Antes de un lanzamiento comercial, abogados cualificados en cada jurisdicción deben revisar y adaptar:

- Términos de uso.
- Política de privacidad ([`docs/PRIVACY.md`](../PRIVACY.md) recoge la línea base interna).
- Política de cookies (mínima en la SPA actual; revisar al integrar analytics o pagos).
- Posicionamiento y clasificación regulatoria del producto:
  - Software de bienestar / educación general (postura actual).
  - Software de salud digital sin pretensión diagnóstica.
  - Dispositivo médico de Clase I/II (UE MDR / FDA SaMD) — implicaría QMS, registros clínicos y certificación.
- Procedimiento de quejas y atención al usuario.
- Retención y borrado de datos en el sentido del RGPD/UK GDPR/LOPDGDD/Ley federal de privacidad equivalente.

Cualquier mención a “diagnóstico”, “detección de”, “interpretación clínica” o equivalentes debe sustituirse por lenguaje informativo y educativo (“orientación”, “información general”). El backend ya devuelve un disclaimer (ver `app.services.analysis_pipeline.DISCLAIMER_*`) que debe respetarse en todas las superficies cliente.
