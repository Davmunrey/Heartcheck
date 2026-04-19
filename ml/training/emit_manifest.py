"""Emit a YAML manifest next to a trained checkpoint.

Schema is the one enforced by ``apps/ml-api/app/ml/manifest.py``. The script
takes:

- the checkpoint (whose SHA-256 is computed and recorded);
- the training-summary JSON (config snapshot);
- the calibration JSON (temperature + conformal threshold + ECE);
- the eval JSON produced by ``app.eval.cli`` against a held-out manifest;
- the list of datasets that fed the run.

It writes ``<checkpoint>.yaml`` (PhysioNet / HeartScan convention) so
``inference._resolve_manifest`` finds it automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ml.datasets.registry import REGISTRY


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(
    checkpoint: Path,
    training_summary: Path,
    calibration: Path | None,
    eval_report: Path | None,
    datasets: list[str],
    architecture: str,
    model_version: str,
    author: str,
) -> dict:
    sha = sha256_file(checkpoint)
    summary = json.loads(training_summary.read_text(encoding="utf-8"))
    cal = json.loads(calibration.read_text(encoding="utf-8")) if calibration else {}
    rep = json.loads(eval_report.read_text(encoding="utf-8")) if eval_report else {}

    metrics: dict[str, float] = {}
    if rep:
        metrics["f1_macro"] = float(rep.get("classification", {}).get("f1_macro", 0.0))
        metrics["accuracy"] = float(rep.get("classification", {}).get("accuracy", 0.0))
        metrics["ece"] = float(rep.get("calibration", {}).get("ece", 0.0))
        metrics["p95_ms"] = float(rep.get("latency_ms", {}).get("p95", 0.0))
    else:
        metrics["f1_macro"] = float(summary.get("best_val_f1_macro", 0.0))
    if cal:
        metrics["temperature"] = float(cal.get("temperature", 1.0))
        metrics["conformal_threshold"] = float(cal.get("conformal_threshold", 1.0))
        metrics["ece_calibrated"] = float(cal.get("ece_calibrated", 0.0))

    primary = REGISTRY[datasets[0]] if datasets else None
    payload = {
        "model_version": model_version,
        "architecture": architecture,
        "sha256": sha,
        "dataset": {
            "name": "+".join(datasets) if datasets else "unknown",
            "version": "+".join(REGISTRY[d].version for d in datasets) if datasets else "0",
            "components": [
                {
                    "name": d,
                    "version": REGISTRY[d].version,
                    "license": REGISTRY[d].license,
                    "license_class": REGISTRY[d].license_class,
                }
                for d in datasets
            ],
        },
        "metrics": metrics,
        "training": summary.get("config", {}),
        "calibration": cal,
        "evaluation": {
            "report_path": str(eval_report) if eval_report else None,
            "metrics": metrics,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "author": author,
        "license_notes": (
            "License of derived weights is the most restrictive of the components; "
            f"primary={primary.license if primary else 'unknown'}"
        ),
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Emit checkpoint manifest YAML")
    p.add_argument("--checkpoint", required=True, type=Path)
    p.add_argument("--training-summary", required=True, type=Path)
    p.add_argument("--calibration", type=Path, default=None)
    p.add_argument("--eval-report", type=Path, default=None)
    p.add_argument("--datasets", nargs="+", default=[])
    p.add_argument("--architecture", default="ECGResNet1D")
    p.add_argument("--model-version", required=True)
    p.add_argument("--author", default="heartscan-eng")
    p.add_argument("--out", type=Path, default=None, help="default <checkpoint>.yaml")
    args = p.parse_args(argv)

    payload = build(
        checkpoint=args.checkpoint,
        training_summary=args.training_summary,
        calibration=args.calibration,
        eval_report=args.eval_report,
        datasets=args.datasets,
        architecture=args.architecture,
        model_version=args.model_version,
        author=args.author,
    )
    out = args.out or args.checkpoint.with_suffix(args.checkpoint.suffix + ".yaml")
    out.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"[manifest] wrote {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
