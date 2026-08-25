from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.anomaly_engine.models import AnomalyTypeEnum, SeverityEnum


class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskCategoryEnum(str, Enum):
    FINANCIAL = "FINANCIAL"
    PROGRESS = "PROGRESS"
    PAYMENT = "PAYMENT"
    VENDOR = "VENDOR"
    AGENCY = "AGENCY"
    DUPLICATE_GEO = "DUPLICATE_GEO"
    COMPLIANCE = "COMPLIANCE"
    ML_STATISTICAL = "ML_STATISTICAL"


# Mapping from 31 anomaly types to the risk categories
ANOMALY_CATEGORY_MAPPING: Dict[AnomalyTypeEnum, RiskCategoryEnum] = {
    # 1. Financial Category
    AnomalyTypeEnum.EXPENDITURE_EXCEEDS_SANCTION: RiskCategoryEnum.FINANCIAL,
    AnomalyTypeEnum.COST_OVERRUN: RiskCategoryEnum.FINANCIAL,
    AnomalyTypeEnum.ABNORMALLY_HIGH_UTILIZATION: RiskCategoryEnum.FINANCIAL,
    AnomalyTypeEnum.ABNORMALLY_LOW_UTILIZATION: RiskCategoryEnum.FINANCIAL,
    AnomalyTypeEnum.PROGRESS_FINANCIAL_MISMATCH: RiskCategoryEnum.FINANCIAL,
    AnomalyTypeEnum.UNUSUAL_EXPENDITURE_PATTERN: RiskCategoryEnum.FINANCIAL,

    # 2. Progress Category
    AnomalyTypeEnum.PROJECT_DELAY: RiskCategoryEnum.PROGRESS,
    AnomalyTypeEnum.SLOW_PROGRESS: RiskCategoryEnum.PROGRESS,
    AnomalyTypeEnum.NO_RECENT_PROGRESS_UPDATE: RiskCategoryEnum.PROGRESS,
    AnomalyTypeEnum.SUDDEN_PROGRESS_JUMP: RiskCategoryEnum.PROGRESS,
    AnomalyTypeEnum.MILESTONE_LAG: RiskCategoryEnum.PROGRESS,
    AnomalyTypeEnum.COMPLETION_RISK: RiskCategoryEnum.PROGRESS,

    # 3. Payment Category
    AnomalyTypeEnum.LARGE_PAYMENT: RiskCategoryEnum.PAYMENT,
    AnomalyTypeEnum.RAPID_MULTIPLE_PAYMENTS: RiskCategoryEnum.PAYMENT,
    AnomalyTypeEnum.REPEATED_PAYMENT_AMOUNT: RiskCategoryEnum.PAYMENT,
    AnomalyTypeEnum.PAYMENT_BEFORE_MILESTONE: RiskCategoryEnum.PAYMENT,
    AnomalyTypeEnum.PAYMENT_LOW_PROGRESS: RiskCategoryEnum.PAYMENT,
    AnomalyTypeEnum.DEADLINE_PAYMENT_CONCENTRATION: RiskCategoryEnum.PAYMENT,

    # 4. Vendor Category
    AnomalyTypeEnum.VENDOR_HIGH_DELAY_RATE: RiskCategoryEnum.VENDOR,
    AnomalyTypeEnum.VENDOR_HIGH_COST_ANOMALY_RATE: RiskCategoryEnum.VENDOR,
    AnomalyTypeEnum.VENDOR_HIGH_PAYMENT_ANOMALY_RATE: RiskCategoryEnum.VENDOR,
    AnomalyTypeEnum.VENDOR_PROJECT_CONCENTRATION: RiskCategoryEnum.VENDOR,

    # 5. Agency Category
    AnomalyTypeEnum.AGENCY_HIGH_ANOMALY_RATE: RiskCategoryEnum.AGENCY,
    AnomalyTypeEnum.AGENCY_REPEATED_ISSUES: RiskCategoryEnum.AGENCY,

    # 6. Duplicate & Geo Category
    AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK: RiskCategoryEnum.DUPLICATE_GEO,

    # 7. Compliance Category
    AnomalyTypeEnum.MISSING_SANCTION_DOCUMENT: RiskCategoryEnum.COMPLIANCE,
    AnomalyTypeEnum.MISSING_PROGRESS_DOCUMENT: RiskCategoryEnum.COMPLIANCE,
    AnomalyTypeEnum.MISSING_INSPECTION_REPORT: RiskCategoryEnum.COMPLIANCE,
    AnomalyTypeEnum.MISSING_PAYMENT_SUPPORT: RiskCategoryEnum.COMPLIANCE,
    AnomalyTypeEnum.MISSING_COMPLETION_CERTIFICATE: RiskCategoryEnum.COMPLIANCE,
    AnomalyTypeEnum.COMPLIANCE_DOCUMENT_GAP: RiskCategoryEnum.COMPLIANCE,
}


