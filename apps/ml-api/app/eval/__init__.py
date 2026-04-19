"""Evaluation harness for HeartScan.

Submodules:
- ``metrics``: classification, calibration, abstention, latency.
- ``synth``: deterministic synthetic ECG photo dataset (paper-rendered).
- ``harness``: run baseline + candidate over a labelled set and emit a report.
- ``cli``: ``python -m app.eval.cli`` entry point used by ``make eval``.
"""
