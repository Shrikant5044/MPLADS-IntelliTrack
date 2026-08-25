import React from "react";

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const norm = (status || "ONGOING").toUpperCase();

  let style = "bg-blue-50 text-blue-700 border-blue-200";
  if (norm === "COMPLETED") {
    style = "bg-emerald-50 text-emerald-700 border-emerald-200";
  } else if (norm === "DELAYED") {
    style = "bg-rose-50 text-rose-700 border-rose-200";
  } else if (norm === "UNDER REVIEW") {
    style = "bg-purple-50 text-purple-700 border-purple-200";
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${style}`}>
      {status}
    </span>
  );
};
