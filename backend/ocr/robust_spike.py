import numpy as np

def robust_trend_flag(vals, threshold=8.0, window=15, min_inliers=5, iterations=3):
    flags = {}
    for c in sorted(vals.keys()):
        if vals.get(c) is None:
            continue
        lo, hi = c - window, c + window
        local = {cc: vals[cc] for cc in range(lo, hi + 1) if cc != c and vals.get(cc) is not None}
        if len(local) < min_inliers:
            continue
        xs = np.array(list(local.keys()), dtype=float)
        ys = np.array(list(local.values()), dtype=float)
        for _ in range(iterations):
            if len(xs) < min_inliers:
                break
            coef = np.polyfit(xs, ys, 1)
            resid = np.abs(ys - np.polyval(coef, xs))
            mad = np.median(resid) + 1e-6
            keep = resid < 3 * mad
            if keep.all():
                break
            xs, ys = xs[keep], ys[keep]
        if len(xs) < min_inliers:
            continue
        coef = np.polyfit(xs, ys, 1)
        expected = np.polyval(coef, c)
        if abs(vals[c] - expected) > threshold:
            flags[c] = (vals[c], round(float(expected), 3))
    return flags
