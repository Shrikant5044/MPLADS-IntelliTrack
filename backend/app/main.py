import sys
import os

# Ensure both project root (for ml) and backend (for app) are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, ".."))
_root_dir = os.path.abspath(os.path.join(_backend_dir, ".."))

for _p in [_root_dir, _backend_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.analytics_engine import (
    AuditQueueItem,
    AuditQueueResponse,
    AuditUrgencyEnum,
    BenchmarkListResponse,
    BenchmarkStatusEnum,
    DistrictAnalyticsResponse,
    DistrictRiskProfile,
    ForecastListResponse,
    GeospatialQualityMetrics,
    InvestigationTypeEnum,
    PeerHierarchyTierEnum,
    ProjectBenchmarkResult,
    ProjectForecastResult,
    TrajectoryStatusEnum,
)
from app.anomaly_engine import (
    AnomalyResult,
    AnomalySummary,
    AnomalyTypeEnum,
    SeverityEnum,
)
from app.cache import get_cache
from app.config import settings
from app.risk_engine import (
    ProjectRiskProfile,
    RiskEngineSummary,
    RiskLevelEnum,
)
from ml.predict import (
    MLAnomalySummary,
    ProjectMLPrediction,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager that warms and precomputes all intelligence caches
    upon server startup for sub-millisecond API responses.
    """
    get_cache()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for MPLADS-IntelliTrack (SIH PS 26102 Prototype)",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for FileNotFoundError
@app.exception_handler(FileNotFoundError)
async def file_not_found_exception_handler(request, exc: FileNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


# Health check response model
class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    service: str = Field(..., example="MPLADS-IntelliTrack API")
    version: str = Field(..., example="0.1.0")


# Projects response model
class ProjectsResponse(BaseModel):
    total: int = Field(..., description="Total number of project records available in dataset")
    limit: int = Field(..., description="Number of records requested/returned in this page")
    offset: int = Field(..., description="Starting record offset")
    count: int = Field(..., description="Number of records in current payload")
    data: List[Dict[str, Any]] = Field(..., description="List of project records")


# Anomalies list response model
class AnomaliesListResponse(BaseModel):
    total: int = Field(..., description="Total number of detected anomalies matching filters")
    limit: int = Field(..., description="Number of records requested/returned")
    offset: int = Field(..., description="Starting record offset")
    count: int = Field(..., description="Number of records in current payload")
    summary: AnomalySummary = Field(..., description="Statistical summary of anomalies")
    data: List[AnomalyResult] = Field(..., description="List of detected anomaly records")


# Single project anomalies response model
class ProjectAnomaliesResponse(BaseModel):
    project_id: str = Field(..., description="Project identifier")
    total_anomalies: int = Field(..., description="Total anomalies detected for this project")
    anomalies: List[AnomalyResult] = Field(..., description="List of detected anomalies for this project")


# Risk profiles list response model
class RiskProfilesResponse(BaseModel):
    total: int = Field(..., description="Total number of projects matching risk filters")
    limit: int = Field(..., description="Number of records requested/returned")
    offset: int = Field(..., description="Starting record offset")
    count: int = Field(..., description="Number of records in current payload")
    summary: RiskEngineSummary = Field(..., description="Statistical summary of project risk distributions")
    data: List[ProjectRiskProfile] = Field(..., description="Ranked list of project risk profiles")


# ML anomalies list response model
class MLAnomaliesResponse(BaseModel):
    total: int = Field(..., description="Total number of projects evaluated by ML")
    limit: int = Field(..., description="Number of records requested/returned")
    offset: int = Field(..., description="Starting record offset")
    count: int = Field(..., description="Number of records in current payload")
    summary: MLAnomalySummary = Field(..., description="Statistical summary of ML anomaly scores")
    data: List[ProjectMLPrediction] = Field(..., description="Ranked list of ML anomaly predictions")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Service health check endpoint.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@app.get(
    "/api/projects",
    response_model=ProjectsResponse,
    tags=["Projects"],
    summary="Get MPLADS projects list",
)
def get_projects(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Limit the number of project records returned (default: 50, max: 500)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination (default: 0)",
    ),
):
    """
    Retrieve project records from cached MPLADS projects dataset.
    """
    cache = get_cache()
    total_records = len(cache.projects_records)
    paginated_records = cache.projects_records[offset : offset + limit]

    return {
        "total": total_records,
        "limit": limit,
        "offset": offset,
        "count": len(paginated_records),
        "data": paginated_records,
    }


@app.get(
    "/api/anomalies",
    response_model=AnomaliesListResponse,
    tags=["Anomalies"],
    summary="Get detected anomalies across all projects",
)
def get_anomalies(
    severity: Optional[SeverityEnum] = Query(
        default=None,
        description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)",
    ),
    anomaly_type: Optional[AnomalyTypeEnum] = Query(
        default=None,
        description="Filter by anomaly type",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=2500,
        description="Maximum number of anomalies to return (default: 100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination (default: 0)",
    ),
):
    """
    Returns detected anomalies across all projects with fast in-memory filtering and pagination.
    """
    cache = get_cache()
    filtered_anomalies = cache.all_anomalies

    if severity:
        filtered_anomalies = [a for a in filtered_anomalies if a.severity == severity]
    if anomaly_type:
        filtered_anomalies = [a for a in filtered_anomalies if a.anomaly_type == anomaly_type]

    total_matching = len(filtered_anomalies)
    paginated_anomalies = filtered_anomalies[offset : offset + limit]

    return {
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "count": len(paginated_anomalies),
        "summary": cache.anomaly_summary,
        "data": paginated_anomalies,
    }


@app.get(
    "/api/anomalies/{project_id}",
    response_model=ProjectAnomaliesResponse,
    tags=["Anomalies"],
    summary="Get detected anomalies for a single project",
)
def get_project_anomalies(project_id: str):
    """
    Returns detected anomalies for a specific project by project_id in O(1) time.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    project_anomalies = cache.anomalies_by_project.get(project_id, [])

    return {
        "project_id": project_id,
        "total_anomalies": len(project_anomalies),
        "anomalies": project_anomalies,
    }


@app.get(
    "/api/risk",
    response_model=RiskProfilesResponse,
    tags=["Risk"],
    summary="Get project risk scores and profiles (fusing rule-based and ML evidence)",
)
def get_risk_profiles(
    risk_level: Optional[RiskLevelEnum] = Query(
        default=None,
        description="Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Limit the number of risk profiles returned (default: 50, max: 500)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination (default: 0)",
    ),
):
    """
    Returns precomputed risk profiles fusing 31 deterministic anomaly rules and supporting unsupervised ML evidence.
    """
    cache = get_cache()
    filtered_profiles = cache.risk_profiles

    if risk_level:
        filtered_profiles = [p for p in filtered_profiles if p.risk_level == risk_level]

    total_matching = len(filtered_profiles)
    paginated_profiles = filtered_profiles[offset : offset + limit]

    return {
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "count": len(paginated_profiles),
        "summary": cache.risk_summary,
        "data": paginated_profiles,
    }


@app.get(
    "/api/risk/{project_id}",
    response_model=ProjectRiskProfile,
    tags=["Risk"],
    summary="Get complete fused risk intelligence profile for a single project",
)
def get_project_risk(project_id: str):
    """
    Retrieves the precomputed complete risk profile for a single project by project_id in O(1) time.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    profile = cache.risk_by_project.get(project_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk profile could not be retrieved for project '{project_id}'.",
        )

    return profile


@app.get(
    "/api/ml/anomalies",
    response_model=MLAnomaliesResponse,
    tags=["Machine Learning"],
    summary="Get unsupervised ML anomaly detection scores (Isolation Forest)",
)
def get_ml_anomalies(
    anomalous_only: bool = Query(
        default=False,
        description="If True, returns only statistical outliers flagged by the Isolation Forest model",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Limit the number of ML predictions returned (default: 50, max: 500)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination (default: 0)",
    ),
):
    """
    Returns precomputed unsupervised Isolation Forest anomaly predictions across all projects.
    """
    cache = get_cache()
    filtered_preds = cache.ml_predictions

    if anomalous_only:
        filtered_preds = [p for p in filtered_preds if p.ml_anomaly_flag]

    total_matching = len(filtered_preds)
    paginated_preds = filtered_preds[offset : offset + limit]

    return {
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "count": len(paginated_preds),
        "summary": cache.ml_summary,
        "data": paginated_preds,
    }


@app.get(
    "/api/ml/anomalies/{project_id}",
    response_model=ProjectMLPrediction,
    tags=["Machine Learning"],
    summary="Get unsupervised ML anomaly prediction for a single project",
)
def get_project_ml_anomaly(project_id: str):
    """
    Retrieves the precomputed ML anomaly prediction for a single project by project_id in O(1) time.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    pred = cache.ml_by_project.get(project_id)
    if not pred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ML prediction could not be computed for project '{project_id}'.",
        )

    return pred


@app.get(
    "/api/analytics/benchmark",
    response_model=BenchmarkListResponse,
    tags=["Analytics"],
    summary="Get comparable project benchmarking evaluations across all projects",
)
def get_benchmarks(
    status_filter: Optional[BenchmarkStatusEnum] = Query(
        default=None,
        alias="status",
        description="Filter by benchmark status (NORMAL, MODERATE_DEVIATION, HIGH_DEVIATION, EXTREME_DEVIATION, LOW_OUTLIER, INSUFFICIENT_PEERS)",
    ),
    tier_filter: Optional[PeerHierarchyTierEnum] = Query(
        default=None,
        alias="tier",
        description="Filter by resolved peer hierarchy tier (DISTRICT_CATEGORY, STATE_CATEGORY, NATIONAL_CATEGORY, INSUFFICIENT)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Limit the number of benchmark records returned (default: 50, max: 500)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination (default: 0)",
    ),
):
    """
    Returns precomputed statistical benchmark evaluations comparing each project against peer cohorts.
    """
    cache = get_cache()
    filtered = cache.benchmark_results

    if status_filter:
        filtered = [b for b in filtered if b.benchmark_status == status_filter]
    if tier_filter:
        filtered = [b for b in filtered if b.peer_hierarchy_tier == tier_filter]

    total_matching = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "count": len(paginated),
        "summary": cache.benchmark_summary,
        "data": paginated,
    }


