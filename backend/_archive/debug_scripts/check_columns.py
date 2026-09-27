import cv2

img = cv2.imread("20m_debug.png")

# zoom into center region
crop = img[250:700, 700:1500]

cv2.imwrite("column_zoom.png", crop)

print("Saved column_zoom.png")