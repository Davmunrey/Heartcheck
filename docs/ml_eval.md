# Evaluación del modelo (HeartScan)

HeartScan analiza **fotos** de tiras de ECG, no señales digitales limpias. La evaluación tiene que medir explícitamente la brecha **foto ↔ señal** además de la calidad del clasificador. La fuente de verdad ejecutable es [`apps/ml-api/app/eval/`](../apps/ml-api/app/eval/) y el comando único:

```bash
make eval                              # genera synth y corre baseline vs candidato
make eval-gate BASELINE=eval/baselines/synth_v1.json
```

## Conjuntos

- **`synth_v1`** — generado por [`apps/ml-api/app/eval/synth.py`](../apps/ml-api/app/eval/synth.py). Determinista por seed; cubre perspectiva, blur, glare, sombras. Documentado en [`docs/DATASHEET_SYNTH.md`](DATASHEET_SYNTH.md).
- **`real_v1`** — fotos reales etiquetadas según [`data/real_eval/README.md`](../data/real_eval/README.md). Nunca commiteadas. Mínimo 50 muestras; ideal 100–200.
- **PTB-XL** (vía `ml/`) — para entrenamiento; no es objetivo principal de esta doc.

## Métricas (todas en el reporte de `make eval`)

| Familia | Métrica | Por qué |
|---------|---------|--------|
| Clasificador | accuracy, F1 macro, F1 por clase, matriz de confusión | Resumen estándar normal/arritmia/ruido. |
| Calibración | ECE, Brier | El estado verde/amarillo/rojo depende de la confianza, no solo del argmax. |
| Confianza vs error | AUROC `max_prob` predice `pred == truth` | "El modelo sabe cuándo no sabe." |
| Latencia | p50, p95, mean (ms) | Foto → JSON debe ser interactivo. |
| Abstención | fracción de respuestas no reportables (rojo+ruido) | Honestidad del producto. |

Todas se calculan en [`apps/ml-api/app/eval/metrics.py`](../apps/ml-api/app/eval/metrics.py) sin sklearn.

## Gate de release

Por defecto el harness no bloquea; con `--gate` y `--baseline path.json` falla con código 2 si:

- F1 macro empeora más de **0.02** (2 puntos), o
- ECE empeora más de **0.05**.

Puedes ajustar `MAX_F1_REGRESSION` y `MAX_ECE_REGRESSION` en [`apps/ml-api/app/eval/cli.py`](../apps/ml-api/app/eval/cli.py) si revisas el [`docs/MODEL_CARD.md`](MODEL_CARD.md) y el [`CONTRIBUTING.md`](../CONTRIBUTING.md) en el mismo cambio.

## Provenance

Cada checkpoint debe ir acompañado de un manifiesto YAML (ver [`apps/ml-api/app/ml/manifest.py`](../apps/ml-api/app/ml/manifest.py)). En producción [`load_model`](../apps/ml-api/app/services/inference.py) rechaza el arranque si el manifiesto falta o el SHA-256 no coincide.

## Carga segura

`torch.load(weights_only=True)` por defecto. La excepción explícita `HEARTSCAN_ALLOW_UNSAFE_TORCH_LOAD` solo se acepta cuando el checkpoint viene de una fuente firmada y auditada.

## Telemetría operacional

[`apps/ml-api/app/core/metrics.py`](../apps/ml-api/app/core/metrics.py) expone histogramas de confianza, calidad y tamaño del conjunto conformal, además de contadores por motivo de no-reporte. Las alertas de drift se definen en [`docs/prometheus/alerts.example.yml`](prometheus/alerts.example.yml).