@app.get(
    "/api/analytics/benchmark/{project_id}",
    response_model=ProjectBenchmarkResult,
    tags=["Analytics"],
    summary="Get comparable peer benchmark evaluation for a single project",
)
def get_project_benchmark(project_id: str):
    """
    Retrieves the comparable benchmark evaluation for a specific project by project_id in O(1) time.
    Returns 404 if project_id is unknown.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    result = cache.benchmark_by_project.get(project_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark evaluation could not be retrieved for project '{project_id}'.",
        )

    return result


@app.get(
    "/api/analytics/forecast",
    response_model=ForecastListResponse,
    tags=["Analytics"],
    summary="Get early-warning progress trajectory and cost forecasts across all projects",
)
def get_forecasts(
    status_filter: Optional[TrajectoryStatusEnum] = Query(
        default=None,
        alias="status",
        description="Filter by trajectory status (COMPLETED, ON_TRACK, WATCH, LIKELY_DELAY, SEVERE_DELAY_RISK, INSUFFICIENT_HISTORY)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Limit the number of forecast records returned (default: 50, max: 500)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination (default: 0)",
    ),
):
    """
    Returns precomputed empirical progress trajectory and cost forecasts across all projects.
    """
    cache = get_cache()
    filtered = cache.forecast_results

    if status_filter:
        filtered = [f for f in filtered if f.trajectory_status == status_filter]

    total_matching = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "count": len(paginated),
        "summary": cache.forecast_summary,
        "data": paginated,
    }


@app.get(
    "/api/analytics/forecast/{project_id}",
    response_model=ProjectForecastResult,
    tags=["Analytics"],
    summary="Get empirical early-warning progress trajectory and cost forecast for a single project",
)
def get_project_forecast(project_id: str):
    """
    Retrieves the empirical progress trajectory and cost forecast for a specific project by project_id in O(1) time.
    Returns 404 if project_id is unknown.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    result = cache.forecast_by_project.get(project_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast evaluation could not be retrieved for project '{project_id}'.",
        )

    return result


