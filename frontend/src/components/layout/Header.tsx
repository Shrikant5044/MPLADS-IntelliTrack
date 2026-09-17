import React from "react";
import { NavigationTab, SystemHealth } from "../../types";
import { useAuth } from "../../context/AuthContext";
import {
  LayoutDashboard,
  ShieldAlert,
  FolderKanban,
  MapPin,
  BarChart3,
  Search,
  RefreshCw,
  Landmark,
  LogOut,
  LogIn,
  KeyRound,
} from "lucide-react";


interface HeaderProps {
  activeTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  health: SystemHealth | null;
  onOpenSearch: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenLoginModal?: () => void;
  onOpenAdminModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  health,
  onOpenSearch,
  onRefresh,
  isRefreshing,
  onOpenLoginModal,
  onOpenAdminModal,
}) => {
  const { user, isAuthenticated, logout } = useAuth();

  const navItems: Array<{ id: NavigationTab; label: string; icon: any }> = [
    { id: "OVERVIEW", label: "Overview", icon: LayoutDashboard },
    { id: "RISK_ALERTS", label: "Risk & Alerts", icon: ShieldAlert },
    { id: "PROJECTS", label: "Projects", icon: FolderKanban },
    { id: "GEO", label: "Geo Intelligence", icon: MapPin },
    { id: "ANALYTICS", label: "Analytics", icon: BarChart3 },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      {/* Government of India MoSPI Banner */}
      <div className="bg-slate-900 text-slate-200 px-4 sm:px-6 py-1.5 text-[11px] flex items-center justify-between font-medium">
        <div className="flex items-center gap-2">
          <Landmark className="w-3.5 h-3.5 text-blue-400" />
          <span>Government of India • Ministry of Statistics and Programme Implementation (MoSPI)</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${health ? "bg-emerald-400" : "bg-rose-400"} animate-pulse`} />
            <span className="text-slate-300">
              {health ? `Backend Live (v${health.version})` : "Connecting..."}
            </span>
          </div>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400 font-mono">SIH 26102</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16 gap-4">
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm font-bold tracking-tight">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-slate-900 text-base tracking-tight">
                  MPLADS-IntelliTrack
                </span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  v2.0
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                AI Monitoring Command Center
              </p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                    isActive
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onOpenSearch}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-500 text-xs font-medium transition-colors cursor-pointer"
            >
              <Search className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Search works...</span>
              <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-white rounded border border-slate-200 text-slate-400">
                ⌘K
              </kbd>
            </button>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Refresh intelligence cache"
              className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-blue-600" : ""}`} />
            </button>

            {/* Authenticated Officer Profile Display */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <div className="hidden lg:flex flex-col text-right">
                  <span className="text-xs font-bold text-slate-900 leading-tight">
                    {user.full_name}
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium">
                    {user.role === "MOSPI_OFFICER" && "MoSPI Officer (National)"}
                    {user.role === "DISTRICT_AUTHORITY" && `District Authority (${user.assigned_district})`}
                    {user.role === "ADMIN" && "System Administrator"}
                  </span>
                </div>

                {user.role === "ADMIN" && onOpenAdminModal && (
                  <button
                    onClick={onOpenAdminModal}
                    title="User Management (ADMIN)"
                    className="p-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition-colors cursor-pointer"
                  >
                    <KeyRound className="w-4 h-4" />
                  </button>
                )}

                <button
                  onClick={logout}
                  title="Sign Out"
                  className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenLoginModal}
                className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Officer Login</span>
              </button>
            )}
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="flex md:hidden items-center gap-1 overflow-x-auto py-2 border-t border-slate-100">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap transition-all cursor-pointer ${
                  isActive
                    ? "bg-slate-900 text-white shadow-xs"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
