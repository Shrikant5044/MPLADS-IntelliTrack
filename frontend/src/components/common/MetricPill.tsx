import React from 'react';

interface Props {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: string;
  highlight?: boolean;
}

export const MetricPill: React.FC<Props> = ({ label, value, subtext, highlight = false }) => {
  return (
    <div className={`flex flex-col p-3 rounded border ${highlight ? 'bg-sky-950/20 border-sky-800/50' : 'bg-[#0d1117] border-[#1e2633]'}`}>
      <span className="text-[11px] uppercase tracking-wider text-[#8b949e] font-mono">{label}</span>
      <div className="flex items-baseline space-x-2 mt-1">
        <span className="text-xl font-bold font-mono text-[#f0f6fc]">{value}</span>
        {subtext && <span className="text-xs text-[#8b949e]">{subtext}</span>}
      </div>
    </div>
  );
};
