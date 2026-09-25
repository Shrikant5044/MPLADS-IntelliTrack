import React, { useState, useEffect } from "react";
import {
  Project,
  ProjectRiskProfile,
  AnomalyResult,
  RealWorkBenchmarkResult,
} from "../../types";
import { api } from "../../api/client";
import { SeverityBadge } from "../common/SeverityBadge";
import { useAuth } from "../../context/AuthContext";
import {
  formatCurrencyLakh,
  formatLakhVal,
  formatProgressPct,
  formatFundUtilizationPct,
} from "../../utils/formatters";
import {
  CheckSquare,
  ShieldAlert,
  Scale,
  FileText,
  ArrowRight,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Lock,
} from "lucide-react";

interface VerificationCheckItem {
  id: string;
  action: string;
  promptedBy: string;
  category: "FINANCIAL" | "TIMELINE" | "COMPLIANCE" | "ROUTINE";
}

interface ConsistencyVerificationCardProps {
  project: Project;
  riskProfile?: ProjectRiskProfile;
  anomalies?: AnomalyResult[];
  onSendToInvestigation: (verificationPlanText: string) => void;
}

// Safe formatting helpers using central utilities
const formatLakh = (val?: number | null): string => formatLakhVal(val);
const formatPct = (val?: number | null): string =>
  val === undefined || val === null || typeof val !== "number" || !isFinite(val)
    ? "—"
    : val.toFixed(1);

