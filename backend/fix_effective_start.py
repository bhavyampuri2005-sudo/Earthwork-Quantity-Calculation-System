p = "routes/upload.py"
src = open(p).read()

old = '''    rows_out = build_review_rows(
        records, chainage_start, chainage_step,
        text_native=(route_used == "text_native"),
    )'''

new = '''    effective_start = chainage_start if chainage_start is not None else records[0]["field_chainage"]
    rows_out = build_review_rows(
        records, effective_start, chainage_step,
        text_native=(route_used == "text_native"),
    )'''

if old not in src:
    print("PATTERN NOT FOUND - no change made, paste current file")
else:
    open(p, "w").write(src.replace(old, new))
    print("patched: effective_start added")
