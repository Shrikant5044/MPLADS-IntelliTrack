from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from app.anomaly_engine.geo import (
    build_spatial_grid,
    get_grid_neighbors,
    haversine_distance_km,
)
from app.anomaly_engine.models import (
    AnomalyResult,
    AnomalyTypeEnum,
    SeverityEnum,
    ThresholdConfig,
)


def compute_string_similarity(str1: str, str2: str) -> float:
    """
    Computes normalized text similarity ratio between two work names.
    """
    s1 = str(str1 or "").strip().lower()
    s2 = str(str2 or "").strip().lower()
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    return SequenceMatcher(None, s1, s2).ratio()


def compute_cost_similarity(cost1: float, cost2: float) -> float:
    """
    Computes fractional similarity (0.0 - 1.0) between two sanctioned/estimated amounts.
    """
    c1 = max(0.0, float(cost1 or 0.0))
    c2 = max(0.0, float(cost2 or 0.0))
    if c1 <= 0 and c2 <= 0:
        return 1.0
    max_c = max(c1, c2, 1.0)
    diff = abs(c1 - c2)
    return round(max(0.0, 1.0 - (diff / max_c)), 3)


class PotentialDuplicateWorkRule:
    """
    Duplicate Work Detection: Synthesizes text similarity, work category matching,
    geospatial proximity, and budget alignment to flag potential duplicate project entries.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or "latitude" not in projects_df.columns or "longitude" not in projects_df.columns:
            return results

        records = projects_df.to_dict(orient="records")
        # Build spatial grid index
        grid = build_spatial_grid(records, cell_size_deg=0.05)

        seen_pairs = set()

        for p1 in records:
            pid1 = str(p1.get("project_id", ""))
            lat1 = p1.get("latitude")
            lon1 = p1.get("longitude")
            if lat1 is None or lon1 is None:
                continue

            try:
                f_lat1, f_lon1 = float(lat1), float(lon1)
            except (ValueError, TypeError):
                continue

            name1 = str(p1.get("work_name", ""))
            cat1 = str(p1.get("work_category", "")).strip().lower()
            cost1 = float(p1.get("sanctioned_amount_lakh", 0.0) or p1.get("estimated_cost_lakh", 0.0) or 0.0)
            dist1 = str(p1.get("district", ""))

            candidates = get_grid_neighbors(grid, f_lat1, f_lon1, cell_size_deg=0.05)

            for p2 in candidates:
                pid2 = str(p2.get("project_id", ""))
                if pid1 >= pid2:
                    continue

                pair_key = (pid1, pid2)
                if pair_key in seen_pairs:
                    continue

                lat2 = p2.get("latitude")
                lon2 = p2.get("longitude")
                if lat2 is None or lon2 is None:
                    continue

                try:
                    f_lat2, f_lon2 = float(lat2), float(lon2)
                except (ValueError, TypeError):
                    continue

                # 1. Geographic distance check
                dist_km = haversine_distance_km(f_lat1, f_lon1, f_lat2, f_lon2)
                if dist_km > self.config.duplicate_max_distance_km:
                    continue

                # 2. Text name similarity
                name2 = str(p2.get("work_name", ""))
                name_sim = compute_string_similarity(name1, name2)

                # 3. Category match
                cat2 = str(p2.get("work_category", "")).strip().lower()
                cat_match = 1.0 if cat1 == cat2 and cat1 != "" else 0.0

                # 4. Cost similarity
                cost2 = float(p2.get("sanctioned_amount_lakh", 0.0) or p2.get("estimated_cost_lakh", 0.0) or 0.0)
                cost_sim = compute_cost_similarity(cost1, cost2)

                # 5. Proximity score (1.0 at 0km decaying to 0.0 at max distance)
                prox_score = max(0.0, 1.0 - (dist_km / self.config.duplicate_max_distance_km))

                # Composite weighted similarity score (0.0 to 1.0)
                composite_similarity = round(
                    (0.40 * name_sim)
                    + (0.25 * prox_score)
                    + (0.20 * cat_match)
                    + (0.15 * cost_sim),
                    3,
                )

                if composite_similarity >= self.config.duplicate_min_composite_similarity:
                    seen_pairs.add(pair_key)

                    if composite_similarity >= self.config.duplicate_critical_composite_similarity:
                        severity = SeverityEnum.CRITICAL
                        confidence = 0.95
                    elif composite_similarity >= self.config.duplicate_high_composite_similarity:
                        severity = SeverityEnum.HIGH
                        confidence = 0.90
                    else:
                        severity = SeverityEnum.MEDIUM
                        confidence = 0.85

                    # Anomaly result for Project 1
                    evidence_p1 = {
                        "matched_project_id": pid2,
                        "similarity_score": composite_similarity,
                        "distance_km": dist_km,
                        "cost_similarity": cost_sim,
                        "category_match": bool(cat_match),
                        "name_similarity": round(name_sim, 3),
                        "matched_work_name": name2,
                        "matched_work_category": p2.get("work_category"),
                        "matched_sanctioned_amount_lakh": round(cost2, 2),
                        "district": dist1,
                    }
                    explanation_p1 = (
                        f"Potential duplicate work: Project matches '{name2}' ({pid2}) located only {dist_km:.2f} km away "
                        f"in {dist1} (name similarity: {name_sim*100:.1f}%, composite similarity: {composite_similarity*100:.1f}%)."
                    )
                    results.append(AnomalyResult(
                        project_id=pid1,
                        anomaly_type=AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK,
                        severity=severity,
                        confidence=confidence,
                        evidence=evidence_p1,
                        explanation=explanation_p1,
                    ))

                    # Reciprocal Anomaly result for Project 2
                    evidence_p2 = {
                        "matched_project_id": pid1,
                        "similarity_score": composite_similarity,
                        "distance_km": dist_km,
                        "cost_similarity": cost_sim,
                        "category_match": bool(cat_match),
                        "name_similarity": round(name_sim, 3),
                        "matched_work_name": name1,
                        "matched_work_category": p1.get("work_category"),
                        "matched_sanctioned_amount_lakh": round(cost1, 2),
                        "district": dist1,
                    }
                    explanation_p2 = (
                        f"Potential duplicate work: Project matches '{name1}' ({pid1}) located only {dist_km:.2f} km away "
                        f"in {dist1} (name similarity: {name_sim*100:.1f}%, composite similarity: {composite_similarity*100:.1f}%)."
                    )
                    results.append(AnomalyResult(
                        project_id=pid2,
                        anomaly_type=AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK,
                        severity=severity,
                        confidence=confidence,
                        evidence=evidence_p2,
                        explanation=explanation_p2,
                    ))

        return results
