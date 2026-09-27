from pdf2image import convert_from_path
import cv2
import numpy as np

print("Loading PDF...")

pdf_path = "uploads/80-85km (1).pdf"

# Reduced DPI as instructed by mentor
images = convert_from_path(
    pdf_path,
    dpi=100
)

img = cv2.cvtColor(
    np.array(images[0]),
    cv2.COLOR_RGB2BGR
)

print("Full Image Shape:", img.shape)

height = img.shape[0]

# ==========================================
# UPDATED CROP
# Include vertical geometry area
# ==========================================

lsection = img[
    int(height * 0.62):int(height * 0.94),
    100:3900
]

cv2.imwrite("vertical_crop.png", lsection)

print("Crop Shape:", lsection.shape)

# ==========================================
# GRAYSCALE
# ==========================================

gray = cv2.cvtColor(
    lsection,
    cv2.COLOR_BGR2GRAY
)

# ==========================================
# THRESHOLD
# ==========================================

binary = cv2.adaptiveThreshold(
    gray,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV,
    15,
    10
)

cv2.imwrite("vertical_binary.png", binary)

# ==========================================
# DETECT VERTICAL LINES
# ==========================================

vertical_kernel = cv2.getStructuringElement(
    cv2.MORPH_RECT,
    (1, 40)
)

vertical = cv2.morphologyEx(
    binary,
    cv2.MORPH_OPEN,
    vertical_kernel
)

cv2.imwrite(
    "vertical_lines.png",
    vertical
)

# ==========================================
# FIND CONTOURS
# ==========================================

contours, _ = cv2.findContours(
    vertical,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

debug = lsection.copy()

x_positions = []

for cnt in contours:

    x, y, w, h = cv2.boundingRect(cnt)

    # keep reasonably tall vertical structures
    if h > 50:

        x_positions.append(x)

        cv2.rectangle(
            debug,
            (x, y),
            (x + w, y + h),
            (255, 0, 0),
            2
        )

x_positions.sort()

print("\nRaw Vertical Lines:")
print(x_positions)

print("\nRaw Count:", len(x_positions))

# ==========================================
# MERGE NEARBY LINES
# ==========================================

merged = []

for x in x_positions:

    if not merged:
        merged.append(x)

    elif abs(x - merged[-1]) > 5:
        merged.append(x)

print("\nMerged Vertical Lines:")
print(merged)

print("\nMerged Count:", len(merged))

# ==========================================
# DRAW LABELS
# ==========================================

for x in merged:

    cv2.line(
        debug,
        (x, 0),
        (x, debug.shape[0]),
        (0, 255, 0),
        2
    )

    cv2.putText(
        debug,
        str(x),
        (x, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (0, 0, 255),
        1
    )

cv2.imwrite(
    "vertical_debug.png",
    debug
)

print("\nDone.")