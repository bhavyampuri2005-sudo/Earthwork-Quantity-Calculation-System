"use client";

import { useCallback, useEffect, useState } from "react";
import * as XLSX from "xlsx";
import api from "@/lib/api";
import ElevationStrip from "@/components/ElevationStrip";
import { useProject } from "@/lib/project-context";

function fmtVolume(v) {
  if (v == null) return "—";
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
  return v.toFixed(1);
}

export default function Dashboard() {
  const { projectId: PROJECT_ID } = useProject();
  const [rows, setRows] = useState(null);
  const [calc, setCalc] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [chainage, calculation] = await Promise.all([
        api.getChainage(PROJECT_ID),
        api.getCalculation(PROJECT_ID).catch(() => null),
      ]);
      setRows(chainage);
      setCalc(calculation);
    } catch (e) {
      setError(e.message);
    }
  }, [PROJECT_ID]);

  useEffect(() => {
    load();
  }, [load]);

  async function onRun() {
    setRunning(true);
    setRunMsg(null);
    try {
      const res = await api.runCalculation(PROJECT_ID);
      setRunMsg({
        kind: "ok",
        text: `Recalculated: ${res.stations_saved} stations, ${res.intervals_saved} intervals saved.`,
      });
      await load();
    } catch (e) {
      setRunMsg({ kind: "err", text: e.message });
    } finally {
      setRunning(false);
    }
  }

  function downloadReport() {
    if (!rows) return;

    const stationRows = rows.map((r) => ({
      Chainage: r.chainage,
      "Ground Level (m)": r.gl ?? "",
      "Formation Level (m)": r.fl ?? "",
      "Cut Depth (m)": r.cut ?? 0,
      "Fill Depth (m)": r.fill ?? 0,
      Status: r.gl != null && r.fl != null ? "Reviewed" : "Pending Review",
    }));

    const reviewedCount = rows.filter((r) => r.gl != null && r.fl != null).length;
    const summaryRows = [
      { Metric: "Project ID", Value: PROJECT_ID },
      { Metric: "Generated", Value: new Date().toISOString() },
      { Metric: "Total Stations", Value: rows.length },
      { Metric: "Stations Reviewed", Value: reviewedCount },
      { Metric: "Stations Pending Review", Value: rows.length - reviewedCount },
      { Metric: "Total Cut Volume (m3, reviewed sections only)", Value: calc?.total_cut_volume ?? "n/a" },
      { Metric: "Total Fill Volume (m3, reviewed sections only)", Value: calc?.total_fill_volume ?? "n/a" },
      { Metric: "Method", Value: "Average End Area: A = B*h + m*h^2, V = ((A1+A2)/2)*d" },
      { Metric: "Formation Width B (m)", Value: 7.85 },
    ];

    const wb = XLSX.utils.book_new();
    const summarySheet = XLSX.utils.json_to_sheet(summaryRows);
    summarySheet["!cols"] = [{ wch: 42 }, { wch: 28 }];
    XLSX.utils.book_append_sheet(wb, summarySheet, "Summary");

    const stationSheet = XLSX.utils.json_to_sheet(stationRows);
    stationSheet["!cols"] = [
      { wch: 12 }, { wch: 16 }, { wch: 18 }, { wch: 14 }, { wch: 14 }, { wch: 16 },
    ];
    XLSX.utils.book_append_sheet(wb, stationSheet, "Stations");

    XLSX.writeFile(wb, `earthwork_project_${PROJECT_ID}_report.xlsx`);
  }

  const reviewed = rows
    ? rows.filter((r) => r.gl != null && r.fl != null).length
    : null;
  const pending = rows != null ? rows.length - reviewed : null;

  return (
    <>
      {error && (
        <div className="msg err">
          Backend unreachable: {error}. Is uvicorn running on port 8000?
        </div>
      )}

      <div className="stats">
        <div className="stat cut">
          <div className="k">Total cut</div>
          <div className="v">
            {fmtVolume(calc?.total_cut_volume)}
            <span className="u">m³</span>
          </div>
        </div>
        <div className="stat fill">
          <div className="k">Total fill</div>
          <div className="v">
            {fmtVolume(calc?.total_fill_volume)}
            <span className="u">m³</span>
          </div>
        </div>
        <div className="stat">
          <div className="k">Stations reviewed</div>
          <div className="v">
            {reviewed ?? "—"}
            <span className="u">/ {rows?.length ?? "—"}</span>
          </div>
        </div>
        <div className="stat pending">
          <div className="k">Pending review</div>
          <div className="v">{pending ?? "—"}</div>
        </div>
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>Longitudinal profile</h2>
          <span className="hint">redrawn from OCR-extracted stations</span>
        </div>
        <div className="panel-body">
          {rows ? (
            <ElevationStrip rows={rows} />
          ) : (
            <div className="loading">loading stations…</div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Recalculate volumes</h2>
          <span className="hint">
            replaces this project&apos;s previous run — safe to repeat
          </span>
        </div>
        <div className="panel-body">
          <p
            style={{
              color: "var(--ink-dim)",
              fontSize: 14,
              marginBottom: 14,
              maxWidth: 640,
            }}
          >
            Re-runs the Average End Area calculation against the current
            review CSV, using side slopes from the Slope Master table.
            Totals cover reviewed stations only; pending intervals are
            excluded until approved.
          </p>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn primary" onClick={onRun} disabled={running}>
              {running ? "Calculating…" : "Run calculation"}
            </button>
            <button className="btn" onClick={downloadReport} disabled={!rows}>
              Download report (.xlsx)
            </button>
          </div>
          {runMsg && <div className={`msg ${runMsg.kind}`}>{runMsg.text}</div>}
        </div>
      </section>
    </>
  );
}
