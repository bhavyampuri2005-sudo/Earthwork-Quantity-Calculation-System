import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)
gl_row, fl_row = g[6], g[7]
cols = sorted(set(gl_row) & set(fl_row))

def in_band(v, lo, hi):
    return v is not None and lo <= v <= hi

# how often does GL[c] sit in true-GL band (374-375) vs FL[c] in FL band (372-374)
for shift in (-1, 0, 1):
    hits = 0; checked = 0
    for c in cols:
        gl = p.clean_value(gl_row.get(c))
        fl = p.clean_value(fl_row.get(c + shift))
        if in_band(gl, 373.5, 375) and in_band(fl, 371, 373.5):
            hits += 1
        if gl is not None:
            checked += 1
    print(f"shift {shift:+d}: GL>FL-with-shift valid pairs = {hits}")
