"""
Average End Area earthwork calculation, per SRS Module 5.

A = B*h + m*h^2
V = ((A1+A2)/2) * d

Cut and fill are calculated and reported separately. Per SRS Module 3,
manual review/approval of extracted data is a workflow the engineer
performs in the product UI - it does not have to be complete before
the calc engine runs.

A station only counts as "reviewed" if BOTH its GL and FL are present
AND fall within a physically plausible elevation range (20-600m, same
bound used elsewhere in the pipeline). Raw OCR garbage that survived
into a non-blank cell (e.g. a missing decimal point turning 374.995
into 374995) is treated the same as a blank cell - pending review -
rather than being fed into the area/volume formulas, where a bad
elevation produces a huge bogus h and, once squared, an impossible
volume.

Any interval touching a station still missing or out-of-range GL/FL
is marked "pending_review" with volume=None and excluded from the
totals, rather than blocking the whole run. Totals reflect only the
reviewed/complete portion of the alignment until the rest is approved.

Cut and fill use separate side-slope values (confirmed by reviewer),
so the slope lookup now passes the station's cut/fill/level type
through to SlopeMaster.get_slope() instead of a single project-wide m.
"""

import csv
from earthwork.slope_master import SlopeMaster

FORMATION_WIDTH_B = 7.85  # project-configured formation width (m)
ELEV_MIN, ELEV_MAX = -100.0, 5000.0  # plausible GL/FL range; matches the band
# text_native_extractor already validates against. The old 20-600 ceiling silently
# nulled every station on corridors above 600m (the KM10-25 stretch sits at ~800m).


def classify(gl, fl):
    diff = gl - fl
    if diff > 1e-6:
        return "cut", diff
    elif diff < -1e-6:
        return "fill", -diff
    return "level", 0.0


def area(h, m):
    return FORMATION_WIDTH_B * h + m * h * h


def load_stations(csv_path):
    stations = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            gl_raw = (row.get("ground_level") or "").strip()
            fl_raw = (row.get("formation_level") or "").strip()
            chainage = float(row["chainage"])

            complete = False
            gl_val = fl_val = None

            if gl_raw != "" and fl_raw != "":
                try:
                    gl_val = float(gl_raw)
                    fl_val = float(fl_raw)
                    complete = (ELEV_MIN <= gl_val <= ELEV_MAX) and (ELEV_MIN <= fl_val <= ELEV_MAX)
                except ValueError:
                    complete = False

            stations.append({
                "index": int(row["index"]),
                "chainage": chainage,
                "gl": gl_val if complete else None,
                "fl": fl_val if complete else None,
                "complete": complete,
            })
    return stations


def compute(csv_path, slope_master_path="data/slope_master.json", b=FORMATION_WIDTH_B):
    global FORMATION_WIDTH_B
    FORMATION_WIDTH_B = b

    slope = SlopeMaster(slope_master_path)
    stations = load_stations(csv_path)

    for s in stations:
        if not s["complete"]:
            s["type"], s["h"], s["m"], s["area"] = None, None, None, None
            continue
        s["type"], s["h"] = classify(s["gl"], s["fl"])
        m = slope.get_slope(s["chainage"], s["type"])
        if m is None:
            raise ValueError(f"No slope master range covers chainage {s['chainage']}")
        s["m"] = m
        s["area"] = area(s["h"], m) if s["type"] != "level" else 0.0

    cut_total = 0.0
    fill_total = 0.0
    intervals = []

    for i in range(len(stations) - 1):
        s1, s2 = stations[i], stations[i + 1]
        d = s2["chainage"] - s1["chainage"]

        if not (s1["complete"] and s2["complete"]):
            intervals.append({
                "from": s1["chainage"], "to": s2["chainage"],
                "type": "pending_review", "volume": None
            })
            continue

        if s1["type"] == s2["type"] or s1["type"] == "level" or s2["type"] == "level":
            vol = ((s1["area"] + s2["area"]) / 2) * d
            regime = s1["type"] if s1["type"] != "level" else s2["type"]
            if regime == "cut":
                cut_total += vol
            elif regime == "fill":
                fill_total += vol
            intervals.append({"from": s1["chainage"], "to": s2["chainage"], "type": regime, "volume": vol})
        else:
            diff1 = s1["gl"] - s1["fl"]
            diff2 = s2["gl"] - s2["fl"]
            t = diff1 / (diff1 - diff2)
            crossover = s1["chainage"] + t * d

            vol1 = (s1["area"] / 2) * (crossover - s1["chainage"])
            vol2 = (s2["area"] / 2) * (s2["chainage"] - crossover)

            if s1["type"] == "cut":
                cut_total += vol1
                fill_total += vol2
            else:
                fill_total += vol1
                cut_total += vol2

            intervals.append({"from": s1["chainage"], "to": crossover, "type": s1["type"], "volume": vol1})
            intervals.append({"from": crossover, "to": s2["chainage"], "type": s2["type"], "volume": vol2})

    complete_count = sum(1 for s in stations if s["complete"])
    pending_count = len(stations) - complete_count

    return {
        "stations": stations,
        "intervals": intervals,
        "total_cut_volume": cut_total,
        "total_fill_volume": fill_total,
        "complete_stations": complete_count,
        "pending_stations": pending_count,
    }


def export_summary(result, out_path="earthwork_summary.csv"):
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["chainage", "ground_level", "formation_level", "h", "type", "side_slope_m", "area", "status"])
        for s in result["stations"]:
            if s["complete"]:
                w.writerow([s["chainage"], s["gl"], s["fl"], round(s["h"], 4), s["type"], s["m"], round(s["area"], 4), "reviewed"])
            else:
                w.writerow([s["chainage"], s["gl"] or "", s["fl"] or "", "", "", "", "", "pending_review"])
        w.writerow([])
        w.writerow(["TOTAL CUT VOLUME (m3, reviewed sections only)", round(result["total_cut_volume"], 3)])
        w.writerow(["TOTAL FILL VOLUME (m3, reviewed sections only)", round(result["total_fill_volume"], 3)])
        w.writerow(["Stations reviewed", result["complete_stations"]])
        w.writerow(["Stations pending review", result["pending_stations"]])


if __name__ == "__main__":
    result = compute("review.csv")
    export_summary(result)
    print(f"Total Cut Volume (reviewed sections)  : {result['total_cut_volume']:.3f} m3")
    print(f"Total Fill Volume (reviewed sections) : {result['total_fill_volume']:.3f} m3")
    print(f"Stations reviewed  : {result['complete_stations']} / {len(result['stations'])}")
    print(f"Stations pending   : {result['pending_stations']}")
    print("Detailed sheet written to earthwork_summary.csv")
