import React, { useState, useMemo } from "react";
import { Project, ProjectRiskProfile } from "../../types";
import { RiskBadge } from "../common/RiskBadge";
import { StatusBadge } from "../common/StatusBadge";
import { EmptyState } from "../common/EmptyState";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";

import { formatCurrencyLakh, formatProgressPct } from "../../utils/formatters";

interface ProjectsViewProps {
  projects: Project[];
  riskProfiles: ProjectRiskProfile[];
  onSelectProject: (projectId: string) => void;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({
  projects,
  riskProfiles,
  onSelectProject,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("ALL");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [selectedStatus, setSelectedStatus] = useState("ALL");
  const [selectedRiskLevel, setSelectedRiskLevel] = useState("ALL");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50;

  const riskMap = useMemo(() => {
    const map = new Map<string, ProjectRiskProfile>();
    riskProfiles.forEach((rp) => map.set(rp.project_id, rp));
    return map;
  }, [riskProfiles]);

  const districts = useMemo(() => {
    return Array.from(new Set(projects.map((p) => p.district).filter(Boolean))).sort();
  }, [projects]);

  const categories = useMemo(() => {
    return Array.from(new Set(projects.map((p) => p.work_category).filter(Boolean))).sort();
  }, [projects]);

  const statuses = useMemo(() => {
    return Array.from(new Set(projects.map((p) => p.status).filter(Boolean))).sort();
  }, [projects]);

  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      const rp = riskMap.get(p.project_id);

      if (selectedDistrict !== "ALL" && p.district !== selectedDistrict) return false;
      if (selectedCategory !== "ALL" && p.work_category !== selectedCategory) return false;
      if (selectedStatus !== "ALL" && p.status !== selectedStatus) return false;
      if (selectedRiskLevel !== "ALL" && rp?.risk_level !== selectedRiskLevel) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchId = p.project_id.toLowerCase().includes(q);
        const matchName = p.work_name.toLowerCase().includes(q);
        const matchMp = p.mp_name.toLowerCase().includes(q);
        if (!matchId && !matchName && !matchMp) return false;
      }

      return true;
    });
  }, [projects, riskMap, selectedDistrict, selectedCategory, selectedStatus, selectedRiskLevel, searchQuery]);

  const totalPages = Math.ceil(filteredProjects.length / pageSize) || 1;
  const paginatedProjects = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredProjects.slice(start, start + pageSize);
  }, [filteredProjects, currentPage, pageSize]);

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          MPLADS Project Registry
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Search and inspect execution records, physical progress, and risk profiles across all 500 works.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          <div className="relative md:col-span-2">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search by ID, work name, MP..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50"
            />
          </div>

          <div>
            <select
              value={selectedDistrict}
              onChange={(e) => {
                setSelectedDistrict(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full py-1.5 px-3 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium"
            >
              <option value="ALL">All Districts ({districts.length})</option>
              {districts.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full py-1.5 px-3 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium"
            >
              <option value="ALL">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full py-1.5 px-3 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50/50 text-slate-700 font-medium"
            >
              <option value="ALL">All Statuses ({statuses.length})</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
          <span>
            Showing <strong>{filteredProjects.length}</strong> matching projects
          </span>
          {(selectedDistrict !== "ALL" || selectedCategory !== "ALL" || selectedStatus !== "ALL" || selectedRiskLevel !== "ALL" || searchQuery) && (
            <button
              onClick={() => {
                setSelectedDistrict("ALL");
                setSelectedCategory("ALL");
                setSelectedRiskLevel("ALL");
                setSelectedStatus("ALL");
                setSearchQuery("");
                setCurrentPage(1);
              }}
              className="text-blue-600 hover:text-blue-800 font-semibold"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {filteredProjects.length === 0 ? (
        <EmptyState
          title="No projects found"
          description="Try changing your search keywords or clearing active filters."
          actionText="Reset Filters"
          onAction={() => {
            setSelectedDistrict("ALL");
            setSelectedCategory("ALL");
            setSelectedRiskLevel("ALL");
            setSelectedStatus("ALL");
            setSearchQuery("");
          }}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-100">
                <tr>
                  <th className="py-3 px-4">Project ID & Name</th>
                  <th className="py-3 px-3">Location & MP</th>
                  <th className="py-3 px-3">Category</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Physical Progress</th>
                  <th className="py-3 px-3">Sanction / Paid</th>
                  <th className="py-3 px-3">Risk Assessment</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedProjects.map((p) => {
                  const rp = riskMap.get(p.project_id);

                  return (
                    <tr
                      key={p.project_id}
                      onClick={() => onSelectProject(p.project_id)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 max-w-xs truncate">
                          {p.work_name}
                        </div>
                        <div className="font-mono text-[11px] text-slate-400 mt-0.5">
                          {p.project_id}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-600">
                        {p.district}, {p.state}
                        <div className="text-[10px] text-slate-400">MP: {p.mp_name}</div>
                      </td>
                      <td className="py-3 px-3 text-slate-700 font-medium">
                        {p.work_category}
                      </td>
                      <td className="py-3 px-3">
                        <StatusBadge status={p.status} />
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              style={{ width: `${Math.min(100, p.physical_progress_pct)}%` }}
                              className="h-full bg-blue-600 rounded-full"
                            />
                          </div>
                          <span className="font-bold text-slate-800 font-mono">
                            {formatProgressPct(p.physical_progress_pct)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-700 font-mono">
                        <div>{formatCurrencyLakh(p.sanctioned_amount_lakh)}</div>
                        <div className="text-[10px] text-slate-400">Paid: {formatCurrencyLakh(p.expenditure_lakh)}</div>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        {rp ? (
                          <RiskBadge level={rp.risk_level} score={rp.risk_score} size="sm" />
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="inline-flex items-center px-2.5 py-1 rounded bg-blue-50 text-blue-700 font-semibold text-[11px] hover:bg-blue-100 border border-blue-200">
                          Dossier
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600 bg-slate-50/50">
            <div>
              Showing page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> (
              {filteredProjects.length} total)
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-slate-600"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 font-semibold text-slate-800 font-mono">
                {currentPage} / {totalPages}
              </span>
              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-slate-600"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