export const ConsistencyVerificationCard: React.FC<ConsistencyVerificationCardProps> = ({
  project,
  riskProfile,
  anomalies = [],
  onSendToInvestigation,
}) => {
  const { user } = useAuth();
  const [realBenchmark, setRealBenchmark] = useState<RealWorkBenchmarkResult | null>(null);
  const [isLoadingBenchmark, setIsLoadingBenchmark] = useState<boolean>(true);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);

  const safeAnomalies = Array.isArray(anomalies) ? anomalies : [];

  // Auth RBAC check
  const isMoSPI = user?.role === "MOSPI_OFFICER";
  const isDistrictAuthority = user?.role === "DISTRICT_AUTHORITY";
  const isDistrictMatch = isDistrictAuthority
    ? (user?.assigned_district || "").trim().toLowerCase() === (project.district || "").trim().toLowerCase()
    : false;
  const canManage = isMoSPI || isDistrictMatch;

  useEffect(() => {
    let isMounted = true;
    setIsLoadingBenchmark(true);
    setBenchmarkError(null);

    const amountRupees = (project.sanctioned_amount_lakh || project.estimated_cost_lakh || 0) * 100000;

    api
      .getRealMPLADSBenchmark({
        description: project.work_name,
        amount: amountRupees,
        state: project.state,
        category: project.work_category,
        dataset: "recommended",
        top_k: 3,
      })
      .then((res) => {
        if (isMounted) {
          setRealBenchmark(res);
          setIsLoadingBenchmark(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setBenchmarkError(err?.message || "Real MPLADS peer benchmark unavailable");
          setIsLoadingBenchmark(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [project.project_id, project.work_name, project.sanctioned_amount_lakh, project.estimated_cost_lakh, project.state, project.work_category]);

  // Derived calculations
  const utilizationPct =
    project.sanctioned_amount_lakh > 0
      ? Math.round((project.expenditure_lakh / project.sanctioned_amount_lakh) * 100)
      : 0;

  // Generate up to 3 concise, actionable checks strictly from actual data
  const generateVerificationChecklist = (): VerificationCheckItem[] => {
    const checks: VerificationCheckItem[] = [];

    // 1. Compliance Document Anomalies Check
    const missingDocs = safeAnomalies.filter((a) => a.anomaly_type && a.anomaly_type.startsWith("MISSING_"));
    if (missingDocs.length > 0) {
      const missingNames = missingDocs
        .map((d) => d.anomaly_type.replace("MISSING_", "").replace(/_/g, " "))
        .join(", ");
      checks.push({
        id: "check-doc",
        action: `Obtain and verify missing statutory documentation (${missingNames.toLowerCase()}) prior to further disbursement.`,
        promptedBy: `Compliance Anomaly Signal: ${missingDocs.length} missing statutory document(s)`,
        category: "COMPLIANCE",
      });
    }

    // 2. Real MPLADS Cost Benchmark / Financial Anomaly Check
    const costAnomalies = safeAnomalies.filter(
      (a) =>
        a.anomaly_type === "COST_OVERRUN" ||
        a.anomaly_type === "EXPENDITURE_EXCEEDS_SANCTION" ||
        a.anomaly_type === "ABNORMALLY_HIGH_UTILIZATION"
    );

    const isDiffValid =
      realBenchmark &&
      realBenchmark.status === "SUCCESS" &&
      typeof realBenchmark.peer_median_lakh === "number" &&
      typeof realBenchmark.percentage_difference_from_peer_median === "number";

    if (isDiffValid && Math.abs(realBenchmark!.percentage_difference_from_peer_median!) > 15) {
      const diffVal = realBenchmark!.percentage_difference_from_peer_median!;
      const diffSign = diffVal > 0 ? "+" : "";
      checks.push({
        id: "check-benchmark",
        action: `Audit Measurement Book (MB) line items against real MPLADS peer median baseline (₹${formatLakh(
          realBenchmark!.peer_median_lakh
        )} Lakhs across ${realBenchmark!.comparable_project_count || 0} verified peer works).`,
        promptedBy: `Real MPLADS Peer Variance: ${diffSign}${formatPct(diffVal)}% from peer median`,
        category: "FINANCIAL",
      });
    } else if (costAnomalies.length > 0) {
      checks.push({
        id: "check-cost",
        action: `Reconcile sanctioned allocation (${formatCurrencyLakh(project.sanctioned_amount_lakh)}) with actual expenditure (${formatCurrencyLakh(project.expenditure_lakh)}) and approved estimates.`,
        promptedBy: `Financial Anomaly Signal: ${costAnomalies[0].anomaly_type.replace(/_/g, " ")}`,
        category: "FINANCIAL",
      });
    }

    // 3. Physical Progress vs Financial Drawdown Mismatch Check
    const progressAnomalies = safeAnomalies.filter(
      (a) =>
        a.anomaly_type === "PROGRESS_FINANCIAL_MISMATCH" ||
        a.anomaly_type === "PROJECT_DELAY" ||
        a.anomaly_type === "SLOW_PROGRESS"
    );

    if (progressAnomalies.length > 0 || Math.abs(project.physical_progress_pct - utilizationPct) > 25) {
      checks.push({
        id: "check-progress",
        action: `Conduct geo-tagged physical site inspection to verify physical completion (${formatProgressPct(project.physical_progress_pct)}) against financial utilization (${formatFundUtilizationPct(project.expenditure_lakh, project.sanctioned_amount_lakh)}).`,
        promptedBy: `Execution Trajectory: Physical (${formatProgressPct(project.physical_progress_pct)}) vs Fund Utilization (${formatFundUtilizationPct(project.expenditure_lakh, project.sanctioned_amount_lakh)})`,
        category: "TIMELINE",
      });
    }

    // Fallback if less than 3 checks generated from anomalies
    if (checks.length === 0) {
      checks.push({
        id: "check-routine-1",
        action: `Perform routine administrative verification of implementing agency (${project.agency_id}) progress records.`,
        promptedBy: "Routine Governance Check",
        category: "ROUTINE",
      });
      checks.push({
        id: "check-routine-2",
        action: `Confirm site inspection log and milestone completion certificate before next payment cycle.`,
        promptedBy: "Routine Statutory Audit Directive",
        category: "COMPLIANCE",
      });
    }

    return checks.slice(0, 3);
  };

  const checklist = generateVerificationChecklist();

  const handleTransfer = () => {
    const lines = [
      `Consistency & Verification Plan for Project ${project.project_id}:`,
      ...checklist.map(
        (c, idx) => `${idx + 1}. [${c.category}] ${c.action} (Triggered by: ${c.promptedBy})`
      ),
    ];
    if (
      realBenchmark &&
      realBenchmark.status === "SUCCESS" &&
      typeof realBenchmark.target_amount_lakh === "number" &&
      typeof realBenchmark.peer_median_lakh === "number"
    ) {
      const diffVal = realBenchmark.percentage_difference_from_peer_median || 0;
      lines.push(
        `Real MPLADS Peer Baseline Context: Target ₹${formatLakh(
          realBenchmark.target_amount_lakh
        )}L vs Peer Median ₹${formatLakh(realBenchmark.peer_median_lakh)}L (${
          diffVal > 0 ? "+" : ""
        }${formatPct(diffVal)}% variance).`
      );
    }
    onSendToInvestigation(lines.join("\n"));
  };

  const isBenchmarkValid =
    realBenchmark &&
    realBenchmark.status === "SUCCESS" &&
    typeof realBenchmark.peer_median_lakh === "number" &&
    typeof realBenchmark.target_amount_lakh === "number";

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-5">
      {/* CARD HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-blue-600" />
            Consistency & Verification Diagnostic
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-checks detected anomaly evidence, real MPLADS peer baselines, and actionable field verification steps
          </p>
        </div>
        <span className="text-[11px] font-mono font-bold text-blue-800 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-full shrink-0">
          Automated Cross-Validation
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* COLUMN 1: DETECTED EVIDENCE & ANOMALIES (lg:col-span-5) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
              1. Detected Evidence & Signals
            </h4>
            <span className="text-[10px] font-mono font-semibold text-slate-500">
              {safeAnomalies.length} Signal{safeAnomalies.length === 1 ? "" : "s"}
            </span>
          </div>

          {safeAnomalies.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {safeAnomalies.map((anom, idx) => {
                const matchingFactor = riskProfile?.risk_factors?.find(
                  (rf) => rf.signal === anom.anomaly_type
                );

                const hasEvidence =
                  anom.evidence &&
                  typeof anom.evidence === "object" &&
                  Object.keys(anom.evidence).length > 0;

                return (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-slate-200 bg-slate-50/60 space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-slate-900 font-mono text-[11px]">
                        {(anom.anomaly_type || "ANOMALY").replace(/_/g, " ")}
                      </span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {anom.severity && <SeverityBadge severity={anom.severity} />}
                        {matchingFactor?.contribution !== undefined && (
                          <span className="font-mono text-[10px] font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                            +{matchingFactor.contribution} pts
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-600 leading-snug">
                      {anom.explanation || "No explanation provided."}
                    </p>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-200/50 font-mono">
                      <span>
                        Confidence:{" "}
                        {typeof anom.confidence === "number"
                          ? `${(anom.confidence * 100).toFixed(0)}%`
                          : "N/A"}
                      </span>
                      {hasEvidence && (
                        <span className="truncate max-w-[180px]">
                          Evidence: {JSON.stringify(anom.evidence).replace(/[{}"\\]/g, "")}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-emerald-50/50 border border-emerald-200 text-xs text-emerald-900 text-center">
              No deterministic anomaly signals detected for this project.
            </div>
          )}
        </div>

        {/* COLUMN 2: REAL MPLADS PEER BENCHMARK EVIDENCE (lg:col-span-7) */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-blue-600" />
              2. Real MPLADS Peer Comparison
            </h4>
            <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 font-mono">
              Source: Real MPLADS Historical Benchmark
            </span>
          </div>

          {isLoadingBenchmark ? (
            <div className="p-6 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-slate-200">
              Evaluating cost consistency against 14.7k real MPLADS works...
            </div>
          ) : benchmarkError ? (
            <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Real MPLADS Benchmark Notice</p>
                <p className="text-[11px] mt-0.5">{benchmarkError}</p>
              </div>
            </div>
          ) : isBenchmarkValid ? (
            <div className="space-y-3">
              {/* Metric Chips */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-bold uppercase">Target Cost</span>
                  <span className="font-mono text-xs font-bold text-slate-900 block mt-0.5">
                    ₹{formatLakh(realBenchmark!.target_amount_lakh)} L
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-bold uppercase">Peer Median</span>
                  <span className="font-mono text-xs font-bold text-slate-900 block mt-0.5">
                    ₹{formatLakh(realBenchmark!.peer_median_lakh)} L
                  </span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-bold uppercase">Cost Variance</span>
                  <div className="flex items-center gap-1 mt-0.5">
                    {(realBenchmark!.percentage_difference_from_peer_median || 0) > 0 ? (
                      <TrendingUp className="w-3 h-3 text-amber-600" />
                    ) : (realBenchmark!.percentage_difference_from_peer_median || 0) < 0 ? (
                      <TrendingDown className="w-3 h-3 text-emerald-600" />
                    ) : (
                      <Minus className="w-3 h-3 text-slate-400" />
                    )}
                    <span className="font-mono text-xs font-bold text-slate-900">
                      {(realBenchmark!.percentage_difference_from_peer_median || 0) > 0 ? "+" : ""}
                      {formatPct(realBenchmark!.percentage_difference_from_peer_median)}%
                    </span>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-bold uppercase">Comparable Peers</span>
                  <span className="font-mono text-xs font-bold text-blue-700 block mt-0.5">
                    {realBenchmark!.comparable_project_count || 0} Works
                  </span>
                </div>
              </div>

              {/* Benchmark Summary Note */}
              <div className="p-3 rounded-lg bg-slate-50/80 border border-slate-200/80 text-[11px] text-slate-700 space-y-1">
                <p className="font-medium text-slate-900 leading-snug">
                  {realBenchmark!.benchmark_insight || "Peer benchmark comparison active."}
                </p>
                <p className="text-[10px] text-slate-500">
                  Match confidence: {formatPct((realBenchmark!.matching_confidence || 0) * 100)}% • Average text similarity: {formatPct((realBenchmark!.average_peer_similarity || 0) * 100)}%
                </p>
              </div>

              {/* Top Verified Peer Snippets */}
              {Array.isArray(realBenchmark!.comparable_works) && realBenchmark!.comparable_works.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                    Top Comparable Real MPLADS Works
                  </span>
                  <div className="space-y-1">
                    {realBenchmark!.comparable_works.slice(0, 2).map((peer) => (
                      <div
                        key={peer.work_id}
                        className="p-2 rounded border border-slate-100 bg-white flex items-center justify-between text-[11px]"
                      >
                        <div className="truncate max-w-[280px]">
                          <span className="font-mono font-bold text-slate-700 mr-1.5">
                            #{peer.work_id}
                          </span>
                          <span className="text-slate-800 font-medium">{peer.work_description}</span>
                        </div>
                        <div className="text-right font-mono shrink-0 ml-2">
                          <span className="font-bold text-slate-900">₹{formatLakh(peer.amount_lakh)}L</span>
                          <span className="text-[9px] text-blue-600 block">
                            {formatPct((peer.similarity_score || 0) * 100)}% match
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center space-y-1">
              <p className="font-semibold text-slate-700">Insufficient Peer Data Available</p>
              <p className="text-[11px]">
                The real MPLADS dataset does not contain enough verified comparable works matching this category and cost range. Cost comparison omitted to prevent false conclusions.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 3: RECOMMENDED VERIFICATION CHECKLIST & INVESTIGATION TRANSFER */}
      <div className="bg-slate-50/80 rounded-xl border border-slate-200 p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-2">
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-blue-600" />
            3. Actionable Verification Checklist (Max 3 Steps)
          </h4>
          <span className="text-[10px] text-slate-500">
            Derived directly from actual anomaly evidence & peer variance
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {checklist.map((item, idx) => (
            <div
              key={item.id}
              className="p-3 rounded-lg bg-white border border-slate-200 shadow-2xs space-y-2 flex flex-col justify-between"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded font-mono bg-blue-50 text-blue-800 border border-blue-200">
                    Step {idx + 1} • {item.category}
                  </span>
                </div>
                <p className="text-xs text-slate-800 font-medium leading-snug">
                  {item.action}
                </p>
              </div>

              <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-500">
                <strong className="text-slate-700">Prompted by:</strong> {item.promptedBy}
              </div>
            </div>
          ))}
        </div>

        {/* TRANSFER TO INVESTIGATION DOCKET ACTION BAR */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-200/80">
          <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
            {canManage ? (
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                <CheckSquare className="w-3.5 h-3.5" />
                Authorized Officer Scope ({user?.role === "MOSPI_OFFICER" ? "MoSPI Officer" : `District Authority - ${project.district}`})
              </span>
            ) : (
              <span className="text-amber-700 font-medium flex items-center gap-1">
                <Lock className="w-3.5 h-3.5" />
                Read-only scope for {project.district} (Actions restricted to assigned officers)
              </span>
            )}
          </div>

          <button
            onClick={handleTransfer}
            className="w-full sm:w-auto px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-xs cursor-pointer"
          >
            <span>Transfer Verification Plan to Investigation</span>
            <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
          </button>
        </div>
      </div>
    </div>
  );
};
