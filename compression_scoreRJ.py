import os
from typing import List

from PIL import Image
import numpy as np


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compute a compression-based manipulation score in [0, 1].

    Input
    -----
    forensic_output_dir : str
        Root forensic directory. This function expects a subdirectory
        called "Compression" that contains JPEG images produced by
        compression_difference(...).

    Method
    ------
    For each image in <forensic_output_dir>/Compression:

        1. Convert to grayscale.
        2. Crop margins to focus on statement content.
        3. Split content into a grid of patches.
        4. Ignore nearly empty patches (background).
        5. For remaining patches:
              - compute mean intensity per patch in [0, 1].
           Then:
              - mu_page = mean of patch means.
              - cv_page = std(patch_means) / mu_page.

    For the whole document:

        - mu_doc = median(mu_page)       # overall compression energy
        - cv_doc = max(cv_page)          # strongest inconsistency

    Scoring:

        - If mu_doc is tiny, return 0.0 (little compression signal).
        - Else map cv_doc into [0, 1]:
            cv_doc <= CV_CLEAN_MAX  -> score ~ 0
            cv_doc >= CV_STRONG_MAX -> score ~ 1

        We square the normalized value to keep mild differences low.

    Interpretation
    --------------
    - Clean, uniformly compressed statements:
        low cv_doc  -> score near 0.
    - Statements with locally different compression (e.g. pasted / edited regions):
        higher cv_doc -> higher score.
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    page_mu: List[float] = []
    page_cv: List[float] = []

    for img_name in os.listdir(comp_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(comp_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        h, w = arr.shape
        if h == 0 or w == 0:
            continue

        # 1) Crop margins: remove viewer borders / big whitespace
        top_margin = int(0.10 * h)
        bottom_margin = int(0.05 * h)
        left_margin = int(0.08 * w)
        right_margin = int(0.08 * w)

        y0 = top_margin
        y1 = max(y0 + 1, h - bottom_margin)
        x0 = left_margin
        x1 = max(x0 + 1, w - right_margin)

        arr = arr[y0:y1, x0:x1]
        h, w = arr.shape
        if h == 0 or w == 0:
            continue

        # 2) Build patches
        GRID = 32
        ph = max(h // GRID, 1)
        pw = max(w // GRID, 1)

        patch_means = []

        for ys in range(0, h, ph):
            ye = min(h, ys + ph)
            for xs in range(0, w, pw):
                xe = min(w, xs + pw)

                patch = arr[ys:ye, xs:xe]

                # Ignore nearly empty patches (background / watermark only)
                active = patch[patch > 1.0]
                if active.size < 0.1 * patch.size:
                    continue

                # Normalize to [0, 1]
                patch_mean = float(active.mean() / 255.0)
                patch_means.append(patch_mean)

        if len(patch_means) < 5:
            # Too little content to say anything
            continue

        means = np.array(patch_means, dtype=np.float32)
        mu = float(means.mean())

        if mu < 1e-6:
            continue

        sigma = float(means.std())
        cv = sigma / mu

        page_mu.append(mu)
        page_cv.append(cv)

    if not page_mu or not page_cv:
        return 0.0

    mu_doc = float(np.median(page_mu))
    cv_doc = float(max(page_cv))

    # ---------------- EARLY CLEAN CHECK ----------------
    # Very low overall compression difference → no signal
    MU_CLEAN_MAX = 0.02  # typical for very "gentle" diff images

    if mu_doc <= MU_CLEAN_MAX:
        return 0.0

    # ---------------- SCORE MAPPING ----------------
    # Typical uniform compression:
    #   cv_doc around 0.0–0.05
    # Strong local inconsistencies:
    #   cv_doc around 0.20+ (depends on data)
    CV_CLEAN_MAX = 0.05
    CV_STRONG_MAX = 0.25

    if cv_doc <= CV_CLEAN_MAX:
        return 0.0

    norm = (cv_doc - CV_CLEAN_MAX) / (CV_STRONG_MAX - CV_CLEAN_MAX)
    norm = float(np.clip(norm, 0.0, 1.0))

    # Non-linear scaling: keep small deviations low, strong ones high
    score = norm * norm

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))
