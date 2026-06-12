FROM python:3.14-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/ml-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/ml-api/app ./app
COPY apps/ml-api/weights ./weights
# Bake the served 28-class diagnostic checkpoint (AUROC ~0.87) so the image
# serves the real model instead of falling back to the heuristic classifier.
# Reuses the git-tracked checkpoint; override HEARTSCAN_DIAGNOSTIC_MODEL_PATH to swap.
COPY runs/local/full27/checkpoint.pt ./weights/diagnostic_ecg27.pt
COPY web_public ./web_public

RUN useradd --create-home --uid 10001 --no-log-init appuser \
    && chown -R appuser:appuser /app
USER 10001

ENV PYTHONPATH=/app
# Default to the baked diagnostic model; Render/Fly secrets can override.
ENV HEARTSCAN_DIAGNOSTIC_MODEL_PATH=/app/weights/diagnostic_ecg27.pt
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
