import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import type { Repository } from "./api/types";
import { AppShell } from "./components/layout/AppShell";
import { ChangeAnalysisPage } from "./pages/ChangeAnalysisPage";
import { DependencyGraphPage } from "./pages/DependencyGraphPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RepositoriesPage } from "./pages/RepositoriesPage";
import { RiskReportPage } from "./pages/RiskReportPage";

export default function App() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [activeRepoId, setActiveRepoId] = useState<number | null>(() => {
    const saved = localStorage.getItem("changescope_active_repo");
    return saved ? Number(saved) : null;
  });
  const [aiEnabled, setAiEnabled] = useState(false);

  const loadRepositories = useCallback(async () => {
    const repos = await api.listRepositories();
    setRepositories(repos);
    setActiveRepoId((prev) => {
      if (prev && repos.some((r) => r.id === prev)) return prev;
      return repos[0]?.id ?? null;
    });
  }, []);

  useEffect(() => {
    api.health().then((h) => setAiEnabled(h.ai_enabled)).catch(() => setAiEnabled(false));
    loadRepositories().catch(() => null);
  }, [loadRepositories]);

  const handleSelectRepo = (id: number) => {
    setActiveRepoId(id);
    localStorage.setItem("changescope_active_repo", String(id));
  };

  return (
    <BrowserRouter>
      <AppShell
        repositories={repositories}
        activeRepoId={activeRepoId}
        onSelectRepo={handleSelectRepo}
        aiEnabled={aiEnabled}
      >
        <Routes>
          <Route
            path="/"
            element={
              <RepositoriesPage
                repositories={repositories}
                activeRepoId={activeRepoId}
                onSelectRepo={handleSelectRepo}
                onRefresh={loadRepositories}
              />
            }
          />
          <Route path="/overview" element={<OverviewPage repoId={activeRepoId} />} />
          <Route path="/graph" element={<DependencyGraphPage repoId={activeRepoId} />} />
          <Route path="/analyze" element={<ChangeAnalysisPage repoId={activeRepoId} />} />
          <Route path="/analyses/:analysisId" element={<RiskReportPage aiEnabled={aiEnabled} />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
