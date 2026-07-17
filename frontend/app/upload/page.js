"use client";

import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { useProject } from "@/lib/project-context";

function ResultView({ result }) {
  if (result == null) return null;
  if (typeof result !== "object") {
    return <div className="msg ok">{String(result)}</div>;
  }
  return (
    <div style={{ marginTop: 14 }}>
      <table>
        <tbody>
          {Object.entries(result).map(([k, v]) => (
            <tr key={k}>
              <td style={{ color: "var(--ink-faint)" }}>{k}</td>
              <td className="num">
                {typeof v === "object" ? JSON.stringify(v) : String(v)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function UploadPage() {
  const { projectId: ctxProjectId } = useProject();
  const [projectId, setProjectId] = useState(String(ctxProjectId));
  const [chainageStart, setChainageStart] = useState("");
  const [chainageStep, setChainageStep] = useState("20");
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | working | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    setProjectId(String(ctxProjectId));
  }, [ctxProjectId]);

  function pickFile(f) {
    if (!f) return;
    if (f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are accepted.");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function onSubmit() {
    if (!file) {
      setError("Choose a scanned L-section PDF first.");
      return;
    }
    const pid = parseInt(projectId, 10);
    if (Number.isNaN(pid)) {
      setError("Project ID must be a number.");
      return;
    }
    const chStart = parseFloat(chainageStart);
    if (Number.isNaN(chStart)) {
      setError(
        "Chainage start is required — read it off the drawing's title block, it can't be reliably auto-detected from the scan."
      );
      return;
    }
    const chStep = parseFloat(chainageStep) || 20;
    setStatus("working");
    setError(null);
    setResult(null);
    try {
      const res = await api.uploadPdf(pid, file, chStart, chStep);
      setResult(res);
      setStatus("done");
    } catch (e) {
      setError(e.message);
      setStatus("error");
    }
  }

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>Upload scanned L-section</h2>
          <span className="hint">
            runs OCR extraction · does not touch ChainageProfile until you
            run the calculation
          </span>
        </div>
        <div className="panel-body">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              pickFile(e.dataTransfer.files?.[0]);
            }}
            onClick={() => inputRef.current?.click()}
            style={{
              border: `1px dashed ${dragOver ? "var(--cut)" : "var(--line-strong)"}`,
              background: dragOver ? "var(--cut-soft)" : "var(--paper-inset)",
              padding: "36px 20px",
              textAlign: "center",
              cursor: "pointer",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              color: "var(--ink-dim)",
            }}
          >
            {file ? (
              <span style={{ color: "var(--ink)" }}>{file.name}</span>
            ) : (
              <span>Drag a PDF here, or click to browse</span>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              style={{ display: "none" }}
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
          </div>

          <div className="form-row" style={{ marginTop: 16 }}>
            <div className="form-field">
              <span className="k">Project ID</span>
              <input
                type="number"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
              />
            </div>
            <div className="form-field">
              <span className="k">Chainage start (m)</span>
              <input
                type="number"
                placeholder="e.g. 79980"
                value={chainageStart}
                onChange={(e) => setChainageStart(e.target.value)}
              />
            </div>
            <div className="form-field">
              <span className="k">Chainage step (m)</span>
              <input
                type="number"
                value={chainageStep}
                onChange={(e) => setChainageStep(e.target.value)}
                style={{ width: 70 }}
              />
            </div>
            <button
              className="btn primary"
              onClick={onSubmit}
              disabled={status === "working"}
            >
              {status === "working" ? "Running OCR…" : "Upload & run OCR"}
            </button>
          </div>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--ink-faint)",
              marginTop: 10,
            }}
          >
            Chainage start can&apos;t be reliably read from the scan itself —
            enter it from the drawing&apos;s title block. Only drawings
            using the same L-section table layout as the 80–85 km section
            will extract correctly.
          </p>

          {status === "working" && (
            <div className="loading">
              Processing scanned drawing — this can take a while for a
              multi-page PDF.
            </div>
          )}
          {error && <div className="msg err">{error}</div>}
          {status === "done" && (
            <div className="msg ok">OCR pipeline finished.</div>
          )}
          <ResultView result={result} />
        </div>
      </section>
    </>
  );
}
