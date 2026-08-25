import React from "react";
import { Severity } from "../../types";

interface SeverityBadgeProps {
  severity: Severity | string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const norm = (severity || "LOW").toUpperCase();

  const styles: Record<string, string> = {
    CRITICAL: "bg-red-50 text-red-700 border-red-200",
    HIGH: "bg-orange-50 text-orange-700 border-orange-200",
    MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
    LOW: "bg-slate-100 text-slate-700 border-slate-200",
  };

  const style = styles[norm] || styles.LOW;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${style}`}>
      {norm}
    </span>
  );
};
