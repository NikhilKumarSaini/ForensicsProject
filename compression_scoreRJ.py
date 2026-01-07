import os
from PIL import Image
import numpy as np


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compression score in [0, 1] based on the AREA of strong
    compression differences in the diff images.

    Behaviour:
    - Very simple, clean digital pages (like the Lokesh Notepad statement)
      → small high-diff area → score near 0.
    - Busier / manipulated statements with more strong differences
      → larger high-diff area → higher score.
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    high_area_ratios = []

    for img_name in os.listdir(comp_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(comp_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        # Flatten and normalize to [0, 1]
        flat = arr.reshape(-1) / 255.0

        # Drop pure background / tiny noise
        flat = flat[flat > 0.02]
        if flat.size == 0:
            continue

        # Fraction of pixels with "strong" compression difference
        # THRESH_STRONG can be tuned; start with 0.25
        THRESH_STRONG = 0.25
        strong = flat > THRESH_STRONG
        ratio_strong = float(np.count_nonzero(strong)) / float(flat.size)

        high_area_ratios.append(ratio_strong)

    if not high_area_ratios:
        return 0.0

    # Document-level: typical strong-area fraction across pages
    doc_ratio = float(np.median(high_area_ratios))

    # ---------------- SCORE MAPPING ----------------
    # For very simple pages, doc_ratio will be very small.
    # We treat anything up to RATIO_CLEAN_MAX as effectively 0.
    RATIO_CLEAN_MAX = 0.03   # ~3% of content pixels strong
    RATIO_HIGH = 0.25        # ~25% strong area is considered very high

    if doc_ratio <= RATIO_CLEAN_MAX:
        return 0.0

    # Normalize between clean and high
    norm = (doc_ratio - RATIO_CLEAN_MAX) / (RATIO_HIGH - RATIO_CLEAN_MAX)
    norm = float(np.clip(norm, 0.0, 1.0))

    # Mild non-linearity: keep small deviations low, strong ones high
    score = norm ** 0.7  # 0.7 < 1 makes it a bit more sensitive

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))
