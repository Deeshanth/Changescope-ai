import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, ArrowRight } from "lucide-react";
import { api } from "../api/client";
import type { AnalysisRunSummary, CommitInfo } from "../api/types";
import { RiskBadge } from "../components/common/RiskBadge";

export function ChangeAnalysisPage({ repoId }: { repoId: number | null }) {
  const navigate = useNavigate();
  const [commits, setCommits] = useState<CommitInfo[]>([]);
  const [history, setHistory] = useState<AnalysisRunSummary[]>([]);
  const [baseCommit, setBaseCommit] = useState("");
  const [headCommit, setHeadCommit] = useState("");
  const [maxDepth, setMaxDepth] = useState(5);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;
    Promise.all([api.listCommits(repoId), api.listAnalyses(repoId)]).then(([cList, runs]) => {
      setCommits(cList);
      setHistory(runs);
      if (cList.length >= 2) {
        setHeadCommit(cList[0].commit_hash);
        setBaseCommit(cList[1].commit_hash);
      } else if (cList.length === 1) {
        setHeadCommit(cList[0].commit_hash);
        setBaseCommit(cList[0].commit_hash);
      }
    });
  }, [repoId]);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoId || !baseCommit || !headCommit) return;
    setRunning(true);
    setError(null);
    try {
      const result = await api.runAnalysis(repoId, baseCommit, headCommit, maxDepth);
      navigate(`/analyses/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impact analysis failed");
    } finally {
      setRunning(false);
    }
  };

  if (!repoId) {
    return <div className="text-sm text-slate-400">Select a repository first.</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Git Change Impact Analysis</h1>
        <p className="text-sm text-slate-400 mt-1">
          Compare two Git commits to trace modified AST symbols, blast radius, and deterministic risk scores.
        </p>
      </div>

      <form onSubmit={handleRun} className="bg-surface-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Base Commit (Before)</label>
            <select
              value={baseCommit}
              onChange={(e) => setBaseCommit(e.target.value)}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-100"
            >
              {commits.map((c) => (
                <option key={c.commit_hash} value={c.commit_hash}>
                  {c.short_hash} - {c.subject.slice(0, 50)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Head Commit (After)</label>
            <select
              value={headCommit}
              onChange={(e) => setHeadCommit(e.target.value)}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-100"
            >
              {commits.map((c) => (
                <option key={c.commit_hash} value={c.commit_hash}>
                  {c.short_hash} - {c.subject.slice(0, 50)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Max Traversal Depth</label>
            <input
              type="number"
              min={1}
              max={8}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-100"
            />
          </div>
        </div>

        {error && <div className="text-xs text-rose-400">{error}</div>}

        <button
          type="submit"
          disabled={running || commits.length === 0}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium text-white"
        >
          <Play className="w-4 h-4" />
          {running ? "Analyzing Dependency Blast Radius..." : "Run Impact Analysis"}
        </button>
      </form>

      <div className="bg-surface-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold mb-3">Previous Analysis Runs</h2>
        <div className="space-y-2">
          {history.length === 0 && (
            <div className="text-xs text-slate-500">No impact analyses run for this repository yet.</div>
          )}
          {history.map((run) => (
            <div
              key={run.id}
              onClick={() => navigate(`/analyses/${run.id}`)}
              className="flex items-center justify-between bg-surface-800 hover:bg-surface-700 border border-slate-800 rounded-lg px-4 py-3 cursor-pointer"
            >
              <div className="flex items-center gap-4">
                <RiskBadge level={run.risk_level} score={run.overall_risk_score} />
                <div className="font-mono text-xs text-slate-200">
                  {run.base_commit.slice(0, 7)} -&gt; {run.head_commit.slice(0, 7)}
                </div>
                <div className="text-xs text-slate-400">
                  Direct: {run.summary_json.direct_impact_count ?? 0} | Transitive:{" "}
                  {run.summary_json.transitive_impact_count ?? 0}
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
