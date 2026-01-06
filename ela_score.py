import os
import numpy as np
from PIL import Image


def compute_ela_score(forensic_output_dir: str) -> float:
    ela_dir = os.path.join(forensic_output_dir, "ELA")

    if not os.path.exists(ela_dir):
        return 0.0

    scores = []
    for img in os.listdir(ela_dir):
        if img.lower().endswith(".jpg"):
            img_path = os.path.join(ela_dir, img)
            image = Image.open(img_path).convert("RGB")
            arr = np.array(image)
            scores.append(arr.std())

    if not scores:
        return 0.0

    raw = float(np.mean(scores)) / 255

    # ---------------- CALIBRATION ----------------
    if raw < 0.02:
        return 0.0                 # CLEAN DEAD-ZONE
    elif raw < 0.05:
        return round((raw - 0.02) / 0.03 * 0.3, 3)   # LOW
    elif raw < 0.10:
        return round(0.3 + (raw - 0.05) / 0.05 * 0.4, 3)  # MODERATE
    else:
        return round(min(1.0, 0.7 + raw), 3)        # HIGH