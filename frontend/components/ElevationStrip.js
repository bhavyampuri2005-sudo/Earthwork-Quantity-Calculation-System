"use client";

import { useMemo, useState } from "react";

const W = 1160;
const H = 300;
const PAD = { top: 18, right: 16, bottom: 34, left: 56 };

export default function ElevationStrip({ rows }) {
  const [hover, setHover] = useState(null);

  const model = useMemo(() => {
    if (!rows || rows.length === 0) return null;

    const valid = rows.filter((r) => r.gl != null && r.fl != null);
    if (valid.length < 2) return null;

    const chMin = rows[0].chainage;
    const chMax = rows[rows.length - 1].chainage;
    let elMin = Infinity;
    let elMax = -Infinity;
    for (const r of valid) {
      elMin = Math.min(elMin, r.gl, r.fl);
      elMax = Math.max(elMax, r.gl, r.fl);
    }
    const elPadding = Math.max((elMax - elMin) * 0.12, 1);
    elMin -= elPadding;
    elMax += elPadding;

    const x = (ch) =>
      PAD.left + ((ch - chMin) / (chMax - chMin)) * (W - PAD.left - PAD.right);
    const y = (el) =>
      PAD.top + ((elMax - el) / (elMax - elMin)) * (H - PAD.top - PAD.bottom);

    // Build polyline segments only across consecutive valid stations,
    // so lines break (rather than bridge) across pending gaps.
    const glSegs = [];
    const flSegs = [];
    const bands = []; // cut / fill quads between consecutive valid stations
    let curGl = [];
    let curFl = [];

    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      const ok = r.gl != null && r.fl != null;
      if (ok) {
        curGl.push(`${x(r.chainage)},${y(r.gl)}`);
        curFl.push(`${x(r.chainage)},${y(r.fl)}`);
        const nxt = rows[i + 1];
        if (nxt && nxt.gl != null && nxt.fl != null) {
          const type =
            r.gl - r.fl > 1e-6 || nxt.gl - nxt.fl > 1e-6
              ? r.gl >= r.fl
                ? "cut"
                : "fill"
              : "fill";
          bands.push({
            type: r.gl >= r.fl ? "cut" : "fill",
            points: [
              `${x(r.chainage)},${y(r.gl)}`,
              `${x(nxt.chainage)},${y(nxt.gl)}`,
              `${x(nxt.chainage)},${y(nxt.fl)}`,
              `${x(r.chainage)},${y(r.fl)}`,
            ].join(" "),
          });
        }
      } else {
        if (curGl.length > 1) {
          glSegs.push(curGl.join(" "));
          flSegs.push(curFl.join(" "));
        }
        curGl = [];
        curFl = [];
      }
    }
    if (curGl.length > 1) {
      glSegs.push(curGl.join(" "));
      flSegs.push(curFl.join(" "));
    }

    // Pending spans: consecutive runs of rows with missing gl/fl
    const gaps = [];
    let gapStart = null;
    for (let i = 0; i < rows.length; i++) {
      const ok = rows[i].gl != null && rows[i].fl != null;
      if (!ok && gapStart === null) gapStart = i;
      if (ok && gapStart !== null) {
        gaps.push([rows[gapStart].chainage, rows[i].chainage]);
        gapStart = null;
      }
    }
    if (gapStart !== null)
      gaps.push([rows[gapStart].chainage, rows[rows.length - 1].chainage]);

    // Elevation gridlines: ~5 round values
    const gridStep = niceStep((elMax - elMin) / 5);
    const gridLines = [];
    for (
      let g = Math.ceil(elMin / gridStep) * gridStep;
      g < elMax;
      g += gridStep
    ) {
      gridLines.push(g);
    }

    // Chainage ticks every km
    const ticks = [];
    const kmStep = 1000;
    for (
      let c = Math.ceil(chMin / kmStep) * kmStep;
      c <= chMax;
      c += kmStep
    ) {
      ticks.push(c);
    }

    return { x, y, chMin, chMax, glSegs, flSegs, bands, gaps, gridLines, ticks };
  }, [rows]);

  if (!model) {
    return (
      <div className="loading">
        Not enough reviewed stations to draw the profile yet.
      </div>
    );
  }

  const { x, y, glSegs, flSegs, bands, gaps, gridLines, ticks } = model;

  function onMove(e) {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    // nearest station by x
    let best = null;
    let bestDist = Infinity;
    for (const r of rows) {
      const d = Math.abs(x(r.chainage) - px);
      if (d < bestDist) {
        bestDist = d;
        best = r;
      }
    }
    setHover(best);
  }

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "auto", display: "block" }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label="Longitudinal profile: ground level and formation level with cut and fill zones"
      >
        <defs>
          <pattern
            id="pendingHatch"
            width="6"
            height="6"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="6" height="6" fill="rgba(226,87,76,0.06)" />
            <line x1="0" y1="0" x2="0" y2="6" stroke="#e2574c" strokeWidth="1" strokeOpacity="0.45" />
          </pattern>
        </defs>

        {/* pending-review hatched spans */}
        {gaps.map(([a, b], i) => (
          <rect
            key={i}
            x={x(a)}
            y={PAD.top}
            width={Math.max(x(b) - x(a), 2)}
            height={H - PAD.top - PAD.bottom}
            fill="url(#pendingHatch)"
          />
        ))}

        {/* elevation gridlines */}
        {gridLines.map((g) => (
          <g key={g}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(g)}
              y2={y(g)}
              stroke="#24395c"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 8}
              y={y(g) + 4}
              textAnchor="end"
              fontSize="10"
              fontFamily="IBM Plex Mono, monospace"
              fill="#5d7288"
            >
              {g}
            </text>
          </g>
        ))}

        {/* cut / fill bands */}
        {bands.map((b, i) => (
          <polygon
            key={i}
            points={b.points}
            fill={b.type === "cut" ? "rgba(224,166,58,0.35)" : "rgba(79,195,176,0.35)"}
          />
        ))}

        {/* FL then GL lines */}
        {flSegs.map((pts, i) => (
          <polyline
            key={`fl${i}`}
            points={pts}
            fill="none"
            stroke="#9db2c8"
            strokeWidth="1.4"
            strokeDasharray="5 3"
          />
        ))}
        {glSegs.map((pts, i) => (
          <polyline
            key={`gl${i}`}
            points={pts}
            fill="none"
            stroke="#eaf1f8"
            strokeWidth="1.8"
          />
        ))}

        {/* chainage ticks */}
        {ticks.map((c) => (
          <g key={c}>
            <line
              x1={x(c)}
              x2={x(c)}
              y1={H - PAD.bottom}
              y2={H - PAD.bottom + 6}
              stroke="#5d7288"
            />
            <text
              x={x(c)}
              y={H - PAD.bottom + 20}
              textAnchor="middle"
              fontSize="10"
              fontFamily="IBM Plex Mono, monospace"
              fill="#5d7288"
            >
              {(c / 1000).toFixed(0)} km
            </text>
          </g>
        ))}

        {/* hover crosshair */}
        {hover && (
          <g>
            <line
              x1={x(hover.chainage)}
              x2={x(hover.chainage)}
              y1={PAD.top}
              y2={H - PAD.bottom}
              stroke="#e0a63a"
              strokeWidth="1"
              strokeDasharray="2 3"
            />
          </g>
        )}
      </svg>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 12,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div className="legend">
          <span className="lg-gl">GL ground</span>
          <span className="lg-fl">FL formation</span>
          <span className="lg-cut">cut</span>
          <span className="lg-fill">fill</span>
          <span className="lg-pending">pending review</span>
        </div>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            color: "var(--ink-dim)",
            minHeight: 18,
          }}
        >
          {hover
            ? `CH ${hover.chainage.toFixed(0)}  ·  GL ${
                hover.gl != null ? hover.gl.toFixed(3) : "—"
              }  ·  FL ${hover.fl != null ? hover.fl.toFixed(3) : "—"}`
            : "hover the profile to inspect a station"}
        </div>
      </div>
    </div>
  );
}

function niceStep(raw) {
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / pow;
  if (n < 1.5) return pow;
  if (n < 3.5) return 2 * pow;
  if (n < 7.5) return 5 * pow;
  return 10 * pow;
}
