import os
from typing import List, Tuple

import numpy as np
from PIL import Image
import cv2


def _robust_stats(x: np.ndarray) -> Tuple[float, float, float]:
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)))
    p99 = float(np.percentile(x, 99))
    return med, mad, p99


def _edge_mask_from_preprocessed(pre_path: str) -> np.ndarray:
    pre = cv2.imread(pre_path, cv2.IMREAD_GRAYSCALE)
    if pre is None:
        return None
    edges = cv2.Canny(pre, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    return edges


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compression score in [0,1]
    - Reads Forensics_Output/<doc>/Compression/page-X.jpg
    - Scores edge-only residual distribution (tail spikes = suspicious)
    """
    comp_dir = os.path.join(forensic_output_dir, "Compression")
    pre_dir = os.path.join(forensic_output_dir, "Preprocessed")

    if not os.path.exists(comp_dir):
        return 0.0

    debug = os.environ.get("FORENSICS_DEBUG", "0") == "1"

    page_scores: List[float] = []

    for img_name in os.listdir(comp_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        comp_path = os.path.join(comp_dir, img_name)
        pre_path = os.path.join(pre_dir, img_name)

        try:
            with Image.open(comp_path).convert("L") as im:
                comp = np.array(im, dtype=np.float32) / 255.0
        except Exception:
            continue

        edges = None
        if os.path.exists(pre_path):
            edges = _edge_mask_from_preprocessed(pre_path)

        if edges is not None:
            mask = edges > 0
            vals = comp[mask]
        else:
            vals = comp[comp > 0.05]

        vals = vals[vals > 0.05]

        if vals.size < 500:
            page_scores.append(0.0)
            continue

        med, mad, p99 = _robust_stats(vals)
        eps = 1e-6
        z99 = (p99 - med) / (mad + eps)

        thr = med + 6.0 * mad
        tail_mass = float(np.mean(vals > thr))

        # Compression diffs can be naturally a bit noisier than ELA diffs
        if z99 < 11.0 and tail_mass < 0.003:
            score_page = 0.0
        else:
            z_norm = float(np.clip((z99 - 11.0) / 20.0, 0.0, 1.0))
            m_norm = float(np.clip((tail_mass - 0.003) / 0.03, 0.0, 1.0))
            raw = 0.70 * z_norm + 0.30 * m_norm
            score_page = float(np.clip(raw ** 1.15, 0.0, 1.0))

        if debug:
            print(f"[COMP] {img_name} med={med:.3f} mad={mad:.3f} p99={p99:.3f} z99={z99:.1f} tail={tail_mass:.4f} -> {score_page:.3f}")

        page_scores.append(score_page)

    if not page_scores:
        return 0.0

    score = float(np.max(page_scores))
    return float(round(score, 3))
