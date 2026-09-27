import json
from ocr.parser import OCRParser

with open("ocr_results.json", "r") as f:
    ocr_results = json.load(f)

parser = OCRParser()
grouped_rows = parser.group_by_row(ocr_results)

chain_cols = set(grouped_rows.get(9, {}))
for name, idx in [("cut_fill", 5), ("ground_level", 6), ("formation_level", 7), ("rail_level", 8)]:
    cols = set(grouped_rows.get(idx, {}))
    print(f"{name:<16} (row {idx}): {len(cols)} cols | "
          f"in {name} not chainage: {len(cols - chain_cols)} | "
          f"in chainage not {name}: {len(chain_cols - cols)}")

print("\nRaw values, rows 4-10, first 15 shared columns:")
rows_to_check = [4, 5, 6, 7, 8, 9, 10]
common = sorted(set.intersection(*(set(grouped_rows[r]) for r in rows_to_check)))[:15]
print(f"{'col':<6}" + "".join(f"row{r:<10}" for r in rows_to_check))
for c in common:
    vals = [str(grouped_rows[r].get(c)) for r in rows_to_check]
    print(f"{c:<6}" + "".join(f"{v:<13}" for v in vals))
