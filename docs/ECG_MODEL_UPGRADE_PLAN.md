# ECG Model Upgrade Plan

Heartcheck cannot claim 100% ECG diagnosis. ECG interpretation is multi-label,
uncertain, device-dependent, and clinically regulated. The production goal is
high-recall screening with calibrated uncertainty, abstention, and transparent
limitations.

## Current Model Tracks

### Screening Model

- Task: `normal`, `arrhythmia`, `noise`.
- Input: lead II, 100 Hz, 1024 samples.
- Best local contingency checkpoint:
  `runs/auto/ptbxl_tier1_enhanced/pretrain_5e/checkpoint.pt`.
- Test metrics on partial PTB-XL subset:
  - Accuracy: `0.7686`
  - Macro-F1: `0.6472`

### Diagnostic Multi-Label Model

- Task: PTB-XL diagnostic superclasses: `NORM`, `MI`, `STTC`, `CD`, `HYP`.
- Input: 12 leads, 100 Hz, 1024 samples.
- Best local checkpoint:
  `runs/auto/ptbxl_georgia_fullish/finetune_4e/checkpoint.pt`.
- Training set: full PTB-XL 1.0.3 plus an in-progress Georgia12 snapshot,
  deterministic manifest with `30,562` rows (`24,393` train, `3,085`
  validation, `3,084` test).
- Test metrics on full PTB-XL diagnostic rows (`n=2,118`) with
  validation-tuned thresholds:
  - Macro-F1: `0.7392`
  - Macro precision: `0.7297`
  - Macro recall: `0.7562`
  - Exact match: `0.6176`
  - Hamming accuracy: `0.8845`
- Test metrics on mixed PTB-XL + Georgia snapshot rows (`n=2,963`):
  - Macro-F1: `0.7192`
  - Exact match: `0.5754`
  - Hamming accuracy: `0.8708`

With per-class validation-tuned thresholds:

- Thresholds: `NORM=0.45`, `MI=0.75`, `STTC=0.60`, `CD=0.65`, `HYP=0.70`
- Per-class F1: `NORM=0.8706`, `MI=0.7490`, `STTC=0.7648`,
  `CD=0.7946`, `HYP=0.5172`

Focal loss is implemented as an option for long runs, but the short 2-epoch
local CPU probe did not beat the 3-epoch BCE checkpoint.

Previous partial-subset tuned checkpoint:
`runs/auto/ptbxl_multilabel_12lead/pretrain_3e/checkpoint.pt`
(`Macro-F1=0.6934`, `Exact=0.5728`, `Hamming=0.8646`). The full PTB-XL
5-epoch checkpoint reached `Macro-F1=0.7314`, `Exact=0.5836`,
`Hamming=0.8720`. The PTB-only 12-epoch augmented checkpoint reached
`Macro-F1=0.7348`, `Exact=0.6157`, `Hamming=0.8812`. The PTB-XL + Georgia
fine-tuned checkpoint is the current local benchmark, but it is not promoted
to the API until calibration, manifest emission, and API architecture
compatibility are completed.

## Next Quality Gates

1. Add per-class calibration and abstention policy for the full PTB-XL
   multi-label checkpoint.
2. Emit checkpoint manifest with dataset hashes, class list, thresholds, and
   architecture metadata.
3. Add API support for 12-lead multi-label output alongside the existing
   3-class screening output.
4. Add external validation datasets: Chapman/Shaoxing, CPSC/CinC, CODE-15%,
   SPH, and access-controlled MIMIC-IV-ECG where licensing allows.
5. Run longer GPU schedule with hyperparameter search and class-aware sampling,
   targeting weaker classes first (`HYP`, then `MI`).
6. Promote only checkpoints that pass locked test-set criteria.
7. Keep UI copy as screening/support, not diagnostic certainty.

## Promotion Criteria

Minimum for a serious beta checkpoint:

- Full PTB-XL train, val, test generated from deterministic manifest.
- Macro-F1 and per-class recall reported.
- Confusion/multi-label reports saved.
- Calibration report saved.
- No data/checkpoint committed to Git.
- Model card updated with known failures.
- API can load selected checkpoint with matching architecture metadata.

## Hard Limits

- No ECG model should promise 100% detection.
- Single-lead photo inference cannot equal 12-lead clinical ECG.
- Small classes such as `HYP` need more data/threshold tuning.
- Clinical use requires medical-device validation beyond repository training.
