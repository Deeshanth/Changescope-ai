import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Sparkles, ShieldAlert, GitBranch, FlaskConical } from "lucide-react";
import { api } from "../api/client";
import type { AIReport, AnalysisRunDetail, ImpactedComponent } from "../api/types";
import { RiskBadge } from "../components/common/RiskBadge";
import { ScoreBreakdownBar } from "../components/common/ScoreBreakdownBar";

export function RiskReportPage({ aiEnabled }: { aiEnabled: boolean }) {
  const { analysisId } = useParams<{ analysisId: string }>();
  const [report, setReport] = useState<AnalysisRunDetail | null>(null);
  const [selected, setSelected] = useState<ImpactedComponent | null>(null);
  const [filter, setFilter] = useState<"all" | "direct" | "transitive">("all");
  const [aiReport, setAiReport] = useState<AIReport | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return;
    const id = Number(analysisId);
    api.getAnalysisDetail(id).then((data) => {
      setReport(data);
      setSelected(data.impacted_components[0] ?? null);
      if (data.has_ai_report) {
        api.getAIReport(id).then(setAiReport).catch(() => null);
      }
    });
  }, [analysisId]);

  const filteredComponents = useMemo(() => {
    if (!report) return [];
    if (filter === "all") return report.impacted_components;
    return report.impacted_components.filter((c) => c.impact_type === filter);
  }, [report, filter]);

  const handleGenerateAI = async (regenerate = false) => {
    if (!report) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await api.generateAIReport(report.id, regenerate);
      setAiReport(res);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Failed to generate AI report");
    } finally {
      setAiLoading(false);
    }
  };

  if (!report) {
    return <div className="text-sm text-slate-400">Loading risk report...</div>;
  }

  const formula = report.summary_json.overall_formula_breakdown ?? {};

  return (
    <div className="space-y-6">
      <div className="bg-surface-900 border border-slate-800 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-xs font-mono text-slate-400">
            ANALYSIS #{report.id} | {report.base_commit.slice(0, 7)} -&gt; {report.head_commit.slice(0, 7)}
          </div>
          <h1 className="text-xl font-semibold tracking-tight mt-1">
            Change Impact & Deterministic Risk Report
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Direct: {report.summary_json.direct_impact_count ?? 0} | Transitive:{" "}
            {report.summary_json.transitive_impact_count ?? 0} | Peak Risk:{" "}
            {formula.peak_risk ?? 0} | Top-5 Avg: {formula.top5_average_risk ?? 0}
          </p>
        </div>

        <div className="text-right">
          <div className="text-xs text-slate-400 mb-1">Overall Risk Score</div>
          <RiskBadge level={report.risk_level} score={report.overall_risk_score} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-surface-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">
              Affected Components ({filteredComponents.length})
            </h2>
            <div className="flex gap-1 text-xs">
              {(["all", "direct", "transitive"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilter(tab)}
                  className={`px-2.5 py-1 rounded capitalize ${
                    filter === tab
                      ? "bg-indigo-600 text-white"
                      : "bg-surface-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          <div className="max-h-[440px] overflow-y-auto space-y-1.5">
            {filteredComponents.length === 0 && (
              <div className="text-xs text-slate-500 py-6 text-center">
                No impacted Python symbols detected between these commits.
              </div>
            )}
            {filteredComponents.map((comp) => (
              <div
                key={comp.id}
                onClick={() => setSelected(comp)}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selected?.id === comp.id
                    ? "bg-surface-800 border-indigo-500/60"
                    : "bg-surface-950/60 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-mono text-xs font-semibold text-slate-100 truncate">
                      {comp.node_key}
                    </div>
                    <div className="text-[11px] text-slate-400">
                      {comp.file_path}:{comp.start_line} |{" "}
                      <span className="uppercase">{comp.impact_type}</span> (hop {comp.hop_distance})
                    </div>
                  </div>
                  <RiskBadge level={comp.risk_level} score={comp.risk_score} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-surface-900 border border-slate-800 rounded-xl p-4 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <ShieldAlert className="w-4 h-4 text-indigo-400" />
            Deterministic Score Breakdown
          </div>

          {selected ? (
            <>
              <div>
                <div className="font-mono text-xs text-slate-200 break-all">{selected.node_key}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  Hop distance: {selected.hop_distance} | Fan-in: {selected.risk_factors.inputs.fan_in} | Complexity:{" "}
                  {selected.risk_factors.inputs.complexity}
                </div>
              </div>

              <ScoreBreakdownBar factors={selected.risk_factors} />

              <div>
                <div className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-2">
                  <GitBranch className="w-3.5 h-3.5 text-sky-400" />
                  Dependency Propagation Paths
                </div>
                <div className="space-y-1.5">
                  {selected.dependency_paths.map((path, idx) => (
                    <div
                      key={idx}
                      className="text-[11px] font-mono bg-surface-950 border border-slate-800 rounded p-2 text-slate-300 break-all"
                    >
                      {path.join(" -> ")}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="text-xs text-slate-500">Select an impacted component to inspect its score.</div>
          )}
        </div>
      </div>

      <div className="bg-surface-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold">Claude AI Explanation & Test Recommendations</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              ADVISORY ONLY | SCORES ARE DETERMINISTIC
            </span>
          </div>

          <button
            onClick={() => handleGenerateAI(Boolean(aiReport))}
            disabled={aiLoading || !aiEnabled}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/30 disabled:opacity-40 text-xs font-medium"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {aiLoading
              ? "Generating AI Insights..."
              : aiReport
              ? "Regenerate AI Insights"
              : aiEnabled
              ? "Generate AI Insights"
              : "Configure ANTHROPIC_API_KEY to Enable"}
          </button>
        </div>

        {aiError && <div className="text-xs text-rose-400">{aiError}</div>}

        {aiReport && (
          <div className="space-y-4">
            <div className="bg-surface-950 border border-slate-800 rounded-lg p-4 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
              {aiReport.explanation_markdown}
            </div>

            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-2">
                <FlaskConical className="w-3.5 h-3.5 text-indigo-400" />
                Recommended Tests ({aiReport.recommended_tests.length})
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {aiReport.recommended_tests.map((test, idx) => (
                  <div
                    key={idx}
                    className="bg-surface-800 border border-slate-800 rounded-lg p-3 space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-indigo-300">
                        {test.target_component}
                      </span>
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-950 border border-slate-700">
                        {test.test_type.toUpperCase()} | {test.priority}
                      </span>
                    </div>
                    <p className="text-slate-300">{test.rationale}</p>
                    <p className="text-slate-400 font-mono text-[11px]">
                      Scenario: {test.suggested_scenario}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
