import re

p = "ocr/review_utils.py"
src = open(p).read()

old = '''def build_review_rows(records, chainage_start, chainage_step=20):
    rows_out = []
    for i, rec in enumerate(records):
        chainage = chainage_start + chainage_step * i
        gl = salvage_decimal(rec.get("ground_level"))
        fl = salvage_decimal(rec.get("formation_level"))
        review = "YES" if (needs_review(gl) or needs_review(fl)) else ""
        rows_out.append([i, chainage, gl, fl, review])
    return rows_out'''

new = '''TEXT_NATIVE_ELEV_MIN, TEXT_NATIVE_ELEV_MAX = -100.0, 5000.0


def build_review_rows(records, chainage_start, chainage_step=20, text_native=False):
    """
    text_native=True skips salvage_decimal entirely. That helper repairs
    misread decimal points from OCR; on a CAD text layer the decimal is
    exact, so "repairing" it only corrupts values (799.438 -> 79.9438 for
    any corridor above the 600m ELEV_MAX ceiling).
    """
    lo, hi = (TEXT_NATIVE_ELEV_MIN, TEXT_NATIVE_ELEV_MAX) if text_native else (ELEV_MIN, ELEV_MAX)

    def _bad(v):
        return v is None or not (lo <= v <= hi)

    rows_out = []
    for i, rec in enumerate(records):
        chainage = chainage_start + chainage_step * i
        gl = rec.get("ground_level")
        fl = rec.get("formation_level")
        if not text_native:
            gl = salvage_decimal(gl)
            fl = salvage_decimal(fl)
        review = "YES" if (_bad(gl) or _bad(fl)) else ""
        rows_out.append([i, chainage, gl, fl, review])
    return rows_out'''

if old not in src:
    print("review_utils.py: PATTERN NOT FOUND - no changes made")
else:
    open(p, "w").write(src.replace(old, new))
    print("review_utils.py: patched")

p2 = "routes/upload.py"
src2 = open(p2).read()
old2 = "rows_out = build_review_rows(records, chainage_start, chainage_step)"
new2 = ('rows_out = build_review_rows(\n'
        '        records, chainage_start, chainage_step,\n'
        '        text_native=(route_used == "text_native"),\n'
        '    )')
if old2 not in src2:
    print("upload.py: PATTERN NOT FOUND - no changes made")
else:
    open(p2, "w").write(src2.replace(old2, new2))
    print("upload.py: patched")
