# Datasheet — Training data for HeartScan

> Format inspired by Gebru et al., "Datasheets for Datasets" (2018).
> Lists every public ECG dataset HeartScan **may** train against and the
> licence terms that constrain how derived weights can be used. The runtime
> registry of these datasets lives in [`ml/datasets/registry.py`](../ml/datasets/registry.py).

## Quick decision table

| Dataset | Records | Leads | License | Commercial product? | Notes |
|---------|---------|-------|---------|---------------------|-------|
| [PTB-XL](../ml/datasets/ptb_xl.py) | 21,837 | 12 | CC BY 4.0 | Yes | Gold standard; 71 SCP-ECG codes; pre-built folds 1–10 |
| [Chapman-Shaoxing-Ningbo](../ml/datasets/chapman_shaoxing.py) | 45,152 | 12 | CC BY 4.0 | Yes | 90 SNOMED-CT codes; great rhythm diversity |
| [CinC 2017](../ml/datasets/cinc2017.py) | 8,528 | 1 | CC BY 4.0 | Yes | Single-lead AliveCor; matches HeartScan's 1D output |
| [BUT QDB](../ml/datasets/but_qdb.py) | 18 | 1 | CC BY 4.0 | Yes | Quality labels; trains the gate, not the classifier |
| [ECG-Image-Database](../ml/datasets/ecg_image_database.py) | 35,595 imgs | 12 | CC BY 4.0 | Yes | **Photo domain** — critical for HeartScan |
| [PTB-XL-Image-17K](../ml/datasets/ptb_xl_image_17k.py) | 17,271 imgs | 12 | CC BY 4.0 | Yes | Synthetic photos with pixel masks |
| [Georgia 12-lead](../ml/datasets/georgia12.py) | 10,344 | 12 | CC BY 4.0 | Yes | Emory; CinC 2020 training subset |
| [SPH (Shandong)](../ml/datasets/sph.py) | 25,770 | 12 | CC BY 4.0 | Yes | Mendeley host; AHA/ACC/HRS statements |
| [CODE-15%](../ml/datasets/code_15pct.py) | 345,779 | 12 | CC BY 4.0 | Yes | Brazilian Telesalud TNMG; 50 GB |
| [MIT-BIH Arrhythmia](../ml/datasets/mit_bih.py) | 48 | 2 | ODC-By | Yes | Historical benchmark |
| [LUDB](../ml/datasets/ludb.py) | 200 | 12 | ODC-By | Yes | P/QRS/T delineation; trains R-peak detector |
| [Icentia11k](../ml/datasets/icentia11k.py) | 11,000 patients | 1 | **CC BY-NC-SA** | **No** | Research only; weights cannot ship |
| [MIMIC-IV-ECG](../ml/datasets/mimic_iv_ecg.py) | ~800,000 | 12 | ODbL + clinical | Pending legal | Free-text reports require NLP harmonisation |

Restricted (manual access): UK Biobank ECG (~90K resting + ~90K exercise),
CODE full (2.47M), Apple Heart Study (not public). Access procedure and
status log live in [`docs/RESTRICTED_DATASETS.md`](RESTRICTED_DATASETS.md).

## How HeartScan combines them

The intended primary blend:

1. **Pretrain on signals** with PTB-XL + Chapman-Shaoxing + Georgia + CinC 2017.
   ([`ml/training/pretrain.py`](../ml/training/pretrain.py))
2. **Fine-tune on images** with ECG-Image-Database + PTB-XL-Image-17K, routed
   through HeartScan's own extractor so the model sees what production sees.
   ([`ml/training/finetune_image.py`](../ml/training/finetune_image.py))
3. **Calibrate** temperature + conformal threshold on a dedicated val split.
   ([`ml/training/calibrate.py`](../ml/training/calibrate.py))
4. **Eval** against the synthetic harness and `data/real_eval/`.
   ([`apps/ml-api/app/eval/cli.py`](../apps/ml-api/app/eval/cli.py))
5. **Emit YAML manifest** with SHA-256, dataset list, metrics.
   ([`ml/training/emit_manifest.py`](../ml/training/emit_manifest.py))

The **tier 1** blend (commercial-safe, ~6 GB) is the recommended baseline.
**Tier 2** adds CODE-15% (50 GB). **Tier 3** requires MIMIC-IV-ECG access.

## Subgroup reporting requirement

Every checkpoint promoted to production must report metrics by:

- source dataset (verifies the blend is balanced),
- age bucket (`<30`, `30-50`, `50-70`, `70+`),
- sex (when available).

If any subgroup F1 macro lags the overall by more than 0.10, the model card
must explain the gap before the checkpoint is signed off.

## Privacy / consent posture

- All datasets above are **already de-identified** by their providers; we do
  not redistribute raw records. We may publish derived statistics in the
  model card.
- Patient identifiers in the manifest are upstream IDs; we never tie them to
  HeartScan user accounts.
- Storage of downloaded data follows [`docs/PRIVACY.md`](PRIVACY.md): cifrado
  en reposo, control de acceso por equipo, no commits.

## Versioning

Each dataset is pinned by version in the registry. When a provider bumps a
dataset (e.g. PTB-XL 1.0.3 → 1.0.4), the operator must:

1. Update the version field in `ml/datasets/<name>.py`.
2. Re-download and re-train.
3. Bump the checkpoint manifest's `dataset.version`.
4. Re-run `make eval` and update [`docs/MODEL_CARD.md`](MODEL_CARD.md).
