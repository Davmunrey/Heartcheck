# Quality gate (extracción de trazo y calidad de foto)

Componente determinista que mide cuánta información útil tiene la foto **antes** de invocar al clasificador. Sin esta puerta, una foto borrosa puede producir un veredicto con confianza espuria.

## Dos versiones

- **v1** — solo señal 1D ([`extraction_quality_score`](../../apps/ml-api/app/services/quality_gate.py)). Se mantiene como referencia y para uso interno (la heurística de fallback se apoya en ella).
- **v2** — multi-señal, exportada como [`quality_gate_v2`](../../apps/ml-api/app/services/quality_gate.py). Combina la señal v1 con métricas de la foto y devuelve un `GateResult` con `score`, `reasons` y `reportable`. Es la que el pipeline expone al cliente.

## Componentes (v1)

| Componente | Peso | Significado |
|------------|------|-------------|
| `cov` | 0.45 | Fracción de columnas con valor finito (cobertura del trazo). |
| `var_score` | 0.35 | `var / (var + 1)` sobre los valores finitos: penaliza señales planas. |
| `peak_score` | 0.20 | `peak_count / (2 · min_peaks_expected)` saturado en 1.0. |

\[ q_{1} = 0.45 \cdot \text{cov} + 0.35 \cdot \text{var\_score} + 0.20 \cdot \text{peak\_score} \]

## Componentes (v2)

`quality_gate_v2` agrega el `q_1` anterior con cuatro señales más, devolviendo el promedio acotado:

| Señal | Cálculo | Razón asociada |
|-------|---------|----------------|
| Blur | varianza del laplaciano normalizada | `PHOTO_BLURRY` cuando `< 0.20` |
| Glare | fracción de píxeles `> 245` | `PHOTO_GLARE` cuando `> 0.10` |
| Contraste | `std/255` | `PHOTO_LOW_CONTRAST` cuando `< 0.08` |
| Inclinación | grados del rectángulo de papel | `PHOTO_TILT` cuando `> 25°` |
| Cuadrícula | `confidence` de la calibración FFT | `PHOTO_NO_GRID_DETECTED` cuando faltan picos |

## Resultado

`GateResult.reportable` es `False` si el score cae bajo `score_min = 0.30` o si activa una razón crítica (`PHOTO_BLURRY`, `PHOTO_LOW_CONTRAST`, `SIGNAL_EXTRACTION_POOR`). En ese caso, [`analysis_pipeline`](../../apps/ml-api/app/services/analysis_pipeline.py) devuelve `status="red"` con `non_reportable_reason` localizado.

## Localización

Las razones son códigos estables (`PHOTO_BLURRY`, etc.) que el cliente puede traducir. El pipeline ya entrega copy en `es` y `en` desde [`analysis_pipeline._localize_reasons`](../../apps/ml-api/app/services/analysis_pipeline.py).

## Versionado y eval

Cualquier cambio de pesos o umbrales requiere bumping de `pipeline_version` en [`Settings`](../../apps/ml-api/app/core/config.py) y un reporte fresco con `make eval`. La doc de evaluación: [`docs/ml_eval.md`](../ml_eval.md).