# Relative Priority Weights for all 31 Anomaly Rules (used for normalized intra-category weighting)
RULE_PRIORITY_WEIGHTS: Dict[AnomalyTypeEnum, int] = {
    # 1. Financial Category
    AnomalyTypeEnum.EXPENDITURE_EXCEEDS_SANCTION: 8,
    AnomalyTypeEnum.COST_OVERRUN: 8,
    AnomalyTypeEnum.ABNORMALLY_HIGH_UTILIZATION: 5,
    AnomalyTypeEnum.ABNORMALLY_LOW_UTILIZATION: 3,
    AnomalyTypeEnum.PROGRESS_FINANCIAL_MISMATCH: 7,
    AnomalyTypeEnum.UNUSUAL_EXPENDITURE_PATTERN: 4,

    # 2. Progress & Timeline Category
    AnomalyTypeEnum.PROJECT_DELAY: 8,
    AnomalyTypeEnum.SLOW_PROGRESS: 6,
    AnomalyTypeEnum.NO_RECENT_PROGRESS_UPDATE: 3,
    AnomalyTypeEnum.SUDDEN_PROGRESS_JUMP: 5,
    AnomalyTypeEnum.MILESTONE_LAG: 6,
    AnomalyTypeEnum.COMPLETION_RISK: 8,

    # 3. Payment Irregularity Category
    AnomalyTypeEnum.LARGE_PAYMENT: 5,
    AnomalyTypeEnum.RAPID_MULTIPLE_PAYMENTS: 4,
    AnomalyTypeEnum.REPEATED_PAYMENT_AMOUNT: 5,
    AnomalyTypeEnum.PAYMENT_BEFORE_MILESTONE: 7,
    AnomalyTypeEnum.PAYMENT_LOW_PROGRESS: 7,
    AnomalyTypeEnum.DEADLINE_PAYMENT_CONCENTRATION: 5,

    # 4. Vendor Risk Category
    AnomalyTypeEnum.VENDOR_HIGH_DELAY_RATE: 4,
    AnomalyTypeEnum.VENDOR_HIGH_COST_ANOMALY_RATE: 5,
    AnomalyTypeEnum.VENDOR_HIGH_PAYMENT_ANOMALY_RATE: 5,
    AnomalyTypeEnum.VENDOR_PROJECT_CONCENTRATION: 3,

    # 5. Agency Risk Category
    AnomalyTypeEnum.AGENCY_HIGH_ANOMALY_RATE: 5,
    AnomalyTypeEnum.AGENCY_REPEATED_ISSUES: 6,

    # 6. Duplicate & Geospatial Category
    AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK: 8,

    # 7. Compliance & Evidence Category
    AnomalyTypeEnum.MISSING_SANCTION_DOCUMENT: 4,
    AnomalyTypeEnum.MISSING_PROGRESS_DOCUMENT: 4,
    AnomalyTypeEnum.MISSING_INSPECTION_REPORT: 4,
    AnomalyTypeEnum.MISSING_PAYMENT_SUPPORT: 6,
    AnomalyTypeEnum.MISSING_COMPLETION_CERTIFICATE: 4,
    AnomalyTypeEnum.COMPLIANCE_DOCUMENT_GAP: 6,
}


# Maximum rule priority weight within each deterministic category (for normalization)
CATEGORY_MAX_RULE_WEIGHT: Dict[RiskCategoryEnum, float] = {
    RiskCategoryEnum.FINANCIAL: 8.0,
    RiskCategoryEnum.PROGRESS: 8.0,
    RiskCategoryEnum.PAYMENT: 7.0,
    RiskCategoryEnum.VENDOR: 5.0,
    RiskCategoryEnum.AGENCY: 6.0,
    RiskCategoryEnum.DUPLICATE_GEO: 8.0,
    RiskCategoryEnum.COMPLIANCE: 6.0,
}


