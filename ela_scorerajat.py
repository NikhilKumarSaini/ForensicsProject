import os
import numpy as np
from PIL import Image


def _patch_means(gray: np.ndarray, grid: int = 48) -> np.ndarray:
    h, w = gray.shape
    ph = max(h // grid, 8)
    pw = max(w // grid, 8)

    vals = []
    for y in range(0, h, ph):
        for x in range(0, w, pw):
            patch = gray[y:y + ph, x:x + pw]
            if patch.size == 0:
                continue

            active = patch[patch > 2.0]
            if active.size < 0.15 * patch.size:
                continue

            vals.append(float(active.mean()) / 255.0)

    return np.array(vals, dtype=np.float32)


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA manipulation score (0..1) from ELA images.

    Uses patch-based tail/outlier ratios.
    This avoids global brightness saturation and focuses on local anomalies.
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    metrics = []

    for name in os.listdir(ela_dir):
        if not name.lower().endswith(".jpg"):
            continue

        path = os.path.join(ela_dir, name)

        try:
            with Image.open(path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        vals = _patch_means(gray, grid=48)
        if vals.size < 30:
            continue

        p50 = float(np.percentile(vals, 50))
        p90 = float(np.percentile(vals, 90))
        p99 = float(np.percentile(vals, 99))
        eps = 1e-6

        tail_ratio = (p99 + eps) / (p50 + eps)
        spike_ratio = (p99 - p90) / (p90 + eps)

        metrics.append(0.7 * (tail_ratio - 1.0) + 0.3 * spike_ratio)

    if not metrics:
        return 0.0

    m = float(max(metrics))

    # Mapping to 0..1
    if m < 0.60:
        return 0.0
    if m < 1.00:
        return float(round(0.05 + (m - 0.60) / 0.40 * 0.15, 3))
    if m < 1.60:
        return float(round(0.20 + (m - 1.00) / 0.60 * 0.30, 3))

    return float(round(min(1.0, 0.50 + (m - 1.60) / 1.00 * 0.50), 3))
