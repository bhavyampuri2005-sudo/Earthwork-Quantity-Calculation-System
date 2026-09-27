"""
Re-applies the current outlier-detection rules to an EXISTING review.csv
without re-running OCR.
"""

import csv
import shutil
import sys

from ocr.review_utils import apply_outlier_detection, write_review_csv, summarize_rows


def load_rows(path):
    rows_out = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            gl_raw = (row.get("ground_level") or "").strip()
            fl_raw = (row.get("formation_level") or "").strip()
            gl = float(gl_raw) if gl_raw else None
            fl = float(fl_raw) if fl_raw else None
            rows_out.append([
                int(row["index"]),
                float(row["chainage"]),
                gl,
                fl,
                row.get("needs_review", ""),
            ])
    return rows_out


def main(path="review.csv"):
    backup_path = path + ".bak2"
    shutil.copy(path, backup_path)
    print(f"Backed up current file to {backup_path}")

    rows_out = load_rows(path)
    depth_flagged, gl_spikes, fl_spikes = apply_outlier_detection(rows_out)
    write_review_csv(rows_out, path)

    summary = summarize_rows(rows_out, depth_flagged, gl_spikes, fl_spikes)
    print(f"\nRe-flagged {summary['total_stations']} rows in {path}")
    print(f"Pre-filled (clean) : {summary['clean_prefilled']}")
    print(f"Needs manual review: {summary['needs_manual_review']}")
    print(f"  of which implausible depth (>20m) flagged: {summary['implausible_depth_flagged']}")
    print(f"  of which GL spikes newly flagged: {summary['gl_spikes_flagged']}")
    print(f"  of which FL spikes newly flagged: {summary['fl_spikes_flagged']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "review.csv")
