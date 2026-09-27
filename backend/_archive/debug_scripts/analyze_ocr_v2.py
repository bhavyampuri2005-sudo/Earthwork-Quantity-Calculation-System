import json
import re
from collections import defaultdict
import sys

RESULTS_PATH = sys.argv[1] if len(sys.argv) > 1 else "ocr_results.json"

# Fallback bounds only used when a row doesn't have enough clean decimal
# reads yet to compute its own expected range. Matches parser.py's own
# sanity bound for elevations (20-600), not a narrow dataset-specific guess.
FALLBACK_MIN, FALLBACK_MAX = 20, 600
RANGE_PADDING = 100          # +/- around the median of confirmed-good reads
MIN_SEEDS_FOR_DYNAMIC_RANGE = 5


def parse_key(filename):
    m = re.match(r"r(\d+)_c(\d+)", filename)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def clean_digits(text):
    """Strip everything except digits and a decimal point."""
    if not text:
        return ""
    return re.sub(r"[^0-9.]", "", text)


def to_number(text):
    cleaned = clean_digits(text)
    if not cleaned or cleaned == "." or cleaned.count(".") > 1:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def compute_expected_range(row_data, cols):
    """
    Derive a realistic expected range for this row from values that are
    already well-formed (exactly one decimal point) and within a broad
    sanity bound. GL/FL vary smoothly along a chainage, so the true
    range for a given subset can sit anywhere inside 20-600 - a single
    hardcoded window (e.g. 300-450) silently misclassifies correct reads
    from a different part of the range as "out of range".
    """
    seeds = []
    for c in cols:
        raw = row_data.get(c, "")
        digits = clean_digits(raw)
        if digits.count(".") != 1:
            continue
        try:
            v = float(digits)
        except ValueError:
            continue
        if FALLBACK_MIN <= v <= FALLBACK_MAX:
            seeds.append(v)

    if len(seeds) < MIN_SEEDS_FOR_DYNAMIC_RANGE:
        return (FALLBACK_MIN, FALLBACK_MAX)

    seeds.sort()
    median = seeds[len(seeds) // 2]
    return (median - RANGE_PADDING, median + RANGE_PADDING)


def salvage_missing_decimal(digits, expected_range):
    """
    If OCR dropped the decimal point entirely (e.g. '374995' instead of
    '374.995'), try inserting it at every position and keep the result
    ONLY if exactly one position lands inside the expected range. If
    more than one position fits, it's ambiguous - leave it flagged for
    manual review rather than guessing.
    """
    if not digits or "." in digits:
        return None
    candidates = []
    for i in range(1, len(digits)):
        candidate_str = digits[:i] + "." + digits[i:]
        try:
            v = float(candidate_str)
        except ValueError:
            continue
        if expected_range[0] <= v <= expected_range[1]:
            candidates.append(v)
    if len(candidates) == 1:
        return candidates[0]
    return None


def classify(row_data, cols, expected_range):
    clean, salvaged, out_of_range, empty = [], [], [], []
    for c in cols:
        raw = row_data.get(c, "")
        digits = clean_digits(raw)
        val = to_number(raw)

        if val is None:
            salvage = salvage_missing_decimal(digits, expected_range)
            if salvage is not None:
                salvaged.append((c, raw, salvage))
            else:
                empty.append((c, raw))
            continue

        if expected_range[0] <= val <= expected_range[1]:
            clean.append((c, raw, val))
        else:
            salvage = salvage_missing_decimal(digits, expected_range)
            if salvage is not None:
                salvaged.append((c, raw, salvage))
            else:
                out_of_range.append((c, raw, val))

    return clean, salvaged, out_of_range, empty


def report(label, clean, salvaged, out_of_range, empty, total, expected_range):
    print(f"\n=== {label} ===")
    print(f"Expected range used   : {expected_range[0]:.1f} - {expected_range[1]:.1f}")
    print(f"Total columns checked : {total}")
    total_clean = len(clean) + len(salvaged)
    print(f"Clean (original)      : {len(clean)} ({len(clean)/total*100:.1f}%)")
    print(f"Clean (salvaged decimal): {len(salvaged)} ({len(salvaged)/total*100:.1f}%)")
    print(f"Clean TOTAL            : {total_clean} ({total_clean/total*100:.1f}%)")
    print(f"Out-of-range (likely garbage) : {len(out_of_range)} ({len(out_of_range)/total*100:.1f}%)")
    print(f"Empty/unparseable     : {len(empty)} ({len(empty)/total*100:.1f}%)")
    real_failure_rate = (len(out_of_range) + len(empty)) / total * 100
    print(f"REAL failure rate     : {real_failure_rate:.1f}%")

    if salvaged:
        print(f"\nFirst 10 salvaged (decimal point inserted) examples:")
        for c, raw, val in salvaged[:10]:
            print(f"  col {c}: raw='{raw}' -> salvaged {val}")
    if out_of_range:
        print(f"\nFirst 15 out-of-range examples:")
        for c, raw, val in out_of_range[:15]:
            print(f"  col {c}: raw='{raw}' -> parsed {val}")
    if empty:
        print(f"\nFirst 15 empty/unparseable examples:")
        for c, raw in empty[:15]:
            print(f"  col {c}: raw='{raw}'")


def main():
    with open(RESULTS_PATH) as f:
        results = json.load(f)

    by_row = defaultdict(dict)
    for filename, text in results.items():
        parsed = parse_key(filename)
        if parsed is None:
            continue
        row, col = parsed
        by_row[row][col] = text

    # Skip column 0 - it looks like a label/index column, not real chainage data
    gl_cells = by_row.get(6, {})
    fl_cells = by_row.get(7, {})
    cols = sorted(c for c in set(gl_cells) | set(fl_cells) if c > 0)

    gl_range = compute_expected_range(gl_cells, cols)
    fl_range = compute_expected_range(fl_cells, cols)

    gl_clean, gl_salvaged, gl_bad, gl_empty = classify(gl_cells, cols, gl_range)
    fl_clean, fl_salvaged, fl_bad, fl_empty = classify(fl_cells, cols, fl_range)

    report("GL (row 6)", gl_clean, gl_salvaged, gl_bad, gl_empty, len(cols), gl_range)
    report("FL (row 7)", fl_clean, fl_salvaged, fl_bad, fl_empty, len(cols), fl_range)

    gl_clean_cols = {c for c, _, _ in gl_clean} | {c for c, _, _ in gl_salvaged}
    fl_clean_cols = {c for c, _, _ in fl_clean} | {c for c, _, _ in fl_salvaged}
    both_clean = gl_clean_cols & fl_clean_cols

    print(f"\n=== Bottom line ===")
    print(f"Columns where BOTH GL and FL are clean: {len(both_clean)}/{len(cols)} ({len(both_clean)/len(cols)*100:.1f}%)")


if __name__ == "__main__":
    main()
