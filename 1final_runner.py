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
    FINAL scoring runner
    - Uses forensic folder that matches this pdf (not latest folder).
    - Forensics (70%) + ML (30%), with clean gate based on forensics only.
    """

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FORENSICS_OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "Forensics_Output")
    REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # -------------------------------------------------
    # PICK FORENSICS FOLDER FOR THIS PDF (NOT "LATEST")
    # -------------------------------------------------
    pdf_base = os.path.splitext(os.path.basename(pdf_path))[0]
    forensic_output_dir = os.path.join(FORENSICS_OUTPUT_ROOT, pdf_base)

    # Safety fallback if folder name doesn't match
    if not os.path.isdir(forensic_output_dir):
        all_dirs = [
            d for d in os.listdir(FORENSICS_OUTPUT_ROOT)
            if os.path.isdir(os.path.join(FORENSICS_OUTPUT_ROOT, d))
        ]
        if not all_dirs:
            raise FileNotFoundError("No forensics output folders found")
        latest_dir = sorted(all_dirs, reverse=True)[0]
        forensic_output_dir = os.path.join(FORENSICS_OUTPUT_ROOT, latest_dir)
        forensics_folder_name = latest_dir
    else:
        forensics_folder_name = pdf_base

    # -------------------------------------------------
    # FORENSIC SCORES (0–1)
    # -------------------------------------------------
    ela_score = compute_ela_score(forensic_output_dir)
    noise_score = compute_noise_score(forensic_output_dir)
    compression_score = compute_compression_score(forensic_output_dir)
    font_score = compute_font_alignment_score(forensic_output_dir)
    metadata_score = compute_metadata_score(pdf_path)

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
        ml_result = predict_risk({
            "ela_score": ela_score,
            "noise_score": noise_score,
            "compression_score": compression_score,
            "font_score": font_score,
            "metadata_score": metadata_score,
            "forensic_risk": forensic_risk
        })
        ml_probability = ml_result.get("probability", 0.5)

        final_score_01 = (0.7 * forensic_risk) + (0.3 * ml_probability)
        final_score_100 = round(final_score_01 * 100, 2)

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

    report = {
        "record_id": record_id,
        "timestamp": datetime.utcnow().isoformat(),
        "forensics_folder": forensics_folder_name,
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

    report_path = os.path.join(REPORTS_DIR, f"{record_id}_final_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    report["report_path"] = report_path
    return report
