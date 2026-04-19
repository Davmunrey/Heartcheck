"""Autonomous training orchestrator for HeartScan.

Chains every step of the public-data training plan into one idempotent
command:

    download -> manifest -> splits -> pretrain
             -> (optional) image fine-tune
             -> calibrate -> eval -> emit manifest YAML
             -> (optional) promote to apps/ml-api/weights/

Each step writes its outputs under ``runs/<run_id>/`` and records state in
``runs/<run_id>/state.json``. Re-running with the same ``--run-id`` skips
already-completed steps, so a cron/systemd job can resume after a crash.

Promotion rule
--------------
The pipeline only copies the new checkpoint into ``apps/ml-api/weights/`` when
its F1 macro on the eval harness beats the configured baseline by at least
``--promote-min-delta`` (default 0.02 = 2 pts). If no baseline file exists,
the first successful run becomes the baseline.

Honest limits
-------------
- Tier-1 download is ~6 GB; image tier adds ~80 GB. The script does **not**
  download tier-2 (CODE-15%, MIMIC-IV-ECG) because those need legal
  clearance and credentials.
- Pretraining 10 epochs on a balanced PTB-XL+Chapman+CinC2017 mix takes
  hours on a CPU and ~20 min on a single A100. Set ``--epochs`` accordingly.
- The orchestrator never bypasses the manifest / SHA verification of
  ``apps/ml-api/app/services/inference.py``; every promoted checkpoint ships
  with its YAML alongside.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

DEFAULT_TIER1 = ["ptb_xl", "chapman_shaoxing", "cinc2017", "but_qdb"]
DEFAULT_IMAGE = ["ecg_image_database", "ptb_xl_image_17k"]


@dataclass
class RunConfig:
    run_id: str
    runs_dir: Path
    raw_dir: Path
    tier1_datasets: list[str] = field(default_factory=lambda: list(DEFAULT_TIER1))
    image_datasets: list[str] = field(default_factory=list)
    epochs: int = 5
    batch_size: int = 64
    lr: float = 1e-3
    workers: int = 2
    eval_label: str = "autonomous"
    eval_synth_n: int = 20
    promote: bool = False
    promote_min_delta: float = 0.02
    baseline_metrics_path: Path | None = None
    skip_download: bool = False
    skip_finetune: bool = False
    model_version: str = ""

    def run_dir(self) -> Path:
        return self.runs_dir / self.run_id


@dataclass
class PipelineState:
    started_at: str
    config: dict
    steps: dict[str, dict] = field(default_factory=dict)

    def mark(self, step: str, status: str, **extra: object) -> None:
        self.steps[step] = {"status": status, "ts": _utc_now(), **extra}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(run_dir: Path) -> Path:
    return run_dir / "state.json"


def _load_state(run_dir: Path) -> PipelineState | None:
    p = _state_path(run_dir)
    if not p.is_file():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    state = PipelineState(started_at=raw["started_at"], config=raw["config"])
    state.steps = raw.get("steps", {})
    return state


def _save_state(run_dir: Path, state: PipelineState) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "started_at": state.started_at,
        "config": state.config,
        "steps": state.steps,
    }
    _state_path(run_dir).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _step_done(state: PipelineState, name: str) -> bool:
    s = state.steps.get(name)
    return bool(s) and s.get("status") == "ok"


def _shell(cmd: Iterable[str], log: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"[run] {' '.join(cmd)}")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(cmd)}\n")
        proc = subprocess.run(list(cmd), stdout=f, stderr=subprocess.STDOUT)
    return proc.returncode


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def step_download(cfg: RunConfig, state: PipelineState, log: Path) -> None:
    if _step_done(state, "download") or cfg.skip_download:
        state.mark("download", "skipped")
        return
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    targets = list(cfg.tier1_datasets) + list(cfg.image_datasets)
    for ds in targets:
        target = cfg.raw_dir / ds
        if (target / ".downloaded").is_file():
            print(f"[skip] {ds} already downloaded")
            continue
        rc = _shell(
            [PY, "-m", "ml.datasets.cli", "download", ds, "--target", str(target)],
            log,
        )
        if rc != 0:
            state.mark("download", "failed", dataset=ds, returncode=rc)
            raise RuntimeError(f"Download failed for {ds} (rc={rc})")
        (target / ".downloaded").write_text(_utc_now())
    state.mark("download", "ok", datasets=targets)


def step_manifest(cfg: RunConfig, state: PipelineState, log: Path) -> Path:
    out = cfg.run_dir() / "manifest.parquet"
    if _step_done(state, "manifest") and out.is_file():
        return out
    rc = _shell(
        [
            PY, "-m", "ml.datasets.cli", "manifest",
            "--root", str(cfg.raw_dir),
            "--datasets", *cfg.tier1_datasets,
            "--out", str(out),
        ],
        log,
    )
    if rc != 0 or not out.is_file():
        state.mark("manifest", "failed", returncode=rc)
        raise RuntimeError(f"Manifest build failed (rc={rc})")
    state.mark("manifest", "ok", path=str(out))
    return out


def step_splits(cfg: RunConfig, state: PipelineState, log: Path, manifest: Path) -> Path:
    out = cfg.run_dir() / "manifest_split.parquet"
    if _step_done(state, "splits") and out.is_file():
        return out
    rc = _shell(
        [
            PY, "-m", "ml.datasets.splits",
            "--manifest", str(manifest),
            "--out", str(out),
        ],
        log,
    )
    if rc != 0 or not out.is_file():
        state.mark("splits", "failed", returncode=rc)
        raise RuntimeError(f"Splits failed (rc={rc})")
    state.mark("splits", "ok", path=str(out))
    return out


def step_pretrain(cfg: RunConfig, state: PipelineState, log: Path, manifest: Path) -> Path:
    out_dir = cfg.run_dir() / "pretrain"
    ckpt = out_dir / "checkpoint.pt"
    if _step_done(state, "pretrain") and ckpt.is_file():
        return ckpt
    rc = _shell(
        [
            PY, "-m", "ml.training.pretrain",
            "--manifest", str(manifest),
            "--out", str(out_dir),
            "--epochs", str(cfg.epochs),
            "--batch-size", str(cfg.batch_size),
            "--lr", str(cfg.lr),
            "--workers", str(cfg.workers),
        ],
        log,
    )
    if rc != 0 or not ckpt.is_file():
        state.mark("pretrain", "failed", returncode=rc)
        raise RuntimeError(f"Pretrain failed (rc={rc})")
    state.mark("pretrain", "ok", checkpoint=str(ckpt))
    return ckpt


def step_finetune(cfg: RunConfig, state: PipelineState, log: Path, pretrained: Path) -> Path:
    if cfg.skip_finetune or not cfg.image_datasets:
        state.mark("finetune", "skipped")
        return pretrained
    image_manifest = cfg.run_dir() / "manifest_images.parquet"
    if not image_manifest.is_file():
        rc = _shell(
            [
                PY, "-m", "ml.datasets.cli", "manifest",
                "--root", str(cfg.raw_dir),
                "--datasets", *cfg.image_datasets,
                "--out", str(image_manifest),
            ],
            log,
        )
        if rc != 0 or not image_manifest.is_file():
            state.mark("finetune", "failed", stage="image_manifest", returncode=rc)
            raise RuntimeError(f"Image manifest failed (rc={rc})")
    image_split = cfg.run_dir() / "manifest_images_split.parquet"
    if not image_split.is_file():
        rc = _shell(
            [PY, "-m", "ml.datasets.splits", "--manifest", str(image_manifest), "--out", str(image_split)],
            log,
        )
        if rc != 0 or not image_split.is_file():
            state.mark("finetune", "failed", stage="image_splits", returncode=rc)
            raise RuntimeError(f"Image splits failed (rc={rc})")
    out_dir = cfg.run_dir() / "finetune"
    ckpt = out_dir / "checkpoint.pt"
    if _step_done(state, "finetune") and ckpt.is_file():
        return ckpt
    rc = _shell(
        [
            PY, "-m", "ml.training.finetune_image",
            "--manifest", str(image_split),
            "--out", str(out_dir),
            "--pretrained", str(pretrained),
            "--epochs", str(max(1, cfg.epochs // 2)),
            "--batch-size", str(cfg.batch_size),
            "--workers", str(cfg.workers),
        ],
        log,
    )
    if rc != 0 or not ckpt.is_file():
        state.mark("finetune", "failed", returncode=rc)
        raise RuntimeError(f"Image fine-tune failed (rc={rc})")
    state.mark("finetune", "ok", checkpoint=str(ckpt))
    return ckpt


def step_calibrate(cfg: RunConfig, state: PipelineState, log: Path, ckpt: Path) -> Path:
    val_logits = ckpt.parent / "val_logits.npz"
    cal_report = ckpt.parent / "calibration.json"
    if _step_done(state, "calibrate") and cal_report.is_file():
        return cal_report
    if not val_logits.is_file():
        state.mark("calibrate", "failed", reason="missing val_logits.npz")
        raise RuntimeError(f"val_logits.npz missing next to {ckpt}")
    rc = _shell(
        [
            PY, "-m", "ml.training.calibrate",
            "--logits", str(val_logits),
            "--checkpoint", str(ckpt),
            "--report", str(cal_report),
        ],
        log,
    )
    if rc != 0 or not cal_report.is_file():
        state.mark("calibrate", "failed", returncode=rc)
        raise RuntimeError(f"Calibrate failed (rc={rc})")
    state.mark("calibrate", "ok", report=str(cal_report))
    return cal_report


def step_eval(cfg: RunConfig, state: PipelineState, log: Path, ckpt: Path) -> dict:
    eval_dir = cfg.run_dir() / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        PY, "-m", "app.eval.cli",
        "--generate-synth",
        "--synth-out", str(cfg.run_dir() / "synth"),
        "--synth-n", str(cfg.eval_synth_n),
        "--manifest", str(cfg.run_dir() / "synth" / "manifest.jsonl"),
        "--out", str(eval_dir),
        "--label", cfg.eval_label,
    ]
    env = {"HEARTSCAN_MODEL_PATH": str(ckpt)}
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"[run] {' '.join(cmd)}  (HEARTSCAN_MODEL_PATH={ckpt})")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n$ HEARTSCAN_MODEL_PATH={ckpt} {' '.join(cmd)}\n")
        proc = subprocess.run(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=REPO_ROOT / "backend",
            env={**dict(__import__("os").environ), **env},
        )
    if proc.returncode != 0:
        state.mark("eval", "failed", returncode=proc.returncode)
        raise RuntimeError(f"Eval failed (rc={proc.returncode})")
    reports = sorted(eval_dir.glob(f"*_{cfg.eval_label}.json"))
    if not reports:
        state.mark("eval", "failed", reason="no report")
        raise RuntimeError(f"No eval report found in {eval_dir}")
    latest = reports[-1]
    metrics = json.loads(latest.read_text(encoding="utf-8"))
    summary = {
        "f1_macro": metrics.get("classification", {}).get("f1_macro"),
        "ece": metrics.get("calibration", {}).get("ece"),
        "p95_ms": metrics.get("latency_ms", {}).get("p95"),
        "report": str(latest),
    }
    state.mark("eval", "ok", **summary)
    return summary


def step_emit_manifest(cfg: RunConfig, state: PipelineState, log: Path, ckpt: Path, cal_report: Path, eval_summary: dict) -> Path:
    summary_path = ckpt.parent / "training_summary.json"
    if not summary_path.is_file():
        # finetune step doesn't produce training_summary.json; reuse pretrain's
        summary_path = (cfg.run_dir() / "pretrain" / "training_summary.json")
    eval_report = Path(eval_summary["report"])
    cmd = [
        PY, "-m", "ml.training.emit_manifest",
        "--checkpoint", str(ckpt),
        "--training-summary", str(summary_path),
        "--calibration", str(cal_report),
        "--eval-report", str(eval_report),
        "--datasets", *cfg.tier1_datasets, *cfg.image_datasets,
        "--model-version", cfg.model_version or f"ecg-resnet1d-{cfg.run_id}",
    ]
    rc = _shell(cmd, log)
    yaml_path = ckpt.with_suffix(ckpt.suffix + ".yaml")
    if rc != 0 or not yaml_path.is_file():
        state.mark("emit_manifest", "failed", returncode=rc)
        raise RuntimeError(f"Manifest emit failed (rc={rc})")
    state.mark("emit_manifest", "ok", path=str(yaml_path))
    return yaml_path


def step_promote(cfg: RunConfig, state: PipelineState, ckpt: Path, yaml_path: Path, eval_summary: dict) -> bool:
    if not cfg.promote:
        state.mark("promote", "skipped", reason="promote=false")
        return False
    f1 = float(eval_summary.get("f1_macro") or 0.0)
    baseline_f1 = 0.0
    if cfg.baseline_metrics_path and cfg.baseline_metrics_path.is_file():
        baseline = json.loads(cfg.baseline_metrics_path.read_text(encoding="utf-8"))
        baseline_f1 = float(baseline.get("classification", {}).get("f1_macro", 0.0))
    delta = f1 - baseline_f1
    if cfg.baseline_metrics_path and delta < cfg.promote_min_delta:
        state.mark(
            "promote",
            "skipped",
            reason="below_min_delta",
            f1_macro=f1,
            baseline_f1=baseline_f1,
            delta=delta,
            min_delta=cfg.promote_min_delta,
        )
        print(f"[promote] skipped: delta {delta:.4f} < min {cfg.promote_min_delta}")
        return False
    weights_dir = REPO_ROOT / "backend" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    name = cfg.model_version or f"ecg-resnet1d-{cfg.run_id}"
    dst_ckpt = weights_dir / f"{name}.pt"
    dst_yaml = weights_dir / f"{name}.pt.yaml"
    shutil.copy2(ckpt, dst_ckpt)
    shutil.copy2(yaml_path, dst_yaml)
    state.mark(
        "promote",
        "ok",
        checkpoint=str(dst_ckpt),
        yaml=str(dst_yaml),
        f1_macro=f1,
        baseline_f1=baseline_f1,
        delta=delta,
    )
    # Also overwrite baseline if requested (auto-baselining when none existed)
    if cfg.baseline_metrics_path and not cfg.baseline_metrics_path.is_file():
        cfg.baseline_metrics_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(eval_summary["report"], cfg.baseline_metrics_path)
    print(f"[promote] {dst_ckpt}  (F1 {f1:.4f}, +{delta:.4f} vs baseline)")
    return True


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(cfg: RunConfig) -> dict:
    cfg.run_dir().mkdir(parents=True, exist_ok=True)
    log = cfg.run_dir() / "pipeline.log"
    state = _load_state(cfg.run_dir()) or PipelineState(started_at=_utc_now(), config=asdict_serialisable(cfg))
    _save_state(cfg.run_dir(), state)

    t0 = time.perf_counter()
    try:
        step_download(cfg, state, log)
        _save_state(cfg.run_dir(), state)
        manifest = step_manifest(cfg, state, log)
        _save_state(cfg.run_dir(), state)
        split = step_splits(cfg, state, log, manifest)
        _save_state(cfg.run_dir(), state)
        ckpt = step_pretrain(cfg, state, log, split)
        _save_state(cfg.run_dir(), state)
        ckpt = step_finetune(cfg, state, log, ckpt)
        _save_state(cfg.run_dir(), state)
        cal_report = step_calibrate(cfg, state, log, ckpt)
        _save_state(cfg.run_dir(), state)
        eval_summary = step_eval(cfg, state, log, ckpt)
        _save_state(cfg.run_dir(), state)
        yaml_path = step_emit_manifest(cfg, state, log, ckpt, cal_report, eval_summary)
        _save_state(cfg.run_dir(), state)
        promoted = step_promote(cfg, state, ckpt, yaml_path, eval_summary)
        _save_state(cfg.run_dir(), state)
    finally:
        elapsed = round(time.perf_counter() - t0, 1)
        state.steps["__finished_at"] = {"ts": _utc_now(), "elapsed_s": elapsed}
        _save_state(cfg.run_dir(), state)
    print(f"[done] run {cfg.run_id} finished in {elapsed:.1f}s")
    return {"run_id": cfg.run_id, "promoted": promoted, "elapsed_s": elapsed, "eval": eval_summary}


def asdict_serialisable(cfg: RunConfig) -> dict:
    d = asdict(cfg)
    for k, v in list(d.items()):
        if isinstance(v, Path):
            d[k] = str(v)
    return d


def _parse(argv: list[str] | None = None) -> RunConfig:
    p = argparse.ArgumentParser(description="Autonomous training pipeline")
    p.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("auto_%Y%m%dT%H%M%SZ"))
    p.add_argument("--runs-dir", default="runs", type=Path)
    p.add_argument("--raw-dir", default="data/raw", type=Path)
    p.add_argument("--datasets", nargs="+", default=DEFAULT_TIER1)
    p.add_argument("--image-datasets", nargs="+", default=[])
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--eval-label", default="autonomous")
    p.add_argument("--eval-synth-n", type=int, default=20)
    p.add_argument("--promote", action="store_true", help="copy to apps/ml-api/weights when F1 wins")
    p.add_argument("--promote-min-delta", type=float, default=0.02)
    p.add_argument("--baseline", type=Path, default=None, help="path to a previous eval JSON used as baseline")
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--skip-finetune", action="store_true")
    p.add_argument("--model-version", default="")
    args = p.parse_args(argv)
    return RunConfig(
        run_id=args.run_id,
        runs_dir=args.runs_dir,
        raw_dir=args.raw_dir,
        tier1_datasets=args.datasets,
        image_datasets=args.image_datasets,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        workers=args.workers,
        eval_label=args.eval_label,
        eval_synth_n=args.eval_synth_n,
        promote=args.promote,
        promote_min_delta=args.promote_min_delta,
        baseline_metrics_path=args.baseline,
        skip_download=args.skip_download,
        skip_finetune=args.skip_finetune,
        model_version=args.model_version,
    )


def main(argv: list[str] | None = None) -> int:
    cfg = _parse(argv)
    summary = run(cfg)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
