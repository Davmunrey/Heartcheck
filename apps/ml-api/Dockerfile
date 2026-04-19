FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/ml-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/ml-api/app ./app
COPY apps/ml-api/weights ./weights
COPY web_public ./web_public

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
