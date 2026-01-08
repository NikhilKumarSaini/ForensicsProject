import os
from io import BytesIO
from typing import List

import numpy as np
from PIL import Image


def _recompress_rgb(original: Image.Image, quality: int) -> np.ndarray:
    """
    Recompress an RGB PIL image to JPEG in-memory and return as uint8 RGB array.
    """
    buf = BytesIO()
    original.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)

    with Image.open(buf) as tmp:
        arr = np.array(tmp.convert("RGB"), dtype=np.int16)

    return arr


def _tail_contrast_from_diff(diff_gray: np.ndarray) -> float:
    """
    diff_gray: int16/float array 0..255
    Returns (mean top 1% - mean next 4%) after removing near-zero values.
    """
    flat = diff_gray.reshape(-1).astype(np.float32)

    # remove near-zero background noise
    flat = flat[flat > 2.0]
    if flat.size < 2000:
        return 0.0

    flat = flat / 255.0
    flat.sort()
    n = flat.size

    idx_95 = int(0.95 * n)
    idx_99 = int(0.99 * n)

    idx_95 = max(0, min(idx_95, n - 1))
    idx_99 = max(idx_95 + 1, min(idx_99, n - 1))

    high_band = flat[idx_95:idx_99]   # 95–99%
    top_band = flat[idx_99:]          # 99–100%

    if high_band.size == 0 or top_band.size == 0:
        return 0.0

    return float(max(0.0, top_band.mean() - high_band.mean()))


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA score in [0, 1] computed from ORIGINAL page JPGs (Images/<folder>/page-*.jpg),
    not from the saved ELA visualization images.

    This avoids the "brightness boost saturation" problem that was making clean docs score ~1.
    """
    folder_name = os.path.basename(forensic_output_dir)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../project_root
    images_dir = os.path.join(project_root, "Images", folder_name)

    if not os.path.isdir(images_dir):
        return 0.0

    energies: List[float] = []
    contrasts: List[float] = []

    for img_name in sorted(os.listdir(images_dir)):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(images_dir, img_name)

        try:
            with Image.open(img_path) as im:
                orig = im.convert("RGB")
                orig_arr = np.array(orig, dtype=np.int16)
                rec_arr = _recompress_rgb(orig, quality=90)

        except Exception:
            continue

        # diff in RGB, then convert to grayscale diff magnitude
        diff = np.abs(orig_arr - rec_arr).astype(np.float32)
        diff_gray = diff.mean(axis=2)  # 0..255

        # energy: average diff over "active" pixels
        active = diff_gray > 2.0
        if active.sum() < 2000:
            energies.append(0.0)
            contrasts.append(0.0)
            continue

        energy_page = float(diff_gray[active].mean() / 255.0)
        energies.append(energy_page)

        contrast_page = _tail_contrast_from_diff(diff_gray)
        contrasts.append(contrast_page)

    if not energies:
        return 0.0

    energy_doc = float(np.median(energies))
    contrast_doc = float(max(contrasts)) if contrasts else 0.0

    # ---------------- Mapping (tunable but stable) ----------------
    # Clean digitally-generated PDFs tend to have very low diff energy.
    ENERGY_CLEAN_MAX = 0.010

    if energy_doc <= ENERGY_CLEAN_MAX and contrast_doc <= 0.010:
        return 0.0

    # Contrast is the main signal for localized edits.
    CONTRAST_MAX = 0.080
    contrast_norm = float(np.clip(contrast_doc / CONTRAST_MAX, 0.0, 1.0))

    # Energy supports contrast (busy scanned pages have higher baseline)
    ENERGY_UPPER = 0.120
    energy_norm = float(np.clip((energy_doc - ENERGY_CLEAN_MAX) / (ENERGY_UPPER - ENERGY_CLEAN_MAX), 0.0, 1.0))

    raw = 0.80 * contrast_norm + 0.20 * energy_norm
    score = raw * raw  # suppress mild noise

    return float(round(np.clip(score, 0.0, 1.0), 3))
