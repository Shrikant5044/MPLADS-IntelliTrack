from enum import Enum
from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, Field


class InvestigationTypeEnum(str, Enum):
    PHYSICAL_INSPECTION = "PHYSICAL_INSPECTION"
    FINANCIAL_AUDIT = "FINANCIAL_AUDIT"
    PAYMENT_VERIFICATION = "PAYMENT_VERIFICATION"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    DUPLICATE_GEO_VERIFICATION = "DUPLICATE_GEO_VERIFICATION"
    VENDOR_REVIEW = "VENDOR_REVIEW"
    AGENCY_REVIEW = "AGENCY_REVIEW"


class AuditUrgencyEnum(str, Enum):
    CRITICAL_URGENCY = "CRITICAL_URGENCY"
    HIGH_URGENCY = "HIGH_URGENCY"
    MEDIUM_URGENCY = "MEDIUM_URGENCY"
    ROUTINE = "ROUTINE"


class AuditQueueItem(BaseModel):
    """
    Prioritized, actionable decision-support record for district/state audit teams.
    """
    priority_rank: int = Field(..., description="Deterministic priority rank (1 = highest urgency target)")
    project_id: str = Field(..., description="Unique project identifier")
    work_name: str = Field(..., description="Name of the work")
    district: str = Field(..., description="Project district")
    state: str = Field(..., description="Project state")
    
    risk_score: int = Field(..., ge=0, le=100, description="Fused aggregate risk score (0-100)")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    urgency: AuditUrgencyEnum = Field(..., description="Operational urgency: CRITICAL_URGENCY, HIGH_URGENCY, MEDIUM_URGENCY, ROUTINE")
    
    primary_risk_drivers: List[str] = Field(default_factory=list, description="Top contributing risk and anomaly signals")
    anomaly_count: int = Field(..., description="Total number of discrete rule anomalies flagged")
    independent_anomaly_domains_count: int = Field(..., description="Count of distinct operational domains with active flags")
    
    financial_exposure_lakh: float = Field(..., description="Current cumulative expenditure subject to audit scrutiny in Lakhs")
    sanctioned_budget_lakh: float = Field(..., description="Total sanctioned budget in Lakhs")
    
    recommended_investigation_types: List[InvestigationTypeEnum] = Field(
        default_factory=list,
        description="Targeted audit tracks (e.g. PHYSICAL_INSPECTION, FINANCIAL_AUDIT, PAYMENT_VERIFICATION)",
    )
    recommended_action: str = Field(..., description="Prescribed statutory administrative next step")
    decision_support_rationale: str = Field(..., description="Synthesized justification for prioritization rank")
    evidence_summary: Dict[str, Any] = Field(default_factory=dict, description="Key numerical metrics backing audit queue entry")


class AuditQueueSummary(BaseModel):
    total_queued_projects: int
    critical_priority_count: int
    high_priority_count: int
    medium_priority_count: int
    routine_priority_count: int
    investigation_type_counts: Dict[str, int]
    total_financial_exposure_lakh: float


class AuditQueueResponse(BaseModel):
    total: int = Field(..., description="Total records matching filters")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")
    count: int = Field(..., description="Items in current payload")
    summary: AuditQueueSummary = Field(..., description="Statistical summary across prioritized audit queue")
    data: List[AuditQueueItem] = Field(..., description="Ranked list of prioritized audit queue items")


