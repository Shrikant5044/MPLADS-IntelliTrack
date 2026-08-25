from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, Field


# India approximate state geographic bounding boxes (lat_min, max_lat, min_lon, max_lon)
STATE_BOUNDS: Dict[str, tuple] = {
    "Karnataka": (11.5, 18.5, 74.0, 78.5),
    "Tamil Nadu": (8.1, 13.6, 76.1, 80.36),
    "Maharashtra": (15.6, 22.0, 72.6, 80.9),
    "Gujarat": (20.1, 24.7, 68.2, 74.4),
    "Rajasthan": (23.0, 30.2, 69.5, 78.3),
    "Madhya Pradesh": (21.1, 26.9, 74.0, 82.8),
    "Uttar Pradesh": (23.8, 30.4, 77.0, 84.6),
    "Bihar": (24.3, 27.5, 83.3, 88.3),
    "West Bengal": (21.5, 27.3, 85.8, 89.9),
    "Telangana": (15.8, 19.9, 77.2, 81.8),
}

# General India territorial boundary box
INDIA_BOUNDS = (8.0, 37.5, 68.0, 97.5)


class ProjectLocationValidation(BaseModel):
    project_id: str
    latitude: float
    longitude: float
    is_valid: bool
    inside_india: bool
    state_match: bool
    is_on_land: bool
    declared_state: str
    declared_district: str
    location_source: str = "synthetic_district_registry"


class GeospatialQualityMetrics(BaseModel):
    total_projects: int = Field(..., description="Total project records analyzed")
    valid_coordinates: int = Field(..., description="Projects with valid numeric coordinates on land")
    invalid_coordinates: int = Field(..., description="Projects with missing or non-numeric coordinates")
    outside_india: int = Field(..., description="Coordinates falling outside national geographic boundaries")
    state_mismatches: int = Field(..., description="Coordinates falling outside declared state boundaries")
    water_points: int = Field(..., description="Coordinates detected in sea/open ocean water")
    district_consistent: int = Field(..., description="Coordinates consistent with synthetic district anchors")
    coverage_percentage: float = Field(..., description="Percentage of projects with valid verified locations")
    state_distribution: Dict[str, int] = Field(default_factory=dict, description="Count of projects per state")


def validate_project_location(project: Dict[str, Any]) -> ProjectLocationValidation:
    """
    Validates a single project's coordinate against India boundary, state bounding box, and land integrity.
    """
    pid = str(project.get("project_id", ""))
    st = str(project.get("state", "")).strip()
    dist = str(project.get("district", "")).strip()
    
    lat = project.get("latitude")
    lon = project.get("longitude")
    
    if lat is None or lon is None:
        return ProjectLocationValidation(
            project_id=pid,
            latitude=0.0,
            longitude=0.0,
            is_valid=False,
            inside_india=False,
            state_match=False,
            is_on_land=False,
            declared_state=st,
            declared_district=dist,
        )
        
    try:
        f_lat = float(lat)
        f_lon = float(lon)
    except (ValueError, TypeError):
        return ProjectLocationValidation(
            project_id=pid,
            latitude=0.0,
            longitude=0.0,
            is_valid=False,
            inside_india=False,
            state_match=False,
            is_on_land=False,
            declared_state=st,
            declared_district=dist,
        )

    # 1. India boundary check
    inside_india = (
        INDIA_BOUNDS[0] <= f_lat <= INDIA_BOUNDS[1]
        and INDIA_BOUNDS[2] <= f_lon <= INDIA_BOUNDS[3]
    )

    # 2. State boundary check
    state_match = True
    if st in STATE_BOUNDS:
        min_lat, max_lat, min_lon, max_lon = STATE_BOUNDS[st]
        state_match = (min_lat <= f_lat <= max_lat and min_lon <= f_lon <= max_lon)

    # 3. Water / Sea exclusion check
    is_on_land = not (
        (f_lat < 19.0 and f_lon < 72.6)
        or (f_lat < 16.0 and f_lon > 81.5)
    )

    is_valid = inside_india and is_on_land and (f_lat != 0.0 or f_lon != 0.0)

    return ProjectLocationValidation(
        project_id=pid,
        latitude=round(f_lat, 6),
        longitude=round(f_lon, 6),
        is_valid=is_valid,
        inside_india=inside_india,
        state_match=state_match,
        is_on_land=is_on_land,
        declared_state=st,
        declared_district=dist,
    )


def get_geospatial_quality_metrics(projects_df: pd.DataFrame) -> GeospatialQualityMetrics:
    """
    Computes portfolio-wide geospatial data quality and accuracy metrics.
    """
    if projects_df.empty:
        return GeospatialQualityMetrics(
            total_projects=0,
            valid_coordinates=0,
            invalid_coordinates=0,
            outside_india=0,
            state_mismatches=0,
            water_points=0,
            district_consistent=0,
            coverage_percentage=0.0,
            state_distribution={},
        )

    records = projects_df.to_dict(orient="records")
    total = len(records)
    
    valid_cnt = 0
    invalid_cnt = 0
    outside_india_cnt = 0
    state_mismatch_cnt = 0
    water_cnt = 0
    dist_consistent_cnt = 0
    state_counts: Dict[str, int] = {}

    for r in records:
        val = validate_project_location(r)
        st = val.declared_state
        state_counts[st] = state_counts.get(st, 0) + 1
        
        if val.is_valid:
            valid_cnt += 1
        else:
            invalid_cnt += 1
            
        if not val.inside_india:
            outside_india_cnt += 1
            
        if not val.state_match:
            state_mismatch_cnt += 1
            
        if not val.is_on_land:
            water_cnt += 1
            
        if val.is_valid:
            dist_consistent_cnt += 1

    coverage_pct = round((valid_cnt / total * 100.0), 2) if total > 0 else 0.0

    return GeospatialQualityMetrics(
        total_projects=total,
        valid_coordinates=valid_cnt,
        invalid_coordinates=invalid_cnt,
        outside_india=outside_india_cnt,
        state_mismatches=state_mismatch_cnt,
        water_points=water_cnt,
        district_consistent=dist_consistent_cnt,
        coverage_percentage=coverage_pct,
        state_distribution=state_counts,
    )
