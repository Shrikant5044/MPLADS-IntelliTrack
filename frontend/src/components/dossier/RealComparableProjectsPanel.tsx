import React, { useState, useEffect } from "react";
import { Project, RealWorkBenchmarkResult } from "../../types";
import { api } from "../../api/client";
import {
  Scale,
  Search,
  Sparkles,
  Building2,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Info,
} from "lucide-react";

interface RealComparableProjectsPanelProps {
  project: Project;
}

export const RealComparableProjectsPanel: React.FC<RealComparableProjectsPanelProps> = ({
  project,
}) => {
  const [dataset, setDataset] = useState<"recommended" | "completed">("recommended");
  const [customWorkId, setCustomWorkId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [benchmarkResult, setBenchmarkResult] = useState<RealWorkBenchmarkResult | null>(null);
  const [isCustomMode, setIsCustomMode] = useState<boolean>(false);

  const totalWorksInDataset = dataset === "recommended" ? "14,745" : "9,828";
  const datasetLabel = dataset === "recommended" ? "Recommended Works" : "Completed Works";

  const fetchBenchmark = (targetWorkId?: number) => {
    setLoading(true);
    setError(null);

    const amountRupees = (project.sanctioned_amount_lakh || project.estimated_cost_lakh || 0) * 100000;

    if (targetWorkId) {
      setIsCustomMode(true);
      api
        .getRealMPLADSBenchmark({
          work_id: targetWorkId,
          dataset,
          top_k: 5,
        })
        .then((res) => {
          setBenchmarkResult(res);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || "Failed to load real comparable works");
          setLoading(false);
        });
    } else {
      setIsCustomMode(false);
      api
        .getRealMPLADSBenchmark({
          description: project.work_name,
          amount: amountRupees,
          state: project.state,
          category: project.work_category,
          dataset,
          top_k: 5,
        })
        .then((res) => {
          setBenchmarkResult(res);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || "Failed to benchmark project against real MPLADS works");
          setLoading(false);
        });
    }
  };

  useEffect(() => {
    fetchBenchmark();
  }, [project.project_id, dataset]);

  const handleCustomIdSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsedId = parseInt(customWorkId.trim(), 10);
    if (!isNaN(parsedId) && parsedId > 0) {
      fetchBenchmark(parsedId);
    } else {
      fetchBenchmark();
    }
  };

  const handleResetToCurrent = () => {
    setCustomWorkId("");
    setIsCustomMode(false);
    fetchBenchmark();
  };

  // Generate standardized neutral conclusion
  const getStandardizedConclusion = (diffPct: number): string => {
    if (Math.abs(diffPct) <= 10.0) {
      return "Target amount is broadly consistent with comparable MPLADS works.";
    }
    if (diffPct > 10.0) {
      return "Target amount is substantially higher than the median of comparable MPLADS works.";
    }
    return "Target amount is substantially lower than the median of comparable MPLADS works.";
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-5">
      {/* 1. HEADER: Clear Purpose & Scope */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Scale className="w-4 h-4 text-blue-600" />
              Comparable Project Analysis
            </h3>
            <span className="px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-[10px] font-bold tracking-wider uppercase">
              Peer Benchmarking
            </span>
          </div>
          <p className="text-xs font-medium text-slate-600 mt-1">
            Real-data peer benchmarking using authentic MPLADS works.
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Compares the selected project&apos;s cost with genuinely similar works from the real MPLADS dataset.
          </p>
        </div>

        {/* Dataset Toggle */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="inline-flex rounded-lg bg-slate-100 p-0.5 border border-slate-200 text-xs font-semibold">
            <button
              onClick={() => setDataset("recommended")}
              className={`px-3 py-1 rounded-md transition-all ${
                dataset === "recommended"
                  ? "bg-white text-slate-900 shadow-xs font-bold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Recommended Works (14.7k)
            </button>
            <button
              onClick={() => setDataset("completed")}
              className={`px-3 py-1 rounded-md transition-all ${
                dataset === "completed"
                  ? "bg-white text-slate-900 shadow-xs font-bold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Completed Works (9.8k)
            </button>
          </div>
        </div>
      </div>

      {/* 2. TARGET PROJECT: Distinguish Prototype vs Real Data */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {isCustomMode ? (
              <span className="px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-900 text-[11px] font-bold tracking-wider uppercase border border-emerald-300">
                REAL MPLADS WORK • Work ID: {benchmarkResult?.target_work?.work_id}
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded bg-blue-100 text-blue-900 text-[11px] font-bold tracking-wider uppercase border border-blue-300">
                PROTOTYPE PROJECT • {project.project_id}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-[11px] text-slate-500">
              Benchmarked against: <strong>{totalWorksInDataset} real {datasetLabel.toLowerCase()}</strong>
            </span>
            <span className="px-2 py-0.5 rounded bg-white border border-slate-200 font-semibold text-slate-700 text-[11px]">
              {benchmarkResult?.amount_type || (dataset === "recommended" ? "Recommended Amount" : "Final Amount")}
            </span>
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-1">
          <p className="text-sm font-semibold text-slate-900 leading-snug">
            {benchmarkResult?.target_work?.work_description || project.work_name}
          </p>
          <div className="text-right shrink-0">
            <span className="text-[10px] font-bold text-slate-400 block uppercase">Target Cost</span>
            <span className="text-base font-bold font-mono text-slate-900">
              ₹{benchmarkResult?.target_amount_lakh !== undefined ? benchmarkResult.target_amount_lakh.toFixed(2) : project.sanctioned_amount_lakh.toFixed(2)} Lakhs
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-slate-500 border-t border-slate-200/50">
          <span>State: <strong>{benchmarkResult?.target_work?.state || project.state}</strong></span>
          <span>•</span>
          <span>Category: <strong>{benchmarkResult?.target_work?.category || project.work_category}</strong></span>
          {benchmarkResult?.target_work?.ida && (
            <>
              <span>•</span>
              <span className="truncate max-w-xs">IDA: <strong>{benchmarkResult.target_work.ida}</strong></span>
            </>
          )}
        </div>
      </div>

      {/* Loading & Error States */}
      {loading && (
        <div className="py-12 text-center space-y-2">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent"></div>
          <p className="text-xs text-slate-500">Executing TF-IDF peer matching against real MPLADS works repository...</p>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Unable to load comparable projects</p>
            <p className="mt-0.5 opacity-90">{error}</p>
          </div>
        </div>
      )}

      {/* 5. NO RELIABLE PEERS STATE */}
      {!loading && !error && benchmarkResult?.status === "INSUFFICIENT_PEERS" && (
        <div className="py-10 text-center px-4 rounded-xl bg-slate-50 border border-dashed border-slate-200 space-y-1.5">
          <Building2 className="w-8 h-8 text-slate-400 mx-auto" />
          <h4 className="text-sm font-bold text-slate-800">No reliable comparable projects found.</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            The available real MPLADS records did not contain enough sufficiently similar works above the quality threshold.
          </p>
        </div>
      )}

      {/* 3 & 4. STATISTICAL COST COMPARISON & COMPARABLE PEERS */}
      {!loading && !error && benchmarkResult?.status === "SUCCESS" && (
        <div className="space-y-5">
          {/* STATISTICAL COST COMPARISON METRICS */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Target Amount
              </span>
              <span className="font-mono text-sm font-bold text-slate-900 mt-0.5 block">
                ₹{benchmarkResult.target_amount_lakh.toFixed(2)} L
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Peer Median
              </span>
              <span className="font-mono text-sm font-bold text-slate-900 mt-0.5 block">
                ₹{benchmarkResult.peer_median_lakh.toFixed(2)} L
              </span>
              <span className="text-[10px] text-slate-400">({benchmarkResult.comparable_project_count} verified peers)</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Difference from Peer Median
              </span>
              <div className="flex items-center gap-1 mt-0.5">
                {benchmarkResult.percentage_difference_from_peer_median > 0 ? (
                  <TrendingUp className="w-3.5 h-3.5 text-amber-600" />
                ) : benchmarkResult.percentage_difference_from_peer_median < 0 ? (
                  <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <Minus className="w-3.5 h-3.5 text-slate-400" />
                )}
                <span
                  className={`font-mono text-sm font-bold ${
                    benchmarkResult.percentage_difference_from_peer_median > 35
                      ? "text-amber-700"
                      : benchmarkResult.percentage_difference_from_peer_median < -35
                      ? "text-emerald-700"
                      : "text-slate-900"
                  }`}
                >
                  {benchmarkResult.percentage_difference_from_peer_median > 0 ? "+" : ""}
                  {benchmarkResult.percentage_difference_from_peer_median.toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Avg Peer Similarity
              </span>
              <span className="font-mono text-sm font-bold text-blue-700 mt-0.5 block">
                {(benchmarkResult.average_peer_similarity * 100).toFixed(0)}%
              </span>
              <span className="text-[10px] text-slate-400">Match Confidence: {(benchmarkResult.matching_confidence * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* 4. CLEAR NEUTRAL CONCLUSION BANNER */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                Statistical Cost Comparison Conclusion
              </span>
              {benchmarkResult.percentage_difference_from_peer_median > 35 && (
                <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] font-bold border border-amber-300">
                  Requires administrative review
                </span>
              )}
            </div>

            <p className="text-xs text-slate-800 leading-relaxed font-semibold">
              {getStandardizedConclusion(benchmarkResult.percentage_difference_from_peer_median)}
            </p>
            <p className="text-[11px] text-slate-500 leading-normal">
              Target amount: ₹{benchmarkResult.target_amount_lakh.toFixed(1)} L vs Peer median: ₹{benchmarkResult.peer_median_lakh.toFixed(1)} L ({benchmarkResult.percentage_difference_from_peer_median > 0 ? "+" : ""}{benchmarkResult.percentage_difference_from_peer_median.toFixed(1)}% variance across {benchmarkResult.comparable_project_count} comparable works).
            </p>
          </div>

          {/* 3. COMPARABLE REAL MPLADS WORKS LIST */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Comparable Real MPLADS Works ({benchmarkResult.comparable_works.length} Verified Peers)
              </h4>
              <span className="text-[11px] text-slate-500">Ranked by similarity & administrative proximity</span>
            </div>

            <div className="space-y-2.5">
              {benchmarkResult.comparable_works.map((peer, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-blue-300 transition-all space-y-2 shadow-2xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                    <div className="space-y-1 max-w-2xl">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                          Work ID: {peer.work_id}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-semibold">
                          {peer.match_tier}
                        </span>
                        <span className="text-[11px] text-slate-400">•</span>
                        <span className="text-[11px] text-slate-600 font-medium">{peer.state}</span>
                      </div>
                      <p className="text-xs font-semibold text-slate-900 leading-snug">
                        {peer.work_description}
                      </p>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="font-mono text-sm font-bold text-slate-900 block">
                        ₹{peer.amount_lakh.toFixed(2)} Lakhs
                      </span>
                      <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full inline-block mt-0.5">
                        Similarity: {(peer.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-100 text-[10px] text-slate-500">
                    <div className="flex flex-wrap items-center gap-2">
                      <span>Category: <strong>{peer.category}</strong></span>
                      {peer.mp_name && (
                        <>
                          <span>•</span>
                          <span>MP: <strong>{peer.mp_name}</strong></span>
                        </>
                      )}
                      {peer.ida && (
                        <>
                          <span>•</span>
                          <span className="truncate max-w-xs">IDA: <strong>{peer.ida}</strong></span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-slate-400">
                      {peer.winning_query && (
                        <span>
                          Match: <strong className="text-slate-600 font-mono">&quot;{peer.winning_query}&quot;</strong>
                        </span>
                      )}
                      <span>Text Cosine: {(peer.text_similarity * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 7. REAL MPLADS WORK DIRECT LOOKUP BAR */}
      <form
        onSubmit={handleCustomIdSubmit}
        className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-[11px] text-slate-500 font-medium shrink-0 flex items-center gap-1">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            Direct Real Work ID Lookup:
          </span>
          <div className="relative flex-1 sm:w-48">
            <input
              type="text"
              placeholder="e.g. 1809, 2147, 849..."
              value={customWorkId}
              onChange={(e) => setCustomWorkId(e.target.value)}
              className="w-full text-xs font-mono px-2.5 py-1.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors flex items-center gap-1 shrink-0"
          >
            <Search className="w-3 h-3" />
            Lookup
          </button>
        </div>

        {isCustomMode && (
          <button
            type="button"
            onClick={handleResetToCurrent}
            className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            Reset to Current Prototype Project ({project.project_id})
          </button>
        )}
      </form>
    </div>
  );
};
