import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Scientifically correct ELA score (0–1)

    - Median std → clean / benign
    - High-percentile std → manipulation
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    medians = []
    p90s = []

    for img in os.listdir(ela_dir):
        if not img.lower().endswith(".jpg"):
            continue

        try:
            image = Image.open(os.path.join(ela_dir, img)).convert("RGB")
            arr = np.array(image, dtype=np.float32)

            std_map = arr.std(axis=2)

            # Ignore background noise
            std_map = std_map[std_map > 1.5]

            if std_map.size > 0:
                medians.append(np.median(std_map))
                p90s.append(np.percentile(std_map, 90))

        except Exception:
            continue

    if not medians:
        return 0.0

    median_raw = np.median(medians) / 255.0
    p90_raw = np.median(p90s) / 255.0

    # ---------------- CLEAN DOCUMENT ----------------
    if median_raw < 0.03 and p90_raw < 0.08:
        return 0.0

    # ---------------- LOW / BENIGN ----------------
    if p90_raw < 0.12:
        return round(min(0.15, p90_raw), 3)

    # ---------------- MODERATE ----------------
    if p90_raw < 0.22:
        score = 0.15 + (p90_raw - 0.12) / 0.10 * 0.20
        return round(score, 3)

    # ---------------- HIGH ----------------
    return round(min(1.0, 0.35 + p90_raw), 3)