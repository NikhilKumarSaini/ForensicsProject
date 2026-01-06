# ela_score.py
import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Compute ELA-based manipulation score in [0, 1].

    Design goals
    ------------
    - Clean digital / programmatic statements:
        score ≈ 0 or very small (0.0xx).
    - Manipulated statements:
        higher scores, to combine later with other signals.

    Method (per document)
    ---------------------
    1. For each ELA JPEG in forensic_output_dir/ELA:
        - Convert to grayscale.
        - Drop near-zero pixels (scanner / compression floor).
        - Compute median, 90th percentile, 99th percentile of intensities
          in [0, 1] space.
    2. Aggregate across pages:
        - med_doc  = median of page medians.
        - p90_doc  = median of page 90th percentiles.
        - p99_doc  = max of page 99th percentiles (worst page).
    3. Shape features:
        - spread     = p90_doc - med_doc  (how wide is the bulk).
        - tail       = p99_doc - p90_doc  (how heavy is the extreme tail).
        - tail_ratio = tail / spread.
    4. Scoring:
        - If tail_ratio is small or p99_doc is low, treat as clean → 0.
        - Otherwise map tail_ratio to [0, 1] with a non-linear scaled
          square so only strong anomalies get large scores.
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_medians = []
    page_p90s = []
    page_p99s = []

    # ---------------- PER PAGE STATS ----------------
    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(ela_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        # Flatten and drop near-zero residuals (background floor)
        flat = arr.reshape(-1)
        flat = flat[flat > 1.0]
        if flat.size == 0:
            continue

        # Normalize to [0, 1]
        flat_norm = flat / 255.0

        page_medians.append(float(np.median(flat_norm)))
        page_p90s.append(float(np.percentile(flat_norm, 90)))
        page_p99s.append(float(np.percentile(flat_norm, 99)))

    if not page_medians:
        return 0.0

    # ---------------- DOCUMENT-LEVEL STATS ----------------
    med_doc = float(np.median(page_medians))
    p90_doc = float(np.median(page_p90s))
    p99_doc = float(np.max(page_p99s))  # strongest page

    # Spread of the main mass vs extreme tail
    spread = max(1e-6, p90_doc - med_doc)
    tail = max(0.0, p99_doc - p90_doc)
    tail_ratio = tail / spread

    # ---------------- EARLY CLEAN CHECK ----------------
    # Conservative conditions so clean, programmatic PDFs go to ~0:
    #  - p99_doc very low   → overall ELA energy small.
    #  - tail_ratio small   → no heavy tail beyond typical ELA.
    #
    # You can tighten or relax these two constants if you inspect
    # a small calibration set, but these are a safe starting point.
    TAIL_CLEAN_MAX = 0.5   # tail not much larger than main spread
    P99_CLEAN_MAX = 0.20   # very weak extremes overall

    if p99_doc < P99_CLEAN_MAX or tail_ratio <= TAIL_CLEAN_MAX:
        return 0.0

    # ---------------- SCORE MAPPING ----------------
    # For suspicious docs, use only the tail_ratio as a shape-based
    # anomaly proxy. We map:
    #   tail_ratio in [TAIL_CLEAN_MAX, TAIL_SUSPICIOUS_MAX] → [0, 1]
    # then square it so values just above the threshold stay very low
    # and only strong tails climb toward 1.
    TAIL_SUSPICIOUS_MAX = 3.0

    # Normalized tail strength
    raw = (tail_ratio - TAIL_CLEAN_MAX) / (TAIL_SUSPICIOUS_MAX - TAIL_CLEAN_MAX)
    raw = float(np.clip(raw, 0.0, 1.0))

    # Non-linear scaling: emphasize strong anomalies
    score = raw * raw

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))