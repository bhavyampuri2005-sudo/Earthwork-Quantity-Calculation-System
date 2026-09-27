import json
from ocr.parser import OCRParser

with open("ocr_results.json", "r") as f:
    ocr_results = json.load(f)

parser = OCRParser()

grouped_rows = parser.group_by_row(ocr_results)

print("Detected Rows:", sorted(grouped_rows.keys()))

print("\n" + "=" * 60)
print("ALL ROW STATS (raw, not just rows 5-9)")
print("=" * 60)
for row_idx in sorted(grouped_rows.keys()):
    cells = grouped_rows[row_idx]
    st = parser._row_stats(cells)
    nums = sorted(v for v in (parser.clean_value(cells[c]) for c in cells) if v is not None)
    spread = round(nums[-1] - nums[0], 2) if nums else None
    print(f"  row {row_idx:<4} count={st['count']:<4} median={st['median']} spread={spread} mono={st['mono']}")
print("=" * 60 + "\n")

parser.assign_engineering_rows(grouped_rows)
