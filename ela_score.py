import os
from typing import List, Tuple

import numpy as np
from PIL import Image

# cv2 is already in your project (noise_score uses it)
import cv2


def _robust_stats(x: np.ndarray) -> Tuple[float, float, float]:
    """
    Returns (median, mad, p99) on x in [0,1].
    """
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)))  # median absolute deviation
    p99 = float(np.percentile(x, 99))
    return med, mad, p99


def _edge_mask_from_preprocessed(pre_path: str) -> np.ndarray:
    """
    Build an edge mask from Preprocessed/page-X.jpg.
    """
    pre = cv2.imread(pre_path, cv2.IMREAD_GRAYSCALE)
    if pre is None:
        return None

    edges = cv2.Canny(pre, 50, 150)
    # Dilate so thin strokes count
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    return edges


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA score in [0,1]
    - Uses edge pixels only (text strokes)
    - Detects "spike-y tail" behaviour (local edits) vs uniform residuals (clean)
    """
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    pre_dir = os.path.join(forensic_output_dir, "Preprocessed")

    if not os.path.exists(ela_dir):
        return 0.0

    debug = os.environ.get("FORENSICS_DEBUG", "0") == "1"

    page_scores: List[float] = []

    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        ela_path = os.path.join(ela_dir, img_name)
        pre_path = os.path.join(pre_dir, img_name)

        try:
            with Image.open(ela_path).convert("L") as im:
                ela = np.array(im, dtype=np.float32) / 255.0
        except Exception:
            continue

        edges = None
        if os.path.exists(pre_path):
            edges = _edge_mask_from_preprocessed(pre_path)

        if edges is not None:
            mask = edges > 0
            vals = ela[mask]
        else:
            # fallback: use non-background pixels
            vals = ela[ela > 0.05]

        # remove tiny residual floor
        vals = vals[vals > 0.05]

        if vals.size < 500:
            page_scores.append(0.0)
            continue

        med, mad, p99 = _robust_stats(vals)
        eps = 1e-6

        # Robust "how spiky is the tail" metric
        z99 = (p99 - med) / (mad + eps)

        # Tail mass above a robust threshold
        thr = med + 6.0 * mad
        tail_mass = float(np.mean(vals > thr))

        # Clean shortcut: tail not spiky
        if z99 < 12.0 and tail_mass < 0.002:
            score_page = 0.0
        else:
            # Map to 0..1
            z_norm = float(np.clip((z99 - 12.0) / 18.0, 0.0, 1.0))
            m_norm = float(np.clip((tail_mass - 0.002) / 0.02, 0.0, 1.0))

            raw = 0.75 * z_norm + 0.25 * m_norm
            score_page = float(np.clip(raw ** 1.2, 0.0, 1.0))

        if debug:
            print(f"[ELA] {img_name} med={med:.3f} mad={mad:.3f} p99={p99:.3f} z99={z99:.1f} tail={tail_mass:.4f} -> {score_page:.3f}")

        page_scores.append(score_page)

    if not page_scores:
        return 0.0

    # Strongest page should decide (single-page tampering)
    score = float(np.max(page_scores))
    return float(round(score, 3))
