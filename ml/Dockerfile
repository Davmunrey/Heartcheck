FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY heartscan_ml ./heartscan_ml

RUN pip install --no-cache-dir -e ".[api]"

ENV HEARTSCAN_HOST=0.0.0.0
ENV HEARTSCAN_PORT=8000

EXPOSE 8000

# Montar volumen con checkpoints/cnn1d_best.pt en /app/checkpoints
CMD ["uvicorn", "heartscan_ml.api:app", "--host", "0.0.0.0", "--port", "8000"]
