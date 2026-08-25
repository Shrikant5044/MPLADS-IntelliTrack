from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RealWorkRecord(BaseModel):
    work_id: int
    work_description: str
    category: str
    mp_name: str
    constituency: str
    state: str
    house: str
    amount: float = Field(..., description="Amount in Rupees (Recommended Amount or Final Amount)")
    amount_lakh: float = Field(..., description="Amount in Lakhs (₹)")
    date: str
    has_images: bool
    ida: str
    dataset_source: str = Field(..., description="'recommended_works' or 'completed_works'")


class RealComparableWorkPeer(BaseModel):
    work_id: int
    work_description: str
    category: str
    state: str
    constituency: str
    mp_name: str
    ida: str
    amount: float = Field(..., description="Peer amount in Rupees")
    amount_lakh: float = Field(..., description="Peer amount in Lakhs (₹)")
    similarity_score: float = Field(..., description="Composite similarity score (0.0 - 1.0)")
    text_similarity: float = Field(..., description="Raw description TF-IDF cosine similarity")
    state_match: bool = Field(..., description="Whether candidate matches target state")
    category_match: bool = Field(..., description="Whether candidate matches target category")
    ida_match: bool = Field(..., description="Whether candidate matches target IDA")
    match_tier: str = Field(..., description="'Same State & District', 'Same State', or 'National Peer'")
    winning_query: Optional[str] = Field(default=None, description="Canonical or raw query that achieved the maximum similarity score")


class RealWorkBenchmarkResult(BaseModel):
    status: str = Field(..., description="'SUCCESS' or 'INSUFFICIENT_PEERS'")
    analysis_type: str = "Comparable Project Analysis / Peer Benchmarking"
    source_dataset: str = Field(..., description="'recommended_works' or 'completed_works'")
    amount_type: str = Field(..., description="'Recommended Amount' or 'Final Amount'")
    target_work: Optional[RealWorkRecord] = None
    target_amount: float
    target_amount_lakh: float
    comparable_project_count: int
    peer_median_amount: float
    peer_median_lakh: float
    peer_average_amount: float
    peer_average_lakh: float
    peer_min_amount: float
    peer_min_lakh: float
    peer_max_amount: float
    peer_max_lakh: float
    peer_std_amount: float
    ratio_to_peer_median: float
    percentage_difference_from_peer_median: float
    average_peer_similarity: float
    matching_confidence: float = Field(..., description="Overall confidence based on peer similarity and count (0.0 - 1.0)")
    benchmark_insight: str
    comparable_works: List[RealComparableWorkPeer] = Field(default_factory=list)


class RealWorksListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    count: int
    dataset: str
    data: List[RealWorkRecord]


class RealMPLADSStatsResponse(BaseModel):
    total_recommended_works: int
    total_completed_works: int
    total_expenditure_records: int
    total_mp_summary_records: int
    total_recommended_amount_lakh: float
    total_completed_final_amount_lakh: float
    total_disbursed_expenditure_lakh: float
    categories_distribution: Dict[str, int]
    top_states_by_works: Dict[str, int]
    data_source_integrity_note: str = "Expenditure dataset contains financial transaction records without foreign Work IDs; no artificial linkages are asserted."
