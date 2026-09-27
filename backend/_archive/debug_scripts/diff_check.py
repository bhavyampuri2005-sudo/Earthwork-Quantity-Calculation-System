import csv
from earthwork.calc_engine import load_stations

stations = load_stations('review.csv')

with open('review.csv') as f:
    reader = csv.DictReader(f)
    csv_rows = {float(r['chainage']): r for r in reader}

mismatches = []
for s in stations:
    ch = s['chainage']
    if not s['complete']:
        raw = csv_rows.get(ch, {})
        gl_raw = (raw.get('ground_level') or '').strip()
        fl_raw = (raw.get('formation_level') or '').strip()
        if gl_raw and fl_raw:
            mismatches.append((ch, gl_raw, fl_raw))

print('mismatch count:', len(mismatches))
for ch, gl, fl in mismatches:
    print(ch, gl, fl)
