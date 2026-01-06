from PIL import Image, ImageChops, ImageEnhance  # Pillow
import os


def perform_ela(image_path, save_path, quality=90):
    """
    Perform Error Level Analysis (ELA) on an input image and save the ELA output.

    Parameters
    ----------
    image_path : str
        Path to the original input image.
    save_path : str
        Path where the ELA image should be written (typically .jpg).
    quality : int, optional
        JPEG quality level for recompression. Defaults to 90.
        This should stay constant across all images in a dataset.
    """

    # Open original in RGB so comparison happens in a consistent color space
    original = Image.open(image_path).convert("RGB")

    # Save a recompressed copy at the given quality
    temp_path = save_path.replace(".jpg", "_temp.jpg")
    original.save(temp_path, "JPEG", quality=quality)

    # Compute absolute difference between original and recompressed image
    compressed = Image.open(temp_path).convert("RGB")
    diff = ImageChops.difference(original, compressed)

    # Enhance brightness to make residuals visible
    enhancer = ImageEnhance.Brightness(diff)
    ela_image = enhancer.enhance(10)

    # Persist ELA output and remove temporary file
    ela_image.save(save_path)
    compressed.close()
    original.close()
    os.remove(temp_path)