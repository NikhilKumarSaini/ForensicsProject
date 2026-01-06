import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    ELA score in [0, 1].

    Goal:
    - Clean digital / programmatic statements → 0 or very low (0.0xx).
    - Manipulated statements → higher values, suitable for clean/low/moderate/high verdicts.

    Approach:
    - Use grayscale ELA intensity.
    - For each page:
        - Ignore near-zero background.
        - Compute median, 90th percentile, 99th percentile.
    - For the document:
        - Use medians of medians / p90, and max of p99 (worst page).
        - Derive simple shape metrics (spread and spike).
    - Map these shape metrics to a 0–1 score.
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    page_meds = []
    page_p90s = []
    page_p99s = []

    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(ela_dir, img_name)

        try:
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)
        except Exception:
            continue

        flat = arr.reshape(-1)

        # Drop pure background / scanner floor
        flat = flat[flat > 1.0]
        if flat.size == 0:
            continue

        # Normalize to [0, 1]
        flat_norm = flat / 255.0

        page_meds.append(float(np.median(flat_norm)))
        page_p90s.append(float(np.percentile(flat_norm, 90)))
        page_p99s.append(float(np.percentile(flat_norm, 99)))

    if not page_meds:
        return 0.0

    # Document-level stats
    med_doc = float(np.median(page_meds))
    p90_doc = float(np.median(page_p90s))
    p99_doc = float(np.max(page_p99s))  # strongest page

    # Shape metrics:
    # spread: how far p90 sits above the median
    spread = max(0.0, p90_doc - med_doc)

    # spike: how far the extreme tail sits above p90
    spike_abs = max(0.0, p99_doc - p90_doc)

    # Avoid division by zero
    spike_rel = spike_abs / (spread + 1e-6)

    # ------------------------------------------------
    # CLEARLY CLEAN DIGITAL / PROGRAMMATIC DOCUMENTS
    # ------------------------------------------------
    # Typical behaviour:
    # - ELA from text edges gives some spread.
    # - Extremes are not dramatically higher than p90.
    #
    # These thresholds are intentionally conservative so
    # programmatic PDFs fall into the "clean" bucket.
    if p99_doc < 0.25 and spike_rel < 0.5:
        return 0.0

    # ------------------------------------------------
    # MAP TO [0, 1]
    # ------------------------------------------------

    # 1) Core signal from extremes.
    #    Below ~0.25: weak overall residuals.
    #    Around ~0.6: very strong residuals.
    core = (p99_doc - 0.25) / (0.60 - 0.25)
    core = float(np.clip(core, 0.0, 1.0))

    # 2) Spike signal: how peaky the tail is vs the bulk.
    #    spike_rel ~0.5 → mild.
    #    spike_rel ~2.0 → strong localized spikes.
    spike_score = (spike_rel - 0.5) / (2.0 - 0.5)
    spike_score = float(np.clip(spike_score, 0.0, 1.0))

    # 3) Optional: penalize extreme spread that is uniform.
    #    This helps keep busy but uniformly compressed pages
    #    from scoring too high just because everything is bright.
    spread_score = (spread - 0.05) / (0.35 - 0.05)
    spread_score = float(np.clip(spread_score, 0.0, 1.0))

    # Final combination:
    # - core and spike dominate
    # - spread has smaller influence
    score = 0.5 * core + 0.35 * spike_score + 0.15 * spread_score

    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))