class PrioritizedAuditQueueEngine:
    """
    Decision-Support Prioritized Audit Queue Engine for MPLADS-IntelliTrack.
    Synthesizes multi-domain evidence, financial exposure, and anomaly severity into an actionable audit worklist.
    """

    def generate_queue(
        self,
        projects_df: pd.DataFrame,
        risk_profiles: List[Any],
        anomalies: List[Any],
    ) -> List[AuditQueueItem]:
        if projects_df.empty or not risk_profiles:
            return []

        proj_map = {str(r["project_id"]): r for r in projects_df.to_dict(orient="records")}
        anom_map: Dict[str, List[Any]] = {}
        for a in anomalies:
            pid = str(a.project_id)
            anom_map.setdefault(pid, []).append(a)

        raw_items: List[Dict[str, Any]] = []

        for p_profile in risk_profiles:
            pid = str(p_profile.project_id)
            p_data = proj_map.get(pid, {})
            p_anoms = anom_map.get(pid, [])
            
            score = int(p_profile.risk_score)
            level = str(p_profile.risk_level.value if hasattr(p_profile.risk_level, "value") else p_profile.risk_level)
            
            expenditure = float(p_data.get("expenditure_lakh", 0.0) or 0.0)
            sanctioned = float(p_data.get("sanctioned_amount_lakh", 0.0) or 0.0)
            
            # Map anomaly types to investigation tracks
            inv_types: set = set()
            domain_types: set = set()
            driver_names: List[str] = []
            
            for rf in p_profile.risk_factors:
                cat = str(rf.category.value if hasattr(rf.category, "value") else rf.category)
                sig = str(rf.signal)
                domain_types.add(cat)
                driver_names.append(sig.replace("_", " "))

            for a in p_anoms:
                t = str(a.anomaly_type.value if hasattr(a.anomaly_type, "value") else a.anomaly_type)
                if t in ("PROJECT_DELAY", "SLOW_PROGRESS", "SUDDEN_PROGRESS_JUMP", "MILESTONE_LAG", "COMPLETION_RISK", "PROGRESS_FINANCIAL_MISMATCH", "MISSING_PROGRESS_DOCUMENT"):
                    inv_types.add(InvestigationTypeEnum.PHYSICAL_INSPECTION)
                if t in ("EXPENDITURE_EXCEEDS_SANCTION", "COST_OVERRUN", "ABNORMALLY_HIGH_UTILIZATION", "ABNORMALLY_LOW_UTILIZATION", "UNUSUAL_EXPENDITURE_PATTERN", "MISSING_PAYMENT_SUPPORT"):
                    inv_types.add(InvestigationTypeEnum.FINANCIAL_AUDIT)
                if t in ("LARGE_PAYMENT", "RAPID_MULTIPLE_PAYMENTS", "REPEATED_PAYMENT_AMOUNT", "PAYMENT_BEFORE_MILESTONE", "PAYMENT_LOW_PROGRESS", "DEADLINE_PAYMENT_CONCENTRATION"):
                    inv_types.add(InvestigationTypeEnum.PAYMENT_VERIFICATION)
                if t in ("MISSING_SANCTION_DOCUMENT", "MISSING_INSPECTION_REPORT", "MISSING_COMPLETION_CERTIFICATE", "COMPLIANCE_DOCUMENT_GAP"):
                    inv_types.add(InvestigationTypeEnum.COMPLIANCE_REVIEW)
                if t == "POTENTIAL_DUPLICATE_WORK":
                    inv_types.add(InvestigationTypeEnum.DUPLICATE_GEO_VERIFICATION)
                if t in ("VENDOR_HIGH_DELAY_RATE", "VENDOR_HIGH_COST_ANOMALY_RATE", "VENDOR_HIGH_PAYMENT_ANOMALY_RATE", "VENDOR_PROJECT_CONCENTRATION"):
                    inv_types.add(InvestigationTypeEnum.VENDOR_REVIEW)
                if t in ("AGENCY_HIGH_ANOMALY_RATE", "AGENCY_REPEATED_ISSUES"):
                    inv_types.add(InvestigationTypeEnum.AGENCY_REVIEW)

            if not inv_types:
                inv_types.add(InvestigationTypeEnum.COMPLIANCE_REVIEW)

            # Assign Urgency
            if level == "CRITICAL" or score >= 75:
                urgency = AuditUrgencyEnum.CRITICAL_URGENCY
            elif level == "HIGH" or score >= 50:
                urgency = AuditUrgencyEnum.HIGH_URGENCY
            elif level == "MEDIUM" or score >= 25:
                urgency = AuditUrgencyEnum.MEDIUM_URGENCY
            else:
                urgency = AuditUrgencyEnum.ROUTINE

            # Decision support rationale
            domain_count = len(domain_types)
            if score >= 70:
                rationale = (
                    f"CRITICAL MULTI-SIGNAL EXPOSURE: Project flagged across {domain_count} distinct operational domains "
                    f"with {len(p_anoms)} verified anomaly signals and ₹{expenditure:.2f}L financial exposure. High-priority investigative audit required."
                )
            elif score >= 50:
                rationale = (
                    f"ELEVATED RISK CONCENTRATION: Compounded risk factors across {domain_count} domains. "
                    f"Targeted audit on {', '.join(sorted([t.value.replace('_', ' ') for t in list(inv_types)[:3]]))} recommended."
                )
            elif score >= 25:
                rationale = (
                    f"MODERATE MONITORING QUEUE: Secondary anomalies detected ({len(p_anoms)} signals). "
                    "Routine desk audit and compliance voucher verification sufficient."
                )
            else:
                rationale = "NOMINAL BASELINE: Project operating within standard statutory tolerances. Periodic monitoring cycle."

            raw_items.append({
                "project_id": pid,
                "work_name": str(p_data.get("work_name", "")),
                "district": str(p_data.get("district", "")),
                "state": str(p_data.get("state", "")),
                "risk_score": score,
                "risk_level": level,
                "urgency": urgency,
                "primary_risk_drivers": driver_names[:5],
                "anomaly_count": len(p_anoms),
                "independent_anomaly_domains_count": domain_count,
                "financial_exposure_lakh": round(expenditure, 2),
                "sanctioned_budget_lakh": round(sanctioned, 2),
                "recommended_investigation_types": sorted(list(inv_types), key=lambda x: x.value),
                "recommended_action": p_profile.recommended_action,
                "decision_support_rationale": rationale,
                "evidence_summary": {
                    "progress_pct": float(p_data.get("physical_progress_pct", 0.0) or 0.0),
                    "expenditure_lakh": round(expenditure, 2),
                    "sanctioned_lakh": round(sanctioned, 2),
                    "ml_outlier_flag": bool(p_profile.ml_signal.flag) if p_profile.ml_signal else False,
                    "ml_anomaly_score": float(p_profile.ml_signal.score) if p_profile.ml_signal else 0.0,
                },
            })

        # Deterministic Sorting:
        # 1. Risk Score (desc)
        # 2. Number of independent anomaly domains (desc)
        # 3. Anomaly count (desc)
        # 4. Financial exposure (desc)
        # 5. Project ID (asc)
        raw_items.sort(
            key=lambda x: (
                -x["risk_score"],
                -x["independent_anomaly_domains_count"],
                -x["anomaly_count"],
                -x["financial_exposure_lakh"],
                x["project_id"],
            )
        )

        # Assign priority rank 1..N
        queue_items: List[AuditQueueItem] = []
        for rank, item in enumerate(raw_items, 1):
            queue_items.append(AuditQueueItem(
                priority_rank=rank,
                project_id=item["project_id"],
                work_name=item["work_name"],
                district=item["district"],
                state=item["state"],
                risk_score=item["risk_score"],
                risk_level=item["risk_level"],
                urgency=item["urgency"],
                primary_risk_drivers=item["primary_risk_drivers"],
                anomaly_count=item["anomaly_count"],
                independent_anomaly_domains_count=item["independent_anomaly_domains_count"],
                financial_exposure_lakh=item["financial_exposure_lakh"],
                sanctioned_budget_lakh=item["sanctioned_budget_lakh"],
                recommended_investigation_types=item["recommended_investigation_types"],
                recommended_action=item["recommended_action"],
                decision_support_rationale=item["decision_support_rationale"],
                evidence_summary=item["evidence_summary"],
            ))

        return queue_items

    def get_summary(
        self,
        items: List[AuditQueueItem],
    ) -> AuditQueueSummary:
        crit_cnt = sum(1 for i in items if i.urgency == AuditUrgencyEnum.CRITICAL_URGENCY)
        high_cnt = sum(1 for i in items if i.urgency == AuditUrgencyEnum.HIGH_URGENCY)
        med_cnt = sum(1 for i in items if i.urgency == AuditUrgencyEnum.MEDIUM_URGENCY)
        routine_cnt = sum(1 for i in items if i.urgency == AuditUrgencyEnum.ROUTINE)
        
        inv_counts: Dict[str, int] = {}
        for i in items:
            for t in i.recommended_investigation_types:
                t_key = t.value
                inv_counts[t_key] = inv_counts.get(t_key, 0) + 1

        total_exposure = round(sum(i.financial_exposure_lakh for i in items if i.urgency in (AuditUrgencyEnum.CRITICAL_URGENCY, AuditUrgencyEnum.HIGH_URGENCY)), 2)

        return AuditQueueSummary(
            total_queued_projects=len(items),
            critical_priority_count=crit_cnt,
            high_priority_count=high_cnt,
            medium_priority_count=med_cnt,
            routine_priority_count=routine_cnt,
            investigation_type_counts=inv_counts,
            total_financial_exposure_lakh=total_exposure,
        )
