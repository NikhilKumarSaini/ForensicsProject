import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Calibrated ELA score (0–1)

    Interpretation:
    - < 0.03  → Clean / Digital noise floor
    - 0.03–0.08 → Low (complex layout, Word tables, benign)
    - 0.08–0.15 → Moderate (suspicious edits)
    - > 0.15 → High (clear manipulation)
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    raw_scores = []

    for img in os.listdir(ela_dir):
        if img.lower().endswith(".jpg"):
            img_path = os.path.join(ela_dir, img)
            try:
                image = Image.open(img_path).convert("RGB")
                arr = np.array(image)
                raw_scores.append(arr.std())
            except Exception:
                continue

    if not raw_scores:
        return 0.0

    # Normalize raw std to [0–1] scale
    raw = float(np.mean(raw_scores)) / 255.0

    # -------------------------------
    # CALIBRATION & NOISE SUPPRESSION
    # -------------------------------
    # Noise floor observed empirically ~0.03
    if raw < 0.03:
        return 0.0

    # Low risk: complex layout / Word tables
    if raw < 0.08:
        # Map 0.03–0.08 → 0.05–0.25
        score = 0.05 + (raw - 0.03) / 0.05 * 0.20
        return round(score, 3)

    # Moderate risk
    if raw < 0.15:
        # Map 0.08–0.15 → 0.25–0.55
        score = 0.25 + (raw - 0.08) / 0.07 * 0.30
        return round(score, 3)

    # High risk (cap at 1.0)
    score = min(1.0, 0.55 + raw)
    return round(score, 3)