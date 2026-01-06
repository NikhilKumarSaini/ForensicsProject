import os
from typing import List

from PIL import Image
import numpy as np


def _page_tail_contrast(arr: np.ndarray, background_threshold: float = 1.0) -> float:
    """
    For a single ELA page (grayscale array), compute a 'tail contrast' value:

    - Flatten pixels.
    - Remove near-zero values (background / scanner floor).
    - Normalize to [0, 1].
    - Compare the mean of the top 1% brightest pixels with the mean of the next 4%.

    Returns a value >= 0:
        0        -> no contrast between extreme tail and rest of high pixels
        higher   -> a few very bright anomalies compared to normal high pixels
    """
    flat = arr.reshape(-1)
    flat = flat[flat > background_threshold]

    if flat.size < 1000:
        # Too few active pixels, treat as low-information
        return 0.0

    # Normalize to [0, 1]
    flat = flat.astype(np.float32) / 255.0

    # Sort ascending
    flat.sort()
    n = flat.size

    # Indices for 95% and 99% quantiles
    idx_95 = int(0.95 * n)
    idx_99 = int(0.99 * n)

    # Safety clamps
    idx_95 = max(0, min(idx_95, n - 1))
    idx_99 = max(idx_95 + 1, min(idx_99, n - 1))

    # Next 4% high pixels (95%–99%)
    high_band = flat[idx_95:idx_99]
    # Top 1% pixels (99%–100%)
    top_band = flat[idx_99:]

    if high_band.size == 0 or top_band.size == 0:
        return 0.0

    mean_high = float(high_band.mean())
    mean_top = float(top_band.mean())

    contrast = max(0.0, mean_top - mean_high)
    return contrast


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Compute an ELA-based manipulation score in [0, 1].

    Design
    ------
    For each ELA JPEG in <forensic_output_dir>/ELA:
        - Convert to grayscale.
        - Compute:
            * energy_page   : mean of non-background intensities (0..1).
            * contrast_page : difference between the top 1% brightest pixels
                              and the next 4% brightest pixels.

    For the whole document:
        - energy_doc   = median(energy_page)
        - contrast_doc = max(contrast_page)  # strongest page

    Behaviour
    ---------
    - Fully digital / clean bank statements:
        * overall energy low–moderate
        * tail contrast small
        → score ≈ 0 or very small (0.0xx)

    - Manipulated statements (local edits):
        * similar energy
        * bigger tail contrast (a few extreme pixels)
        → higher score, suitable for low / moderate / high bands.
    """
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    energies: List[float] = []
    contrasts: List[float] = []

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
        flat_active = flat[flat > 1.0]

        if flat_active.size == 0:
            continue

        # Normalized energy for this page
        energy_page = float(flat_active.mean() / 255.0)
        energies.append(energy_page)

        # Tail contrast for this page
        contrast_page = _page_tail_contrast(arr)
        contrasts.append(contrast_page)

    if not energies or not contrasts:
        return 0.0

    energy_doc = float(np.median(energies))
    contrast_doc = float(max(contrasts))

    # ---------------- EARLY CLEAN SHORTCUT ----------------
    # Very low ELA energy: clean digital, system-generated statements.
    ENERGY_CLEAN_MAX = 0.02  # typical for simple, fully digital pages

    if energy_doc <= ENERGY_CLEAN_MAX:
        return 0.0

    # ---------------- SCORE MAPPING ----------------
    # 1) Normalize contrast
    #    A contrast around 0.0–0.02 is mild noise.
    #    Around 0.10+ suggests strong local anomalies.
    CONTRAST_MAX = 0.12
    contrast_norm = contrast_doc / CONTRAST_MAX
    contrast_norm = float(np.clip(contrast_norm, 0.0, 1.0))

    # 2) Normalize energy above the clean baseline so very busy / noisy
    #    documents get a mild boost, but contrast still dominates.
    ENERGY_UPPER = 0.20
    energy_norm = (energy_doc - ENERGY_CLEAN_MAX) / (ENERGY_UPPER - ENERGY_CLEAN_MAX)
    energy_norm = float(np.clip(energy_norm, 0.0, 1.0))

    # Combine: contrast is main driver, energy just supports it.
    raw_score = 0.8 * contrast_norm + 0.2 * energy_norm

    # Non-linear scaling to keep mild anomalies low.
    score = raw_score * raw_score

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))