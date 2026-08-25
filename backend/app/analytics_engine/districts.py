from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class DistrictRiskProfile(BaseModel):
    district: str = Field(..., description="District name")
    state: str = Field(..., description="State name")
    total_projects: int = Field(..., description="Total project count in district")
    active_projects: int = Field(..., description="Ongoing/active projects count")
    completed_projects: int = Field(..., description="Completed projects count")
    
    total_sanctioned_lakh: float = Field(..., description="Total sanctioned budget in Lakhs")
    total_expenditure_lakh: float = Field(..., description="Total expenditure in Lakhs")
    fund_utilization_pct: float = Field(..., description="Overall fund utilization percentage")
    
    average_risk_score: float = Field(..., description="Average project risk score in district (0-100)")
    critical_risk_count: int = Field(..., description="Count of CRITICAL risk projects (75-100)")
    high_risk_count: int = Field(..., description="Count of HIGH risk projects (50-74)")
    medium_risk_count: int = Field(..., description="Count of MEDIUM risk projects (25-49)")
    low_risk_count: int = Field(..., description="Count of LOW risk projects (0-24)")
    
    total_anomalies_detected: int = Field(..., description="Total anomalies detected across district works")
    anomalous_projects_count: int = Field(..., description="Number of projects with at least one anomaly")
    duplicate_work_pairs_count: int = Field(..., description="Count of suspected duplicate works in district")
    
    unique_vendors_count: int = Field(..., description="Number of distinct vendors active in district")
    max_vendor_concentration_share_pct: float = Field(..., description="Highest percentage of district projects held by a single vendor")
    top_implementing_agency: str = Field(..., description="Agency managing the most projects in district")


class DistrictAnalyticsSummary(BaseModel):
    total_districts: int
    total_projects: int
    national_average_district_risk: float
    highest_risk_district: str
    highest_risk_district_score: float
    total_sanctioned_all_districts_lakh: float
    total_expenditure_all_districts_lakh: float


class DistrictAnalyticsResponse(BaseModel):
    total: int
    summary: DistrictAnalyticsSummary
    data: List[DistrictRiskProfile]


class DistrictAnalyticsEngine:
    """
    Macro-level District & Regional Risk Aggregation Engine.
    Synthesizes portfolio health, market concentration, and statutory anomaly density per district.
    """

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        risk_profiles: List[Any],
        anomalies: List[Any],
    ) -> List[DistrictRiskProfile]:
        if projects_df.empty:
            return []

        risk_map = {str(p.project_id): p for p in risk_profiles}
        anom_map: Dict[str, List[Any]] = {}
        for a in anomalies:
            pid = str(a.project_id)
            anom_map.setdefault(pid, []).append(a)

        district_profiles: List[DistrictRiskProfile] = []

        for dist_name, g in projects_df.groupby("district"):
            dist_str = str(dist_name)
            state_str = str(g["state"].iloc[0]) if "state" in g.columns and not g["state"].empty else "Unknown"
            
            total_proj = len(g)
            completed_cnt = int((g["status"] == "Completed").sum())
            active_cnt = total_proj - completed_cnt
            
            total_sanc = float(g["sanctioned_amount_lakh"].sum() or 0.0)
            total_exp = float(g["expenditure_lakh"].sum() or 0.0)
            utilization = round((total_exp / total_sanc * 100.0), 1) if total_sanc > 0 else 0.0
            
            pids = [str(pid) for pid in g["project_id"]]
            
            dist_scores = [risk_map[pid].risk_score for pid in pids if pid in risk_map]
            avg_risk = round(float(np.mean(dist_scores)), 2) if dist_scores else 0.0
            
            crit_cnt = sum(1 for pid in pids if pid in risk_map and risk_map[pid].risk_level.value == "CRITICAL")
            high_cnt = sum(1 for pid in pids if pid in risk_map and risk_map[pid].risk_level.value == "HIGH")
            med_cnt = sum(1 for pid in pids if pid in risk_map and risk_map[pid].risk_level.value == "MEDIUM")
            low_cnt = sum(1 for pid in pids if pid in risk_map and risk_map[pid].risk_level.value == "LOW")
            
            dist_anoms = [a for pid in pids for a in anom_map.get(pid, [])]
            total_anoms = len(dist_anoms)
            anom_proj_cnt = len(set(a.project_id for a in dist_anoms))
            dup_cnt = sum(1 for a in dist_anoms if a.anomaly_type.value == "POTENTIAL_DUPLICATE_WORK")
            
            vendors = g["vendor_id"].dropna().tolist()
            unique_v = len(set(vendors))
            max_v_share = 0.0
            if vendors:
                v_counts = pd.Series(vendors).value_counts()
                max_v_share = round((float(v_counts.iloc[0]) / float(len(vendors))) * 100.0, 1)
                
            top_agency = "None"
            if "agency_id" in g.columns and not g["agency_id"].dropna().empty:
                top_agency = str(g["agency_id"].value_counts().index[0])

            district_profiles.append(DistrictRiskProfile(
                district=dist_str,
                state=state_str,
                total_projects=total_proj,
                active_projects=active_cnt,
                completed_projects=completed_cnt,
                total_sanctioned_lakh=round(total_sanc, 2),
                total_expenditure_lakh=round(total_exp, 2),
                fund_utilization_pct=utilization,
                average_risk_score=avg_risk,
                critical_risk_count=crit_cnt,
                high_risk_count=high_cnt,
                medium_risk_count=med_cnt,
                low_risk_count=low_cnt,
                total_anomalies_detected=total_anoms,
                anomalous_projects_count=anom_proj_cnt,
                duplicate_work_pairs_count=dup_cnt,
                unique_vendors_count=unique_v,
                max_vendor_concentration_share_pct=max_v_share,
                top_implementing_agency=top_agency,
            ))

        # Rank districts by average risk score descending
        district_profiles.sort(key=lambda d: d.average_risk_score, reverse=True)
        return district_profiles

    def get_summary(
        self,
        profiles: List[DistrictRiskProfile],
    ) -> DistrictAnalyticsSummary:
        if not profiles:
            return DistrictAnalyticsSummary(
                total_districts=0,
                total_projects=0,
                national_average_district_risk=0.0,
                highest_risk_district="N/A",
                highest_risk_district_score=0.0,
                total_sanctioned_all_districts_lakh=0.0,
                total_expenditure_all_districts_lakh=0.0,
            )

        total_d = len(profiles)
        total_p = sum(p.total_projects for p in profiles)
        avg_risk = round(float(np.mean([p.average_risk_score for p in profiles])), 2)
        highest_d = profiles[0].district
        highest_score = profiles[0].average_risk_score
        total_sanc = round(sum(p.total_sanctioned_lakh for p in profiles), 2)
        total_exp = round(sum(p.total_expenditure_lakh for p in profiles), 2)

        return DistrictAnalyticsSummary(
            total_districts=total_d,
            total_projects=total_p,
            national_average_district_risk=avg_risk,
            highest_risk_district=highest_d,
            highest_risk_district_score=highest_score,
            total_sanctioned_all_districts_lakh=total_sanc,
            total_expenditure_all_districts_lakh=total_exp,
        )
