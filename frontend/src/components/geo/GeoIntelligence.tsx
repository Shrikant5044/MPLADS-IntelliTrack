import React, { useState, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';
import { Project, ProjectRiskProfile, AnomalyResult } from '../../types';
import { RiskBadge } from '../common/RiskBadge';
import { MapPin, Copy } from 'lucide-react';
import { formatCurrencyLakh, formatProgressPct } from '../../utils/formatters';

interface Props {
  projects: Project[];
  riskProfiles: ProjectRiskProfile[];
  anomalies: AnomalyResult[];
  onSelectProject: (projectId: string) => void;
}

export const GeoIntelligence: React.FC<Props> = ({
  projects,
  riskProfiles,
  anomalies,
  onSelectProject,
}) => {
  const [selectedRisk, setSelectedRisk] = useState<string>('ALL');
  const [duplicateOnly, setDuplicateOnly] = useState<boolean>(false);
  const [selectedDistrict, setSelectedDistrict] = useState<string>('ALL');

  const riskMap = useMemo(() => new Map(riskProfiles.map((p) => [p.project_id, p])), [riskProfiles]);
  const projectMap = useMemo(() => new Map(projects.map((p) => [p.project_id, p])), [projects]);

  const duplicatePairs = useMemo(() => {
    const pairs: Array<{
      p1: Project;
      p2: Project;
      distanceKm: number;
      similarity: number;
    }> = [];

    const seen = new Set<string>();

    anomalies
      .filter((a) => a.anomaly_type === 'POTENTIAL_DUPLICATE_WORK')
      .forEach((a) => {
        const id1 = a.project_id;
        const id2 = a.evidence?.matched_project_id;
        if (!id2) return;

        const key = [id1, id2].sort().join('--');
        if (seen.has(key)) return;
        seen.add(key);

        const p1 = projectMap.get(id1);
        const p2 = projectMap.get(id2);
        if (p1 && p2) {
          pairs.push({
            p1,
            p2,
            distanceKm: a.evidence?.distance_km ?? 0.1,
            similarity: (a.evidence?.similarity_score ?? 0.85) * 100,
          });
        }
      });

    return pairs;
  }, [anomalies, projectMap]);

  const duplicateProjectIds = useMemo(() => {
    const set = new Set<string>();
    duplicatePairs.forEach((p) => {
      set.add(p.p1.project_id);
      set.add(p.p2.project_id);
    });
    return set;
  }, [duplicatePairs]);

  const districts = useMemo(() => {
    const set = new Set(projects.map((p) => p.district));
    return Array.from(set).sort();
  }, [projects]);

  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      const r = riskMap.get(p.project_id);
      const level = r?.risk_level || 'LOW';

      if (selectedRisk !== 'ALL' && level !== selectedRisk) return false;
      if (selectedDistrict !== 'ALL' && p.district !== selectedDistrict) return false;
      if (duplicateOnly && !duplicateProjectIds.has(p.project_id)) return false;

      if (isNaN(p.latitude) || isNaN(p.longitude) || p.latitude === 0 || p.longitude === 0) return false;

      return true;
    });
  }, [projects, riskMap, selectedRisk, selectedDistrict, duplicateOnly, duplicateProjectIds]);

  const getColor = (level: string) => {
    switch (level) {
      case 'CRITICAL': return '#ef4444';
      case 'HIGH': return '#f97316';
      case 'MEDIUM': return '#f59e0b';
      default: return '#10b981';
    }
  };

  const centerPosition: [number, number] = [22.5937, 78.9629];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[calc(100vh-140px)] min-h-[600px]">
      <div className="lg:col-span-8 xl:col-span-9 bg-[#0c1017] border border-[#1e2633] rounded-lg flex flex-col overflow-hidden">
        <div className="p-3 border-b border-[#1e2633] flex flex-wrap items-center justify-between gap-3 bg-[#0d121a] z-10">
          <div className="flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-sky-400" />
            <span className="font-mono text-xs uppercase font-bold text-[#f0f6fc]">
              Geospatial Intelligence Map ({filteredProjects.length} Visible)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(e.target.value)}
              className="bg-[#121720] border border-[#1e2633] rounded px-2 py-1 text-xs text-[#f0f6fc] font-mono focus:outline-none"
            >
              <option value="ALL">All Risk Levels</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>

            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="bg-[#121720] border border-[#1e2633] rounded px-2 py-1 text-xs text-[#f0f6fc] font-mono focus:outline-none"
            >
              <option value="ALL">All Districts</option>
              {districts.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>

            <button
              onClick={() => setDuplicateOnly(!duplicateOnly)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-colors border ${
                duplicateOnly
                  ? 'bg-red-950 text-red-300 border-red-800'
                  : 'bg-[#121720] text-[#8b949e] border-[#1e2633] hover:text-white'
              }`}
            >
              {duplicateOnly ? '✓ Duplicates Only (24)' : 'Show Duplicates Only'}
            </button>
          </div>
        </div>

        <div className="flex-1 w-full h-full relative">
          <MapContainer
            center={centerPosition}
            zoom={5}
            scrollWheelZoom={true}
            style={{ width: '100%', height: '100%', backgroundColor: '#080a0f' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            {duplicatePairs.map((pair, idx) => (
              <Polyline
                key={`line-${idx}`}
                positions={[
                  [pair.p1.latitude, pair.p1.longitude],
                  [pair.p2.latitude, pair.p2.longitude],
                ]}
                pathOptions={{
                  color: '#ef4444',
                  weight: 2,
                  dashArray: '4, 4',
                  opacity: 0.8,
                }}
              />
            ))}

            {filteredProjects.map((p) => {
              const r = riskMap.get(p.project_id);
              const level = r?.risk_level || 'LOW';
              const color = getColor(level);
              const isDuplicate = duplicateProjectIds.has(p.project_id);

              return (
                <CircleMarker
                  key={p.project_id}
                  center={[p.latitude, p.longitude]}
                  radius={level === 'CRITICAL' ? 8 : isDuplicate ? 6.5 : 4.5}
                  pathOptions={{
                    fillColor: color,
                    fillOpacity: 0.85,
                    color: isDuplicate ? '#ffffff' : color,
                    weight: isDuplicate ? 2 : 1,
                  }}
                >
                  <Popup>
                    <div className="p-1 space-y-2 text-xs font-mono">
                      <div className="flex items-center justify-between border-b border-[#1e2633] pb-1">
                        <span className="font-bold text-sky-400">{p.project_id}</span>
                        <RiskBadge level={level} score={r?.risk_score} showScore size="sm" />
                      </div>
                      <div className="text-[#f0f6fc] font-medium leading-snug">
                        {p.work_name}
                      </div>
                      <div className="text-[#8b949e] text-[11px] space-y-0.5">
                        <div>District: {p.district}</div>
                        <div>Progress: {formatProgressPct(p.physical_progress_pct)}</div>
                        <div>Sanction: {formatCurrencyLakh(p.sanctioned_amount_lakh)}</div>
                        {isDuplicate && (
                          <div className="text-red-400 font-bold mt-1">
                            ⚠ POTENTIAL DUPLICATE WORK
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => onSelectProject(p.project_id)}
                        className="w-full mt-2 py-1 px-2 rounded bg-sky-950 text-sky-300 border border-sky-800 hover:bg-sky-900 text-[11px] font-bold text-center"
                      >
                        OPEN PROJECT DOSSIER →
                      </button>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
      </div>

      <div className="lg:col-span-4 xl:col-span-3 bg-[#0c1017] border border-[#1e2633] rounded-lg p-4 flex flex-col justify-between overflow-hidden">
        <div>
          <div className="flex items-center justify-between border-b border-[#1e2633]/60 pb-2 mb-3">
            <div className="flex items-center space-x-2">
              <Copy className="w-4 h-4 text-red-400" />
              <span className="font-mono text-xs uppercase font-bold text-[#f0f6fc]">
                Potential Duplicate Pairs ({duplicatePairs.length})
              </span>
            </div>
            <span className="text-[10px] font-mono text-[#8b949e]">
              Composite $\ge 0.65$
            </span>
          </div>

          <div className="overflow-y-auto max-h-[480px] space-y-2.5 pr-1">
            {duplicatePairs.map((pair, idx) => (
              <div
                key={idx}
                className="p-3 rounded bg-[#121720] border border-[#1e2633] space-y-2"
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center space-x-1.5 font-bold">
                    <span className="text-sky-400 cursor-pointer hover:underline" onClick={() => onSelectProject(pair.p1.project_id)}>
                      {pair.p1.project_id}
                    </span>
                    <span className="text-[#8b949e]">↔</span>
                    <span className="text-sky-400 cursor-pointer hover:underline" onClick={() => onSelectProject(pair.p2.project_id)}>
                      {pair.p2.project_id}
                    </span>
                  </div>
                  <span className="px-1.5 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 text-[10px]">
                    {pair.distanceKm.toFixed(2)} km
                  </span>
                </div>

                <div className="text-[11px] text-[#8b949e] font-mono">
                  <div className="text-[#f0f6fc] truncate">{pair.p1.work_name}</div>
                  <div className="text-[#f0f6fc]/70 truncate">{pair.p2.work_name}</div>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-[#1e2633]/60 text-[10px] font-mono text-[#8b949e]">
                  <span>Match: {pair.similarity.toFixed(1)}%</span>
                  <button
                    onClick={() => onSelectProject(pair.p1.project_id)}
                    className="text-sky-400 hover:text-sky-300"
                  >
                    Investigate Pair →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-3 border-t border-[#1e2633]/60 text-[10px] font-mono text-[#8b949e]">
          NOTE: Proximity alone does not trigger duplication; requires name, category, and cost alignment.
        </div>
      </div>
    </div>
  );
};
