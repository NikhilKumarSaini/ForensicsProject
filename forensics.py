import os
from preprocess import preprocess_image
from ela import perform_ela
from compression import compression_difference
from noise import noise_pattern_analysis
from font_alignment import font_alignment_check


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

IMAGE_ROOT = os.path.join(PROJECT_ROOT, "Images")
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Forensics_Output")

os.makedirs(OUTPUT_ROOT, exist_ok=True)

for folder in os.listdir(IMAGE_ROOT):
    img_folder = os.path.join(IMAGE_ROOT, folder)
    if not os.path.isdir(img_folder):
        continue

    print(f"Processing: {folder}")

    base_out = os.path.join(OUTPUT_ROOT, folder)

    pre_dir = os.path.join(base_out, "Preprocessed")
    ela_dir = os.path.join(base_out, "ELA")
    comp_dir = os.path.join(base_out, "Compression")
    noise_dir = os.path.join(base_out, "Noise")
    font_dir = os.path.join(base_out, "Font_Alignment")

    for d in [pre_dir, ela_dir, comp_dir, noise_dir, font_dir]:
        os.makedirs(d, exist_ok=True)

    for img in os.listdir(img_folder):
        if img.lower().endswith((".png", ".jpg", ".jpeg")):
            img_path = os.path.join(img_folder, img)

            # Keep output names as .jpg for compatibility in downstream scoring
            out_name = os.path.splitext(img)[0] + ".jpg"

            pre_path = os.path.join(pre_dir, out_name)
            ela_path = os.path.join(ela_dir, out_name)
            comp_path = os.path.join(comp_dir, out_name)
            noise_path = os.path.join(noise_dir, out_name)
            font_out = os.path.join(font_dir, out_name)

            preprocess_image(img_path, pre_path)
            perform_ela(img_path, ela_path)
            compression_difference(img_path, comp_path)
            noise_pattern_analysis(img_path, noise_path)
            font_alignment_check(img_path, font_out)

print("Image Forensics completed successfully")
