"use client";

import { createContext, useContext, useEffect, useState } from "react";

const ProjectContext = createContext({ projectId: 1, setProjectId: () => {} });

export function ProjectProvider({ children }) {
  const [projectId, setProjectIdState] = useState(1);

  useEffect(() => {
    const saved = window.localStorage.getItem("earthwork.projectId");
    if (saved) setProjectIdState(parseInt(saved, 10) || 1);
  }, []);

  function setProjectId(id) {
    const clean = Number.isFinite(id) && id > 0 ? id : 1;
    setProjectIdState(clean);
    window.localStorage.setItem("earthwork.projectId", String(clean));
  }

  return (
    <ProjectContext.Provider value={{ projectId, setProjectId }}>
      {children}
    </ProjectContext.Provider>
  );
}

export const useProject = () => useContext(ProjectContext);
