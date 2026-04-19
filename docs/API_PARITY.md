# Paridad de respuestas: FastAPI vs `heartscan_ml`

HeartScan expone dos backends que pueden servir al mismo cliente web a través de `/api/v1/*`:

- **FastAPI principal** ([`apps/ml-api/app/api/routes/analyze.py`](../apps/ml-api/app/api/routes/analyze.py)) → respuesta validada contra el modelo Pydantic [`AnalysisResponse`](../apps/ml-api/app/schemas/analysis.py).
- **Paquete standalone** ([`ml/heartscan_ml/api.py`](../ml/heartscan_ml/api.py)) → respuesta construida en [`heartscan_ml/inference.build_full_response`](../ml/heartscan_ml/inference.py).

El SPA de Vite ([`web/src/App.jsx`](../web/src/App.jsx)) consume cualquiera de las dos. Esta tabla documenta los **campos críticos** y las **diferencias conocidas** para que los clientes puedan tratarlas de forma defensiva.

## Campos comunes

| Campo | FastAPI | ML | Notas |
|-------|---------|----|-------|
| `status` | `green | yellow | red` | `green | yellow | red | unknown` | ML añade `unknown` cuando `gr.reportable=false`. El SPA renderiza el badge gris para valores no esperados. |
| `bpm` | `float | null` | `float | null` | Mismo significado; `null` cuando no es trazable. |
| `message` | str (i18n) | str (es) | FastAPI cambia idioma por `Accept-Language`; ML responde en español hoy. |
| `confidence_score` | `[0, 1]` | `[0, 1]` | Idéntico. |
| `rhythm_regularity` | `regular | irregular | unknown` | igual | Idéntico. |
| `class_label` | `normal | arrhythmia | noise` | igual | Idéntico. |
| `disclaimer` | str (i18n) | str (es) | Mismo principio que `message`. |
| `pipeline_version` | `Settings.pipeline_version` | `heartscan_ml.PIPELINE_VERSION` | Pueden divergir entre versionados. |
| `model_version` | `loaded:<file>` o baseline | `<family>-trained` o baseline | Útil para auditar qué pesos respondieron. |
| `extraction_quality` | `[0, 1]` | `[0, 1]` | Idéntico. |
| `request_id` | UUID por petición | UUID por petición | Útil para trazabilidad. |
| `non_reportable_reason` | `dict | null` | igual | |
| `analysis_limit` | lista | lista | |
| `supported_findings` | lista | lista | |
| `measurement_basis` | str | `"ASSUMED_UNIFORM_TIME_AXIS"` | Mismo set de valores definido en docs/algorithms. |
| `education_topic_ids` | lista | lista | |

## Diferencias conocidas

1. **`status="unknown"` solo aparece en ML** cuando la salida no es reportable. El SPA debe tratar valores fuera del trío `green|yellow|red` como “sin clasificar” y mostrar `result.message` íntegro.
2. **i18n**: ML responde en español; FastAPI usa `Accept-Language` y cae a inglés por defecto. Si el cliente exige idioma específico, enviar la cabecera explícita.
3. **`raw_probs`** existe internamente en `heartscan_ml.inference.run_inference` pero no se promueve a la respuesta pública; no contar con él en clientes.
4. **Auth**: FastAPI exige Bearer JWT o `X-API-Key`; ML no autentica. En despliegues mixtos el WAF/proxy debe aplicar política equivalente.

## Estrategia recomendada

- Cuando la SPA o mobile dependan de un campo nuevo, añadirlo primero al modelo Pydantic FastAPI; replicar en ML para mantener paridad.
- Añadir un test de contrato (HTTP) en cada despliegue que invoque `/api/v1/meta` y, si hay imagen de ejemplo, `/api/v1/analyze`, comparando la presencia de los campos críticos arriba.
