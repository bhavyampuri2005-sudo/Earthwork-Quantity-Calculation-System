import csv

stale_chainages = [80040.0, 80120.0, 80160.0, 80500.0, 80520.0, 80640.0, 80960.0,
                    80980.0, 81360.0, 81420.0, 81440.0, 81460.0, 81880.0, 81920.0,
                    82280.0, 82360.0, 82400.0, 83200.0, 83220.0, 83500.0, 83560.0,
                    83580.0, 83600.0, 83640.0, 83960.0, 84420.0, 84820.0]

with open('raw_gl_fl_dump.csv') as f:
    rows = {float(r['chainage']): r for r in csv.DictReader(f)}

for ch in stale_chainages:
    r = rows.get(ch)
    if r:
        print(ch, 'raw_gl=', r['gl'] or 'NONE', 'raw_fl=', r['fl'] or 'NONE')
