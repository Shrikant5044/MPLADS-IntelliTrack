from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SeverityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyTypeEnum(str, Enum):
    # Financial & Cost Rules
    EXPENDITURE_EXCEEDS_SANCTION = "EXPENDITURE_EXCEEDS_SANCTION"
    COST_OVERRUN = "COST_OVERRUN"
    ABNORMALLY_HIGH_UTILIZATION = "ABNORMALLY_HIGH_UTILIZATION"
    ABNORMALLY_LOW_UTILIZATION = "ABNORMALLY_LOW_UTILIZATION"
    PROGRESS_FINANCIAL_MISMATCH = "PROGRESS_FINANCIAL_MISMATCH"
    UNUSUAL_EXPENDITURE_PATTERN = "UNUSUAL_EXPENDITURE_PATTERN"

    # Progress & Timeline Rules
    PROJECT_DELAY = "PROJECT_DELAY"
    SLOW_PROGRESS = "SLOW_PROGRESS"
    NO_RECENT_PROGRESS_UPDATE = "NO_RECENT_PROGRESS_UPDATE"
    SUDDEN_PROGRESS_JUMP = "SUDDEN_PROGRESS_JUMP"
    MILESTONE_LAG = "MILESTONE_LAG"
    COMPLETION_RISK = "COMPLETION_RISK"

    # Payment Rules
    LARGE_PAYMENT = "LARGE_PAYMENT"
    RAPID_MULTIPLE_PAYMENTS = "RAPID_MULTIPLE_PAYMENTS"
    REPEATED_PAYMENT_AMOUNT = "REPEATED_PAYMENT_AMOUNT"
    PAYMENT_BEFORE_MILESTONE = "PAYMENT_BEFORE_MILESTONE"
    PAYMENT_LOW_PROGRESS = "PAYMENT_LOW_PROGRESS"
    DEADLINE_PAYMENT_CONCENTRATION = "DEADLINE_PAYMENT_CONCENTRATION"

    # Vendor & Agency Rules
    VENDOR_HIGH_DELAY_RATE = "VENDOR_HIGH_DELAY_RATE"
    VENDOR_HIGH_COST_ANOMALY_RATE = "VENDOR_HIGH_COST_ANOMALY_RATE"
    VENDOR_HIGH_PAYMENT_ANOMALY_RATE = "VENDOR_HIGH_PAYMENT_ANOMALY_RATE"
    VENDOR_PROJECT_CONCENTRATION = "VENDOR_PROJECT_CONCENTRATION"
    AGENCY_HIGH_ANOMALY_RATE = "AGENCY_HIGH_ANOMALY_RATE"
    AGENCY_REPEATED_ISSUES = "AGENCY_REPEATED_ISSUES"

    # Duplicate Work & Geographic Rules
    POTENTIAL_DUPLICATE_WORK = "POTENTIAL_DUPLICATE_WORK"

    # Compliance & Evidence Rules
    MISSING_SANCTION_DOCUMENT = "MISSING_SANCTION_DOCUMENT"
    MISSING_PROGRESS_DOCUMENT = "MISSING_PROGRESS_DOCUMENT"
    MISSING_INSPECTION_REPORT = "MISSING_INSPECTION_REPORT"
    MISSING_PAYMENT_SUPPORT = "MISSING_PAYMENT_SUPPORT"
    MISSING_COMPLETION_CERTIFICATE = "MISSING_COMPLETION_CERTIFICATE"
    COMPLIANCE_DOCUMENT_GAP = "COMPLIANCE_DOCUMENT_GAP"


