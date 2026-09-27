from ocr.robust_spike import robust_trend_flag
"""
Shared OCR-review utilities: decimal salvage, valid-range checking, and
outlier detection for suspect GL/FL readings.

Two independent outlier checks run, in order:

1. flag_implausible_depth - an absolute sanity ceiling on cut/fill
   DEPTH itself (|GL-FL|). Every confirmed-real depth in this dataset
   is under 2m; every confirmed-bad one (OCR digit swaps like
   374->574) is 190m+. No ambiguous middle ground, so this is a
   simple, order-independent, highly reliable catch for the "many
   stations near 200m cut" class of error.

2. flag_spikes - a neighbor-based check for subtler misreads that
   don't blow past the absolute ceiling. Builds its comparison window
   from a FROZEN snapshot of the original values taken before any
   flagging happens in that pass, so an earlier station being flagged
   never distorts what a later station sees as its neighbors.
"""

import csv

ELEV_MIN, ELEV_MAX = 20, 600
MAX_PLAUSIBLE_DEPTH = 20.0
SPIKE_THRESHOLD = 8.0
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


def flag_implausible_depth(rows_out, max_depth=MAX_PLAUSIBLE_DEPTH):
    flagged = 0
    for row in rows_out:
        gl, fl = row[GL_FIELD], row[FL_FIELD]
        if gl is None or fl is None:
            continue
        if abs(gl - fl) > max_depth:
            row[GL_FIELD] = None
            row[FL_FIELD] = None
            row[REVIEW_FIELD] = "YES"
            flagged += 1
    return flagged


def _median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def flag_spikes(rows, field_idx, threshold=SPIKE_THRESHOLD, window=SPIKE_NEIGHBOR_WINDOW):
    n = len(rows)
    snapshot = [rows[i][field_idx] for i in range(n)]
    flagged = 0

    for i in range(n):
        value = snapshot[i]
        if value is None:
            continue

        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        nearby = [snapshot[j] for j in range(lo, hi) if j != i and snapshot[j] is not None]

        if len(nearby) < 2:
            continue

        local_median = _median(nearby)

        if abs(value - local_median) > threshold:
            rows[i][field_idx] = None
            rows[i][REVIEW_FIELD] = "YES"
            flagged += 1

    return flagged


def flag_spikes_robust(rows, field_idx, threshold=SPIKE_THRESHOLD, window=15):
    vals = {i: rows[i][field_idx] for i in range(len(rows))}
    flags = robust_trend_flag(vals, threshold=threshold, window=window)
    for i in flags:
        rows[i][field_idx] = None
        rows[i][REVIEW_FIELD] = "YES"
    return len(flags)

TEXT_NATIVE_ELEV_MIN, TEXT_NATIVE_ELEV_MAX = -100.0, 5000.0


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
        chainage = rec.get("field_chainage")
        if chainage is None:
            chainage = chainage_start + chainage_step * i
        gl = rec.get("ground_level")
        fl = rec.get("formation_level")
        if not text_native:
            gl = salvage_decimal(gl)
            fl = salvage_decimal(fl)
        review = "YES" if (_bad(gl) or _bad(fl)) else ""
        rows_out.append([i, chainage, gl, fl, review])
    return rows_out


def apply_outlier_detection(rows_out):
    gl_spikes = flag_spikes_robust(rows_out, GL_FIELD)
    fl_spikes = flag_spikes_robust(rows_out, FL_FIELD)
    depth_flagged = flag_implausible_depth(rows_out, max_depth=100.0)
    return depth_flagged, gl_spikes, fl_spikes


def write_review_csv(rows_out, out_path):
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "chainage", "ground_level", "formation_level", "needs_review"])
        for i, ch, gl, fl, review in rows_out:
            w.writerow([i, ch, "" if gl is None else gl, "" if fl is None else fl, review])


def summarize_rows(rows_out, depth_flagged=0, gl_spikes=0, fl_spikes=0):
    flagged = sum(1 for row in rows_out if row[REVIEW_FIELD] == "YES")
    total = len(rows_out)
    return {
        "total_stations": total,
        "clean_prefilled": total - flagged,
        "needs_manual_review": flagged,
        "implausible_depth_flagged": depth_flagged,
        "gl_spikes_flagged": gl_spikes,
        "fl_spikes_flagged": fl_spikes,
    }
