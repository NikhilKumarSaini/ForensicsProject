
# # # import os
# # # import numpy as np
# # # from PIL import Image
# # # import cv2


# # # def compute_compression_score(forensic_output_dir: str) -> float:
# # #     """
# # #     Compression tampering score (0.0 – 1.0)

# # #     Factors used:
# # #     1. Residual energy
# # #     2. Spatial concentration
# # #     3. Total highlighted area
# # #     4. Largest connected patch
# # #     5. Number of distinct manipulation regions (connected components)
# # #     """

# # #     comp_dir = os.path.join(forensic_output_dir, "Compression")
# # #     if not os.path.exists(comp_dir):
# # #         return 0.0

# # #     page_scores = []

# # #     for fname in os.listdir(comp_dir):
# # #         if not fname.lower().endswith(".jpg"):
# # #             continue

# # #         img_path = os.path.join(comp_dir, fname)

# # #         try:
# # #             with Image.open(img_path).convert("L") as im:
# # #                 gray = np.array(im, dtype=np.float32)
# # #         except Exception:
# # #             continue

# # #         # Normalize to [0, 1]
# # #         gray /= 255.0
# # #         h, w = gray.shape
# # #         total_pixels = h * w

# # #         # Remove near-zero background
# # #         active_mask = gray > 0.02
# # #         if np.sum(active_mask) < 100:
# # #             page_scores.append(0.0)
# # #             continue

# # #         active_vals = gray[active_mask]

# # #         # High-energy residuals (top 5%)
# # #         high_thresh = np.percentile(active_vals, 95)
# # #         high_mask = gray >= high_thresh

# # #         high_pixel_count = int(np.sum(high_mask))
# # #         if high_pixel_count < 50:
# # #             page_scores.append(0.0)
# # #             continue

# # #         # 1️⃣ Energy
# # #         energy = float(np.mean(gray[high_mask]))

# # #         # 2️⃣ Concentration
# # #         concentration = high_pixel_count / total_pixels

# # #         # 3️⃣ Area ratio
# # #         area_ratio = concentration

# # #         # Connected components analysis
# # #         mask_uint8 = (high_mask * 255).astype(np.uint8)
# # #         num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
# # #             mask_uint8, connectivity=8
# # #         )

# # #         # Ignore background label (0) and very small regions
# # #         region_areas = [
# # #             stats[i, cv2.CC_STAT_AREA]
# # #             for i in range(1, num_labels)
# # #             if stats[i, cv2.CC_STAT_AREA] > 100
# # #         ]

# # #         # 4️⃣ Largest patch ratio
# # #         if region_areas:
# # #             largest_patch_ratio = max(region_areas) / total_pixels
# # #         else:
# # #             largest_patch_ratio = 0.0

# # #         # 5️⃣ Manipulation count score (NEW)
# # #         manipulation_count = len(region_areas)

# # #         # Normalize manipulation count (cap at 5)
# # #         manipulation_score = min(1.0, manipulation_count / 5.0)

# # #         # 🔢 Final weighted score
# # #         raw_score = (
# # #             0.30 * energy +
# # #             0.20 * concentration * 10.0 +
# # #             0.15 * area_ratio * 10.0 +
# # #             0.20 * largest_patch_ratio * 15.0 +
# # #             0.15 * manipulation_score
# # #         )

# # #         score = min(1.0, raw_score)
# # #         page_scores.append(score)

# # #     if not page_scores:
# # #         return 0.0

# # #     # Max-page strategy
# # #     return float(round(max(page_scores), 3))
# # import os
# # import numpy as np
# # from PIL import Image
# # import cv2


# # def compute_compression_score(forensic_output_dir: str) -> float:
# #     """
# #     Location-driven compression tampering score (0.0 – 1.0)

# #     Priority:
# #     1. Number of distinct manipulation locations (dominant)
# #     2. Residual energy (secondary)
# #     3. Area coverage (minor stabilizer)
# #     """

# #     comp_dir = os.path.join(forensic_output_dir, "Compression")
# #     if not os.path.exists(comp_dir):
# #         return 0.0

# #     page_scores = []

# #     for fname in os.listdir(comp_dir):
# #         if not fname.lower().endswith(".jpg"):
# #             continue

# #         img_path = os.path.join(comp_dir, fname)

# #         try:
# #             with Image.open(img_path).convert("L") as im:
# #                 gray = np.array(im, dtype=np.float32)
# #         except Exception:
# #             continue

# #         gray /= 255.0
# #         h, w = gray.shape
# #         total_pixels = h * w

# #         # Remove background
# #         active_vals = gray[gray > 0.02]
# #         if active_vals.size < 100:
# #             page_scores.append(0.0)
# #             continue

# #         # High residuals
# #         high_thresh = np.percentile(active_vals, 95)
# #         high_mask = gray >= high_thresh

# #         if np.sum(high_mask) < 50:
# #             page_scores.append(0.0)
# #             continue

# #         # Connected components = manipulation locations
# #         mask_uint8 = (high_mask * 255).astype(np.uint8)
# #         num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
# #             mask_uint8, connectivity=8
# #         )

# #         # Filter small noise regions
# #         region_areas = [
# #             stats[i, cv2.CC_STAT_AREA]
# #             for i in range(1, num_labels)
# #             if stats[i, cv2.CC_STAT_AREA] > 120
# #         ]

# #         manipulation_locations = len(region_areas)

# #         # --- 1️⃣ LOCATION SCORE (dominant) ---
# #         location_score = min(1.0, manipulation_locations / 4.0)

