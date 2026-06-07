#!/usr/bin/env bash
# scripts/lambda_setup.sh
#
# Bootstrap a fresh Lambda Labs / RunPod / Vast.ai GPU instance for a
# full Axis training run. Idempotent: re-running on the same VM
# only does work that's missing.
#
# Expected target: Ubuntu 22.04 LTS + CUDA 12.x base image, single A100
# (40 GB or 80 GB) or H100. ~150 GB free disk for tier-1 + image data.
#
# Usage on the GPU box, after `git clone <repo>`:
#
#   chmod +x scripts/lambda_setup.sh
#   ./scripts/lambda_setup.sh
#
# Then run training (see end of this script for the recommended command).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { printf "\n[lambda_setup] %s\n" "$*"; }

# ---------------------------------------------------------------------------
# 0. Sanity checks
# ---------------------------------------------------------------------------

log "checking host prerequisites"
command -v python3 >/dev/null || { echo "python3 missing" >&2; exit 1; }
command -v git >/dev/null     || { echo "git missing" >&2; exit 1; }

if ! command -v nvidia-smi >/dev/null; then
  cat >&2 <<'WARN'
[warn] nvidia-smi not found. Continuing, but pretrain will fall back to CPU
       (which on tier-1 takes ~24-48 h). On Lambda/RunPod the base image
       ships nvidia-smi out of the box; if you hit this, you picked the
       wrong instance type.
WARN
else
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true
fi

DISK_FREE_GB=$(df -BG "$ROOT" | awk 'NR==2 {gsub("G","",$4); print $4}')
if [[ "${DISK_FREE_GB:-0}" -lt 100 ]]; then
  echo "[warn] only ${DISK_FREE_GB} GB free on $ROOT — tier-1+image needs ~90 GB" >&2
fi

# ---------------------------------------------------------------------------
# 1. System packages (PhysioNet downloads need libsndfile + curl)
# ---------------------------------------------------------------------------

if command -v apt-get >/dev/null; then
  log "installing apt prerequisites (libsndfile1, build-essential, unzip)"
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    build-essential libsndfile1 unzip curl ca-certificates >/dev/null
fi

# ---------------------------------------------------------------------------
# 2. Backend venv (reuses scripts/install_backend.sh) + wfdb for downloads
# ---------------------------------------------------------------------------

if [[ ! -x "$ROOT/apps/ml-api/.venv/bin/python" ]]; then
  log "creating apps/ml-api/.venv via scripts/install_backend.sh"
  bash "$ROOT/scripts/install_backend.sh"
else
  log "venv already present, skipping install_backend.sh"
fi

PY="$ROOT/apps/ml-api/.venv/bin/python"
PIP="$ROOT/apps/ml-api/.venv/bin/pip"

log "ensuring training-only deps (wfdb for PhysioNet, tqdm for progress bars)"
"$PIP" install --quiet wfdb 'tqdm>=4.65'

# ---------------------------------------------------------------------------
# 3. Confirm CUDA-aware torch (the requirements.txt installs CPU torch)
# ---------------------------------------------------------------------------

CUDA_OK=$("$PY" -c "import torch; print(int(torch.cuda.is_available()))" 2>/dev/null || echo 0)
if [[ "$CUDA_OK" != "1" ]]; then
  log "torch sees no CUDA; reinstalling torch with the cu121 wheel"
  "$PIP" install --quiet --upgrade --index-url https://download.pytorch.org/whl/cu121 \
    torch torchvision
  CUDA_OK=$("$PY" -c "import torch; print(int(torch.cuda.is_available()))")
  if [[ "$CUDA_OK" != "1" ]]; then
    echo "[abort] still no CUDA after reinstall — check the host driver" >&2
    exit 3
  fi
fi
"$PY" -c "import torch; print(f'[lambda_setup] torch={torch.__version__} cuda={torch.version.cuda} device={torch.cuda.get_device_name(0)}')"

# ---------------------------------------------------------------------------
# 4. Repo-side smoke test — fast pretrain on synthetic noise
# ---------------------------------------------------------------------------

log "running synthetic dry-run (1 epoch) to validate the pipeline"
mkdir -p "$ROOT/runs/lambda_smoke"
"$PY" - <<'PY'
import numpy as np, pyarrow as pa, pyarrow.parquet as pq
from pathlib import Path
root = Path("runs/lambda_smoke"); root.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(0)
rows = []
for i in range(96):
    cls = i % 3
    p = root / f"{i:03d}.npy"
    np.save(p, rng.standard_normal(1024).astype(np.float32))
    rows.append({
        "patient_id": f"p{i:03d}", "record_id": f"r{i}",
        "label": ["normal","arrhythmia","noise"][cls], "label_id": cls,
        "source_dataset": "lambda_smoke", "source_label": "x",
        "file_path": str(p), "sampling_rate_hz": 100,
        "n_leads": 1, "duration_s": 10.0,
        "split": "train" if i < 72 else "val",
    })
pq.write_table(pa.Table.from_pylist(rows), root / "manifest_split.parquet")
PY

"$PY" -m ml.training.pretrain \
  --manifest runs/lambda_smoke/manifest_split.parquet \
  --out runs/lambda_smoke/pretrain \
  --epochs 1 --batch-size 16 --workers 0

log "smoke pretrain OK — checkpoint at runs/lambda_smoke/pretrain/checkpoint.pt"

# ---------------------------------------------------------------------------
# 5. Print recommended training command
# ---------------------------------------------------------------------------

cat <<EOF

============================================================================
[lambda_setup] DONE. Ready for a real training run.

Recommended first run (tier-1 signals + image fine-tune, ~3-5 h on A100):

  EPOCHS=30 BATCH_SIZE=256 WORKERS=8 \\
  IMAGE_DATASETS="ecg_image_database ptb_xl_image_17k" \\
  PROMOTE=1 BASELINE=eval/baselines/synth_v1.json \\
  MODEL_VERSION=ecg-resnet1d-v1.0.0 \\
  ./scripts/train_autonomous.sh

When it finishes, scp the promoted checkpoint and YAML back to your laptop:

  scp ubuntu@<lambda_ip>:~/Heartcheck/apps/ml-api/weights/ecg-resnet1d-v1.0.0.pt* ./apps/ml-api/weights/

Then redeploy ml-api:  fly deploy -c apps/ml-api/fly.toml
============================================================================
EOF
