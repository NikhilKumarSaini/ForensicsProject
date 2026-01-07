from PIL import Image, ImageChops
import os
import numpy as np


def compression_difference(image_path, save_path):
    """
    Non-saturating compression diff generator.

    Fix:
    - Removes Brightness.enhance(10) which clips and forces scores toward 1.
    - Normalizes diff to 0..255 based on page max diff.
    """

    img = Image.open(image_path).convert("RGB")

    low = save_path.replace(".jpg", "_low.jpg")
    high = save_path.replace(".jpg", "_high.jpg")

    img.save(low, "JPEG", quality=70)
    img.save(high, "JPEG", quality=95)

    low_img = Image.open(low).convert("RGB")
    high_img = Image.open(high).convert("RGB")

    diff = ImageChops.difference(low_img, high_img)

    arr = np.array(diff, dtype=np.float32)
    maxv = float(arr.max())
    if maxv < 1.0:
        maxv = 1.0

    arr = np.clip(arr * (255.0 / maxv), 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, mode="RGB")
    out.save(save_path, "JPEG")

    img.close()
    low_img.close()
    high_img.close()

    os.remove(low)
    os.remove(high)
