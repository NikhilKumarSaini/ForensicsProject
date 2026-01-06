# ela_score.py
import os
from typing import Tuple

from PIL import Image
import numpy as np


def _page_patch_features(
    arr: np.ndarray,
    grid: int = 32,
    background_threshold: float = 1.0,
) -> Tuple[float, float]:
    """
    Compute patch-based features for a single ELA page.

    Returns
    -------
    max_z : float
        Maximum robust z-score of patch means (only positive outliers).
    max_mean_norm : float
        Maximum patch mean intensity, normalized to [0, 1].
    """
    h, w = arr.shape
    if h == 0 or w == 0:
        return 0.0, 0.0

    # Focus on central content region; crop margins (bank logo, viewer chrome)
    top_margin = int(0.10 * h)
    bottom_margin = int(0.05 * h)
    left_margin = int(0.08 * w)
    right_margin = int(0.08 * w)

    y0 = top_margin
    y1 = max(y0 + 1, h - bottom_margin)
    x0 = left_margin
    x1 = max(x0 + 1, w - right_margin)

    arr = arr[y0:y1, x0:x1]
    h, w = arr.shape
    if h == 0 or w == 0:
        return 0.0, 0.0

    # Patch size; ensure at least 1 pixel per patch
    ph = max(h // grid, 1)
    pw = max(w // grid, 1)

    patch_means = []

    for y_start in range(0, h, ph):
        y_end = min(h, y_start + ph)
        for x_start in range(0, w, pw):
            x_end = min(w, x_start + pw)

            patch = arr[y_start:y_end, x_start:x_end]

            # Ignore patches that are essentially background
            active = patch[patch > background_threshold]
            if active.size == 0:
                continue

            patch_means.append(float(active.mean()))

    if not patch_means:
        return 0.0, 0.0

    means = np.array(patch_means, dtype=np.float32)

    # Normalize to [0, 1]
    means_norm = means / 255.0
    max_mean_norm = float(np.max(means_norm))

    # Robust z-scores for outlier strength
    median = float(np.median(means_norm))
    mad = float(np.median(np.abs(means_norm - median)))

    if mad < 1e-6:
        return 0.0, max_mean_norm

    z_scores = (means_norm - median) / (mad + 1e-6)
    max_z = float(np.max(z_scores))

    if max_z < 0.0:
        max_z = 0.0

    return max_z, max_mean_norm


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Compute ELA-based manipulation score in [0, 1].

    Goal
    ----
    - Clean digital / programmatic bank statements:
        Score ≈ 0 or very small (0.0xx).
    - Manipulated statements:
        Higher scores, to combine with compression / noise / metadata scores.

    For each ELA JPEG in <forensic_output_dir>/ELA:
        - Convert to grayscale.
        - Compute:
            * max_z: strongest positive robust z-score of patch means.
            * max_mean_norm: brightest patch mean (0–1).
    For the document:
        - doc_z         = max(max_z over pages)
        - doc_mean      = max(max_mean_norm over pages)
        - doc_med_mean  = median(max_mean_norm over pages)
        - bright_spike  = max(doc_mean - doc_med_mean, 0)
    Scoring:
        - If outlier strength and brightness are small → 0.0 (clean).
        - Else map outlier strength and brightness spike into [0, 1].
    """
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_zs = []
    page_means = []

    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(ela_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        max_z, max_mean_norm = _page_patch_features(arr)
        page_zs.append(max_z)
        page_means.append(max_mean_norm)

    if not page_zs:
        return 0.0

    doc_z = float(max(page_zs))
    doc_mean = float(max(page_means))
    doc_med_mean = float(np.median(page_means))
    bright_spike = max(0.0, doc_mean - doc_med_mean)

    # ------------ EARLY CLEAN CHECK ------------
    # These thresholds are intentionally conservative so
    # programmatic statements with only regular text and
    # watermark behaviour collapse to 0.
    Z_MIN_SUSPICIOUS = 4.0       # robust z above this suggests a local anomaly
    MEAN_MIN_SUSPICIOUS = 0.30   # need non-trivial ELA brightness in some patch

    if doc_z < Z_MIN_SUSPICIOUS or doc_mean < MEAN_MIN_SUSPICIOUS:
        return 0.0

    # ------------ SCORE MAPPING ------------
    # 1) Outlier strength based on doc_z
    Z_MAX_STRONG = 12.0
    nz = (doc_z - Z_MIN_SUSPICIOUS) / (Z_MAX_STRONG - Z_MIN_SUSPICIOUS)
    nz = float(np.clip(nz, 0.0, 1.0))

    # 2) Brightness spike: how much brighter the worst patch is
    #    compared to a typical bright patch.
    #    0.00–0.05 is mild, ~0.25–0.30 is strong.
    B_MAX_STRONG = 0.30
    nb = bright_spike / B_MAX_STRONG
    nb = float(np.clip(nb, 0.0, 1.0))

    # Combine. Outlier strength dominates; brightness spike helps.
    raw_score = 0.7 * nz + 0.3 * nb

    # Non-linear scaling to keep mild anomalies low.
    score = raw_score * raw_score

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))