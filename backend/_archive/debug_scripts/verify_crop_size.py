import cv2

samples = ["r6_c1", "r6_c2", "r6_c32", "r7_c11"]
for name in samples:
    img = cv2.imread(f"cells/{name}.png")
    if img is None:
        print(f"{name}: MISSING")
        continue
    h, w = img.shape[:2]
    print(f"{name}: width={w}px height={h}px")
