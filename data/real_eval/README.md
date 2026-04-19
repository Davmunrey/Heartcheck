# Real-photo evaluation set (gitignored content, public protocol)

This directory holds the labelled photos used to evaluate HeartScan against
real-world conditions (lighting, perspective, glare, paper variants). The
**images themselves are never committed** because they may contain identifiable
clinical context; only the `manifest.jsonl` template and protocol live here.

## Protocol (must be followed before adding any sample)

1. **Source.** Photos must come from one of:
   - Authors' own ECG strips with explicit written consent.
   - Open datasets that allow redistribution (cite license in `manifest.jsonl`).
   - Synthetic photos rendered through `app.eval.synth` (no consent needed).
2. **Anonymisation.** Strip every identifier before saving:
   - Crop or blur patient name, MRN, dates, hospital/clinic logos.
   - Remove EXIF (`exiftool -all= file.jpg`).
3. **Labelling.** Each sample carries a label in `{normal, arrhythmia, noise}`
   chosen by **two reviewers** (or one reviewer + a documented rationale).
   Disagreements demote the sample to `noise`.
4. **Storage.** Files live under `data/real_eval/images/`. Add to
   `manifest.jsonl` as one JSON object per line:

   ```json
   {"file": "real_001.jpg", "label": "normal",     "label_id": 0, "source": "internal", "consent": "signed-2026-04"}
   {"file": "real_002.jpg", "label": "arrhythmia", "label_id": 1, "source": "internal", "consent": "signed-2026-04"}
   ```

5. **Run the harness.**

   ```bash
   make eval SYNTH_DIR=data/real_eval EVAL_LABEL=real_v1
   ```

## Why a small set is still useful

Even 50 photos surface failure modes a synthetic generator misses (paper
texture, ink colour, ambient light, fingers in frame). A confidence interval
on F1 macro at N=50 with three classes is wide; treat results as directional
until the set grows.

## Privacy

All retention policies follow [`docs/PRIVACY.md`](../../docs/PRIVACY.md). When
the eval set leaves a development machine it must be encrypted at rest and the
list of recipients must be auditable.
