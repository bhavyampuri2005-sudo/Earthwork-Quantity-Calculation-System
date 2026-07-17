const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}
export const api = {
  getChainage: (projectId) => request(`/chainage/${projectId}`),
  updateChainage: (id, data) =>
    request(`/chainage/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  getSlopes: (projectId) => request(`/slope/${projectId}`),
  addSlope: (data) =>
    request(`/slope`, { method: "POST", body: JSON.stringify(data) }),
  getCalculation: (projectId) => request(`/calculation/${projectId}`),
  runCalculation: (projectId) =>
    request(`/calculation/run`, {
      method: "POST",
      body: JSON.stringify({ project_id: projectId }),
    }),
  uploadPdf: async (projectId, file, chainageStart, chainageStep = 20) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("chainage_start", String(chainageStart));
    formData.append("chainage_step", String(chainageStep));
    const res = await fetch(`${BASE_URL}/upload-pdf/${projectId}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail || JSON.stringify(body);
      } catch {
        /* keep statusText */
      }
      throw new Error(detail);
    }
    return res.json();
  },
  getAuditLog: (projectId) => request(`/audit-log/${projectId}`),
  getProjectFiles: (projectId) => request(`/project-files/${projectId}`),
  getReviewStatus: (projectId) => request(`/review/status/${projectId}`),
  autoValidate: (projectId) =>
    request(`/review/auto-validate/${projectId}`, { method: "POST" }),
  bulkApprove: (projectId, reviewedBy) => {
    const body = { project_id: projectId };
    if (reviewedBy) body.reviewed_by = reviewedBy;
    return request(`/review/bulk-approve`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};
export default api;
