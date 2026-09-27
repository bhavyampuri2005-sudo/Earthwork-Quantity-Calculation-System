"""
Text-native (CAD-exported) L-section extraction.

Two responsibilities:

1. is_text_native(pdf_path)
   Decide whether a PDF has a real embedded text layer (AutoCAD / any CAD
   export) or is a scan. Scans go down the OCR pipeline unchanged.

2. extract_text_native_records(pdf_path, chainage_start, chainage_step)
   Pull station rows straight out of the text layer with `pdftotext -layout`
   plus a line regex -- no rasterising, no OCR.

Layout families
---------------
CAD PDFs do not share a table layout. Each known family gets its own line
pattern; on extraction every pattern is tried and the one yielding the most
valid rows wins.

  FORMAT_A  6-digit.2-decimal chainage, 5 columns
            e.g.  143900.00  229.745  235.264  236.026  5.519
            cols: chainage  GL  FL  RL  cut/fill-diff
            Two redundancy checks available:
                diff == FL - GL
                RL   == FL + RAIL_OFFSET
            Two equations, four fields -> a single failing check identifies
            which field is wrong, so it can be auto-corrected.

  FORMAT_B  5-digit integer chainage, 4 columns
            e.g.  11700  808.257  812.389  4.132
            cols: chainage  GL  FL  banking/cutting-diff
            No rail-level row on these sheets, so only one check is
            available:
                diff == FL - GL
            One equation cannot say WHICH field is wrong, so a mismatch is
            flagged for review and never auto-corrected.
            Negative diff == cutting (formation below ground).

Output
------
Returns (records, meta).

`records` is one dict per station on the chainage_start/chainage_step grid,
in order, using the same field names as the OCR path's parser (ocr/parser.py
KNOWN):

    field_chainage, ground_level, formation_level, rail_level, cut_fill

Missing or unresolvable stations are kept in place as None-valued records so
downstream arithmetic chainage alignment is preserved. `gap` distinguishes
"no line for this station in the source" from "line found but unresolvable".

If no pattern produces a usable number of rows, `records` comes back EMPTY so
the caller's existing "no rows extracted" guard fires instead of writing a
grid of nulls.
"""

import re
import subprocess

# --- tuning -----------------------------------------------------------------

# Rail level sits this far above formation level (FORMAT_A sheets only).
# Confirmed from the drawing's own track-structure notes:
# rail 172mm + pad 10mm + sleeper 230mm + ballast 350mm = 0.762 m
RAIL_OFFSET = 0.762

# Redundancy-check tolerance in metres.
TOLERANCE = 0.01

# A row that has GL and FL but no printed diff column cannot be validated.
# False -> flag it for manual review (stricter, default).
# True  -> accept it, filling diff = FL - GL (more usable, unvalidated).
ACCEPT_UNVALIDATED_ROWS = False

# If the best-scoring pattern matches fewer than this fraction of the expected
# stations, treat the sheet as an unknown layout rather than returning junk.
MIN_VALID_FRACTION = 0.05

# Plausible elevation band (metres) for GL/FL/RL. Rejects stray numbers picked
# up from annotations, bridge schedules, curve tables etc.
MIN_LEVEL = -100.0
MAX_LEVEL = 5000.0


# --- format detection -------------------------------------------------------

def is_text_native(pdf_path):
    """True if the PDF carries a real embedded text layer (CAD export)."""
    try:
        out = subprocess.run(
            ["pdffonts", str(pdf_path)],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if out.returncode != 0:
        return False

    # pdffonts always prints a 2-line header; any line beyond that is a font.
    lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    return len(lines) > 2


def _pdf_text(pdf_path):
    """Column-aligned text dump of every page."""
    try:
        out = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=180,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "pdftotext not found -- install poppler (brew install poppler)."
        )
    except subprocess.SubprocessError as exc:
        raise RuntimeError("pdftotext failed: %s" % exc)

    if out.returncode != 0:
        raise RuntimeError("pdftotext failed: %s" % (out.stderr or "").strip())
    return out.stdout


# --- line patterns ----------------------------------------------------------

_NUM = r"-?\d+\.\d{2,3}"

FORMAT_A_RE = re.compile(
    r"(?<![\d.])(\d{6}\.\d{2})\s+"      # chainage 143900.00
    r"(%s)\s+(%s)\s+(%s)\s+(%s)"        # GL  FL  RL  diff
    % (_NUM, _NUM, _NUM, _NUM)
)

FORMAT_B_RE = re.compile(
    r"(?<![\d.])(\d{5})\s+"             # chainage 11700
    r"(%s)\s+(%s)\s+(%s)"               # GL  FL  diff
    % (_NUM, _NUM, _NUM)
)

