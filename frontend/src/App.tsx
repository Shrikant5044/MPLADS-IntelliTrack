import React, { useEffect, useState } from "react";
import {
  AnomalyResult,
  AnomalySummary,
  DistrictAnalyticsSummary,
  DistrictRiskProfile,
  MLAnomalySummary,
  NavigationTab,
  Project,
  ProjectMLPrediction,
  ProjectRiskProfile,
  RiskEngineSummary,
  SystemHealth,
} from "./types";
import { api } from "./api/client";
import { Header } from "./components/layout/Header";
import { GlobalSearchModal } from "./components/layout/GlobalSearchModal";
import { OverviewView } from "./components/overview/OverviewView";
import { RiskAlertsView } from "./components/risk/RiskAlertsView";
import { ProjectsView } from "./components/projects/ProjectsView";
import { GeoView } from "./components/geo/GeoView";
import { AnalyticsView } from "./components/analytics/AnalyticsView";
import { ProjectDossierModal } from "./components/dossier/ProjectDossierModal";
import { ShieldAlert, AlertTriangle, RefreshCw } from "lucide-react";

export const App: React.FC = () => {
  // Navigation & Dossier state
  const [activeTab, setActiveTab] = useState<NavigationTab>("OVERVIEW");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);

  // Application Data State
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyResult[]>([]);
  const [anomalySummary, setAnomalySummary] = useState<AnomalySummary | null>(null);
  const [riskProfiles, setRiskProfiles] = useState<ProjectRiskProfile[]>([]);
  const [riskSummary, setRiskSummary] = useState<RiskEngineSummary | null>(null);
  const [mlPredictions, setMLPredictions] = useState<ProjectMLPrediction[]>([]);
  const [mlSummary, setMLSummary] = useState<MLAnomalySummary | null>(null);
  const [districts, setDistricts] = useState<DistrictRiskProfile[]>([]);
  const [districtSummary, setDistrictSummary] = useState<DistrictAnalyticsSummary | null>(null);

  // Loading & Error States
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const loadData = async () => {
    try {
      setError(null);
      const [hRes, pRes, aRes, rRes, mRes, dRes] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getProjects(500, 0),
        api.getAnomalies({ limit: 2500 }),
        api.getRiskProfiles({ limit: 500 }),
        api.getMLAnomalies({ limit: 500 }),
        api.getDistricts().catch(() => null),
      ]);

      if (hRes) setHealth(hRes);
      setProjects(pRes.data || []);
      setAnomalies(aRes.data || []);
      setAnomalySummary(aRes.summary || null);
      setRiskProfiles(rRes.data || []);
      setRiskSummary(rRes.summary || null);
      setMLPredictions(mRes.data || []);
      setMLSummary(mRes.summary || null);
      if (dRes) {
        setDistricts(dRes.data || []);
        setDistrictSummary(dRes.summary || null);
      }
    } catch (err: any) {
      console.error("Failed to load MPLADS intelligence data:", err);
      setError(err?.message || "Failed to connect to backend intelligence service.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Global Keyboard Shortcut (⌘K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    loadData();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center space-y-4 font-sans text-slate-800">
        <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center shadow-xs animate-pulse">
          <ShieldAlert className="w-6 h-6 text-blue-600" />
        </div>
        <div className="text-center space-y-1">
          <div className="text-sm font-bold text-slate-900 tracking-tight">
            Loading MPLADS Intelligence Platform
          </div>
          <div className="text-xs text-slate-500">
            Synchronizing 31 Anomaly Rules, ML Outliers & Trajectory Forecasts...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 font-sans">
        <div className="max-w-md w-full p-6 bg-white border border-rose-200 rounded-2xl shadow-lg text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto text-rose-600">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Backend Connection Error</h2>
            <p className="text-xs text-slate-500 mt-1">{error}</p>
          </div>
          <button
            onClick={() => {
              setIsLoading(true);
              loadData();
            }}
            className="px-4 py-2 rounded-lg bg-slate-900 text-white hover:bg-slate-800 text-xs font-bold transition-colors inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100/60 text-slate-900 font-sans flex flex-col antialiased">
      {/* Government Standard Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        health={health}
        onOpenSearch={() => setIsSearchOpen(true)}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* Main Content View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {activeTab === "OVERVIEW" && (
          <OverviewView
            projects={projects}
            riskProfiles={riskProfiles}
            riskSummary={riskSummary}
            anomalies={anomalies}
            anomalySummary={anomalySummary}
            mlSummary={mlSummary}
            onSelectProject={setSelectedProjectId}
            onNavigateTab={setActiveTab}
          />
        )}

        {activeTab === "RISK_ALERTS" && (
          <RiskAlertsView
            projects={projects}
            riskProfiles={riskProfiles}
            anomalies={anomalies}
            onSelectProject={setSelectedProjectId}
          />
        )}

        {activeTab === "PROJECTS" && (
          <ProjectsView
            projects={projects}
            riskProfiles={riskProfiles}
            onSelectProject={setSelectedProjectId}
          />
        )}

        {activeTab === "GEO" && (
          <GeoView
            projects={projects}
            riskProfiles={riskProfiles}
            districts={districts}
            onSelectProject={setSelectedProjectId}
          />
        )}

        {activeTab === "ANALYTICS" && (
          <AnalyticsView
            projects={projects}
            riskProfiles={riskProfiles}
            districts={districts}
            districtSummary={districtSummary}
            onSelectProject={setSelectedProjectId}
          />
        )}
      </main>

      {/* Project Dossier Modal */}
      {selectedProjectId && (
        <ProjectDossierModal
          projectId={selectedProjectId}
          onClose={() => setSelectedProjectId(null)}
          allProjects={projects}
          allRiskProfiles={riskProfiles}
          allAnomalies={anomalies}
          allMLPredictions={mlPredictions}
        />
      )}

      {/* Global Quick Search Modal */}
      <GlobalSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        projects={projects}
        riskProfiles={riskProfiles}
        onSelectProject={setSelectedProjectId}
      />

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-xs text-slate-500 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            <strong>MPLADS-IntelliTrack</strong> • Smart India Hackathon Problem Statement 26102
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-400">
            <span>Deterministic Anomaly Engine</span>
            <span>•</span>
            <span>Unsupervised Isolation Forest</span>
            <span>•</span>
            <span>Trajectory Forecasting</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
