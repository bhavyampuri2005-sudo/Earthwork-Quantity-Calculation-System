from pdf2image import convert_from_path
import cv2
import numpy as np


def merge_close_lines(lines, threshold=10):
    if not lines:
        return []

    lines.sort()

    merged = [lines[0]]

    for y in lines[1:]:
        if abs(y - merged[-1]) > threshold:
            merged.append(y)

    return merged


print("Loading PDF...")

pdf_path = "uploads/80-85km (1).pdf"

# Mentor said don't keep original DPI
images = convert_from_path(
    pdf_path,
    dpi=100
)

img = cv2.cvtColor(
    np.array(images[0]),
    cv2.COLOR_RGB2BGR
)

print("Full Image Shape:", img.shape)

# ==================================================
# STEP 1: Extract L-Section Area
# ==================================================

height = img.shape[0]

# Bottom 35%
lsection = img[int(height * 0.65):, :]

cv2.imwrite("lsection_only.png", lsection)

print("Saved lsection_only.png")
print("L-section Shape:", lsection.shape)

# ==================================================
# STEP 2: Convert to Grayscale
# ==================================================

gray = cv2.cvtColor(
    lsection,
    cv2.COLOR_BGR2GRAY
)

cv2.imwrite("gray.png", gray)

# ==================================================
# STEP 3: Binary Threshold
# ==================================================

binary = cv2.adaptiveThreshold(
    gray,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV,
    15,
    10
)

cv2.imwrite("binary.png", binary)

# ==================================================
# STEP 4: Detect Horizontal Lines
# ==================================================

horizontal_kernel = cv2.getStructuringElement(
    cv2.MORPH_RECT,
    (150, 1)
)

horizontal = cv2.morphologyEx(
    binary,
    cv2.MORPH_OPEN,
    horizontal_kernel
)

cv2.imwrite(
    "horizontal_lines.png",
    horizontal
)

# ==================================================
# STEP 5: Find Horizontal Contours
# ==================================================

contours, _ = cv2.findContours(
    horizontal,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

debug = lsection.copy()

y_positions = []

for cnt in contours:

    x, y, w, h = cv2.boundingRect(cnt)

    # Ignore tiny detections
    if w > 200:

        y_positions.append(y)

        cv2.rectangle(
            debug,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

# ==================================================
# STEP 6: Merge Duplicate Rows
# ==================================================

y_positions = merge_close_lines(
    y_positions,
    threshold=10
)

# ==================================================
# STEP 7: Draw Row Numbers
# ==================================================

for y in y_positions:

    cv2.putText(
        debug,
        str(y),
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 255),
        3
    )

# ==================================================
# STEP 8: Save Debug Image
# ==================================================

cv2.imwrite(
    "horizontal_debug.png",
    debug
)

print("\nMerged Rows:")
print(y_positions)

print("\nTotal Rows:", len(y_positions))

print("\nDone.")