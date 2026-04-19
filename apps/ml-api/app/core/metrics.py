"""Prometheus metrics — operational + model-quality.

Operational counters:

- ``heartscan_analyze_latency_seconds`` (histogram): end-to-end /analyze latency.
- ``heartscan_analyze_total`` (counter): outcomes per status (ok/bad_request/...).

Model-quality (plan v2 §J1):

- ``heartscan_analyze_status_total`` (counter): green/yellow/red ratios.
- ``heartscan_analyze_class_total`` (counter): predicted class distribution.
- ``heartscan_analyze_confidence`` (histogram): calibrated confidence.
- ``heartscan_analyze_extraction_quality`` (histogram): final quality score.
- ``heartscan_analyze_non_reportable_total`` (counter): keyed by reason code.
- ``heartscan_analyze_prediction_set_size`` (histogram): conformal set size.
- ``heartscan_analyze_grid_calibrated_total`` (counter): how often BPM is measured vs assumed.
"""

from prometheus_client import Counter, Histogram

REQUEST_LATENCY = Histogram(
    "heartscan_analyze_latency_seconds",
    "Latency of analyze endpoint",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ANALYZE_TOTAL = Counter(
    "heartscan_analyze_total",
    "Analyze requests",
    ["status"],
)

# ---- Quality / model telemetry ------------------------------------------------

ANALYZE_STATUS_TOTAL = Counter(
    "heartscan_analyze_status_total",
    "AnalysisResponse.status distribution (green/yellow/red).",
    ["status"],
)

ANALYZE_CLASS_TOTAL = Counter(
    "heartscan_analyze_class_total",
    "Predicted class distribution.",
    ["class_label"],
)

ANALYZE_CONFIDENCE = Histogram(
    "heartscan_analyze_confidence",
    "Calibrated confidence of predicted class.",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
)

ANALYZE_QUALITY = Histogram(
    "heartscan_analyze_extraction_quality",
    "Final extraction_quality score (post v2 gate).",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

ANALYZE_NON_REPORTABLE = Counter(
    "heartscan_analyze_non_reportable_total",
    "Non-reportable outcomes keyed by reason code.",
    ["reason"],
)

ANALYZE_PREDICTION_SET_SIZE = Histogram(
    "heartscan_analyze_prediction_set_size",
    "Size of conformal prediction set returned to clients.",
    buckets=(1, 2, 3, 4),
)

ANALYZE_GRID_CALIBRATED = Counter(
    "heartscan_analyze_grid_calibrated_total",
    "Whether BPM was measured from the grid (basis label).",
    ["basis"],
)
