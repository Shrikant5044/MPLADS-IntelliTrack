import math
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from pydantic import BaseModel, Field


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Computes the great-circle distance between two GPS coordinates in kilometers
    using the Haversine formula.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float("inf")

    try:
        f_lat1, f_lon1 = float(lat1), float(lon1)
        f_lat2, f_lon2 = float(lat2), float(lon2)
    except (ValueError, TypeError):
        return float("inf")

    # Earth radius in kilometers
    r = 6371.0

    phi1 = math.radians(f_lat1)
    phi2 = math.radians(f_lat2)
    delta_phi = math.radians(f_lat2 - f_lat1)
    delta_lambda = math.radians(f_lon2 - f_lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(r * c, 3)


def build_spatial_grid(
    records: List[Dict[str, Any]],
    cell_size_deg: float = 0.05,
) -> Dict[Tuple[int, int], List[Dict[str, Any]]]:
    """
    Partitions geographical records into 2D spatial grid buckets (O(1) localized lookups).
    A cell size of 0.05 degrees is approximately ~5.5 km.
    """
    grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for r in records:
        lat = r.get("latitude")
        lon = r.get("longitude")
        if lat is not None and lon is not None:
            try:
                cx = int(float(lat) / cell_size_deg)
                cy = int(float(lon) / cell_size_deg)
                cell = (cx, cy)
                if cell not in grid:
                    grid[cell] = []
                grid[cell].append(r)
            except (ValueError, TypeError):
                continue
    return grid


def get_grid_neighbors(
    grid: Dict[Tuple[int, int], List[Dict[str, Any]]],
    lat: float,
    lon: float,
    cell_size_deg: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Retrieves all records in the 3x3 neighboring spatial grid cells for a coordinate.
    """
    cx = int(lat / cell_size_deg)
    cy = int(lon / cell_size_deg)
    neighbors: List[Dict[str, Any]] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            neighbors.extend(grid.get((cx + dx, cy + dy), []))
    return neighbors


class SpatialCluster(BaseModel):
    cluster_id: int
    center_latitude: float
    center_longitude: float
    radius_km: float
    project_count: int
    district: str
    project_ids: List[str]
    work_categories: List[str]


def compute_spatial_clusters(
    projects_df: pd.DataFrame,
    eps_km: float = 1.0,
    min_projects: int = 2,
) -> List[SpatialCluster]:
    """
    Identifies geographic clusters of projects in close physical proximity (<= eps_km).
    """
    if projects_df.empty or "latitude" not in projects_df.columns or "longitude" not in projects_df.columns:
        return []

    records = projects_df.to_dict(orient="records")
    valid_records = [r for r in records if r.get("latitude") is not None and r.get("longitude") is not None]

    visited = set()
    clusters: List[SpatialCluster] = []
    cluster_idx = 1

    for i, p1 in enumerate(valid_records):
        pid1 = str(p1["project_id"])
        if pid1 in visited:
            continue

        lat1, lon1 = float(p1["latitude"]), float(p1["longitude"])
        cluster_members = [p1]

        for j, p2 in enumerate(valid_records):
            if i == j:
                continue
            lat2, lon2 = float(p2["latitude"]), float(p2["longitude"])
            if haversine_distance_km(lat1, lon1, lat2, lon2) <= eps_km:
                cluster_members.append(p2)

        if len(cluster_members) >= min_projects:
            member_ids = [str(m["project_id"]) for m in cluster_members]
            for mid in member_ids:
                visited.add(mid)

            avg_lat = sum(float(m["latitude"]) for m in cluster_members) / len(cluster_members)
            avg_lon = sum(float(m["longitude"]) for m in cluster_members) / len(cluster_members)
            max_r = max(haversine_distance_km(avg_lat, avg_lon, float(m["latitude"]), float(m["longitude"])) for m in cluster_members)
            categories = list({str(m.get("work_category", "")) for m in cluster_members if m.get("work_category")})

            clusters.append(SpatialCluster(
                cluster_id=cluster_idx,
                center_latitude=round(avg_lat, 6),
                center_longitude=round(avg_lon, 6),
                radius_km=round(max_r, 3),
                project_count=len(cluster_members),
                district=str(p1.get("district", "Unknown")),
                project_ids=member_ids,
                work_categories=categories,
            ))
            cluster_idx += 1

    return clusters
