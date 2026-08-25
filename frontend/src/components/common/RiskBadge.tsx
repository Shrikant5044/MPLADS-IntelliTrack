import React from "react";
import { RiskLevel } from "../../types";

interface RiskBadgeProps {
  level: RiskLevel | string;
  score?: number;
  showScore?: boolean;
  size?: "sm" | "md" | "lg";
  showDot?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level,
  score,
  showScore = true,
  size = "md",
  showDot = true,
}) => {
  const normLevel = (level || "LOW").toUpperCase();

  let colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-200";
  let dotColor = "bg-emerald-500";
  let label = "LOW RISK";

  if (normLevel === "CRITICAL") {
    colorClasses = "bg-red-100 text-red-800 border-red-300 font-semibold";
    dotColor = "bg-red-600";
    label = "CRITICAL RISK";
  } else if (normLevel === "HIGH") {
    colorClasses = "bg-rose-50 text-rose-700 border-rose-200 font-semibold";
    dotColor = "bg-rose-500";
    label = "HIGH RISK";
  } else if (normLevel === "MEDIUM") {
    colorClasses = "bg-amber-50 text-amber-700 border-amber-200";
    dotColor = "bg-amber-500";
    label = "MEDIUM RISK";
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-xs",
    lg: "px-3 py-1.5 text-sm",
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${colorClasses} ${sizeClasses} transition-colors`}
    >
      {showDot && (
        <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      )}
      <span>{label}</span>
      {showScore && score !== undefined && (
        <span className="font-mono font-bold opacity-90">({score})</span>
      )}
    </span>
  );
};
