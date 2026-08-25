from typing import Any, Dict, List, Optional, Set
import pandas as pd
from app.anomaly_engine.models import (
    AnomalyResult,
    AnomalyTypeEnum,
    SeverityEnum,
    ThresholdConfig,
)


def extract_compliance_map(compliance_df: pd.DataFrame) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Extracts nested dictionary: {project_id: {requirement_name: record_dict}}.
    """
    comp_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if compliance_df.empty:
        return comp_map

    for r in compliance_df.to_dict(orient="records"):
        pid = str(r.get("project_id", ""))
        req = str(r.get("requirement", "")).strip()
        if pid not in comp_map:
            comp_map[pid] = {}
        comp_map[pid][req] = r
    return comp_map


def extract_evidence_types_by_project(evidence_df: pd.DataFrame) -> Dict[str, Set[str]]:
    """
    Extracts {project_id: set_of_evidence_types}.
    """
    ev_map: Dict[str, Set[str]] = {}
    if evidence_df.empty or "evidence_type" not in evidence_df.columns:
        return ev_map

    for r in evidence_df.to_dict(orient="records"):
        pid = str(r.get("project_id", ""))
        ev_type = str(r.get("evidence_type", "")).strip()
        if pid not in ev_map:
            ev_map[pid] = set()
        ev_map[pid].add(ev_type)
    return ev_map


class MissingSanctionDocumentRule:
    """
    Rule 1 (Compliance): Detects projects with approved sanction limits or disbursements
    where statutory Sanction Order documentation is missing.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        compliance_df: pd.DataFrame,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or compliance_df.empty:
            return results

        comp_map = extract_compliance_map(compliance_df)
        ev_map = extract_evidence_types_by_project(evidence_df) if evidence_df is not None else {}

        for proj in projects_df.to_dict(orient="records"):
            pid = str(proj.get("project_id", ""))
            sanctioned = float(proj.get("sanctioned_amount_lakh", 0.0) or 0.0)
            expenditure = float(proj.get("expenditure_lakh", 0.0) or 0.0)

            if sanctioned <= 0:
                continue

            comp_record = comp_map.get(pid, {}).get("Sanction Order")
            status_val = str(comp_record.get("status", "")).strip().lower() if comp_record else "missing"
            has_evidence = "Sanction Document" in ev_map.get(pid, set())

            if status_val == "missing" and not has_evidence:
                severity = SeverityEnum.HIGH if (expenditure >= 15.0 or sanctioned >= 25.0) else SeverityEnum.MEDIUM
                confidence = 0.95

                evidence = {
                    "requirement": "Sanction Order",
                    "compliance_status": "Missing",
                    "sanctioned_amount_lakh": round(sanctioned, 2),
                    "expenditure_lakh": round(expenditure, 2),
                    "due_date": comp_record.get("due_date") if comp_record else None,
                }

                explanation = (
                    f"Statutory document missing: Sanction Order is missing for project {pid} "
                    f"(Sanctioned: ₹{sanctioned:.2f} Lakh, Disbursed: ₹{expenditure:.2f} Lakh)."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.MISSING_SANCTION_DOCUMENT,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class MissingProgressDocumentRule:
    """
    Rule 2 (Compliance): Detects active or ongoing projects with physical progress on the ground
    where required periodic progress documentation / photographs are missing.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        compliance_df: pd.DataFrame,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or compliance_df.empty:
            return results

        comp_map = extract_compliance_map(compliance_df)
        ev_map = extract_evidence_types_by_project(evidence_df) if evidence_df is not None else {}

        for proj in projects_df.to_dict(orient="records"):
            pid = str(proj.get("project_id", ""))
            physical_progress = float(proj.get("physical_progress_pct", 0.0) or 0.0)
            status = str(proj.get("status", "")).strip()

            # Applicable to active works with reported physical progress
            if physical_progress <= 0:
                continue

            comp_record = comp_map.get(pid, {}).get("Progress Update")
            status_val = str(comp_record.get("status", "")).strip().lower() if comp_record else "missing"
            has_evidence = "Progress Photo" in ev_map.get(pid, set())

            if status_val == "missing" and not has_evidence:
                severity = SeverityEnum.MEDIUM if physical_progress >= 40.0 else SeverityEnum.LOW
                confidence = 0.90

                evidence = {
                    "requirement": "Progress Update",
                    "compliance_status": "Missing",
                    "physical_progress_pct": round(physical_progress, 2),
                    "project_status": status,
                    "due_date": comp_record.get("due_date") if comp_record else None,
                }

                explanation = (
                    f"Progress evidence missing: periodic Progress Update documentation is missing while "
                    f"reported physical execution stands at {physical_progress:.2f}% ({status})."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.MISSING_PROGRESS_DOCUMENT,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class MissingInspectionReportRule:
    """
    Rule 3 (Compliance): Detects projects reaching significant execution stages (>=40% physical progress
    or marked Completed) where mandatory technical inspection reports are missing.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        compliance_df: pd.DataFrame,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or compliance_df.empty:
            return results

        comp_map = extract_compliance_map(compliance_df)
        ev_map = extract_evidence_types_by_project(evidence_df) if evidence_df is not None else {}

        for proj in projects_df.to_dict(orient="records"):
            pid = str(proj.get("project_id", ""))
            physical_progress = float(proj.get("physical_progress_pct", 0.0) or 0.0)
            status = str(proj.get("status", "")).strip()

            # Inspection required when project is in advanced execution or completed
            if physical_progress < 40.0 and status.lower() != "completed":
                continue

            comp_record = comp_map.get(pid, {}).get("Inspection Report")
            status_val = str(comp_record.get("status", "")).strip().lower() if comp_record else "missing"
            has_evidence = "Inspection Report" in ev_map.get(pid, set())

            if status_val == "missing" and not has_evidence:
                severity = SeverityEnum.HIGH if (status.lower() == "completed" or physical_progress >= 75.0) else SeverityEnum.MEDIUM
                confidence = 0.90

                evidence = {
                    "requirement": "Inspection Report",
                    "compliance_status": "Missing",
                    "physical_progress_pct": round(physical_progress, 2),
                    "project_status": status,
                    "due_date": comp_record.get("due_date") if comp_record else None,
                }

                explanation = (
                    f"Technical inspection missing: mandatory site Inspection Report is missing for project {pid} "
                    f"at {physical_progress:.2f}% completion stage ({status})."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.MISSING_INSPECTION_REPORT,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class MissingPaymentSupportRule:
    """
    Rule 4 (Compliance): Detects projects where financial disbursements have been executed
    without required Payment Support documentation (vouchers, Measurement Book entries, bills).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        compliance_df: pd.DataFrame,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or compliance_df.empty:
            return results

        comp_map = extract_compliance_map(compliance_df)
        ev_map = extract_evidence_types_by_project(evidence_df) if evidence_df is not None else {}

        for proj in projects_df.to_dict(orient="records"):
            pid = str(proj.get("project_id", ""))
            expenditure = float(proj.get("expenditure_lakh", 0.0) or 0.0)

            # Applicable to projects with actual financial disbursements
            if expenditure <= 0:
                continue

            comp_record = comp_map.get(pid, {}).get("Payment Support")
            status_val = str(comp_record.get("status", "")).strip().lower() if comp_record else "missing"
            has_evidence = "Payment Document" in ev_map.get(pid, set())

            if status_val == "missing" and not has_evidence:
                severity = SeverityEnum.HIGH if expenditure >= 15.0 else SeverityEnum.MEDIUM
                confidence = 0.92

                evidence = {
                    "requirement": "Payment Support",
                    "compliance_status": "Missing",
                    "expenditure_lakh": round(expenditure, 2),
                    "due_date": comp_record.get("due_date") if comp_record else None,
                }

                explanation = (
                    f"Financial compliance gap: Payment Support documentation is missing for disbursed "
                    f"funds totaling ₹{expenditure:.2f} Lakh."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.MISSING_PAYMENT_SUPPORT,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class MissingCompletionCertificateRule:
    """
    Rule 5 (Compliance): Detects officially Completed projects without a verified Completion Certificate.
    Excludes ongoing/incomplete projects.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        compliance_df: pd.DataFrame,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or compliance_df.empty:
            return results

        comp_map = extract_compliance_map(compliance_df)
        ev_map = extract_evidence_types_by_project(evidence_df) if evidence_df is not None else {}

        for proj in projects_df.to_dict(orient="records"):
            pid = str(proj.get("project_id", ""))
            status = str(proj.get("status", "")).strip()
            physical_progress = float(proj.get("physical_progress_pct", 0.0) or 0.0)

            # Strict guard: ONLY for genuinely completed projects
            if status.lower() != "completed" and physical_progress < 100.0:
                continue

            comp_record = comp_map.get(pid, {}).get("Completion Certificate")
            status_val = str(comp_record.get("status", "")).strip().lower() if comp_record else "missing"
            has_evidence = "Completion Certificate" in ev_map.get(pid, set())

            if status_val == "missing" and not has_evidence:
                severity = SeverityEnum.HIGH
                confidence = 0.96

                evidence = {
                    "requirement": "Completion Certificate",
                    "compliance_status": "Missing",
                    "project_status": status,
                    "physical_progress_pct": round(physical_progress, 2),
                    "due_date": comp_record.get("due_date") if comp_record else None,
                }

                explanation = (
                    f"Formal completion certificate missing: project {pid} is recorded as 'Completed' "
                    f"(100% physical progress) but lacks mandatory Work Completion Certificate evidence."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.MISSING_COMPLETION_CERTIFICATE,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results


class ComplianceDocumentGapRule:
    """
    Rule 6 (Compliance): Detects systemic documentation neglect where multiple (>=2) mandatory
    compliance documents are missing for a project based on its lifecycle stage.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        compliance_df: pd.DataFrame,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if projects_df.empty or compliance_df.empty:
            return results

        comp_map = extract_compliance_map(compliance_df)
        ev_map = extract_evidence_types_by_project(evidence_df) if evidence_df is not None else {}

        for proj in projects_df.to_dict(orient="records"):
            pid = str(proj.get("project_id", ""))
            status = str(proj.get("status", "")).strip()
            physical_progress = float(proj.get("physical_progress_pct", 0.0) or 0.0)
            expenditure = float(proj.get("expenditure_lakh", 0.0) or 0.0)
            sanctioned = float(proj.get("sanctioned_amount_lakh", 0.0) or 0.0)

            p_comp = comp_map.get(pid, {})
            p_ev = ev_map.get(pid, set())

            missing_docs = []

            # 1. Sanction
            if sanctioned > 0 and str(p_comp.get("Sanction Order", {}).get("status", "")).strip().lower() == "missing" and "Sanction Document" not in p_ev:
                missing_docs.append("Sanction Order")

            # 2. Progress
            if physical_progress > 0 and str(p_comp.get("Progress Update", {}).get("status", "")).strip().lower() == "missing" and "Progress Photo" not in p_ev:
                missing_docs.append("Progress Update")

            # 3. Inspection
            if (physical_progress >= 40.0 or status.lower() == "completed") and str(p_comp.get("Inspection Report", {}).get("status", "")).strip().lower() == "missing" and "Inspection Report" not in p_ev:
                missing_docs.append("Inspection Report")

            # 4. Payment
            if expenditure > 0 and str(p_comp.get("Payment Support", {}).get("status", "")).strip().lower() == "missing" and "Payment Document" not in p_ev:
                missing_docs.append("Payment Support")

            # 5. Completion
            if (status.lower() == "completed" or physical_progress >= 100.0) and str(p_comp.get("Completion Certificate", {}).get("status", "")).strip().lower() == "missing" and "Completion Certificate" not in p_ev:
                missing_docs.append("Completion Certificate")

            if len(missing_docs) >= 2:
                severity = SeverityEnum.HIGH if len(missing_docs) >= 3 else SeverityEnum.MEDIUM
                confidence = 0.92

                evidence = {
                    "missing_document_count": len(missing_docs),
                    "missing_documents": missing_docs,
                    "project_status": status,
                    "physical_progress_pct": round(physical_progress, 2),
                    "expenditure_lakh": round(expenditure, 2),
                }

                explanation = (
                    f"Multiple compliance documentation gaps: {len(missing_docs)} mandatory documents "
                    f"are missing ({', '.join(missing_docs)})."
                )

                results.append(AnomalyResult(
                    project_id=pid,
                    anomaly_type=AnomalyTypeEnum.COMPLIANCE_DOCUMENT_GAP,
                    severity=severity,
                    confidence=confidence,
                    evidence=evidence,
                    explanation=explanation,
                ))

        return results
