import os
import numpy as np
from PIL import Image


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Computes compression tampering score (0.0 – 1.0) from
    compression difference images.

    Assumptions:
    - Input images are compression difference outputs
    - High-energy residual regions (orange/blue clusters)
      indicate localized recompression
    - No watermark present in compression image

    Method:
    - Focus on strongest residual responses (top percentile)
    - Measure energy + spatial concentration
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

        # Normalize to [0, 1]
        gray /= 255.0

        # Ignore near-zero background
        active = gray[gray > 0.02]
        if active.size < 100:
            page_scores.append(0.0)
            continue

        # Focus on strongest residuals (colored regions)
        high_threshold = np.percentile(active, 95)
        high_residuals = active[active >= high_threshold]

        if high_residuals.size < 50:
            page_scores.append(0.0)
            continue

        # Residual energy (strength of compression artifacts)
        energy = float(np.mean(high_residuals))

        # Spatial concentration (localized edits)
        concentration = float(high_residuals.size) / float(gray.size)

        # Combined compression signal
        # Scaling factor chosen empirically for JPEG residuals
        raw_score = energy * concentration * 8.0

        score = min(1.0, raw_score)
        page_scores.append(score)

    if not page_scores:
        return 0.0

    # Use max-page strategy (tampering is localized)
    return float(round(max(page_scores), 3))
