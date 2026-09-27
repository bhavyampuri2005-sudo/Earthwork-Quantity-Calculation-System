import json
import re
from collections import defaultdict

ROW_LABELS = {
    5: "cut_fill",
    6: "GL",
    7: "FL",
    8: "RL",
    9: "chainage",
}

RESULTS_PATH = "ocr_results.json"


def parse_key(filename):
    match = re.match(r"r(\d+)_c(\d+)", filename)
    if not match:
        return None
    row, col = match.groups()
    return int(row), int(col)


def to_number(text):
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


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

    print("=== Per-row summary (rows 5-9 only) ===\n")
    for row in sorted(ROW_LABELS):
        label = ROW_LABELS[row]
        cells = by_row.get(row, {})
        total = len(cells)
        with_digit = sum(1 for v in cells.values() if v and any(ch.isdigit() for ch in v))
        blank = total - with_digit
        print(f"Row {row} ({label}): {with_digit}/{total} have digits, {blank} blank/garbage")

    print("\n=== Sample values, first 10 columns per row ===\n")
    for row in sorted(ROW_LABELS):
        label = ROW_LABELS[row]
        cells = by_row.get(row, {})
        sample = [f"c{c}='{cells.get(c, '<missing>')}'" for c in sorted(cells)[:10]]
        print(f"Row {row} ({label}): " + ", ".join(sample))

    gl_row, fl_row = 6, 7
    gl_cells = by_row.get(gl_row, {})
    fl_cells = by_row.get(fl_row, {})
    cols = sorted(set(gl_cells) | set(fl_cells))

    print(f"\n=== GL/FL anomaly checks (rows {gl_row}, {fl_row}) ===\n")

    flagged = 0
    prev_gl = None
    for c in cols:
        gl_val = to_number(gl_cells.get(c))
        fl_val = to_number(fl_cells.get(c))

        issues = []

        if gl_val is None:
            issues.append("GL unparseable")
        if fl_val is None:
            issues.append("FL unparseable")

        if gl_val is not None and prev_gl is not None and abs(gl_val - prev_gl) > 5:
            issues.append(f"GL jump {prev_gl} -> {gl_val}")

        if gl_val is not None and fl_val is not None and abs(gl_val - fl_val) > 15:
            issues.append(f"GL-FL spread {abs(gl_val - fl_val):.2f}")

        if issues:
            flagged += 1
            print(
                f"col {c}: GL='{gl_cells.get(c)}' FL='{fl_cells.get(c)}' -> "
                + "; ".join(issues)
            )

        if gl_val is not None:
            prev_gl = gl_val

    print(f"\nTotal columns checked: {len(cols)}")
    print(f"Flagged columns: {flagged}")


if __name__ == "__main__":
    main()
