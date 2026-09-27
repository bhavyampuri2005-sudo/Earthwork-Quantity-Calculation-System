p = "ocr/review_utils.py"
src = open(p).read()

old = '''    rows_out = []
    for i, rec in enumerate(records):
        chainage = chainage_start + chainage_step * i
        gl = rec.get("ground_level")'''

new = '''    rows_out = []
    for i, rec in enumerate(records):
        chainage = rec.get("field_chainage")
        if chainage is None:
            chainage = chainage_start + chainage_step * i
        gl = rec.get("ground_level")'''

if old not in src:
    print("review_utils.py: PATTERN NOT FOUND - no change (already patched?)")
else:
    open(p, "w").write(src.replace(old, new))
    print("review_utils.py: patched (uses real field_chainage when the extractor supplies it)")