# #         # --- 2️⃣ ENERGY SCORE ---
# #         energy_score = float(np.mean(gray[high_mask]))

# #         # --- 3️⃣ AREA SCORE (weak stabilizer) ---
# #         area_score = float(np.sum(high_mask)) / total_pixels

# #         # --- FINAL SCORE ---
# #         final_score = (
# #             0.55 * location_score +
# #             0.30 * energy_score +
# #             0.15 * area_score * 10.0
# #         )

# #         page_scores.append(min(1.0, final_score))

# #     if not page_scores:
# #         return 0.0

# #     return float(round(max(page_scores), 3))

# import os
# import numpy as np
# from PIL import Image
# import cv2


# def compute_compression_score(forensic_output_dir: str) -> float:
#     """
#     Compression score with strict manipulation-location gating.

#     Stage 1: Detect real manipulation locations
#     Stage 2: Score severity only if locations exist
#     """

#     comp_dir = os.path.join(forensic_output_dir, "Compression")
#     if not os.path.exists(comp_dir):
#         return 0.0

#     page_scores = []

#     for fname in os.listdir(comp_dir):
#         if not fname.lower().endswith(".jpg"):
#             continue

#         path = os.path.join(comp_dir, fname)

#         try:
#             with Image.open(path).convert("L") as im:
#                 gray = np.array(im, dtype=np.float32) / 255.0
#         except Exception:
#             continue

#         h, w = gray.shape
#         total_pixels = h * w

#         # ---------- STEP 1: High-residual mask ----------
#         active = gray > 0.03
#         if np.sum(active) < 200:
#             continue

#         high_thresh = np.percentile(gray[active], 97)
#         high_mask = gray >= high_thresh

#         if np.sum(high_mask) < 80:
#             continue

#         # ---------- STEP 2: Connected components ----------
#         mask = (high_mask * 255).astype(np.uint8)
#         num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
#             mask, connectivity=8
#         )

#         valid_regions = []

#         for i in range(1, num_labels):
#             area = stats[i, cv2.CC_STAT_AREA]
#             x, y, bw, bh, _ = stats[i]

#             # -------- STRICT FILTERING --------
#             if area < 150:
#                 continue

#             aspect_ratio = max(bw, bh) / max(1, min(bw, bh))
#             if aspect_ratio > 8:  # removes text-line noise
#                 continue

#             density = area / (bw * bh)
#             if density < 0.25:
#                 continue

#             valid_regions.append(area)

#         # ---------- HARD GATE ----------
#         if len(valid_regions) == 0:
#             # NO manipulation locations → clean
#             page_scores.append(0.0)
#             continue

#         # ---------- STEP 3: Severity scoring ----------
#         location_count = len(valid_regions)
#         location_score = min(1.0, location_count / 3.0)

#         energy_score = float(np.mean(gray[high_mask]))
#         area_score = sum(valid_regions) / total_pixels

#         final_score = (
#             0.60 * location_score +
#             0.25 * energy_score +
#             0.15 * area_score * 10.0
#         )

#         page_scores.append(min(1.0, final_score))

#     if not page_scores:
#         return 0.0

#     return float(round(max(page_scores), 3))

import os
import numpy as np
from PIL import Image
import cv2
import math


def compute_compression_score(forensic_output_dir: str):
    """
    Compression score based on MANIPULATION LOCATIONS.
    Returns:
        final_score (float): 0.0 – 1.0
        location_scores (list): per-location scores
    """

    comp_dir = os.path.join(forensic_output_dir, "Compression")
    if not os.path.exists(comp_dir):
        return 0.0, []

    page_scores = []
    all_location_scores = []

    for fname in os.listdir(comp_dir):
        if not fname.lower().endswith(".jpg"):
            continue

        img_path = os.path.join(comp_dir, fname)

        try:
            gray = np.array(Image.open(img_path).convert("L"), dtype=np.float32)
        except Exception:
            continue

        gray /= 255.0
        h, w = gray.shape
        total_pixels = h * w

        # ---------- STEP 1: find active residuals ----------
        active_mask = gray > 0.02
        if np.sum(active_mask) < 50:
            continue

        # Use 95th percentile (NOT 97)
        high_thresh = np.percentile(gray[active_mask], 95)
        high_mask = gray >= high_thresh

        if np.sum(high_mask) < 30:
            continue

        # ---------- STEP 2: connected components ----------
        mask_uint8 = (high_mask * 255).astype(np.uint8)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask_uint8, connectivity=8
        )

        location_scores = []

        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            x, y, bw, bh, _ = stats[i]

            # ---- PRACTICAL FILTERS (NOT aggressive) ----
            if area < 60:
                continue
            if bw < 8 or bh < 8:
                continue

            region_mask = (labels == i)

            # ---------- PER-LOCATION FEATURES ----------
            energy = float(np.mean(gray[region_mask]))
            area_ratio = area / total_pixels

            # ---------- LOCATION SCORE ----------
            loc_score = (
                0.7 * energy +
                0.3 * area_ratio * 10.0
            )

            location_scores.append(min(1.0, loc_score))

        # ---------- SOFT GATE ----------
        if not location_scores:
            page_scores.append(0.0)
            continue

        # ---------- AGGREGATION ----------
        mean_loc = float(np.mean(location_scores))
        loc_count = len(location_scores)

        final_page_score = min(
            1.0,
            mean_loc * (1.0 + 0.6 * math.log1p(loc_count))
        )

        page_scores.append(final_page_score)
        all_location_scores.extend(location_scores)

    if not page_scores:
        return 0.0, []

    return float(round(max(page_scores), 3)), all_location_scores
