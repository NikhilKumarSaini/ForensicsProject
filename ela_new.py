import os
import tempfile
from PIL import Image, ImageChops, ImageEnhance


def perform_ela(image_path: str, save_path: str, quality: int = 90) -> None:
    """
    ELA output image (diff) written to save_path.

    Key fixes:
    - recompress at fixed quality
    - compute diff
    - scale adaptively based on max residual (no fixed enhance(10) saturation)
    """
    original = Image.open(image_path).convert("RGB")

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    os.close(tmp_fd)

    try:
        original.save(tmp_path, "JPEG", quality=quality, optimize=True)

        recompressed = Image.open(tmp_path).convert("RGB")
        diff = ImageChops.difference(original, recompressed)

        # Adaptive scaling: stretch residuals so max becomes 255
        extrema = diff.getextrema()  # [(min,max) per channel]
        max_residual = max(ch[1] for ch in extrema) if extrema else 0

        if max_residual > 0:
            scale = 255.0 / float(max_residual)
        else:
            scale = 1.0

        ela_image = ImageEnhance.Brightness(diff).enhance(scale)

        # Save ELA image
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        ela_image.save(save_path, "JPEG", quality=95, optimize=True)

    finally:
        try:
            original.close()
        except Exception:
            pass
        try:
            recompressed.close()
        except Exception:
            pass
        try:
            os.remove(tmp_path)
        except Exception:
            pass
