import React from "react";
import {
  ShieldAlert,
  AlertCircle,
  ArrowDown,
  Database,
  Cpu,
  BarChart3,
  Layers,
  Search,
  Lock,
  Award,
  GitBranch,
  Info,
} from "lucide-react";

export const AboutView: React.FC = () => {
  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-2">
            <Info className="w-3.5 h-3.5" />
            Platform Architecture & Purpose
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            About MPLADS-IntelliTrack
          </h1>
          <p className="text-sm font-semibold text-blue-900 mt-1">
            Turning project data into actionable monitoring intelligence.
          </p>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          <div className="px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 shadow-xs">
            <Award className="w-3.5 h-3.5 text-blue-400" />
            <span>SIH 2026 · SIH26102</span>
          </div>
        </div>
      </div>

      {/* Two-Column Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Overview, Pillars, Disclaimer, Accountable Monitoring, Badge */}
        <div className="lg:col-span-7 space-y-6">
          {/* Main Description Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-5">
            <div>
              <h2 className="text-base font-bold text-slate-900 mb-2">
                Executive Overview
              </h2>
              <p className="text-xs text-slate-700 leading-relaxed font-normal">
                <strong className="text-slate-900 font-semibold">MPLADS-IntelliTrack</strong> is an AI-powered monitoring and risk intelligence platform designed to help authorities identify and prioritize MPLADS projects that require closer review.
              </p>
            </div>

            {/* Core Pillars List */}
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
                The Platform Combines
              </h3>
              <div className="space-y-2.5">
                <div className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                  <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <div className="text-xs text-slate-700">
                    <strong className="text-slate-900 font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 font-mono">
                      31 Rules
                    </strong>{" "}
                    domain-specific deterministic anomaly detection rules
                  </div>
                </div>

                <div className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                  <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <div className="text-xs text-slate-700">
                    <strong className="text-slate-900 font-bold px-1.5 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200 font-mono">
                      ML
                    </strong>{" "}
                    Isolation Forest-based statistical anomaly detection
                  </div>
                </div>

                <div className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                  <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <div className="text-xs text-slate-700">
                    <strong className="text-slate-900 font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono">
                      Real MPLADS Benchmark
                    </strong>{" "}
                    peer comparison with authentic historical works
                  </div>
                </div>

                <div className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                  <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <div className="text-xs text-slate-700">
                    <strong className="text-slate-900 font-bold px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-mono">
                      Risk Score
                    </strong>{" "}
                    explainable multi-factor risk scoring (0–100)
                  </div>
                </div>

                <div className="flex items-start gap-2.5 p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                  <span className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <div className="text-xs text-slate-700">
                    <strong className="text-slate-900 font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 font-mono">
                      Investigation
                    </strong>{" "}
                    jurisdiction-aware monitoring and case investigation workflows
                  </div>
                </div>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed border-t border-slate-100 pt-4">
              It analyzes patterns across project costs, progress, payments, vendors, agencies, geography, and supporting documentation to identify projects that may require closer attention.
            </p>
          </div>

          {/* Important Message Disclaimer Box */}
          <div className="bg-amber-50/80 rounded-xl border border-amber-200/90 p-5 shadow-xs">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-amber-100 text-amber-800 shrink-0 mt-0.5">
                <AlertCircle className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                  Important Monitoring Directive
                </h3>
                <p className="text-xs text-amber-950 font-medium leading-relaxed">
                  The platform does not declare a project as fraudulent.
                </p>
                <p className="text-xs text-amber-900 leading-relaxed">
                  It helps authorities identify which projects deserve closer attention — and why.
                </p>
              </div>
            </div>
          </div>

          {/* Small Accountable Monitoring Block */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex items-start gap-3">
            <div className="p-2 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 shrink-0 mt-0.5">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-slate-900">
                Accountable Monitoring
              </h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Use role-based access control and jurisdiction-aware workflows so users see and act on information according to their authorized scope.
              </p>
            </div>
          </div>

          {/* Small Prototype Badge / Footer */}
          <div className="bg-slate-900 text-white rounded-xl p-4 shadow-xs flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-mono font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>SIH 2026 · Problem Statement SIH26102 · Team Code-Red</span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">MoSPI Official</span>
          </div>
        </div>

        {/* RIGHT COLUMN: Visual Workflow & 5 Compact Explanations */}
        <div className="lg:col-span-5 space-y-6">
          {/* Visual Workflow Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Visual Intelligence Workflow
                </h2>
                <p className="text-[11px] text-slate-500">
                  End-to-end data ingestion to administrative action
                </p>
              </div>
              <GitBranch className="w-4 h-4 text-slate-400" />
            </div>

            {/* Vertical Flowchart Steps */}
            <div className="space-y-2">
              {/* Step 1: Project Data */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Database className="w-4 h-4 text-slate-600" />
                  <span className="text-xs font-bold text-slate-800 tracking-wide font-mono">
                    PROJECT DATA
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 font-medium">Stage 1</span>
              </div>

              <div className="flex justify-center text-slate-400 py-0.5">
                <ArrowDown className="w-4 h-4 animate-bounce" />
              </div>

              {/* Step 2: 31 Rules + ML (Visually Prominent) */}
              <div className="p-3 bg-blue-50/80 rounded-lg border border-blue-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Cpu className="w-4 h-4 text-blue-700" />
                  <span className="text-xs font-bold text-blue-900 tracking-wide font-mono">
                    31 RULES + ML
                  </span>
                </div>
                <span className="text-[10px] font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded border border-blue-300">
                  Detection Engine
                </span>
              </div>

              <div className="flex justify-center text-slate-400 py-0.5">
                <ArrowDown className="w-4 h-4" />
              </div>

              {/* Step 3: Risk Score (Visually Prominent) */}
              <div className="p-3 bg-purple-50/80 rounded-lg border border-purple-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <ShieldAlert className="w-4 h-4 text-purple-700" />
                  <span className="text-xs font-bold text-purple-900 tracking-wide font-mono">
                    RISK SCORE
                  </span>
                </div>
                <span className="text-[10px] font-bold text-purple-700 bg-purple-100 px-2 py-0.5 rounded border border-purple-300">
                  0–100 Scale
                </span>
              </div>

              <div className="flex justify-center text-slate-400 py-0.5">
                <ArrowDown className="w-4 h-4" />
              </div>

              {/* Step 4: Real MPLADS Benchmark (Visually Prominent) */}
              <div className="p-3 bg-emerald-50/80 rounded-lg border border-emerald-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <BarChart3 className="w-4 h-4 text-emerald-700" />
                  <span className="text-xs font-bold text-emerald-900 tracking-wide font-mono">
                    REAL MPLADS BENCHMARK
                  </span>
                </div>
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300">
                  Peer Baseline
                </span>
              </div>

              <div className="flex justify-center text-slate-400 py-0.5">
                <ArrowDown className="w-4 h-4" />
              </div>

              {/* Step 5: Priority */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Layers className="w-4 h-4 text-slate-700" />
                  <span className="text-xs font-bold text-slate-800 tracking-wide font-mono">
                    PRIORITY
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-medium">Stage 5</span>
              </div>

              <div className="flex justify-center text-slate-400 py-0.5">
                <ArrowDown className="w-4 h-4 text-rose-500" />
              </div>

              {/* Step 6: Investigation (Visually Prominent) */}
              <div className="p-3 bg-rose-50/80 rounded-lg border border-rose-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Search className="w-4 h-4 text-rose-700" />
                  <span className="text-xs font-bold text-rose-900 tracking-wide font-mono">
                    INVESTIGATION
                  </span>
                </div>
                <span className="text-[10px] font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded border border-rose-300">
                  Actionable Resolution
                </span>
              </div>
            </div>
          </div>

          {/* 5 Compact Explanation Items */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2">
              Workflow Stages & Responsibilities
            </h3>

            <div className="space-y-3">
              {/* 1. DETECT */}
              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/40 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 font-mono">
                    1. DETECT
                  </span>
                  <span className="text-xs font-bold text-slate-900">Pattern Identification</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Identify unusual project patterns using deterministic anomaly rules and statistical ML signals.
                </p>
              </div>

              {/* 2. EXPLAIN */}
              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/40 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 font-mono">
                    2. EXPLAIN
                  </span>
                  <span className="text-xs font-bold text-slate-900">Transparent Signals</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Show the evidence and signals contributing to a project's risk assessment.
                </p>
              </div>

              {/* 3. BENCHMARK */}
              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/40 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 font-mono">
                    3. BENCHMARK
                  </span>
                  <span className="text-xs font-bold text-slate-900">Contextual Peer Evidence</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Compare projects with relevant real MPLADS works to provide contextual evidence.
                </p>
              </div>

              {/* 4. PRIORITIZE */}
              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/40 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 font-mono">
                    4. PRIORITIZE
                  </span>
                  <span className="text-xs font-bold text-slate-900">Risk Scoring & Ranking</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Convert detected signals into an explainable 0–100 risk score and monitoring priority.
                </p>
              </div>

              {/* 5. INVESTIGATE */}
              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/40 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 font-mono">
                    5. INVESTIGATE
                  </span>
                  <span className="text-xs font-bold text-slate-900">Structured Case Workflow</span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  Allow authorized officers to create, assign, track, and document investigations through a structured workflow.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
