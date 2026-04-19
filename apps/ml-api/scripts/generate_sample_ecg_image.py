#!/usr/bin/env python3
"""Generate a small synthetic ECG-like PNG for local demos."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def main() -> None:
    import cv2

    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "web_public" / "static" / "sample_ecg.png")
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 900, 280
    img = np.ones((h, w, 3), dtype=np.uint8) * 255
    # light pink grid
    for x in range(0, w, 20):
        cv2.line(img, (x, 0), (x, h), (255, 230, 240), 1)
    for y in range(0, h, 20):
        cv2.line(img, (0, y), (w, y), (255, 230, 240), 1)

    pts = []
    for x in range(40, w - 40, 2):
        y = int(h / 2 + 35 * np.sin(x / 45.0) + 8 * np.sin(x / 12.0))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        cv2.line(img, pts[i], pts[i + 1], (40, 40, 60), 2)

    cv2.imwrite(str(args.out), img)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
