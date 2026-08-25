from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd


def parse_date(date_val: Any) -> Optional[datetime]:
    if date_val is None:
        return None
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, pd.Timestamp):
        return date_val.to_pydatetime()
    s = str(date_val).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt)
        except Exception:
            continue
    return None


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float("inf")
    try:
        f_lat1, f_lon1, f_lat2, f_lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (ValueError, TypeError):
        return float("inf")

    r = 6371.0
    phi1, phi2 = math.radians(f_lat1), math.radians(f_lat2)
    d_phi = math.radians(f_lat2 - f_lat1)
    d_lam = math.radians(f_lon2 - f_lon1)

    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    return round(r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 3)


def extract_project_features(
    projects_df: pd.DataFrame,
    financials_df: Optional[pd.DataFrame] = None,
    payments_df: Optional[pd.DataFrame] = None,
    progress_df: Optional[pd.DataFrame] = None,
    compliance_df: Optional[pd.DataFrame] = None,
    evidence_df: Optional[pd.DataFrame] = None,
    reference_date: Optional[datetime] = None,
) -> Tuple[List[str], pd.DataFrame]:
    """
    Constructs an independent, project-level numerical feature matrix across all 8 datasets.
    Excludes raw GPS coordinates, collinear duplicates, and rule-derived thresholded aggregates.
    Returns (project_ids, features_dataframe).
    """
    ref_date = reference_date or datetime(2026, 8, 23)

    if projects_df.empty:
        return [], pd.DataFrame()

    df = projects_df.copy()
    project_ids = [str(pid) for pid in df["project_id"]]

    # 1. Financial base metrics (Clean continuous variables)
    df["sanctioned_amount_lakh"] = df["sanctioned_amount_lakh"].fillna(0.0).astype(float)
    df["estimated_cost_lakh"] = df["estimated_cost_lakh"].fillna(0.0).astype(float)
    df["expenditure_lakh"] = df["expenditure_lakh"].fillna(0.0).astype(float)
    df["physical_progress_pct"] = df["physical_progress_pct"].fillna(0.0).astype(float)
    df["planned_progress_pct"] = df["planned_progress_pct"].fillna(0.0).astype(float)

    safe_sanction = np.maximum(df["sanctioned_amount_lakh"].values, 0.01)
    safe_estimate = np.maximum(df["estimated_cost_lakh"].values, 0.01)

    exp_to_sanction_ratio = df["expenditure_lakh"].values / safe_sanction
    cost_variance_pct = ((df["expenditure_lakh"].values - df["estimated_cost_lakh"].values) / safe_estimate) * 100.0
    utilization_pct = exp_to_sanction_ratio * 100.0
    progress_financial_gap = utilization_pct - df["physical_progress_pct"].values

    # 2. Progress and Timeline metrics
    start_dates = [parse_date(d) for d in df["start_date"]]
    exp_comp_dates = [parse_date(d) for d in df["expected_completion_date"]]
    statuses = [str(s).strip().lower() for s in df["status"]]

    planned_duration_days = []
    delay_days = []
    for i in range(len(project_ids)):
        s_dt = start_dates[i]
        e_dt = exp_comp_dates[i]
        st = statuses[i]
        prog = df["physical_progress_pct"].iloc[i]

        # Duration
        if s_dt and e_dt:
            dur = (e_dt - s_dt).days
            planned_duration_days.append(max(0, dur))
        else:
            planned_duration_days.append(180)

        # Elapsed delay
        if st != "completed" and prog < 100.0 and e_dt:
            d_over = (ref_date - e_dt).days
            delay_days.append(max(0, d_over))
        elif st == "delayed":
            delay_days.append(30)
        else:
            delay_days.append(0)

    # Progress updates aggregation
    progress_counts = {pid: 0 for pid in project_ids}
    days_since_last_update = {pid: 180 for pid in project_ids}

    if progress_df is not None and not progress_df.empty:
        prog_recs = progress_df.to_dict(orient="records")
        prog_grouped: Dict[str, List[datetime]] = {}
        for r in prog_recs:
            pid = str(r.get("project_id", ""))
            u_dt = parse_date(r.get("update_date"))
            if pid and u_dt:
                if pid not in prog_grouped:
                    prog_grouped[pid] = []
                prog_grouped[pid].append(u_dt)

        for pid, dts in prog_grouped.items():
            if pid in progress_counts:
                progress_counts[pid] = len(dts)
                latest = max(dts)
                days_since_last_update[pid] = max(0, (ref_date - latest).days)

    # 3. Payment Aggregation
    pmt_counts = {pid: 0 for pid in project_ids}
    pmt_totals = {pid: 0.0 for pid in project_ids}
    pmt_maxs = {pid: 0.0 for pid in project_ids}
    pmt_spans = {pid: 0 for pid in project_ids}

    if payments_df is not None and not payments_df.empty:
        pmt_recs = payments_df.to_dict(orient="records")
        pmt_grouped: Dict[str, List[Tuple[float, Optional[datetime]]]] = {}
        for r in pmt_recs:
            pid = str(r.get("project_id", ""))
            amt = float(r.get("amount_lakh", 0.0) or 0.0)
            p_dt = parse_date(r.get("payment_date"))
            if pid:
                if pid not in pmt_grouped:
                    pmt_grouped[pid] = []
                pmt_grouped[pid].append((amt, p_dt))

        for pid, p_list in pmt_grouped.items():
            if pid in pmt_counts:
                pmt_counts[pid] = len(p_list)
                total_a = sum(amt for amt, _ in p_list)
                pmt_totals[pid] = total_a
                pmt_maxs[pid] = max(amt for amt, _ in p_list)

                valid_dts = [dt for _, dt in p_list if dt]
                if len(valid_dts) >= 2:
                    pmt_spans[pid] = max(0, (max(valid_dts) - min(valid_dts)).days)

    pmt_count_arr = np.array([pmt_counts[pid] for pid in project_ids])
    pmt_total_arr = np.array([pmt_totals[pid] for pid in project_ids])
    pmt_max_arr = np.array([pmt_maxs[pid] for pid in project_ids])
    pmt_avg_arr = pmt_total_arr / np.maximum(pmt_count_arr, 1)
    pmt_max_ratio_arr = pmt_max_arr / np.maximum(pmt_total_arr, 0.01)
    pmt_span_arr = np.array([pmt_spans[pid] for pid in project_ids])

    # 4. Neutral Vendor & Agency Statistical Descriptors (NO rule thresholds)
    v_stats = df.groupby("vendor_id").agg(
        vendor_total_projects=("project_id", "count"),
        vendor_average_expenditure=("expenditure_lakh", "mean"),
        vendor_expenditure_std=("expenditure_lakh", "std"),
        vendor_average_project_cost=("estimated_cost_lakh", "mean"),
    ).fillna(0.0).to_dict(orient="index")

    a_stats = df.groupby("agency_id").agg(
        agency_total_projects=("project_id", "count"),
        agency_average_expenditure=("expenditure_lakh", "mean"),
        agency_expenditure_std=("expenditure_lakh", "std"),
    ).fillna(0.0).to_dict(orient="index")

    vendor_total_projects = np.array([v_stats.get(vid, {}).get("vendor_total_projects", 1) for vid in df["vendor_id"]])
    vendor_average_expenditure = np.array([v_stats.get(vid, {}).get("vendor_average_expenditure", 0.0) for vid in df["vendor_id"]])
    vendor_expenditure_std = np.array([v_stats.get(vid, {}).get("vendor_expenditure_std", 0.0) for vid in df["vendor_id"]])
    vendor_average_project_cost = np.array([v_stats.get(vid, {}).get("vendor_average_project_cost", 0.0) for vid in df["vendor_id"]])

    agency_total_projects = np.array([a_stats.get(aid, {}).get("agency_total_projects", 1) for aid in df["agency_id"]])
    agency_average_expenditure = np.array([a_stats.get(aid, {}).get("agency_average_expenditure", 0.0) for aid in df["agency_id"]])
    agency_expenditure_std = np.array([a_stats.get(aid, {}).get("agency_expenditure_std", 0.0) for aid in df["agency_id"]])

    # 5. Compliance & Evidence Count Metrics
    comp_missing_counts = {pid: 0 for pid in project_ids}
    if compliance_df is not None and not compliance_df.empty:
        c_missing = compliance_df[compliance_df["status"].str.strip().str.lower() == "missing"]
        c_missing_counts = c_missing["project_id"].value_counts().to_dict()
        for pid in project_ids:
            comp_missing_counts[pid] = c_missing_counts.get(pid, 0)

    evidence_counts = {pid: 0 for pid in project_ids}
    if evidence_df is not None and not evidence_df.empty:
        ev_counts = evidence_df["project_id"].value_counts().to_dict()
        for pid in project_ids:
            evidence_counts[pid] = ev_counts.get(pid, 0)

    comp_missing_arr = np.array([comp_missing_counts[pid] for pid in project_ids])
    evidence_count_arr = np.array([evidence_counts[pid] for pid in project_ids])

    # 6. Relative Geographic Proximity Metric (Exclude raw lat/lon degrees)
    lats = df["latitude"].fillna(0.0).astype(float).values
    lons = df["longitude"].fillna(0.0).astype(float).values

    coords = list(zip(lats, lons))
    nearby_5km_counts = []
    for i in range(len(coords)):
        lat1, lon1 = coords[i]
        c_count = 0
        for j in range(len(coords)):
            if i == j:
                continue
            lat2, lon2 = coords[j]
            if abs(lat1 - lat2) <= 0.05 and abs(lon1 - lon2) <= 0.05:
                if haversine_distance_km(lat1, lon1, lat2, lon2) <= 5.0:
                    c_count += 1
        nearby_5km_counts.append(c_count)

    nearby_5km_arr = np.array(nearby_5km_counts)

    # Assemble Final Decontaminated Feature Matrix (27 Features)
    feature_dict = {
        # Financial (6 features)
        "sanctioned_amount_lakh": df["sanctioned_amount_lakh"].values,
        "estimated_cost_lakh": df["estimated_cost_lakh"].values,
        "expenditure_lakh": df["expenditure_lakh"].values,
        "expenditure_to_sanction_ratio": exp_to_sanction_ratio,
        "cost_variance_pct": cost_variance_pct,
        "utilization_pct": utilization_pct,
        # Progress & Timeline (7 features)
        "physical_progress_pct": df["physical_progress_pct"].values,
        "planned_progress_pct": df["planned_progress_pct"].values,
        "progress_financial_gap": progress_financial_gap,
        "planned_duration_days": np.array(planned_duration_days),
        "delay_days": np.array(delay_days),
        "progress_updates_count": np.array([progress_counts[pid] for pid in project_ids]),
        "days_since_last_update": np.array([days_since_last_update[pid] for pid in project_ids]),
        # Payments (6 features)
        "payment_count": pmt_count_arr,
        "total_payment_amount_lakh": pmt_total_arr,
        "avg_payment_amount_lakh": pmt_avg_arr,
        "max_payment_amount_lakh": pmt_max_arr,
        "max_payment_ratio": pmt_max_ratio_arr,
        "payment_date_span_days": pmt_span_arr,
        # Neutral Vendor & Agency Descriptors (7 features)
        "vendor_total_projects": vendor_total_projects,
        "vendor_average_expenditure": vendor_average_expenditure,
        "vendor_expenditure_std": vendor_expenditure_std,
        "vendor_average_project_cost": vendor_average_project_cost,
        "agency_total_projects": agency_total_projects,
        "agency_average_expenditure": agency_average_expenditure,
        "agency_expenditure_std": agency_expenditure_std,
        # Compliance & Evidence (2 features)
        "missing_compliance_count": comp_missing_arr,
        "total_evidence_count": evidence_count_arr,
        # Relative Geographic Intelligence (1 feature)
        "nearby_projects_count_5km": nearby_5km_arr,
    }

    feature_df = pd.DataFrame(feature_dict)
    feature_df = feature_df.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    return project_ids, feature_df
