import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# ==================================================
# PATHS
# ==================================================
ROOT = os.getcwd()
OUT_DIR = os.path.join(ROOT, "sample_statements")
os.makedirs(OUT_DIR, exist_ok=True)

# A4 @ ~150 DPI
W, H = 1240, 1754

SCB_BLUE = (0, 92, 169)
SCB_GREEN = (0, 166, 81)

# ==================================================
# IMAGE DEGRADATION UTILITIES
# ==================================================
def add_noise(img, sigma):
    arr = np.array(img).astype(np.float32)
    noise = np.random.normal(0, sigma, arr.shape)
    arr = np.clip(arr + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def recompress(img, quality):
    tmp = img.copy()
    path = "_tmp.jpg"
    tmp.save(path, "JPEG", quality=quality, subsampling=2)
    out = Image.open(path).copy()
    os.remove(path)
    return out


def embed_pdf(img, pdf_path, quality):
    tmp = pdf_path.replace(".pdf", ".jpg")
    img.save(tmp, "JPEG", quality=quality, subsampling=2)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawImage(tmp, 0, 0, width=A4[0], height=A4[1])
    c.showPage()
    c.save()
    os.remove(tmp)

# ==================================================
# STATEMENT GENERATOR
# ==================================================
def generate_statement(misalign_px, noise_sigma, blur_radius, jpeg_quality):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    try:
        font_main = ImageFont.truetype("arial.ttf", 28)
        font_alt = ImageFont.truetype("cour.ttf", 26)
    except:
        font_main = font_alt = ImageFont.load_default()

    # -------- Header --------
    d.rectangle((0, 0, W, 140), fill=(235, 243, 252))
    d.text((130, 45), "Standard Chartered", fill=SCB_BLUE, font=font_main)

    # Fake SCB logo
    d.ellipse((50, 40, 95, 85), fill=SCB_BLUE)
    d.ellipse((70, 60, 115, 105), fill=SCB_GREEN)

    y = 170
    d.text((60, y), "Credit Card Statement", fill=SCB_BLUE, font=font_main)
    y += 50

    meta = [
        ("Account Holder", "BABIN DAS"),
        ("Account Number", "109000000671452"),
        ("Statement Period", "12 Nov 2024 – 11 Dec 2024"),
        ("Credit Limit (INR)", "100,500.00"),
        ("Total Due (INR)", "19,998.61"),
        ("Minimum Due (INR)", "1,998.61"),
    ]

    for k, v in meta:
        d.text((60, y), k, fill="black", font=font_main)
        d.text(
            (520 + np.random.randint(-misalign_px, misalign_px), y),
            v,
            fill="black",
            font=font_alt,
        )
        y += 38

    y += 15
    d.rectangle((50, y, W - 50, y + 40), fill=SCB_GREEN)
    d.text((60, y + 8), "Transactions", fill="white", font=font_main)
    y += 55

    # -------- MANY TRANSACTIONS --------
    for i in range(30):
        d.text((60, y), f"{i+1:02d}/12/24", fill="black", font=font_main)
        d.text((180, y), f"Retail Spend #{i+1}", fill="black", font=font_alt)
        d.text(
            (920 + np.random.randint(-misalign_px, misalign_px), y),
            f"{random_amount():,.2f}",
            fill="black",
            font=font_main,
        )
        y += 32

        if y > H - 100:
            break

    # -------- HEAVY DEGRADATIONS --------
    img = add_noise(img, noise_sigma)
    img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Double recompression (ELA killer)
    img = recompress(img, jpeg_quality)
    img = recompress(img, jpeg_quality - 10)

    return img


def random_amount():
    return np.random.uniform(120, 12000)

# ==================================================
# GENERATE ALL PDFs (ALL HEAVILY MANIPULATED)
# ==================================================
def generate_all():
    specs = [
        ("manipulated_A.pdf", 12, 14.0, 1.2, 55),
        ("manipulated_B.pdf", 18, 20.0, 1.8, 45),
        ("manipulated_C.pdf", 26, 28.0, 2.5, 35),
    ]

    for name, misalign, noise, blur, quality in specs:
        img = generate_statement(misalign, noise, blur, quality)
        embed_pdf(img, os.path.join(OUT_DIR, name), quality)

    print("✅ All heavily manipulated PDFs generated.")

if __name__ == "__main__":
    generate_all()
