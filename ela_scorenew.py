# ela_score.py
import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Compute a normalized ELA energy score in [0, 1].

    Interpretation:
    - Fully digital statements (like your examples) produce very low residual
      energy after recompression, so the score is near 0.
    - Image-based or heavily recompressed documents (screenshots, photos,
      flattened scans) produce higher residual energy and score higher.

    This score is *not* reliable for distinguishing small text edits inside
    otherwise fully digital PDFs. It is mainly useful to distinguish
    "photo/scan" vs "clean digital".
    """
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_means = []

    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(ela_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        flat = arr.reshape(-1)
        # Drop near-zero background
        flat = flat[flat > 1.0]
        if flat.size == 0:
            continue

        mean_val = float(flat.mean())
        page_means.append(mean_val)

    if not page_means:
        return 0.0

    # Median mean intensity across pages, normalized to [0, 1]
    mean_raw = float(np.median(page_means)) / 255.0

    # Map small energies to near 0, larger energies toward 1.
    # For typical digital PDFs, mean_raw is very small, so score ≈ 0.
    # For screenshots or heavily recompressed images, mean_raw is higher.
    base = 0.02   # typical upper bound for clean digital statements
    upper = 0.30  # strong ELA activity

    norm = (mean_raw - base) / (upper - base)
    norm = float(np.clip(norm, 0.0, 1.0))

    # Mild non-linearity to compress low values further
    score = norm * norm

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))