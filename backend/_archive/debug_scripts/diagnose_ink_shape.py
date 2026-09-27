import cv2
import numpy as np
import glob

CELLS_DIR = "cells"

def find_crop(row, col):
    matches = glob.glob(f"{CELLS_DIR}/r{row}_c{col}.png")
    return matches[0] if matches else None

def ink_stats(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    # Use Otsu instead of a fixed threshold - calibrates per-image
    # since these crops aren't at fixed absolute brightness.
    _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mask = (mask > 0).astype(np.uint8)
    ink_pct = round(100 * mask.sum() / img.size, 1)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n_labels <= 1:
        largest_area, largest_h = 0, 0
    else:
        areas = stats[1:, cv2.CC_STAT_AREA]
        idx = int(np.argmax(areas)) + 1
        largest_area = int(stats[idx, cv2.CC_STAT_AREA])
        largest_h = int(stats[idx, cv2.CC_STAT_HEIGHT])

    return {"ink_pct": ink_pct, "largest_blob_area": largest_area, "largest_blob_height": largest_h}

empty_cols = [12,13,14,15,16,17,18,19,20,21,34,35,36,37,38]
good_cols = [1,2,3,7,9,10]

for row in (6, 7):
    print(f"\n--- row {row} ---")
    for col in empty_cols + good_cols:
        path = find_crop(row, col)
        label = "EMPTY-BUCKET" if col in empty_cols else "known-good"
        if path is None:
            print(f"  col {col:>3} [{label}]: NO FILE")
            continue
        print(f"  col {col:>3} [{label}]: {ink_stats(path)}")
