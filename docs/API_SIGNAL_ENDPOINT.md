# 12-lead diagnostic endpoint (`/api/v1/analyze/signal`)

The **signal wedge** of the product: a clinical-copilot path that runs the
strong 12-lead `ECGResNet1D` model over a raw ECG signal and returns calibrated
multi-label superclass findings. Distinct from `POST /api/v1/analyze`, which is
the single-lead **photo** screening path (3-class normal/arrhythmia/noise).

## Contract

```
POST /api/v1/analyze/signal
Auth:    Bearer <Clerk JWT>  OR  X-API-Key: <key>  (when legacy key enabled)
Body:    multipart/form-data
  - file              (.npy  array (12,N) or (N,12)  |  .csv  12 cols or 12 rows)
  - sampling_rate_hz  (int, default 500; model resamples to its training rate)
```

### Response (`200`)

```jsonc
{
  "abnormal": false,                       // any non-NORM superclass flagged positive
  "findings": [
    { "code": "NORM", "label": "Normal ECG", "probability": 0.98,
      "positive": true, "threshold": 0.45 },
    { "code": "MI",   "label": "Myocardial infarction (possible)", ... },
    { "code": "STTC", ... }, { "code": "CD", ... }, { "code": "HYP", ... }
  ],
  "n_leads": 12,
  "sampling_rate_hz": 100,
  "model_version": "ecg-resnet1d-ptbxl-multilabel-0.1.0",
  "pipeline_version": "0.1.0",
  "request_id": "…",
  "disclaimer": "HeartScan is a clinical decision-support copilot …",
  "analysis_limit": ["12-lead diagnostic superclasses only …", …]
}
```

`positive` uses the **per-class calibrated threshold** shipped inside the
checkpoint (tuned on a validation split), not a flat 0.5. The superclasses are
the PTB-XL diagnostic superclasses: `NORM, MI, STTC, CD, HYP`.

### Errors

| Status | `error_code` | When |
|--------|--------------|------|
| 401 | `AUTH_REQUIRED` | No Bearer / valid `X-API-Key`. |
| 413 | `PAYLOAD_TOO_LARGE` | Upload exceeds `HEARTSCAN_MAX_UPLOAD_BYTES`. |
| 415 | `UNSUPPORTED_FORMAT` | Not a `.npy` or comma-separated `.csv`. |
| 422 | `BAD_SHAPE` / `BAD_LEADS` / `BAD_SAMPLE_RATE` / `EMPTY_PAYLOAD` | Malformed signal. |
| 503 | `MODEL_UNAVAILABLE` | No diagnostic checkpoint configured. |

## Configuration

- `HEARTSCAN_DIAGNOSTIC_MODEL_PATH` — path to the checkpoint. If unset, the
  service auto-discovers from `runs/auto/ptbxl_georgia_full/.../checkpoint.pt`
  then the Chapman-blend checkpoint.
- The model is **lazy-loaded** on first use so the API binds immediately on cold
  start. `GET /api/v1/meta` reports `diagnostic_model.loaded` and `version`.

## Implementation

- Service: [`apps/ml-api/app/services/diagnostic_inference.py`](../apps/ml-api/app/services/diagnostic_inference.py)
  — safe `torch.load(weights_only=True)`, preprocessing in lockstep with
  [`ml/training/data.py`](../ml/training/data.py) (`PTBXLDiagnosticDataset`).
- Route: [`apps/ml-api/app/api/routes/analyze_signal.py`](../apps/ml-api/app/api/routes/analyze_signal.py)
- Schema: [`apps/ml-api/app/schemas/diagnostic.py`](../apps/ml-api/app/schemas/diagnostic.py)

## Known limitation

The current champion (PTB-XL + Georgia) under-detects subtle **MI** and **HYP**
(see [`MODEL_CARD.md`](MODEL_CARD.md)). A focal-loss fine-tune on the
Chapman-augmented blend is the planned improvement; until promoted, treat
non-NORM negatives with appropriate clinical caution.

## cURL example

```bash
curl -H "X-API-Key: $HEARTSCAN_API_KEY" \
  -F "file=@ecg.npy" -F "sampling_rate_hz=100" \
  http://localhost:8000/api/v1/analyze/signal
```
