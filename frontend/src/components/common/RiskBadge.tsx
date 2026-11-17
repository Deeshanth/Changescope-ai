import type { RiskLevel } from "../../api/types";

const LEVEL_STYLES: Record<RiskLevel, string> = {
  CRITICAL: "bg-rose-500/15 text-rose-400 border-rose-500/40",
  HIGH: "bg-amber-500/15 text-amber-400 border-amber-500/40",
  MEDIUM: "bg-sky-500/15 text-sky-400 border-sky-500/40",
  LOW: "bg-emerald-500/15 text-emerald-400 border-emerald-500/40",
};

export function RiskBadge({ level, score }: { level: RiskLevel; score?: number }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium border ${
        LEVEL_STYLES[level] || LEVEL_STYLES.LOW
      }`}
    >
      <span>{level}</span>
      {score !== undefined && <span className="opacity-80">{score.toFixed(1)}</span>}
    </span>
  );
}
