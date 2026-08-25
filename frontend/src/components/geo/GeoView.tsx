import React, { useState, useMemo } from "react";
import { Project, ProjectRiskProfile, DistrictRiskProfile } from "../../types";
import { RiskBadge } from "../common/RiskBadge";
import {
  Search,
  MapPin,
  ShieldAlert,
  CheckCircle2,
  Layers,
  Building2,
  RotateCcw,
  ChevronRight,
  ArrowLeft,
  ExternalLink,
} from "lucide-react";
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
  // Hierarchical Geographic Filters State
  const [selectedState, setSelectedState] = useState<string>("ALL");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("ALL");
  const [selectedConstituency, setSelectedConstituency] = useState<string>("ALL");

  // Secondary Filters
  const [selectedRiskFilter, setSelectedRiskFilter] = useState<string>("ALL");
  const [tableSearch, setTableSearch] = useState<string>("");

  const riskMap = useMemo(() => {
    const map = new Map<string, ProjectRiskProfile>();
    riskProfiles.forEach((rp) => map.set(rp.project_id, rp));
    return map;
  }, [riskProfiles]);

  // 1. Hierarchical Options Computation
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

  // 2. Hierarchical Filter Change Handlers
  const handleStateChange = (newState: string) => {
    setSelectedState(newState);

    if (newState === "ALL") {
      // Restore all districts and constituencies
      setSelectedDistrict("ALL");
      setSelectedConstituency("ALL");
    } else {
      // Check if current district belongs to the new state
      const validDistrictsInNewState = new Set(
        projects.filter((p) => p.state === newState).map((p) => p.district)
      );
      if (selectedDistrict !== "ALL" && !validDistrictsInNewState.has(selectedDistrict)) {
        setSelectedDistrict("ALL");
      }
      setSelectedConstituency("ALL");
    }
  };

  const handleDistrictChange = (newDistrict: string) => {
    setSelectedDistrict(newDistrict);

    if (newDistrict === "ALL") {
      setSelectedConstituency("ALL");
    } else {
      // Check if current constituency belongs to the new district
      const validConstituencies = new Set(
        projects
          .filter(
            (p) =>
              p.district === newDistrict &&
              (selectedState === "ALL" || p.state === selectedState)
          )
          .map((p) => p.constituency)
      );
      if (selectedConstituency !== "ALL" && !validConstituencies.has(selectedConstituency)) {
        setSelectedConstituency("ALL");
      }
    }
  };

  const handleConstituencyChange = (newConstituency: string) => {
    setSelectedConstituency(newConstituency);
  };

  const handleResetGeoFilters = () => {
    setSelectedState("ALL");
    setSelectedDistrict("ALL");
    setSelectedConstituency("ALL");
    setSelectedRiskFilter("ALL");
    setTableSearch("");
  };

  const hasActiveGeoFilter =
    selectedState !== "ALL" ||
    selectedDistrict !== "ALL" ||
    selectedConstituency !== "ALL" ||
    selectedRiskFilter !== "ALL" ||
    tableSearch.trim() !== "";

  // 3. Dynamic Filtered Projects (Respects State -> District -> Constituency -> Risk -> Search)
  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      const rp = riskMap.get(p.project_id);

      if (selectedState !== "ALL" && p.state !== selectedState) return false;
      if (selectedDistrict !== "ALL" && p.district !== selectedDistrict) return false;
      if (selectedConstituency !== "ALL" && p.constituency !== selectedConstituency) return false;
      if (selectedRiskFilter !== "ALL" && rp?.risk_level !== selectedRiskFilter) return false;

      if (tableSearch.trim()) {
        const q = tableSearch.toLowerCase();
        const match =
          p.project_id.toLowerCase().includes(q) ||
          p.work_name.toLowerCase().includes(q) ||
          p.mp_name.toLowerCase().includes(q) ||
          p.district.toLowerCase().includes(q) ||
          p.state.toLowerCase().includes(q) ||
          p.constituency.toLowerCase().includes(q);
        if (!match) return false;
      }

      return p.latitude && p.longitude && !isNaN(p.latitude) && !isNaN(p.longitude);
    });
  }, [
    projects,
    riskMap,
    selectedState,
    selectedDistrict,
    selectedConstituency,
    selectedRiskFilter,
    tableSearch,
  ]);

  // 4. Dynamic Summary Metrics
  const highRiskCount = useMemo(
    () => filteredProjects.filter((p) => riskMap.get(p.project_id)?.risk_level === "HIGH").length,
    [filteredProjects, riskMap]
  );

  const mediumRiskCount = useMemo(
    () => filteredProjects.filter((p) => riskMap.get(p.project_id)?.risk_level === "MEDIUM").length,
    [filteredProjects, riskMap]
  );

  const lowRiskCount = useMemo(
    () => filteredProjects.filter((p) => riskMap.get(p.project_id)?.risk_level === "LOW").length,
    [filteredProjects, riskMap]
  );

  const totalSanctionedLakh = useMemo(
    () => filteredProjects.reduce((acc, p) => acc + (p.sanctioned_amount_lakh || 0), 0),
    [filteredProjects]
  );

  const totalExpenditureLakh = useMemo(
    () => filteredProjects.reduce((acc, p) => acc + (p.expenditure_lakh || 0), 0),
    [filteredProjects]
  );

  const monitoredDistrictsCount = useMemo(() => {
    const set = new Set(filteredProjects.map((p) => p.district));
    return set.size;
  }, [filteredProjects]);

  const monitoredConstituenciesCount = useMemo(() => {
    const set = new Set(filteredProjects.map((p) => p.constituency));
    return set.size;
  }, [filteredProjects]);

  // 5. Filtered Districts for District Table
  const filteredDistrictStats = useMemo(() => {
    let list = districts;
    if (selectedState !== "ALL") {
      list = list.filter((d) => d.state === selectedState);
    }
    if (selectedDistrict !== "ALL") {
      list = list.filter((d) => d.district === selectedDistrict);
    }
    if (tableSearch.trim()) {
      const q = tableSearch.toLowerCase();
      list = list.filter(
        (d) => d.district.toLowerCase().includes(q) || d.state.toLowerCase().includes(q)
      );
    }
    return list;
  }, [districts, selectedState, selectedDistrict, tableSearch]);

  const getMarkerColor = (level?: string) => {
    if (level === "CRITICAL") return "#dc2626";
    if (level === "HIGH") return "#e11d48";
    if (level === "MEDIUM") return "#f59e0b";
    return "#10b981";
  };

  const isDrilledDownToProjects = selectedDistrict !== "ALL" || selectedConstituency !== "ALL";

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      {/* Header & Hierarchical Filters */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Geospatial Intelligence & Regional Monitoring
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Hierarchical territorial analysis across State → District → Constituency → Project Works.
          </p>
        </div>

        {/* Compact 3-Level Hierarchical Geographic Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* 1. State Filter */}
          <div className="flex items-center gap-1.5 bg-white px-2.5 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">State:</span>
            <select
              value={selectedState}
              onChange={(e) => handleStateChange(e.target.value)}
              className="text-xs font-bold text-slate-800 bg-transparent focus:outline-none cursor-pointer max-w-[140px] truncate"
            >
              <option value="ALL">All States ({projects.length})</option>
              {availableStates.map((st) => (
                <option key={st} value={st}>
                  {st} ({projects.filter((p) => p.state === st).length})
                </option>
              ))}
            </select>
          </div>

          {/* 2. District Filter */}
          <div className="flex items-center gap-1.5 bg-white px-2.5 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">District:</span>
            <select
              value={selectedDistrict}
              onChange={(e) => handleDistrictChange(e.target.value)}
              className="text-xs font-bold text-slate-800 bg-transparent focus:outline-none cursor-pointer max-w-[140px] truncate"
            >
              <option value="ALL">All Districts ({availableDistricts.length})</option>
              {availableDistricts.map((dist) => {
                const count = projects.filter(
                  (p) => p.district === dist && (selectedState === "ALL" || p.state === selectedState)
                ).length;
                return (
                  <option key={dist} value={dist}>
                    {dist} ({count})
                  </option>
                );
              })}
            </select>
          </div>

          {/* 3. Constituency Filter */}
          <div className="flex items-center gap-1.5 bg-white px-2.5 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Constituency:</span>
            <select
              value={selectedConstituency}
              onChange={(e) => handleConstituencyChange(e.target.value)}
              className="text-xs font-bold text-slate-800 bg-transparent focus:outline-none cursor-pointer max-w-[150px] truncate"
            >
              <option value="ALL">All ({availableConstituencies.length})</option>
              {availableConstituencies.map((c) => {
                const count = projects.filter(
                  (p) =>
                    p.constituency === c &&
                    (selectedState === "ALL" || p.state === selectedState) &&
                    (selectedDistrict === "ALL" || p.district === selectedDistrict)
                ).length;
                return (
                  <option key={c} value={c}>
                    {c} ({count})
                  </option>
                );
              })}
            </select>
          </div>

          {/* Reset Filters */}
          {hasActiveGeoFilter && (
            <button
              onClick={handleResetGeoFilters}
              title="Reset all geographic filters"
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 shadow-2xs transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* Active Geographic Scope Breadcrumb */}
      {hasActiveGeoFilter && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600 bg-blue-50/70 border border-blue-100 px-3.5 py-2 rounded-lg">
          <span className="font-semibold text-blue-900">Active Scope:</span>
          <span className="font-bold text-slate-800">
            {selectedState === "ALL" ? "All States" : selectedState}
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-bold text-slate-800">
            {selectedDistrict === "ALL" ? "All Districts" : selectedDistrict}
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-bold text-slate-800">
            {selectedConstituency === "ALL" ? "All Constituencies" : selectedConstituency}
          </span>
          {selectedRiskFilter !== "ALL" && (
            <>
              <span className="text-slate-400">•</span>
              <span className="font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 text-[11px]">
                Risk: {selectedRiskFilter}
              </span>
            </>
          )}
          <span className="ml-auto text-[11px] text-slate-500 font-mono">
            {filteredProjects.length} Works Displayed
          </span>
        </div>
      )}

      {/* Dynamic Summary Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Total Works */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Markers</span>
            <MapPin className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">{filteredProjects.length}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {selectedState === "ALL" ? "Across 10 States" : selectedState}
          </p>
        </div>

        {/* High Risk */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Priority High Risk</span>
            <ShieldAlert className="w-4 h-4 text-rose-600" />
          </div>
          <p className="text-2xl font-bold text-rose-700 font-mono">{highRiskCount}</p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {mediumRiskCount} Medium / {lowRiskCount} Low
          </p>
        </div>

        {/* Coverage Scope */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Territorial Scope</span>
            <Layers className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 font-mono">
            {monitoredDistrictsCount} <span className="text-xs font-normal text-slate-500">Districts</span>
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {monitoredConstituenciesCount} Constituencies covered
          </p>
        </div>

        {/* Financial Expenditure */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Sanction & Spend</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-xl font-bold text-slate-900 font-mono truncate">
            ₹{totalExpenditureLakh.toFixed(1)}L
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
            of ₹{totalSanctionedLakh.toFixed(1)}L Sanctioned
          </p>
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
                  className={`px-2.5 py-1 rounded text-xs font-semibold transition-all cursor-pointer ${
                    selectedRiskFilter === tab.id
                      ? "bg-slate-900 text-white shadow-2xs"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="text-xs text-slate-500 font-mono">
            Showing {filteredProjects.length} of {projects.length} works
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
            {filteredProjects.map((p) => {
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
                            {p.constituency} • {p.district}, {p.state}
                          </span>
                        </div>
                        {rp && <RiskBadge level={rp.risk_level} score={rp.risk_score} size="sm" />}
                      </div>

                      <div className="grid grid-cols-2 gap-1.5 text-[11px] bg-slate-50 p-1.5 rounded border border-slate-100">
                        <div>
                          <span className="text-slate-400">Sanctioned:</span>
                          <div className="font-bold text-slate-800 font-mono">
                            ₹{p.sanctioned_amount_lakh}L
                          </div>
                        </div>
                        <div>
                          <span className="text-slate-400">Expenditure:</span>
                          <div className="font-bold text-slate-800 font-mono">
                            ₹{p.expenditure_lakh}L
                          </div>
                        </div>
                        <div>
                          <span className="text-slate-400">Physical Progress:</span>
                          <div className="font-bold text-slate-800 font-mono">
                            {p.physical_progress_pct}%
                          </div>
                        </div>
                        <div>
                          <span className="text-slate-400">Category:</span>
                          <div className="font-semibold text-slate-700 truncate">
                            {p.work_category}
                          </div>
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                          Top Risk Signal:
                        </span>
                        <p className="text-[11px] font-medium text-slate-700 truncate font-mono">
                          {primaryAnomaly}
                        </p>
                      </div>

                      <button
                        onClick={() => onSelectProject(p.project_id)}
                        className="w-full mt-2 py-1.5 text-center font-bold text-[11px] rounded bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
                      >
                        <span>Inspect Dossier & Evidence</span>
                        <ExternalLink className="w-3 h-3" />
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
            GPS Source: Deterministic Land Registry (500/500 India Land Points)
          </span>
        </div>
      </div>

      {/* District & Constituency Portfolio Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              {isDrilledDownToProjects && (
                <button
                  onClick={() => {
                    setSelectedDistrict("ALL");
                    setSelectedConstituency("ALL");
                  }}
                  className="p-1 rounded-md hover:bg-slate-100 text-slate-600 transition-colors cursor-pointer"
                  title="Back to All Districts"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
              )}
              <h2 className="text-sm font-bold text-slate-900">
                {isDrilledDownToProjects
                  ? `Constituency Projects (${filteredProjects.length} Works in ${selectedDistrict !== "ALL" ? selectedDistrict : selectedState})`
                  : `District Portfolio Breakdown (${filteredDistrictStats.length} Monitored Districts)`}
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {isDrilledDownToProjects
                ? `Granular project works and execution tracking within ${selectedDistrict !== "ALL" ? selectedDistrict : selectedState}${selectedConstituency !== "ALL" ? ` • ${selectedConstituency}` : ""}`
                : "Aggregated statutory monitoring across districts synchronized with hierarchical filters"}
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={tableSearch}
              onChange={(e) => setTableSearch(e.target.value)}
              placeholder="Search works, district, MP..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
            />
          </div>
        </div>

        {/* 1. When District / Constituency is selected: Show Project-Level Constituency Table */}
        {isDrilledDownToProjects ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-100">
                <tr>
                  <th className="py-3 px-4">Project Work</th>
                  <th className="py-3 px-3">Constituency & MP</th>
                  <th className="py-3 px-3">Category</th>
                  <th className="py-3 px-3">Sanction</th>
                  <th className="py-3 px-3">Expenditure</th>
                  <th className="py-3 px-3 text-center">Progress</th>
                  <th className="py-3 px-3 text-center">Risk Score</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredProjects.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400">
                      No project works found matching the active geographic criteria.
                    </td>
                  </tr>
                ) : (
                  filteredProjects.map((p) => {
                    const rp = riskMap.get(p.project_id);
                    return (
                      <tr key={p.project_id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 font-semibold text-slate-900 max-w-xs">
                          <div className="font-mono text-[10px] font-bold text-slate-400">
                            {p.project_id}
                          </div>
                          <div className="truncate font-bold text-slate-800">{p.work_name}</div>
                        </td>
                        <td className="py-3 px-3 text-slate-700">
                          <span className="font-semibold text-slate-900">{p.constituency}</span>
                          <div className="text-[11px] text-slate-400">{p.mp_name}</div>
                        </td>
                        <td className="py-3 px-3 text-slate-600">{p.work_category}</td>
                        <td className="py-3 px-3 font-mono text-slate-800">
                          ₹{p.sanctioned_amount_lakh}L
                        </td>
                        <td className="py-3 px-3 font-mono text-slate-800">
                          ₹{p.expenditure_lakh}L
                        </td>
                        <td className="py-3 px-3 text-center font-mono">
                          <span
                            className={`font-bold ${
                              p.physical_progress_pct >= 70
                                ? "text-emerald-700"
                                : p.physical_progress_pct >= 40
                                ? "text-blue-700"
                                : "text-amber-700"
                            }`}
                          >
                            {p.physical_progress_pct}%
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center">
                          {rp && <RiskBadge level={rp.risk_level} score={rp.risk_score} size="sm" />}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => onSelectProject(p.project_id)}
                            className="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 text-white font-bold text-[10px] transition-colors shadow-2xs cursor-pointer"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        ) : (
          /* 2. When viewing State / All: Show District Aggregation Table */
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
                  <th className="py-3 px-4 text-right">Drill Down</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDistrictStats.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-400">
                      No districts found matching the active filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredDistrictStats.map((d) => (
                    <tr
                      key={d.district}
                      onClick={() => handleDistrictChange(d.district)}
                      className="hover:bg-blue-50/40 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        <div className="flex items-center gap-1.5 font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                          <Building2 className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600" />
                          <span>{d.district}</span>
                        </div>
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
                        <div className="font-bold text-slate-800 font-mono">
                          {d.fund_utilization_pct}%
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDistrictChange(d.district);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-700 font-bold text-[10px] transition-colors shadow-2xs inline-flex items-center gap-1"
                        >
                          <span>Explore</span>
                          <ChevronRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
