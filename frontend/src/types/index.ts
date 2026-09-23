export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type NavigationTab = 
  | "OVERVIEW"
  | "RISK_ALERTS"
  | "PROJECTS"
  | "GEO"
  | "ANALYTICS"
  | "ABOUT";

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

export interface RealWorkRecord {
  work_id: number;
  work_description: string;
  category: string;
  mp_name: string;
  constituency: string;
  state: string;
  house: string;
  amount: number;
  amount_lakh: number;
  date: string;
  has_images: boolean;
  ida: string;
  dataset_source: "recommended_works" | "completed_works";
}

export interface RealComparableWorkPeer {
  work_id: number;
  work_description: string;
  category: string;
  state: string;
  constituency: string;
  mp_name: string;
  ida: string;
  amount: number;
  amount_lakh: number;
  similarity_score: number;
  text_similarity: number;
  state_match: boolean;
  category_match: boolean;
  ida_match: boolean;
  match_tier: string;
  winning_query?: string | null;
}

export interface RealWorkBenchmarkResult {
  status: "SUCCESS" | "INSUFFICIENT_PEERS" | "ERROR_NOT_FOUND";
  analysis_type: string;
  source_dataset: "recommended_works" | "completed_works";
  amount_type: "Recommended Amount" | "Final Amount";
  target_work?: RealWorkRecord | null;
  target_amount: number;
  target_amount_lakh: number;
  comparable_project_count: number;
  peer_median_amount: number;
  peer_median_lakh: number;
  peer_average_amount: number;
  peer_average_lakh: number;
  peer_min_amount: number;
  peer_min_lakh: number;
  peer_max_amount: number;
  peer_max_lakh: number;
  peer_std_amount: number;
  ratio_to_peer_median: number;
  percentage_difference_from_peer_median: number;
  average_peer_similarity: number;
  matching_confidence: number;
  benchmark_insight: string;
  comparable_works: RealComparableWorkPeer[];
}

export interface RealWorksListResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  dataset: string;
  data: RealWorkRecord[];
}

export interface RealMPLADSStatsResponse {
  total_recommended_works: number;
  total_completed_works: number;
  total_expenditure_records: number;
  total_mp_summary_records: number;
  total_recommended_amount_lakh: number;
  total_completed_final_amount_lakh: number;
  total_disbursed_expenditure_lakh: number;
  categories_distribution: Record<string, number>;
  top_states_by_works: Record<string, number>;
  data_source_integrity_note: string;
}

// -------------------------------------------------------------
// AUTHENTICATION & RBAC TYPES
// -------------------------------------------------------------
export type UserRole = "MOSPI_OFFICER" | "DISTRICT_AUTHORITY" | "ADMIN";

export interface User {
  user_id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  assigned_district?: string | null;
  assigned_state?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserCreate {
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  assigned_district?: string | null;
  assigned_state?: string | null;
  password: string;
  is_active?: boolean;
}

export interface UserUpdate {
  full_name?: string;
  email?: string;
  role?: UserRole;
  assigned_district?: string | null;
  assigned_state?: string | null;
  is_active?: boolean;
  password?: string;
}

// -------------------------------------------------------------
// INVESTIGATION / CASE MANAGEMENT TYPES
// -------------------------------------------------------------
export type InvestigationStatus =
  | "NOT_STARTED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "EVIDENCE_COLLECTION"
  | "UNDER_REVIEW"
  | "ACTION_REQUIRED"
  | "ESCALATED"
  | "RESOLVED"
  | "CLOSED";

export type CaseInvestigationType =
  | "FINANCIAL_VERIFICATION"
  | "PHYSICAL_VERIFICATION"
  | "TECHNICAL_VERIFICATION"
  | "DOCUMENT_VERIFICATION"
  | "IMPLEMENTATION_REVIEW"
  | "GENERAL_REVIEW";

export type AssignedRole =
  | "District Authority"
  | "Technical / Engineering Officer"
  | "Implementing Agency Officer"
  | "State Nodal Officer"
  | "Third-Party Monitoring Agency";

export interface InvestigationAuditEntry {
  entry_id: string;
  timestamp: string;
  user_name: string;
  user_role: string;
  action: string;
  previous_status?: string | null;
  new_status?: string | null;
  comment: string;
}

export interface InvestigationFinding {
  finding_id: string;
  timestamp: string;
  author_name: string;
  author_role: string;
  finding_text: string;
  evidence_notes?: string | null;
}

export interface InvestigationRecord {
  investigation_id: string;
  project_id: string;
  work_name: string;
  district: string;
  state: string;
  sanctioned_amount_lakh: number;
  risk_score: number;
  risk_level: string;
  status: InvestigationStatus;
  investigation_type: CaseInvestigationType;
  progress_percentage: number;
  created_by: string;
  assigned_to?: string | null;
  assigned_role?: string | null;
  reason: string;
  findings: InvestigationFinding[];
  audit_trail: InvestigationAuditEntry[];
  final_recommendation?: string | null;
  escalation_status?: string | null;
  created_at: string;
  updated_at: string;
  due_date?: string | null;
  is_demo: boolean;
}

export interface CreateInvestigationRequest {
  project_id: string;
  investigation_type: CaseInvestigationType;
  reason: string;
  assigned_to?: string;
  assigned_role?: AssignedRole;
  due_date?: string;
}


