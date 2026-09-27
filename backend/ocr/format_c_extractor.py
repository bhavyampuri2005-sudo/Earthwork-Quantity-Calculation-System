"""
FORMAT_C extractor - KRC "PLAN AND PROFILE" text-native drawings.

Unlike FORMAT_A / FORMAT_B (per-station text lines), this format emits each
COLUMN as one concatenated blob line:

    line X: 253752540025425...          <- every chainage, no separators
    line Y: 809.276809.255809.005...    <- every formation level
    line Z: 4.9906.0016.590...          <- every cut/fill value (signed)
    line W: 804.286803.254802.415...    <- every ground level

Complications handled here:
  * blob line index varies per page -> detect by content, never by position
  * column order is not fixed -> classify by value range, then disambiguate
    FL vs GL using the FL - GL == cut/fill redundancy check
  * a column can be SPLIT across two lines (pages 6 and 9) and the fragments
    are not always in reading order -> try both orders, keep whichever
    satisfies the redundancy check
  * value columns can be one shorter than the chainage column -> try both
    alignments, keep whichever satisfies the redundancy check
"""

import re

LEVEL_MIN, LEVEL_MAX = 300.0, 1200.0   # plausible RL band for this corridor
DIFF_MAX = 100.0                        # cut/fill magnitude ceiling
TOL = 0.002                             # metres; printed to 3 dp

NUM_RE = re.compile(r"-?\d+\.\d{3}")
CH_RE = re.compile(r"\d{5}")


def _numbers(line):
    return [float(x) for x in NUM_RE.findall(line)]


def _find_chainage_line(lines):
    """Pure-digit blob that decodes to 5-digit chainages on a constant step."""
    best = None
    for i, line in enumerate(lines):
        s = line.strip()
        if len(s) < 50 or not s.isdigit() or len(s) % 5:
            continue
        vals = [int(x) for x in CH_RE.findall(s)]
        if len(vals) < 20:
            continue
        steps = {b - a for a, b in zip(vals, vals[1:])}
        if len(steps) == 1 and 0 < steps.pop() <= 100:
            if best is None or len(vals) > len(best[1]):
                best = (i, vals)
    return best


def _classify(lines, skip_idx, n_expect):
    """Split numeric blobs into level-like and diff-like fragments."""
    levels, diffs = [], []
    for i, line in enumerate(lines):
        if i == skip_idx:
            continue
        nums = _numbers(line)
        if len(nums) < 20:
            continue
        in_level = sum(LEVEL_MIN <= abs(v) <= LEVEL_MAX for v in nums)
        in_diff = sum(abs(v) <= DIFF_MAX for v in nums)
        if in_level / len(nums) > 0.9:
            levels.append((i, nums))
        elif in_diff / len(nums) > 0.9:
            diffs.append((i, nums))
    return levels, diffs


def _assemble(frags, n_expect):
    """
    Turn fragments into candidate full columns.

    A fragment already at (near) full length is a column on its own. Shorter
    fragments are pieced together; because reading order is not reliable, both
    orderings are returned as candidates for the caller to validate.
    """
    full = [f for f in frags if len(f[1]) >= 0.9 * n_expect]
    partial = [f for f in frags if len(f[1]) < 0.9 * n_expect]

    candidates = [[list(f[1])] for f in full]
    out = [c[0] for c in candidates]

    if partial:
        partial.sort(key=lambda f: f[0])
        joined = []
        for a, b in ((0, 1), (1, 0)):
            if len(partial) >= 2:
                merged = list(partial[a][1]) + list(partial[b][1])
                if 0.9 * n_expect <= len(merged) <= 1.1 * n_expect:
                    joined.append(merged)
        if not joined and len(partial) == 1:
            joined.append(list(partial[0][1]))
        out.extend(joined)
    return out


def _check(fl, gl, cf):
    """Fraction of stations where FL - GL matches the printed cut/fill."""
    n = min(len(fl), len(gl), len(cf))
    if not n:
        return 0.0, 0
    ok = sum(abs((fl[i] - gl[i]) - cf[i]) <= TOL for i in range(n))
    return ok / n, n


def _offsets(arr, length, cap=4):
    """Every window start that could align this fragment to `length`."""
    slack = len(arr) - length
    if slack < 0:
        return []
    return list(range(min(slack, cap) + 1))


def parse_page(text):
    """
    Parse one FORMAT_C sheet.

    Returns dict with stations (chainage, gl, fl, cut_fill) plus a match_rate
    describing how much of the sheet passed the FL - GL redundancy check.
    """
    lines = text.split("\n")
    found = _find_chainage_line(lines)
    if not found:
        return {"ok": False, "reason": "no chainage blob found"}

    ch_idx, chainages = found
    n = len(chainages)

    levels, diffs = _classify(lines, ch_idx, n)
    if not levels or not diffs:
        return {"ok": False, "reason": f"levels={len(levels)} diffs={len(diffs)}"}

    level_cols = _assemble(levels, n)
    diff_cols = _assemble(diffs, n)

    best = None
    for cf_raw in diff_cols:
        for a in level_cols:
            for b in level_cols:
                if a is b:
                    continue
                L = min(len(a), len(b), len(cf_raw), len(chainages))
                if L < 20:
                    continue
                for oa in _offsets(a, L):
                    for ob in _offsets(b, L):
                        for oc in _offsets(cf_raw, L):
                            fl = a[oa:oa + L]
                            gl = b[ob:ob + L]
                            cf = cf_raw[oc:oc + L]
                            rate, cnt = _check(fl, gl, cf)
                            if best is None or rate > best[0]:
                                best = (rate, cnt, fl, gl, cf, len(a), oa)

    if best is None or best[0] < 0.5:
        return {"ok": False, "reason": f"redundancy check failed (best={best[0] if best else 0:.2f})"}

    rate, cnt, fl, gl, cf, fl_len, fl_off = best

    # The full-length columns share the chainage column's indexing, so reuse
    # the winning formation-level offset when the lengths line up.
    ch_all = [float(c) for c in chainages]
    ch_off = fl_off if len(ch_all) == fl_len else 0
    ch = ch_all[ch_off:ch_off + cnt]
    if len(ch) < cnt:
        return {"ok": False, "reason": "chainage column shorter than value columns"}

    stations = []
    for i in range(cnt):
        matches = abs((fl[i] - gl[i]) - cf[i]) <= TOL
        stations.append({
            "chainage": ch[i],
            "ground_level": round(gl[i], 3),
            "formation_level": round(fl[i], 3),
            "cut_fill": round(cf[i], 3),
            "status": "clean" if matches else "flagged",
        })

    return {
        "ok": True,
        "match_rate": rate,
        "n_stations": len(stations),
        "chainage_start": stations[0]["chainage"],
        "chainage_end": stations[-1]["chainage"],
        "stations": stations,
    }


def parse_pdf(path):
    """Parse every FORMAT_C sheet in the file, in page order."""
    import pypdf
    reader = pypdf.PdfReader(path)
    sheets = []
    for pi, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if len(text) < 2000:
            continue
        res = parse_page(text)
        res["page"] = pi + 1
        sheets.append(res)
    return sheets
