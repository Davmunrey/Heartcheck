# Datasheet — Synthetic ECG-photo set (`synth_v1`)

> Format inspired by Gebru et al., "Datasheets for Datasets" (2018).

## Motivation

`synth_v1` exists so the eval harness ([`apps/ml-api/app/eval/cli.py`](../apps/ml-api/app/eval/cli.py)) can run on any developer machine and in CI without depending on a clinical dataset. It is **not** a substitute for real photos; it stress-tests the OpenCV pipeline and the calibration logic.

## Composition

- 3 classes: `normal`, `arrhythmia`, `noise`. See [`apps/ml-api/app/eval/synth.py`](../apps/ml-api/app/eval/synth.py) `CLASS_NAMES`.
- Default size: 20 images per class (60 total) — tunable via `--n`.
- One PNG per sample (`800x240` grayscale rendered on a paper-style grid) plus a `manifest.jsonl` mapping `(file → label, label_id)`.
- All samples are deterministic given `--seed` (default `1234`).

## Collection process

Generated programmatically:

1. Sample a per-class waveform template (Gaussian beats for normal/arrhythmia, pure noise for noise).
2. Draw fine + bold grid lines.
3. Draw the trace.
4. Apply random perspective skew, shading, optional glare.
5. Apply blur and additive noise.

No real patient data, no consent considerations.

## Preprocessing / labeling

Labels come from the generator; no human in the loop. Class boundaries are based on the template shape; a generated `arrhythmia` sample is always labelled `arrhythmia` even if a human reviewer might disagree on subtle cases. This is deliberate — synthetic ground truth is unambiguous by construction.

## Uses

- Continuous integration (`make eval`).
- Smoke testing of the analysis pipeline after refactors.
- Unit tests when needed.

It must **not** be used as the sole evidence for model claims. The ratio of synthetic-only to real-photo evaluation is reported in the model card.

## Distribution

The generator ships in the repo. Generated images and `manifest.jsonl` are excluded from version control via [`.gitignore`](../.gitignore).

## Maintenance

- Owners: HeartScan engineering.
- Bump `synth_v1` to `synth_v2` when augmentation defaults change in a way that affects metrics. The current numbers in `eval/baselines/` are tied to the version and should be regenerated atomically with the change.
