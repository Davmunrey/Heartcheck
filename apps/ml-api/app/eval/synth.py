"""Deterministic synthetic dataset of paper-rendered ECG photos.

This module is intentionally **independent of PTB-XL**: it generates labelled
samples from analytic templates so the harness can run in CI and on a fresh
laptop without external datasets. When a real PTB-XL renderer is plugged in
(``ml/heartscan_ml``), it should obey the same on-disk schema: one PNG per
sample plus a JSONL manifest with ``(filename, label, label_id)``.

Manifest schema
---------------
::

    {"file": "synth_000001.png", "label": "normal",     "label_id": 0}
    {"file": "synth_000002.png", "label": "arrhythmia", "label_id": 1}
    {"file": "synth_000003.png", "label": "noise",      "label_id": 2}

Augmentations applied per sample (seeded by ``--seed`` for reproducibility):

- random perspective skew up to ``±perspective_max`` degrees;
- Gaussian blur with sigma sampled in ``[0, blur_max]``;
- additive Gaussian noise with sigma sampled in ``[0, noise_max]``;
- multiplicative shading (uneven lighting);
- optional glare (bright Gaussian blob) with probability ``glare_prob``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

CLASS_NAMES = ("normal", "arrhythmia", "noise")
CLASS_TO_ID = {name: i for i, name in enumerate(CLASS_NAMES)}


@dataclass
class SynthConfig:
    n_per_class: int = 30
    out_dir: Path = Path("data/synth_v1")
    seed: int = 1234
    width: int = 800
    height: int = 240
    grid_px: int = 20  # 5 mm small square at ~25 mm/s, 20 px ~= 5 mm
    perspective_max: float = 8.0
    blur_max: float = 1.6
    noise_max: float = 8.0
    glare_prob: float = 0.2


def _draw_grid(img: np.ndarray, grid_px: int) -> None:
    h, w = img.shape
    fine_color = 235
    bold_color = 200
    for x in range(0, w, grid_px):
        img[:, x] = fine_color
    for y in range(0, h, grid_px):
        img[y, :] = fine_color
    for x in range(0, w, grid_px * 5):
        img[:, x] = bold_color
    for y in range(0, h, grid_px * 5):
        img[y, :] = bold_color


def _ecg_template(label: str, width: int, height: int, rng: np.random.Generator) -> np.ndarray:
    """Return ``y(x)`` in pixels for ``x in [0, width)``."""
    base = height // 2
    x = np.arange(width, dtype=np.float64)
    if label == "noise":
        return base + rng.normal(0, 8, size=width)

    bpm = rng.uniform(60, 80) if label == "normal" else rng.uniform(45, 130)
    samples_per_beat = max(20.0, 60.0 / bpm * 200.0)  # arbitrary horizontal scale
    if label == "arrhythmia":
        # jitter beat positions to break regularity
        jitter = rng.normal(0, samples_per_beat * 0.18, size=int(width / samples_per_beat) + 4)
    else:
        jitter = np.zeros(int(width / samples_per_beat) + 4)
    beat_centers: list[float] = []
    pos = rng.uniform(samples_per_beat * 0.3, samples_per_beat)
    i = 0
    while pos < width:
        beat_centers.append(pos + jitter[i])
        pos += samples_per_beat
        i += 1
    y = np.full(width, base, dtype=np.float64)
    for c in beat_centers:
        y += -60.0 * np.exp(-((x - c) ** 2) / (2.0 * (samples_per_beat * 0.05) ** 2))  # R peak
        y += 18.0 * np.exp(-((x - c - samples_per_beat * 0.08) ** 2) / (2.0 * (samples_per_beat * 0.06) ** 2))  # S
        y += -10.0 * np.exp(-((x - c - samples_per_beat * 0.18) ** 2) / (2.0 * (samples_per_beat * 0.1) ** 2))  # T
    return y


def _draw_trace(img: np.ndarray, y_signal: np.ndarray) -> None:
    h, w = img.shape
    for xi in range(w):
        yv = int(round(y_signal[xi]))
        if 0 <= yv < h:
            img[max(0, yv - 1) : min(h, yv + 2), xi] = 30


def _apply_perspective(img: np.ndarray, max_deg: float, rng: np.random.Generator) -> np.ndarray:
    if max_deg <= 0:
        return img
    try:
        import cv2
    except ImportError:
        return img
    h, w = img.shape
    angle = math.radians(rng.uniform(-max_deg, max_deg))
    shift = h * math.tan(angle) * 0.2
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[0, shift], [w, 0], [w, h - shift], [0, h]])
    m = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, m, (w, h), borderValue=255)


def _apply_blur_noise(img: np.ndarray, blur: float, noise: float) -> np.ndarray:
    out = img.astype(np.float64)
    if blur > 0:
        try:
            import cv2

            k = max(1, int(round(blur * 2)) * 2 + 1)
            out = cv2.GaussianBlur(out, (k, k), blur)
        except ImportError:
            pass
    if noise > 0:
        rng = np.random.default_rng()  # noise can be unseeded for variety
        out = out + rng.normal(0, noise, size=out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def _apply_shading(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    h, w = img.shape
    grad_x = np.linspace(rng.uniform(0.85, 1.0), rng.uniform(0.85, 1.0), w)
    grad_y = np.linspace(rng.uniform(0.85, 1.0), rng.uniform(0.85, 1.0), h)
    field = grad_y[:, None] * grad_x[None, :]
    return np.clip(img.astype(np.float64) * field, 0, 255).astype(np.uint8)


def _apply_glare(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    h, w = img.shape
    cx, cy = rng.integers(0, w), rng.integers(0, h)
    sigma = rng.uniform(min(h, w) * 0.1, min(h, w) * 0.25)
    yy, xx = np.mgrid[0:h, 0:w]
    blob = 80.0 * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma * sigma)))
    return np.clip(img.astype(np.float64) + blob, 0, 255).astype(np.uint8)


def render_one(label: str, cfg: SynthConfig, sample_seed: int) -> np.ndarray:
    rng = np.random.default_rng(sample_seed)
    img = np.full((cfg.height, cfg.width), 250, dtype=np.uint8)
    _draw_grid(img, cfg.grid_px)
    y_signal = _ecg_template(label, cfg.width, cfg.height, rng)
    _draw_trace(img, y_signal)
    img = _apply_perspective(img, cfg.perspective_max, rng)
    img = _apply_shading(img, rng)
    if rng.random() < cfg.glare_prob:
        img = _apply_glare(img, rng)
    blur = float(rng.uniform(0.0, cfg.blur_max))
    noise = float(rng.uniform(0.0, cfg.noise_max))
    return _apply_blur_noise(img, blur, noise)


def generate_dataset(cfg: SynthConfig) -> Path:
    """Write PNGs + ``manifest.jsonl`` to ``cfg.out_dir``. Returns the manifest path."""
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("opencv-python-headless required for synth generation") from exc

    out_dir = cfg.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"
    rng = np.random.default_rng(cfg.seed)
    counter = 0
    with manifest_path.open("w", encoding="utf-8") as mf:
        for label in CLASS_NAMES:
            for _ in range(cfg.n_per_class):
                counter += 1
                sample_seed = int(rng.integers(0, 2**31 - 1))
                img = render_one(label, cfg, sample_seed)
                fname = f"synth_{counter:06d}.png"
                cv2.imwrite(str(out_dir / fname), img)
                mf.write(
                    json.dumps(
                        {"file": fname, "label": label, "label_id": CLASS_TO_ID[label]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    return manifest_path


def _parse_args() -> SynthConfig:
    p = argparse.ArgumentParser(description="Generate synthetic ECG-photo dataset")
    p.add_argument("--out", default="data/synth_v1", type=Path)
    p.add_argument("--n", type=int, default=30, help="samples per class")
    p.add_argument("--seed", type=int, default=1234)
    args = p.parse_args()
    return SynthConfig(n_per_class=args.n, out_dir=args.out, seed=args.seed)


def main() -> None:
    cfg = _parse_args()
    path = generate_dataset(cfg)
    print(f"Wrote {path} with {cfg.n_per_class * len(CLASS_NAMES)} samples in {cfg.out_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
