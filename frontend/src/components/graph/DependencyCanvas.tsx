import { useMemo, useState } from "react";
import { RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import type { GraphEdge, GraphNode } from "../../api/types";

interface DependencyCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: number | null;
  onSelectNode: (nodeId: number) => void;
}

const NODE_COLORS: Record<string, string> = {
  module: "#6366f1",
  class: "#0ea5e9",
  function: "#10b981",
  method: "#14b8a6",
};

export function DependencyCanvas({
  nodes,
  edges,
  selectedNodeId,
  onSelectNode,
}: DependencyCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState<{ x: number; y: number } | null>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  const layout = useMemo(() => {
    const positions = new Map<number, { x: number; y: number }>();
    if (nodes.length === 0) return { positions };

    const sorted = [...nodes].sort((a, b) => {
      const scoreA = a.fan_out - a.fan_in;
      const scoreB = b.fan_out - b.fan_in;
      return scoreB - scoreA || a.node_key.localeCompare(b.node_key);
    });

    const cols = Math.max(3, Math.ceil(Math.sqrt(sorted.length * 1.4)));
    const colSpacing = 240;
    const rowSpacing = 96;

    sorted.forEach((node, idx) => {
      const col = idx % cols;
      const row = Math.floor(idx / cols);
      const staggerY = col % 2 === 1 ? 26 : 0;
      positions.set(node.id, {
        x: 130 + col * colSpacing,
        y: 80 + row * rowSpacing + staggerY,
      });
    });

    return { positions };
  }, [nodes]);

  const activeId = hoveredId ?? selectedNodeId;
  const connectedIds = useMemo(() => {
    const set = new Set<number>();
    if (activeId === null) return set;
    set.add(activeId);
    for (const edge of edges) {
      if (edge.source === activeId) set.add(edge.target);
      if (edge.target === activeId) set.add(edge.source);
    }
    return set;
  }, [activeId, edges]);

  return (
    <div className="relative bg-surface-900 border border-slate-800 rounded-xl overflow-hidden select-none">
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-surface-950/90 border border-slate-800 rounded-lg p-1">
        <button
          onClick={() => setZoom((z) => Math.min(2.2, z + 0.2))}
          className="p-1.5 rounded hover:bg-surface-800 text-slate-300"
          title="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.35, z - 0.2))}
          className="p-1.5 rounded hover:bg-surface-800 text-slate-300"
          title="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="p-1.5 rounded hover:bg-surface-800 text-slate-300"
          title="Reset view"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 bg-surface-950/90 border border-slate-800 rounded-lg px-3 py-1.5 text-[11px] text-slate-300">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1.5 capitalize">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            {type}
          </span>
        ))}
      </div>

      <svg
        className="w-full h-[560px] cursor-grab active:cursor-grabbing"
        onMouseDown={(e) => setDragging({ x: e.clientX - pan.x, y: e.clientY - pan.y })}
        onMouseMove={(e) => {
          if (dragging) setPan({ x: e.clientX - dragging.x, y: e.clientY - dragging.y });
        }}
        onMouseUp={() => setDragging(null)}
        onMouseLeave={() => setDragging(null)}
      >
        <defs>
          <marker
            id="arrow-default"
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#475569" />
          </marker>
          <marker
            id="arrow-active"
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#818cf8" />
          </marker>
        </defs>

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {edges.map((edge, idx) => {
            const p1 = layout.positions.get(edge.source);
            const p2 = layout.positions.get(edge.target);
            if (!p1 || !p2) return null;
            const isActive =
              activeId !== null && (edge.source === activeId || edge.target === activeId);
            const dimmed = activeId !== null && !isActive;

            const dx = (p2.x - p1.x) * 0.4;
            const d = `M ${p1.x} ${p1.y} C ${p1.x + dx} ${p1.y}, ${p2.x - dx} ${p2.y}, ${p2.x} ${p2.y}`;

            return (
              <path
                key={`${edge.source}-${edge.target}-${idx}`}
                d={d}
                fill="none"
                stroke={isActive ? "#818cf8" : "#334155"}
                strokeWidth={isActive ? 2 : 1.2}
                strokeDasharray={edge.confidence === "heuristic" ? "4 3" : undefined}
                opacity={dimmed ? 0.18 : isActive ? 0.95 : 0.65}
                markerEnd={isActive ? "url(#arrow-active)" : "url(#arrow-default)"}
              />
            );
          })}

          {nodes.map((node) => {
            const pos = layout.positions.get(node.id);
            if (!pos) return null;
            const isSelected = node.id === selectedNodeId;
            const isConnected = activeId === null || connectedIds.has(node.id);
            const fill = NODE_COLORS[node.node_type] || "#64748b";

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectNode(node.id);
                }}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                className="cursor-pointer"
                opacity={isConnected ? 1 : 0.25}
              >
                <rect
                  x={-88}
                  y={-22}
                  width={176}
                  height={44}
                  rx={8}
                  fill="#0f131a"
                  stroke={isSelected ? "#818cf8" : "#273042"}
                  strokeWidth={isSelected ? 2 : 1}
                />
                <circle cx={-70} cy={-4} r={4.5} fill={fill} />
                <text
                  x={-58}
                  y={0}
                  fill="#f1f5f9"
                  fontSize="11"
                  fontFamily="ui-monospace, monospace"
                >
                  {node.name.length > 18 ? `${node.name.slice(0, 17)}...` : node.name}
                </text>
                <text x={-70} y={14} fill="#94a3b8" fontSize="9.5" fontFamily="ui-monospace, monospace">
                  in:{node.fan_in} out:{node.fan_out} {node.is_test ? "[test]" : ""}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
