import re


class OCRParser:

    # Row order per the drawing + Ishan's correction.
    # Bands confirmed from ocr_results.json:
    #   row 6 -> ~374  formation
    #   row 7 -> ~373  rail
    #   row 8 -> ~365  GROUND (the real ground level)
    #   row 9 -> 80xxx chainage
    # Previously ground_level was mapped to row 6 (~374 = formation), which
    # made GL > FL every row -> always cut -> fill=0. Fixed below.
    KNOWN = {
        "cut_fill": 4,
        "formation_level": 6,
        "rail_level": 5,
        "ground_level": 7,
        "field_chainage": 8,
    }

    def __init__(self):
        pass

    # ------------------------------------------------
    # r10_c25.png -> (10, 25)
    # ------------------------------------------------
    def parse_filename(self, filename):
        match = re.match(r"r(\d+)_c(\d+)\.png", filename)
        if match is None:
            return None
        return int(match.group(1)), int(match.group(2))

    # ------------------------------------------------
    # Group by row, columns sorted numerically
    # ------------------------------------------------
    def group_by_row(self, ocr_results):
        grouped = {}
        for filename, value in ocr_results.items():
            parsed = self.parse_filename(filename)
            if parsed is None:
                continue
            row, col = parsed
            grouped.setdefault(row, {})[col] = value
        for row in grouped:
            grouped[row] = dict(sorted(grouped[row].items()))
        return grouped

    # ------------------------------------------------
    # Clean dirty OCR:
    #   "374.995-"  -> 374.995   (trailing minus = artifact)
    #   "80140 7"   -> 801407.0  (space = merged cell, flagged as outlier)
    #   "+"         -> None
    #   "1."        -> 1.0
    # ------------------------------------------------
    def clean_value(self, value):
        if value is None:
            return None
        s = str(value).strip().replace(" ", "")
        s = re.sub(r"[^0-9.\-]", "", s)      # keep only digits . -
        neg = s.startswith("-")               # keep only a leading minus
        s = s.replace("-", "")
        if neg:
            s = "-" + s
        if s.count(".") > 1 or s in ("", ".", "-", "-."):
            return None
        try:
            return float(s)
        except ValueError:
            return None

    # ------------------------------------------------
    # Per-row stats (in column order)
    # ------------------------------------------------
    def _row_stats(self, cells):
        cols = sorted(cells.keys())
        nums = [v for v in (self.clean_value(cells[c]) for c in cols) if v is not None]
        if not nums:
            return {"count": 0, "median": None, "median_abs": None, "mono": 0.0}
        s = sorted(nums)
        median = s[len(s) // 2]
        median_abs = sorted(abs(x) for x in nums)[len(nums) // 2]
        inc = sum(1 for a, b in zip(nums, nums[1:]) if b > a)
        mono = inc / max(1, len(nums) - 1)
        return {"count": len(nums), "median": median,
                "median_abs": median_abs, "mono": round(mono, 2)}

    # ------------------------------------------------
    # Map engineering rows (known positions + validation)
    # ------------------------------------------------
    def assign_engineering_rows(self, grouped_rows):
        print("\n" + "=" * 60)
        print("ROW MAPPING (known positions + shape check)")
        print("=" * 60)

        mapping = {}
        for name, row_idx in self.KNOWN.items():
            if row_idx not in grouped_rows:
                print(f"  MISSING row {row_idx} for {name}")
                continue

            mapping[name] = row_idx
            st = self._row_stats(grouped_rows[row_idx])

            # sanity check per field.
            # Bands are segment-specific (80-85km); widen if a later segment
            # legitimately falls outside these. A WARN is a flag, not a filter.
            flag = "ok"
            if name == "field_chainage":
                if not (st["mono"] >= 0.8 and (st["median"] or 0) > 1000):
                    flag = "WARN (expected large, increasing)"
            elif name == "cut_fill":
                if st["median_abs"] is not None and st["median_abs"] > 50:
                    flag = "WARN (expected small values)"
            elif name == "formation_level":
                m = st["median"]
                if m is not None and not (350 <= m <= 380):
                    flag = "WARN (formation expected ~374)"
            elif name == "rail_level":
                m = st["median"]
                if m is not None and not (350 <= m <= 380):
                    flag = "WARN (rail expected ~373)"
            elif name == "ground_level":
                m = st["median"]
                if m is not None and not (340 <= m <= 372):
                    flag = "WARN (ground expected ~365, below formation)"
            else:
                m = st["median"]
                if m is not None and not (20 <= m <= 600):
                    flag = "WARN (expected ~100-400)"

            print(f"  {name:<16} -> row {row_idx}  "
                  f"count={st['count']:<4} median={st['median']}  "
                  f"mono={st['mono']}  [{flag}]")

        print("=" * 60 + "\n")
        return mapping

    # ------------------------------------------------
    # Build records
    # ------------------------------------------------
    def build_records(self, grouped_rows, mapping):
        records = []
        chainage_row = grouped_rows[mapping["field_chainage"]]

        for col in sorted(chainage_row.keys()):
            record = {
                "chainage": self.clean_value(
                    grouped_rows[mapping["field_chainage"]].get(col)),
                "ground_level": self.clean_value(
                    grouped_rows[mapping["ground_level"]].get(col)),
                "formation_level": self.clean_value(
                    grouped_rows[mapping["formation_level"]].get(col)),
                "rail_level": self.clean_value(
                    grouped_rows[mapping["rail_level"]].get(col)),
                "cut_fill": self.clean_value(
                    grouped_rows[mapping["cut_fill"]].get(col)),
            }
            records.append(record)

        return records

    # kept for backward compatibility
    def to_number(self, value):
        return self.clean_value(value)
