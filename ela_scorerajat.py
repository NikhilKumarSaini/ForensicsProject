import os
from PIL import Image
import numpy as np


def compute_ela_score(forensic_output_dir: str) -> float:
    """
    Scientifically correct ELA score (0–1) based on ELA residual energy.

    Logic:
    - Use per-pixel ELA intensity (not RGB channel variance).
    - For each ELA page:
        - Collect median and 90th percentile of non-trivial residuals.
    - Across the document:
        - median_raw   → baseline / benign signal level.
        - p90_raw(max) → strongest manipulation spike among pages.
        - spike        → p90_raw / median_raw.

    Behaviour (intended):
    - Clean PDFs (true digital, no edits) → 0.0
    - Word / programmatic PDFs → low score
    - Manipulated PDFs → clear spikes, higher score

    Parameters
    ----------
    forensic_output_dir : str
        Root directory of the forensic output. This function expects
        an "ELA" subdirectory containing JPEG ELA images.

    Returns
    -------
    float
        Score in [0, 1].
    """

    ela_dir = os.path.join(forensic_output_dir, "ELA")
    if not os.path.exists(ela_dir):
        return 0.0

    medians = []
    p90s = []

    for img_name in os.listdir(ela_dir):
        if not img_name.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(ela_dir, img_name)

        try:
            # Work in grayscale intensity: ELA residual magnitude per pixel
            with Image.open(img_path).convert("L") as image:
                arr = np.array(image, dtype=np.float32)

            # ELA residual map
            ela_map = arr

            # Remove scanner / compression floor (very low residuals)
            ela_map = ela_map[ela_map > 1.5]

            if ela_map.size == 0:
                continue

            medians.append(float(np.median(ela_map)))
            p90s.append(float(np.percentile(ela_map, 90)))

        except Exception:
            # Any unreadable / corrupted file is ignored
            continue

    if not medians:
        return 0.0

    # -----------------------------------------------
    # NORMALIZED STATS
    # -----------------------------------------------

    # Overall benign energy level (typical clean pages sit very low here)
    median_raw = float(np.median(medians) / 255.0)

    # Use the strongest page-wide spike, not the median of spikes.
    # This preserves one heavily edited page inside a long statement.
    p90_raw = float(np.max(p90s) / 255.0)

    # Spike factor: how much the high residuals stand above the baseline
    spike = p90_raw / (median_raw + 1e-6)

    # -----------------------------------------------
    # SCORING
    # -----------------------------------------------

    # Clearly clean:
    # - very low overall energy
    # - low high-percentile residuals
    # - no strong spike above the baseline
    if median_raw < 0.02 and p90_raw < 0.05 and spike < 1.3:
        return 0.0

    # Core score from absolute residual level
    # Typical "clean but busy" layouts tend to stay below ~0.03–0.05.
    # Strongly edited content tends to push p90_raw towards ~0.15–0.25 or more.
    base = 0.03   # upper bound of typical clean / benign
    upper = 0.25  # where we treat it as strongly manipulated

    core = (p90_raw - base) / (upper - base)
    core = float(np.clip(core, 0.0, 1.0))

    # Spike contribution: 1.0 = no spike, 2.0 = very strong spike
    spike_norm = (spike - 1.0) / 1.0
    spike_norm = float(np.clip(spike_norm, 0.0, 1.0))

    # Combine: both absolute energy and spike behavior matter
    score = 0.5 * core + 0.5 * spike_norm

    # Final clamp and rounding
    score = float(np.clip(score, 0.0, 1.0))
    return float(round(score, 3))