export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type NavigationTab = 
  | "OVERVIEW"
  | "RISK_ALERTS"
  | "PROJECTS"
  | "GEO"
  | "ANALYTICS";

export interface Project {
  project_id: string;
  mp_name: string;
  state: string;
  constituency: string;
  district: string;
  work_name: string;
  work_category: string;
  recommendation_date: string;
  sanction_date: string;
  start_date: string;
  estimated_cost_lakh: number;
  sanctioned_amount_lakh: number;
  expected_completion_date: string;
  actual_completion_date?: string | null;
  status: string;
  agency_id: string;
  vendor_id: string;
  latitude: number;
  longitude: number;
  planned_progress_pct: number;
  physical_progress_pct: number;
  expenditure_lakh: number;
}

export interface ProjectsResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  data: Project[];
}

export interface AnomalyResult {
  project_id: string;
  anomaly_type: string;
  severity: Severity;
  confidence: number;
  evidence: Record<string, any>;
  explanation: string;
}

export interface AnomalySummary {
  total_projects_evaluated: number;
  total_anomalies_detected: number;
  anomalous_projects_count: number;
  anomalies_by_type: Record<string, number>;
  anomalies_by_severity: Record<string, number>;
}

export interface AnomaliesResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  summary: AnomalySummary;
  data: AnomalyResult[];
}

export interface ProjectAnomaliesResponse {
  project_id: string;
  total_anomalies: number;
  anomalies: AnomalyResult[];
}

export interface MLRiskSignal {
  score: number;
  flag: boolean;
  contribution: number;
  model_version: string;
}

export interface RiskFactor {
  category: string;
  signal: string;
  contribution: number;
  severity: Severity;
  confidence: number;
  rule_weight?: number;
  weighted_impact?: number;
}

export interface ProjectRiskProfile {
  project_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  risk_factors: RiskFactor[];
  ml_signal?: MLRiskSignal | null;
  summary: string;
  recommended_action: string;
}

export interface RiskEngineSummary {
  total_projects: number;
  average_risk_score: number;
  risk_level_counts: {
    LOW: number;
    MEDIUM: number;
    HIGH: number;
    CRITICAL: number;
  };
  highest_risk_projects: Array<{
    project_id: string;
    risk_score: number;
    risk_level: string;
    summary: string;
  }>;
}

export interface RiskListResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  summary: RiskEngineSummary;
  data: ProjectRiskProfile[];
}

export interface ProjectMLPrediction {
  project_id: string;
  ml_anomaly_score: number;
  ml_anomaly_flag: boolean;
  model_version: string;
}

export interface MLAnomalySummary {
  total_projects_evaluated: number;
  anomalous_projects_count: number;
  contamination_rate: number;
  average_ml_score: number;
  model_version: string;
  feature_count: number;
}

export interface MLAnomaliesResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  summary: MLAnomalySummary;
  data: ProjectMLPrediction[];
}

// -------------------------------------------------------------
// BENCHMARKING MODELS
// -------------------------------------------------------------
export type BenchmarkStatus = 
  | "NORMAL" 
  | "MODERATE_DEVIATION" 
  | "HIGH_DEVIATION" 
  | "EXTREME_DEVIATION" 
  | "LOW_OUTLIER" 
  | "INSUFFICIENT_PEERS";

export interface PeerSummaryStats {
  peer_count: number;
  peer_tier: string;
  peer_mean_cost_lakh: number;
  peer_median_cost_lakh: number;
  peer_std_cost_lakh: number;
  peer_min_cost_lakh: number;
  peer_max_cost_lakh: number;
  peer_iqr_lakh: number;
}

export interface ProjectBenchmarkResult {
  project_id: string;
  work_name: string;
  work_category: string;
  district: string;
  state: string;
  project_estimated_cost_lakh: number;
  project_sanctioned_amount_lakh: number;
  project_expenditure_lakh: number;
  benchmark_status: BenchmarkStatus;
  peer_hierarchy_tier: string;
  peer_count: number;
  cost_ratio_vs_peer_median?: number | null;
  deviation_percentage?: number | null;
  percentile_position?: number | null;
  confidence: number;
  peer_stats?: PeerSummaryStats | null;
  sample_peer_project_ids?: string[];
  explanation: string;
  limitations: string;
}

