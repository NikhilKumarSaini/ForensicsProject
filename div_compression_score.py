import os
import numpy as np
from PIL import Image


def _block_variances(gray: np.ndarray, block: int = 32) -> np.ndarray:
    """
    Compute local variance for fixed-size blocks.
    Variance captures compression residual energy.
    """
    h, w = gray.shape
    variances = []

    for y in range(0, h - block + 1, block):
        for x in range(0, w - block + 1, block):
            patch = gray[y:y + block, x:x + block]
            if patch.shape != (block, block):
                continue
            variances.append(float(np.var(patch)))

    return np.array(variances, dtype=np.float32)


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Robust compression tampering score (0.0 – 1.0)

    Assumptions:
    - Compression difference image contains no watermark
    - Local recompression causes variance spikes
    - Genuine documents show uniform variance distribution

    Method:
    - Block-wise variance analysis
    - Variance inconsistency normalization
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    page_scores = []

    for fname in os.listdir(comp_dir):
        if not fname.lower().endswith(".jpg"):
            continue

        path = os.path.join(comp_dir, fname)
        try:
            with Image.open(path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        # 1️⃣ Local variance extraction
        variances = _block_variances(gray, block=32)
        if variances.size < 50:
            page_scores.append(0.0)
            continue

        # 2️⃣ Robust statistics (median-based, outlier-safe)
        med = float(np.median(variances))
        mad = float(np.median(np.abs(variances - med))) + 1e-6

        # 3️⃣ Normalized inconsistency score
        # High when few blocks have much larger variance
        inconsistency = float(np.mean((variances - med) ** 2) ** 0.5 / mad)

        # 4️⃣ Normalize to [0,1]
        # Empirically stable for JPEG residuals
        Tc = 6.0
        score = min(1.0, inconsistency / Tc)

        page_scores.append(score)

    if not page_scores:
        return 0.0

    # Max-page strategy (bank fraud is localized)
    return float(round(min(1.0, max(page_scores)), 3))
