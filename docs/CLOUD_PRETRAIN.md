# Cloud pretraining — deep ECG backbone on CODE-15%

The real lever past the served champion (0.608 macro-F1) is pretraining the
6.8M-param `ECGResNetDeep1D` on a large corpus, then fine-tuning. CODE-15%
(345k 12-lead ECGs) is too big for the laptop (~50 GB) and far too slow to
pretrain on Apple MPS. **Do the pretraining in the cloud; fine-tune locally.**

```
┌─ CLOUD GPU (50 GB disk) ────────────┐      ┌─ LAPTOP ───────────────────────┐
│ download CODE-15 (345k ECGs)        │      │ has PTB-XL + CinC2020 blend    │
│ pretrain deep backbone (CUDA)       │ ──▶  │ fine-tune 5-superclass head    │
│ → backbone.pt  (~27 MB)             │ scp  │   --init-backbone backbone.pt  │
└─────────────────────────────────────┘      └────────────────────────────────┘
```

Only `backbone.pt` (~27 MB) crosses the wire. The 50 GB corpus stays in the cloud.

## 1. On the cloud GPU box (one command)

Any CUDA box works — Colab Pro, Lambda, RunPod, Vast.ai, EC2 g5/p3. ~24 GB VRAM
is comfortable at batch 128; drop `BATCH` if you hit OOM.

```bash
git clone https://github.com/Davmunrey/Heartcheck && cd Heartcheck
bash scripts/cloud_pretrain_code15.sh
# tunables: EPOCHS=10 BATCH=128 LR=1e-3 WORKERS=8
```

It installs minimal deps (torch + numpy + h5py + the `heartscan_ml` package),
downloads CODE-15 (resumable), pretrains, and writes `runs/cloud/code15_pretrain/backbone.pt`.

**Rough time** (10 epochs, 345k records @ 4096 samples): ~2–4 h on an A10/A100,
vs **days** on the laptop's MPS. Cost is typically a few dollars.

## 2. Bring the backbone back + fine-tune locally

```bash
mkdir -p runs/local/code15_pretrain
scp <cloud>:.../runs/cloud/code15_pretrain/backbone.pt runs/local/code15_pretrain/backbone.pt

# fine-tune the 5 superclasses on the local blend (skips pretrain automatically
# because backbone.pt is present):
FT_OUT=runs/local/deep_code15_ft \
  PRETRAIN_OUT=runs/local/code15_pretrain \
  scripts/pretrain_finetune_code15.sh
```

Then evaluate the new checkpoint against the champion's **0.608** on the same
PTB-XL slice (see `scripts/eval_cinc2020_blend.sh`); promote only if it wins.

## Notes

- **Colab**: upload nothing — `git clone` in a cell, then `!bash scripts/cloud_pretrain_code15.sh`.
  Mount Drive (`/content/drive`) and set `CODE15_ROOT` there if the 50 GB won't
  fit on the ephemeral disk.
- **Subset option**: if cloud disk is tight, download only some `exams_partN.zip`
  — `pretrain_code15.py` trains on whatever parts are present (6–8 parts ≈
  100–140k ECGs is already a strong corpus).
- **Determinism**: pretrain uses a fixed seed and a patient-disjoint val split,
  so no patient leaks between train and val.
- The pipeline is the same code path that's unit-tested locally
  (`transfer_backbone`, tie-aware AUROC) — only the hardware differs.
