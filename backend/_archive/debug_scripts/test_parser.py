from ocr.parser import OCRParser

parser = OCRParser()

ocr = {

    "r7_c0.png":"3.515",
    "r7_c1.png":"3.612",

    "r8_c0.png":"376.950",
    "r8_c1.png":"376.960",

    "r9_c0.png":"375.973",
    "r9_c1.png":"375.980",

    "r10_c0.png":"372.458",
    "r10_c1.png":"372.462",

    "r11_c0.png":"80320",
    "r11_c1.png":"80340"

}

rows = parser.group_by_row(ocr)

mapping = parser.assign_engineering_rows(rows)

records = parser.build_records(
    rows,
    mapping
)

for record in records:
    print(record)