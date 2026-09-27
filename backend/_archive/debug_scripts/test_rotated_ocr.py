import cv2
import easyocr

reader = easyocr.Reader(['en'], gpu=False)

img = cv2.imread("row_16.png")

# Rotate 90 degrees clockwise
rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

cv2.imwrite("row16_rotated.png", rotated)

result = reader.readtext(
    rotated,
    detail=0,
    paragraph=False
)

print("\nOCR Results:")
print(result[:100])
