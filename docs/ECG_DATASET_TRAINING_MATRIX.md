# ECG Dataset Training Matrix

Goal: clinical-assist ECG models with explicit dataset provenance.

| Dataset | Status | Use | Blocker |
| --- | --- | --- | --- |
| PTB-XL 1.0.3 | Partial local, full ZIP downloading | 12-lead diagnostic multi-label + screening | Full ZIP still incomplete |
| MIT-BIH 1.0.0 | Open, downloading via PhysioNet | Arrhythmia benchmark + screening robustness | Small dataset, record-level labels are coarse |
| MIMIC-IV-ECG 1.0 | Restricted | Large-scale 12-lead pretraining + report-derived labels | PhysioNet credentialed access + CITI + label harmonization |
| MEETI Zenodo v1 | Open CC BY 4.0, downloading | Multimodal image/text/features training | 3.3 GB ZIP; labels need careful report harmonization |
| Full MEETI Hugging Face | Restricted/large derivative | Full multimodal pretraining | Depends on MIMIC-IV-ECG lineage/access review |
| CODE-II | Not locally available | Future large-scale external training/validation | Public paper/link is not enough; need dataset access + license |

## Current Legal Training Path

1. Train PTB-XL partial 12-lead multi-label.
2. Add MIT-BIH once download completes.
3. Add MEETI Zenodo for image/text screening once downloaded/extracted.
4. Rebuild combined screening manifest: `ptb_xl mit_bih meeti`.
5. Keep diagnostic multi-label restricted to datasets with diagnostic class metadata.
6. Do not train on MIMIC/full-MEETI/CODE-II until credentials/data/license are present.

## MIMIC/MEETI Readiness Gate

Before training:

- PhysioNet credentialed access approved.
- CITI training complete.
- Data use agreement accepted.
- `data/raw/mimic_iv_ecg/` present.
- Free-text reports harmonized into labels.
- `.harmonized` sentinel placed or `MIMIC_IV_ECG_HARMONIZED=1`.

## Promotion Rule

No checkpoint promotion without:

- Dataset list.
- License notes.
- Train/val/test split.
- Per-class metrics.
- Calibration/thresholds.
- Model card update.
