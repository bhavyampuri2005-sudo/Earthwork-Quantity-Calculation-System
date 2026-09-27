import json
from ocr.parser import OCRParser

with open("ocr_results.json") as f:
    ocr = json.load(f)
p = OCRParser()
g = p.group_by_row(ocr)

gl_row, fl_row = g[6], g[7]
cols = sorted(set(gl_row) & set(fl_row))

both = fill = cut = gl_none = fl_none = 0
for c in cols:
    gl = p.clean_value(gl_row.get(c))
    fl = p.clean_value(fl_row.get(c))
    if gl is None: gl_none += 1
    if fl is None: fl_none += 1
    if gl is None or fl is None: continue
    both += 1
    if fl > gl: fill += 1
    elif fl < gl: cut += 1

print(f"cols={len(cols)} both_present={both} | fill(FL>GL)={fill} cut(FL<GL)={cut}")
print(f"GL None={gl_none}  FL None={fl_none}")
print("\nfirst 20 paired:")
for c in cols[:20]:
    print(f"  col {c:<4} GL={p.clean_value(gl_row.get(c))}  FL={p.clean_value(fl_row.get(c))}")
