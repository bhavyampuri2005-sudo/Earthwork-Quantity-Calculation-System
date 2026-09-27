import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)

for r in [5, 6, 7, 8, 9]:
    cells = g.get(r, {})
    vals = [p.clean_value(v) for v in cells.values()]
    good = [v for v in vals if v is not None]
    # "elevation-shaped" = 3 digits before decimal, in 300-400 range
    elev = [v for v in good if 300 <= v <= 400]
    print(f"row {r}: {len(cells)} cells | non-null {len(good)} | elevation-shaped(300-400) {len(elev)}")
    # show a sample of raw strings to see what OCR actually returned
    raw_sample = list(cells.values())[:12]
    print(f"   raw: {raw_sample}")
