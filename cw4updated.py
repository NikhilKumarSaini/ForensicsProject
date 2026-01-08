import os
import numpy as np
from PIL import Image
import cv2

# Adjust import path if needed
from compression_score import compute_compression_score


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA-based manipulation score (0.0 – 1.0)

    Compression-gated logic:
    - compression < 0.03  → ELA = 0
    - 0.03–0.07           → ELA down-weighted
    - > 0.07              → ELA fully active

    Core ELA logic remains unchanged.
    """

    # =====================================================
    # COMPRESSION GATE
    # =====================================================
    compression_score = compute_compression_score(forensic_output_dir)

    if compression_score < 0.03:
        return 0.0

    # Down-weight factor for gray zone
    if compression_score < 0.07:
        ela_weight = 0.5   # conservative influence
    else:
        ela_weight = 1.0   # full confidence

    # =====================================================
    # ELA PROCESSING
    # =====================================================
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_scores = []

    for fname in os.listdir(ela_dir):
        if not fname.lower().endswith(".jpg"):
            continue

        path = os.path.join(ela_dir, fname)

        img_rgb = cv2.imread(path)
        if img_rgb is None:
            continue

        # ===============================
        # STEP 1: Convert to grayscale
        # ===============================
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

        # ===============================
        # STEP 2: Watermark / overlay masking
        # ===============================
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2HSV)
        _, s, v = cv2.split(hsv)

        watermark_mask = (v > 200) & (s < 40)

        valid_mask = (~watermark_mask) & (gray > 0.02)
        valid_pixels = gray[valid_mask]

        # ===============================
        # STEP 3: Low-content guard
        # ===============================
        if valid_pixels.size < 500:
            page_scores.append(0.0)
            continue

        # ===============================
        # STEP 4: ELA intensity measurement
        # ===============================
        mean_ela = float(np.mean(valid_pixels))
        std_ela = float(np.std(valid_pixels))

        # Very low ELA intensity → clean
        if mean_ela < 0.03:
            page_scores.append(0.0)
            continue

        # ===============================
        # STEP 5: Severity normalization
        # ===============================
        raw_score = (0.7 * mean_ela) + (0.3 * std_ela * 2.0)

        score = min(1.0, raw_score * 4.0)

        page_scores.append(score)

    if not page_scores:
        return 0.0

    # =====================================================
    # FINAL ELA SCORE (with compression weighting)
    # =====================================================
    final_ela_score = max(page_scores) * ela_weight

    return float(round(final_ela_score, 3))