# Same as B but with no printed diff -- used only to salvage rows that would
# otherwise vanish entirely.
FORMAT_B_PARTIAL_RE = re.compile(
    r"(?<![\d.])(\d{5})\s+(%s)\s+(%s)(?!\s*-?\d)" % (_NUM, _NUM)
)


def _plausible_level(v):
    return MIN_LEVEL <= v <= MAX_LEVEL


def _scan(text, pattern, ncols, grid):
    """
    Pull every match of `pattern` out of `text`.

    Only chainages that land on the expected station grid are kept -- this is
    what stops bridge numbers, curve tables and road chainages in the
    annotation blocks from being read as station rows.

    Returns {chainage: (values...)}.
    """
    found = {}
    for m in pattern.finditer(text):
        try:
            ch = float(m.group(1))
        except ValueError:
            continue
        if ch not in grid:
            continue

        vals = []
        ok = True
        for i in range(2, 2 + ncols):
            try:
                v = float(m.group(i))
            except (ValueError, IndexError):
                ok = False
                break
            vals.append(v)
        if not ok:
            continue

        # GL / FL / RL must look like elevations; the diff column may not.
        levels = vals[:-1] if len(vals) > 1 else vals
        if not all(_plausible_level(v) for v in levels):
            continue

        # First occurrence wins -- sheets repeat overlap stations at the joins.
        found.setdefault(ch, tuple(vals))
    return found


# --- per-format row resolution ---------------------------------------------

def _resolve_a(gl, fl, rl, diff):
    """
    FORMAT_A: two redundancy checks over four fields.

    One failing check -> the shared field of the failing check is wrong; the
    other check pins the rest, so correct it. Both failing -> unresolvable.

    Returns (record_fields_or_None, note).
    """
    diff_ok = abs((fl - gl) - diff) <= TOLERANCE
    rail_ok = abs((fl + RAIL_OFFSET) - rl) <= TOLERANCE

    if diff_ok and rail_ok:
        return (gl, fl, rl, diff), "clean"

    if rail_ok and not diff_ok:
        # FL and RL agree with each other, so trust them: GL or diff is off.
        # diff is the derived column -- recompute it.
        return (gl, fl, rl, round(fl - gl, 3)), "corrected:cut_fill"

    if diff_ok and not rail_ok:
        # GL, FL and diff are mutually consistent -- RL is the odd one out.
        return (gl, fl, round(fl + RAIL_OFFSET, 3), diff), "corrected:rail_level"

    return None, "unresolved:both_checks_failed"


def _resolve_b(gl, fl, diff):
    """
    FORMAT_B: one redundancy check, four-ish fields.

    A mismatch says something is wrong but not what, so it is flagged, never
    auto-corrected. rail_level is not present on these sheets.
    """
    if diff is None:
        if ACCEPT_UNVALIDATED_ROWS:
            return (gl, fl, None, round(fl - gl, 3)), "unvalidated:no_diff_column"
        return None, "unresolved:no_diff_column"

    if abs((fl - gl) - diff) <= TOLERANCE:
        return (gl, fl, None, diff), "clean"

    return None, "unresolved:diff_mismatch"


# --- main entry point -------------------------------------------------------

