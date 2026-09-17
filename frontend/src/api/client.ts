import {
  AnomaliesResponse,
  AuditQueueResponse,
  BenchmarkListResponse,
  CreateInvestigationRequest,
  DistrictAnalyticsResponse,
  ForecastListResponse,
  InvestigationRecord,
  LoginRequest,
  MLAnomaliesResponse,
  ProjectAnomaliesResponse,
  ProjectBenchmarkResult,
  ProjectForecastResult,
  ProjectMLPrediction,
  ProjectRiskProfile,
  ProjectsResponse,
  RealMPLADSStatsResponse,
  RealWorkBenchmarkResult,
  RealWorksListResponse,
  RiskListResponse,
  SystemHealth,
  TokenResponse,
  User,
  UserCreate,
  UserUpdate,
} from "../types";

const BASE_URL = "";

let authToken: string | null = localStorage.getItem("mplads_auth_token");

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem("mplads_auth_token", token);
  } else {
    localStorage.removeItem("mplads_auth_token");
  }
}

export function getAuthToken(): string | null {
  return authToken;
}

function getAuthHeaders(isJson = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (isJson) {
    headers["Content-Type"] = "application/json";
  }
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return headers;
}

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
  // -----------------------------------------------------------
  // AUTHENTICATION
  // -----------------------------------------------------------
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const res = await fetch(`${BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials),
    });
    const data = await handleResponse<TokenResponse>(res);
    setAuthToken(data.access_token);
    return data;
  },

  async getMe(): Promise<User> {
    const res = await fetch(`${BASE_URL}/api/auth/me`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<User>(res);
  },

  async logout(): Promise<{ status: string; message: string }> {
    try {
      const res = await fetch(`${BASE_URL}/api/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
      return await handleResponse<{ status: string; message: string }>(res);
    } finally {
      setAuthToken(null);
    }
  },

  // -----------------------------------------------------------
  // ADMIN USER MANAGEMENT
  // -----------------------------------------------------------
  async getUsers(): Promise<User[]> {
    const res = await fetch(`${BASE_URL}/api/admin/users`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<User[]>(res);
  },

  async createUser(payload: UserCreate): Promise<User> {
    const res = await fetch(`${BASE_URL}/api/admin/users`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    return handleResponse<User>(res);
  },

  async updateUser(userId: string, payload: UserUpdate): Promise<User> {
    const res = await fetch(`${BASE_URL}/api/admin/users/${encodeURIComponent(userId)}`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    return handleResponse<User>(res);
  },

  async deleteUser(userId: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${BASE_URL}/api/admin/users/${encodeURIComponent(userId)}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    return handleResponse<{ status: string; message: string }>(res);
  },

  // -----------------------------------------------------------
  // INVESTIGATION / CASE MANAGEMENT
  // -----------------------------------------------------------
  async getInvestigations(district?: string): Promise<InvestigationRecord[]> {
    const query = new URLSearchParams();
    if (district) query.set("district", district);
    const res = await fetch(`${BASE_URL}/api/investigations?${query}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<InvestigationRecord[]>(res);
  },

  async getInvestigation(investigationId: string): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  async getProjectInvestigation(projectId: string): Promise<InvestigationRecord | null> {
    const res = await fetch(`${BASE_URL}/api/investigations/project/${encodeURIComponent(projectId)}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<InvestigationRecord | null>(res);
  },

  async createInvestigation(payload: CreateInvestigationRequest): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  async assignInvestigation(
    investigationId: string,
    assignedTo: string,
    assignedRole: string,
    comment?: string,
  ): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/assign`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ assigned_to: assignedTo, assigned_role: assignedRole, comment }),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  async updateInvestigationStatus(
    investigationId: string,
    status: string,
    comment: string,
  ): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/status`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ status, comment }),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  async updateInvestigationProgress(
    investigationId: string,
    progressPercentage: number,
    comment?: string,
  ): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/progress`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ progress_percentage: progressPercentage, comment }),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  async addInvestigationFinding(
    investigationId: string,
    findingText: string,
    evidenceNotes?: string,
  ): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/findings`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ finding_text: findingText, evidence_notes: evidenceNotes }),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  async escalateInvestigation(investigationId: string, reason: string): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/escalate`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ reason }),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  async resolveInvestigation(
    investigationId: string,
    finalRecommendation: string,
    closeCase = false,
  ): Promise<InvestigationRecord> {
    const res = await fetch(`${BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/resolve`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ final_recommendation: finalRecommendation, close_case: closeCase }),
    });
    return handleResponse<InvestigationRecord>(res);
  },

  // -----------------------------------------------------------
  // CORE INTELLIGENCE APIS
  // -----------------------------------------------------------
  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${BASE_URL}/health`, { headers: getAuthHeaders() });
    return handleResponse<SystemHealth>(res);
  },

  async getProjects(limit = 50, offset = 0, district?: string, state?: string): Promise<ProjectsResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (district) params.set("district", district);
    if (state) params.set("state", state);
    const res = await fetch(`${BASE_URL}/api/projects?${params}`, { headers: getAuthHeaders() });
    return handleResponse<ProjectsResponse>(res);
  },

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

    const res = await fetch(`${BASE_URL}/api/anomalies?${query}`, { headers: getAuthHeaders() });
    return handleResponse<AnomaliesResponse>(res);
  },

  async getProjectAnomalies(projectId: string): Promise<ProjectAnomaliesResponse> {
    const res = await fetch(`${BASE_URL}/api/anomalies/${encodeURIComponent(projectId)}`, { headers: getAuthHeaders() });
    return handleResponse<ProjectAnomaliesResponse>(res);
  },

  async getRiskProfiles(params?: {
    risk_level?: string;
    limit?: number;
    offset?: number;
  }): Promise<RiskListResponse> {
    const query = new URLSearchParams();
    if (params?.risk_level) query.set("risk_level", params.risk_level);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/risk?${query}`, { headers: getAuthHeaders() });
    return handleResponse<RiskListResponse>(res);
  },

  async getProjectRisk(projectId: string): Promise<ProjectRiskProfile> {
    const res = await fetch(`${BASE_URL}/api/risk/${encodeURIComponent(projectId)}`, { headers: getAuthHeaders() });
    return handleResponse<ProjectRiskProfile>(res);
  },

  async getMLAnomalies(params?: {
    anomalous_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<MLAnomaliesResponse> {
    const query = new URLSearchParams();
    if (params?.anomalous_only !== undefined) query.set("anomalous_only", String(params.anomalous_only));
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/ml/anomalies?${query}`, { headers: getAuthHeaders() });
    return handleResponse<MLAnomaliesResponse>(res);
  },

  async getProjectML(projectId: string): Promise<ProjectMLPrediction> {
    const res = await fetch(`${BASE_URL}/api/ml/anomalies/${encodeURIComponent(projectId)}`, { headers: getAuthHeaders() });
    return handleResponse<ProjectMLPrediction>(res);
  },

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

    const res = await fetch(`${BASE_URL}/api/analytics/benchmark?${query}`, { headers: getAuthHeaders() });
    return handleResponse<BenchmarkListResponse>(res);
  },

  async getProjectBenchmark(projectId: string): Promise<ProjectBenchmarkResult> {
    const res = await fetch(`${BASE_URL}/api/analytics/benchmark/${encodeURIComponent(projectId)}`, { headers: getAuthHeaders() });
    return handleResponse<ProjectBenchmarkResult>(res);
  },

  async getForecasts(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ForecastListResponse> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/analytics/forecast?${query}`, { headers: getAuthHeaders() });
    return handleResponse<ForecastListResponse>(res);
  },

  async getProjectForecast(projectId: string): Promise<ProjectForecastResult> {
    const res = await fetch(`${BASE_URL}/api/analytics/forecast/${encodeURIComponent(projectId)}`, { headers: getAuthHeaders() });
    return handleResponse<ProjectForecastResult>(res);
  },

  async getDistricts(): Promise<DistrictAnalyticsResponse> {
    const res = await fetch(`${BASE_URL}/api/analytics/districts`, { headers: getAuthHeaders() });
    return handleResponse<DistrictAnalyticsResponse>(res);
  },

  async getAuditQueue(params?: {
    risk_level?: string;
    investigation_type?: string;
    urgency?: string;
    district?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditQueueResponse> {
    const query = new URLSearchParams();
    if (params?.risk_level) query.set("risk_level", params.risk_level);
    if (params?.investigation_type) query.set("investigation_type", params.investigation_type);
    if (params?.urgency) query.set("urgency", params.urgency);
    if (params?.district) query.set("district", params.district);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/analytics/audit-queue?${query}`, { headers: getAuthHeaders() });
    return handleResponse<AuditQueueResponse>(res);
  },

  async getRealMPLADSWorks(params?: {
    dataset?: string;
    state?: string;
    category?: string;
    q?: string;
    limit?: number;
    offset?: number;
  }): Promise<RealWorksListResponse> {
    const query = new URLSearchParams();
    if (params?.dataset) query.set("dataset", params.dataset);
    if (params?.state) query.set("state", params.state);
    if (params?.category) query.set("category", params.category);
    if (params?.q) query.set("q", params.q);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));

    const res = await fetch(`${BASE_URL}/api/real-mplads/works?${query}`, { headers: getAuthHeaders() });
    return handleResponse<RealWorksListResponse>(res);
  },

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
  }): Promise<RealWorkBenchmarkResult> {
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

    const res = await fetch(`${BASE_URL}/api/real-mplads/benchmark?${query}`, { headers: getAuthHeaders() });
    return handleResponse<RealWorkBenchmarkResult>(res);
  },

  async getRealMPLADSStats(): Promise<RealMPLADSStatsResponse> {
    const res = await fetch(`${BASE_URL}/api/real-mplads/stats`, { headers: getAuthHeaders() });
    return handleResponse<RealMPLADSStatsResponse>(res);
  },
};
