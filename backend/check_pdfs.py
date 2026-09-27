import glob
import subprocess
from ocr.text_native_extractor import is_text_native, STATION_RE

for path in sorted(glob.glob("uploads/*.pdf")):
    native = is_text_native(path)
    matched = 0
    if native:
        out = subprocess.run(
            ["pdftotext", "-layout", path, "-"],
            capture_output=True, text=True, timeout=60,
        ).stdout
        matched = sum(1 for l in out.splitlines() if STATION_RE.search(l))
    print(f"{path}\n  type={'text_native' if native else 'scanned'}  station_lines={matched}")
