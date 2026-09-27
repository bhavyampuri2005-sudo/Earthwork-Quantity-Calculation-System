import cv2
import glob

CELLS_DIR = "cells"  # <-- update after you confirm the real path

def find_crop(row, col):
    matches = glob.glob(f"{CELLS_DIR}/r{row}_c{col}.png")
    return matches[0] if matches else None

def stats(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    return {
        "shape": img.shape,
        "mean": round(float(img.mean()), 1),
        "std": round(float(img.std()), 1),
        "min": int(img.min()),
        "max": int(img.max()),
    }

empty_cols = [12,13,14,15,16,17,18,19,20,21,34,35,36,37,38]
good_cols = [1,2,3,7,9,10]

for row in (6, 7):
    print(f"\n--- row {row} ---")
    for col in empty_cols + good_cols:
        path = find_crop(row, col)
        label = "EMPTY-BUCKET" if col in empty_cols else "known-good"
        if path is None:
            print(f"  col {col:>3} [{label}]: NO FILE FOUND")
            continue
        print(f"  col {col:>3} [{label}]: {stats(path)}")
