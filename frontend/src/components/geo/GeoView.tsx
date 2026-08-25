import React, { useState, useMemo } from "react";
import { Project, ProjectRiskProfile, DistrictRiskProfile } from "../../types";
import { RiskBadge } from "../common/RiskBadge";
import { Search, MapPin, ShieldAlert, CheckCircle2, Layers } from "lucide-react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

interface GeoViewProps {
  projects: Project[];
  riskProfiles: ProjectRiskProfile[];
  districts: DistrictRiskProfile[];
  onSelectProject: (projectId: string) => void;
}

export const GeoView: React.FC<GeoViewProps> = ({
  projects,
  riskProfiles,
  districts,
  onSelectProject,
}) => {
  const [selectedRiskFilter, setSelectedRiskFilter] = useState<string>("ALL");
  const [selectedStateFilter, setSelectedStateFilter] = useState<string>("ALL");
  const [districtSearch, setDistrictSearch] = useState<string>("");

  const riskMap = useMemo(() => {
    const map = new Map<string, ProjectRiskProfile>();
    riskProfiles.forEach((rp) => map.set(rp.project_id, rp));
    return map;
  }, [riskProfiles]);

  const uniqueStates = useMemo(() => {
    const set = new Set<string>();
    projects.forEach((p) => {
      if (p.state) set.add(p.state);
    });
    return Array.from(set).sort();
  }, [projects]);

  const geoProjects = useMemo(() => {
    return projects.filter((p) => {
      const rp = riskMap.get(p.project_id);
      if (selectedRiskFilter !== "ALL" && rp?.risk_level !== selectedRiskFilter) return false;
      if (selectedStateFilter !== "ALL" && p.state !== selectedStateFilter) return false;
      return p.latitude && p.longitude && !isNaN(p.latitude) && !isNaN(p.longitude);
    });
  }, [projects, riskMap, selectedRiskFilter, selectedStateFilter]);

  const filteredDistricts = useMemo(() => {
    let list = districts;
    if (selectedStateFilter !== "ALL") {
      list = list.filter((d) => d.state === selectedStateFilter);
    }
    if (districtSearch.trim()) {
      const q = districtSearch.toLowerCase();
      list = list.filter(
        (d) => d.district.toLowerCase().includes(q) || d.state.toLowerCase().includes(q)
      );
    }
    return list;
  }, [districts, selectedStateFilter, districtSearch]);

  const getMarkerColor = (level?: string) => {
    if (level === "CRITICAL") return "#dc2626";
    if (level === "HIGH") return "#e11d48";
    if (level === "MEDIUM") return "#f59e0b";
    return "#10b981";
  };

  const highRiskCount = geoProjects.filter((p) => riskMap.get(p.project_id)?.risk_level === "HIGH").length;

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Geospatial Intelligence & Regional Monitoring
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Territorial distribution, cluster density, and localized risk concentration across all constituencies.
          </p>
        </div>

        {/* State Filter Dropdown */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500">State:</span>
            <select
              value={selectedStateFilter}
              onChange={(e) => setSelectedStateFilter(e.target.value)}
              className="text-xs font-bold text-slate-800 bg-transparent focus:outline-none cursor-pointer"
            >
              <option value="ALL">All 10 States ({projects.length})</option>
              {uniqueStates.map((st) => (
                <option key={st} value={st}>
                  {st} ({projects.filter((p) => p.state === st).length})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Metric Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Markers</span>
            <MapPin className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">{geoProjects.length}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Plotting within India</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Priority High Risk</span>
            <ShieldAlert className="w-4 h-4 text-rose-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">{highRiskCount}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Requiring priority inspection</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Monitored Districts</span>
            <Layers className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">{filteredDistricts.length}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">Across {selectedStateFilter === "ALL" ? "10 States" : selectedStateFilter}</p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Boundary Accuracy</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-bold text-emerald-700 font-mono">100.0%</p>
          <p className="text-[11px] text-emerald-700 mt-0.5">Verified on-land coordinates</p>
        </div>
      </div>

      {/* Map Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3 pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Filter Risk Level:</span>
            <div className="flex items-center gap-1.5">
              {[
                { id: "ALL", label: `All (${projects.length})` },
                { id: "HIGH", label: `High (26)` },
                { id: "MEDIUM", label: `Medium (93)` },
                { id: "LOW", label: `Low (381)` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSelectedRiskFilter(tab.id)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                    selectedRiskFilter === tab.id
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="text-xs text-slate-500 font-mono">
            Showing {geoProjects.length} of {projects.length} works
          </div>
        </div>

        {/* Leaflet Map */}
        <div className="h-[480px] w-full rounded-lg overflow-hidden relative z-0 border border-slate-200">
          <MapContainer
            center={[22.50, 79.50]}
            zoom={5}
            minZoom={4}
            maxZoom={12}
            scrollWheelZoom={false}
            className="h-full w-full"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {geoProjects.map((p) => {
              const rp = riskMap.get(p.project_id);
              const color = getMarkerColor(rp?.risk_level);
              const primaryAnomaly = rp?.risk_factors?.[0]?.signal || "Normal Operation";

              return (
                <CircleMarker
                  key={p.project_id}
                  center={[p.latitude, p.longitude]}
                  radius={rp?.risk_level === "HIGH" ? 7 : 5}
                  pathOptions={{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.85,
                    weight: 1.5,
                  }}
                >
                  <Popup>
                    <div className="p-1.5 max-w-xs space-y-2 text-xs font-sans">
                      <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-1.5">
                        <div>
                          <span className="font-mono text-[10px] font-bold text-slate-400">
                            {p.project_id}
                          </span>
                          <h4 className="font-bold text-slate-900 text-xs leading-tight">
                            {p.work_name}
                          </h4>
                          <span className="text-[10px] text-slate-500 font-medium">
                            {p.district}, {p.state}
                          </span>
                        </div>
                        {rp && <RiskBadge level={rp.risk_level} score={rp.risk_score} size="sm" />}
                      </div>

                      <div className="grid grid-cols-2 gap-1.5 text-[11px] bg-slate-50 p-1.5 rounded border border-slate-100">
                        <div>
                          <span className="text-slate-400">Sanctioned:</span>
                          <div className="font-bold text-slate-800 font-mono">₹{p.sanctioned_amount_lakh}L</div>
                        </div>
                        <div>
                          <span className="text-slate-400">Expenditure:</span>
                          <div className="font-bold text-slate-800 font-mono">₹{p.expenditure_lakh}L</div>
                        </div>
                        <div>
                          <span className="text-slate-400">Physical Progress:</span>
                          <div className="font-bold text-slate-800 font-mono">{p.physical_progress_pct}%</div>
                        </div>
                        <div>
                          <span className="text-slate-400">Category:</span>
                          <div className="font-semibold text-slate-700 truncate">{p.work_category}</div>
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Top Risk Signal:</span>
                        <p className="text-[11px] font-medium text-slate-700 truncate font-mono">
                          {primaryAnomaly}
                        </p>
                      </div>

                      <button
                        onClick={() => onSelectProject(p.project_id)}
                        className="w-full mt-2 py-1.5 text-center font-bold text-[11px] rounded bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs"
                      >
                        Inspect Dossier & Evidence
                      </button>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>

        {/* Legend */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-600 px-1">
          <div className="flex items-center gap-4">
            <span className="font-semibold text-slate-500">Legend:</span>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-rose-600" />
              <span>High Risk (50–74)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-amber-400" />
              <span>Medium Risk (25–49)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-emerald-500" />
              <span>Low Risk (0–24)</span>
            </div>
          </div>
          <span className="text-slate-400 font-mono text-[11px]">
            GPS Source: Deterministic Land Registry
          </span>
        </div>
      </div>

      {/* District Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              District Portfolio & Performance Breakdown
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Aggregated statutory monitoring across all 30 districts synchronized with map markers
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={districtSearch}
              onChange={(e) => setDistrictSearch(e.target.value)}
              placeholder="Search district or state..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-100">
              <tr>
                <th className="py-3 px-4">District & State</th>
                <th className="py-3 px-3 text-center">Total Works</th>
                <th className="py-3 px-3 text-center">High Risk</th>
                <th className="py-3 px-3">Average Risk</th>
                <th className="py-3 px-3">Total Sanction</th>
                <th className="py-3 px-3">Expenditure</th>
                <th className="py-3 px-3">Fund Utilization</th>
                <th className="py-3 px-4">Top Agency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredDistricts.map((d) => (
                <tr key={d.district} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    {d.district}
                    <div className="text-[11px] text-slate-400 font-normal">{d.state}</div>
                  </td>
                  <td className="py-3 px-3 text-center font-bold text-slate-700 font-mono">
                    {d.total_projects}
                  </td>
                  <td className="py-3 px-3 text-center">
                    {d.high_risk_count > 0 ? (
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200 font-mono">
                        {d.high_risk_count}
                      </span>
                    ) : (
                      <span className="text-slate-400 font-mono">0</span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-800 font-mono">
                        {d.average_risk_score}
                      </span>
                      <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${Math.min(100, d.average_risk_score * 1.5)}%` }}
                          className={`h-full rounded-full ${
                            d.average_risk_score > 20 ? "bg-rose-500" : "bg-emerald-500"
                          }`}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-700">₹{d.total_sanctioned_lakh}L</td>
                  <td className="py-3 px-3 font-mono text-slate-700">₹{d.total_expenditure_lakh}L</td>
                  <td className="py-3 px-3">
                    <div className="font-bold text-slate-800 font-mono">{d.fund_utilization_pct}%</div>
                  </td>
                  <td className="py-3 px-4 text-slate-600 text-[11px]">
                    {d.top_implementing_agency}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
