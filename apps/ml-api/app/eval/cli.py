"""Command-line entry point for the HeartScan evaluation harness.

Used by the repo-level ``Makefile`` target ``make eval``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.eval.harness import EvalConfig, compare_to_baseline, run_eval, write_report
from app.eval.synth import SynthConfig, generate_dataset

# Release gate thresholds — see docs/MODEL_CARD.md and CONTRIBUTING.md.
MAX_F1_REGRESSION = 0.02  # 2 pts F1 macro
MAX_ECE_REGRESSION = 0.05


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HeartScan evaluation harness")
    p.add_argument("--manifest", type=Path, default=Path("data/synth_v1/manifest.jsonl"))
    p.add_argument(
        "--generate-synth",
        action="store_true",
        help="Generate a fresh synthetic dataset under --synth-out before running eval.",
    )
    p.add_argument("--synth-out", type=Path, default=Path("data/synth_v1"))
    p.add_argument("--synth-n", type=int, default=20, help="samples per class for synth")
    p.add_argument("--out", type=Path, default=Path("eval/reports"))
    p.add_argument("--label", default="candidate")
    p.add_argument("--baseline", type=Path, default=None, help="Previous report JSON to compare.")
    p.add_argument(
        "--gate",
        action="store_true",
        help="Exit non-zero if regression vs --baseline exceeds the release thresholds.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse()
    if args.generate_synth or not args.manifest.is_file():
        cfg = SynthConfig(n_per_class=args.synth_n, out_dir=args.synth_out)
        manifest = generate_dataset(cfg)
        if args.manifest != manifest:
            args.manifest = manifest
        print(f"[harness] generated synthetic manifest at {manifest}")

    report = run_eval(EvalConfig(manifest=args.manifest, label=args.label))
    json_path, html_path = write_report(report, args.out)
    print(f"[harness] wrote {json_path}")
    print(f"[harness] wrote {html_path}")

    summary = {
        "f1_macro": report.classification["f1_macro"],
        "accuracy": report.classification["accuracy"],
        "ece": report.calibration["ece"],
        "p95_ms": report.latency_ms["p95"],
        "abstention_rate": report.abstention_rate,
    }
    print("[harness] summary:", json.dumps(summary, indent=2))

    if args.baseline:
        deltas = compare_to_baseline(report, args.baseline)
        print("[harness] vs baseline:", json.dumps(deltas, indent=2))
        if args.gate:
            failures = []
            if -deltas["delta_f1_macro"] > MAX_F1_REGRESSION:
                failures.append(
                    f"F1 macro regressed by {-deltas['delta_f1_macro']:.4f} (>{MAX_F1_REGRESSION})"
                )
            if deltas["delta_ece"] > MAX_ECE_REGRESSION:
                failures.append(
                    f"ECE worsened by {deltas['delta_ece']:.4f} (>{MAX_ECE_REGRESSION})"
                )
            if failures:
                print("[harness][gate] FAILED:", "; ".join(failures))
                return 2
            print("[harness][gate] PASSED")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
