import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: "default" | "warning" | "danger" | "critical" | "success" | "info";
  badge?: string;
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  badge,
  onClick,
}) => {
  // Calm, clean government dashboard card hierarchy
  const variantStyles = {
    default: "border-slate-200 hover:border-slate-300 text-slate-900 bg-white",
    warning: "border-slate-200 hover:border-amber-300 text-slate-900 bg-white",
    danger: "border-slate-200 hover:border-rose-300 text-slate-900 bg-white",
    critical: "border-red-300 bg-red-50/40 text-slate-900",
    success: "border-slate-200 hover:border-emerald-300 text-slate-900 bg-white",
    info: "border-slate-200 hover:border-blue-300 text-slate-900 bg-white",
  }[variant];

  const iconColors = {
    default: "text-slate-600 bg-slate-100",
    warning: "text-amber-700 bg-amber-50 border border-amber-200/60",
    danger: "text-rose-600 bg-rose-50 border border-rose-200/60",
    critical: "text-red-700 bg-red-100 border border-red-300",
    success: "text-emerald-700 bg-emerald-50 border border-emerald-200/60",
    info: "text-blue-700 bg-blue-50 border border-blue-200/60",
  }[variant];

  const badgeStyles = {
    default: "bg-slate-100 text-slate-600 border border-slate-200",
    warning: "bg-amber-50 text-amber-700 border border-amber-200",
    danger: "bg-rose-50 text-rose-700 border border-rose-200",
    critical: "bg-red-100 text-red-800 border border-red-300",
    success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    info: "bg-blue-50 text-blue-700 border border-blue-200",
  }[variant];

  return (
    <div
      onClick={onClick}
      className={`rounded-xl border p-5 shadow-xs transition-all ${variantStyles} ${
        onClick ? "cursor-pointer hover:shadow-sm" : ""
      }`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            {title}
          </p>
          <p className="text-2xl font-bold mt-1.5 text-slate-900 tracking-tight font-mono">
            {value}
          </p>
        </div>
        <div className={`p-2.5 rounded-lg ${iconColors}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      {(subtitle || badge) && (
        <div className="mt-3 flex items-center gap-2 pt-2 border-t border-slate-100">
          {badge && (
            <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${badgeStyles}`}>
              {badge}
            </span>
          )}
          {subtitle && (
            <span className="text-xs text-slate-500">{subtitle}</span>
          )}
        </div>
      )}
    </div>
  );
};
