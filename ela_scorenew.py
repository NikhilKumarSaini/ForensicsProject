import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Conservative ELA score in [0, 1].

    Design
    ------
    - For fully digital, system-generated PDFs (like your examples),
      ELA residuals after a single JPEG recompression are low and fairly
      uniform. Score should be 0 or very small.
    - For scanned / heavily recompressed / image-heavy PDFs,
      residual energy is higher and more variable → higher score.

    For each ELA jpg:
        - Convert to grayscale.
        - Remove near-zero background.
        - Compute mean and std of residual intensity in [0, 1].

    Document-level:
        - energy_doc = median(mean_page)
        - var_doc    = median(std_page)
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_means = []
    page_stds = []

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
        flat = flat[flat > 1.0]  # drop pure background
        if flat.size == 0:
            continue

        flat_norm = flat / 255.0

        page_means.append(float(flat_norm.mean()))
        page_stds.append(float(flat_norm.std()))

    if not page_means:
        return 0.0

    energy_doc = float(np.median(page_means))
    var_doc = float(np.median(page_stds))

    # ---------------- EARLY CLEAN SHORTCUT ----------------
    # Very low ELA energy: clean digital, system-generated statements.
    ENERGY_CLEAN_MAX = 0.015

    if energy_doc <= ENERGY_CLEAN_MAX:
        return 0.0

    # ---------------- SCORE MAPPING ----------------
    ENERGY_HIGH = 0.15
    VAR_HIGH = 0.08

    energy_norm = energy_doc / ENERGY_HIGH
    energy_norm = float(np.clip(energy_norm, 0.0, 1.0))

    var_norm = var_doc / VAR_HIGH
    var_norm = float(np.clip(var_norm, 0.0, 1.0))

    # ELA is a weaker signal, so we compress it
    raw_score = 0.6 * energy_norm + 0.4 * var_norm

    # Stronger compression to keep digital docs low
    score = raw_score ** 1.5

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))