class ThresholdConfig(BaseModel):
    """
    Calibrated parameters and thresholds for the MPLADS-IntelliTrack anomaly engine.
    """
    # Reference snapshot date for timeline evaluations
    reference_date_str: str = Field(
        default="2026-08-23",
        description="Reference snapshot date (YYYY-MM-DD) for progress and delay evaluations.",
    )

    # 1. Expenditure exceeds sanctioned amount rule
    expenditure_excess_tolerance_lakh: float = Field(
        default=0.05,
        description="Minimum excess in Lakhs to flag an expenditure over sanctioned amount (buffer for float rounding).",
    )
    expenditure_critical_excess_pct: float = Field(
        default=20.0,
        description="Excess percentage of sanctioned amount considered CRITICAL severity.",
    )
    expenditure_high_excess_pct: float = Field(
        default=10.0,
        description="Excess percentage of sanctioned amount considered HIGH severity.",
    )

    # 2. Cost overrun rule
    cost_overrun_pct_threshold: float = Field(
        default=5.0,
        description="Threshold percentage above estimated cost to trigger cost overrun anomaly (>5% to filter minor variations).",
    )
    cost_overrun_critical_pct: float = Field(
        default=25.0,
        description="Cost overrun percentage considered CRITICAL severity.",
    )
    cost_overrun_high_pct: float = Field(
        default=15.0,
        description="Cost overrun percentage considered HIGH severity.",
    )
    cost_overrun_medium_pct: float = Field(
        default=5.0,
        description="Cost overrun percentage considered MEDIUM severity.",
    )

    # 3. Abnormally high utilization rule
    high_utilization_threshold_pct: float = Field(
        default=90.0,
        description="Fund utilization rate threshold considered high.",
    )
    high_utilization_physical_lag_pct: float = Field(
        default=50.0,
        description="Physical progress percentage below which high utilization is suspicious.",
    )
    over_utilization_ceiling_pct: float = Field(
        default=100.0,
        description="Fund utilization rate exceeding 100% is immediately anomalous.",
    )

    # 4. Abnormally low utilization rule
    low_utilization_threshold_pct: float = Field(
        default=15.0,
        description="Fund utilization rate considered abnormally low.",
    )
    low_utilization_planned_progress_min_pct: float = Field(
        default=50.0,
        description="Minimum planned progress percentage to flag lagging utilization.",
    )

    # 5. Financial vs physical progress mismatch rule
    progress_mismatch_gap_pct: float = Field(
        default=35.0,
        description="Minimum difference between financial % and physical % to flag mismatch.",
    )
    progress_mismatch_critical_gap_pct: float = Field(
        default=50.0,
        description="Progress gap percentage considered CRITICAL severity.",
    )
    progress_mismatch_high_gap_pct: float = Field(
        default=40.0,
        description="Progress gap percentage considered HIGH severity.",
    )

    # 6. Unusual expenditure pattern rule
    single_payment_concentration_pct: float = Field(
        default=60.0,
        description="Percentage of total project payments in a single transaction considered anomalous.",
    )
    early_stage_concentration_pct: float = Field(
        default=50.0,
        description="Single mobilization/foundation payment percentage triggering elevated severity.",
    )

    # 7. Project Delay rule
    project_delay_critical_days: int = Field(
        default=90,
        description="Days past expected completion date considered CRITICAL severity.",
    )
    project_delay_high_days: int = Field(
        default=45,
        description="Days past expected completion date considered HIGH severity.",
    )
    project_delay_medium_days: int = Field(
        default=15,
        description="Days past expected completion date considered MEDIUM severity.",
    )

    # 8. Slow Progress rule
    slow_progress_threshold_pct: float = Field(
        default=30.0,
        description="Minimum difference between planned % and physical % to flag slow progress.",
    )
    slow_progress_critical_pct: float = Field(
        default=45.0,
        description="Physical progress lag percentage considered CRITICAL severity.",
    )
    slow_progress_high_pct: float = Field(
        default=35.0,
        description="Physical progress lag percentage considered HIGH severity.",
    )

    # 9. No Recent Progress Update rule
    no_update_threshold_days: int = Field(
        default=90,
        description="Number of days without a progress update to flag stagnation (quarterly dormancy).",
    )
    no_update_critical_days: int = Field(
        default=120,
        description="Number of days without a progress update considered HIGH severity.",
    )

    # 10. Sudden Progress Jump rule
    sudden_progress_jump_threshold_pct: float = Field(
        default=35.0,
        description="Increase in reported physical progress between consecutive updates to flag sudden jump.",
    )
    sudden_progress_jump_critical_pct: float = Field(
        default=45.0,
        description="Progress jump percentage considered CRITICAL severity.",
    )

    # 11. Milestone Lag rule
    milestone_lag_threshold_pct: float = Field(
        default=30.0,
        description="Milestone progress shortfall percentage considered anomalous.",
    )
    milestone_lag_critical_pct: float = Field(
        default=45.0,
        description="Milestone progress shortfall considered CRITICAL severity.",
    )

    # 12. Completion Risk rule
    completion_risk_window_days: int = Field(
        default=45,
        description="Days remaining to deadline to evaluate completion risk.",
    )
    completion_risk_progress_threshold_pct: float = Field(
        default=40.0,
        description="Maximum physical progress percentage to flag as completion risk when near deadline.",
    )

    # 13. Large Payment rule
    large_payment_share_threshold_pct: float = Field(
        default=60.0,
        description="Share of total project payments in a single transaction to flag as large payment.",
    )
    large_payment_amount_lakh: float = Field(
        default=25.0,
        description="Absolute payment amount in Lakhs considered exceptionally large.",
    )

    # 14. Rapid Multiple Payments rule
    rapid_payment_window_days: int = Field(
        default=5,
        description="Maximum days between consecutive payments to flag rapid disbursement.",
    )
    rapid_payment_min_count: int = Field(
        default=3,
        description="Minimum number of payments in rapid window to trigger anomaly.",
    )

    # 15. Repeated Payment Amount rule
    repeated_amount_min_count: int = Field(
        default=2,
        description="Minimum identical payment amounts for the same project to flag as repeated.",
    )
    repeated_amount_min_value_lakh: float = Field(
        default=5.0,
        description="Minimum transaction value in Lakhs to check for duplicate amounts (filters trivial small retainers).",
    )

    # 16. Payment Before Milestone rule
    payment_before_milestone_physical_threshold_pct: float = Field(
        default=25.0,
        description="Physical progress threshold below which advanced stage payments (Final/Finishing) are flagged.",
    )

    # 17. Payment Low Progress rule
    payment_low_progress_paid_pct: float = Field(
        default=40.0,
        description="Cumulative payment percentage of sanctioned funds to check against low physical progress.",
    )
    payment_low_progress_physical_pct: float = Field(
        default=15.0,
        description="Maximum physical progress percentage to flag when significant payments are disbursed.",
    )

    # 18. Deadline Payment Concentration rule
    deadline_payment_window_days: int = Field(
        default=20,
        description="Window in days relative to completion deadline to check payment concentration.",
    )
    deadline_payment_share_threshold_pct: float = Field(
        default=50.0,
        description="Share of total project payments within deadline window on ONGOING projects.",
    )

    # 19. Vendor High Delay Rate rule
    vendor_min_projects: int = Field(
        default=4,
        description="Minimum total projects handled by a vendor to evaluate historical delay rate.",
    )
    vendor_high_delay_rate_threshold: float = Field(
        default=0.35,
        description="Proportion of delayed projects for a vendor considered anomalous.",
    )

    # 20. Vendor High Cost Anomaly Rate rule
    vendor_high_cost_anomaly_threshold: float = Field(
        default=0.30,
        description="Proportion of cost overrun projects for a vendor considered anomalous.",
    )

    # 21. Vendor High Payment Anomaly Rate rule
    vendor_high_payment_anomaly_threshold: float = Field(
        default=0.35,
        description="Proportion of projects with payment irregularities for a vendor considered anomalous.",
    )

    # 22. Vendor Project Concentration rule
    vendor_district_concentration_share: float = Field(
        default=0.35,
        description="Share of district projects awarded to a single vendor considered high concentration.",
    )
    vendor_max_projects_overall: int = Field(
        default=12,
        description="Total project count threshold for a single vendor across the dataset.",
    )

    # 23. Agency High Anomaly Rate rule
    agency_min_projects: int = Field(
        default=8,
        description="Minimum total projects managed by an agency to evaluate anomaly rate.",
    )
    agency_high_anomaly_rate_threshold: float = Field(
        default=0.22,
        description="Proportion of anomalous/delayed projects under an agency considered high.",
    )

    # 24. Agency Repeated Issues rule
    agency_repeated_issue_min_delayed: int = Field(
        default=2,
        description="Minimum number of delayed projects for an agency to evaluate recurring issues.",
    )
    agency_repeated_issue_min_overrun: int = Field(
        default=2,
        description="Minimum number of cost overrun projects for an agency to evaluate recurring issues.",
    )

    # 25. Potential Duplicate Work rule
    duplicate_max_distance_km: float = Field(
        default=3.0,
        description="Maximum geographical distance in kilometers to evaluate potential duplicate work.",
    )
    duplicate_min_name_similarity: float = Field(
        default=0.50,
        description="Minimum text similarity ratio between project names.",
    )
    duplicate_min_composite_similarity: float = Field(
        default=0.65,
        description="Composite similarity threshold to flag POTENTIAL_DUPLICATE_WORK.",
    )
    duplicate_critical_composite_similarity: float = Field(
        default=0.85,
        description="Composite similarity threshold considered CRITICAL severity.",
    )
    duplicate_high_composite_similarity: float = Field(
        default=0.75,
        description="Composite similarity threshold considered HIGH severity.",
    )


class AnomalyResult(BaseModel):
    """
    Standardized anomaly output structure for all detection rules.
    """
    project_id: str = Field(..., description="Unique identifier of the project")
    anomaly_type: AnomalyTypeEnum = Field(..., description="Type of detected anomaly")
    severity: SeverityEnum = Field(..., description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Numerical & categorical evidence supporting anomaly")
    explanation: str = Field(..., description="Human-readable explanation of why this anomaly was triggered")


class AnomalySummary(BaseModel):
    total_projects_evaluated: int
    total_anomalies_detected: int
    anomalous_projects_count: int
    anomalies_by_type: Dict[str, int]
    anomalies_by_severity: Dict[str, int]
