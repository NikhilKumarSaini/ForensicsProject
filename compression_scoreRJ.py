import os
from PIL import Image
import numpy as np


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compression score in [0, 1] based on global energy and variability of the
    compression-difference images.

    Behaviour:
    - Very simple, clean digital pages (e.g. Notepad Lokesh statement)
      → very low mean diff → score near 0.
    - Normal clean statements with more text/table/logo
      → low to moderate scores.
    - Manipulated / unusual statements (heavier or uneven artefacts)
      → higher scores.

    This mapping is deliberately gentle so it does not saturate at 1 for
    every bank statement.
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    page_means = []
    page_stds = []

    for img_name in os.listdir(comp_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(comp_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        flat = arr.reshape(-1)

        # Remove near-zero background
        flat = flat[flat > 1.0]
        if flat.size == 0:
            continue

        flat_norm = flat / 255.0

        page_means.append(float(flat_norm.mean()))
        page_stds.append(float(flat_norm.std()))

    if not page_means:
        return 0.0

    # Document-level stats
    mean_doc = float(np.median(page_means))   # overall artefact energy
    std_doc = float(np.median(page_stds))     # overall variability

    # ---------------- EARLY CLEAN SHORTCUT ----------------
    # Very low energy: essentially no compression difference.
    ENERGY_CLEAN_MAX = 0.015  # adjust slightly if Lokesh still > 0

    if mean_doc <= ENERGY_CLEAN_MAX:
        return 0.0

    # ---------------- SCORE MAPPING ----------------
    # 1) Energy-based component
    ENERGY_HIGH = 0.20  # strong diff; chosen high so we do not saturate
    energy_norm = mean_doc / ENERGY_HIGH
    energy_norm = float(np.clip(energy_norm, 0.0, 1.0))

    # 2) Variability component (how uneven the artefacts are)
    STD_HIGH = 0.10
    std_norm = std_doc / STD_HIGH
    std_norm = float(np.clip(std_norm, 0.0, 1.0))

    # Combine: energy dominates, variability supports
    raw_score = 0.7 * energy_norm + 0.3 * std_norm

    # Gentle non-linearity so small deviations stay low
    score = raw_score ** 0.8

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))
