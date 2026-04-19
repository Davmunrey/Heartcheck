# Label harmonisation — public ECG datasets → HeartScan classes

The HeartScan classifier exposes three classes: `normal | arrhythmia | noise`.
Every public dataset HeartScan trains against uses its own coding scheme
(SCP-ECG, SNOMED-CT, ad-hoc challenge labels). This document is the
**single source of truth** for how those codes collapse into the three
HeartScan classes.

The runtime mappings live in [`ml/datasets/labels.py`](../ml/datasets/labels.py)
so they are both auditable and tested.

## Universal rules

1. **Multi-label "arrhythmia wins."** A record carrying *any* arrhythmia
   code is labelled `arrhythmia`, even if it also has `NORM` / `SR`. The
   product is informational; we err on the side of caution.
2. **`noise` is reserved** for records explicitly tagged as bad signal,
   plus records that match no rule (defensive default).
3. **Conduction blocks and ischaemia codes count as `arrhythmia`** for the
   HeartScan label space because the user-facing message ("consult a
   clinician") applies the same way.
4. **Records without a label** become `noise`. They are not silently
   dropped, so the loader's coverage is auditable.

## Dataset-by-dataset mapping

### PTB-XL (SCP-ECG)

`ml/datasets/labels.py` → `map_ptbxl_codes`.

| HeartScan | SCP codes |
|-----------|-----------|
| `normal` | `NORM`, `SR` |
| `arrhythmia` | Supraventricular: `AFIB`, `AFLT`, `PSVT`, `PAC`, `STACH`, `SBRAD`, `SARRH`, `SVTAC` · Ventricular: `PVC`, `VTAC`, `VFL`, `BIGU`, `TRIGU` · Conduction: `1AVB`, `2AVB`, `3AVB`, `LBBB`, `RBBB`, `CLBBB`, `CRBBB`, `ILBBB`, `IRBBB`, `WPW`, `LPFB`, `LAFB` · Ischaemia/MI: `AMI`, `IMI`, `LMI`, `PMI`, `ASMI`, `ALMI`, `ILMI`, `IPMI`, `IPLMI`, `ISC_`, `ISCAL`, `ISCAS`, `ISCIN`, `ISCIL`, `ISCAN`, `ISCLA` |
| `noise` | All other codes (defensive default) |

### Chapman / Shaoxing / Ningbo (SNOMED-CT subset)

`map_chapman_codes`.

| HeartScan | SNOMED codes |
|-----------|--------------|
| `normal` | `426783006` (sinus rhythm) |
| `arrhythmia` | `164889003` AF · `164890007` AFL · `426761007` SVT · `164909002` LBBB · `59118001` RBBB · `164931005` ST elevation · `164934002` T-wave abnormal · `39732003` LAD · `164873001` LVH · `270492004` 1° AVB · `284470004` PAC · `427172004` PVC · `55827005` LVH · `428750005` non-specific ST-T · `63593006` SVPB · `17338001` VPB · `164912004` P-wave abnormal · `164917005` Q-wave abnormal |
| `noise` | All other codes |

### CinC 2017 (single letter)

`map_cinc2017`.

| HeartScan | CinC label |
|-----------|------------|
| `normal` | `N` |
| `arrhythmia` | `A` (atrial fibrillation), `O` (other rhythm) |
| `noise` | `~` |

### CODE-15% (six binary indicator columns)

`map_code15`.

| HeartScan | CODE-15 columns |
|-----------|-----------------|
| `normal` | All six columns equal `0` |
| `arrhythmia` | Any of `1dAVb`, `RBBB`, `LBBB`, `SB`, `ST`, `AF` equals `1` |
| `noise` | (Unused — every record carries the six fields.) |

### Georgia 12-lead (CinC 2020 SNOMED subset)

Reuses `map_chapman_codes` because the CinC 2020 label space is the same
SNOMED-CT subset. The Georgia loader extracts `# Dx:` lines from the WFDB
header and feeds them to the same mapping.

### SPH — Shandong Provincial Hospital (AHA / ACC / HRS strings)

`map_sph`.

| HeartScan | SPH statement prefix |
|-----------|---------------------|
| `normal` | `AECG: Normal ECG` |
| `arrhythmia` | `AECG: Atrial fibrillation`, `AECG: Atrial flutter`, `AECG: Atrial premature complex`, `AECG: Ventricular premature complex`, `AECG: Sinus tachycardia`, `AECG: Sinus bradycardia`, `AECG: First/Second/Third degree AV block`, `AECG: Right/Left bundle branch block`, `AECG: Left anterior/posterior fascicular block`, `AECG: Wolff-Parkinson-White` |
| `noise` | All other statements |

### MIMIC-IV-ECG (free-text reports)

The dataset ships free-text reports rather than coded statements. The
default loader returns `noise` for every record so the operator is forced
to write an NLP step (rule-based extraction or a fine-tuned model) before
including MIMIC-IV-ECG in training. Document the chosen mapping under a
new heading here when that step lands.

### LUDB / MIT-BIH

LUDB is for delineation; every record is labelled `normal` (placeholder)
and consumed by the segmentation pipeline rather than the classifier.
MIT-BIH Arrhythmia records are labelled `arrhythmia` at record level
because the cohort is curated for arrhythmia detection.

### Icentia11k (NON-COMMERCIAL)

Loader labels every record as `arrhythmia` because the cohort comes from
a Holter screening population. Excluded from any commercial build.

## Coverage report

After running `python -m ml.datasets.cli manifest`, count rows per
`(source_dataset, label)` to confirm no class is starved. A healthy
mixed-source manifest should keep each HeartScan class at ≥ 10 % of total
samples; oversample if needed via the trainer's `WeightedRandomSampler`.

## Audit / change process

1. Open a PR that edits both `ml/datasets/labels.py` and this document
   together. Otherwise CI rejects the change.
2. Bump `pipeline_version` in `apps/ml-api/app/core/config.py` so downstream
   manifests can detect the schema change.
3. Re-run `make eval` and attach the report.
