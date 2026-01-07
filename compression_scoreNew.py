import os
import numpy as np
from PIL import Image


def _patch_values(gray: np.ndarray, grid: int = 60) -> np.ndarray:
    h, w = gray.shape
    ph = max(h // grid, 10)
    pw = max(w // grid, 10)

    vals = []
    for y in range(0, h, ph):
        for x in range(0, w, pw):
            patch = gray[y:y + ph, x:x + pw]
            if patch.size == 0:
                continue

            active = patch > 2.0
            if active.mean() < 0.12:
                continue

            vals.append(float(patch[active].mean()) / 255.0)

    return np.array(vals, dtype=np.float32)


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compression score (0..1) from Compression diff images.

    Fixes:
    - Low-content guard like ELA
    - More aggressive mapping so manipulated rises above 0.1–0.2 range
    """
    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    page_scores = []

    for name in os.listdir(comp_dir):
        if not name.lower().endswith(".jpg"):
            continue

        path = os.path.join(comp_dir, name)
        try:
            with Image.open(path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        active_fraction = float((gray > 2.0).mean())
        if active_fraction < 0.015:
            page_scores.append(0.0)
            continue

        vals = _patch_values(gray, grid=60)
        if vals.size < 120:
            page_scores.append(0.0)
            continue

        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med))) + 1e-6
        thresh = med + 3.0 * mad

        ratio = float(np.count_nonzero(vals > thresh)) / float(vals.size)

        if med < 0.03 and ratio < 0.06:
            page_scores.append(0.0)
            continue

        # Mapping
        if ratio < 0.01:
            score = 0.0
        elif ratio < 0.03:
            score = 0.10 + (ratio - 0.01) / 0.02 * 0.30  # 0.10 -> 0.40
        elif ratio < 0.08:
            score = 0.40 + (ratio - 0.03) / 0.05 * 0.40  # 0.40 -> 0.80
        else:
            score = 0.80 + min(0.20, (ratio - 0.08) / 0.10 * 0.20)

        page_scores.append(float(score))

    if not page_scores:
        return 0.0

    return float(round(min(1.0, max(page_scores)), 3))
