from PyPDF2 import PdfReader


def compute_metadata_score(pdf_path: str) -> float:
    """
    Soft metadata scoring (0.0 – 1.0)

    Fix:
    - Treat common programmatic PDF generators (reportlab, fpdf, pymupdf, etc.)
      as LOW risk, not medium.
    """

    try:
        reader = PdfReader(pdf_path)
        meta = reader.metadata

        if not meta:
            return 0.2  # unknown metadata → mild risk

        producer = (meta.producer or "").lower()
        creator = (meta.creator or "").lower()

        text = (producer + " " + creator).strip()

        # -------------------------------------------------
        # CLEAN / COMMON DIGITAL SOURCES
        # -------------------------------------------------
        clean_sources = [
            "microsoft", "word", "excel",
            "chrome", "mac os", "libreoffice",
            "google", "docs", "drive",
        ]

        # Programmatic / dev-generated PDFs (your use case)
        programmatic_clean = [
            "reportlab", "fpdf", "pyfpdf",
            "pymupdf", "fitz",
            "wkhtmltopdf", "weasyprint",
            "pandoc", "latex", "tex",
        ]

        if any(x in text for x in clean_sources):
            return 0.1

        if any(x in text for x in programmatic_clean):
            return 0.1  # IMPORTANT FIX

        # -------------------------------------------------
        # SCANNERS / PRINT FLOWS
        # -------------------------------------------------
        scanner_sources = [
            "scanner", "print", "cups", "xerox", "canon", "epson", "hp", "brother"
        ]
        if any(x in text for x in scanner_sources):
            return 0.25

        # -------------------------------------------------
        # IMAGE / GRAPHIC EDITORS (STRONG SIGNAL)
        # -------------------------------------------------
        editor_sources = [
            "photoshop", "canva", "gimp", "illustrator", "indesign"
        ]
        if any(x in text for x in editor_sources):
            return 0.8

        # -------------------------------------------------
        # UNKNOWN
        # -------------------------------------------------
        return 0.35

    except Exception:
        return 0.2
