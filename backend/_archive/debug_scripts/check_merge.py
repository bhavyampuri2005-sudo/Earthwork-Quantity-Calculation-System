import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)

cf_row = g[4]  # cut_fill
large = recoverable = 0
for col in sorted(cf_row.keys()):
    raw = cf_row[col]
    val = p.clean_value(raw)
    if val is None or abs(val) <= 50:
        continue
    large += 1
    scaled = val / 1000
    tag = "RECOVERABLE" if 0.5 <= abs(scaled) <= 50 else ""
    if tag:
        recoverable += 1
    print(f"col {col:<4} raw={raw!r:<15} cleaned={val:<12} /1000={round(scaled,3):<10} {tag}")

print(f"\nlarge={large} recoverable={recoverable}")