@app.get(
    "/api/analytics/audit-queue",
    response_model=AuditQueueResponse,
    tags=["Analytics"],
    summary="Get prioritized, decision-support audit queue for district and state inspection teams",
)
def get_audit_queue(
    risk_level: Optional[RiskLevelEnum] = Query(
        default=None,
        description="Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)",
    ),
    investigation_type: Optional[InvestigationTypeEnum] = Query(
        default=None,
        description="Filter by recommended investigation type (e.g. PHYSICAL_INSPECTION, FINANCIAL_AUDIT, PAYMENT_VERIFICATION, COMPLIANCE_REVIEW, DUPLICATE_GEO_VERIFICATION, VENDOR_REVIEW, AGENCY_REVIEW)",
    ),
    urgency: Optional[AuditUrgencyEnum] = Query(
        default=None,
        description="Filter by operational urgency (CRITICAL_URGENCY, HIGH_URGENCY, MEDIUM_URGENCY, ROUTINE)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Limit the number of audit queue records returned (default: 50, max: 500)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination (default: 0)",
    ),
):
    """
    Returns precomputed prioritized decision-support audit queue ranked by compounded multi-signal risk and financial exposure.
    """
    cache = get_cache()
    filtered = cache.audit_queue_items

    if risk_level:
        filtered = [item for item in filtered if item.risk_level == risk_level.value]
    if investigation_type:
        filtered = [item for item in filtered if investigation_type in item.recommended_investigation_types]
    if urgency:
        filtered = [item for item in filtered if item.urgency == urgency]

    total_matching = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "count": len(paginated),
        "summary": cache.audit_queue_summary,
        "data": paginated,
    }


