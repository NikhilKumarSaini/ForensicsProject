from PIL import Image
import numpy as np
import os


def compression_difference(image_path, save_path):
    """
    Compression difference map.

    Key changes:
    - Bigger quality gap (35 vs 95) so altered regions pop.
    - Normalize per page (like ELA) so results are comparable across docs.
    - Save JPG only.
    """
    img = Image.open(image_path).convert("RGB")

    low = save_path.replace(".jpg", "_low.jpg")
    high = save_path.replace(".jpg", "_high.jpg")

    # stronger separation
    img.save(low, "JPEG", quality=35, optimize=True, subsampling=0)
    img.save(high, "JPEG", quality=95, optimize=True, subsampling=0)

    a = np.asarray(Image.open(low).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(high).convert("RGB"), dtype=np.int16)

    diff = np.abs(a - b).astype(np.float32)
    diff_gray = diff.mean(axis=2)

    mx = float(diff_gray.max())
    if mx < 1e-6:
        out = np.zeros_like(diff_gray, dtype=np.uint8)
    else:
        out = np.clip((diff_gray / mx) * 255.0, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(save_path, "JPEG", quality=95, optimize=True, subsampling=0)

    img.close()
    os.remove(low)
    os.remove(high)
