# Ruta canónica del proyecto

**La raíz de trabajo es:**

```text
~/dev/Heartcheck
```

Abre **esta** carpeta en el IDE. Aquí está el monorepo **Axis**
(`apps/ml-api/`, `apps/web/`, `apps/mobile/`, `ml/`, `web_public/`).

## ⚠️ No uses la copia del Desktop

```text
~/Desktop/Heartcheck   ← NO USAR
```

Esa carpeta vive en **iCloud Drive** (Desktop & Documents) y quedó *evicted /
dataless*: los archivos son placeholders sin contenido local. Leerlos cuelga
servidores (`http.server`, uvicorn) y entrenamientos durante minutos, o
devuelve respuestas vacías (HTTP 000). La copia limpia y editable está en
`~/dev/Heartcheck`; trabaja siempre ahí.

## Comprobar Axis

```bash
test -f ~/dev/Heartcheck/apps/ml-api/app/main.py \
  && test -f ~/dev/Heartcheck/apps/web/package.json \
  && echo "OK: Axis en ~/dev/Heartcheck"
```
