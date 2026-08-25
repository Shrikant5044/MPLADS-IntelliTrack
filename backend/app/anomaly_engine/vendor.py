from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import pandas as pd
from app.anomaly_engine.models import (
    AnomalyResult,
    AnomalyTypeEnum,
    SeverityEnum,
    ThresholdConfig,
)


def parse_date(date_val: Any) -> Optional[datetime]:
    if date_val is None:
        return None
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, pd.Timestamp):
        return date_val.to_pydatetime()
    s = str(date_val).strip()
    if not s or s.lower() == "nan" or s.lower() == "nat":
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except Exception:
        try:
            return datetime.strptime(s[:10], "%d-%m-%Y")
        except Exception:
            return None


class VendorHighDelayRateRule:
    """
    Rule 7 (Vendor): Computes historical delay rate for vendors (>=35% delay rate across >=4 projects)
    and applies contextual vendor-delay risk to affected projects experiencing timeline strain.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or "vendor_id" not in projects_df.columns:
            return results

        ref_date = parse_date(self.config.reference_date_str) or datetime(2026, 8, 23)

        df = projects_df.copy()
        df["exp_dt"] = df["expected_completion_date"].apply(parse_date)
        df["is_delayed"] = (
            (df["status"] == "Delayed")
            | ((df["exp_dt"] < ref_date) & (df["status"] != "Completed") & (df["physical_progress_pct"] < 100.0))
        )

        v_stats = df.groupby("vendor_id").agg(
            total_projects=("project_id", "count"),
            delayed_projects=("is_delayed", "sum"),
        ).reset_index()
        v_stats["delay_rate"] = v_stats["delayed_projects"] / v_stats["total_projects"]

        # Filter qualifying high-delay vendors
        high_delay_vendors = v_stats[
            (v_stats["total_projects"] >= self.config.vendor_min_projects)
            & (v_stats["delay_rate"] >= self.config.vendor_high_delay_rate_threshold)
        ]

        v_lookup = {str(row["vendor_id"]): row for _, row in high_delay_vendors.iterrows()}

        for _, proj in df.iterrows():
            vid = str(proj.get("vendor_id", ""))
            is_proj_delayed = bool(proj["is_delayed"])
            proj_status = str(proj.get("status", "")).strip()

            # Anti-contagion: flag only if vendor has high delay rate AND current project is delayed/ongoing with strain
            if vid in v_lookup and (is_proj_delayed or proj_status in ["Delayed", "Ongoing"]):
                v_data = v_lookup[vid]
                d_rate = round(float(v_data["delay_rate"]) * 100, 2)
                t_count = int(v_data["total_projects"])
                d_count = int(v_data["delayed_projects"])

                severity = SeverityEnum.CRITICAL if (d_rate >= 50.0 and is_proj_delayed) else SeverityEnum.HIGH
                confidence = 0.92

                evidence = {
                    "vendor_id": str(vid),
                    "vendor_total_projects": int(t_count),
                    "vendor_delayed_projects": int(d_count),
                    "vendor_delay_rate_pct": float(d_rate),
                    "project_status": str(proj_status),
                    "project_is_delayed": is_proj_delayed,
                    "threshold_rate_pct": float(self.config.vendor_high_delay_rate_threshold * 100),
                }

                explanation = (
                    f"Vendor risk factor (chronic delay): assigned vendor {vid} has a historical delay rate of {d_rate:.1f}% "
                    f"({d_count} of {t_count} projects delayed), posing heightened execution risk for this project ({proj_status})."
                )

                results.append(AnomalyResult(
                    project_id=str(proj["project_id"]),
                    anomaly_type=AnomalyTypeEnum.VENDOR_HIGH_DELAY_RATE,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class VendorHighCostAnomalyRateRule:
    """
    Rule 8 (Vendor): Computes historical cost overrun rate for each vendor (>=30% overrun rate across >=4 projects)
    and applies contextual vendor-cost risk to affected projects experiencing budget escalation.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or "vendor_id" not in projects_df.columns:
            return results

        df = projects_df.copy()
        if financials_df is not None and not financials_df.empty:
            df = pd.merge(df, financials_df[["project_id", "cost_overrun_pct"]], on="project_id", how="left")
            df["is_overrun"] = (df["cost_overrun_pct"] > 0) | (df["expenditure_lakh"] > df["estimated_cost_lakh"])
        else:
            df["is_overrun"] = df["expenditure_lakh"] > df["estimated_cost_lakh"]

        v_stats = df.groupby("vendor_id").agg(
            total_projects=("project_id", "count"),
            overrun_projects=("is_overrun", "sum"),
        ).reset_index()
        v_stats["overrun_rate"] = v_stats["overrun_projects"] / v_stats["total_projects"]

        high_cost_vendors = v_stats[
            (v_stats["total_projects"] >= self.config.vendor_min_projects)
            & (v_stats["overrun_rate"] >= self.config.vendor_high_cost_anomaly_threshold)
        ]

        v_lookup = {str(row["vendor_id"]): row for _, row in high_cost_vendors.iterrows()}

        for _, proj in df.iterrows():
            vid = str(proj.get("vendor_id", ""))
            is_proj_overrun = bool(proj["is_overrun"])

            # Anti-contagion: flag only if vendor has high overrun rate AND current project has cost overrun/inflation
            if vid in v_lookup and is_proj_overrun:
                v_data = v_lookup[vid]
                o_rate = round(float(v_data["overrun_rate"]) * 100, 2)
                t_count = int(v_data["total_projects"])
                o_count = int(v_data["overrun_projects"])

                severity = SeverityEnum.CRITICAL if o_rate >= 50.0 else SeverityEnum.HIGH
                confidence = 0.92

                evidence = {
                    "vendor_id": str(vid),
                    "vendor_total_projects": int(t_count),
                    "vendor_cost_overrun_projects": int(o_count),
                    "vendor_cost_overrun_rate_pct": float(o_rate),
                    "project_cost_overrun_present": is_proj_overrun,
                    "threshold_rate_pct": float(self.config.vendor_high_cost_anomaly_threshold * 100),
                }

                explanation = (
                    f"Vendor risk factor (cost escalation history): assigned vendor {vid} has a historical cost overrun rate of "
                    f"{o_rate:.1f}% ({o_count} of {t_count} projects experienced cost escalation)."
                )

                results.append(AnomalyResult(
                    project_id=str(proj["project_id"]),
                    anomaly_type=AnomalyTypeEnum.VENDOR_HIGH_COST_ANOMALY_RATE,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class VendorHighPaymentAnomalyRateRule:
    """
    Rule 9 (Vendor): Identifies vendors with high payment anomaly rates (>=35% across >=4 projects)
    and applies contextual payment risk to affected projects.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        payments_df: pd.DataFrame,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or payments_df.empty:
            return results

        pmt_totals = payments_df.groupby("project_id")["amount_lakh"].transform("sum")
        pmt_calc = payments_df.copy()
        pmt_calc["share"] = pmt_calc["amount_lakh"] / pmt_totals
        anom_pids: Set[str] = set(pmt_calc[pmt_calc["share"] >= 0.55]["project_id"].unique())

        df = projects_df.copy()
        df["has_pmt_anom"] = df["project_id"].isin(anom_pids)

        v_stats = df.groupby("vendor_id").agg(
            total_projects=("project_id", "count"),
            anom_projects=("has_pmt_anom", "sum"),
        ).reset_index()
        v_stats["pmt_anom_rate"] = v_stats["anom_projects"] / v_stats["total_projects"]

        high_pmt_vendors = v_stats[
            (v_stats["total_projects"] >= self.config.vendor_min_projects)
            & (v_stats["pmt_anom_rate"] >= self.config.vendor_high_payment_anomaly_threshold)
        ]

        v_lookup = {str(row["vendor_id"]): row for _, row in high_pmt_vendors.iterrows()}

        for _, proj in df.iterrows():
            vid = str(proj.get("vendor_id", ""))
            pid = str(proj["project_id"])
            has_proj_pmt_anom = pid in anom_pids

            # Anti-contagion: flag only if vendor has high rate AND current project has payment pattern issues
            if vid in v_lookup and has_proj_pmt_anom:
                v_data = v_lookup[vid]
                p_rate = round(float(v_data["pmt_anom_rate"]) * 100, 2)
                t_count = int(v_data["total_projects"])
                a_count = int(v_data["anom_projects"])

                severity = SeverityEnum.HIGH if p_rate >= 50.0 else SeverityEnum.MEDIUM
                confidence = 0.90

                evidence = {
                    "vendor_id": str(vid),
                    "vendor_total_projects": int(t_count),
                    "vendor_payment_anomaly_projects": int(a_count),
                    "vendor_payment_anomaly_rate_pct": float(p_rate),
                    "project_has_payment_anomaly": has_proj_pmt_anom,
                }

                explanation = (
                    f"Vendor risk factor (payment pattern): assigned vendor {vid} has {a_count} of {t_count} projects "
                    f"({p_rate:.1f}%) with irregular payment disbursement patterns."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.VENDOR_HIGH_PAYMENT_ANOMALY_RATE,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class VendorProjectConcentrationRule:
    """
    Rule 10 (Vendor): Flags high concentration of contracts awarded to a single vendor
    within a district (>=35% market share) or overall portfolio (>=12 projects).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty:
            return results

        dist_totals = projects_df.groupby("district").size().to_dict()
        v_dist_counts = projects_df.groupby(["vendor_id", "district"]).size().reset_index(name="count")
        v_overall_counts = projects_df.groupby("vendor_id").size().to_dict()

        for _, proj in projects_df.iterrows():
            pid = str(proj["project_id"])
            vid = str(proj.get("vendor_id", ""))
            district = str(proj.get("district", ""))

            d_total = int(dist_totals.get(district, 1))
            match = v_dist_counts[(v_dist_counts["vendor_id"] == vid) & (v_dist_counts["district"] == district)]
            v_dist_c = int(match.iloc[0]["count"]) if not match.empty else 0
            v_dist_share = round((v_dist_c / d_total) * 100, 2)
            v_overall_c = int(v_overall_counts.get(vid, 0))

            is_dist_conc = v_dist_share >= (self.config.vendor_district_concentration_share * 100)
            is_overall_conc = v_overall_c >= self.config.vendor_max_projects_overall

            if is_dist_conc or is_overall_conc:
                severity = SeverityEnum.HIGH if (v_dist_share >= 40.0 or v_overall_c >= 14) else SeverityEnum.MEDIUM
                confidence = 0.90

                evidence = {
                    "vendor_id": str(vid),
                    "district": str(district),
                    "vendor_district_projects": int(v_dist_c),
                    "district_total_projects": int(d_total),
                    "district_market_share_pct": float(v_dist_share),
                    "vendor_overall_projects_count": int(v_overall_c),
                }

                explanation = (
                    f"Vendor contract concentration: vendor {vid} holds {v_dist_c} of {d_total} projects ({v_dist_share:.1f}%) "
                    f"in {district} (portfolio size: {v_overall_c} projects)."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.VENDOR_PROJECT_CONCENTRATION,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class AgencyHighAnomalyRateRule:
    """
    Rule 11 (Agency): Calculates implementation agency historical problem rate (>=35% across >=8 projects)
    and flags projects under that agency that exhibit active implementation strain.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or "agency_id" not in projects_df.columns:
            return results

        ref_date = parse_date(self.config.reference_date_str) or datetime(2026, 8, 23)
        df = projects_df.copy()
        df["exp_dt"] = df["expected_completion_date"].apply(parse_date)
        df["is_delayed"] = (
            (df["status"] == "Delayed")
            | ((df["exp_dt"] < ref_date) & (df["status"] != "Completed") & (df["physical_progress_pct"] < 100.0))
        )

        if financials_df is not None and not financials_df.empty:
            df = pd.merge(df, financials_df[["project_id", "cost_overrun_pct"]], on="project_id", how="left")
            df["is_overrun"] = (df["cost_overrun_pct"] > 0) | (df["expenditure_lakh"] > df["estimated_cost_lakh"])
        else:
            df["is_overrun"] = df["expenditure_lakh"] > df["estimated_cost_lakh"]

        df["is_problematic"] = df["is_delayed"] | df["is_overrun"]

        a_stats = df.groupby("agency_id").agg(
            total_projects=("project_id", "count"),
            problem_projects=("is_problematic", "sum"),
        ).reset_index()
        a_stats["problem_rate"] = a_stats["problem_projects"] / a_stats["total_projects"]

        high_anom_agencies = a_stats[
            (a_stats["total_projects"] >= self.config.agency_min_projects)
            & (a_stats["problem_rate"] >= self.config.agency_high_anomaly_rate_threshold)
        ]

        a_lookup = {str(row["agency_id"]): row for _, row in high_anom_agencies.iterrows()}

        for _, proj in df.iterrows():
            aid = str(proj.get("agency_id", ""))
            is_proj_problematic = bool(proj["is_problematic"])

            # Anti-contagion: flag only if agency has high problem rate AND current project has implementation issues
            if aid in a_lookup and is_proj_problematic:
                a_data = a_lookup[aid]
                p_rate = round(float(a_data["problem_rate"]) * 100, 2)
                t_count = int(a_data["total_projects"])
                pr_count = int(a_data["problem_projects"])

                severity = SeverityEnum.HIGH if p_rate >= 45.0 else SeverityEnum.MEDIUM
                confidence = 0.90

                evidence = {
                    "agency_id": str(aid),
                    "agency_total_projects": int(t_count),
                    "agency_problem_projects": int(pr_count),
                    "agency_anomaly_rate_pct": float(p_rate),
                    "project_is_problematic": is_proj_problematic,
                    "threshold_rate_pct": float(self.config.agency_high_anomaly_rate_threshold * 100),
                }

                explanation = (
                    f"Agency risk factor: implementing agency {aid} has a {p_rate:.1f}% problem rate "
                    f"across its portfolio ({pr_count} of {t_count} projects with delays or cost escalation)."
                )

                results.append(AnomalyResult(
                    project_id=str(proj["project_id"]),
                    anomaly_type=AnomalyTypeEnum.AGENCY_HIGH_ANOMALY_RATE,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class AgencyRepeatedIssuesRule:
    """
    Rule 12 (Agency): Detects agencies with recurring systemic issues (>=3 delayed AND >=3 cost overrun projects)
    and applies contextual agency risk to affected projects experiencing active issues.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or "agency_id" not in projects_df.columns:
            return results

        ref_date = parse_date(self.config.reference_date_str) or datetime(2026, 8, 23)
        df = projects_df.copy()
        df["exp_dt"] = df["expected_completion_date"].apply(parse_date)
        df["is_delayed"] = (
            (df["status"] == "Delayed")
            | ((df["exp_dt"] < ref_date) & (df["status"] != "Completed") & (df["physical_progress_pct"] < 100.0))
        )

        if financials_df is not None and not financials_df.empty:
            df = pd.merge(df, financials_df[["project_id", "cost_overrun_pct"]], on="project_id", how="left")
            df["is_overrun"] = (df["cost_overrun_pct"] > 0) | (df["expenditure_lakh"] > df["estimated_cost_lakh"])
        else:
            df["is_overrun"] = df["expenditure_lakh"] > df["estimated_cost_lakh"]

        a_stats = df.groupby("agency_id").agg(
            total_projects=("project_id", "count"),
            delayed_projects=("is_delayed", "sum"),
            overrun_projects=("is_overrun", "sum"),
        ).reset_index()

        rep_agencies = a_stats[
            (a_stats["delayed_projects"] >= self.config.agency_repeated_issue_min_delayed)
            & (a_stats["overrun_projects"] >= self.config.agency_repeated_issue_min_overrun)
        ]

        a_lookup = {str(row["agency_id"]): row for _, row in rep_agencies.iterrows()}

        for _, proj in df.iterrows():
            aid = str(proj.get("agency_id", ""))
            is_proj_affected = bool(proj["is_delayed"] or proj["is_overrun"])

            # Anti-contagion: flag only if agency has systemic issues AND current project has active delays or overruns
            if aid in a_lookup and is_proj_affected:
                a_data = a_lookup[aid]
                t_count = int(a_data["total_projects"])
                d_count = int(a_data["delayed_projects"])
                o_count = int(a_data["overrun_projects"])

                severity = SeverityEnum.HIGH if (d_count >= 4 or o_count >= 4) else SeverityEnum.MEDIUM
                confidence = 0.90

                evidence = {
                    "agency_id": str(aid),
                    "agency_total_projects": int(t_count),
                    "agency_delayed_projects": int(d_count),
                    "agency_overrun_projects": int(o_count),
                    "project_is_affected": is_proj_affected,
                }

                explanation = (
                    f"Recurring agency implementation failure: agency {aid} exhibits multiple systemic issues "
                    f"across {t_count} projects ({d_count} delayed, {o_count} with cost overruns)."
                )

                results.append(AnomalyResult(
                    project_id=str(proj["project_id"]),
                    anomaly_type=AnomalyTypeEnum.AGENCY_REPEATED_ISSUES,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results
