# ela.py
import os
from PIL import Image, ImageChops, ImageEnhance


def perform_ela(image_path: str, save_path: str, quality: int = 90) -> None:
    """
    Perform Error Level Analysis (ELA) on an input image and save the ELA result.
    """
    original = Image.open(image_path).convert("RGB")

    temp_path = save_path + ".tmp.jpg"
    original.save(temp_path, "JPEG", quality=quality)

    recompressed = Image.open(temp_path).convert("RGB")
    diff = ImageChops.difference(original, recompressed)

    enhancer = ImageEnhance.Brightness(diff)
    ela_image = enhancer.enhance(10.0)

    ela_image.save(save_path, "JPEG")

    original.close()
    recompressed.close()
    os.remove(temp_path)