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

# Same crop you used before
crop = img[
    int(height * 0.62):int(height * 0.90),
    100:3900
]

debug = crop.copy()

# Draw vertical guides every 100 pixels
for x in range(0, crop.shape[1], 100):
    cv2.line(
        debug,
        (x, 0),
        (x, crop.shape[0]),
        (0, 0, 255),
        1
    )

    cv2.putText(
        debug,
        str(x),
        (x, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 0, 0),
        1
    )

cv2.imwrite("major_column_debug.png", debug)

print("Saved major_column_debug.png")