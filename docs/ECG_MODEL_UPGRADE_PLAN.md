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
- Checkpoint:
  `runs/auto/ptbxl_multilabel_12lead/pretrain_3e/checkpoint.pt`.
- Test metrics on partial PTB-XL subset:
  - Macro-F1: `0.6787`
  - Macro precision: `0.6005`
  - Macro recall: `0.8059`
  - Exact match: `0.4817`
  - Hamming accuracy: `0.8317`

With per-class validation-tuned thresholds:

- Thresholds: `NORM=0.45`, `MI=0.75`, `STTC=0.60`, `CD=0.65`, `HYP=0.60`
- Test Macro-F1: `0.6934`
- Test exact match: `0.5728`
- Test hamming accuracy: `0.8646`

Focal loss is implemented as an option for long runs, but the short 2-epoch
local CPU probe did not beat the 3-epoch BCE checkpoint.

## Next Quality Gates

1. Complete full PTB-XL ZIP extraction, regenerate full manifest/splits.
2. Train full 12-lead multi-label model for longer schedule on GPU.
3. Add threshold tuning per class on validation set.
4. Add external validation datasets: Chapman/Shaoxing, CPSC/CinC, CODE-15%, SPH.
5. Add per-class calibration and abstention policy.
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
