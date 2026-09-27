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

fill_count = cut_count = skipped = 0
fill_sum = 0.0
for rec in records:
    if rec["ground_level"] is None or rec["formation_level"] is None or rec["cut_fill"] is None:
        skipped += 1
        continue
    db = mapper.map_record(rec, project_id=0)
    if db["fill"] > 0:
        fill_count += 1
        fill_sum += db["fill"]
    elif db["cut"] > 0:
        cut_count += 1

print(f"records={len(records)} skipped={skipped} fill={fill_count} cut={cut_count}")
if fill_count:
    print(f"avg fill (where >0): {round(fill_sum/fill_count, 3)}")
