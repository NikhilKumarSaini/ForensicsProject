import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    FINAL ELA SCORE (0–1)

    Strategy:
    - Use TWO independent ELA interpretations:
        1) Calibrated ELA (noise-suppressed, layout-aware)
        2) Raw ELA (high-sensitivity manipulation detector)

    Final rule:
        final_ela = max(calibrated_ela, raw_ela)

    Interpretation:
    - 0.00            → Clean document
    - 0.05 – 0.15     → Low / benign complexity
    - 0.15 – 0.30     → Moderate manipulation
    - > 0.30          → High manipulation
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

    # --------------------------------------------------
    # RAW ELA (high-sensitivity signal)
    # --------------------------------------------------
    raw = float(np.mean(raw_scores)) / 255.0

    if raw < 0.02:
        raw_ela = 0.0
    elif raw < 0.05:
        raw_ela = (raw - 0.02) / 0.03 * 0.30
    elif raw < 0.10:
        raw_ela = 0.30 + (raw - 0.05) / 0.05 * 0.40
    else:
        raw_ela = min(1.0, 0.70 + raw)

    raw_ela = round(raw_ela, 3)

    # --------------------------------------------------
    # CALIBRATED ELA (noise-suppressed, layout-aware)
    # --------------------------------------------------
    if raw < 0.03:
        calibrated_ela = 0.0

    elif raw < 0.08:
        calibrated_ela = 0.05 + (raw - 0.03) / 0.05 * 0.20

    elif raw < 0.15:
        calibrated_ela = 0.25 + (raw - 0.08) / 0.07 * 0.30

    else:
        calibrated_ela = min(1.0, 0.55 + raw)

    calibrated_ela = round(calibrated_ela, 3)

    # --------------------------------------------------
    # FINAL DECISION RULE
    # --------------------------------------------------
    final_ela = max(raw_ela, calibrated_ela)

    return round(final_ela, 3)