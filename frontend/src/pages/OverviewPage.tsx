import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { RepoFile, RepoOverview } from "../api/types";

export function OverviewPage({ repoId }: { repoId: number | null }) {
  const [overview, setOverview] = useState<RepoOverview | null>(null);
  const [files, setFiles] = useState<RepoFile[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!repoId) return;
    setLoading(true);
    Promise.all([api.getOverview(repoId), api.listFiles(repoId)])
      .then(([ov, fl]) => {
        setOverview(ov);
        setFiles(fl);
      })
      .finally(() => setLoading(false));
  }, [repoId]);

  if (!repoId) {
    return <div className="text-sm text-slate-400">Register or select a repository first.</div>;
  }
  if (loading || !overview) {
    return <div className="text-sm text-slate-400">Loading repository overview...</div>;
  }

  const statCards = [
    { label: "Tracked Python Files", value: overview.total_files },
    { label: "Lines of Code", value: overview.total_loc.toLocaleString() },
    { label: "AST Code Nodes", value: overview.total_nodes },
    { label: "Dependency Edges", value: overview.total_edges },
  ];

  const parseErrors = files.filter((f) => f.parse_status !== "ok");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{overview.name} - Overview</h1>
        <p className="text-xs font-mono text-slate-400 mt-1">
          Indexed HEAD: {overview.last_indexed_commit ?? "N/A"}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((c) => (
          <div key={c.label} className="bg-surface-900 border border-slate-800 rounded-xl p-4">
            <div className="text-xs text-slate-400">{c.label}</div>
            <div className="text-2xl font-mono font-semibold mt-1">{c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-900 border border-slate-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold mb-3">High Fan-In Hotspots (Blast Radius Magnets)</h2>
          <div className="space-y-2">
            {overview.top_fan_in_hotspots.length === 0 && (
              <div className="text-xs text-slate-500">No cross-component dependencies detected.</div>
            )}
            {overview.top_fan_in_hotspots.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between bg-surface-800 border border-slate-800 rounded-lg px-3 py-2 text-xs"
              >
                <div className="min-w-0">
                  <div className="font-mono text-slate-100 truncate">{item.node_key}</div>
                  <div className="text-slate-400">{item.file_path}</div>
                </div>
                <div className="font-mono text-amber-400 shrink-0 ml-3">
                  fan-in: {item.fan_in}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-surface-900 border border-slate-800 rounded-xl p-4">
          <h2 className="text-sm font-semibold mb-3">Highest Complexity Functions</h2>
          <div className="space-y-2">
            {overview.top_complex_symbols.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between bg-surface-800 border border-slate-800 rounded-lg px-3 py-2 text-xs"
              >
                <div className="min-w-0">
                  <div className="font-mono text-slate-100 truncate">{item.node_key}</div>
                  <div className="text-slate-400">{item.file_path}</div>
                </div>
                <div className="font-mono text-indigo-400 shrink-0 ml-3">
                  CC: {item.complexity}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {parseErrors.length > 0 && (
        <div className="bg-surface-900 border border-amber-500/30 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-amber-400 mb-2">
            Files with Parse Warnings ({parseErrors.length})
          </h2>
          <div className="space-y-1.5 text-xs font-mono">
            {parseErrors.map((f) => (
              <div key={f.id} className="flex justify-between bg-surface-800 px-3 py-1.5 rounded">
                <span>{f.file_path}</span>
                <span className="text-rose-400">{f.parse_error}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
