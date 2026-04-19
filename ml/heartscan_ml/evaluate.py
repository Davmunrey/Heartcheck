from __future__ import annotations

import argparse
import json
import os

import torch
from torch.utils.data import DataLoader
from torchmetrics.classification import MulticlassConfusionMatrix, MulticlassF1Score

from heartscan_ml.ckpt import load_torch
from heartscan_ml.config import TrainConfig
from heartscan_ml.dataset_ptbxl import PTBXLScreeningDataset
from heartscan_ml.labels import CLASS_NAMES
from heartscan_ml.model_cnn1d import CNN1D12Lead


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate CNN1D on PTB-XL test fold.")
    p.add_argument("--ptbxl-dir", default=os.environ.get("PTBXL_DIR", ""))
    p.add_argument("--checkpoint", default="checkpoints/cnn1d_best.pt")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

    if not args.ptbxl_dir:
        raise SystemExit("Set --ptbxl-dir or PTBXL_DIR.")

    cfg = TrainConfig(ptbxl_dir=args.ptbxl_dir)
    ds = PTBXLScreeningDataset(cfg, (cfg.test_fold,), augment_noise=False)
    loader = DataLoader(ds, batch_size=64, shuffle=False)

    device = torch.device(args.device)
    ckpt = load_torch(args.checkpoint, device)
    model = CNN1D12Lead(seq_len=cfg.crop_len, num_classes=3).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    f1 = MulticlassF1Score(num_classes=3, average="none").to(device)
    cm = MulticlassConfusionMatrix(num_classes=3).to(device)

    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            pred = model(xb).argmax(dim=1)
            f1.update(pred, yb)
            cm.update(pred, yb)

    f1v = f1.compute().cpu().numpy()
    cmv = cm.compute().cpu().numpy()
    report = {
        "per_class_f1": {CLASS_NAMES[i]: float(f1v[i]) for i in range(3)},
        "confusion_matrix": cmv.tolist(),
        "class_names": list(CLASS_NAMES),
        "checkpoint": args.checkpoint,
    }
    print(json.dumps(report, indent=2))
    out = os.path.join(os.path.dirname(args.checkpoint) or ".", "eval_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