class RiskConfig(BaseModel):
    """
    Configurable parameters for risk aggregation, category weighting, and ML integration.
    """
    # Deterministic category weights (Caps)
    weight_financial: float = Field(default=25.0, description="Max points for Financial risk category")
    weight_progress: float = Field(default=20.0, description="Max points for Progress & Timeline risk category")
    weight_payment: float = Field(default=20.0, description="Max points for Payment irregularity risk category")
    weight_vendor: float = Field(default=10.0, description="Max points for Vendor risk category")
    weight_agency: float = Field(default=10.0, description="Max points for Implementing Agency risk category")
    weight_duplicate_geo: float = Field(default=10.0, description="Max points for Duplicate & Geospatial risk category")
    weight_compliance: float = Field(default=5.0, description="Max points for Compliance & Evidence risk category")

    # ML Anomaly Category Weight (Max 5 points)
    weight_ml: float = Field(default=5.0, description="Max contribution points for ML statistical anomaly category")

    # Global Fusion Blend Weights
    rule_weight: float = Field(default=0.80, description="Global deterministic rule weight blend factor")
    ml_weight: float = Field(default=0.20, description="Global ML statistical anomaly weight blend factor")

    # Severity multiplier factors
    severity_critical: float = Field(default=1.0, description="Multiplier for CRITICAL severity anomalies")
    severity_high: float = Field(default=0.75, description="Multiplier for HIGH severity anomalies")
    severity_medium: float = Field(default=0.45, description="Multiplier for MEDIUM severity anomalies")
    severity_low: float = Field(default=0.20, description="Multiplier for LOW severity anomalies")

    # Diminishing returns factors for correlated intra-category signals
    secondary_signal_discount: float = Field(default=0.35, description="Weight for 2nd anomaly in same category")
    tertiary_signal_discount: float = Field(default=0.15, description="Weight for 3rd+ anomaly in same category")

    # Rule Priority Weights Mapping
    rule_priority_weights: Dict[AnomalyTypeEnum, int] = Field(
        default_factory=lambda: dict(RULE_PRIORITY_WEIGHTS),
        description="Relative priority weights (3-8) for all 31 anomaly rules",
    )


class MLRiskSignal(BaseModel):
    """
    Standardized record of ML statistical anomaly contribution.
    """
    score: float = Field(..., ge=0.0, le=100.0, description="Normalized 0-100 ML anomaly score")
    flag: bool = Field(..., description="Binary statistical outlier flag from Isolation Forest")
    contribution: int = Field(..., ge=0, le=15, description="Points contributed by ML to total risk score")
    model_version: str = Field(..., description="Model version identifier")


class RiskFactor(BaseModel):
    """
    Detailed explainability record for each anomaly contributing to the risk score.
    """
    category: RiskCategoryEnum = Field(..., description="Risk category of the signal")
    signal: str = Field(..., description="Anomaly type code or ML signal identifier")
    contribution: int = Field(..., description="Point contribution to the total 0-100 risk score")
    severity: SeverityEnum = Field(..., description="Severity level")
    confidence: float = Field(..., description="Confidence score")
    rule_weight: Optional[int] = Field(default=None, description="Relative priority weight of the rule (3-8)")
    weighted_impact: Optional[float] = Field(
        default=None,
        description="Normalized weighted impact (normalized rule weight * severity * confidence)",
    )


class ProjectRiskProfile(BaseModel):
    """
    Standardized project risk intelligence profile with ML evidence fusion.
    """
    project_id: str = Field(..., description="Unique project identifier")
    risk_score: int = Field(..., ge=0, le=100, description="Aggregate risk score (0-100)")
    risk_level: RiskLevelEnum = Field(..., description="LOW (0-24), MEDIUM (25-49), HIGH (50-74), CRITICAL (75-100)")
    risk_factors: List[RiskFactor] = Field(default_factory=list, description="Sorted list of contributing risk factors")
    ml_signal: Optional[MLRiskSignal] = Field(default=None, description="Supporting ML statistical anomaly signal")
    summary: str = Field(..., description="Concise human-readable explanation of key project risk drivers")
    recommended_action: str = Field(..., description="Actionable governance / audit recommendation")


class RiskListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    count: int
    data: List[ProjectRiskProfile]


class RiskEngineSummary(BaseModel):
    total_projects: int
    average_risk_score: float
    risk_level_counts: Dict[str, int]
    highest_risk_projects: List[Dict[str, Any]]
