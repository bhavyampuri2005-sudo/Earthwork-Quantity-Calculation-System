import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)

truth = {0: 365.911, 1: 365.755, 2: 365.569, 3: 365.362, 4: 365.131, 5: 364.967}

print(f"{'col':<5}{'chainage':<10}{'truth GL':<10}{'raw OCR':<20}{'cleaned':<10}")
for col, gl in truth.items():
    raw = g[8].get(col)
    cleaned = p.clean_value(raw)
    print(f"{col:<5}{79980+20*col:<10}{gl:<10}{str(raw):<20}{str(cleaned):<10}")
