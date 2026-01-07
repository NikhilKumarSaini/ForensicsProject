import os
import numpy as np
from PIL import Image, ImageChops


def perform_ela(image_path: str, save_path: str, quality: int = 90) -> None:
    """
    Non-saturating ELA generator.

    Fix:
    - Removes Brightness.enhance(10) which clips and makes all pages look high.
    - Normalizes diff to 0..255 based on page max diff (preserves structure).
    """

    original = Image.open(image_path).convert("RGB")

    temp_path = save_path + ".tmp.jpg"
    original.save(temp_path, "JPEG", quality=quality)

    recompressed = Image.open(temp_path).convert("RGB")
    diff = ImageChops.difference(original, recompressed)

    arr = np.array(diff, dtype=np.float32)
    maxv = float(arr.max())
    if maxv < 1.0:
        maxv = 1.0

    arr = np.clip(arr * (255.0 / maxv), 0, 255).astype(np.uint8)
    ela_image = Image.fromarray(arr, mode="RGB")
    ela_image.save(save_path, "JPEG")

    original.close()
    recompressed.close()
    os.remove(temp_path)
