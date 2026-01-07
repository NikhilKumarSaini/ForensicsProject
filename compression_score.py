import os
from PIL import Image
import numpy as np


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Robust compression inconsistency score (0–1)

    Logic:
    - Clean PDFs → ~0.0
    - Word / layout-heavy → very low
    - Manipulated → localized spikes
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    medians = []
    p90s = []

    for img in os.listdir(comp_dir):
        if not img.lower().endswith(".jpg"):
            continue

        try:
            image = Image.open(os.path.join(comp_dir, img)).convert("RGB")
            arr = np.array(image, dtype=np.float32)

            # Pixel-wise std across channels
            std_map = arr.std(axis=2)

            # Remove low-level JPEG noise
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

    # ---------------- CLEAN ----------------
    if median_raw < 0.03 and p90_raw < 0.08:
        return 0.0

    # ---------------- LOW / BENIGN ----------------
    if p90_raw < 0.12:
        return round(p90_raw, 3)

    # ---------------- MODERATE ----------------
    if p90_raw < 0.22:
        score = 0.12 + (p90_raw - 0.12) / 0.10 * 0.20
        return round(score, 3)

    # ---------------- HIGH ----------------
    return round(min(1.0, 0.30 + p90_raw), 3)