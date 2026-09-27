p = "routes/upload.py"
src = open(p).read()

old = '''            if not raw_records:
                # FORMAT_A/B either did not match or chainage_start was not
                # supplied -- try FORMAT_C (multi-sheet, chainage read from
                # the PDF text directly, no chainage_start needed).
                raw_records, extract_meta = extract_format_c_records(file_path)'''

new = '''            expected = extract_meta.get("expected_stations", 0)
            matched = extract_meta.get("lines_matched", 0)
            ab_match_ratio = (matched / expected) if expected else 0
            if not raw_records or ab_match_ratio < 0.5:
                # FORMAT_A/B either did not match, matched too sparsely to
                # trust (a real sheet should match the large majority of its
                # own grid; a false-positive match against annotation text
                # or a wrong chainage grid matches only a small fraction),
                # or chainage_start was not supplied -- try FORMAT_C
                # (multi-sheet, chainage read from the PDF text directly,
                # no chainage_start needed).
                raw_records, extract_meta = extract_format_c_records(file_path)'''

if old not in src:
    print("PATTERN NOT FOUND - no change made, paste current file section")
else:
    open(p, "w").write(src.replace(old, new))
    print("patched: A/B fallback now requires >=50% grid match before trusting the result")
