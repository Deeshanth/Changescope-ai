import { Crosshair, ArrowDownLeft, ArrowUpRight } from "lucide-react";
import type { NodeNeighborhood } from "../../api/types";

interface NodeInspectorPanelProps {
  details: NodeNeighborhood | null;
  onFocusNode: (nodeId: number) => void;
  onSelectNode: (nodeId: number) => void;
}

export function NodeInspectorPanel({
  details,
  onFocusNode,
  onSelectNode,
}: NodeInspectorPanelProps) {
  if (!details) {
    return (
      <div className="bg-surface-900 border border-slate-800 rounded-xl p-5 text-sm text-slate-400">
        Select any node in the graph to inspect its dependencies, callers, and complexity metrics.
      </div>
    );
  }

  const { node, dependents, dependencies } = details;

  return (
    <div className="bg-surface-900 border border-slate-800 rounded-xl p-4 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[11px] uppercase font-mono text-indigo-400">{node.node_type}</div>
          <h3 className="text-sm font-mono font-semibold text-slate-100 break-all">
            {node.node_key}
          </h3>
          <p className="text-xs text-slate-400 mt-0.5 break-all">
            {node.file_path}:{node.start_line}-{node.end_line}
          </p>
        </div>
        <button
          onClick={() => onFocusNode(node.id)}
          className="shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs hover:bg-indigo-500/25"
        >
          <Crosshair className="w-3.5 h-3.5" />
          Focus Subgraph
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-surface-800 border border-slate-800 rounded-lg p-2">
          <div className="text-[11px] text-slate-400">Fan-In</div>
          <div className="text-sm font-mono font-semibold">{node.fan_in}</div>
        </div>
        <div className="bg-surface-800 border border-slate-800 rounded-lg p-2">
          <div className="text-[11px] text-slate-400">Fan-Out</div>
          <div className="text-sm font-mono font-semibold">{node.fan_out}</div>
        </div>
        <div className="bg-surface-800 border border-slate-800 rounded-lg p-2">
          <div className="text-[11px] text-slate-400">Complexity</div>
          <div className="text-sm font-mono font-semibold">{node.complexity}</div>
        </div>
      </div>

      <div>
        <div className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-2">
          <ArrowDownLeft className="w-3.5 h-3.5 text-amber-400" />
          Impacted Dependents ({dependents.length})
        </div>
        <div className="max-h-40 overflow-y-auto space-y-1">
          {dependents.length === 0 && <div className="text-xs text-slate-500">None</div>}
          {dependents.map((dep) => (
            <button
              key={dep.id}
              onClick={() => onSelectNode(dep.id)}
              className="w-full text-left px-2.5 py-1.5 rounded bg-surface-800 hover:bg-surface-700 text-xs font-mono text-slate-200 flex justify-between items-center"
            >
              <span className="truncate">{dep.node_key}</span>
              <span className="text-[10px] text-slate-400 ml-2">{dep.edge_types.join(",")}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-2">
          <ArrowUpRight className="w-3.5 h-3.5 text-sky-400" />
          Outgoing Dependencies ({dependencies.length})
        </div>
        <div className="max-h-40 overflow-y-auto space-y-1">
          {dependencies.length === 0 && <div className="text-xs text-slate-500">None</div>}
          {dependencies.map((dep) => (
            <button
              key={dep.id}
              onClick={() => onSelectNode(dep.id)}
              className="w-full text-left px-2.5 py-1.5 rounded bg-surface-800 hover:bg-surface-700 text-xs font-mono text-slate-200 flex justify-between items-center"
            >
              <span className="truncate">{dep.node_key}</span>
              <span className="text-[10px] text-slate-400 ml-2">{dep.edge_types.join(",")}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
