import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)

row6 = g[6]
trailing = sum(1 for v in row6.values() if str(v).rstrip().endswith("-"))
leading  = sum(1 for v in row6.values() if str(v).strip().startswith("-"))
print(f"row6: {len(row6)} cells | trailing-minus: {trailing} | leading-minus: {leading}")
