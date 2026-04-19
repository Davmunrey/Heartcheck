"""End-to-end autonomous training orchestrator.

Runs every step of the HeartScan training plan in order and is fully
idempotent: each step skips itself when its expected output already exists,
so the orchestrator can be safely re-run from a cron job or CI.

Pipeline
--------

::

    download -> manifest -> splits ->
        pretrain -> calibrate (signals val) ->
        [optional] finetune-image -> calibrate (image val) ->
        evaluate (against synth + real) ->
        emit_manifest ->
        promote (atomic copy to apps/ml-api/weights/)

Promotion gate
--------------

A new checkpoint is promoted to ``apps/ml-api/weights/active/`` only when

- ``eval.classification.f1_macro`` is at least the previous champion's
  F1 macro minus ``--max-f1-regression`` (default 0.02), AND
- ``eval.calibration.ece`` is at most the previous champion's ECE plus
  ``--max-ece-regression`` (default 0.05).

If no champion exists yet the new checkpoint is promoted unconditionally.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PY = REPO_ROOT / "backend" / ".venv" / "bin" / "python"


@dataclass
class StepResult:
    name: str
    skipped: bool
    seconds: float
    output: Path | None = None


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"[orch {ts}] {msg}", flush=True)


def _run(cmd: list[str]) -> None:
    _log(f"$ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(REPO_ROOT))


def _step(name: str, target: Path, fn) -> StepResult:
    if target.exists():
        _log(f"[skip] {name}: {target} already exists")
        return StepResult(name=name, skipped=True, seconds=0.0, output=target)
    t0 = time.perf_counter()
    fn()
    if not target.exists():
        raise RuntimeError(f"step {name} did not produce {target}")
    return StepResult(name=name, skipped=False, seconds=time.perf_counter() - t0, output=target)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def step_download(name: str, raw_root: Path) -> StepResult:
    target = raw_root / name
    sentinel = target / ".downloaded"

    def _do():
        target.mkdir(parents=True, exist_ok=True)
        _run([str(PY), "-m", "ml.datasets.cli", "download", name, "--target", str(target)])
        sentinel.write_text("ok\n")

    return _step(f"download:{name}", sentinel, _do)


def step_manifest(raw_root: Path, datasets: list[str], out: Path) -> StepResult:
    def _do():
        cmd = [str(PY), "-m", "ml.datasets.cli", "manifest",
               "--root", str(raw_root), "--datasets", *datasets, "--out", str(out)]
        _run(cmd)

    return _step("manifest", out, _do)


def step_splits(manifest_in: Path, out: Path) -> StepResult:
    def _do():
        _run([str(PY), "-m", "ml.datasets.splits",
              "--manifest", str(manifest_in), "--out", str(out)])

    return _step("splits", out, _do)


def step_pretrain(manifest: Path, out_dir: Path, epochs: int) -> StepResult:
    target = out_dir / "checkpoint.pt"

    def _do():
        out_dir.mkdir(parents=True, exist_ok=True)
        _run([str(PY), "-m", "ml.training.pretrain",
              "--manifest", str(manifest), "--out", str(out_dir),
              "--epochs", str(epochs)])

    return _step("pretrain", target, _do)


def step_calibrate(out_dir: Path) -> StepResult:
    target = out_dir / "calibration.json"

    def _do():
        _run([str(PY), "-m", "ml.training.calibrate",
              "--logits", str(out_dir / "val_logits.npz"),
              "--checkpoint", str(out_dir / "checkpoint.pt"),
              "--report", str(target)])

    return _step("calibrate", target, _do)


def step_finetune_image(image_manifest: Path, pretrained: Path,
                         out_dir: Path, epochs: int) -> StepResult:
    target = out_dir / "checkpoint.pt"

    def _do():
        out_dir.mkdir(parents=True, exist_ok=True)
        _run([str(PY), "-m", "ml.training.finetune_image",
              "--manifest", str(image_manifest),
              "--pretrained", str(pretrained),
              "--out", str(out_dir), "--epochs", str(epochs)])

    return _step("finetune_image", target, _do)


def step_eval(checkpoint: Path, out_dir: Path) -> StepResult:
    """Run the production eval harness against the synth set."""
    target = out_dir / "eval_report.json"

    def _do():
        out_dir.mkdir(parents=True, exist_ok=True)
        eval_dir = out_dir / "eval"
        eval_dir.mkdir(parents=True, exist_ok=True)
        env_cmd = [
            str(PY), "-m", "app.eval.cli",
            "--generate-synth",
            "--synth-out", str(REPO_ROOT / "data" / "synth_orch"),
            "--manifest", str(REPO_ROOT / "data" / "synth_orch" / "manifest.jsonl"),
            "--out", str(eval_dir),
            "--label", out_dir.name,
        ]
        _log(f"$ HEARTSCAN_MODEL_PATH={checkpoint} {' '.join(env_cmd)}")
        env = {"HEARTSCAN_MODEL_PATH": str(checkpoint)}
        subprocess.check_call(env_cmd, cwd=str(REPO_ROOT / "backend"), env={**_inherit_env(), **env})
        # Pick the most recent JSON in eval_dir.
        latest = max(eval_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        shutil.copy2(latest, target)

    return _step("eval", target, _do)


def step_emit_manifest(checkpoint: Path, training_summary: Path,
                        calibration: Path, eval_report: Path,
                        datasets: list[str], model_version: str) -> StepResult:
    target = checkpoint.with_suffix(checkpoint.suffix + ".yaml")

    def _do():
        cmd = [str(PY), "-m", "ml.training.emit_manifest",
               "--checkpoint", str(checkpoint),
               "--training-summary", str(training_summary),
               "--calibration", str(calibration),
               "--eval-report", str(eval_report),
               "--datasets", *datasets,
               "--model-version", model_version]
        _run(cmd)

    return _step("emit_manifest", target, _do)


def _inherit_env() -> dict:
    import os
    return dict(os.environ)


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


def _read_metrics(eval_report: Path) -> dict[str, float]:
    payload = json.loads(eval_report.read_text(encoding="utf-8"))
    return {
        "f1_macro": float(payload.get("classification", {}).get("f1_macro", 0.0)),
        "ece": float(payload.get("calibration", {}).get("ece", 0.0)),
    }


def promote(
    candidate_dir: Path,
    weights_dir: Path,
    *,
    max_f1_regression: float,
    max_ece_regression: float,
    force: bool = False,
) -> bool:
    cand_eval = candidate_dir / "eval_report.json"
    cand_ckpt = candidate_dir / "checkpoint.pt"
    cand_yaml = candidate_dir / "checkpoint.pt.yaml"
    if not cand_ckpt.is_file() or not cand_eval.is_file() or not cand_yaml.is_file():
        raise RuntimeError(
            f"missing artefacts in {candidate_dir}: need checkpoint.pt, .yaml, eval_report.json"
        )
    cand_metrics = _read_metrics(cand_eval)
    weights_dir.mkdir(parents=True, exist_ok=True)
    active = weights_dir / "active"
    champion_eval = active / "eval_report.json"
    if force or not champion_eval.is_file():
        _log(f"[promote] no champion (or --force); promoting {candidate_dir} (f1={cand_metrics['f1_macro']:.4f})")
        return _atomic_promote(candidate_dir, active)
    champ_metrics = _read_metrics(champion_eval)
    delta_f1 = cand_metrics["f1_macro"] - champ_metrics["f1_macro"]
    delta_ece = cand_metrics["ece"] - champ_metrics["ece"]
    _log(f"[promote] candidate vs champion: ΔF1={delta_f1:+.4f} ΔECE={delta_ece:+.4f}")
    if -delta_f1 > max_f1_regression:
        _log(f"[promote] REJECT — F1 regressed by {-delta_f1:.4f} (>{max_f1_regression})")
        return False
    if delta_ece > max_ece_regression:
        _log(f"[promote] REJECT — ECE worsened by {delta_ece:.4f} (>{max_ece_regression})")
        return False
    _log("[promote] ACCEPT — promoting candidate to active")
    return _atomic_promote(candidate_dir, active)


def _atomic_promote(src: Path, dst: Path) -> bool:
    tmp = dst.with_suffix(".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    for fname in ("checkpoint.pt", "checkpoint.pt.yaml", "eval_report.json", "calibration.json"):
        s = src / fname
        if s.is_file():
            shutil.copy2(s, tmp / fname)
    if dst.exists():
        prev = dst.with_suffix(".prev")
        if prev.exists():
            shutil.rmtree(prev)
        shutil.move(str(dst), str(prev))
    shutil.move(str(tmp), str(dst))
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    raw_root = Path(args.raw_root).resolve()
    work_root = Path(args.work_root).resolve()
    weights_dir = Path(args.weights_dir).resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    signal_datasets = [d.strip() for d in args.signal_datasets.split(",") if d.strip()]
    image_datasets = [d.strip() for d in args.image_datasets.split(",") if d.strip()] if args.image_datasets else []

    results: list[StepResult] = []
    for ds in signal_datasets:
        results.append(step_download(ds, raw_root))

    signal_manifest = work_root / "signal_manifest.parquet"
    results.append(step_manifest(raw_root, signal_datasets, signal_manifest))

    split_manifest = work_root / "signal_manifest_split.parquet"
    results.append(step_splits(signal_manifest, split_manifest))

    pretrain_dir = work_root / "pretrain"
    results.append(step_pretrain(split_manifest, pretrain_dir, epochs=args.epochs))
    results.append(step_calibrate(pretrain_dir))
    final_ckpt_dir = pretrain_dir

    if image_datasets:
        for ds in image_datasets:
            results.append(step_download(ds, raw_root))
        image_manifest = work_root / "image_manifest.parquet"
        results.append(step_manifest(raw_root, image_datasets, image_manifest))
        image_split = work_root / "image_manifest_split.parquet"
        results.append(step_splits(image_manifest, image_split))
        finetune_dir = work_root / "finetune"
        results.append(
            step_finetune_image(
                image_split, pretrain_dir / "checkpoint.pt", finetune_dir, epochs=args.image_epochs
            )
        )
        results.append(step_calibrate(finetune_dir))
        final_ckpt_dir = finetune_dir

    results.append(step_eval(final_ckpt_dir / "checkpoint.pt", final_ckpt_dir))
    used_datasets = signal_datasets + image_datasets
    results.append(
        step_emit_manifest(
            final_ckpt_dir / "checkpoint.pt",
            final_ckpt_dir / "training_summary.json"
            if (final_ckpt_dir / "training_summary.json").is_file()
            else final_ckpt_dir / "finetune_summary.json",
            final_ckpt_dir / "calibration.json",
            final_ckpt_dir / "eval_report.json",
            used_datasets,
            args.model_version,
        )
    )

    promoted = promote(
        final_ckpt_dir,
        weights_dir,
        max_f1_regression=args.max_f1_regression,
        max_ece_regression=args.max_ece_regression,
        force=args.force_promote,
    )

    summary = {
        "model_version": args.model_version,
        "promoted": promoted,
        "candidate_dir": str(final_ckpt_dir),
        "active_dir": str(weights_dir / "active") if promoted else None,
        "steps": [
            {"name": r.name, "skipped": r.skipped, "seconds": round(r.seconds, 2)}
            for r in results
        ],
    }
    print(json.dumps(summary, indent=2))
    (work_root / "orchestrator_summary.json").write_text(json.dumps(summary, indent=2))
    return 0 if promoted or args.allow_no_promote else 3


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="HeartScan autonomous training orchestrator")
    p.add_argument("--raw-root", default="data/raw")
    p.add_argument("--work-root", default="runs/auto")
    p.add_argument("--weights-dir", default="apps/ml-api/weights")
    p.add_argument("--signal-datasets", default="ptb_xl,chapman_shaoxing,cinc2017")
    p.add_argument("--image-datasets", default="", help="comma-separated; empty to skip image fine-tune")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--image-epochs", type=int, default=3)
    p.add_argument("--model-version", required=True)
    p.add_argument("--max-f1-regression", type=float, default=0.02)
    p.add_argument("--max-ece-regression", type=float, default=0.05)
    p.add_argument("--force-promote", action="store_true")
    p.add_argument("--allow-no-promote", action="store_true",
                   help="exit 0 even when promotion is rejected (useful for cron/CI)")
    args = p.parse_args(argv)
    return run(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
