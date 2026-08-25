import React, { useState, useEffect, useRef } from "react";
import { Project, ProjectRiskProfile } from "../../types";
import { RiskBadge } from "../common/RiskBadge";
import { Search, X, FolderKanban, ArrowRight } from "lucide-react";

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  projects: Project[];
  riskProfiles: ProjectRiskProfile[];
  onSelectProject: (projectId: string) => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({
  isOpen,
  onClose,
  projects,
  riskProfiles,
  onSelectProject,
}) => {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const riskMap = new Map<string, ProjectRiskProfile>();
  riskProfiles.forEach((rp) => riskMap.set(rp.project_id, rp));

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const results = query.trim()
    ? projects
        .filter((p) => {
          const q = query.toLowerCase();
          return (
            p.project_id.toLowerCase().includes(q) ||
            p.work_name.toLowerCase().includes(q) ||
            p.mp_name.toLowerCase().includes(q) ||
            p.district.toLowerCase().includes(q) ||
            p.work_category.toLowerCase().includes(q)
          );
        })
        .slice(0, 10)
    : [];

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-start justify-center p-4 sm:p-12 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden mt-10 animate-in fade-in zoom-in-95 duration-100"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-slate-200 flex items-center gap-3">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type project ID, work description, district, MP name..."
            className="w-full text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none bg-transparent"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="text-slate-400 hover:text-slate-600 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono bg-slate-100 rounded border border-slate-200 text-slate-500">
            ESC
          </kbd>
        </div>

        <div className="max-h-96 overflow-y-auto p-2">
          {query.trim() === "" ? (
            <div className="p-8 text-center text-xs text-slate-400">
              <FolderKanban className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              Search across all 500 MPLADS registered works and anomaly records
            </div>
          ) : results.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No projects found matching "{query}"
            </div>
          ) : (
            <div className="space-y-1">
              {results.map((p) => {
                const rp = riskMap.get(p.project_id);

                return (
                  <div
                    key={p.project_id}
                    onClick={() => {
                      onSelectProject(p.project_id);
                      onClose();
                    }}
                    className="p-3 rounded-xl hover:bg-slate-50 cursor-pointer flex items-center justify-between gap-3 transition-colors border border-transparent hover:border-slate-200"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-500">
                          {p.project_id}
                        </span>
                        <span className="text-slate-300">•</span>
                        <span className="text-xs text-slate-500 font-medium">
                          {p.district}, {p.state}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-900 max-w-md truncate">
                        {p.work_name}
                      </h4>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {rp && (
                        <RiskBadge
                          level={rp.risk_level}
                          score={rp.risk_score}
                          size="sm"
                        />
                      )}
                      <ArrowRight className="w-4 h-4 text-slate-400" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-slate-50 p-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 px-4">
          <span>Navigate with arrow keys</span>
          <span>Press Enter to select</span>
        </div>
      </div>
    </div>
  );
};
