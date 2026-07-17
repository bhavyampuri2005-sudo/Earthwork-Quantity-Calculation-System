"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useProject } from "@/lib/project-context";

const ACTION_LABELS = {
  calculation_run: "Calculation run",
  pdf_uploaded: "PDF uploaded",
  ocr_completed: "OCR completed",
  ocr_failed: "OCR failed",
  slope_range_added: "Slope range added",
  station_edited: "Station edited",
};

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString();
}

function DetailSummary({ action, detailsRaw }) {
  let details;
  try {
    details = JSON.parse(detailsRaw);
  } catch {
    return <span>{detailsRaw}</span>;
  }
  if (action === "calculation_run") {
    return (
      <span>
        {details.stations_reviewed}/{details.stations_saved} reviewed · cut{" "}
        {details.total_cut_volume} m³ · fill {details.total_fill_volume} m³
      </span>
    );
  }
  if (action === "station_edited") {
    return (
      <span>
        CH {details.chainage} → GL {details.gl}, FL {details.fl}
      </span>
    );
  }
  if (action === "slope_range_added") {
    return (
      <span>
        {details.from_chainage}–{details.to_chainage}: cut {details.side_slope_cut}, fill{" "}
        {details.side_slope_fill}
      </span>
    );
  }
  if (action === "pdf_uploaded" || action === "ocr_failed") {
    return <span>{details.filename}</span>;
  }
  if (action === "ocr_completed") {
    return (
      <span>
        {details.clean_prefilled}/{details.total_stations} clean on first pass
      </span>
    );
  }
  return <span>{JSON.stringify(details)}</span>;
}

export default function ActivityPage() {
  const { projectId: PROJECT_ID } = useProject();
  const [log, setLog] = useState(null);
  const [files, setFiles] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    Promise.all([api.getAuditLog(PROJECT_ID), api.getProjectFiles(PROJECT_ID)])
      .then(([l, f]) => {
        setLog(l);
        setFiles(f);
      })
      .catch((e) => setError(e.message));
  }, [PROJECT_ID]);

  return (
    <>
      {error && <div className="msg err">Backend unreachable: {error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Uploaded files</h2>
          <span className="hint">ProjectFiles — upload &amp; processing status</span>
        </div>
        <div className="table-wrap">
          {!files ? (
            <div className="loading">loading…</div>
          ) : files.length === 0 ? (
            <div className="loading">
              No files uploaded through the app yet for this project.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Uploaded</th>
                  <th>Status</th>
                  <th>Chainage range</th>
                  <th>Rows extracted</th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr key={f.id} className={f.status === "failed" ? "row-pending" : ""}>
                    <td>{f.filename}</td>
                    <td>{fmtTime(f.uploaded_at)}</td>
                    <td>
                      <span className={`pill ${f.status === "completed" ? "ok" : f.status === "failed" ? "pending" : "cut"}`}>
                        {f.status}
                      </span>
                    </td>
                    <td className="num">
                      {f.chainage_start != null
                        ? `${f.chainage_start}${f.chainage_step ? ` (+${f.chainage_step})` : ""}`
                        : "—"}
                    </td>
                    <td className="num">{f.rows_extracted ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Audit log</h2>
          <span className="hint">
            actor tracking pending login/RBAC — every entry below is unattributed for now
          </span>
        </div>
        <div className="table-wrap">
          {!log ? (
            <div className="loading">loading…</div>
          ) : log.length === 0 ? (
            <div className="loading">No actions logged yet for this project.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Action</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {log.map((entry) => (
                  <tr key={entry.id}>
                    <td>{fmtTime(entry.created_at)}</td>
                    <td>
                      <span className="pill ok">
                        {ACTION_LABELS[entry.action] || entry.action}
                      </span>
                    </td>
                    <td style={{ color: "var(--ink-dim)", whiteSpace: "normal" }}>
                      <DetailSummary action={entry.action} detailsRaw={entry.details} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </>
  );
}
