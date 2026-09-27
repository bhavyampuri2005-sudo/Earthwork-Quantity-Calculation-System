import os
import cv2
from ocr.ocr_engine import OCREngine

engine = OCREngine()
os.makedirs("debug_view", exist_ok=True)

samples = ["r6_c1", "r6_c2", "r6_c3", "r6_c32", "r6_c45", "r7_c11", "r7_c22"]

for name in samples:
    path = f"cells/{name}.png"
    img = cv2.imread(path)
    if img is None:
        print(f"missing {path}")
        continue
    processed = engine.preprocess(img)
    cw = engine.rotate_clockwise(processed)
    cv2.imwrite(f"debug_view/{name}_0_original.png", img)
    cv2.imwrite(f"debug_view/{name}_1_rotated.png", cw)
    _, otsu = cv2.threshold(cw, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(f"debug_view/{name}_2_otsu.png", otsu)

print("Saved to debug_view/")
