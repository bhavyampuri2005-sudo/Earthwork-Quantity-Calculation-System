"use client";

import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { useProject } from "@/lib/project-context";

export default function ReviewPage() {
  const { projectId: PROJECT_ID } = useProject();
  const [rows, setRows] = useState(null);
  const [reviewStatus, setReviewStatus] = useState(null); // Map: chainage -> {status, reason}
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all"); // all | flagged | ready | approved
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState({ gl: "", fl: "" });
  const [saveMsg, setSaveMsg] = useState(null);
  const [validating, setValidating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [reviewerName, setReviewerName] = useState("");

  function loadReviewStatus() {
    api
      .getReviewStatus(PROJECT_ID)
      .then((res) => {
        const map = new Map();
        (res.rows || []).forEach((r) => map.set(r.chainage, r));
        setReviewStatus(map);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    api
      .getChainage(PROJECT_ID)
      .then(setRows)
      .catch((e) => setError(e.message));
    loadReviewStatus();
  }, [PROJECT_ID]);

  async function handleAutoValidate() {
    setValidating(true);
    setSaveMsg(null);
    try {
      const res = await api.autoValidate(PROJECT_ID);
      loadReviewStatus();
      setSaveMsg({
        kind: "ok",
        text: `Auto-validate: ${res.pending} ready to approve, ${res.flagged} flagged for review.`,
      });
    } catch (e) {
      setSaveMsg({ kind: "err", text: e.message });
    } finally {
      setValidating(false);
    }
  }

  async function handleBulkApprove() {
    setApproving(true);
    setSaveMsg(null);
    try {
      const res = await api.bulkApprove(PROJECT_ID, reviewerName || null);
      loadReviewStatus();
      setSaveMsg({ kind: "ok", text: `${res.approved} rows approved.` });
    } catch (e) {
      setSaveMsg({ kind: "err", text: e.message });
    } finally {
      setApproving(false);
    }
  }

  // Merge chainage data with review status by chainage. A row has no
  // reviewStatus until Run auto-validate has executed at least once
  // for this project.
  const merged = useMemo(() => {
    if (!rows) return null;
    return rows.map((r) => {
      const rv = reviewStatus ? reviewStatus.get(r.chainage) : null;
      return {
        ...r,
        reviewStatus: rv ? rv.status : null,
        reviewReason: rv ? rv.reason : null,
      };
    });
  }, [rows, reviewStatus]);

  const shown = useMemo(() => {
    if (!merged) return null;
    if (filter === "flagged") return merged.filter((r) => r.reviewStatus === "flagged");
    if (filter === "ready") return merged.filter((r) => r.reviewStatus === "pending");
    if (filter === "approved") return merged.filter((r) => r.reviewStatus === "approved");
    return merged;
  }, [merged, filter]);

  function startEdit(row) {
    setEditing(row.id);
    setDraft({
      gl: row.gl != null ? String(row.gl) : "",
      fl: row.fl != null ? String(row.fl) : "",
    });
    setSaveMsg(null);
  }

  async function saveEdit(row) {
    const gl = parseFloat(draft.gl);
    const fl = parseFloat(draft.fl);
    if (Number.isNaN(gl) || Number.isNaN(fl)) {
      setSaveMsg({ kind: "err", text: "GL and FL must both be numbers." });
      return;
    }
    const diff = gl - fl;
    const cut = diff > 0 ? diff : 0;
    const fill = diff < 0 ? -diff : 0;
    try {
      await api.updateChainage(row.id, {
        project_id: PROJECT_ID,
        chainage: row.chainage,
        gl,
        fl,
        cut,
        fill,
      });
      setRows((prev) =>
        prev.map((r) => (r.id === row.id ? { ...r, gl, fl, cut, fill } : r))
      );
      setEditing(null);
      setSaveMsg({
        kind: "ok",
        text: `CH ${row.chainage.toFixed(0)} updated. Note: totals recompute from the review CSV — mirror this correction there before the final run. Re-run auto-validate to refresh this row's review status.`,
      });
    } catch (e) {
      setSaveMsg({ kind: "err", text: e.message });
    }
  }

  const flaggedCount = merged ? merged.filter((r) => r.reviewStatus === "flagged").length : 0;
  const readyCount = merged ? merged.filter((r) => r.reviewStatus === "pending").length : 0;
  const approvedCount = merged ? merged.filter((r) => r.reviewStatus === "approved").length : 0;

  return (
    <>
      {error && <div className="msg err">Backend unreachable: {error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Station review — {rows ? rows.length : "…"} stations</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button
              className="btn"
              onClick={handleAutoValidate}
              disabled={validating || approving}
            >
              {validating ? "Validating…" : "Run auto-validate"}
            </button>
            <input
              className="cell-edit"
              placeholder="Reviewer name"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              style={{ width: 120 }}
            />
            <button
              className="btn"
              onClick={handleBulkApprove}
              disabled={approving || validating || readyCount === 0}
            >
              {approving ? "Approving…" : `Bulk approve (${readyCount})`}
            </button>
          </div>
        </div>

        <div className="panel-head" style={{ paddingTop: 0 }}>
          <div style={{ display: "flex", gap: 8 }}>
            {[
              { key: "all", label: "all" },
              { key: "flagged", label: `flagged (${flaggedCount})` },
              { key: "ready", label: `ready to approve (${readyCount})` },
              { key: "approved", label: `approved (${approvedCount})` },
            ].map((f) => (
              <button
                key={f.key}
                className="btn"
                style={
                  filter === f.key
                    ? { borderColor: "var(--cut)", color: "var(--cut)" }
                    : undefined
                }
                onClick={() => setFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {saveMsg && (
          <div style={{ padding: "0 20px" }}>
            <div className={`msg ${saveMsg.kind}`}>{saveMsg.text}</div>
          </div>
        )}

        <div className="table-wrap" style={{ marginTop: 8 }}>
          {!shown ? (
            <div className="loading">loading stations…</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Chainage</th>
                  <th>GL (m)</th>
                  <th>FL (m)</th>
                  <th>Cut h (m)</th>
                  <th>Fill h (m)</th>
                  <th>Review status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => {
                  const isEditing = editing === r.id;
                  return (
                    <tr key={r.id} className={r.reviewStatus === "flagged" ? "row-pending" : ""}>
                      <td className="num">{r.chainage.toFixed(0)}</td>
                      <td className="num">
                        {isEditing ? (
                          <input
                            className="cell-edit"
                            type="number"
                            step="0.001"
                            value={draft.gl}
                            onChange={(e) =>
                              setDraft((d) => ({ ...d, gl: e.target.value }))
                            }
                          />
                        ) : r.gl != null ? (
                          r.gl.toFixed(3)
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="num">
                        {isEditing ? (
                          <input
                            className="cell-edit"
                            type="number"
                            step="0.001"
                            value={draft.fl}
                            onChange={(e) =>
                              setDraft((d) => ({ ...d, fl: e.target.value }))
                            }
                          />
                        ) : r.fl != null ? (
                          r.fl.toFixed(3)
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>{r.cut > 0 ? r.cut.toFixed(3) : ""}</td>
                      <td>{r.fill > 0 ? r.fill.toFixed(3) : ""}</td>
                      <td>
                        {r.reviewStatus === "approved" && (
                          <span className="pill ok">approved</span>
                        )}
                        {r.reviewStatus === "flagged" && (
                          <span className="pill pending" title={r.reviewReason || ""}>
                            flagged
                          </span>
                        )}
                        {r.reviewStatus === "pending" && (
                          <span className="pill ok" style={{ opacity: 0.7 }}>
                            ready to approve
                          </span>
                        )}
                        {r.reviewStatus == null && (
                          <span className="pill pending" style={{ opacity: 0.5 }}>
                            not validated
                          </span>
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <span style={{ display: "flex", gap: 6 }}>
                            <button
                              className="btn"
                              style={{ padding: "3px 10px" }}
                              onClick={() => saveEdit(r)}
                            >
                              Save
                            </button>
                            <button
                              className="btn"
                              style={{ padding: "3px 10px" }}
                              onClick={() => setEditing(null)}
                            >
                              Cancel
                            </button>
                          </span>
                        ) : (
                          <button
                            className="btn"
                            style={{ padding: "3px 10px" }}
                            onClick={() => startEdit(r)}
                          >
                            Edit
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </>
  );
}
