# ela.py
import os
from PIL import Image, ImageChops, ImageEnhance


def perform_ela(image_path: str, save_path: str, quality: int = 90) -> None:
    """
    Perform Error Level Analysis (ELA) on an input image and save the ELA result.

    Parameters
    ----------
    image_path : str
        Path to the original input image (page raster from PDF).
    save_path : str
        Path where the ELA JPEG image should be written.
    quality : int, optional
        JPEG quality for recompression. Must be constant across the dataset.
    """
    # Load original in a consistent RGB space
    original = Image.open(image_path).convert("RGB")

    # Temporary recompressed copy
    temp_path = save_path + ".tmp.jpg"
    original.save(temp_path, "JPEG", quality=quality)

    # Reload recompressed version
    recompressed = Image.open(temp_path).convert("RGB")

    # Absolute difference between original and recompressed
    diff = ImageChops.difference(original, recompressed)

    # Boost brightness so residuals are visible
    enhancer = ImageEnhance.Brightness(diff)
    ela_image = enhancer.enhance(10.0)

    # Save final ELA image
    ela_image.save(save_path, "JPEG")

    # Cleanup
    original.close()
    recompressed.close()
    os.remove(temp_path)