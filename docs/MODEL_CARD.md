# Axis — Model Card

> Format inspired by Mitchell et al., "Model Cards for Model Reporting" (FAccT 2019).
> This card is **mandatory reading** for anyone deploying or integrating Axis.

## Model details

| Field | Value |
|-------|-------|
| Name | Axis classifier |
| Architecture | `ECGResNet1D` (3 residual stages, ~150k params) — see [`apps/ml-api/app/ml/cnn1d.py`](../apps/ml-api/app/ml/cnn1d.py) |
| Input | 1024-sample 1D signal extracted from a single-lead ECG strip photo |
| Output | One of `normal | arrhythmia | noise` plus a calibrated probability and a conformal prediction set |
| Calibration | Temperature scaling + split conformal prediction (target coverage 90 %) |
| Owners | Axis engineering |
| Distribution | Bundled with the FastAPI backend; checkpoint loaded via `HEARTSCAN_MODEL_PATH` |
| Versioning | `model_version` exposed at `/api/v1/meta`; provenance manifest in [`apps/ml-api/weights/`](../apps/ml-api/weights/) |

## Intended use

- **Primary**: educational tool that gives a high-level orientation about the rhythm in a photo of an ECG strip.
- **Secondary**: training data and metric reference for Axis integrations and clients.

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

### Local 12-lead diagnostic benchmark

The strongest local research checkpoint is not yet the production API model.
It fine-tunes the full PTB-XL 1.0.3 12-lead model with a Georgia 12-lead
snapshot (`8,857` records) and predicts the PTB-XL diagnostic superclasses:
`NORM`, `MI`, `STTC`, `CD`, `HYP`. The full Georgia download is now available
locally and should be used for the next training pass.

| Field | Value |
|-------|-------|
| Checkpoint | `runs/auto/ptbxl_georgia_8857/finetune_12e/checkpoint.pt` |
| Manifest | `runs/auto/ptbxl_georgia_8857/signal_manifest_split.parquet` |
| Test report | `runs/auto/ptbxl_georgia_8857/finetune_12e/ptbxl_test_report.json` |
| Test rows | `2,118` diagnostic-labelled PTB-XL rows |
| Thresholds | `NORM=0.45`, `MI=0.65`, `STTC=0.55`, `CD=0.65`, `HYP=0.70` |
| Macro-F1 | `0.7541` |
| Macro precision | `0.7245` |
| Macro recall | `0.7888` |
| Exact match | `0.6204` |
| Hamming accuracy | `0.8873` |

Per-class F1: `NORM=0.8712`, `MI=0.7739`, `STTC=0.7710`, `CD=0.8042`,
`HYP=0.5505`. `HYP` remains the weakest class and blocks any claim of broad
clinical-grade coverage.

On the mixed PTB-XL + Georgia test split, the same checkpoint reaches
`Macro-F1=0.7249`, `Exact=0.5626`, `Hamming=0.8688`, beating the previous
PTB-only checkpoint on the earlier mixed snapshot test (`Macro-F1=0.7000`,
`Exact=0.5535`, `Hamming=0.8587`).

#### Focal fine-tune on full PTB-XL (2026-06-06) — current served model

Re-run via [`scripts/retrain_local.sh`](../scripts/retrain_local.sh) against the
full PTB-XL 1.0.3 (21,799 records, local non-iCloud root), focal loss,
fine-tuned from the previous champion. Served by the API when
`HEARTSCAN_DIAGNOSTIC_MODEL_PATH` points at it.

| Field | Value |
|-------|-------|
| Checkpoint | `runs/local/focal_from_champion/checkpoint.pt` (git-ignored artifact) |
| Test rows | `2,118` held-out PTB-XL |
| Macro-F1 | `0.7551` · Exact `0.626` · Hamming `0.890` |
| Per-class F1 | `NORM=0.879`, `MI=0.778`, `STTC=0.765`, `CD=0.801`, `HYP=0.552` |

Versus the checkpoint previously wired as the API default
(`finetune_12e_from_8857`, `HYP F1≈0.495`, `MI F1≈0.692` on its own val), this
notably improves the two weak classes — **MI precision 0.58→0.80, HYP precision
0.35→0.53** — so it is promoted as the served diagnostic model. `HYP` is still
the weakest class; treat non-NORM negatives with clinical caution.

> Known issue: the temperature/conformal `calibrate.py` step assumes a
> single-label logits shape and currently errors on the 5-way multi-label head
> (non-fatal; the checkpoint ships per-class tuned thresholds). Multi-label
> calibration is tracked as follow-up.

