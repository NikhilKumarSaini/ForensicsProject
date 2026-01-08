import os
import numpy as np
from PIL import Image
import cv2


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Computes compression tampering score (0.0 – 1.0) from
    compression difference images.

    Assumptions:
    - Input images are compression difference outputs
    - High-energy residual regions (orange / blue clusters)
      indicate localized recompression
    - No watermark present in compression image

    Method:
    - Measure residual energy
    - Measure spatial concentration
    - Measure total highlighted area
    - Measure largest connected highlighted patch
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    page_scores = []

    for fname in os.listdir(comp_dir):
        if not fname.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(comp_dir, fname)

        try:
            with Image.open(img_path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        # Normalize to [0,1]
        gray /= 255.0
        h, w = gray.shape
        total_pixels = h * w

        # Remove near-zero background
        active_mask = gray > 0.02
        if np.sum(active_mask) < 100:
            page_scores.append(0.0)
            continue

        active_vals = gray[active_mask]

        # High-energy residual threshold (top 5%)
        high_thresh = np.percentile(active_vals, 95)
        high_mask = gray >= high_thresh

        high_pixel_count = int(np.sum(high_mask))
        if high_pixel_count < 50:
            page_scores.append(0.0)
            continue

        # 1️⃣ Residual Energy (strength)
        energy = float(np.mean(gray[high_mask]))

        # 2️⃣ Spatial Concentration
        concentration = high_pixel_count / total_pixels

        # 3️⃣ Area Ratio (explicit)
        area_ratio = concentration

        # 4️⃣ Largest Connected Patch Ratio
        mask_uint8 = (high_mask * 255).astype(np.uint8)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask_uint8, connectivity=8
        )

        if num_labels > 1:
            largest_patch_area = max(stats[1:, cv2.CC_STAT_AREA])
            largest_patch_ratio = largest_patch_area / total_pixels
        else:
            largest_patch_ratio = 0.0

        # 🔢 Final Compression Score (weighted, stable)
        raw_score = (
            0.35 * energy +
            0.25 * concentration * 10.0 +
            0.20 * area_ratio * 10.0 +
            0.20 * largest_patch_ratio * 15.0
        )

        score = min(1.0, raw_score)
        page_scores.append(score)

    if not page_scores:
        return 0.0

    # Max-page strategy (tampering is localized)
    return float(round(max(page_scores), 3))

