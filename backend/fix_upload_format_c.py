p = "routes/upload.py"
src = open(p).read()
changes = []

# 1. Import extract_format_c_records
old1 = "from ocr.text_native_extractor import is_text_native, extract_text_native_records"
new1 = "from ocr.text_native_extractor import is_text_native, extract_text_native_records, extract_format_c_records"
if old1 in src:
    src = src.replace(old1, new1)
    changes.append("import updated")

# 2. Make chainage_start optional
old2 = "    chainage_start: float = Form(...),"
new2 = "    chainage_start: float = Form(None),"
if old2 in src:
    src = src.replace(old2, new2)
    changes.append("chainage_start made optional")

# 3. Try A/B, fall back to FORMAT_C, with OCR-path guard
old3 = '''        if route_used == "text_native":
            raw_records, extract_meta = extract_text_native_records(
                file_path, chainage_start, chainage_step
            )
            records = [
                {
                    "field_chainage": r["field_chainage"],
                    "ground_level": r["ground_level"],
                    "formation_level": r["formation_level"],
                    "rail_level": r["rail_level"],
                    "cut_fill": r["cut_fill"],
                }
                for r in raw_records
            ]
        else:
            pipeline = OCRPipeline()
            records = pipeline.process(file_path, project_id)'''

new3 = '''        if route_used == "text_native":
            if chainage_start is not None:
                raw_records, extract_meta = extract_text_native_records(
                    file_path, chainage_start, chainage_step
                )
            else:
                raw_records, extract_meta = [], {}

            if not raw_records:
                # FORMAT_A/B either did not match or chainage_start was not
                # supplied -- try FORMAT_C (multi-sheet, chainage read from
                # the PDF text directly, no chainage_start needed).
                raw_records, extract_meta = extract_format_c_records(file_path)

            records = [
                {
                    "field_chainage": r["field_chainage"],
                    "ground_level": r["ground_level"],
                    "formation_level": r["formation_level"],
                    "rail_level": r.get("rail_level"),
                    "cut_fill": r["cut_fill"],
                }
                for r in raw_records
            ]
        else:
            if chainage_start is None:
                raise HTTPException(
                    status_code=422,
                    detail="chainage_start is required for scanned (OCR) uploads.",
                )
            pipeline = OCRPipeline()
            records = pipeline.process(file_path, project_id)'''

if old3 in src:
    src = src.replace(old3, new3)
    changes.append("extraction logic updated with FORMAT_C fallback")

# 4. Use real chainage for the CSV instead of assuming chainage_start is set
old4 = '''    rows_out = build_review_rows(records, chainage_start, chainage_step)'''
new4 = '''    effective_start = chainage_start if chainage_start is not None else records[0]["field_chainage"]
    rows_out = build_review_rows(
        records, effective_start, chainage_step,
        text_native=(route_used == "text_native"),
    )'''
if old4 in src:
    src = src.replace(old4, new4)
    changes.append("build_review_rows call updated")
else:
    print("WARNING: pattern 4 not found - your build_review_rows call may already pass text_native. Checking...")

# 5. Fix summary fields to use effective_start
old5 = '''    summary["chainage_start"] = chainage_start
    summary["chainage_step"] = chainage_step
    summary["chainage_end"] = chainage_start + chainage_step * (len(records) - 1)'''
new5 = '''    is_format_c = extract_meta.get("format_detected") == "C"
    summary["chainage_start"] = effective_start
    summary["chainage_step"] = chainage_step
    summary["chainage_end"] = (
        records[-1]["field_chainage"] if is_format_c
        else effective_start + chainage_step * (len(records) - 1)
    )'''
if old5 in src:
    src = src.replace(old5, new5)
    changes.append("summary chainage fields updated")

open(p, "w").write(src)
print("Applied:", changes)
print("Total changes:", len(changes), "(expect 5)")