def extract_text_native_records(pdf_path, chainage_start, chainage_step):
    """
    Extract station records from a text-native (CAD) L-section PDF.

    Returns (records, meta). `records` is empty if no known layout matched.
    """
    chainage_start = float(chainage_start)
    chainage_step = float(chainage_step)
    if chainage_step <= 0:
        raise ValueError("chainage_step must be positive")

    text = _pdf_text(pdf_path)

    # Build the expected station grid from the sheet's own chainage span, so
    # detection does not depend on the user guessing the station count.
    all_ch = [float(m.group(1)) for m in FORMAT_A_RE.finditer(text)]
    all_ch += [float(m.group(1)) for m in FORMAT_B_RE.finditer(text)]
    on_grid = [
        c for c in all_ch
        if c >= chainage_start
        and abs(((c - chainage_start) / chainage_step) % 1.0) < 1e-6
    ]
    chainage_end = max(on_grid) if on_grid else chainage_start

    grid = []
    c = chainage_start
    while c <= chainage_end + 1e-6:
        grid.append(round(c, 3))
        c += chainage_step
    grid_set = set(grid)

    # Try every known layout; most valid rows wins.
    hits_a = _scan(text, FORMAT_A_RE, 4, grid_set)
    hits_b = _scan(text, FORMAT_B_RE, 3, grid_set)

    if len(hits_a) >= len(hits_b) and hits_a:
        fmt, hits = "A", hits_a
    elif hits_b:
        fmt, hits = "B", hits_b
    else:
        fmt, hits = None, {}

    # FORMAT_B only: salvage stations that have GL and FL but no printed diff.
    partial = {}
    if fmt == "B":
        for ch, vals in _scan(text, FORMAT_B_PARTIAL_RE, 2, grid_set).items():
            if ch not in hits:
                partial[ch] = vals

    meta = {
        "route_used": "text_native",
        "format_detected": fmt,
        "expected_stations": len(grid),
        "lines_matched": len(hits) + len(partial),
        "clean": 0,
        "corrected": 0,
        "flagged": 0,
        "missing": 0,
    }

    # Unknown layout -> hand back nothing and let the caller's guard fire.
    if not fmt or (len(grid) and
                   (len(hits) + len(partial)) < MIN_VALID_FRACTION * len(grid)):
        meta["reason"] = "no known layout matched this sheet"
        return [], meta

    records = []
    for ch in grid:
        note = "missing"
        fields = None

        if ch in hits:
            if fmt == "A":
                gl, fl, rl, diff = hits[ch]
                fields, note = _resolve_a(gl, fl, rl, diff)
            else:
                gl, fl, diff = hits[ch]
                fields, note = _resolve_b(gl, fl, diff)
        elif ch in partial:
            gl, fl = partial[ch]
            fields, note = _resolve_b(gl, fl, None)

        gap = (ch not in hits) and (ch not in partial)

        if fields is None:
            # Null ALL four fields, not just cut_fill: downstream review keys
            # solely off gl/fl being NULL, so a row with a null diff but live
            # gl/fl would sail through as clean.
            rec = {
                "field_chainage": ch,
                "ground_level": None,
                "formation_level": None,
                "rail_level": None,
                "cut_fill": None,
                "gap": gap,
                "flagged": True,
                "note": note,
            }
            if gap:
                meta["missing"] += 1
            else:
                meta["flagged"] += 1
        else:
            gl, fl, rl, diff = fields
            rec = {
                "field_chainage": ch,
                "ground_level": gl,
                "formation_level": fl,
                "rail_level": rl,
                "cut_fill": diff,
                "gap": False,
                "flagged": False,
                "note": note,
            }
            if note.startswith("corrected"):
                meta["corrected"] += 1
            meta["clean"] += 1

        records.append(rec)

    return records, meta


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("usage: text_native_extractor.py <pdf> <chainage_start> <step>")
        raise SystemExit(1)
    recs, m = extract_text_native_records(sys.argv[1], sys.argv[2], sys.argv[3])
    print("text-native:", is_text_native(sys.argv[1]))
    print(m)
    for r in recs[:5]:
        print(r)


# --- FORMAT_C: multi-sheet KRC-style blob-column PDFs -----------------------
# Unlike FORMAT_A/B (single sheet per file, pdftotext-based), these files
# hold multiple data sheets and must be read with pypdf's per-page
# extraction -- pdftotext (even with -layout) does not reproduce the
# column-blob structure this format relies on.

def extract_format_c_records(pdf_path):
    """
    Parse every FORMAT_C sheet and merge, later sheet winning at overlaps --
    same rule the combined multi-project export uses. Chainage comes
    directly from the PDF text, so there is nothing for the caller to
    supply or get wrong.
    """
    from ocr.format_c_extractor import parse_pdf as _parse_format_c

    sheets = _parse_format_c(pdf_path)
    failed = [s for s in sheets if not s.get("ok")]

    meta = {
        "route_used": "text_native",
        "format_detected": "C",
        "expected_stations": 0,
        "lines_matched": 0,
        "clean": 0,
        "corrected": 0,
        "flagged": 0,
        "missing": 0,
        "sheets_total": len(sheets),
        "sheets_failed": len(failed),
    }

    if not sheets or failed:
        meta["reason"] = (
            "no sheets found" if not sheets
            else "%d/%d sheet(s) failed: %s" % (
                len(failed), len(sheets),
                "; ".join("page %s: %s" % (s.get("page"), s.get("reason")) for s in failed),
            )
        )
        return [], meta

    merged = {}
    for sheet in sheets:
        for st in sheet["stations"]:
            merged[st["chainage"]] = st
    ordered = [merged[c] for c in sorted(merged)]

    records = [
        {
            "field_chainage": st["chainage"],
            "ground_level": st["ground_level"],
            "formation_level": st["formation_level"],
            "rail_level": None,
            "cut_fill": st["cut_fill"],
        }
        for st in ordered
    ]

    clean = sum(1 for st in ordered if st["status"] == "clean")
    meta.update({
        "expected_stations": len(ordered),
        "lines_matched": len(ordered),
        "clean": clean,
        "flagged": len(ordered) - clean,
    })
    return records, meta
