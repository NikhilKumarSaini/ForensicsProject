import os
import numpy as np
from PIL import Image


def _patch_values(gray: np.ndarray, grid: int = 60) -> np.ndarray:
    """
    Returns per-patch mean intensity (0..1) ignoring background.
    """
    h, w = gray.shape
    ph = max(h // grid, 10)
    pw = max(w // grid, 10)

    vals = []
    for y in range(0, h, ph):
        for x in range(0, w, pw):
            patch = gray[y:y + ph, x:x + pw]
            if patch.size == 0:
                continue

            # Ignore near-zero background
            active = patch[patch > 2.0]
            if active.size < 0.10 * patch.size:
                continue

            vals.append(float(active.mean()) / 255.0)

    return np.array(vals, dtype=np.float32)


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA score (0..1) using robust outlier-patch ratio.

    - Compute patch mean intensities from the ELA image.
    - Compute robust baseline: median + 3*MAD.
    - Score is based on fraction of patches exceeding that baseline.
    """
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_scores = []

    for name in os.listdir(ela_dir):
        if not name.lower().endswith(".jpg"):
            continue

        path = os.path.join(ela_dir, name)
        try:
            with Image.open(path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        vals = _patch_values(gray, grid=60)
        if vals.size < 40:
            continue

        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med))) + 1e-6  # robust spread
        thresh = med + 3.0 * mad

        outliers = vals > thresh
        ratio = float(np.count_nonzero(outliers)) / float(vals.size)

        # Map ratio to [0,1]
        # Clean pages usually have tiny outlier ratios.
        # Manipulated tends to create more localized spikes.
        if ratio < 0.01:
            score = 0.0
        elif ratio < 0.04:
            score = 0.10 + (ratio - 0.01) / 0.03 * 0.25
        elif ratio < 0.10:
            score = 0.35 + (ratio - 0.04) / 0.06 * 0.35
        else:
            score = 0.70 + min(0.30, (ratio - 0.10) / 0.10 * 0.30)

        page_scores.append(float(score))

    if not page_scores:
        return 0.0

    # Strongest page drives document score
    return float(round(min(1.0, max(page_scores)), 3))
