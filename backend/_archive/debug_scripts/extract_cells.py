import cv2
import numpy as np
from pdf2image import convert_from_path
import os

print("Loading PDF...")

pdf_path = "uploads/80-85km (1).pdf"

images = convert_from_path(
    pdf_path,
    dpi=100
)

img = cv2.cvtColor(
    np.array(images[0]),
    cv2.COLOR_RGB2BGR
)

height = img.shape[0]

# Same crop as verify_20m_columns.py
crop = img[
    int(height * 0.62):int(height * 0.90),
    100:3900
]

print("Crop Shape:", crop.shape)

rows = [
    123,170,202,232,255,266,290,
    340,386,418,438,454,512,
    532,590,606,626,658,725,
    805,862
]

major_cols = [
    240,
    950,
    1660,
    2370,
    3080,
    3790
]

# Generate 20m columns
all_cols = []

for i in range(len(major_cols) - 1):

    start = major_cols[i]
    end = major_cols[i + 1]

    step = (end - start) / 50

    for j in range(50):
        all_cols.append(
            int(start + j * step)
        )

# Only append if different
if all_cols[-1] != major_cols[-1]:
    all_cols.append(
        major_cols[-1]
    )

print("Rows:", len(rows))
print("Columns:", len(all_cols))

os.makedirs(
    "cells",
    exist_ok=True
)

count = 0
empty_count = 0

for r in range(len(rows) - 1):

    y1 = rows[r]
    y2 = rows[r + 1]

    for c in range(len(all_cols) - 1):

        x1 = all_cols[c]
        x2 = all_cols[c + 1]

        # Skip invalid cells
        if x2 <= x1:
            empty_count += 1
            continue

        if y2 <= y1:
            empty_count += 1
            continue

        cell = crop[y1:y2, x1:x2]

        if cell.size == 0:
            empty_count += 1
            continue

        cv2.imwrite(
            f"cells/r{r}_c{c}.png",
            cell
        )

        count += 1

print("\nCells Saved:", count)
print("Empty Cells Skipped:", empty_count)
print("Done.")