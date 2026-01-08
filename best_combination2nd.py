# =========================
# details.py  (UPDATED: save JPG only)
# =========================
import fitz
import os
from io import BytesIO
from PIL import Image

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

pdf_folder = os.path.join(project_root, "uploads")
images_folder = os.path.join(project_root, "Images")

print("PDF folder:", pdf_folder)
print("Images folder:", images_folder)

if not os.path.exists(pdf_folder):
    print("error pdf folder not exists")

os.makedirs(images_folder, exist_ok=True)

for pdf_file in os.listdir(pdf_folder):
    if not pdf_file.lower().endswith(".pdf"):
        continue

    pdf_path = os.path.join(pdf_folder, pdf_file)
    pdf_name = os.path.splitext(pdf_file)[0]
    output_folder = os.path.join(images_folder, pdf_name)

    os.makedirs(output_folder, exist_ok=True)

    print(f"Converting: {pdf_file}")
    doc = None

    try:
        doc = fitz.open(pdf_path)

        # Render at 2x scale for stable text edges (roughly 144 DPI)
        mat = fitz.Matrix(2, 2)

        for page_number in range(doc.page_count):
            page = doc.load_page(page_number)

            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)

            # Save as JPG only (manager requirement)
            image_name = f"page-{page_number + 1}.jpg"
            image_path = os.path.join(output_folder, image_name)

            # Convert pixmap -> PIL -> JPEG to guarantee .jpg output
            png_bytes = pix.tobytes("png")
            pil_img = Image.open(BytesIO(png_bytes)).convert("RGB")
            pil_img.save(image_path, "JPEG", quality=92, optimize=True)

        print(f"Converted {doc.page_count} Pages Successfully")

    except Exception as e:
        print(f"Error converting {pdf_file}: {str(e)}")

    finally:
        if doc is not None and not doc.is_closed:
            doc.close()

    print(f"Done: images saved in {output_folder}")

print("PDF Pages converted to images successfully!")


# =========================
# forensics.py  (UNCHANGED LOGIC)
# =========================
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


# =========================
# ela.py  (UNCHANGED LOGIC)
# =========================
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


# =========================
# compression.py  (UNCHANGED LOGIC)
# =========================
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


# =========================
# ela_score.py  (UNCHANGED LOGIC)
# =========================
import os
import numpy as np
from PIL import Image


