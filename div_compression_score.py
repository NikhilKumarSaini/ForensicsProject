
# import os
# import numpy as np
# from PIL import Image
# import cv2


# def compute_compression_score(forensic_output_dir: str) -> float:
#     """
#     Compression tampering score (0.0 – 1.0)

#     Factors used:
#     1. Residual energy
#     2. Spatial concentration
#     3. Total highlighted area
#     4. Largest connected patch
#     5. Number of distinct manipulation regions (connected components)
#     """

#     comp_dir = os.path.join(forensic_output_dir, "Compression")
#     if not os.path.exists(comp_dir):
#         return 0.0

#     page_scores = []

#     for fname in os.listdir(comp_dir):
#         if not fname.lower().endswith(".jpg"):
#             continue

#         img_path = os.path.join(comp_dir, fname)

#         try:
#             with Image.open(img_path).convert("L") as im:
#                 gray = np.array(im, dtype=np.float32)
#         except Exception:
#             continue

#         # Normalize to [0, 1]
#         gray /= 255.0
#         h, w = gray.shape
#         total_pixels = h * w

#         # Remove near-zero background
#         active_mask = gray > 0.02
#         if np.sum(active_mask) < 100:
#             page_scores.append(0.0)
#             continue

#         active_vals = gray[active_mask]

#         # High-energy residuals (top 5%)
#         high_thresh = np.percentile(active_vals, 95)
#         high_mask = gray >= high_thresh

#         high_pixel_count = int(np.sum(high_mask))
#         if high_pixel_count < 50:
#             page_scores.append(0.0)
#             continue

#         # 1️⃣ Energy
#         energy = float(np.mean(gray[high_mask]))

#         # 2️⃣ Concentration
#         concentration = high_pixel_count / total_pixels

#         # 3️⃣ Area ratio
#         area_ratio = concentration

#         # Connected components analysis
#         mask_uint8 = (high_mask * 255).astype(np.uint8)
#         num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
#             mask_uint8, connectivity=8
#         )

#         # Ignore background label (0) and very small regions
#         region_areas = [
#             stats[i, cv2.CC_STAT_AREA]
#             for i in range(1, num_labels)
#             if stats[i, cv2.CC_STAT_AREA] > 100
#         ]

#         # 4️⃣ Largest patch ratio
#         if region_areas:
#             largest_patch_ratio = max(region_areas) / total_pixels
#         else:
#             largest_patch_ratio = 0.0

#         # 5️⃣ Manipulation count score (NEW)
#         manipulation_count = len(region_areas)

#         # Normalize manipulation count (cap at 5)
#         manipulation_score = min(1.0, manipulation_count / 5.0)

#         # 🔢 Final weighted score
#         raw_score = (
#             0.30 * energy +
#             0.20 * concentration * 10.0 +
#             0.15 * area_ratio * 10.0 +
#             0.20 * largest_patch_ratio * 15.0 +
#             0.15 * manipulation_score
#         )

#         score = min(1.0, raw_score)
#         page_scores.append(score)

#     if not page_scores:
#         return 0.0

#     # Max-page strategy
#     return float(round(max(page_scores), 3))
import os
import numpy as np
from PIL import Image
import cv2


def compute_compression_score(forensic_output_dir: str) -> float:
    """
    Location-driven compression tampering score (0.0 – 1.0)

    Priority:
    1. Number of distinct manipulation locations (dominant)
    2. Residual energy (secondary)
    3. Area coverage (minor stabilizer)
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0

    page_scores = []

    for fname in os.listdir(comp_dir):
        if not fname.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(comp_dir, fname)

        try:
            with Image.open(img_path).convert("L") as im:
                gray = np.array(im, dtype=np.float32)
        except Exception:
            continue

        gray /= 255.0
        h, w = gray.shape
        total_pixels = h * w

        # Remove background
        active_vals = gray[gray > 0.02]
        if active_vals.size < 100:
            page_scores.append(0.0)
            continue

        # High residuals
        high_thresh = np.percentile(active_vals, 95)
        high_mask = gray >= high_thresh

        if np.sum(high_mask) < 50:
            page_scores.append(0.0)
            continue

        # Connected components = manipulation locations
        mask_uint8 = (high_mask * 255).astype(np.uint8)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask_uint8, connectivity=8
        )

        # Filter small noise regions
        region_areas = [
            stats[i, cv2.CC_STAT_AREA]
            for i in range(1, num_labels)
            if stats[i, cv2.CC_STAT_AREA] > 120
        ]

        manipulation_locations = len(region_areas)

        # --- 1️⃣ LOCATION SCORE (dominant) ---
        location_score = min(1.0, manipulation_locations / 4.0)

        # --- 2️⃣ ENERGY SCORE ---
        energy_score = float(np.mean(gray[high_mask]))

        # --- 3️⃣ AREA SCORE (weak stabilizer) ---
        area_score = float(np.sum(high_mask)) / total_pixels

        # --- FINAL SCORE ---
        final_score = (
            0.55 * location_score +
            0.30 * energy_score +
            0.15 * area_score * 10.0
        )

        page_scores.append(min(1.0, final_score))

    if not page_scores:
        return 0.0

    return float(round(max(page_scores), 3))


