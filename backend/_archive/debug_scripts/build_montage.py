import cv2
import numpy as np
import os

SRC_DIR = "debug_view"
OUT_PATH = "debug_montage.png"

samples = ["r6_c1", "r6_c2", "r6_c3", "r6_c32", "r6_c45", "r7_c11", "r7_c22"]
stages = ["0_original", "1_rotated", "2_otsu"]

TILE_H = 180
LABEL_H = 30
PAD = 10

tiles = []
row_labels = []

for name in samples:
    row_imgs = []
    for stage in stages:
        path = os.path.join(SRC_DIR, f"{name}_{stage}.png")
        img = cv2.imread(path)
        if img is None:
            img = np.full((TILE_H, TILE_H, 3), 60, dtype=np.uint8)
            cv2.putText(img, "missing", (5, TILE_H // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        else:
            h, w = img.shape[:2]
            scale = TILE_H / h
            img = cv2.resize(img, (int(w * scale), TILE_H))
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        row_imgs.append(img)
    row_labels.append(name)
    tiles.append(row_imgs)

max_w = max(sum(t.shape[1] for t in row) + PAD * (len(row) - 1) for row in tiles)
total_h = sum(TILE_H + LABEL_H + PAD for _ in tiles) + PAD

canvas = np.full((total_h, max_w + 2 * PAD, 3), 30, dtype=np.uint8)

y = PAD
for label, row in zip(row_labels, tiles):
    cv2.putText(canvas, label, (PAD, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    y += LABEL_H
    x = PAD
    for img in row:
        h, w = img.shape[:2]
        canvas[y:y+h, x:x+w] = img
        x += w + PAD
    y += TILE_H + PAD

cv2.imwrite(OUT_PATH, canvas)
print(f"Saved {OUT_PATH}, size: {canvas.shape[1]}x{canvas.shape[0]}")