@app.get(
    "/api/analytics/districts",
    response_model=DistrictAnalyticsResponse,
    tags=["Analytics"],
    summary="Get macro-level regional risk and performance analytics across all districts",
)
def get_district_analytics():
    """
    Returns precomputed district-level risk aggregations, market concentration shares, and statutory anomaly density.
    """
    cache = get_cache()
    return {
        "total": len(cache.district_profiles),
        "summary": cache.district_summary,
        "data": cache.district_profiles,
    }


@app.get(
    "/api/analytics/geospatial/quality",
    response_model=GeospatialQualityMetrics,
    tags=["Analytics", "Geospatial"],
    summary="Get geospatial data quality and coordinate validation metrics",
)
def get_geospatial_quality():
    """
    Returns portfolio-wide geospatial accuracy metrics, boundary validation stats, and territorial integrity counts.
    """
    cache = get_cache()
    if not cache.geospatial_quality:
        from app.analytics_engine.geospatial import get_geospatial_quality_metrics
        return get_geospatial_quality_metrics(cache.datasets.get("projects"))
    return cache.geospatial_quality


@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint with service info and links.
    """
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "projects": "/api/projects",
        "anomalies": "/api/anomalies",
        "risk": "/api/risk",
        "ml": "/api/ml/anomalies",
        "benchmarking": "/api/analytics/benchmark",
        "forecasting": "/api/analytics/forecast",
        "audit_queue": "/api/analytics/audit-queue",
        "districts": "/api/analytics/districts",
        "geospatial_quality": "/api/analytics/geospatial/quality",
    }
