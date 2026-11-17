import { useState } from "react";
import { FolderPlus, RefreshCw, AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "../api/client";
import type { Repository } from "../api/types";

interface RepositoriesPageProps {
  repositories: Repository[];
  activeRepoId: number | null;
  onSelectRepo: (id: number) => void;
  onRefresh: () => Promise<void>;
}

export function RepositoriesPage({
  repositories,
  activeRepoId,
  onSelectRepo,
  onRefresh,
}: RepositoriesPageProps) {
  const [localPath, setLocalPath] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [scanningId, setScanningId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localPath.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const repo = await api.registerRepository(localPath.trim(), name.trim() || undefined);
      setLocalPath("");
      setName("");
      await onRefresh();
      onSelectRepo(repo.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to register repository");
    } finally {
      setLoading(false);
    }
  };

  const handleRescan = async (repoId: number) => {
    setScanningId(repoId);
    setError(null);
    try {
      await api.rescanRepository(repoId);
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rescan repository");
    } finally {
      setScanningId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Local Git Repositories</h1>
        <p className="text-sm text-slate-400 mt-1">
          Register a local Python Git repository to statically parse AST symbols and build its dependency graph.
        </p>
      </div>

      <form
        onSubmit={handleRegister}
        className="bg-surface-900 border border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Local Repository Path
            </label>
            <input
              type="text"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="C:\Users\P R Deeshanth\projects\my-python-repo"
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-100 focus:outline-none focus:border-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Display Name (Optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., billing-service"
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium text-white"
        >
          <FolderPlus className="w-4 h-4" />
          {loading ? "Scanning Repository..." : "Register & Scan Repository"}
        </button>
      </form>

      <div className="grid grid-cols-1 gap-3">
        {repositories.map((repo) => (
          <div
            key={repo.id}
            onClick={() => onSelectRepo(repo.id)}
            className={`bg-surface-900 border rounded-xl p-4 cursor-pointer transition-colors ${
              repo.id === activeRepoId
                ? "border-indigo-500/60"
                : "border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-100">{repo.name}</span>
                  <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <CheckCircle2 className="w-3 h-3" />
                    {repo.status}
                  </span>
                </div>
                <div className="text-xs font-mono text-slate-400 mt-1">{repo.local_path}</div>
              </div>

              <div className="flex items-center gap-6 text-xs">
                <div>
                  <span className="text-slate-400">Files: </span>
                  <span className="font-mono font-semibold">{repo.stats?.file_count ?? 0}</span>
                </div>
                <div>
                  <span className="text-slate-400">Symbols: </span>
                  <span className="font-mono font-semibold">{repo.stats?.node_count ?? 0}</span>
                </div>
                <div>
                  <span className="text-slate-400">Edges: </span>
                  <span className="font-mono font-semibold">{repo.stats?.edge_count ?? 0}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRescan(repo.id);
                  }}
                  disabled={scanningId === repo.id}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-800 border border-slate-700 hover:bg-surface-700 text-slate-200"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${scanningId === repo.id ? "animate-spin" : ""}`} />
                  Re-scan
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
