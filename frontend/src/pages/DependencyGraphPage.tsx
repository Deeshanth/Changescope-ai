import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { GraphView, NodeNeighborhood } from "../api/types";
import { DependencyCanvas } from "../components/graph/DependencyCanvas";
import { NodeInspectorPanel } from "../components/graph/NodeInspectorPanel";

export function DependencyGraphPage({ repoId }: { repoId: number | null }) {
  const [level, setLevel] = useState<"module" | "symbol">("module");
  const [nodeType, setNodeType] = useState<string>("");
  const [includeTests, setIncludeTests] = useState(true);
  const [focusNodeId, setFocusNodeId] = useState<number | undefined>(undefined);
  const [graph, setGraph] = useState<GraphView | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [details, setDetails] = useState<NodeNeighborhood | null>(null);

  useEffect(() => {
    if (!repoId) return;
    api
      .getGraph(repoId, {
        level,
        node_type: level === "symbol" && nodeType ? nodeType : undefined,
        focus_node_id: focusNodeId,
        depth: 2,
        include_tests: includeTests,
        limit: 200,
      })
      .then(setGraph);
  }, [repoId, level, nodeType, focusNodeId, includeTests]);

  useEffect(() => {
    if (!repoId || selectedNodeId === null) {
      setDetails(null);
      return;
    }
    api.getNodeDetails(repoId, selectedNodeId).then(setDetails).catch(() => setDetails(null));
  }, [repoId, selectedNodeId]);

  if (!repoId) {
    return <div className="text-sm text-slate-400">Select a repository first.</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dependency Graph</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            {graph
              ? `Showing ${graph.returned_nodes} nodes & ${graph.returned_edges} edges (${graph.total_nodes_in_repo} total in repo)`
              : "Loading graph..."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex rounded-lg overflow-hidden border border-slate-700">
            <button
              onClick={() => {
                setLevel("module");
                setFocusNodeId(undefined);
              }}
              className={`px-3 py-1.5 ${
                level === "module" ? "bg-indigo-600 text-white" : "bg-surface-900 text-slate-300"
              }`}
            >
              Module View
            </button>
            <button
              onClick={() => setLevel("symbol")}
              className={`px-3 py-1.5 ${
                level === "symbol" ? "bg-indigo-600 text-white" : "bg-surface-900 text-slate-300"
              }`}
            >
              Symbol View
            </button>
          </div>

          {level === "symbol" && (
            <select
              value={nodeType}
              onChange={(e) => setNodeType(e.target.value)}
              className="bg-surface-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200"
            >
              <option value="">All Symbol Types</option>
              <option value="module">Modules</option>
              <option value="class">Classes</option>
              <option value="function">Functions</option>
              <option value="method">Methods</option>
            </select>
          )}

          <label className="flex items-center gap-1.5 px-2.5 py-1.5 bg-surface-900 border border-slate-700 rounded-lg cursor-pointer">
            <input
              type="checkbox"
              checked={includeTests}
              onChange={(e) => setIncludeTests(e.target.checked)}
            />
            <span>Include Tests</span>
          </label>

          {focusNodeId !== undefined && (
            <button
              onClick={() => setFocusNodeId(undefined)}
              className="px-2.5 py-1.5 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300"
            >
              Clear Focus
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <DependencyCanvas
            nodes={graph?.nodes ?? []}
            edges={graph?.edges ?? []}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />
        </div>
        <div>
          <NodeInspectorPanel
            details={details}
            onSelectNode={setSelectedNodeId}
            onFocusNode={(nid) => {
              setLevel("symbol");
              setFocusNodeId(nid);
              setSelectedNodeId(nid);
            }}
          />
        </div>
      </div>
    </div>
  );
}
