"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useProject } from "@/lib/project-context";

export default function SlopesPage() {
  const { projectId: PROJECT_ID } = useProject();
  const [slopes, setSlopes] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    from_chainage: "",
    to_chainage: "",
    side_slope_cut: "",
    side_slope_fill: "",
    remarks: "",
  });
  const [msg, setMsg] = useState(null);
  const [saving, setSaving] = useState(false);

  function load() {
    api
      .getSlopes(PROJECT_ID)
      .then(setSlopes)
      .catch((e) => setError(e.message));
  }

  useEffect(load, [PROJECT_ID]);

  async function onAdd() {
    const from = parseFloat(form.from_chainage);
    const to = parseFloat(form.to_chainage);
    const cutSlope = parseFloat(form.side_slope_cut);
    const fillSlope = parseFloat(form.side_slope_fill);
    if ([from, to, cutSlope, fillSlope].some(Number.isNaN)) {
      setMsg({ kind: "err", text: "All four fields must be numbers." });
      return;
    }
    if (to <= from) {
      setMsg({ kind: "err", text: "To-chainage must be greater than from-chainage." });
      return;
    }
    setSaving(true);
    setMsg(null);
    try {
      await api.addSlope({
        project_id: PROJECT_ID,
        from_chainage: from,
        to_chainage: to,
        side_slope_cut: cutSlope,
        side_slope_fill: fillSlope,
        remarks: form.remarks.trim() || null,
      });
      setForm({ from_chainage: "", to_chainage: "", side_slope_cut: "", side_slope_fill: "", remarks: "" });
      setMsg({
        kind: "ok",
        text: "Range added. Run the calculation again for it to take effect.",
      });
      load();
    } catch (e) {
      setMsg({ kind: "err", text: e.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {error && <div className="msg err">Backend unreachable: {error}</div>}

      <section className="panel">
        <div className="panel-head">
          <h2>Slope Master — side slope m by chainage range</h2>
          <span className="hint">A = B·h + m·h² · cut and fill use separate m</span>
        </div>
        <div className="table-wrap">
          {!slopes ? (
            <div className="loading">loading ranges…</div>
          ) : slopes.length === 0 ? (
            <div className="loading">
              No ranges defined. The calculation will refuse to run until at
              least one range covers the alignment.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>From chainage</th>
                  <th>To chainage</th>
                  <th>Cut slope m</th>
                  <th>Fill slope m</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {slopes.map((s) => (
                  <tr key={s.id}>
                    <td className="num">{s.from_chainage.toFixed(0)}</td>
                    <td className="num">{s.to_chainage.toFixed(0)}</td>
                    <td className="num" style={{ color: "var(--cut)" }}>
                      {s.side_slope_cut}
                    </td>
                    <td className="num" style={{ color: "var(--fill)" }}>
                      {s.side_slope_fill}
                    </td>
                    <td style={{ color: "var(--ink-dim)", whiteSpace: "normal" }}>
                      {s.remarks || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Add range</h2>
        </div>
        <div className="panel-body">
          <div className="form-row">
            <div className="form-field">
              <span className="k">From chainage</span>
              <input
                type="number"
                value={form.from_chainage}
                onChange={(e) =>
                  setForm((f) => ({ ...f, from_chainage: e.target.value }))
                }
              />
            </div>
            <div className="form-field">
              <span className="k">To chainage</span>
              <input
                type="number"
                value={form.to_chainage}
                onChange={(e) =>
                  setForm((f) => ({ ...f, to_chainage: e.target.value }))
                }
              />
            </div>
            <div className="form-field">
              <span className="k">Cut slope m</span>
              <input
                type="number"
                step="0.1"
                value={form.side_slope_cut}
                onChange={(e) =>
                  setForm((f) => ({ ...f, side_slope_cut: e.target.value }))
                }
                style={{ borderColor: "var(--cut)" }}
              />
            </div>
            <div className="form-field">
              <span className="k">Fill slope m</span>
              <input
                type="number"
                step="0.1"
                value={form.side_slope_fill}
                onChange={(e) =>
                  setForm((f) => ({ ...f, side_slope_fill: e.target.value }))
                }
                style={{ borderColor: "var(--fill)" }}
              />
            </div>
            <div className="form-field">
              <span className="k">Remarks</span>
              <input
                type="text"
                placeholder="e.g. loose soil, rock cut"
                value={form.remarks}
                onChange={(e) =>
                  setForm((f) => ({ ...f, remarks: e.target.value }))
                }
                style={{ width: 180 }}
              />
            </div>
            <button className="btn primary" onClick={onAdd} disabled={saving}>
              {saving ? "Adding…" : "Add range"}
            </button>
          </div>
          {msg && <div className={`msg ${msg.kind}`}>{msg.text}</div>}
        </div>
      </section>
    </>
  );
}
