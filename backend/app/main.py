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
from fastapi import Depends, FastAPI, HTTPException, Query, status
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
from app.real_mplads import (
    RealMPLADSLoader,
    RealMPLADSStatsResponse,
    RealPeerBenchmarkEngine,
    RealWorkBenchmarkResult,
    RealWorksListResponse,
    get_real_benchmark_engine,
    get_real_data_loader,
    get_real_search_index,
)
from app.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserRole,
    UserUpdate,
    check_district_access,
    create_access_token,
    get_current_user,
    get_optional_current_user,
    get_user_store,
    require_role,
    verify_password,
)
from app.investigation import (
    AddFindingRequest,
    AssignInvestigationRequest,
    CreateInvestigationRequest,
    EscalateInvestigationRequest,
    InvestigationRecord,
    InvestigationStatus,
    InvestigationType,
    ResolveInvestigationRequest,
    UpdateProgressRequest,
    UpdateStatusRequest,
    get_investigation_store,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager that warms and precomputes all intelligence caches
    upon server startup for sub-millisecond API responses.
    """
    get_cache()
    get_real_data_loader()
    get_real_search_index()
    get_user_store()
    get_investigation_store()
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


# =============================================================
# AUTHENTICATION & RBAC ENDPOINTS
# =============================================================
@app.post(
    "/api/auth/login",
    response_model=TokenResponse,
    tags=["Authentication"],
    summary="Authenticate officer credentials and issue standard HS256 JWT access token",
)
def login(req: LoginRequest):
    """
    Authenticates username and password against PBKDF2 hashed credentials.
    Returns standard RFC 7519 HS256 JWT with role and authorized district boundaries.
    """
    store = get_user_store()
    user = store.get_by_username(req.username)
    if not user or not verify_password(req.password, user.hashed_password, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This officer account is deactivated. Contact platform administrator.",
        )

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            assigned_district=user.assigned_district,
            assigned_state=user.assigned_state,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    }


@app.get(
    "/api/auth/me",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Get current authenticated officer profile and statutory scope",
)
def get_current_officer(current_user: UserResponse = Depends(get_current_user)):
    """
    Returns the authenticated user details, assigned role, and territorial scope.
    """
    return current_user


@app.post(
    "/api/auth/logout",
    tags=["Authentication"],
    summary="Log out and invalidate session",
)
def logout(current_user: UserResponse = Depends(get_current_user)):
    """
    Client session logout acknowledgement.
    """
    return {
        "status": "success",
        "message": f"Officer '{current_user.username}' successfully logged out.",
    }


# =============================================================
# ADMIN USER MANAGEMENT (ADMIN ROLE ONLY)
# =============================================================
@app.get(
    "/api/admin/users",
    response_model=List[UserResponse],
    tags=["Admin"],
    summary="List all registered platform users and statutory assignments (ADMIN only)",
)
def admin_list_users(admin: UserResponse = Depends(require_role(UserRole.ADMIN))):
    """
    List all officer accounts. Restricted strictly to ADMIN role.
    """
    return get_user_store().list_all()


@app.post(
    "/api/admin/users",
    response_model=UserResponse,
    tags=["Admin"],
    summary="Create a new officer account and assign district bounds (ADMIN only)",
)
def admin_create_user(
    payload: UserCreate,
    admin: UserResponse = Depends(require_role(UserRole.ADMIN)),
):
    """
    Creates an officer user with PBKDF2 hashed credentials and role/district assignment.
    """
    try:
        return get_user_store().create_user(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.put(
    "/api/admin/users/{user_id}",
    response_model=UserResponse,
    tags=["Admin"],
    summary="Update officer role, district bounds, or active status (ADMIN only)",
)
def admin_update_user(
    user_id: str,
    payload: UserUpdate,
    admin: UserResponse = Depends(require_role(UserRole.ADMIN)),
):
    """
    Updates an existing officer account.
    """
    updated = get_user_store().update_user(user_id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")
    return updated


@app.delete(
    "/api/admin/users/{user_id}",
    tags=["Admin"],
    summary="Deactivate or remove officer account (ADMIN only)",
)
def admin_delete_user(
    user_id: str,
    admin: UserResponse = Depends(require_role(UserRole.ADMIN)),
):
    """
    Removes or deactivates user account.
    """
    if admin.user_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own admin account.")
    success = get_user_store().delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")
    return {"status": "success", "message": f"User '{user_id}' removed."}


# =============================================================
# CORE INTELLIGENCE ROUTES (WITH BACKEND RBAC SCOPING)
# =============================================================
@app.get(
    "/api/projects",
    response_model=ProjectsResponse,
    tags=["Projects"],
    summary="Get MPLADS projects list (filtered by authorized district if District Authority)",
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
    district: Optional[str] = Query(default=None, description="Filter by district"),
    state: Optional[str] = Query(default=None, description="Filter by state"),
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Retrieve project records from cached MPLADS projects dataset.
    If authenticated as DISTRICT_AUTHORITY, backend strictly filters to the assigned district
    and rejects foreign district queries with HTTP 403 Forbidden.
    """
    cache = get_cache()
    records = cache.projects_records

    # Backend RBAC enforcement for District Authority
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        assigned = current_user.assigned_district
        if district and district.strip().lower() != (assigned or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You are only authorized to access records for district '{assigned}'. Requested: '{district}'.",
            )
        records = [p for p in records if p.get("district", "").strip().lower() == (assigned or "").strip().lower()]
    else:
        if district:
            d_clean = district.strip().lower()
            records = [p for p in records if p.get("district", "").strip().lower() == d_clean]
        if state:
            s_clean = state.strip().lower()
            records = [p for p in records if p.get("state", "").strip().lower() == s_clean]

    total_records = len(records)
    paginated_records = records[offset : offset + limit]

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
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns detected anomalies across all projects with fast in-memory filtering and pagination.
    If authenticated as DISTRICT_AUTHORITY, scoped strictly to assigned district.
    """
    cache = get_cache()
    filtered_anomalies = cache.all_anomalies

    # RBAC Scoping
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        assigned = (current_user.assigned_district or "").strip().lower()
        dist_pids = {
            pid for pid, p in cache.projects_by_id.items()
            if p.get("district", "").strip().lower() == assigned
        }
        filtered_anomalies = [a for a in filtered_anomalies if a.project_id in dist_pids]

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
def get_project_anomalies(
    project_id: str,
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns detected anomalies for a specific project by project_id in O(1) time.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # RBAC Scoping
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        p = cache.projects_by_id.get(project_id, {})
        p_dist = p.get("district", "")
        if p_dist.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Project '{project_id}' belongs to district '{p_dist}', which is outside your assigned district '{current_user.assigned_district}'.",
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
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns precomputed risk profiles fusing 31 deterministic anomaly rules and supporting unsupervised ML evidence.
    If authenticated as DISTRICT_AUTHORITY, scoped strictly to assigned district.
    """
    cache = get_cache()
    filtered_profiles = cache.risk_profiles

    # RBAC Scoping
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        assigned = (current_user.assigned_district or "").strip().lower()
        filtered_profiles = [
            rp for rp in filtered_profiles
            if cache.projects_by_id.get(rp.project_id, {}).get("district", "").strip().lower() == assigned
        ]

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
def get_project_risk(
    project_id: str,
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Retrieves the precomputed complete risk profile for a single project by project_id in O(1) time.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # RBAC Scoping
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        p = cache.projects_by_id.get(project_id, {})
        p_dist = p.get("district", "")
        if p_dist.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Project '{project_id}' belongs to district '{p_dist}', which is outside your assigned district '{current_user.assigned_district}'.",
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
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns precomputed unsupervised Isolation Forest anomaly predictions across all projects.
    """
    cache = get_cache()
    filtered_preds = cache.ml_predictions

    # RBAC Scoping
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        assigned = (current_user.assigned_district or "").strip().lower()
        filtered_preds = [
            m for m in filtered_preds
            if cache.projects_by_id.get(m.project_id, {}).get("district", "").strip().lower() == assigned
        ]

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
def get_project_ml_anomaly(
    project_id: str,
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Retrieves the precomputed ML anomaly prediction for a single project by project_id in O(1) time.
    """
    cache = get_cache()
    if project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    # RBAC Scoping
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        p = cache.projects_by_id.get(project_id, {})
        p_dist = p.get("district", "")
        if p_dist.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Project '{project_id}' belongs to district '{p_dist}', which is outside your assigned district '{current_user.assigned_district}'.",
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
    district: Optional[str] = Query(default=None, description="Filter by district"),
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
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns precomputed prioritized decision-support audit queue ranked by compounded multi-signal risk and financial exposure.
    If authenticated as DISTRICT_AUTHORITY, scoped strictly to assigned district.
    """
    cache = get_cache()
    filtered = cache.audit_queue_items

    # RBAC Scoping
    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        assigned = (current_user.assigned_district or "").strip().lower()
        if district and district.strip().lower() != assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You are only authorized to access records for district '{current_user.assigned_district}'. Requested: '{district}'.",
            )
        filtered = [item for item in filtered if item.district.strip().lower() == assigned]
    else:
        if district:
            d_clean = district.strip().lower()
            filtered = [item for item in filtered if item.district.strip().lower() == d_clean]

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


# =============================================================
# INVESTIGATION & CASE MANAGEMENT ENDPOINTS (NEW LAYER)
# =============================================================
@app.get(
    "/api/investigations",
    response_model=List[InvestigationRecord],
    tags=["Investigations"],
    summary="List all administrative investigations (scoped by role and district)",
)
def list_investigations(
    district: Optional[str] = Query(default=None, description="Filter by district"),
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns list of administrative cases.
    If authenticated as DISTRICT_AUTHORITY, returns cases within assigned district only
    and rejects foreign district queries with HTTP 403 Forbidden.
    """
    store = get_investigation_store()
    target_dist = district

    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        assigned = current_user.assigned_district
        if district and district.strip().lower() != (assigned or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You are only authorized to access investigations in district '{assigned}'.",
            )
        target_dist = assigned

    return store.list_all(district=target_dist)


@app.get(
    "/api/investigations/{investigation_id}",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Get details and full immutable audit trail for a specific investigation",
)
def get_investigation(
    investigation_id: str,
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns the investigation record and its complete chronological audit log.
    """
    store = get_investigation_store()
    inv = store.get_by_id(investigation_id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found.",
        )

    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Investigation belongs to district '{inv.district}', which is outside your assigned district '{current_user.assigned_district}'.",
            )

    return inv


@app.get(
    "/api/investigations/project/{project_id}",
    response_model=Optional[InvestigationRecord],
    tags=["Investigations"],
    summary="Get active investigation record for a specific project ID",
)
def get_project_investigation(
    project_id: str,
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
):
    """
    Returns the active investigation for a given project if one exists.
    """
    store = get_investigation_store()
    inv = store.get_by_project(project_id)
    if not inv:
        return None

    if current_user and current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Project investigation belongs to district '{inv.district}', which is outside your assigned district '{current_user.assigned_district}'.",
            )

    return inv


@app.post(
    "/api/investigations",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Initiate a new administrative investigation for a prioritized project",
)
def create_investigation(
    req: CreateInvestigationRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Creates an investigation record. Authorized for MOSPI_OFFICER or DISTRICT_AUTHORITY (within assigned district).
    """
    cache = get_cache()
    if req.project_id not in cache.project_ids_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{req.project_id}' not found.",
        )

    proj_meta = cache.projects_by_id.get(req.project_id, {})
    proj_district = proj_meta.get("district", "Unknown")

    if current_user.role == UserRole.DISTRICT_AUTHORITY:
        if proj_district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You cannot initiate investigations for project in district '{proj_district}'. Your assigned district is '{current_user.assigned_district}'.",
            )

    risk_prof = cache.risk_by_project.get(req.project_id)
    meta = {
        "work_name": proj_meta.get("work_name", f"Project {req.project_id}"),
        "district": proj_district,
        "state": proj_meta.get("state", "Unknown"),
        "sanctioned_amount_lakh": proj_meta.get("sanctioned_amount_lakh", 0.0),
        "risk_score": risk_prof.risk_score if risk_prof else 50,
        "risk_level": risk_prof.risk_level.value if risk_prof else "MEDIUM",
    }

    try:
        return get_investigation_store().create_investigation(
            req=req,
            user_name=current_user.full_name,
            user_role=current_user.role.value,
            project_meta=meta,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.put(
    "/api/investigations/{investigation_id}/assign",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Assign or reassign investigation to an officer or monitoring body",
)
def assign_investigation(
    investigation_id: str,
    req: AssignInvestigationRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Assigns authority to execute local verification.
    """
    store = get_investigation_store()
    inv = store.get_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")

    if current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Outside assigned district.")

    updated = store.assign(
        investigation_id=investigation_id,
        assigned_to=req.assigned_to,
        assigned_role=req.assigned_role.value,
        user_name=current_user.full_name,
        user_role=current_user.role.value,
        comment=req.comment or "Assigned for verification",
    )
    return updated


@app.put(
    "/api/investigations/{investigation_id}/status",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Transition investigation status and record immutable audit entry",
)
def update_investigation_status(
    investigation_id: str,
    req: UpdateStatusRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Transitions case status (e.g. ASSIGNED -> IN_PROGRESS -> UNDER_REVIEW).
    """
    store = get_investigation_store()
    inv = store.get_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")

    if current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Outside assigned district.")

    updated = store.update_status(
        investigation_id=investigation_id,
        new_status=req.status,
        user_name=current_user.full_name,
        user_role=current_user.role.value,
        comment=req.comment,
    )
    return updated


@app.put(
    "/api/investigations/{investigation_id}/progress",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Update investigation completion progress percentage",
)
def update_investigation_progress(
    investigation_id: str,
    req: UpdateProgressRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Updates completion progress percentage (0-100%).
    """
    store = get_investigation_store()
    inv = store.get_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")

    if current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Outside assigned district.")

    updated = store.update_progress(
        investigation_id=investigation_id,
        progress_percentage=req.progress_percentage,
        user_name=current_user.full_name,
        user_role=current_user.role.value,
        comment=req.comment or f"Progress updated to {req.progress_percentage}%",
    )
    return updated


@app.post(
    "/api/investigations/{investigation_id}/findings",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Append field observation or documentary evidence finding to case",
)
def add_investigation_finding(
    investigation_id: str,
    req: AddFindingRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Records an official observation or evidentiary finding in the case docket.
    """
    store = get_investigation_store()
    inv = store.get_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")

    if current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Outside assigned district.")

    updated = store.add_finding(
        investigation_id=investigation_id,
        finding_text=req.finding_text,
        evidence_notes=req.evidence_notes,
        user_name=current_user.full_name,
        user_role=current_user.role.value,
    )
    return updated


@app.post(
    "/api/investigations/{investigation_id}/escalate",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Escalate administrative investigation for higher-level ministerial/nodal review",
)
def escalate_investigation(
    investigation_id: str,
    req: EscalateInvestigationRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Escalates case to ESCALATED status with recorded rationale.
    """
    store = get_investigation_store()
    inv = store.get_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")

    if current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Outside assigned district.")

    updated = store.escalate(
        investigation_id=investigation_id,
        reason=req.reason,
        user_name=current_user.full_name,
        user_role=current_user.role.value,
    )
    return updated


@app.post(
    "/api/investigations/{investigation_id}/resolve",
    response_model=InvestigationRecord,
    tags=["Investigations"],
    summary="Resolve or close investigation with official final administrative recommendations",
)
def resolve_investigation(
    investigation_id: str,
    req: ResolveInvestigationRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Concludes case with final statutory recommendations.
    """
    store = get_investigation_store()
    inv = store.get_by_id(investigation_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Investigation '{investigation_id}' not found.")

    if current_user.role == UserRole.DISTRICT_AUTHORITY:
        if inv.district.strip().lower() != (current_user.assigned_district or "").strip().lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Outside assigned district.")

    updated = store.resolve(
        investigation_id=investigation_id,
        final_recommendation=req.final_recommendation,
        close_case=req.close_case,
        user_name=current_user.full_name,
        user_role=current_user.role.value,
    )
    return updated



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


@app.get(
    "/api/real-mplads/works",
    response_model=RealWorksListResponse,
    tags=["Real MPLADS"],
    summary="Browse and search genuine real MPLADS recommended and completed works",
)
def get_real_works(
    dataset: str = Query("recommended", description="'recommended' or 'completed'"),
    state: Optional[str] = Query(None, description="Filter by State"),
    category: Optional[str] = Query(None, description="Filter by Category"),
    q: Optional[str] = Query(None, description="Search query across Work Description"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Returns paginated authentic records from official MPLADS portal exports without synthetic augmentation.
    """
    loader = get_real_data_loader()
    dataset_clean = dataset.lower().strip()
    records = loader.recommended_records if dataset_clean == "recommended" else loader.completed_records

    filtered = records
    if state:
        st_clean = state.strip().lower()
        filtered = [r for r in filtered if r.state.strip().lower() == st_clean]
    if category:
        cat_clean = category.strip().lower()
        filtered = [r for r in filtered if r.category.strip().lower() == cat_clean]
    if q and q.strip():
        q_clean = q.strip().lower()
        filtered = [r for r in filtered if q_clean in r.work_description.lower()]

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": len(paginated),
        "dataset": "recommended_works" if dataset_clean == "recommended" else "completed_works",
        "data": paginated,
    }


@app.get(
    "/api/real-mplads/benchmark",
    response_model=RealWorkBenchmarkResult,
    tags=["Real MPLADS"],
    summary="Execute peer benchmarking and comparable project cost analysis against real MPLADS data",
)
def benchmark_real_work(
    work_id: Optional[int] = Query(None, description="Official Real MPLADS Work ID"),
    dataset: str = Query("recommended", description="'recommended' or 'completed'"),
    description: Optional[str] = Query(None, description="Custom work description for ad-hoc benchmarking"),
    amount: Optional[float] = Query(None, description="Custom proposed amount in Rupees"),
    state: Optional[str] = Query(None, description="Custom state context"),
    category: Optional[str] = Query(None, description="Custom category context"),
    ida: Optional[str] = Query(None, description="Custom IDA context"),
    top_k: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(0.35, ge=0.1, le=1.0),
):
    """
    Finds genuinely comparable real works using TF-IDF n-gram text similarity + administrative hierarchy,
    and computes median peer costs, variances, and explainable benchmarking insights without fabricating linkages.
    """
    engine = get_real_benchmark_engine()
    dataset_clean = dataset.lower().strip()

    if work_id is not None:
        return engine.benchmark_by_id(
            work_id=work_id,
            dataset=dataset_clean,
            top_k=top_k,
            min_composite_similarity=min_similarity,
        )
    elif description and amount is not None:
        return engine.benchmark_custom(
            description=description,
            amount=amount,
            state=state,
            category=category,
            ida=ida,
            dataset=dataset_clean,
            top_k=top_k,
            min_composite_similarity=min_similarity,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'work_id' or both ('description' and 'amount') must be provided for peer benchmarking.",
        )


@app.get(
    "/api/real-mplads/stats",
    response_model=RealMPLADSStatsResponse,
    tags=["Real MPLADS"],
    summary="Get summary metrics across the real MPLADS dataset repository",
)
def get_real_stats():
    """
    Returns summary statistics across recommended works, completed works, and macro financial datasets.
    """
    loader = get_real_data_loader()
    return loader.get_stats()


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
        "real_mplads_works": "/api/real-mplads/works",
        "real_mplads_benchmark": "/api/real-mplads/benchmark",
        "real_mplads_stats": "/api/real-mplads/stats",
    }
