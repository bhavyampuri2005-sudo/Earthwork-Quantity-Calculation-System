p = "earthwork/calc_engine.py"
src = open(p).read()
old = "ELEV_MIN, ELEV_MAX = 20, 600  # plausible GL/FL range - guards against unreviewed OCR garbage"
new = ("ELEV_MIN, ELEV_MAX = -100.0, 5000.0  # plausible GL/FL range; matches the band\n"
       "# text_native_extractor already validates against. The old 20-600 ceiling silently\n"
       "# nulled every station on corridors above 600m (the KM10-25 stretch sits at ~800m).")
if old not in src:
    print("NOT FOUND - no change")
else:
    open(p, "w").write(src.replace(old, new))
    print("calc_engine.py: patched")
