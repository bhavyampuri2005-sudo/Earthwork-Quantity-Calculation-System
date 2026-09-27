from pdf2image import convert_from_path
import cv2
import numpy as np

print("Loading PDF...")

images = convert_from_path(
    "uploads/80-85km (1).pdf",
    dpi=100
)

img = cv2.cvtColor(
    np.array(images[0]),
    cv2.COLOR_RGB2BGR
)

height, width = img.shape[:2]

# Same crop used before
crop = img[
    int(height * 0.62):int(height * 0.90),
    100:3900
]

debug = crop.copy()

# Major chainage positions
major_cols = [
    240,   # 80 km
    950,   # 81 km
    1660,  # 82 km
    2370,  # 83 km
    3080,  # 84 km
    3790   # 85 km
]

# Draw major chainage lines
for x in major_cols:
    cv2.line(
        debug,
        (x, 0),
        (x, debug.shape[0]),
        (255, 0, 0),
        3
    )

# Generate 20m columns
cols = []

for i in range(len(major_cols) - 1):

    start = major_cols[i]
    end = major_cols[i + 1]

    step = (end - start) / 50

    for j in range(50):
        cols.append(int(start + j * step))

cols.append(major_cols[-1])

# Draw 20m columns
for x in cols:
    cv2.line(
        debug,
        (x, 0),
        (x, debug.shape[0]),
        (0, 255, 0),
        1
    )

cv2.imwrite("20m_debug.png", debug)

print("Columns generated:", len(cols))
print("Saved: 20m_debug.png")