import type { ImpactedComponent } from "../../api/types";

export function ScoreBreakdownBar({ factors }: { factors: ImpactedComponent["risk_factors"] }) {
  const rows = [
    { label: "Proximity", score: factors.proximity_score, max: factors.proximity_max, color: "bg-indigo-500" },
    { label: "Centrality (Fan-In)", score: factors.centrality_score, max: factors.centrality_max, color: "bg-sky-500" },
    { label: "Change Churn", score: factors.churn_score, max: factors.churn_max, color: "bg-amber-500" },
    { label: "AST Complexity", score: factors.complexity_score, max: factors.complexity_max, color: "bg-violet-500" },
    { label: "Static Uncertainty", score: factors.uncertainty_penalty, max: factors.uncertainty_max, color: "bg-rose-500" },
  ];

  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const pct = row.max > 0 ? Math.min(100, (row.score / row.max) * 100) : 0;
        return (
          <div key={row.label} className="space-y-1">
            <div className="flex justify-between text-xs text-slate-300">
              <span>{row.label}</span>
              <span className="font-mono text-slate-400">
                {row.score.toFixed(2)} / {row.max.toFixed(0)}
              </span>
            </div>
            <div className="h-1.5 w-full bg-surface-950 rounded-full overflow-hidden border border-slate-800">
              <div className={`h-full ${row.color}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
      {factors.test_dampening_factor < 1 && (
        <div className="text-[11px] font-mono text-slate-400 pt-1">
          Test-file dampening applied: {factors.raw_score.toFixed(2)} x {factors.test_dampening_factor}
        </div>
      )}
    </div>
  );
}
