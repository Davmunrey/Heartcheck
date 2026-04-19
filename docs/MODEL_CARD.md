# HeartScan — Model Card

> Format inspired by Mitchell et al., "Model Cards for Model Reporting" (FAccT 2019).
> This card is **mandatory reading** for anyone deploying or integrating HeartScan.

## Model details

| Field | Value |
|-------|-------|
| Name | HeartScan classifier |
| Architecture | `ECGResNet1D` (3 residual stages, ~150k params) — see [`apps/ml-api/app/ml/cnn1d.py`](../apps/ml-api/app/ml/cnn1d.py) |
| Input | 1024-sample 1D signal extracted from a single-lead ECG strip photo |
| Output | One of `normal | arrhythmia | noise` plus a calibrated probability and a conformal prediction set |
| Calibration | Temperature scaling + split conformal prediction (target coverage 90 %) |
| Owners | HeartScan engineering |
| Distribution | Bundled with the FastAPI backend; checkpoint loaded via `HEARTSCAN_MODEL_PATH` |
| Versioning | `model_version` exposed at `/api/v1/meta`; provenance manifest in [`apps/ml-api/weights/`](../apps/ml-api/weights/) |

## Intended use

- **Primary**: educational tool that gives a high-level orientation about the rhythm in a photo of an ECG strip.
- **Secondary**: training data and metric reference for HeartScan integrations and clients.

## Out-of-scope use

- Diagnosis or treatment decisions.
- Emergency triage.
- Population screening for asymptomatic users.
- Replacing a 12-lead clinical ECG.

See [`docs/WHEN_NOT_TO_USE.md`](WHEN_NOT_TO_USE.md) for the full list.

## Factors

- **Photo quality**: lighting, focus, glare, perspective, paper variant.
- **Patient demographics**: not modelled — the system has *no* demographic input. Performance may vary across cohorts in ways the current eval set cannot detect.
- **Lead and paper convention**: assumed single-lead, paper at 25 mm/s and ~10 mm/mV. Anything else degrades BPM accuracy.

## Metrics

Reported automatically by `make eval` on the deterministic synthetic set ([`apps/ml-api/app/eval/synth.py`](../apps/ml-api/app/eval/synth.py)). Real-photo metrics live in [`data/real_eval/README.md`](../data/real_eval/README.md). The current numbers are placeholders until a checkpoint trained against the v2 pipeline ships:

| Set | Accuracy | F1 macro | ECE | p95 latency (ms) |
|-----|----------|----------|-----|------------------|
| `synth_v1` (baseline, untrained) | 0.33 | 0.17 | 0.22 | ~140 |
| `synth_v1` (target trained) | ≥ 0.85 | ≥ 0.80 | ≤ 0.06 | ≤ 200 |
| `real_v1` (target) | ≥ 0.75 | ≥ 0.70 | ≤ 0.10 | ≤ 250 |

A release whose F1 macro regresses by more than 2 points or whose ECE worsens by more than 0.05 fails the CI gate (see [`Makefile`](../Makefile) `eval-gate`).

## Evaluation data

- **Synthetic**: described in [`docs/DATASHEET_SYNTH.md`](DATASHEET_SYNTH.md). Generated deterministically per seed; covers perspective, blur, glare and shading augmentations.
- **Real**: described in [`data/real_eval/README.md`](../data/real_eval/README.md). Anonymised, consent-gated; never committed.

## Training data

The full catalogue of public ECG datasets HeartScan can train against —
plus their licence terms and commercial-use posture — lives in
[`docs/DATASHEET_TRAINING.md`](DATASHEET_TRAINING.md). Every dataset is
declared in the [`ml/datasets`](../ml/datasets/) registry so the manifest
emitter can record the exact version + license of each component.

When real training is performed, document the dataset version in the
checkpoint manifest ([`apps/ml-api/app/ml/manifest.py`](../apps/ml-api/app/ml/manifest.py)).
The current shipped baseline is **untrained** (random init); inference
falls back to the rule-based heuristic defined in
[`apps/ml-api/app/services/heuristic_classify.py`](../apps/ml-api/app/services/heuristic_classify.py).

The recommended training pipeline is:

```bash
# Tier 1 (commercial-safe, ~6 GB):
scripts/download_datasets_tier1.sh

# Build manifest + splits:
apps/ml-api/.venv/bin/python -m ml.datasets.cli manifest \
  --root data/raw \
  --datasets ptb_xl chapman_shaoxing cinc2017 \
  --out data/manifests/tier1.parquet
apps/ml-api/.venv/bin/python -m ml.datasets.splits \
  --manifest data/manifests/tier1.parquet \
  --out data/manifests/tier1_split.parquet

# Pretrain (CPU OK for tier 1; GPU recommended):
apps/ml-api/.venv/bin/python -m ml.training.pretrain \
  --manifest data/manifests/tier1_split.parquet \
  --out runs/pretrain_v1 --epochs 10

# Calibrate + ship:
apps/ml-api/.venv/bin/python -m ml.training.calibrate \
  --logits runs/pretrain_v1/val_logits.npz \
  --checkpoint runs/pretrain_v1/checkpoint.pt
apps/ml-api/.venv/bin/python -m ml.training.emit_manifest \
  --checkpoint runs/pretrain_v1/checkpoint.pt \
  --training-summary runs/pretrain_v1/training_summary.json \
  --calibration runs/pretrain_v1/calibration.json \
  --datasets ptb_xl chapman_shaoxing cinc2017 \
  --model-version ecg-resnet1d-1.0.0
```

Add the image fine-tune step ([`ml/training/finetune_image.py`](../ml/training/finetune_image.py))
once the image datasets are downloaded with
[`scripts/download_datasets_images.sh`](../scripts/download_datasets_images.sh).

## Quantitative analyses

The harness emits `eval/reports/<timestamp>_<label>.{json,html}` with:

- per-class F1 and confusion matrix;
- ECE, Brier and AUROC for the "is the model right?" detector;
- abstention rate and latency p50/p95/mean.

These should be inspected before promoting a checkpoint. Plot drift over time using the Prometheus metrics in [`apps/ml-api/app/core/metrics.py`](../apps/ml-api/app/core/metrics.py) (see [`docs/prometheus/alerts.example.yml`](prometheus/alerts.example.yml)).

## Ethical considerations

- **False reassurance.** A `green` result on a tight clinical question can mislead an anxious user. Disclaimers are mandatory in every surface that renders the result.
- **False alarm.** A `red` result without context can cause unnecessary distress. Guardrails in [`apps/ml-api/app/services/analysis_pipeline.py`](../apps/ml-api/app/services/analysis_pipeline.py) downgrade arrhythmia predictions whose calibrated confidence falls below 0.6.
- **Demographic blind spots.** Until the eval set has demographic metadata, performance subgroup gaps are unknown.

## Caveats and recommendations

- Combine with [`docs/WHEN_NOT_TO_USE.md`](WHEN_NOT_TO_USE.md) at every UI surface.
- Re-run `make eval` whenever any of the following changes:
  - any module under `apps/ml-api/app/services/` or `apps/ml-api/app/ml/`;
  - the model checkpoint;
  - the synthetic generator (`SynthConfig` defaults).
- File regressions as plan-v2 todos and link them to a fix or an explicit acceptance.
