import React, { useState, useEffect } from "react";
import {
  Project,
  ProjectRiskProfile,
  AnomalyResult,
  ProjectMLPrediction,
  ProjectBenchmarkResult,
  ProjectForecastResult,
} from "../../types";
import { api } from "../../api/client";
import { RiskBadge } from "../common/RiskBadge";
import { StatusBadge } from "../common/StatusBadge";
import { SeverityBadge } from "../common/SeverityBadge";
import {
  X,
  ShieldAlert,
  Coins,
  Clock,
  FileCheck,
  Cpu,
  CheckCircle2,
  XCircle,
  Scale,
} from "lucide-react";

interface ProjectDossierModalProps {
  projectId: string | null;
  onClose: () => void;
  allProjects: Project[];
  allRiskProfiles: ProjectRiskProfile[];
  allAnomalies: AnomalyResult[];
  allMLPredictions: ProjectMLPrediction[];
}

export const ProjectDossierModal: React.FC<ProjectDossierModalProps> = ({
  projectId,
  onClose,
  allProjects,
  allRiskProfiles,
  allAnomalies,
  allMLPredictions,
}) => {
  const [benchmark, setBenchmark] = useState<ProjectBenchmarkResult | null>(null);
  const [forecast, setForecast] = useState<ProjectForecastResult | null>(null);

  const project = allProjects.find((p) => p.project_id === projectId);
  const riskProfile = allRiskProfiles.find((p) => p.project_id === projectId);
  const projectAnomalies = allAnomalies.filter((a) => a.project_id === projectId);
  const mlPrediction = allMLPredictions.find((m) => m.project_id === projectId);

  useEffect(() => {
    if (!projectId) return;

    let isMounted = true;

    Promise.all([
      api.getProjectBenchmark(projectId).catch(() => null),
      api.getProjectForecast(projectId).catch(() => null),
    ]).then(([bmRes, fcRes]) => {
      if (isMounted) {
        setBenchmark(bmRes);
        setForecast(fcRes);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [projectId]);

  if (!projectId || !project) return null;

  // Compliance documents presence check
  const hasSanctionDoc = !projectAnomalies.some((a) => a.anomaly_type === "MISSING_SANCTION_DOCUMENT");
  const hasProgressDoc = !projectAnomalies.some((a) => a.anomaly_type === "MISSING_PROGRESS_DOCUMENT");
  const hasInspectionDoc = !projectAnomalies.some((a) => a.anomaly_type === "MISSING_INSPECTION_REPORT");
  const hasPaymentSupport = !projectAnomalies.some((a) => a.anomaly_type === "MISSING_PAYMENT_SUPPORT");
  const hasCompletionCert = !projectAnomalies.some((a) => a.anomaly_type === "MISSING_COMPLETION_CERTIFICATE");

  const utilizationPct = project.sanctioned_amount_lakh > 0
    ? Math.round((project.expenditure_lakh / project.sanctioned_amount_lakh) * 100)
    : 0;

  const costVariancePct = project.sanctioned_amount_lakh > 0
    ? Math.round(((project.estimated_cost_lakh - project.sanctioned_amount_lakh) / project.sanctioned_amount_lakh) * 100)
    : 0;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      <div
        className="bg-slate-50 w-full max-w-5xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh] animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="bg-white px-6 py-4 border-b border-slate-200 flex items-start justify-between gap-4 sticky top-0 z-20">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                {project.project_id}
              </span>
              <StatusBadge status={project.status} />
              <span className="text-xs text-slate-400">•</span>
              <span className="text-xs text-slate-600 font-medium">
                {project.work_category}
              </span>
              <span className="text-xs text-slate-400">•</span>
              <span className="text-xs text-slate-600">
                {project.district}, {project.state} (MP: {project.mp_name})
              </span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-1">
              {project.work_name}
            </h2>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {riskProfile && (
              <RiskBadge
                level={riskProfile.risk_level}
                score={riskProfile.risk_score}
                size="lg"
              />
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-6 space-y-6 overflow-y-auto">
          {/* SECTION 1: PROJECT SNAPSHOT */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Sanctioned</span>
              <div className="text-base font-bold text-slate-900 mt-0.5 font-mono">
                ₹{project.sanctioned_amount_lakh}L
              </div>
            </div>

            <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Actual Spent</span>
              <div className="text-base font-bold text-slate-900 mt-0.5 font-mono">
                ₹{project.expenditure_lakh}L
              </div>
            </div>

            <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Physical Progress</span>
              <div className="text-base font-bold text-blue-700 mt-0.5 font-mono">
                {project.physical_progress_pct}%
              </div>
            </div>

            <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Planned Target</span>
              <div className="text-base font-bold text-slate-900 mt-0.5 font-mono">
                {project.planned_progress_pct}%
              </div>
            </div>

            <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Fund Utilization</span>
              <div className="text-base font-bold text-slate-900 mt-0.5 font-mono">
                {utilizationPct}%
              </div>
            </div>

            <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Agency ID</span>
              <div className="text-xs font-bold text-slate-700 mt-1 truncate">
                {project.agency_id}
              </div>
            </div>
          </div>

          {/* SECTION 8: RECOMMENDED GOVERNANCE ACTION BANNER */}
          {riskProfile && (
            <div className="bg-gradient-to-r from-blue-900 to-slate-900 rounded-xl p-5 text-white shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-blue-500/30 text-blue-200 font-bold text-[11px] uppercase tracking-wider border border-blue-400/30">
                    Recommended Governance Action
                  </span>
                </div>
                <p className="text-sm font-semibold text-white mt-1">
                  {riskProfile.recommended_action}
                </p>
              </div>

              <div className="shrink-0">
                <span className="px-3 py-1.5 rounded-lg bg-blue-600 font-bold text-xs text-white shadow-xs inline-flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  Priority Field Audit Directive
                </span>
              </div>
            </div>
          )}

          {/* SECTION 2: WHY IS IT HIGH RISK? */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                  Risk Engine Diagnostic & Factors Breakdown
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Ranked by normalized priority weight, severity multiplier, and intra-category diminishing returns
                </p>
              </div>
              <span className="text-xs font-mono font-bold text-slate-600 bg-slate-100 px-2 py-1 rounded">
                Deterministic Score: {riskProfile?.risk_score ?? 0} / 100
              </span>
            </div>

            {riskProfile && riskProfile.risk_factors.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {riskProfile.risk_factors.map((rf, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-start justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-slate-900">
                          {rf.signal.replace(/_/g, " ")}
                        </span>
                        <SeverityBadge severity={rf.severity} />
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">
                        Domain: <strong>{rf.category}</strong> • Rule Weight: <strong>{rf.rule_weight ?? "N/A"}</strong>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="font-mono text-sm font-bold text-rose-700">
                        +{rf.contribution} pts
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400">
                No active deterministic risk factors detected. Project is currently operating normally.
              </div>
            )}
          </div>

          {/* SECTION 3: FINANCIAL HEALTH & PEER BENCHMARKING */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
                <Coins className="w-4 h-4 text-amber-600" />
                Financial Health & Variance
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Sanctioned Allocation:</span>
                  <span className="font-mono font-bold text-slate-900">₹{project.sanctioned_amount_lakh} Lakhs</span>
                </div>
                <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Estimated Technical Cost:</span>
                  <span className="font-mono font-bold text-slate-900">₹{project.estimated_cost_lakh} Lakhs</span>
                </div>
                <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Actual Cumulative Drawdown:</span>
                  <span className="font-mono font-bold text-slate-900">₹{project.expenditure_lakh} Lakhs</span>
                </div>
                <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Sanction Utilization:</span>
                  <span className="font-mono font-bold text-slate-900">{utilizationPct}%</span>
                </div>
                <div className="flex items-center justify-between text-xs py-1.5">
                  <span className="text-slate-500">Cost Variance vs Sanction:</span>
                  <span className={`font-mono font-bold ${costVariancePct > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                    {costVariancePct > 0 ? `+${costVariancePct}% Overrun` : `${costVariancePct}%`}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
                <Scale className="w-4 h-4 text-blue-600" />
                Comparable Project Peer Benchmarking
              </h3>

              {benchmark ? (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-100 text-blue-900">
                    <p className="leading-relaxed font-medium">
                      {benchmark.explanation}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                      <span className="text-[11px] text-slate-400">Peer Cohort Tier:</span>
                      <div className="font-bold text-slate-800 mt-0.5">
                        {benchmark.peer_hierarchy_tier.replace(/_/g, " ")}
                      </div>
                      <div className="text-[10px] text-slate-400">({benchmark.peer_count} peer projects)</div>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                      <span className="text-[11px] text-slate-400">Cost Ratio vs Median:</span>
                      <div className="font-bold text-slate-800 mt-0.5 font-mono">
                        {benchmark.cost_ratio_vs_peer_median ? `${benchmark.cost_ratio_vs_peer_median.toFixed(2)}x` : "1.00x"}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {benchmark.percentile_position !== null ? `${benchmark.percentile_position}th Percentile` : "Normal"}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-slate-400">
                  Loading comparable peer benchmark statistics...
                </div>
              )}
            </div>
          </div>

          {/* SECTION 4: PROGRESS & FORECAST TIMELINE */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Clock className="w-4 h-4 text-purple-600" />
              Progress Trajectory & Early Warning Forecast
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 text-[11px]">Execution Velocity:</span>
                <div className="font-bold text-slate-900 mt-0.5 font-mono text-sm">
                  {forecast?.velocity_pct_per_day ? `${(forecast.velocity_pct_per_day * 100).toFixed(2)}% / day` : "Stagnant"}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 text-[11px]">Est. Days to Complete:</span>
                <div className="font-bold text-slate-900 mt-0.5 font-mono text-sm">
                  {forecast?.estimated_days_remaining !== null && forecast?.estimated_days_remaining !== undefined ? `${forecast.estimated_days_remaining} days` : "Indeterminate"}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 text-[11px]">Forecasted Completion:</span>
                <div className="font-bold text-slate-900 mt-0.5 font-mono text-sm">
                  {forecast?.forecast_completion_date || "Past Deadline"}
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-slate-400 text-[11px]">Projected Delay:</span>
                <div className="font-bold mt-0.5 font-mono text-sm text-rose-600">
                  {forecast?.forecast_delay_days ? `+${forecast.forecast_delay_days} days` : "On Schedule"}
                </div>
              </div>
            </div>

            {forecast && (
              <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100 leading-relaxed">
                <strong>Trajectory Diagnostic:</strong> {forecast.explanation}
              </p>
            )}
          </div>

          {/* SECTION 6: STATUTORY COMPLIANCE CHECKLIST */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
              <FileCheck className="w-4 h-4 text-emerald-600" />
              Statutory Compliance & Evidence Audit Checklist
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
              <div className={`p-3 rounded-lg border flex items-center gap-2.5 ${hasSanctionDoc ? "bg-emerald-50/50 border-emerald-200 text-emerald-900" : "bg-rose-50/50 border-rose-200 text-rose-900"}`}>
                {hasSanctionDoc ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> : <XCircle className="w-4 h-4 text-rose-600 shrink-0" />}
                <div>
                  <div className="text-xs font-bold">Sanction Order</div>
                  <div className="text-[10px] opacity-75">{hasSanctionDoc ? "Verified" : "Missing"}</div>
                </div>
              </div>

              <div className={`p-3 rounded-lg border flex items-center gap-2.5 ${hasProgressDoc ? "bg-emerald-50/50 border-emerald-200 text-emerald-900" : "bg-rose-50/50 border-rose-200 text-rose-900"}`}>
                {hasProgressDoc ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> : <XCircle className="w-4 h-4 text-rose-600 shrink-0" />}
                <div>
                  <div className="text-xs font-bold">Progress Photos</div>
                  <div className="text-[10px] opacity-75">{hasProgressDoc ? "Verified" : "Missing"}</div>
                </div>
              </div>

              <div className={`p-3 rounded-lg border flex items-center gap-2.5 ${hasPaymentSupport ? "bg-emerald-50/50 border-emerald-200 text-emerald-900" : "bg-rose-50/50 border-rose-200 text-rose-900"}`}>
                {hasPaymentSupport ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> : <XCircle className="w-4 h-4 text-rose-600 shrink-0" />}
                <div>
                  <div className="text-xs font-bold">MB Record / Vouchers</div>
                  <div className="text-[10px] opacity-75">{hasPaymentSupport ? "Verified" : "Missing"}</div>
                </div>
              </div>

              <div className={`p-3 rounded-lg border flex items-center gap-2.5 ${hasInspectionDoc ? "bg-emerald-50/50 border-emerald-200 text-emerald-900" : "bg-rose-50/50 border-rose-200 text-rose-900"}`}>
                {hasInspectionDoc ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> : <XCircle className="w-4 h-4 text-rose-600 shrink-0" />}
                <div>
                  <div className="text-xs font-bold">Site Inspection</div>
                  <div className="text-[10px] opacity-75">{hasInspectionDoc ? "Verified" : "Missing"}</div>
                </div>
              </div>

              <div className={`p-3 rounded-lg border flex items-center gap-2.5 ${hasCompletionCert ? "bg-emerald-50/50 border-emerald-200 text-emerald-900" : "bg-rose-50/50 border-rose-200 text-rose-900"}`}>
                {hasCompletionCert ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" /> : <XCircle className="w-4 h-4 text-rose-600 shrink-0" />}
                <div>
                  <div className="text-xs font-bold">Completion Cert</div>
                  <div className="text-[10px] opacity-75">{hasCompletionCert ? "Verified" : "Missing"}</div>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 7: MACHINE LEARNING STATISTICAL INSIGHT */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-600" />
                Unsupervised Machine Learning Supporting Signal
              </h3>
              <span className="text-[11px] font-mono text-slate-500">
                IsolationForest v1.1.0 • 29 Continuous Features
              </span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                <span className="font-semibold text-slate-800">
                  {mlPrediction?.ml_anomaly_flag
                    ? "Statistical Multi-Dimensional Outlier Flagged"
                    : "Within Normal Statistical Distribution"}
                </span>
                <p className="text-slate-500 text-[11px] mt-0.5">
                  Evaluated across 29 continuous execution, timeline, and disbursement dimensions. ML acts strictly as a supporting signal (max +5 pts).
                </p>
              </div>

              <div className="text-right shrink-0">
                <span className="text-slate-400 text-[10px] block">ML Anomaly Score</span>
                <span className="font-mono font-bold text-slate-900 text-base">
                  {mlPrediction?.ml_anomaly_score.toFixed(1) ?? 0} / 100
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="bg-slate-100/80 px-6 py-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 sticky bottom-0">
          <span>MPLADS Intelligence System • SIH Problem Statement 26102</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-semibold hover:bg-slate-800 transition-colors"
          >
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  );
};
