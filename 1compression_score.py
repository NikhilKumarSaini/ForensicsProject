import os
from io import BytesIO

import numpy as np
from PIL import Image


def _recompress_arr(original: Image.Image, quality: int) -> np.ndarray:
    buf = BytesIO()
    original.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    with Image.open(buf) as tmp:
        return np.array(tmp.convert("RGB"), dtype=np.int16)


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compression inconsistency score in [0,1] from ORIGINAL page JPGs.
    We avoid using the saved Compression images because they were boosted/saturated.

    Method:
    - recompress original at Q=60 and Q=95
    - diff = abs(Q60 - Q95) averaged to grayscale
    - only count "content" pixels (not near-white background)
    - ratio of strong-diff pixels => document score (median over pages)
    """
    folder_name = os.path.basename(forensic_output_dir)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    images_dir = os.path.join(project_root, "Images", folder_name)

    if not os.path.isdir(images_dir):
        return 0.0

    ratios = []

    for img_name in sorted(os.listdir(images_dir)):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(images_dir, img_name)

        try:
            with Image.open(img_path) as im:
                orig = im.convert("RGB")
                low = _recompress_arr(orig, quality=60)
                high = _recompress_arr(orig, quality=95)
                orig_arr = np.array(orig, dtype=np.int16)
        except Exception:
            continue

        diff = np.abs(low - high).astype(np.float32)
        diff_gray = diff.mean(axis=2)  # 0..255

        # content mask: exclude near-white background
        orig_gray = orig_arr.mean(axis=2).astype(np.float32)
        content = orig_gray < 245.0

        denom = int(content.sum())
        if denom < 5000:
            continue

        # strong diff threshold (in 0..255)
        strong = diff_gray > 18.0

        ratio = float((strong & content).sum()) / float(denom)
        ratios.append(ratio)

    if not ratios:
        return 0.0

    doc_ratio = float(np.median(ratios))

    # Map ratio -> [0,1]
    RATIO_CLEAN_MAX = 0.004   # 0.4% strong-diff content pixels -> treat as clean
    RATIO_HIGH = 0.060        # 6% strong-diff content pixels -> very suspicious

    if doc_ratio <= RATIO_CLEAN_MAX:
        return 0.0

    norm = (doc_ratio - RATIO_CLEAN_MAX) / (RATIO_HIGH - RATIO_CLEAN_MAX)
    norm = float(np.clip(norm, 0.0, 1.0))

    score = norm ** 0.65
    return float(round(np.clip(score, 0.0, 1.0), 3))
