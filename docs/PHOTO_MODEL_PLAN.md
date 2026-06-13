# Axis — Photo model: training & workflow plan

> Strategy for replacing the heuristic photo path with a trained model.
> Snapshot 2026-06-13. Indexed in [`MASTER_DOCS.md`](MASTER_DOCS.md).
> Related: [`MODEL_CARD.md`](MODEL_CARD.md), [`AUTONOMOUS_TRAINING.md`](AUTONOMOUS_TRAINING.md),
> [`ECG_MODEL_UPGRADE_PLAN.md`](ECG_MODEL_UPGRADE_PLAN.md), [`DATASHEET_TRAINING.md`](DATASHEET_TRAINING.md).

## Where we are

| | Photo (`/api/v1/analyze`) | Signal (`/api/v1/analyze/signal`) |
|---|---|---|
| Input | Phone photo of a 1-lead strip | 12-lead `.npy`/`.csv` |
| Pipeline | image → grid-suppress → **extract 1D** → **heuristic** (RR/regularity) | 12-lead → ResNet1D |
| Model | **none** — `checkpoint_loaded:false`, `*-untrained`; uses `heuristic_classify` | `ecg_27class`, AUROC ~0.88 (served) |
| Classes | 3: `normal / arrhythmia / noise` | 27 conditions / 5 superclasses |
| UI today | labeled "cribado heurístico" (honest) | "copiloto calibrado" |

**The photo path is the weak wedge** (deliberately de-emphasized, signal-first).
Goal here is modest and concrete: **beat the heuristic with a calibrated 3-class
screen**, not turn a single-lead photo into a diagnosis. The single-lead photo
has a hard accuracy ceiling vs a 12-lead signal — keep the "screening, not
diagnostic" framing regardless of metrics.

## The right approach: train on images *through the extractor*

The repo already has the correct idea in [`ml/training/finetune_image.py`](../ml/training/finetune_image.py):
fine-tune `ECGResNet1D` on ECG **images routed through Axis's own extraction
pipeline**, so the model trains on the *same noisy 1D signal it sees at
inference* (closes the foto↔señal distribution gap). The served model stays a
CNN1D (`HEARTSCAN_MODEL_PATH` → `inference.load_model`); the photo pipeline keeps
extracting 1D and just swaps the heuristic for the trained classifier.

**Rejected alternative — `train_beat_image.py`** (direct image CNN on
`~/Downloads/ECG_Image_data`): it's **beat-level** (single-beat crops, 6 AAMI
classes N/S/V/F/Q/M) not strip-level 3-class, and the prior 0.994 F1 was
**inflated by intra-patient leakage**. Wrong granularity + leaky eval → not the
serving path. (Keep it as research only.)

## Data

| Dataset | What | Use |
|---|---|---|
| `ptb_xl_image_17k` | PTB-XL rendered as 12-lead images, superclass labels | **primary** — maps to the 3-class strip task via the extractor |
| PTB-XL signals (`~/Downloads/ptb-xl-...-1.0.3`) | clean 12-lead signals | render → image → extract, or synth-photo augmentation |
| `ECG_Image_data` (1.1 GB, 124k beats) | beat crops, 6 AAMI classes | research/aux only (granularity mismatch) |

**Label mapping** to `{0:normal, 1:arrhythmia, 2:noise}`: derive from PTB-XL
superclasses (NORM→normal; rhythm/conduction abnormals→arrhythmia) + quality-gate
failures→noise. Document the exact map in the model card.

**Two non-negotiables (lessons already learned):**
1. **Patient-disjoint splits** — split by patient id, never by image. The 0.994
   beat-image F1 was leakage. Use `ml.datasets.splits` (patient-stratified).
2. **External validation** — final metric on a source/patient never seen in
   training. Report **AUROC** (+ per-class), not raw F1 on an easy slice
   (cross-split F1 is not comparable — see MODEL_CARD methodology note).

## Training workflow (commands exist)

```
1. Manifest   python -m ml.datasets.cli manifest --datasets ptb_xl_image_17k \
                 --out data/manifests/photo.parquet            # file_path,label_id{0,1,2},split
2. Split      python -m ml.datasets.splits --manifest ... --out photo_split.parquet   # patient-disjoint
3. Train      python -m ml.training.finetune_image --manifest photo_split.parquet \
                 --init-checkpoint <signal champion> --out runs/local/photo_ft --loss focal
4. Calibrate  temperature + per-class thresholds (val); conformal abstention set
5. Eval       python -m ml.training.evaluate_checkpoint  # patient-disjoint test + external; AUROC
6. Promote    if it beats the heuristic + champion on the SAME slice →
                 set HEARTSCAN_MODEL_PATH=runs/local/photo_ft/checkpoint.pt
```

Autonomous variant (idempotent, cron/CI): `scripts/train_autonomous.sh`
(download → train → calibrate → eval → promote-if-better). CI quality gate:
`.github/workflows/eval-gate.yml`. See [`AUTONOMOUS_TRAINING.md`](AUTONOMOUS_TRAINING.md).

## Serving & app integration (small, after a checkpoint exists)

- Set `HEARTSCAN_MODEL_PATH` (Render secret + local `.env`). `inference.load_model`
  picks it up; `/api/v1/meta` flips `checkpoint_loaded:true` + real `model_version`.
- The photo pipeline already calls the classifier after extraction — no code
  change to swap heuristic→model beyond loading weights.
- **Safety gates** (keep, even with a model): quality-gate abstention (blur/glare/
  no-grid → don't classify), conformal abstention (low confidence → "no
  concluyente"), and the `extraction_quality` already in the response.
- **UI**: when a validated model is served, the analyze "cribado heurístico" tag
  → "modelo entrenado (cribado 1 derivación)"; keep it below the signal copilot.
  Gate this on the eval passing, not just on a checkpoint existing.

## Success criteria

- Beats the heuristic on a **patient-disjoint** test (macro-AUROC + per-class).
- Calibrated (ECE low) + abstains on low-quality input rather than guessing.
- Honest ceiling: a 1-lead photo screen, not a diagnosis. If it can't clear a
  safety bar, **keep the heuristic + the "screening" label** rather than ship a
  confident-but-wrong model.

## What's autonomous vs needs you

- **Scaffolded ✓ (no GPU):** [`scripts/train_photo.sh`](../scripts/train_photo.sh) —
  one-shot, idempotent: (optional) download → manifest (3-class via
  `map_ptbxl_codes`) → **patient-disjoint split** → `finetune_image` →
  `evaluate_checkpoint` (test) → promote hint. Every command + flag validated
  against the live CLIs; runnable when data+compute are ready.
  ```bash
  DOWNLOAD=1 EPOCHS=8 PRETRAINED=runs/local/full27/checkpoint.pt ./scripts/train_photo.sh
  ```
- **Needs you / compute:** the dataset downloads (`ecg_image_database` ~60 GB,
  `ptb_xl_image_17k` ~20 GB — both CC BY 4.0, PhysioNet/zip), the GPU training
  run, and the promote decision (review `eval_test.json` AUROC).

## Recommendation

Time-box it. The signal model (AUROC 0.88, the real product) deserves the next
heavy ML investment (CODE-15/MIMIC pretrain → ≥0.92). For the photo: one
`finetune_image.py` pass with a patient-disjoint split to **credibly beat the
heuristic**, served behind the existing safety gates, kept explicitly secondary.
Don't let the photo wedge consume the ML budget.
