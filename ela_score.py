import os
from typing import List, Tuple

from PIL import Image
import numpy as np


def _tail_features(x: np.ndarray) -> Tuple[float, float, float]:
    """
    x: normalized [0..1] 1D array of active pixels
    Returns:
      q50, q95, q99
    """
    q50 = float(np.quantile(x, 0.50))
    q95 = float(np.quantile(x, 0.95))
    q99 = float(np.quantile(x, 0.99))
    return q50, q95, q99


def compute_ela_score(forensic_output_dir: str) -> float:
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    debug = os.getenv("DEBUG_FORENSICS", "0") == "1"

    page_scores: List[float] = []

    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(ela_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as im:
                arr = np.asarray(im, dtype=np.float32) / 255.0
        except Exception:
            continue

        flat = arr.reshape(-1)

        # drop background floor
        flat = flat[flat > 0.04]
        if flat.size < 2000:
            continue

        q50, q95, q99 = _tail_features(flat)

        # Tail gap: big when there are a few very bright anomalies
        tail_gap = max(0.0, q99 - q95)

        # Tail lift: how far high tail sits above normal content
        tail_lift = max(0.0, q95 - q50)

        # Combine, tail_gap dominates
        raw = (1.6 * tail_gap) + (0.6 * tail_lift)

        # Map to [0..1] with practical thresholds
        # Tune points: clean tends to have tiny tail_gap.
        LO = 0.010
        HI = 0.080
        score = (raw - LO) / (HI - LO)
        score = float(np.clip(score, 0.0, 1.0))

        page_scores.append(score)

        if debug:
            print(f"[ELA] {img_name} q50={q50:.3f} q95={q95:.3f} q99={q99:.3f} raw={raw:.4f} score={score:.3f}")

    if not page_scores:
        return 0.0

    # Document score: use max to catch a single tampered page
    doc_score = float(np.max(page_scores))
    return float(round(doc_score, 3))
