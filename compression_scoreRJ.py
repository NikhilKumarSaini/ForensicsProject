import os
from PIL import Image
import numpy as np


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compression score in [0, 1], based on the energy and variability
    of the compression-difference images.

    Expected behaviour
    ------------------
    - Very simple, clean digital statements (like the Lokesh Notepad PDF)
      → near 0 (often exactly 0).
    - Normal, clean but busy bank statements
      → low to moderate scores.
    - Manipulated / unusual statements with stronger or uneven artefacts
      → higher scores.
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
            # Work in grayscale on the compression-diff image
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        flat = arr.reshape(-1)

        # Remove near-zero background
        flat = flat[flat > 1.0]
        if flat.size == 0:
            continue

        # Normalize to [0, 1]
        flat_norm = flat / 255.0

        page_means.append(float(flat_norm.mean()))
        page_stds.append(float(flat_norm.std()))

    if not page_means:
        return 0.0

    # Document-level stats (across pages)
    mean_doc = float(np.median(page_means))   # overall artefact energy
    std_doc = float(np.median(page_stds))     # overall variability

    # ---------------- EARLY CLEAN SHORTCUT ----------------
    # Very low energy means the page barely changes between
    # quality 70 and 95 → gentle compression, clean digital.
    ENERGY_CLEAN_MAX = 0.015  # tweak up or down if needed

    if mean_doc <= ENERGY_CLEAN_MAX:
        return 0.0

    # ---------------- SCORE MAPPING ----------------
    # 1) Core score from energy:
    #    mean_doc in [ENERGY_CLEAN_MAX, ENERGY_HIGH] → [0, 1]
    ENERGY_HIGH = 0.10  # where we consider compression artefacts strong

    energy_norm = (mean_doc - ENERGY_CLEAN_MAX) / (ENERGY_HIGH - ENERGY_CLEAN_MAX)
    energy_norm = float(np.clip(energy_norm, 0.0, 1.0))

    # 2) Extra score from variability:
    #    std_doc in [STD_LOW, STD_HIGH] → [0, 1]
    STD_LOW = 0.005
    STD_HIGH = 0.06

    std_norm = (std_doc - STD_LOW) / (STD_HIGH - STD_LOW)
    std_norm = float(np.clip(std_norm, 0.0, 1.0))

    # Combine: energy dominates, variability supports
    raw_score = 0.7 * energy_norm + 0.3 * std_norm

    # Gentle non-linearity so small deviations stay low
    score = raw_score * raw_score

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))
