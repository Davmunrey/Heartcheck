# Label harmonisation — public ECG datasets → Axis classes

The Axis classifier exposes three classes: `normal | arrhythmia | noise`.
Every public dataset Axis trains against uses its own coding scheme
(SCP-ECG, SNOMED-CT, ad-hoc challenge labels). This document is the
**single source of truth** for how those codes collapse into the three
Axis classes.

The runtime mappings live in [`ml/datasets/labels.py`](../ml/datasets/labels.py)
so they are both auditable and tested.

## Universal rules

1. **Multi-label "arrhythmia wins."** A record carrying *any* arrhythmia
   code is labelled `arrhythmia`, even if it also has `NORM` / `SR`. The
   product is informational; we err on the side of caution.
2. **`noise` is reserved** for records explicitly tagged as bad signal,
   plus records that match no rule (defensive default).
3. **Conduction blocks and ischaemia codes count as `arrhythmia`** for the
   Axis label space because the user-facing message ("consult a
   clinician") applies the same way.
4. **Records without a label** become `noise`. They are not silently
   dropped, so the loader's coverage is auditable.

## Dataset-by-dataset mapping

### PTB-XL (SCP-ECG)

`ml/datasets/labels.py` → `map_ptbxl_codes`.

| Axis | SCP codes |
|-----------|-----------|
| `normal` | `NORM`, `SR` |
| `arrhythmia` | Supraventricular: `AFIB`, `AFLT`, `PSVT`, `PAC`, `STACH`, `SBRAD`, `SARRH`, `SVTAC` · Ventricular: `PVC`, `VTAC`, `VFL`, `BIGU`, `TRIGU` · Conduction: `1AVB`, `2AVB`, `3AVB`, `LBBB`, `RBBB`, `CLBBB`, `CRBBB`, `ILBBB`, `IRBBB`, `WPW`, `LPFB`, `LAFB` · Ischaemia/MI: `AMI`, `IMI`, `LMI`, `PMI`, `ASMI`, `ALMI`, `ILMI`, `IPMI`, `IPLMI`, `ISC_`, `ISCAL`, `ISCAS`, `ISCIN`, `ISCIL`, `ISCAN`, `ISCLA` |
| `noise` | All other codes (defensive default) |

### Chapman / Shaoxing / Ningbo (SNOMED-CT subset)

`map_chapman_codes`.

| Axis | SNOMED codes |
|-----------|--------------|
| `normal` | `426783006` (sinus rhythm) |
| `arrhythmia` | `164889003` AF · `164890007` AFL · `426761007` SVT · `164909002` LBBB · `59118001` RBBB · `164931005` ST elevation · `164934002` T-wave abnormal · `39732003` LAD · `164873001` LVH · `270492004` 1° AVB · `284470004` PAC · `427172004` PVC · `55827005` LVH · `428750005` non-specific ST-T · `63593006` SVPB · `17338001` VPB · `164912004` P-wave abnormal · `164917005` Q-wave abnormal |
| `noise` | All other codes |

### CinC 2017 (single letter)

`map_cinc2017`.

| Axis | CinC label |
|-----------|------------|
| `normal` | `N` |
| `arrhythmia` | `A` (atrial fibrillation), `O` (other rhythm) |
| `noise` | `~` |

### CODE-15% (six binary indicator columns)

`map_code15`.

| Axis | CODE-15 columns |
|-----------|-----------------|
| `normal` | All six columns equal `0` |
| `arrhythmia` | Any of `1dAVb`, `RBBB`, `LBBB`, `SB`, `ST`, `AF` equals `1` |
| `noise` | (Unused — every record carries the six fields.) |

### Georgia 12-lead (CinC 2020 SNOMED subset)

Reuses `map_chapman_codes` because the CinC 2020 label space is the same
SNOMED-CT subset. The Georgia loader extracts `# Dx:` lines from the WFDB
header and feeds them to the same mapping.

### CinC 2020 — full multi-source blend (SNOMED-CT)

`ml/datasets/cinc2020.py`. The PhysioNet/CinC 2020 release bundles six source
databases (`cpsc_2018`, `cpsc_2018_extra`, `georgia`, `ptb`,
`st_petersburg_incart`, and a copy of `ptb-xl`). The loader walks every source
**except `ptb-xl`** (excluded by default to avoid duplicating the native
`ptb_xl` dataset in a blended manifest; override with
`CINC2020_INCLUDE_PTBXL=1`). Each record's `# Dx:` SNOMED-CT codes feed both
`map_chapman_codes` (3-class space) and `diagnostic_superclasses_from_snomed`
(5-class diagnostic head, below). Sampling rate is read per-record from the
header (500 Hz for most, 1000 Hz for `ptb`, 257 Hz for INCART). 18,062 of
21,264 records (84.9 %) carry at least one diagnostic superclass and are kept by
the multi-label trainer.

## Diagnostic superclass harmonisation (5-class 12-lead head)

The production 12-lead model predicts the five **PTB-XL diagnostic
superclasses** — `NORM`, `MI`, `STTC`, `CD`, `HYP` — not the 3-class space.
SNOMED-CT datasets (Georgia, CinC 2020) are mapped to these via
`diagnostic_superclasses_from_snomed` in `ml/datasets/labels.py`. A record can
carry several superclasses (true multi-label); if `NORM` co-occurs with any
abnormal class, `NORM` is dropped. Records that map to **no** superclass are
dropped by the trainer (`data.py`), so map coverage directly determines
training-set size.

| Superclass | SNOMED-CT codes |
|------------|-----------------|
| `NORM` | `426783006` sinus rhythm · `426177001` sinus bradycardia · `427084000` sinus tachycardia |
| `MI` | `164865005` MI · `164867002` old MI · `57054005` acute MI · `429622005` STEMI |
| `STTC` | `164930006` ST depression · `164931005` ST elevation · `164934002` T-wave abnormal · `59931005` T-wave inversion · `428750005` non-specific ST-T · `164861001` myocardial ischemia · `55930002` non-specific ST changes |
| `CD` | `164909002` LBBB · `59118001` RBBB · `713427006` complete RBBB · `713426002` incomplete RBBB · `445118002` LAFB · `164947007` LPFB · `698252002` non-specific IVCD · `270492004` 1° AV block |
| `HYP` | `164873001` LVH · `89792004` RVH · `67741000119109` left atrial enlargement · `446813000` left atrial hypertrophy · `446358003` right atrial hypertrophy |

> **2026-06-07 expansion (CinC 2020 integration).** Added `164861001`,
> `55930002` to STTC and `67741000119109`, `446813000`, `446358003` to HYP.
> Rationale: these are high-frequency CinC 2020 codes (ischemia ≈2.5k records,
> left-atrial enlargement ≈1.3k) that PTB-XL groups under STTC (ISC\*) and HYP
> (atrial enlargement subclasses) respectively. They roughly **double HYP
> supervision** (the model's weakest class) and add ~3.3k STTC records. Codes
> outside the five diagnostic axes (rhythm: AF/PAC/PVC; axis deviation; QT
> prolongation; low voltage) are intentionally **not** mapped — they belong to
> PTB-XL's separate `rhythm`/`form` label groups, not the diagnostic head.

### SPH — Shandong Provincial Hospital (AHA / ACC / HRS strings)

`map_sph`.

| Axis | SPH statement prefix |
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
mixed-source manifest should keep each Axis class at ≥ 10 % of total
samples; oversample if needed via the trainer's `WeightedRandomSampler`.

## Audit / change process

1. Open a PR that edits both `ml/datasets/labels.py` and this document
   together. Otherwise CI rejects the change.
2. Bump `pipeline_version` in `apps/ml-api/app/core/config.py` so downstream
   manifests can detect the schema change.
3. Re-run `make eval` and attach the report.
