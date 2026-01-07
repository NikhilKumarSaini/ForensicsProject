import fitz
import os

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

            image_name = f"page-{page_number + 1}.png"
            image_path = os.path.join(output_folder, image_name)
            pix.save(image_path)

        print(f"Converted {doc.page_count} Pages Successfully")

    except Exception as e:
        print(f"Error converting {pdf_file}: {str(e)}")

    finally:
        if doc is not None and not doc.is_closed:
            doc.close()

    print(f"Done: images saved in {output_folder}")

print("PDF Pages converted to images successfully!")
