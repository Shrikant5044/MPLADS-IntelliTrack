from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BenchmarkStatusEnum(str, Enum):
    NORMAL = "NORMAL"
    MODERATE_DEVIATION = "MODERATE_DEVIATION"
    HIGH_DEVIATION = "HIGH_DEVIATION"
    EXTREME_DEVIATION = "EXTREME_DEVIATION"
    LOW_OUTLIER = "LOW_OUTLIER"
    INSUFFICIENT_PEERS = "INSUFFICIENT_PEERS"


class PeerHierarchyTierEnum(str, Enum):
    DISTRICT_CATEGORY = "DISTRICT_CATEGORY"
    STATE_CATEGORY = "STATE_CATEGORY"
    NATIONAL_CATEGORY = "NATIONAL_CATEGORY"
    INSUFFICIENT = "INSUFFICIENT"


class BenchmarkConfig(BaseModel):
    """
    Configurable parameters for comparable project benchmarking.
    All thresholds are analytical reference points and not statutory fraud declarations.
    """
    min_peers: int = Field(
        default=3,
        ge=2,
        description="Minimum number of comparable peer projects required for statistical benchmarking.",
    )
    moderate_ratio_threshold: float = Field(
        default=1.25,
        description="Cost-to-median ratio threshold for MODERATE_DEVIATION (e.g. 1.25x).",
    )
    high_ratio_threshold: float = Field(
        default=1.60,
        description="Cost-to-median ratio threshold for HIGH_DEVIATION (e.g. 1.60x).",
    )
    extreme_ratio_threshold: float = Field(
        default=2.20,
        description="Cost-to-median ratio threshold for EXTRERE_DEVIATION (e.g. 2.20x).",
    )
    low_outlier_ratio_threshold: float = Field(
        default=0.50,
        description="Cost-to-median ratio threshold below which project is flagged as a LOW_OUTLIER (e.g. <0.50x).",
    )
    allow_state_fallback: bool = Field(
        default=True,
        description="If True, expands peer search to state-level category when district peers are fewer than min_peers.",
    )
    allow_national_fallback: bool = Field(
        default=True,
        description="If True, expands peer search to national category baseline when state peers are fewer than min_peers.",
    )


class PeerSummaryStats(BaseModel):
    peer_count: int = Field(..., description="Number of comparable projects in peer cohort")
    peer_tier: PeerHierarchyTierEnum = Field(..., description="Geographic hierarchy tier of resolved peer group")
    peer_mean_cost_lakh: float = Field(..., description="Arithmetic mean estimated cost of peer cohort in Lakhs")
    peer_median_cost_lakh: float = Field(..., description="Median estimated cost of peer cohort in Lakhs")
    peer_std_cost_lakh: float = Field(..., description="Standard deviation of peer cohort cost in Lakhs")
    peer_min_cost_lakh: float = Field(..., description="Minimum estimated cost in peer cohort in Lakhs")
    peer_max_cost_lakh: float = Field(..., description="Maximum estimated cost in peer cohort in Lakhs")
    peer_iqr_lakh: float = Field(..., description="Interquartile range (IQR) of peer costs in Lakhs")


class ProjectBenchmarkResult(BaseModel):
    """
    Standardized benchmarking evaluation result for a single project.
    """
    project_id: str = Field(..., description="Target project identifier")
    work_name: str = Field(..., description="Name / description of the work")
    work_category: str = Field(..., description="Standardized work category")
    district: str = Field(..., description="Project district")
    state: str = Field(..., description="Project state")

    project_estimated_cost_lakh: float = Field(..., description="Target project estimated cost in Lakhs")
    project_sanctioned_amount_lakh: float = Field(..., description="Target project sanctioned amount in Lakhs")
    project_expenditure_lakh: float = Field(..., description="Target project actual expenditure in Lakhs")

    benchmark_status: BenchmarkStatusEnum = Field(
        ...,
        description="Analytical status: NORMAL, MODERATE_DEVIATION, HIGH_DEVIATION, EXTREME_DEVIATION, LOW_OUTLIER, INSUFFICIENT_PEERS",
    )
    peer_hierarchy_tier: PeerHierarchyTierEnum = Field(
        ...,
        description="Geographic scope used for peer selection: DISTRICT_CATEGORY, STATE_CATEGORY, NATIONAL_CATEGORY, INSUFFICIENT",
    )

    peer_count: int = Field(..., description="Number of comparable peer projects used")
    cost_ratio_vs_peer_median: Optional[float] = Field(
        default=None,
        description="Ratio of target project cost relative to peer median cost (e.g. 1.85x)",
    )
    deviation_percentage: Optional[float] = Field(
        default=None,
        description="Percentage deviation from peer median ((cost - median) / median * 100)",
    )
    percentile_position: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Empirical percentile ranking (0-100) of project cost within peer group",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Statistical confidence score based on peer sample size and geographic specificity",
    )

    peer_stats: Optional[PeerSummaryStats] = Field(
        default=None,
        description="Detailed statistical descriptors of the peer cohort",
    )
    sample_peer_project_ids: List[str] = Field(
        default_factory=list,
        description="List of sample project IDs included in the peer cohort (up to 10)",
    )

    explanation: str = Field(
        ...,
        description="Clear, explainable summary of peer comparison and percentile position",
    )
    limitations: str = Field(
        ...,
        description="Methodological limitations and context (e.g. terrain, local material variances)",
    )


class BenchmarkSummary(BaseModel):
    total_projects_evaluated: int
    benchmarkable_projects_count: int
    insufficient_peers_count: int
    status_counts: Dict[str, int]
    tier_counts: Dict[str, int]
    average_cost_ratio: float


class BenchmarkListResponse(BaseModel):
    total: int = Field(..., description="Total records matching filters")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")
    count: int = Field(..., description="Items in current payload")
    summary: BenchmarkSummary = Field(..., description="Statistical summary across all benchmark evaluations")
    data: List[ProjectBenchmarkResult] = Field(..., description="List of project benchmark evaluations")
