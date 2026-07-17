import json


class SlopeMaster:
    """
    Maps a chainage to its side-slope value 'm' using engineer-defined
    ranges (FR-06). Backed by a JSON file; same interface can be backed
    by a real DB table without changing calc_engine.py (see
    routes/calculation.py's _sync_slope_master_file).

    Cut and fill use separate side-slope values (confirmed by
    reviewer), so each range now carries both 'side_slope_cut' and
    'side_slope_fill' rather than a single value.
    """

    def __init__(self, path="data/slope_master.json"):
        self.path = path
        self.ranges = []
        self.load()

    def load(self):
        with open(self.path) as f:
            self.ranges = json.load(f)
        self.ranges.sort(key=lambda r: r["from_chainage"])

    def get_slope(self, chainage, slope_type=None):
        """
        slope_type: 'cut', 'fill', or 'level'/None. 'level' stations
        have h=0 so the slope value is never actually used in the area
        formula - any non-None return is fine to satisfy the coverage
        check in calc_engine.py, so 'level' falls back to the cut value.
        """
        for r in self.ranges:
            if r["from_chainage"] <= chainage <= r["to_chainage"]:
                if slope_type == "fill":
                    return r.get("side_slope_fill")
                return r.get("side_slope_cut")
        return None

    def missing_coverage(self, chainages):
        return [c for c in chainages if self.get_slope(c, "cut") is None]
