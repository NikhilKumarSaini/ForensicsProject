from PIL import Image, ImageChops, ImageEnhance
import os
import tempfile


def compression_difference(image_path, save_path):
    """
    Generates a compression inconsistency map by comparing low vs high JPEG quality.

    Key fixes:
    - adaptive scaling (no enhance(10) saturation)
    - slightly stronger separation between low/high qualities
    """
    img = Image.open(image_path).convert("RGB")

    low_fd, low_path = tempfile.mkstemp(suffix="_low.jpg")
    high_fd, high_path = tempfile.mkstemp(suffix="_high.jpg")
    os.close(low_fd)
    os.close(high_fd)

    try:
        # Wider gap helps detect local edits
        img.save(low_path, "JPEG", quality=60, optimize=True)
        img.save(high_path, "JPEG", quality=95, optimize=True)

        low_img = Image.open(low_path).convert("RGB")
        high_img = Image.open(high_path).convert("RGB")

        diff = ImageChops.difference(low_img, high_img)

        extrema = diff.getextrema()
        max_residual = max(ch[1] for ch in extrema) if extrema else 0
        scale = 255.0 / float(max_residual) if max_residual > 0 else 1.0

        comp_image = ImageEnhance.Brightness(diff).enhance(scale)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        comp_image.save(save_path, "JPEG", quality=95, optimize=True)

    finally:
        try:
            img.close()
        except Exception:
            pass
        try:
            low_img.close()
        except Exception:
            pass
        try:
            high_img.close()
        except Exception:
            pass
        for p in (low_path, high_path):
            try:
                os.remove(p)
            except Exception:
                pass
