"use client";

import { useProject } from "@/lib/project-context";

export default function ProjectSelector() {
  const { projectId, setProjectId } = useProject();
  return (
    <div className="titleblock-cell">
      <span className="k">Project</span>
      <input
        type="number"
        min="1"
        value={projectId}
        onChange={(e) => setProjectId(parseInt(e.target.value, 10))}
        style={{ width: 70, marginTop: 2 }}
        aria-label="Project ID"
      />
    </div>
  );
}
