import cv2, os, csv
from ocr.batch_ocr import BatchOCR
from ocr.review_utils import salvage_decimal

CHAINAGE_START = 79980.0
CHAINAGE_STEP = 20.0
N_STATIONS = 250
GROUND_ROW = 7
FORMATION_ROW = 6
MAX_DEPTH = 20.0

b = BatchOCR(cells_dir='cells_fresh')

def read(row, col):
    p = f'cells_fresh/r{row}_c{col}.png'
    if not os.path.exists(p):
        return None
    img = cv2.imread(p)
    if img is None:
        return None
    v = b.read_with_offset_search(img)
    if not v or '.' not in v:
        return None
    try:
        num = float(v.rstrip('-'))
    except ValueError:
        return None
    return salvage_decimal(num)

rows = []
for i in range(N_STATIONS):
    chainage = CHAINAGE_START + CHAINAGE_STEP * i
    gl = read(GROUND_ROW, i)
    fl = read(FORMATION_ROW, i)
    rows.append((i, chainage, gl, fl))
    if i % 25 == 0:
        print('progress:', i)

with open('raw_gl_fl_dump.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['col', 'chainage', 'gl', 'fl', 'depth'])
    for i, ch, gl, fl in rows:
        depth = abs(gl - fl) if (gl is not None and fl is not None) else None
        w.writerow([i, ch, gl, fl, depth])

print('\n--- IMPLAUSIBLE DEPTH ROWS (>20m) ---')
count = 0
for i, ch, gl, fl in rows:
    if gl is not None and fl is not None and abs(gl - fl) > MAX_DEPTH:
        count += 1
        print(f'col={i} chainage={ch} gl={gl} fl={fl} depth={abs(gl-fl):.2f}')
print('\ntotal implausible:', count)
