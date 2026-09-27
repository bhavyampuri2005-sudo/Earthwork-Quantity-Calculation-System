import cv2
import pytesseract

img = cv2.imread("cells/r15_c50.png")

rotated = cv2.rotate(
    img,
    cv2.ROTATE_90_CLOCKWISE
)

cv2.imwrite(
    "rotated_test.png",
    rotated
)

text = pytesseract.image_to_string(
    rotated,
    config="--psm 7 -c tessedit_char_whitelist=0123456789.-"
)

print("OCR:", text)