export interface BenchmarkSummary {
  total_projects_evaluated: number;
  benchmarkable_projects_count: number;
  insufficient_peers_count: number;
  status_counts: Record<string, number>;
  tier_counts: Record<string, number>;
  average_cost_ratio: number;
}

export interface BenchmarkListResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  summary: BenchmarkSummary;
  data: ProjectBenchmarkResult[];
}

// -------------------------------------------------------------
// FORECASTING MODELS
// -------------------------------------------------------------
export type TrajectoryStatus = 
  | "COMPLETED" 
  | "ON_TRACK" 
  | "WATCH" 
  | "LIKELY_DELAY" 
  | "SEVERE_DELAY_RISK" 
  | "INSUFFICIENT_HISTORY";

export interface ProjectForecastResult {
  project_id: string;
  work_name: string;
  status: string;
  current_progress_pct: number;
  planned_progress_pct: number;
  velocity_pct_per_day?: number | null;
  elapsed_days: number;
  estimated_days_remaining?: number | null;
  forecast_completion_date?: string | null;
  expected_completion_date?: string | null;
  actual_completion_date?: string | null;
  forecast_delay_days?: number | null;
  burn_rate_lakh_per_day?: number | null;
  current_expenditure_lakh: number;
  sanctioned_amount_lakh: number;
  projected_final_expenditure_lakh?: number | null;
  projected_cost_variance_pct?: number | null;
  trajectory_status: TrajectoryStatus;
  confidence: number;
  explanation: string;
  assumptions_and_limitations: string;
}

export interface ForecastSummary {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  status_counts: Record<string, number>;
  average_forecast_delay_days?: number | null;
  total_projected_cost_overrun_lakh: number;
}

export interface ForecastListResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  summary: ForecastSummary;
  data: ProjectForecastResult[];
}

// -------------------------------------------------------------
// DISTRICT ANALYTICS MODELS
// -------------------------------------------------------------
export interface DistrictRiskProfile {
  district: string;
  state: string;
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  total_sanctioned_lakh: number;
  total_expenditure_lakh: number;
  fund_utilization_pct: number;
  average_risk_score: number;
  critical_risk_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  total_anomalies_detected: number;
  anomalous_projects_count: number;
  duplicate_work_pairs_count: number;
  unique_vendors_count: number;
  max_vendor_concentration_share_pct: number;
  top_implementing_agency: string;
}

export interface DistrictAnalyticsSummary {
  total_districts: number;
  total_projects: number;
  national_average_district_risk: number;
  highest_risk_district: string;
  highest_risk_district_score: number;
  total_sanctioned_all_districts_lakh: number;
  total_expenditure_all_districts_lakh: number;
}

export interface DistrictAnalyticsResponse {
  total: number;
  summary: DistrictAnalyticsSummary;
  data: DistrictRiskProfile[];
}

// -------------------------------------------------------------
// AUDIT QUEUE MODELS
// -------------------------------------------------------------
export type AuditUrgency = "CRITICAL_URGENCY" | "HIGH_URGENCY" | "MEDIUM_URGENCY" | "ROUTINE";
export type InvestigationType = 
  | "PHYSICAL_INSPECTION"
  | "FINANCIAL_AUDIT"
  | "PAYMENT_VERIFICATION"
  | "COMPLIANCE_REVIEW"
  | "DUPLICATE_GEO_VERIFICATION"
  | "VENDOR_REVIEW"
  | "AGENCY_REVIEW";

export interface AuditQueueItem {
  priority_rank: number;
  project_id: string;
  work_name: string;
  district: string;
  state: string;
  risk_score: number;
  risk_level: RiskLevel;
  urgency: AuditUrgency;
  primary_risk_drivers: string[];
  anomaly_count: number;
  independent_anomaly_domains_count: number;
  financial_exposure_lakh: number;
  sanctioned_budget_lakh: number;
  recommended_investigation_types: InvestigationType[];
  recommended_action: string;
  decision_support_rationale: string;
  evidence_summary: Record<string, any>;
}

export interface AuditQueueSummary {
  total_queued_projects: number;
  critical_priority_count: number;
  high_priority_count: number;
  medium_priority_count: number;
  routine_priority_count: number;
  investigation_type_counts: Record<string, number>;
  total_financial_exposure_lakh: number;
}

export interface AuditQueueResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  summary: AuditQueueSummary;
  data: AuditQueueItem[];
}

export interface SystemHealth {
  status: string;
  service: string;
  version: string;
}
