from ocr.grid_detector import GridDetector
import cv2
import numpy as np

g = GridDetector('uploads/80-85km (1).pdf')
g.load_pdf()
g.crop_lsection()
g.detect_horizontal_lines()

b = g.preprocess()
h = g.lsection.shape[0]
k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, int(h * 0.5))))
vert = cv2.morphologyEx(b, cv2.MORPH_OPEN, k)
cv2.imwrite('uploads/debug_TEST_vertical.png', vert)

cnts, _ = cv2.findContours(vert, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
xs = [cv2.boundingRect(c)[0] for c in cnts
      if cv2.boundingRect(c)[3] > h * 0.5 and cv2.boundingRect(c)[2] < 15]
print('Raw vertical strokes found:', len(cnts))
print('Tall thin strokes kept:', len(xs))