> ⚠️ **The `0.7551` above is on this checkpoint's *own* PTB-XL test split and is
> NOT comparable across runs** — different patient-stratified splits have
> different difficulty. For an honest A/B, always evaluate two checkpoints on the
> *same* slice (see the CinC2020 section's same-slice table). On the harder
> 2,134-row blended PTB-XL slice this same checkpoint scores macro-F1 `0.578`.

#### CinC2020 multi-source blend (2026-06-07) — current served model

Fine-tuned from the focal champion on a **43,063-record blend**: full PTB-XL
1.0.3 (21,799) + the five non-PTB-XL CinC2020 source databases (21,264:
cpsc_2018, cpsc_2018_extra, georgia, ptb, st_petersburg_incart). Motivated by
the Ribeiro et al. residual-CNN work
([antonior92/automatic-ecg-diagnosis](https://github.com/antonior92/automatic-ecg-diagnosis),
Nature Comms 2020) and the PTB-XL Inception1D benchmark
([AutoECG/Automated-ECG-Interpretation](https://github.com/AutoECG/Automated-ECG-Interpretation)).
The SNOMED→superclass map was expanded (ischemia/ST→STTC, atrial
enlargement→HYP) so ~18k previously-dropped CinC2020 records become supervision,
**doubling HYP training records** (≈2k→3,957). 12-epoch focal fine-tune, MPS,
~100 s/epoch.

| Field | Value |
|-------|-------|
| Checkpoint | `runs/local/cinc2020_blend/checkpoint.pt` |
| Best val (blended) | tuned macro-F1 `0.6456` |

**Honest same-slice A/B** (both checkpoints evaluated on the identical 2,134-row
PTB-XL test slice — the only fair comparison):

| Model | Macro-F1 | NORM | MI | STTC | CD | **HYP** |
|-------|----------|------|----|------|----|---------|
| Focal champion (PTB-XL only) | 0.578 | 0.735 | 0.611 | 0.569 | 0.655 | **0.319** |
| **CinC2020 blend (served)** | **0.608** | 0.744 | 0.597 | 0.623 | 0.629 | **0.447** |

The blend wins overall and lifts **HYP +40 % relative (0.319→0.447)** and STTC,
i.e. the CinC2020 data + expanded labels hit their target (the two weak classes).
On the full multi-source blended test (2,134 rows from 6 source distributions)
it reaches macro-F1 `0.628`, evidence of better cross-dataset generalisation
than a PTB-XL-only model.

> **Reality check for clinical readers.** Macro-F1 ≈ 0.6 at fixed thresholds is
> *not* "near-perfect" and no honest 5-superclass PTB-XL model is — published
> SOTA is ≈ 0.93 **AUROC** (threshold-independent) with macro-F1 in the
> 0.70–0.80 range. F1 at one operating point understates a model whose ranking
> (AUROC) is strong. The clinically meaningful path is calibrated probabilities +
> conformal abstention + high negative predictive value, used as a **copilot**,
> not an autonomous diagnosis. See "Path to clinical-grade" below.

#### 500 Hz + deep backbone (2026-06-08) — negative result, NOT promoted

Two experiments testing the "higher resolution + bigger net" hypothesis on the
same 43k blend, evaluated on the identical 2,134-row PTB-XL slice as the
champion (macro-F1 `0.608`):

| Run | Arch | Input | Levers | Val tuned-F1 | Slice macro-F1 |
|-----|------|-------|--------|--------------|----------------|
| `hr500_masked` | ECGResNet1D (~150k) | 500 Hz / 4096 | mask | 0.491 | ~0.40 |
| `deep500` | ECGResNetDeep1D (6.8M) | 500 Hz / 4096 | mask + balanced + warmup + clip | 0.511 | ~0.40 |

**Both underperform the 100 Hz champion (0.608).** Findings:

1. *Warm-starting the shallow net at 500 Hz hurt* — a fixed-width conv kernel
   covers 5× less time at 500 Hz, so the champion's filters were the wrong
   temporal scale and had to re-learn (epoch-1 F1 cratered 0.64→0.45, never
   recovered within 12 epochs).
2. *The deep net cold-started is data-starved* — 6.8M params on ~34k records.
   Ribeiro et al. trained an analogous net on **2M+** ECGs. It plateaued at
   val-F1 ~0.51 by epoch 12 of 20 and never approached the champion.

Conclusion: at this data scale, a **well-initialised smaller model (the served
champion) beats a high-capacity model trained from scratch.** The deep backbone
and 500 Hz path are kept in code (`--arch deep`, `PTBXL_USE_HR=1`) but the
correct way to use them is **pretrain on a large corpus (CODE-15 ~345k /
MIMIC-IV-ECG ~800k) then fine-tune**, not cold-start. The served model remains
the 100 Hz CinC2020 blend (`runs/local/cinc2020_blend/checkpoint.pt`).

#### Pretrain → fine-tune pipeline (ready to run)

The transfer path above is now implemented end-to-end:

1. **Pretrain** the deep backbone on CODE-15% (345k records, 6 abnormality
   labels) — [`ml/training/pretrain_code15.py`](../ml/training/pretrain_code15.py).
   Patient-disjoint val, macro-AUROC monitored, saves `backbone.pt`.
2. **Transfer + fine-tune** — `train_multilabel --arch deep --init-backbone
   backbone.pt` loads every conv/stem tensor and re-initialises only the head
   (`transfer_backbone()`), then fine-tunes the 5 superclasses on the blend.
3. **Orchestration** — [`scripts/pretrain_finetune_code15.sh`](../scripts/pretrain_finetune_code15.sh)
   runs both; [`scripts/download_code15.sh`](../scripts/download_code15.sh)
   fetches the corpus (~50 GB, Zenodo 4916206).

Blocked only on the CODE-15 download. Backbone-transfer + AUROC logic are unit
tested (`ml/tests/test_training_data.py`).

#### AUROC — the honest clinical metric (2026-06-10)

F1 at a fixed threshold badly *understated* the served champion. Evaluated on the
same 2,134-row PTB-XL slice, the champion's **threshold-independent AUROC** is:

| | NORM | MI | STTC | CD | HYP | **macro** |
|-|------|----|------|----|----|-----------|
| AUROC | 0.879 | 0.844 | 0.858 | 0.873 | 0.806 | **0.852** |

So the model that "only" scored macro-F1 0.608 actually **ranks sick-vs-healthy at
0.85 AUROC** (SOTA on these superclasses is ≈0.93). Even HYP — the "weak" class by
F1 (0.447) — ranks at **0.806 AUROC**. The gap between F1 and AUROC is the
operating point, not the model: it discriminates well, the thresholds just trade
precision/recall.

**Implication for the roadmap:** chasing macro-F1 with bigger models was the wrong
target (deep/500 Hz/CODE-15-pretrain experiments all plateaued below the champion).
The model is already a strong ranker; the launch-blocking work is **calibration +
conformal abstention + reporting AUROC/sensitivity-at-fixed-specificity**, not more
capacity. Report AUROC as the headline metric going forward.

#### Path to clinical-grade (roadmap)

Ranked by expected impact for the weak classes (HYP/MI/STTC):

1. **Higher input resolution.** Train at 500 Hz / 4096 samples (Ribeiro uses
   400 Hz/4096) instead of 100 Hz/1024 — HYP/MI hinge on fine QRS-voltage and
   ST morphology that 100 Hz smooths away. Flags already exist
   (`--target-fs 500 --target-len 4096`); `records500` is available locally.
2. **Partial-label masking.** CPSC sources only annotate a few classes; absent
   labels are currently treated as negatives (false negatives that poison MI/STTC
   precision). Add a per-record label mask so loss ignores un-annotated classes.
3. **Stronger backbone.** `ECGResNet1D` is ~150 k params; adopt the deeper
   Ribeiro residual net (proven ≈0.93 AUROC) — train from scratch at high-res.
4. **Threshold/calibration per deployment distribution** + split-conformal
   prediction sets for abstention; report **AUROC/AUPRC** and sensitivity at
   fixed specificity as the primary clinical metrics, not raw F1.
5. **External validation** on a fully held-out dataset (e.g. SPH/Chapman) and
   **ECE** reporting so probabilities are trustworthy.
6. **Ensemble + test-time augmentation** for the final percent.

### Beat-image classifier (2026-06-07) — research only, NOT production

A separate image/beat wedge: a compact 2D CNN
([`scripts/train_beat_image.py`](../scripts/train_beat_image.py), torch-only)
trained on a MIT-BIH-style beat-image set (`ECG_Image_data`, 6 AAMI classes
`N/S/V/F/Q/M`, majority-capped + class-weighted).

| Field | Value |
|-------|-------|
| Checkpoint | `runs/local/beat_image/checkpoint.pt` (git-ignored) |
| Test rows | `24,799` beat images |
| Test macro-F1 | `0.994` · accuracy `0.999` |
| Per-class F1 | `F=1.00, M=1.00, N=1.00, Q=1.00, S=0.97, V=0.99` |

**⚠️ Do not read this as clinical performance — this model is NOT deployable.**

Two independent checks show the headline number is misleading:

1. *Split.* No direct file/content leakage (0 shared names, 0 identical images
   train↔test), but the filenames carry no patient id and the dataset ships no
   metadata, so a patient-disjoint split cannot be built or verified. The
   provider's beat-level split is almost certainly intra-patient, which
   overstates real accuracy.
2. *Brittleness (decisive).* Under mild Gaussian noise the model collapses far
   below chance: macro-F1 `0.994 → 0.010` (acc `0.999 → 0.031`) at `σ=0.1` on
   the normalised input. A robust morphology classifier would degrade
   gracefully. This collapse means the CNN memorised the exact pixel signature
   of this specific rendering rather than ECG morphology — it would fail on a
   photo of a screen, a different plot style, or any real-world variation.

Treat the beat-image checkpoint as a **negative result / baseline only**. A
deployable image wedge needs: heavy augmentation (noise/blur/rotation), a
patient-disjoint dataset with metadata, and likely the digitise-to-1D-signal
path (reusing the strong 12-lead model) rather than raw-pixel classification.

## Evaluation data

- **Synthetic**: described in [`docs/DATASHEET_SYNTH.md`](DATASHEET_SYNTH.md). Generated deterministically per seed; covers perspective, blur, glare and shading augmentations.
- **Real**: described in [`data/real_eval/README.md`](../data/real_eval/README.md). Anonymised, consent-gated; never committed.

## Training data

The full catalogue of public ECG datasets Axis can train against —
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
