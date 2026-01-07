import os
from PIL import Image
import numpy as np


def perform_ela(image_path: str, save_path: str, quality: int = 85) -> None:
    """
    Error Level Analysis (ELA) that produces a normalized residual map.

    Key changes vs your old version:
    - Use numpy to compute residuals.
    - Normalize residual per page by its max, so "enhance(10)" saturation does not flatten all docs.
    - Save as JPG only.
    """
    original = Image.open(image_path).convert("RGB")

    # temp recompressed jpg
    temp_path = save_path + ".tmp.jpg"
    original.save(temp_path, "JPEG", quality=quality, optimize=True, subsampling=0)

    recompressed = Image.open(temp_path).convert("RGB")

    a = np.asarray(original, dtype=np.int16)
    b = np.asarray(recompressed, dtype=np.int16)

    diff = np.abs(a - b).astype(np.float32)  # 0..255
    diff_gray = diff.mean(axis=2)            # 0..255

    mx = float(diff_gray.max())
    if mx < 1e-6:
        out = np.zeros_like(diff_gray, dtype=np.uint8)
    else:
        # normalize to full contrast
        out = np.clip((diff_gray / mx) * 255.0, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(save_path, "JPEG", quality=95, optimize=True, subsampling=0)

    original.close()
    recompressed.close()
    os.remove(temp_path)
