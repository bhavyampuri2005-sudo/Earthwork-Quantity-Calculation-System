"""
Load a FORMAT_C (KRC plan-and-profile) multi-sheet PDF into a review CSV.

Every sheet inside the PDF is parsed, then merged into one continuous station
list. Where consecutive sheets overlap, the later sheet wins -- the same rule
the combined export uses.

Chainage is read from the PDF text itself, so no chainage_start / chainage_step
is supplied or needed. That is deliberate: reconstructing chainage
arithmetically is what silently corrupted project 6.

Usage:
    python3 load_krc.py uploads/<file>.pdf <project_id>
    python3 load_krc.py uploads/<file>.pdf <project_id> --dry-run
"""

import csv
import os
import sys

from ocr.format_c_extractor import parse_pdf


def review_csv_path(project_id):
    """Matches upload.py's naming: review.csv for project 1, else review_N.csv."""
    return "review.csv" if int(project_id) == 1 else "review_%s.csv" % project_id


def merge_sheets(sheets):
    """Merge all sheets, later sheet winning at overlapping chainages."""
    merged = {}
    provenance = {}
    for sheet in sheets:
        if not sheet.get("ok"):
            continue
        for st in sheet["stations"]:
            merged[st["chainage"]] = st
            provenance[st["chainage"]] = sheet["page"]
    ordered = [merged[c] for c in sorted(merged)]
    return ordered, provenance


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    if len(args) != 2:
        print(__doc__)
        return 1

    pdf_path, project_id = args[0], args[1]

    if not os.path.exists(pdf_path):
        print("ERROR: file not found: %s" % pdf_path)
        return 1

    print("Parsing %s ..." % pdf_path)
    sheets = parse_pdf(pdf_path)

    failed = [s for s in sheets if not s.get("ok")]
    for s in sheets:
        if s.get("ok"):
            clean = sum(1 for x in s["stations"] if x["status"] == "clean")
            print("  page %-3s %4d stations  %.0f-%.0f  clean=%d  match=%.1f%%" % (
                s["page"], s["n_stations"], s["chainage_start"],
                s["chainage_end"], clean, s["match_rate"] * 100))
        else:
            print("  page %-3s FAILED - %s" % (s["page"], s.get("reason")))

    if failed:
        print("\n%d sheet(s) failed to parse. Aborting rather than writing partial data." % len(failed))
        return 1

    stations, provenance = merge_sheets(sheets)
    if not stations:
        print("No stations parsed. Aborting.")
        return 1

    chainages = [s["chainage"] for s in stations]
    steps = sorted({round(b - a, 3) for a, b in zip(chainages, chainages[1:])})
    gaps = [(a, b) for a, b in zip(chainages, chainages[1:]) if round(b - a, 3) != steps[0]]
    flagged = [s for s in stations if s["status"] != "clean"]

    print("\nMerged: %d stations, %.0f - %.0f" % (len(stations), chainages[0], chainages[-1]))
    print("Step(s) present: %s" % steps)
    print("Gaps: %d" % len(gaps))
    print("Flagged (FL-GL != printed cut/fill): %d" % len(flagged))

    if len(steps) > 1:
        print("\nWARNING: more than one step size present -- inspect before trusting.")
        for a, b in gaps[:10]:
            print("   %.0f -> %.0f" % (a, b))

    out_path = review_csv_path(project_id)

    if dry_run:
        print("\n--dry-run: nothing written. Would write %d rows to %s" % (len(stations), out_path))
        print("\nFirst 3 rows:")
        for i, st in enumerate(stations[:3]):
            print("  %d,%s,%s,%s," % (i, st["chainage"], st["ground_level"], st["formation_level"]))
        return 0

    if os.path.exists(out_path):
        backup = out_path + ".bak"
        os.replace(out_path, backup)
        print("\nExisting %s moved to %s" % (out_path, backup))

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "chainage", "ground_level", "formation_level", "needs_review"])
        for i, st in enumerate(stations):
            w.writerow([
                i,
                st["chainage"],
                st["ground_level"],
                st["formation_level"],
                "" if st["status"] == "clean" else "YES",
            ])

    print("Wrote %d rows to %s" % (len(stations), out_path))
    print("\nNext:")
    print("  1. Add SlopeMaster ranges covering %.0f-%.0f for project %s" % (
        chainages[0], chainages[-1], project_id))
    print("  2. POST /calculation/run       {\"project_id\": %s}" % project_id)
    print("  3. POST /review/auto-validate/%s" % project_id)
    print("  4. POST /calculation/run again  (volumes only count approved stations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