def _patch_values(gray: np.ndarray, grid: int = 60) -> np.ndarray:
    """
    Returns per-patch mean intensity (0..1), ignoring background-heavy patches.
    """
    h, w = gray.shape
    ph = max(h // grid, 10)
    pw = max(w // grid, 10)

    vals = []
    for y in range(0, h, ph):
        for x in range(0, w, pw):
            patch = gray[y:y + ph, x:x + pw]
            if patch.size == 0:
                continue

            active = patch > 2.0
            # Ignore patches that are mostly background
            if active.mean() < 0.12:
                continue

            vals.append(float(patch[active].mean()) / 255.0)

    return np.array(vals, dtype=np.float32)


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA score (0..1)

    Key fixes:
    - LOW CONTENT GUARD:
      If the page has too little active area OR too few usable patches,
      return 0 for that page (prevents Lokesh false positives).
    - More aggressive mapping AFTER the guard so manipulated pages rise.
    """
    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_scores = []

    for name in os.listdir(ela_dir):
        if not name.lower().endswith(".jpg"):
            continue

        path = os.path.join(ela_dir, name)
        try:
            with Image.open(path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        # ---------------- LOW CONTENT GUARD ----------------
        active_fraction = float((gray > 2.0).mean())
        # Very empty pages (Lokesh-style) should not produce ELA spikes
        if active_fraction < 0.015:  # 1.5% of pixels active
            page_scores.append(0.0)
            continue

        vals = _patch_values(gray, grid=60)

        # If too few patches survived, stats become unstable -> treat as clean
        if vals.size < 120:
            page_scores.append(0.0)
            continue

        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med))) + 1e-6
        thresh = med + 3.0 * mad

        ratio = float(np.count_nonzero(vals > thresh)) / float(vals.size)

        # Extra guard: for low-energy documents, small ratios are benign
        if med < 0.03 and ratio < 0.06:
            page_scores.append(0.0)
            continue

        # ---------------- SCORE MAPPING (MORE SENSITIVE) ----------------
        if ratio < 0.01:
            score = 0.0
        elif ratio < 0.03:
            score = 0.12 + (ratio - 0.01) / 0.02 * 0.28   # 0.12 -> 0.40
        elif ratio < 0.07:
            score = 0.40 + (ratio - 0.03) / 0.04 * 0.35   # 0.40 -> 0.75
        else:
            score = 0.75 + min(0.25, (ratio - 0.07) / 0.08 * 0.25)  # up to 1.0

        page_scores.append(float(score))

    if not page_scores:
        return 0.0

    return float(round(min(1.0, max(page_scores)), 3))


# =========================
# compression_score.py  (UNCHANGED LOGIC)
# =========================
import os
import numpy as np
from PIL import Image


def _patch_values(gray: np.ndarray, grid: int = 60) -> np.ndarray:
    h, w = gray.shape
    ph = max(h // grid, 10)
    pw = max(w // grid, 10)

    vals = []
    for y in range(0, h, ph):
        for x in range(0, w, pw):
            patch = gray[y:y + ph, x:x + pw]
            if patch.size == 0:
                continue

            active = patch > 2.0
            if active.mean() < 0.12:
                continue

            vals.append(float(patch[active].mean()) / 255.0)

    return np.array(vals, dtype=np.float32)


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Compression score (0..1) from Compression diff images.

    Fixes:
    - Low-content guard like ELA
    - More aggressive mapping so manipulated rises above 0.1–0.2 range
    """
    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    page_scores = []

    for name in os.listdir(comp_dir):
        if not name.lower().endswith(".jpg"):
            continue

        path = os.path.join(comp_dir, name)
        try:
            with Image.open(path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        active_fraction = float((gray > 2.0).mean())
        if active_fraction < 0.015:
            page_scores.append(0.0)
            continue

        vals = _patch_values(gray, grid=60)
        if vals.size < 120:
            page_scores.append(0.0)
            continue

        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med))) + 1e-6
        thresh = med + 3.0 * mad

        ratio = float(np.count_nonzero(vals > thresh)) / float(vals.size)

        if med < 0.03 and ratio < 0.06:
            page_scores.append(0.0)
            continue

        # Mapping
        if ratio < 0.01:
            score = 0.0
        elif ratio < 0.03:
            score = 0.10 + (ratio - 0.01) / 0.02 * 0.30  # 0.10 -> 0.40
        elif ratio < 0.08:
            score = 0.40 + (ratio - 0.03) / 0.05 * 0.40  # 0.40 -> 0.80
        else:
            score = 0.80 + min(0.20, (ratio - 0.08) / 0.10 * 0.20)

        page_scores.append(float(score))

    if not page_scores:
        return 0.0

    return float(round(min(1.0, max(page_scores)), 3))


# =========================
# final_runner.py  (UNCHANGED LOGIC)
# =========================
import os
import json
from datetime import datetime

from scoring.ela_score import compute_ela_score
from scoring.noise_score import compute_noise_score
from scoring.compression_score import compute_compression_score
from scoring.font_alignment_score import compute_font_alignment_score
from scoring.metadata_score import compute_metadata_score
from scoring.final_score import compute_final_score

from ml.predict_xgb import predict_risk


