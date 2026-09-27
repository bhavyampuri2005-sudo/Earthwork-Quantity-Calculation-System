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

h = img.shape[0]

# Same crop as vertical detection
lsection = img[
    int(h * 0.78):int(h * 0.94),
    100:3900
]

print("Crop shape:", lsection.shape)

# Save original crop
cv2.imwrite(
    "chainage_inspect.png",
    lsection
)

# Save enlarged version
zoom = cv2.resize(
    lsection,
    None,
    fx=3,
    fy=3,
    interpolation=cv2.INTER_CUBIC
)

cv2.imwrite(
    "chainage_zoom.png",
    zoom
)

print("Saved:")
print("chainage_inspect.png")
print("chainage_zoom.png")