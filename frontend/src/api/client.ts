import {
  AnomaliesResponse,
  AuditQueueResponse,
  BenchmarkListResponse,
  DistrictAnalyticsResponse,
  ForecastListResponse,
  MLAnomaliesResponse,
  ProjectAnomaliesResponse,
  ProjectBenchmarkResult,
  ProjectForecastResult,
  ProjectMLPrediction,
  ProjectRiskProfile,
  ProjectsResponse,
  RiskListResponse,
  SystemHealth,
} from "../types";

const BASE_URL = "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = "API request failed";
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // System Health
  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${BASE_URL}/health`);
    return handleResponse<SystemHealth>(res);
  },

  // Projects Explorer
  async getProjects(limit = 50, offset = 0): Promise<ProjectsResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    const res = await fetch(`${BASE_URL}/api/projects?${params}`);
    return handleResponse<ProjectsResponse>(res);
  },

  // All Anomalies
  async getAnomalies(params?: {
    severity?: string;
    anomaly_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<AnomaliesResponse> {
    const query = new URLSearchParams();
    if (params?.severity) query.set("severity", params.severity);
    if (params?.anomaly_type) query.set("anomaly_type", params.anomaly_type);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/anomalies?${query}`);
    return handleResponse<AnomaliesResponse>(res);
  },

  // Project Specific Anomalies
  async getProjectAnomalies(projectId: string): Promise<ProjectAnomaliesResponse> {
    const res = await fetch(`${BASE_URL}/api/anomalies/${encodeURIComponent(projectId)}`);
    return handleResponse<ProjectAnomaliesResponse>(res);
  },

  // Risk Profiles
  async getRiskProfiles(params?: {
    risk_level?: string;
    limit?: number;
    offset?: number;
  }): Promise<RiskListResponse> {
    const query = new URLSearchParams();
    if (params?.risk_level) query.set("risk_level", params.risk_level);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/risk?${query}`);
    return handleResponse<RiskListResponse>(res);
  },

  // Project Specific Risk Profile
  async getProjectRisk(projectId: string): Promise<ProjectRiskProfile> {
    const res = await fetch(`${BASE_URL}/api/risk/${encodeURIComponent(projectId)}`);
    return handleResponse<ProjectRiskProfile>(res);
  },

  // ML Statistical Outliers
  async getMLAnomalies(params?: {
    anomalous_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<MLAnomaliesResponse> {
    const query = new URLSearchParams();
    if (params?.anomalous_only !== undefined) query.set("anomalous_only", String(params.anomalous_only));
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/ml/anomalies?${query}`);
    return handleResponse<MLAnomaliesResponse>(res);
  },

  // Project ML Prediction
  async getProjectML(projectId: string): Promise<ProjectMLPrediction> {
    const res = await fetch(`${BASE_URL}/api/ml/anomalies/${encodeURIComponent(projectId)}`);
    return handleResponse<ProjectMLPrediction>(res);
  },

  // Benchmarking Explorer
  async getBenchmarks(params?: {
    status?: string;
    tier?: string;
    limit?: number;
    offset?: number;
  }): Promise<BenchmarkListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.tier) query.set("tier", params.tier);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/analytics/benchmark?${query}`);
    return handleResponse<BenchmarkListResponse>(res);
  },

  // Project Benchmark
  async getProjectBenchmark(projectId: string): Promise<ProjectBenchmarkResult> {
    const res = await fetch(`${BASE_URL}/api/analytics/benchmark/${encodeURIComponent(projectId)}`);
    return handleResponse<ProjectBenchmarkResult>(res);
  },

  // Early Warning Forecasts
  async getForecasts(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ForecastListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/analytics/forecast?${query}`);
    return handleResponse<ForecastListResponse>(res);
  },

  // Project Forecast
  async getProjectForecast(projectId: string): Promise<ProjectForecastResult> {
    const res = await fetch(`${BASE_URL}/api/analytics/forecast/${encodeURIComponent(projectId)}`);
    return handleResponse<ProjectForecastResult>(res);
  },

  // District Analytics
  async getDistricts(): Promise<DistrictAnalyticsResponse> {
    const res = await fetch(`${BASE_URL}/api/analytics/districts`);
    return handleResponse<DistrictAnalyticsResponse>(res);
  },

  // Prioritized Audit Queue
  async getAuditQueue(params?: {
    risk_level?: string;
    investigation_type?: string;
    urgency?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditQueueResponse> {
    const query = new URLSearchParams();
    if (params?.risk_level) query.set("risk_level", params.risk_level);
    if (params?.investigation_type) query.set("investigation_type", params.investigation_type);
    if (params?.urgency) query.set("urgency", params.urgency);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/analytics/audit-queue?${query}`);
    return handleResponse<AuditQueueResponse>(res);
  },

  // Real MPLADS Works Explorer
  async getRealMPLADSWorks(params?: {
    dataset?: string;
    state?: string;
    category?: string;
    q?: string;
    limit?: number;
    offset?: number;
  }): Promise<import("../types").RealWorksListResponse> {
    const query = new URLSearchParams();
    if (params?.dataset) query.set("dataset", params.dataset);
    if (params?.state) query.set("state", params.state);
    if (params?.category) query.set("category", params.category);
    if (params?.q) query.set("q", params.q);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/real-mplads/works?${query}`);
    return handleResponse<import("../types").RealWorksListResponse>(res);
  },

  // Real MPLADS Peer Benchmarking
  async getRealMPLADSBenchmark(params: {
    work_id?: number;
    dataset?: string;
    description?: string;
    amount?: number;
    state?: string;
    category?: string;
    ida?: string;
    top_k?: number;
    min_similarity?: number;
  }): Promise<import("../types").RealWorkBenchmarkResult> {
    const query = new URLSearchParams();
    if (params.work_id !== undefined) query.set("work_id", String(params.work_id));
    if (params.dataset) query.set("dataset", params.dataset);
    if (params.description) query.set("description", params.description);
    if (params.amount !== undefined) query.set("amount", String(params.amount));
    if (params.state) query.set("state", params.state);
    if (params.category) query.set("category", params.category);
    if (params.ida) query.set("ida", params.ida);
    if (params.top_k) query.set("top_k", String(params.top_k));
    if (params.min_similarity) query.set("min_similarity", String(params.min_similarity));

    const res = await fetch(`${BASE_URL}/api/real-mplads/benchmark?${query}`);
    return handleResponse<import("../types").RealWorkBenchmarkResult>(res);
  },

  // Real MPLADS Dataset Stats
  async getRealMPLADSStats(): Promise<import("../types").RealMPLADSStatsResponse> {
    const res = await fetch(`${BASE_URL}/api/real-mplads/stats`);
    return handleResponse<import("../types").RealMPLADSStatsResponse>(res);
  },
};

