import cv2, shutil, os
from ocr.batch_ocr import BatchOCR
from ocr.review_utils import apply_outlier_detection, write_review_csv, summarize_rows, salvage_decimal

CHAINAGE_START = 79980.0
CHAINAGE_STEP = 20.0
N_STATIONS = 250
GROUND_ROW = 7
FORMATION_ROW = 6

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

if os.path.exists('review.csv'):
    shutil.copy('review.csv', 'review.csv.pre_regen_bak')
    print('backed up review.csv -> review.csv.pre_regen_bak')

rows_out = []
for i in range(N_STATIONS):
    chainage = CHAINAGE_START + CHAINAGE_STEP * i
    gl = read(GROUND_ROW, i)
    fl = read(FORMATION_ROW, i)
    rows_out.append([i, chainage, gl, fl, ""])
    if i % 25 == 0:
        print('progress:', i)

depth_flagged, gl_spikes, fl_spikes = apply_outlier_detection(rows_out)
write_review_csv(rows_out, 'review.csv')
summary = summarize_rows(rows_out, depth_flagged, gl_spikes, fl_spikes)
print('\n--- REGEN COMPLETE ---')
print('total stations:', summary['total_stations'])
print('clean prefilled:', summary['clean_prefilled'])
print('needs manual review:', summary['needs_manual_review'])
print('  implausible depth:', summary['implausible_depth_flagged'])
print('  GL spikes:', summary['gl_spikes_flagged'])
print('  FL spikes:', summary['fl_spikes_flagged'])
