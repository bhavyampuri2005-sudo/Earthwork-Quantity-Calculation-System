"""
Export pipeline records to a review CSV for manual correction.
"""

import csv
from ocr.pipeline import OCRPipeline

CHAINAGE_START = 79980
CHAINAGE_STEP = 20
ELEV_MIN, ELEV_MAX = 20, 600

SPIKE_THRESHOLD = 15.0
SPIKE_NEIGHBOR_WINDOW = 3

GL_FIELD, FL_FIELD = 2, 3


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


def flag_spikes(rows, field_idx, threshold=SPIKE_THRESHOLD, window=SPIKE_NEIGHBOR_WINDOW):
    n = len(rows)
    flagged = 0
    for i in range(n):
        value = rows[i][field_idx]
        if value is None:
            continue

        prev_val = next_val = None
        for j in range(i - 1, max(i - 1 - window, -1), -1):
            v = rows[j][field_idx]
            if v is not None:
                prev_val = v
                break
        for j in range(i + 1, min(i + 1 + window, n)):
            v = rows[j][field_idx]
            if v is not None:
                next_val = v
                break

        if prev_val is None or next_val is None:
            continue

        neighbors_agree = abs(prev_val - next_val) <= threshold
        far_from_neighbors = (
            abs(value - prev_val) > threshold and abs(value - next_val) > threshold
        )

        if neighbors_agree and far_from_neighbors:
            rows[i][field_idx] = None
            rows[i][4] = "YES"
            flagged += 1

    return flagged


def export(pdf_path, project_id=1, out_path="review.csv"):
    pipeline = OCRPipeline()
    records = pipeline.process(pdf_path, project_id)

    rows_out = []
    for i, rec in enumerate(records):
        chainage = CHAINAGE_START + CHAINAGE_STEP * i
        gl = salvage_decimal(rec.get("ground_level"))
        fl = salvage_decimal(rec.get("formation_level"))
        review = "YES" if (needs_review(gl) or needs_review(fl)) else ""
        rows_out.append([i, chainage, gl, fl, review])

    gl_spikes = flag_spikes(rows_out, GL_FIELD)
    fl_spikes = flag_spikes(rows_out, FL_FIELD)

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "chainage", "ground_level", "formation_level", "needs_review"])
        for i, ch, gl, fl, review in rows_out:
            w.writerow([i, ch, "" if gl is None else gl, "" if fl is None else fl, review])

    flagged = sum(1 for row in rows_out if row[4] == "YES")
    total = len(rows_out)
    print(f"\nWrote {total} rows to {out_path}")
    print(f"Pre-filled (clean) : {total - flagged}")
    print(f"Needs manual review: {flagged}")
    print(f"  of which GL spikes newly flagged: {gl_spikes}")
    print(f"  of which FL spikes newly flagged: {fl_spikes}")


if __name__ == "__main__":
    export("uploads/80-85km (1).pdf", project_id=1, out_path="review.csv")