def run_scoring(record_id: int, pdf_path: str) -> dict:
    """
    FINAL scoring runner (LOCKED – OPTION 2)

    ✔ Clean gate based ONLY on forensic risk
    ✔ ML is SOFT signal (ignored for clean docs)
    ✔ Forensics (70%) + ML (30%)
    ✔ Final score: 0–100
    ✔ Professional verdicts
    """

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FORENSICS_OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Forensics_Output")
    REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # -------------------------------------------------
    # PICK FORENSICS FOLDER FOR THIS PDF
    # -------------------------------------------------
    # Example:
    # uploads/1767727889_NewFinalManipulated.pdf
    # -> Forensics_Output/1767727889_NewFinalManipulated
    pdf_base = os.path.splitext(os.path.basename(pdf_path))[0]
    forensic_output_dir = os.path.join(FORENSICS_OUTPUT_ROOT, pdf_base)

    if not os.path.isdir(forensic_output_dir):
        # Fallback: old behaviour (latest folder) if something is off
        all_dirs = [
            d for d in os.listdir(FORENSICS_OUTPUT_ROOT)
            if os.path.isdir(os.path.join(FORENSICS_OUTPUT_ROOT, d))
        ]
        if not all_dirs:
            raise FileNotFoundError("No forensics output folders found")

        latest_dir = sorted(all_dirs, reverse=True)[0]
        forensic_output_dir = os.path.join(FORENSICS_OUTPUT_ROOT, latest_dir)
        pdf_base = latest_dir

    # -------------------------------------------------
    # FORENSIC SCORES (0–1)
    # -------------------------------------------------
    ela_score = compute_ela_score(forensic_output_dir)
    noise_score = compute_noise_score(forensic_output_dir)
    compression_score = compute_compression_score(forensic_output_dir)
    font_score = compute_font_alignment_score(forensic_output_dir)
    metadata_score = compute_metadata_score(pdf_path)

    # -------------------------------------------------
    # FORENSIC AGGREGATION (RULE BASED)
    # -------------------------------------------------
    forensic_risk = compute_final_score(
        ela_score=ela_score,
        noise_score=noise_score,
        compression_score=compression_score,
        font_score=font_score,
        metadata_score=metadata_score
    )

    # -------------------------------------------------
    # CLEAN DOCUMENT GATE (FORENSIC ONLY)
    # -------------------------------------------------
    if forensic_risk < 0.06:
        final_score_100 = 0.0
        risk_category = "Clean Document"
        ml_probability = 0.0

    else:
        # -------------------------------------------------
        # ML PROBABILITY (SOFT SIGNAL)
        # -------------------------------------------------
        ml_result = predict_risk({
            "ela_score": ela_score,
            "noise_score": noise_score,
            "compression_score": compression_score,
            "font_score": font_score,
            "metadata_score": metadata_score,
            "forensic_risk": forensic_risk
        })

        ml_probability = ml_result.get("probability", 0.5)

        # -------------------------------------------------
        # FINAL COMBINED SCORE (0–100)
        # -------------------------------------------------
        final_score_01 = (0.7 * forensic_risk) + (0.3 * ml_probability)
        final_score_100 = round(final_score_01 * 100, 2)

        # -------------------------------------------------
        # PROFESSIONAL VERDICTS
        # -------------------------------------------------
        if final_score_100 < 10:
            final_score_100 = 0.0
            risk_category = "Clean Document"
        elif final_score_100 < 35:
            risk_category = "Low Risk"
        elif final_score_100 < 55:
            risk_category = "Moderate Risk"
        elif final_score_100 < 75:
            risk_category = "High Risk"
        elif final_score_100 < 90:
            risk_category = "Very High Risk"
        else:
            risk_category = "Critical Risk"

    # -------------------------------------------------
    # FINAL REPORT
    # -------------------------------------------------
    report = {
        "record_id": record_id,
        "timestamp": datetime.utcnow().isoformat(),
        "forensics_folder": pdf_base,

        "final_result": {
            "final_score": final_score_100,
            "risk_category": risk_category
        },

        "components": {
            "forensics": {
                "ela_score": ela_score,
                "noise_score": noise_score,
                "compression_score": compression_score,
                "font_score": font_score,
                "metadata_score": metadata_score,
                "forensic_risk": forensic_risk
            },
            "ml": {
                "ml_probability": ml_probability
            }
        }
    }

    report_path = os.path.join(
        REPORTS_DIR,
        f"{record_id}_final_report.json"
    )

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    report["report_path"] = report_path
    return report
