import os
import numpy as np
from PIL import Image


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    FINAL ELA SCORE (CALIBRATED)

    Clean documents  -> ~0.00 – 0.02
    Light edits      -> ~0.05 – 0.12
    Manipulated docs -> >0.15
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    scores = []

    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(ela_dir, img_name)
        img = Image.open(img_path).convert("L")  # grayscale
        arr = np.array(img, dtype=np.float32)

        # 🔑 Bright error pixels only
        threshold = 20          # tuned for documents
        bright_pixels = arr > threshold

        ratio = bright_pixels.sum() / arr.size
        scores.append(ratio)

    if not scores:
        return 0.0

    # Clamp & round for stability
    ela_score = float(np.mean(scores))
    ela_score = min(ela_score, 1.0)

    return round(ela_score, 3)
