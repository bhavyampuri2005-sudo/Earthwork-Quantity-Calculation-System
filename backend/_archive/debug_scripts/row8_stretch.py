import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)

row8 = g[8]
cols = sorted(row8.keys())[:40]
for c in cols:
    raw = row8.get(c)
    cleaned = p.clean_value(raw)
    ok = "OK" if cleaned is not None and 360 <= cleaned <= 370 else ""
    print(f"col {c:<4} raw={str(raw):<15} cleaned={str(cleaned):<12} {ok}")
