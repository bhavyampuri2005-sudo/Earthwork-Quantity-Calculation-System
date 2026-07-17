"""
Export pipeline records to a review CSV for manual correction.
"""

import csv
from ocr.pipeline import OCRPipeline

CHAINAGE_START = 79980
CHAINAGE_STEP = 20
ELEV_MIN, ELEV_MAX = 20, 600


def salvage_decimal(value):
    if value is None:
        return None
    if ELEV_MIN <= value <= ELEV_MAX:
        return value
    digits = str(int(abs(value))) if value == int(value) else str(abs(value)).replace(".", "")
    candidates = []
    for i in range(1, len(digits)):
        try:
            cand = float(digits[:i] + "." + digits[i:])
        except ValueError:
            continue
        if ELEV_MIN <= cand <= ELEV_MAX:
            candidates.append(cand)
    return candidates[0] if len(candidates) == 1 else value


def needs_review(value):
    return value is None or not (ELEV_MIN <= value <= ELEV_MAX)


def export(pdf_path, project_id=1, out_path="review.csv"):
    pipeline = OCRPipeline()
    records = pipeline.process(pdf_path, project_id)

    rows_out = []
    for i, rec in enumerate(records):
        chainage = CHAINAGE_START + CHAINAGE_STEP * i
        gl = salvage_decimal(rec.get("ground_level"))
        fl = salvage_decimal(rec.get("formation_level"))
        review = "YES" if (needs_review(gl) or needs_review(fl)) else ""
        rows_out.append((i, chainage, gl, fl, review))

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "chainage", "ground_level", "formation_level", "needs_review"])
        for i, ch, gl, fl, review in rows_out:
            w.writerow([i, ch, "" if gl is None else gl, "" if fl is None else fl, review])

    flagged = sum(1 for _, _, gl, fl, r in rows_out if r == "YES")
    total = len(rows_out)
    print(f"\nWrote {total} rows to {out_path}")
    print(f"Pre-filled (clean) : {total - flagged}")
    print(f"Needs manual review: {flagged}")


if __name__ == "__main__":
    export("uploads/80-85km (1).pdf", project_id=1, out_path="review.csv")