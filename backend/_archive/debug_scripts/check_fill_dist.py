import json
from ocr.parser import OCRParser
from ocr.record_mapper import RecordMapper

with open("ocr_results.json") as f:
    ocr = json.load(f)

parser = OCRParser()
mapper = RecordMapper()

grouped = parser.group_by_row(ocr)
mapping = parser.assign_engineering_rows(grouped)
records = parser.build_records(grouped, mapping)

fills, cuts = [], []
for rec in records:
    if None in (rec["ground_level"], rec["formation_level"], rec["cut_fill"]):
        continue
    db = mapper.map_record(rec, project_id=0)
    if db["fill"] > 0:
        fills.append((rec["chainage"], db["fill"]))
    elif db["cut"] > 0:
        cuts.append((rec["chainage"], db["cut"]))

fills.sort(key=lambda x: -x[1])
print("Top 10 fill (chainage, value):")
for c, f in fills[:10]:
    print(f"  {c}: {f}")

print(f"\nfill median: {sorted(v for _,v in fills)[len(fills)//2]}")
print(f"cut median:  {sorted(v for _,v in cuts)[len(cuts)//2]}")
