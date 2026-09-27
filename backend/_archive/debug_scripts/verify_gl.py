import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)

def band_frac(row, lo, hi):
    vals = [p.clean_value(v) for v in row.values()]
    vals = [v for v in vals if v is not None]
    if not vals:
        return (0, 0.0)
    hits = sum(1 for v in vals if lo <= v <= hi)
    return (hits, round(hits / len(vals), 2))

print("row 6 in 373.8-374.5 (formation):", band_frac(g[6], 373.8, 374.5))
print("row 7 in 372.8-373.6 (rail):     ", band_frac(g[7], 372.8, 373.6))
print("row 8 in 363-366 (GROUND ~365):  ", band_frac(g[8], 363.0, 366.0))
