import json
from ocr.parser import OCRParser
from ocr.review_utils import salvage_cut_fill

with open("ocr_results.json") as f:
    ocr = json.load(f)

parser = OCRParser()
grouped = parser.group_by_row(ocr)
mapping = parser.assign_engineering_rows(grouped)

gl_row = grouped[mapping["ground_level"]]
fl_row = grouped[mapping["formation_level"]]
cf_row = grouped[mapping["cut_fill"]]

fixed = unresolved = 0
for col in sorted(cf_row.keys()):
    gl = parser.clean_value(gl_row.get(col))
    fl = parser.clean_value(fl_row.get(col))
    cf = parser.clean_value(cf_row.get(col))
    if gl is None or fl is None or cf is None:
        continue
    expected = round(fl - gl, 3)
    if abs(expected - cf) <= 0.05:
        continue
    salvaged = salvage_cut_fill(cf, expected, tolerance=0.05)
    ok = abs(expected - salvaged) <= 0.05
    fixed += ok
    unresolved += not ok
    print(f"col {col:<4} raw_cf={cf:<12} expected={expected:<10} salvaged={salvaged:<10} {'FIXED' if ok else 'unresolved'}")

print(f"\nfixed={fixed} unresolved={unresolved}")
