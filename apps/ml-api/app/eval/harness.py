"""Run the analysis pipeline over a labelled dataset and emit a report.

Usage (programmatic):

    from app.eval.harness import run_eval, EvalConfig
    report = run_eval(EvalConfig(manifest=Path("data/synth_v1/manifest.jsonl")))

The CLI wrapper lives in :mod:`app.eval.cli` and is the entry point for
``make eval``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.eval import metrics as M
from app.eval.synth import CLASS_NAMES, CLASS_TO_ID
from app.services.analysis_pipeline import run_analysis


@dataclass
class EvalConfig:
    manifest: Path
    out_dir: Path = Path("eval/reports")
    label: str = "candidate"
    baseline_report: Path | None = None  # path to a previous JSON for comparison


@dataclass
class EvalReport:
    label: str
    timestamp: str
    n_samples: int
    classification: dict[str, Any]
    calibration: dict[str, float]
    abstention_rate: float
    latency_ms: dict[str, float]
    per_sample: list[dict[str, Any]] = field(default_factory=list)


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _confidence_to_probs(class_label: str, confidence: float) -> np.ndarray:
    """Map a single (label, confidence) into a soft probability vector.

    The pipeline currently returns one label and one confidence; we distribute
    the residual ``(1 - confidence)`` uniformly across the other classes. This
    is a deliberate, conservative choice for the harness so calibration metrics
    are well defined; future iterations exposing real softmax should override.
    """
    probs = np.full(len(CLASS_NAMES), (1.0 - confidence) / max(1, len(CLASS_NAMES) - 1))
    if class_label in CLASS_TO_ID:
        probs[CLASS_TO_ID[class_label]] = confidence
    else:
        probs[:] = 1.0 / len(CLASS_NAMES)
    return probs


def run_eval(cfg: EvalConfig) -> EvalReport:
    items = _load_manifest(cfg.manifest)
    settings = get_settings()
    base_dir = cfg.manifest.parent

    y_true: list[int] = []
    y_pred: list[int] = []
    probs_list: list[np.ndarray] = []
    latencies_ms: list[float] = []
    abstain_flags: list[str | None] = []
    per_sample: list[dict[str, Any]] = []

    for item in items:
        label_id = int(item["label_id"])
        img_path = base_dir / item["file"]
        with img_path.open("rb") as f:
            data = f.read()
        t0 = time.perf_counter()
        result = run_analysis(
            data,
            settings,
            request_id=f"eval-{item['file']}",
            accept_language="en",
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

        pred_label = result.class_label
        pred_id = CLASS_TO_ID.get(pred_label, -1)
        # Treat any non-reportable status (red + extraction issues) as an
        # abstention candidate for the abstention metric. We still record a
        # prediction for accuracy/calibration so a model that always says
        # "noise" cannot game the metrics.
        is_abstain = result.status == "red" and pred_label == "noise"
        abstain_flags.append(None if is_abstain else pred_label)

        y_true.append(label_id)
        y_pred.append(pred_id if pred_id >= 0 else CLASS_TO_ID["noise"])
        probs_list.append(_confidence_to_probs(pred_label, result.confidence_score))
        per_sample.append(
            {
                "file": item["file"],
                "label": item["label"],
                "predicted": pred_label,
                "status": result.status,
                "confidence": result.confidence_score,
                "extraction_quality": result.extraction_quality,
                "bpm": result.bpm,
                "latency_ms": elapsed_ms,
            }
        )

    yt = np.array(y_true)
    yp = np.array(y_pred)
    probs = np.stack(probs_list) if probs_list else np.zeros((0, len(CLASS_NAMES)))

    cls = M.classification_report(yt, yp, list(CLASS_NAMES))
    ece = M.expected_calibration_error(yt, probs) if len(yt) else 0.0
    brier = M.brier_score_multiclass(yt, probs, len(CLASS_NAMES)) if len(yt) else 0.0
    auroc = M.confidence_correctness_auroc(yt, probs) if len(yt) else 0.5

    report = EvalReport(
        label=cfg.label,
        timestamp=datetime.now(timezone.utc).isoformat(),
        n_samples=len(items),
        classification={
            "accuracy": cls.accuracy,
            "f1_macro": cls.f1_macro,
            "f1_per_class": cls.f1_per_class,
            "confusion": cls.confusion,
            "support": cls.support,
            "class_names": list(CLASS_NAMES),
        },
        calibration={
            "ece": ece,
            "brier": brier,
            "confidence_correctness_auroc": auroc,
        },
        abstention_rate=M.abstention_rate(abstain_flags),
        latency_ms={
            "p50": M.percentile(latencies_ms, 50),
            "p95": M.percentile(latencies_ms, 95),
            "mean": float(np.mean(latencies_ms)) if latencies_ms else 0.0,
        },
        per_sample=per_sample,
    )
    return report


def write_report(report: EvalReport, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"{stamp}_{report.label}.json"
    html_path = out_dir / f"{stamp}_{report.label}.html"
    payload = {
        "label": report.label,
        "timestamp": report.timestamp,
        "n_samples": report.n_samples,
        "classification": report.classification,
        "calibration": report.calibration,
        "abstention_rate": report.abstention_rate,
        "latency_ms": report.latency_ms,
        "per_sample": report.per_sample,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html_path.write_text(_render_html(payload), encoding="utf-8")
    return json_path, html_path


def _render_html(payload: dict[str, Any]) -> str:
    cls = payload["classification"]
    cal = payload["calibration"]
    lat = payload["latency_ms"]
    confusion_rows = "".join(
        "<tr><th>{name}</th>".format(name=cls["class_names"][i])
        + "".join(f"<td>{v}</td>" for v in row)
        + "</tr>"
        for i, row in enumerate(cls["confusion"])
    )
    confusion_header = "".join(f"<th>{n}</th>" for n in cls["class_names"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>HeartScan eval — {payload['label']}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:1rem;color:#111}}
h1{{font-size:1.4rem}} table{{border-collapse:collapse;margin:1rem 0}}
th,td{{border:1px solid #ccc;padding:0.4rem 0.7rem;text-align:right}}
th:first-child{{text-align:left;background:#f7f7f7}}
.kv{{display:grid;grid-template-columns:200px 1fr;gap:0.4rem 1rem;margin:1rem 0}}
.kv dt{{color:#555}} .kv dd{{margin:0;font-weight:600}}
</style></head><body>
<h1>HeartScan eval — {payload['label']}</h1>
<p>{payload['timestamp']} · {payload['n_samples']} samples</p>
<dl class="kv">
  <dt>Accuracy</dt><dd>{cls['accuracy']:.4f}</dd>
  <dt>F1 macro</dt><dd>{cls['f1_macro']:.4f}</dd>
  <dt>ECE</dt><dd>{cal['ece']:.4f}</dd>
  <dt>Brier</dt><dd>{cal['brier']:.4f}</dd>
  <dt>Confidence vs correctness AUROC</dt><dd>{cal['confidence_correctness_auroc']:.4f}</dd>
  <dt>Abstention rate</dt><dd>{payload['abstention_rate']:.4f}</dd>
  <dt>Latency p50 / p95 / mean (ms)</dt><dd>{lat['p50']:.1f} / {lat['p95']:.1f} / {lat['mean']:.1f}</dd>
</dl>
<h2>F1 per class</h2>
<table><tr><th>Class</th><th>F1</th><th>Support</th></tr>
{''.join(f"<tr><th>{n}</th><td>{cls['f1_per_class'][n]:.4f}</td><td>{cls['support'][i]}</td></tr>" for i, n in enumerate(cls['class_names']))}
</table>
<h2>Confusion matrix (rows=true, cols=pred)</h2>
<table><tr><th></th>{confusion_header}</tr>{confusion_rows}</table>
</body></html>"""


def compare_to_baseline(candidate: EvalReport, baseline_path: Path) -> dict[str, Any]:
    """Return regression deltas vs a previously stored baseline JSON."""
    base = json.loads(baseline_path.read_text(encoding="utf-8"))
    return {
        "delta_f1_macro": candidate.classification["f1_macro"] - base["classification"]["f1_macro"],
        "delta_accuracy": candidate.classification["accuracy"] - base["classification"]["accuracy"],
        "delta_ece": candidate.calibration["ece"] - base["calibration"]["ece"],
        "delta_p95_ms": candidate.latency_ms["p95"] - base["latency_ms"]["p95"],
    }
