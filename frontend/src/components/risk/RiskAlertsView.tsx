import React, { useState, useMemo } from "react";
import {
  Project,
  ProjectRiskProfile,
  AnomalyResult,
} from "../../types";
import { RiskBadge } from "../common/RiskBadge";
import { SeverityBadge } from "../common/SeverityBadge";
import { EmptyState } from "../common/EmptyState";
import {
  formatCurrencyLakh,
  formatProgressPct,
  formatPlannedTargetPct,
} from "../../utils/formatters";
import {
  Search,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  FileText,
  Copy,
  ExternalLink,
  ShieldAlert,
  RotateCcw,
} from "lucide-react";

interface RiskAlertsViewProps {
  projects: Project[];
  riskProfiles: ProjectRiskProfile[];
  anomalies: AnomalyResult[];
  onSelectProject: (projectId: string) => void;
}

export const RiskAlertsView: React.FC<RiskAlertsViewProps> = ({
  projects,
  riskProfiles,
  anomalies,
  onSelectProject,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRiskLevel, setSelectedRiskLevel] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedDomain, setSelectedDomain] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<"RISK_DESC" | "RISK_ASC" | "ANOMALIES_DESC">("RISK_DESC");
  const [expandedProjectId, setExpandedProjectId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"ALL_ALERTS" | "DUPLICATES">("ALL_ALERTS");

  // Geographic Hierarchy Filters
  const [selectedState, setSelectedState] = useState<string>("ALL");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("ALL");
  const [selectedConstituency, setSelectedConstituency] = useState<string>("ALL");

  const projMap = useMemo(() => {
    const map = new Map<string, Project>();
    projects.forEach((p) => map.set(p.project_id, p));
    return map;
  }, [projects]);

  const anomMap = useMemo(() => {
    const map = new Map<string, AnomalyResult[]>();
    anomalies.forEach((a) => {
      const arr = map.get(a.project_id) || [];
      arr.push(a);
      map.set(a.project_id, arr);
    });
    return map;
  }, [anomalies]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    projects.forEach((p) => {
      if (p.work_category) set.add(p.work_category);
    });
    return Array.from(set).sort();
  }, [projects]);

  // Hierarchical Options Computation
  const availableStates = useMemo(() => {
    const set = new Set<string>();
    projects.forEach((p) => {
      if (p.state) set.add(p.state);
    });
    return Array.from(set).sort();
  }, [projects]);

  const availableDistricts = useMemo(() => {
    const set = new Set<string>();
    projects.forEach((p) => {
      if (selectedState === "ALL" || p.state === selectedState) {
        if (p.district) set.add(p.district);
      }
    });
    return Array.from(set).sort();
  }, [projects, selectedState]);

  const availableConstituencies = useMemo(() => {
    const set = new Set<string>();
    projects.forEach((p) => {
      const matchState = selectedState === "ALL" || p.state === selectedState;
      const matchDistrict = selectedDistrict === "ALL" || p.district === selectedDistrict;
      if (matchState && matchDistrict) {
        if (p.constituency) set.add(p.constituency);
      }
    });
    return Array.from(set).sort();
  }, [projects, selectedState, selectedDistrict]);

  const handleStateChange = (st: string) => {
    setSelectedState(st);
    if (st === "ALL") {
      setSelectedDistrict("ALL");
      setSelectedConstituency("ALL");
    } else {
      const validDistricts = new Set(
        projects.filter((p) => p.state === st).map((p) => p.district)
      );
      if (selectedDistrict !== "ALL" && !validDistricts.has(selectedDistrict)) {
        setSelectedDistrict("ALL");
      }
      setSelectedConstituency("ALL");
    }
  };

  const handleDistrictChange = (dist: string) => {
    setSelectedDistrict(dist);
    if (dist === "ALL") {
      setSelectedConstituency("ALL");
    } else {
      const validConstituencies = new Set(
        projects.filter((p) => p.district === dist && (selectedState === "ALL" || p.state === selectedState)).map((p) => p.constituency)
      );
      if (selectedConstituency !== "ALL" && !validConstituencies.has(selectedConstituency)) {
        setSelectedConstituency("ALL");
      }
    }
  };

  const handleConstituencyChange = (c: string) => {
    setSelectedConstituency(c);
  };

  const handleResetGeoFilters = () => {
    setSelectedState("ALL");
    setSelectedDistrict("ALL");
    setSelectedConstituency("ALL");
  };

  const hasActiveGeoFilter =
    selectedState !== "ALL" ||
    selectedDistrict !== "ALL" ||
    selectedConstituency !== "ALL";

  const duplicatePairs = useMemo(() => {
    const dupAnoms = anomalies.filter((a) => a.anomaly_type === "POTENTIAL_DUPLICATE_WORK");
    const pairMap = new Map<string, { p1: Project; p2: Project; anom: AnomalyResult }>();

    dupAnoms.forEach((a) => {
      const matchedId = a.evidence?.matched_project_id;
      if (!matchedId) return;
      const key = [a.project_id, matchedId].sort().join("::");
      if (!pairMap.has(key)) {
        const p1 = projMap.get(a.project_id);
        const p2 = projMap.get(matchedId);
        if (p1 && p2) {
          pairMap.set(key, { p1, p2, anom: a });
        }
      }
    });

    return Array.from(pairMap.values());
  }, [anomalies, projMap]);

  const filteredProfiles = useMemo(() => {
    return riskProfiles.filter((rp) => {
      const p = projMap.get(rp.project_id);
      if (!p) return false;

      if (selectedRiskLevel !== "ALL" && rp.risk_level !== selectedRiskLevel) {
        return false;
      }

      if (selectedCategory !== "ALL" && p.work_category !== selectedCategory) {
        return false;
      }

      if (selectedState !== "ALL" && p.state !== selectedState) {
        return false;
      }

      if (selectedDistrict !== "ALL" && p.district !== selectedDistrict) {
        return false;
      }

      if (selectedConstituency !== "ALL" && p.constituency !== selectedConstituency) {
        return false;
      }

      if (selectedDomain !== "ALL") {
        const pAnoms = anomMap.get(rp.project_id) || [];
        if (selectedDomain === "FINANCIAL") {
          if (!pAnoms.some((a) => ["EXPENDITURE_EXCEEDS_SANCTION", "COST_OVERRUN", "ABNORMALLY_HIGH_UTILIZATION", "ABNORMALLY_LOW_UTILIZATION", "PROGRESS_FINANCIAL_MISMATCH", "UNUSUAL_EXPENDITURE_PATTERN"].includes(a.anomaly_type))) return false;
        } else if (selectedDomain === "PROGRESS") {
          if (!pAnoms.some((a) => ["PROJECT_DELAY", "SLOW_PROGRESS", "NO_RECENT_PROGRESS_UPDATE", "SUDDEN_PROGRESS_JUMP", "MILESTONE_LAG", "COMPLETION_RISK"].includes(a.anomaly_type))) return false;
        } else if (selectedDomain === "PAYMENT") {
          if (!pAnoms.some((a) => ["LARGE_PAYMENT", "RAPID_MULTIPLE_PAYMENTS", "REPEATED_PAYMENT_AMOUNT", "PAYMENT_BEFORE_MILESTONE", "PAYMENT_LOW_PROGRESS", "DEADLINE_PAYMENT_CONCENTRATION"].includes(a.anomaly_type))) return false;
        } else if (selectedDomain === "VENDOR_AGENCY") {
          if (!pAnoms.some((a) => ["VENDOR_HIGH_DELAY_RATE", "VENDOR_HIGH_COST_ANOMALY_RATE", "VENDOR_HIGH_PAYMENT_ANOMALY_RATE", "VENDOR_PROJECT_CONCENTRATION", "AGENCY_HIGH_ANOMALY_RATE", "AGENCY_REPEATED_ISSUES"].includes(a.anomaly_type))) return false;
        } else if (selectedDomain === "DUPLICATE") {
          if (!pAnoms.some((a) => a.anomaly_type === "POTENTIAL_DUPLICATE_WORK")) return false;
        } else if (selectedDomain === "COMPLIANCE") {
          if (!pAnoms.some((a) => a.anomaly_type.startsWith("MISSING_") || a.anomaly_type === "COMPLIANCE_DOCUMENT_GAP")) return false;
        }
      }

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchId = rp.project_id.toLowerCase().includes(q);
        const matchName = p.work_name.toLowerCase().includes(q);
        const matchDist = p.district.toLowerCase().includes(q);
        const matchConst = p.constituency ? p.constituency.toLowerCase().includes(q) : false;
        if (!matchId && !matchName && !matchDist && !matchConst) return false;
      }

      return true;
    }).sort((a, b) => {
      if (sortBy === "RISK_DESC") return b.risk_score - a.risk_score;
      if (sortBy === "RISK_ASC") return a.risk_score - b.risk_score;
      if (sortBy === "ANOMALIES_DESC") {
        const cntA = anomMap.get(a.project_id)?.length || 0;
        const cntB = anomMap.get(b.project_id)?.length || 0;
        return cntB - cntA;
      }
      return 0;
    });
  }, [
    riskProfiles,
    projMap,
    anomMap,
    selectedRiskLevel,
    selectedCategory,
    selectedDomain,
    selectedState,
    selectedDistrict,
    selectedConstituency,
    searchQuery,
    sortBy,
  ]);


  const toggleExpand = (pid: string) => {
    setExpandedProjectId(expandedProjectId === pid ? null : pid);
  };

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Risk & Anomaly Investigation
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Prioritized worklist for monitoring authorities with evidence trails and targeted recommendations.
          </p>
        </div>

        <div className="flex items-center rounded-lg border border-slate-200 p-1 bg-white shadow-sm">
          <button
            onClick={() => setViewMode("ALL_ALERTS")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              viewMode === "ALL_ALERTS"
                ? "bg-slate-900 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            All Risk Alerts ({filteredProfiles.length})
          </button>
          <button
            onClick={() => setViewMode("DUPLICATES")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
              viewMode === "DUPLICATES"
                ? "bg-slate-900 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Copy className="w-3.5 h-3.5" />
            Duplicate Works ({duplicatePairs.length} Pairs)
          </button>
        </div>
      </div>

      {viewMode === "DUPLICATES" ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 text-xs text-blue-900">
            <div className="font-bold flex items-center gap-2 text-sm text-blue-950">
              <Copy className="w-4 h-4 text-blue-700" />
              12 Suspected Duplicate Pairs Detected (24 Projects Total)
            </div>
            <p className="mt-1 text-blue-800/90 leading-relaxed">
              Flagged by multi-factor similarity: <strong>GPS Haversine distance (&le; 3.0 km)</strong>, <strong>lexical work-name similarity</strong>, <strong>work category match</strong>, and <strong>comparable sanctioned amount</strong> (&ge; 0.65 threshold).
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {duplicatePairs.map(({ p1, p2, anom }, idx) => {
              const distKm = anom.evidence?.distance_km ?? 0;
              const simScore = anom.evidence?.similarity_score ?? 0.85;

              return (
                <div
                  key={idx}
                  className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-slate-300 transition-all"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded bg-blue-100 text-blue-800 text-xs font-bold font-mono">
                        Pair #{idx + 1}
                      </span>
                      <span className="text-xs font-semibold text-slate-700">
                        {p1.district}, {p1.state}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-xs text-slate-600">
                        Distance: <strong className="text-slate-900 font-mono">{distKm.toFixed(2)} km</strong>
                      </div>
                      <div className="text-xs text-slate-600">
                        Similarity: <strong className="text-blue-700 font-mono">{(simScore * 100).toFixed(0)}%</strong>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-lg border border-slate-200 p-4 bg-slate-50/40">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="font-mono text-xs font-bold text-slate-500">
                            {p1.project_id}
                          </span>
                          <h4 className="text-sm font-bold text-slate-900 mt-0.5">
                            {p1.work_name}
                          </h4>
                        </div>
                        <button
                          onClick={() => onSelectProject(p1.project_id)}
                          className="text-xs text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-0.5"
                        >
                          Dossier <ExternalLink className="w-3 h-3 ml-0.5" />
                        </button>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-200/60">
                        <div>
                          <span className="text-slate-400 text-[11px]">Sanction:</span>
                          <div className="font-bold text-slate-800">{formatCurrencyLakh(p1.sanctioned_amount_lakh)}</div>
                        </div>
                        <div>
                          <span className="text-slate-400 text-[11px]">Progress:</span>
                          <div className="font-bold text-slate-800">{formatProgressPct(p1.physical_progress_pct)}</div>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-lg border border-slate-200 p-4 bg-slate-50/40">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="font-mono text-xs font-bold text-slate-500">
                            {p2.project_id}
                          </span>
                          <h4 className="text-sm font-bold text-slate-900 mt-0.5">
                            {p2.work_name}
                          </h4>
                        </div>
                        <button
                          onClick={() => onSelectProject(p2.project_id)}
                          className="text-xs text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-0.5"
                        >
                          Dossier <ExternalLink className="w-3 h-3 ml-0.5" />
                        </button>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-200/60">
                        <div>
                          <span className="text-slate-400 text-[11px]">Sanction:</span>
                          <div className="font-bold text-slate-800">{formatCurrencyLakh(p2.sanctioned_amount_lakh)}</div>
                        </div>
                        <div>
                          <span className="text-slate-400 text-[11px]">Progress:</span>
                          <div className="font-bold text-slate-800">{formatProgressPct(p2.physical_progress_pct)}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <div className="text-slate-700">
                      <strong className="text-slate-900">Why flagged:</strong> Both works share near-identical descriptions, same {p1.work_category} category, and are located within {distKm.toFixed(2)} km of each other.
                    </div>
                    <div className="text-blue-900 font-semibold shrink-0">
                      Recommendation: Conduct on-site GPS verification & MB inspection
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2.5">
              {/* Search */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search projects..."
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
                />
              </div>

              {/* Risk Level */}
              <div>
                <select
                  value={selectedRiskLevel}
                  onChange={(e) => setSelectedRiskLevel(e.target.value)}
                  className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium truncate"
                >
                  <option value="ALL">All Risk Levels</option>
                  <option value="HIGH">High Risk (50-74)</option>
                  <option value="MEDIUM">Medium Risk (25-49)</option>
                  <option value="LOW">Low Risk (0-24)</option>
                </select>
              </div>

              {/* 1. State Filter */}
              <div>
                <select
                  value={selectedState}
                  onChange={(e) => handleStateChange(e.target.value)}
                  className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium truncate"
                >
                  <option value="ALL">All States</option>
                  {availableStates.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              {/* 2. District Filter */}
              <div>
                <select
                  value={selectedDistrict}
                  onChange={(e) => handleDistrictChange(e.target.value)}
                  className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium truncate"
                >
                  <option value="ALL">All Districts ({availableDistricts.length})</option>
                  {availableDistricts.map((dist) => (
                    <option key={dist} value={dist}>
                      {dist}
                    </option>
                  ))}
                </select>
              </div>

              {/* 3. Constituency Filter */}
              <div>
                <select
                  value={selectedConstituency}
                  onChange={(e) => handleConstituencyChange(e.target.value)}
                  className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium truncate"
                >
                  <option value="ALL">All ({availableConstituencies.length})</option>
                  {availableConstituencies.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              {/* Category Filter */}
              <div>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium truncate"
                >
                  <option value="ALL">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sort By */}
              <div>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="w-full py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium truncate"
                >
                  <option value="RISK_DESC">Sort: Highest Risk</option>
                  <option value="ANOMALIES_DESC">Sort: Most Anomalies</option>
                  <option value="RISK_ASC">Sort: Lowest Risk</option>
                </select>
              </div>
            </div>

            {/* Showing Count & Active Scope Status */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-700 font-bold">
                  Showing {filteredProfiles.length} priority projects
                </span>
                {hasActiveGeoFilter && (
                  <span className="text-[11px] text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100 font-medium">
                    Filtered by: {selectedState !== "ALL" ? selectedState : "All States"}
                    {selectedDistrict !== "ALL" ? ` • ${selectedDistrict}` : ""}
                    {selectedConstituency !== "ALL" ? ` • ${selectedConstituency}` : ""}
                  </span>
                )}
              </div>
              {hasActiveGeoFilter && (
                <button
                  onClick={handleResetGeoFilters}
                  className="flex items-center gap-1 text-[11px] font-bold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded transition-colors cursor-pointer"
                >
                  <RotateCcw className="w-3 h-3 text-slate-400" />
                  <span>Reset Geo</span>
                </button>
              )}
            </div>


            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1">
                Domain Filter:
              </span>
              {[
                { id: "ALL", label: "All Signals" },
                { id: "FINANCIAL", label: "Financial & Cost" },
                { id: "PROGRESS", label: "Progress & Timeline" },
                { id: "PAYMENT", label: "Payment Irregularities" },
                { id: "VENDOR_AGENCY", label: "Vendor & Agency" },
                { id: "DUPLICATE", label: "Potential Duplicate Works" },
                { id: "COMPLIANCE", label: "Statutory Compliance" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSelectedDomain(tab.id)}
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors ${
                    selectedDomain === tab.id
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {filteredProfiles.length === 0 ? (
            <EmptyState
              title="No risk alerts match filters"
              description="Try adjusting your search query, risk level, or anomaly domain filters."
              actionText="Reset All Filters"
              onAction={() => {
                setSearchQuery("");
                setSelectedRiskLevel("ALL");
                setSelectedCategory("ALL");
                setSelectedDomain("ALL");
              }}
            />
          ) : (
            <div className="space-y-3">
              {filteredProfiles.map((rp) => {
                const proj = projMap.get(rp.project_id);
                const pAnoms = anomMap.get(rp.project_id) || [];
                const isExpanded = expandedProjectId === rp.project_id;

                const primaryFactors = rp.risk_factors.slice(0, 3);

                return (
                  <div
                    key={rp.project_id}
                    className={`bg-white rounded-xl border transition-all shadow-xs overflow-hidden ${
                      isExpanded
                        ? "border-blue-300 ring-1 ring-blue-100"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div
                      onClick={() => toggleExpand(rp.project_id)}
                      className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3 cursor-pointer hover:bg-slate-50/50"
                    >
                      <div className="flex items-start gap-3">
                        <div className="shrink-0 mt-0.5">
                          <RiskBadge level={rp.risk_level} score={rp.risk_score} size="md" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-slate-500">
                              {rp.project_id}
                            </span>
                            <span className="text-slate-300">•</span>
                            <span className="text-xs text-slate-500">
                              {proj?.district}, {proj?.state}
                            </span>
                          </div>
                          <h3 className="text-sm font-bold text-slate-900 mt-0.5">
                            {proj?.work_name || rp.project_id}
                          </h3>
                        </div>
                      </div>

                      <div className="flex items-center justify-between md:justify-end gap-4 shrink-0">
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                          <span>
                            <strong>{pAnoms.length}</strong> Anomaly Flags
                          </span>
                        </div>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectProject(rp.project_id);
                          }}
                          className="px-3 py-1 text-xs font-semibold rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors inline-flex items-center gap-1"
                        >
                          View Dossier
                        </button>

                        <div className="text-slate-400">
                          {isExpanded ? (
                            <ChevronUp className="w-5 h-5" />
                          ) : (
                            <ChevronDown className="w-5 h-5" />
                          )}
                        </div>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="p-5 border-t border-slate-100 bg-slate-50/60 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="bg-white rounded-lg p-4 border border-slate-200">
                            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                              <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                              Why is this flagged?
                            </h4>
                            <div className="space-y-2">
                              {primaryFactors.map((rf, idx) => (
                                <div key={idx} className="text-xs">
                                  <div className="flex items-center justify-between">
                                    <span className="font-semibold text-slate-800">
                                      {rf.signal.replace(/_/g, " ")}
                                    </span>
                                    <span className="text-[11px] font-bold text-slate-500 font-mono">
                                      +{rf.contribution} pts
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2 mt-0.5">
                                    <SeverityBadge severity={rf.severity} />
                                    <span className="text-[11px] text-slate-400">
                                      {(rf.confidence * 100).toFixed(0)}% conf
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="bg-white rounded-lg p-4 border border-slate-200">
                            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-blue-600" />
                              Ground Truth Evidence
                            </h4>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <span className="text-slate-400 text-[11px]">Physical Progress:</span>
                                <div className="font-bold text-slate-800">{formatProgressPct(proj?.physical_progress_pct)}</div>
                              </div>
                              <div>
                                <span className="text-slate-400 text-[11px]">Planned Target:</span>
                                <div className="font-bold text-slate-800">{formatPlannedTargetPct(proj?.planned_progress_pct)}</div>
                              </div>
                              <div>
                                <span className="text-slate-400 text-[11px]">Sanctioned Budget:</span>
                                <div className="font-bold text-slate-800">{formatCurrencyLakh(proj?.sanctioned_amount_lakh)}</div>
                              </div>
                              <div>
                                <span className="text-slate-400 text-[11px]">Cumulative Paid:</span>
                                <div className="font-bold text-slate-800">{formatCurrencyLakh(proj?.expenditure_lakh)}</div>
                              </div>
                            </div>
                          </div>

                          <div className="bg-white rounded-lg p-4 border border-slate-200 flex flex-col justify-between">
                            <div>
                              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                Recommended Action
                              </h4>
                              <p className="text-xs text-slate-700 leading-relaxed font-medium">
                                {rp.recommended_action}
                              </p>
                            </div>

                            <button
                              onClick={() => onSelectProject(rp.project_id)}
                              className="mt-3 w-full py-1.5 text-xs font-semibold rounded bg-slate-900 text-white hover:bg-slate-800 transition-colors text-center"
                            >
                              Open Complete Dossier
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
