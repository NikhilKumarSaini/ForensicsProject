import os
from PIL import Image
import numpy as np


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Robust Compression Artifact Score (0–1)

    Logic:
    - Clean / vector PDFs → 0.0
    - Benign compression → very low
    - Manipulated / recompressed regions → spikes preserved
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    p90_values = []

    for img in os.listdir(comp_dir):
        if not img.lower().endswith(".jpg"):
            continue

        try:
            image = Image.open(os.path.join(comp_dir, img)).convert("RGB")
            arr = np.array(image, dtype=np.float32)

            # Per-pixel std across channels
            std_map = arr.std(axis=2)

            # Remove background noise
            std_map = std_map[std_map > 1.5]

            if std_map.size > 0:
                p90_values.append(np.percentile(std_map, 90))

        except Exception:
            continue

    if not p90_values:
        return 0.0

    raw = float(np.median(p90_values)) / 255.0

    # ---------------- CLEAN GATE ----------------
    if raw < 0.04:
        return 0.0

    # ---------------- LOW ----------------
    if raw < 0.08:
        return round((raw - 0.04) / 0.04 * 0.25, 3)

    # ---------------- MODERATE ----------------
    if raw < 0.15:
        return round(0.25 + (raw - 0.08) / 0.07 * 0.30, 3)

    # ---------------- HIGH ----------------
    return round(min(1.0, 0.55 + raw), 3)