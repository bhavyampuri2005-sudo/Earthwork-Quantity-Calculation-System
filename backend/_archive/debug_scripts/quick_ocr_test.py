import os
import re
import cv2
import json
import time

from ocr.ocr_engine import OCREngine

# Only test these rows while iterating. Add more (e.g. 5, 8) once
# GL/FL are settled and you want to sanity-check cut_fill/RL too.
ROWS_TO_TEST = [6, 7]

CELLS_DIR = "cells"
OUTPUT_PATH = "ocr_results_subset.json"


def cell_key(filename):
    m = re.match(r"r(\d+)_c(\d+)", filename)
    if not m:
        return (float("inf"), float("inf"))
    r, c = m.groups()
    return int(r), int(c)


def main():
    engine = OCREngine()

    files = [
        f for f in os.listdir(CELLS_DIR)
        if f.endswith(".png") and cell_key(f)[0] in ROWS_TO_TEST
    ]
    files.sort(key=cell_key)

    print(f"Testing rows {ROWS_TO_TEST}: {len(files)} cells\n")

    results = {}
    start = time.time()

    for i, filename in enumerate(files, 1):
        path = os.path.join(CELLS_DIR, filename)
        img = cv2.imread(path)
        if img is None:
            print(f"Could not read {filename}")
            continue
        text = engine.read_cell(img)
        results[filename] = text
        if i % 50 == 0:
            print(f"  {i}/{len(files)} done...")

    elapsed = time.time() - start

    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=4)

    print(f"\nDone in {elapsed:.1f}s. Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
