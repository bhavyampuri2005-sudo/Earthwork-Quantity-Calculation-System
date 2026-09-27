from ocr.grid_detector import GridDetector
import cv2
import numpy as np

g = GridDetector('uploads/80-85km (1).pdf')
g.load_pdf()
g.crop_lsection()
g.detect_horizontal_lines()
b = g.preprocess()  # white ink on black, inverted binary

# Look only at the GL/FL vertical span so we measure data-row ink,
# not header/label rows. Rows detected: use the band around row 6/7.
# From your detected rows, GL/FL sit in the lower-middle of the crop.
rows = g.rows
print("Detected row y-positions:", rows)

# Sum ink vertically across the full height to get an ink-per-column profile
col_profile = b.sum(axis=0).astype(float)

# Focus on the first km: x=240..950
seg = col_profile[240:950]

# Smooth lightly so each printed number becomes one bump
kernel = np.ones(9) / 9
smooth = np.convolve(seg, kernel, mode='same')

# Find peaks = centers of printed numbers
peaks = []
for i in range(2, len(smooth) - 2):
    if smooth[i] > smooth[i-1] and smooth[i] >= smooth[i+1] and smooth[i] > smooth.mean():
        peaks.append(i + 240)

# Merge peaks closer than 8px (same number)
merged = []
for p in peaks:
    if not merged or p - merged[-1] > 8:
        merged.append(p)

print(f"Ink-column centers found in km 80-81: {len(merged)}")
print("Positions:", merged)
if len(merged) > 1:
    gaps = [merged[i+1] - merged[i] for i in range(len(merged)-1)]
    print("Gaps between centers:", gaps)
    print("Median gap (px):", int(np.median(gaps)))
    print("Implied columns per km:", round(710 / np.median(gaps), 1))
