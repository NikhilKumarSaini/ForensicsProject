import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Robust ELA score (0–1)

    - Clean PDFs → ~0.0
    - Word / programmatic PDFs → very low (0–0.05)
    - Manipulated → spikes preserved
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    scores = []

    for img in os.listdir(ela_dir):
        if not img.lower().endswith(".jpg"):
            continue

        try:
            image = Image.open(os.path.join(ela_dir, img)).convert("RGB")
            arr = np.array(image, dtype=np.float32)

            # Compute per-channel std
            std_map = arr.std(axis=2)

            # Remove background noise (very low variance)
            std_map = std_map[std_map > 2.0]

            if std_map.size > 0:
                # Use MEDIAN (robust to benign spikes)
                scores.append(np.median(std_map))

        except Exception:
            continue

    if not scores:
        return 0.0

    raw = float(np.median(scores)) / 255.0

    # -----------------------------
    # CLEAN NOISE FLOOR (CRITICAL)
    # -----------------------------
    if raw < 0.06:
        return 0.0

    return round(raw, 3)