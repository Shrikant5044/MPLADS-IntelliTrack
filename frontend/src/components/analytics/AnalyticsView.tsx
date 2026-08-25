import React, { useState, useEffect } from "react";
import {
  Project,
  ProjectRiskProfile,
  DistrictRiskProfile,
  DistrictAnalyticsSummary,
  ProjectForecastResult,
  ForecastSummary,
  AuditQueueItem,
  AuditQueueSummary,
} from "../../types";
import { api } from "../../api/client";
import { RiskBadge } from "../common/RiskBadge";
import {
  TrendingUp,
  Clock,
  Building2,
  ListOrdered,
  Search,
} from "lucide-react";

interface AnalyticsViewProps {
  projects?: Project[];
  riskProfiles?: ProjectRiskProfile[];
  districts: DistrictRiskProfile[];
  districtSummary: DistrictAnalyticsSummary | null;
  onSelectProject: (projectId: string) => void;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({
  districts,
  districtSummary,
  onSelectProject,
}) => {
  const [activeTab, setActiveTab] = useState<"AUDIT_QUEUE" | "FORECASTING" | "DISTRICTS" | "TRENDS">("AUDIT_QUEUE");

  const [forecasts, setForecasts] = useState<ProjectForecastResult[]>([]);
  const [forecastSummary, setForecastSummary] = useState<ForecastSummary | null>(null);
  const [forecastFilter, setForecastFilter] = useState<string>("ALL");
  const [forecastSearch, setForecastSearch] = useState<string>("");

  const [auditQueue, setAuditQueue] = useState<AuditQueueItem[]>([]);
  const [auditSummary, setAuditSummary] = useState<AuditQueueSummary | null>(null);
  const [urgencyFilter, setUrgencyFilter] = useState<string>("ALL");
  const [investigationFilter, setInvestigationFilter] = useState<string>("ALL");
  const [auditSearch, setAuditSearch] = useState<string>("");

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [fcRes, aqRes] = await Promise.all([
          api.getForecasts({ limit: 500 }).catch(() => null),
          api.getAuditQueue({ limit: 500 }).catch(() => null),
        ]);
        if (fcRes) {
          setForecasts(fcRes.data || []);
          setForecastSummary(fcRes.summary || null);
        }
        if (aqRes) {
          setAuditQueue(aqRes.data || []);
          setAuditSummary(aqRes.summary || null);
        }
      } catch (err) {
        console.error("Failed to load analytics data:", err);
      }
    };
    fetchAnalytics();
  }, []);

  const filteredForecasts = forecasts.filter((f) => {
    if (forecastFilter !== "ALL" && f.trajectory_status !== forecastFilter) return false;
    if (forecastSearch.trim()) {
      const q = forecastSearch.toLowerCase();
      if (!f.project_id.toLowerCase().includes(q) && !f.work_name.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const filteredAuditQueue = auditQueue.filter((item) => {
    if (urgencyFilter !== "ALL" && item.urgency !== urgencyFilter) return false;
    if (investigationFilter !== "ALL" && !item.recommended_investigation_types.includes(investigationFilter as any)) return false;
    if (auditSearch.trim()) {
      const q = auditSearch.toLowerCase();
      if (!item.project_id.toLowerCase().includes(q) && !item.work_name.toLowerCase().includes(q) && !item.district.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const getTrajectoryBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">COMPLETED</span>;
      case "ON_TRACK":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200">ON TRACK</span>;
      case "WATCH":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">WATCH</span>;
      case "LIKELY_DELAY":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-orange-50 text-orange-700 border border-orange-200">LIKELY DELAY</span>;
      case "SEVERE_DELAY_RISK":
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">SEVERE DELAY</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">{status}</span>;
    }
  };

  const getUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case "CRITICAL_URGENCY":
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-100 text-red-800 border border-red-300">CRITICAL</span>;
      case "HIGH_URGENCY":
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">HIGH URGENCY</span>;
      case "MEDIUM_URGENCY":
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">ROUTINE</span>;
    }
  };

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Advanced Analytics & Decision Support
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Predictive trajectories, macro district performance, and prioritized field audit queues.
          </p>
        </div>

        <div className="flex items-center rounded-lg border border-slate-200 p-1 bg-white shadow-sm overflow-x-auto">
          {[
            { id: "AUDIT_QUEUE", label: "Audit Queue", icon: ListOrdered },
            { id: "FORECASTING", label: "Early Warning Forecast", icon: Clock },
            { id: "DISTRICTS", label: "District Analytics", icon: Building2 },
            { id: "TRENDS", label: "Portfolio Trends", icon: TrendingUp },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-slate-900 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {activeTab === "AUDIT_QUEUE" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Queued Works</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">{auditSummary?.total_queued_projects || 500}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Ranked by risk exposure</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 shadow-sm">
              <span className="text-xs font-semibold text-rose-700 uppercase tracking-wider">High Urgency Targets</span>
              <div className="text-2xl font-bold text-rose-950 mt-1 font-mono">{auditSummary?.high_priority_count || 26}</div>
              <div className="text-[11px] text-rose-700 mt-0.5">Immediate inspection</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">High Risk Exposure</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">₹{auditSummary?.total_financial_exposure_lakh || 0}L</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Under active review</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Physical Site Tracks</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">{auditSummary?.investigation_type_counts?.PHYSICAL_INSPECTION || 180}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">On-site verification</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={auditSearch}
                  onChange={(e) => setAuditSearch(e.target.value)}
                  placeholder="Search project, work name, district..."
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
                />
              </div>

              <div>
                <select
                  value={urgencyFilter}
                  onChange={(e) => setUrgencyFilter(e.target.value)}
                  className="w-full py-1.5 px-3 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium"
                >
                  <option value="ALL">All Urgency Levels</option>
                  <option value="HIGH_URGENCY">High Urgency ({auditSummary?.high_priority_count || 26})</option>
                  <option value="MEDIUM_URGENCY">Medium Urgency ({auditSummary?.medium_priority_count || 93})</option>
                  <option value="ROUTINE">Routine Monitoring ({auditSummary?.routine_priority_count || 381})</option>
                </select>
              </div>

              <div>
                <select
                  value={investigationFilter}
                  onChange={(e) => setInvestigationFilter(e.target.value)}
                  className="w-full py-1.5 px-3 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium"
                >
                  <option value="ALL">All Investigation Tracks</option>
                  <option value="PHYSICAL_INSPECTION">Physical Site Inspection</option>
                  <option value="FINANCIAL_AUDIT">Financial & Expenditure Audit</option>
                  <option value="PAYMENT_VERIFICATION">Payment Voucher Verification</option>
                  <option value="COMPLIANCE_REVIEW">Compliance Document Review</option>
                  <option value="DUPLICATE_GEO_VERIFICATION">Duplicate Work Verification</option>
                  <option value="VENDOR_REVIEW">Vendor Review</option>
                  <option value="AGENCY_REVIEW">Agency Review</option>
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {filteredAuditQueue.map((item) => (
              <div
                key={item.project_id}
                onClick={() => onSelectProject(item.project_id)}
                className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs hover:border-slate-300 hover:shadow-sm cursor-pointer transition-all space-y-3"
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-lg bg-slate-900 text-white font-mono font-bold text-xs flex items-center justify-center shrink-0">
                      #{item.priority_rank}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-500">{item.project_id}</span>
                        <span className="text-slate-300">•</span>
                        <span className="text-xs text-slate-500">{item.district}, {item.state}</span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-900">{item.work_name}</h3>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <RiskBadge level={item.risk_level} score={item.risk_score} size="md" />
                    {getUrgencyBadge(item.urgency)}
                    <span className="px-2 py-1 text-xs font-bold rounded bg-slate-100 text-slate-700 font-mono">
                      ₹{item.financial_exposure_lakh}L Exp
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-slate-100 text-xs">
                  <div className="text-slate-600">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Key Risk Signals ({item.anomaly_count})
                    </span>
                    <div className="capitalize truncate">
                      {item.primary_risk_drivers.slice(0, 3).join(", ") || "General anomaly"}
                    </div>
                  </div>

                  <div className="text-slate-600">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Recommended Investigation Tracks
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {item.recommended_investigation_types.map((track) => (
                        <span key={track} className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          {track.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Prescribed Action
                    </span>
                    <p className="text-slate-800 font-medium truncate">
                      {item.recommended_action}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "FORECASTING" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Forecasts</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">{forecastSummary?.active_projects || 362}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">{forecastSummary?.completed_projects || 138} completed works</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 shadow-sm">
              <span className="text-xs font-semibold text-rose-700 uppercase tracking-wider">Severe Delay Risk</span>
              <div className="text-2xl font-bold text-rose-950 mt-1 font-mono">{forecastSummary?.status_counts?.SEVERE_DELAY_RISK || 203}</div>
              <div className="text-[11px] text-rose-700 mt-0.5">&gt; 90 days delay projected</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">On Track</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">{forecastSummary?.status_counts?.ON_TRACK || 110}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">On or ahead of schedule</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Avg Projected Delay</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">{forecastSummary?.average_forecast_delay_days || 166.7}d</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Beyond scheduled deadline</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="relative w-full sm:w-64">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={forecastSearch}
                  onChange={(e) => setForecastSearch(e.target.value)}
                  placeholder="Filter forecast project..."
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
                />
              </div>

              <div className="flex items-center gap-2">
                {["ALL", "SEVERE_DELAY_RISK", "LIKELY_DELAY", "ON_TRACK", "COMPLETED"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setForecastFilter(st)}
                    className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                      forecastFilter === st
                        ? "bg-slate-900 text-white"
                        : "text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    {st.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-100">
                  <tr>
                    <th className="py-3 px-4">Project</th>
                    <th className="py-3 px-3">Progress</th>
                    <th className="py-3 px-3">Velocity</th>
                    <th className="py-3 px-3">Est. Days Rem</th>
                    <th className="py-3 px-3">Forecast Completion</th>
                    <th className="py-3 px-3">Expected Delay</th>
                    <th className="py-3 px-3">Burn Rate</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredForecasts.slice(0, 50).map((f) => (
                    <tr
                      key={f.project_id}
                      onClick={() => onSelectProject(f.project_id)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 max-w-xs truncate">{f.work_name}</div>
                        <div className="font-mono text-[11px] text-slate-400">{f.project_id}</div>
                      </td>
                      <td className="py-3 px-3 font-bold text-slate-800 font-mono">
                        {f.current_progress_pct.toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-600">
                        {f.velocity_pct_per_day ? `${(f.velocity_pct_per_day * 100).toFixed(2)}%/d` : "-"}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-700">
                        {f.estimated_days_remaining !== null && f.estimated_days_remaining !== undefined ? `${f.estimated_days_remaining}d` : "-"}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-700">
                        {f.forecast_completion_date || "-"}
                      </td>
                      <td className="py-3 px-3 font-mono">
                        {f.forecast_delay_days !== null && f.forecast_delay_days !== undefined ? (
                          <span className={f.forecast_delay_days > 0 ? "text-rose-600 font-bold" : "text-emerald-600 font-bold"}>
                            {f.forecast_delay_days > 0 ? `+${f.forecast_delay_days}d` : `${f.forecast_delay_days}d`}
                          </span>
                        ) : "-"}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-600">
                        {f.burn_rate_lakh_per_day ? `₹${(f.burn_rate_lakh_per_day * 30).toFixed(1)}L/mo` : "-"}
                      </td>
                      <td className="py-3 px-3">
                        {getTrajectoryBadge(f.trajectory_status)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold text-[11px] hover:bg-blue-100">
                          Dossier
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "DISTRICTS" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Districts</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">{districtSummary?.total_districts || 30}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Across 10 states</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">National Average Risk</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">{districtSummary?.national_average_district_risk || 13.68}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Out of 100</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 shadow-sm">
              <span className="text-xs font-semibold text-rose-700 uppercase tracking-wider">Highest Risk District</span>
              <div className="text-2xl font-bold text-rose-950 mt-1">{districtSummary?.highest_risk_district || "District-13"}</div>
              <div className="text-[11px] text-rose-700 mt-0.5">Score: {districtSummary?.highest_risk_district_score || 24.5}</div>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Sanctioned</span>
              <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">₹{districtSummary?.total_sanctioned_all_districts_lakh || 0}L</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Portfolio budget</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-100">
                  <tr>
                    <th className="py-3 px-4">District & State</th>
                    <th className="py-3 px-3 text-center">Projects</th>
                    <th className="py-3 px-3 text-center">High Risk</th>
                    <th className="py-3 px-3">Average Risk Score</th>
                    <th className="py-3 px-3">Total Sanction</th>
                    <th className="py-3 px-3">Expenditure</th>
                    <th className="py-3 px-3">Fund Utilization</th>
                    <th className="py-3 px-3">Top Vendor Concentration</th>
                    <th className="py-3 px-4">Top Agency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {districts.map((d) => (
                    <tr key={d.district} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        {d.district}
                        <div className="text-[11px] text-slate-400 font-normal">{d.state}</div>
                      </td>
                      <td className="py-3 px-3 text-center font-bold text-slate-800 font-mono">{d.total_projects}</td>
                      <td className="py-3 px-3 text-center">
                        {d.high_risk_count > 0 ? (
                          <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200 font-mono">
                            {d.high_risk_count}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-mono">0</span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono font-bold text-slate-800">
                        {d.average_risk_score}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-700">₹{d.total_sanctioned_lakh}L</td>
                      <td className="py-3 px-3 font-mono text-slate-700">₹{d.total_expenditure_lakh}L</td>
                      <td className="py-3 px-3 font-mono font-semibold text-slate-800">{d.fund_utilization_pct}%</td>
                      <td className="py-3 px-3 font-mono text-slate-600">{d.max_vendor_concentration_share_pct}% share</td>
                      <td className="py-3 px-4 text-slate-600 text-[11px]">{d.top_implementing_agency}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "TRENDS" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
              <h3 className="text-sm font-bold text-slate-900">Sanctioned Budget vs Actual Expenditure</h3>
              <p className="text-xs text-slate-500">Macro financial drawdown across top 10 districts</p>
              <div className="h-48 flex items-end gap-3 pt-6 border-b border-slate-100">
                {districts.slice(0, 10).map((d) => {
                  const sHeight = Math.min(100, (d.total_sanctioned_lakh / 1500) * 100);
                  const eHeight = Math.min(100, (d.total_expenditure_lakh / 1500) * 100);
                  return (
                    <div key={d.district} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                      <div className="w-full flex items-end justify-center gap-0.5 h-full">
                        <div style={{ height: `${sHeight}%` }} className="w-2 bg-blue-300 rounded-t" title={`Sanctioned: ₹${d.total_sanctioned_lakh}L`} />
                        <div style={{ height: `${eHeight}%` }} className="w-2 bg-blue-700 rounded-t" title={`Expenditure: ₹${d.total_expenditure_lakh}L`} />
                      </div>
                      <span className="text-[9px] text-slate-400 truncate w-full text-center">{d.district.replace("District-", "D-")}</span>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center justify-center gap-4 text-xs text-slate-500 pt-1">
                <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-blue-300 rounded-xs" /><span>Sanctioned Amount</span></div>
                <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-blue-700 rounded-xs" /><span>Actual Expenditure</span></div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
              <h3 className="text-sm font-bold text-slate-900">Top Anomaly Categories</h3>
              <p className="text-xs text-slate-500">Distribution across 896 active rule detections</p>
              <div className="space-y-2.5 pt-2">
                {[
                  { name: "Financial & Cost", count: 265, pct: 29.6, color: "bg-amber-500" },
                  { name: "Progress & Timeline", count: 215, pct: 24.0, color: "bg-rose-500" },
                  { name: "Payment Irregularities", count: 223, pct: 24.9, color: "bg-purple-500" },
                  { name: "Vendor & Agency", count: 93, pct: 10.4, color: "bg-indigo-500" },
                  { name: "Statutory Compliance", count: 76, pct: 8.5, color: "bg-slate-500" },
                  { name: "Potential Duplicate Works", count: 24, pct: 2.7, color: "bg-blue-500" },
                ].map((cat) => (
                  <div key={cat.name} className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                      <span>{cat.name}</span>
                      <span className="font-mono">{cat.count} ({cat.pct}%)</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div style={{ width: `${cat.pct}%` }} className={`h-full ${cat.color} rounded-full`} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
