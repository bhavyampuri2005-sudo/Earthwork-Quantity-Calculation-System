"""
Shared OCR-review utilities: decimal salvage, valid-range checking, and
neighbor-outlier ("spike") detection for suspect GL/FL readings.

Used by BOTH export_review_csv.py (CLI, calibrated for the 80-85km
section) and routes/upload.py (web upload, for any section using the
same L-section table layout OCRPipeline is calibrated to read). Keeping
this logic in one place means the two entry points can't silently drift
out of sync with different review rules.
"""

import csv

ELEV_MIN, ELEV_MAX = 20, 600

# A value is flagged as a probable OCR misread if it deviates from the
# local median (of nearby valid readings on both sides) by more than
# this. Range confirmed by reviewer: ~5-10m; using the midpoint.
SPIKE_THRESHOLD = 8.0

# How many stations to look on EACH side when building the local
# comparison window (so up to 2*window readings, minus gaps, feed the
# median). Widened from an earlier prev/next-pair design: that version
# required the immediate neighbor before AND after to agree with each
# other before flagging anything, which meant a second nearby bad value
# could mask the first (both sit outside the range check individually,
# so neither cross-checks as a valid neighbor for the other, and the
# whole check silently skips). A wider median-based window is robust to
# more than one bad value in the same local stretch.
SPIKE_NEIGHBOR_WINDOW = 5

INDEX_FIELD, CHAINAGE_FIELD, GL_FIELD, FL_FIELD, REVIEW_FIELD = 0, 1, 2, 3, 4


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


def _median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def flag_spikes(rows, field_idx, threshold=SPIKE_THRESHOLD, window=SPIKE_NEIGHBOR_WINDOW):
    """
    Mutates `rows` in place. For each row, gathers up to `window` valid
    values on each side (skipping the row itself), takes their median as
    the local expected trend, and flags the row's own value if it
    deviates from that median by more than `threshold`. A single other
    bad value nearby no longer blocks detection - as long as the
    majority of the window is clean, the median reflects the true
    local trend.
    """
    n = len(rows)
    flagged = 0
    for i in range(n):
        value = rows[i][field_idx]
        if value is None:
            continue

        nearby = []
        for j in range(max(0, i - window), min(n, i + window + 1)):
            if j == i:
                continue
            v = rows[j][field_idx]
            if v is not None:
                nearby.append(v)

        if len(nearby) < 2:
            continue

        local_median = _median(nearby)

        if abs(value - local_median) > threshold:
            rows[i][field_idx] = None
            rows[i][REVIEW_FIELD] = "YES"
            flagged += 1

    return flagged


def build_review_rows(records, chainage_start, chainage_step=20):
    """
    records: list of dicts from OCRPipeline.process(), each expected to
    have 'ground_level' and 'formation_level' keys.

    Returns rows_out: list of [index, chainage, gl, fl, needs_review].
    """
    rows_out = []
    for i, rec in enumerate(records):
        chainage = chainage_start + chainage_step * i
        gl = salvage_decimal(rec.get("ground_level"))
        fl = salvage_decimal(rec.get("formation_level"))
        review = "YES" if (needs_review(gl) or needs_review(fl)) else ""
        rows_out.append([i, chainage, gl, fl, review])
    return rows_out


def apply_spike_detection(rows_out):
    """Runs flag_spikes on both GL and FL in place. Returns (gl_spikes, fl_spikes)."""
    gl_spikes = flag_spikes(rows_out, GL_FIELD)
    fl_spikes = flag_spikes(rows_out, FL_FIELD)
    return gl_spikes, fl_spikes


def write_review_csv(rows_out, out_path):
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "chainage", "ground_level", "formation_level", "needs_review"])
        for i, ch, gl, fl, review in rows_out:
            w.writerow([i, ch, "" if gl is None else gl, "" if fl is None else fl, review])


def summarize_rows(rows_out, gl_spikes=0, fl_spikes=0):
    flagged = sum(1 for row in rows_out if row[REVIEW_FIELD] == "YES")
    total = len(rows_out)
    return {
        "total_stations": total,
        "clean_prefilled": total - flagged,
        "needs_manual_review": flagged,
        "gl_spikes_flagged": gl_spikes,
        "fl_spikes_flagged": fl_spikes,
    }
