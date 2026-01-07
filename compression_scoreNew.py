import os
from PIL import Image
import numpy as np


def compute_compression_score(forensic_output_dir: str) -> float:
    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    debug = os.getenv("DEBUG_FORENSICS", "0") == "1"

    page_scores = []

    for img_name in os.listdir(comp_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(comp_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as im:
                arr = np.asarray(im, dtype=np.float32) / 255.0
        except Exception:
            continue

        flat = arr.reshape(-1)

        # ignore background
        flat = flat[flat > 0.04]
        if flat.size < 2000:
            continue

        q50 = float(np.quantile(flat, 0.50))
        q95 = float(np.quantile(flat, 0.95))
        q99 = float(np.quantile(flat, 0.99))

        tail_gap = max(0.0, q99 - q95)
        tail_lift = max(0.0, q95 - q50)

        # strong-area ratio, relative threshold (not fixed 0.25)
        thr = min(0.95, q95 + 0.5 * (q99 - q95))
        strong_ratio = float(np.mean(flat > thr))

        raw = (1.2 * tail_gap) + (0.5 * tail_lift) + (0.8 * strong_ratio)

        LO = 0.010
        HI = 0.120
        score = (raw - LO) / (HI - LO)
        score = float(np.clip(score, 0.0, 1.0))

        page_scores.append(score)

        if debug:
            print(f"[COMP] {img_name} q50={q50:.3f} q95={q95:.3f} q99={q99:.3f} thr={thr:.3f} strong={strong_ratio:.4f} raw={raw:.4f} score={score:.3f}")

    if not page_scores:
        return 0.0

    # Document score: max catches a single tampered page
    doc_score = float(np.max(page_scores))
    return float(round(doc_score, 3))
