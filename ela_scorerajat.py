import os
import numpy as np
from PIL import Image


def _patch_values(gray: np.ndarray, grid: int = 60) -> np.ndarray:
    """
    Returns per-patch mean intensity (0..1), ignoring background-heavy patches.
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

            active = patch > 2.0
            # Ignore patches that are mostly background
            if active.mean() < 0.12:
                continue

            vals.append(float(patch[active].mean()) / 255.0)

    return np.array(vals, dtype=np.float32)


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA score (0..1)

    Key fixes:
    - LOW CONTENT GUARD:
      If the page has too little active area OR too few usable patches,
      return 0 for that page (prevents Lokesh false positives).
    - More aggressive mapping AFTER the guard so manipulated pages rise.
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

        # ---------------- LOW CONTENT GUARD ----------------
        active_fraction = float((gray > 2.0).mean())
        # Very empty pages (Lokesh-style) should not produce ELA spikes
        if active_fraction < 0.015:  # 1.5% of pixels active
            page_scores.append(0.0)
            continue

        vals = _patch_values(gray, grid=60)

        # If too few patches survived, stats become unstable -> treat as clean
        if vals.size < 120:
            page_scores.append(0.0)
            continue

        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med))) + 1e-6
        thresh = med + 3.0 * mad

        ratio = float(np.count_nonzero(vals > thresh)) / float(vals.size)

        # Extra guard: for low-energy documents, small ratios are benign
        if med < 0.03 and ratio < 0.06:
            page_scores.append(0.0)
            continue

        # ---------------- SCORE MAPPING (MORE SENSITIVE) ----------------
        if ratio < 0.01:
            score = 0.0
        elif ratio < 0.03:
            score = 0.12 + (ratio - 0.01) / 0.02 * 0.28   # 0.12 -> 0.40
        elif ratio < 0.07:
            score = 0.40 + (ratio - 0.03) / 0.04 * 0.35   # 0.40 -> 0.75
        else:
            score = 0.75 + min(0.25, (ratio - 0.07) / 0.08 * 0.25)  # up to 1.0

        page_scores.append(float(score))

    if not page_scores:
        return 0.0

    return float(round(min(1.0, max(page_scores)), 3))
