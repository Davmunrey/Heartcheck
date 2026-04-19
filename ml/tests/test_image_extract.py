import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from heartscan_ml.image_extract import extract_lead_1d_from_gray, single_lead_to_12


def test_synthetic_trace():
    h, w = 128, 512
    gray = np.ones((h, w), dtype=np.uint8) * 240
    for x in range(w):
        y = int(h // 2 + 20 * np.sin(x / 20.0))
        gray[max(0, y - 1) : min(h, y + 2), x] = 30
    lead, cov = extract_lead_1d_from_gray(gray, target_len=256)
    assert lead.shape[0] == 256
    assert np.isfinite(lead).all()
    assert cov > 0.1
    m12 = single_lead_to_12(lead)
    assert m12.shape == (12, 256)
