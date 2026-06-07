#!/usr/bin/env bash
# One-shot: calibrate + evaluate the CinC2020-blend checkpoint on two slices
# (PTB-XL-only test for apples-to-apples vs the champion, and the full blended
# multi-source test for generalisation). Prints both reports. Does NOT promote.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/apps/ml-api/.venv/bin/python"
OUT="$ROOT/runs/local/cinc2020_blend"
CKPT="$OUT/checkpoint.pt"

[[ -f "$CKPT" ]] || { echo "[abort] no checkpoint at $CKPT (training not finished?)"; exit 2; }

echo "[1/3] calibrate (non-fatal if it skips the multi-label head)"
"$PY" -m ml.training.calibrate \
  --logits "$OUT/val_logits.npz" --checkpoint "$CKPT" \
  --report "$OUT/calibration.json" || echo "[warn] calibrate skipped"

echo "[2/3] evaluate — full blended multi-source test (generalisation)"
"$PY" -m ml.training.evaluate_multilabel \
  --manifest "$OUT/manifest_split.parquet" --checkpoint "$CKPT" \
  --split test --workers 6 --out "$OUT/eval_blend_test.json"

echo "[3/3] evaluate — PTB-XL-only test (apples-to-apples vs champion 0.755)"
"$PY" -m ml.training.evaluate_multilabel \
  --manifest "$OUT/ptbxl_test_only.parquet" --checkpoint "$CKPT" \
  --split test --workers 6 --out "$OUT/eval_ptbxl_test.json"

echo
echo "=== SUMMARY ==="
"$PY" - <<'PYEOF'
import json, pathlib
out = pathlib.Path("runs/local/cinc2020_blend")
for label, f in (("BLEND (multi-source)", "eval_blend_test.json"),
                 ("PTB-XL only", "eval_ptbxl_test.json")):
    p = out / f
    if not p.exists():
        print(f"{label}: (missing)"); continue
    d = json.loads(p.read_text())
    macro = d.get("macro_f1") or d.get("tuned_macro_f1")
    per = d.get("per_class_f1") or d.get("per_class") or {}
    print(f"\n{label}: macro-F1={macro}")
    if isinstance(per, dict):
        print("  per-class F1:", {k: round(v,3) if isinstance(v,(int,float)) else v for k,v in per.items()})
PYEOF
