from typing import Any, Dict, List, Optional
import pandas as pd
from app.anomaly_engine.models import (
    AnomalyResult,
    AnomalyTypeEnum,
    SeverityEnum,
    ThresholdConfig,
)


class ExpenditureExceedsSanctionRule:
    """
    Rule 1 (Financial): Detects projects where actual expenditure exceeds the approved sanctioned limit.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(self, project_row: Dict[str, Any]) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        sanctioned_amount = float(project_row.get("sanctioned_amount_lakh", 0.0) or 0.0)
        expenditure = float(project_row.get("expenditure_lakh", 0.0) or 0.0)

        if sanctioned_amount <= 0:
            return None

        excess_amount = round(expenditure - sanctioned_amount, 2)
        if excess_amount > self.config.expenditure_excess_tolerance_lakh:
            excess_pct = round((excess_amount / sanctioned_amount) * 100, 2)

            if excess_pct >= self.config.expenditure_critical_excess_pct or excess_amount >= 10.0:
                severity = SeverityEnum.CRITICAL
                confidence = 0.98
            elif excess_pct >= self.config.expenditure_high_excess_pct or excess_amount >= 5.0:
                severity = SeverityEnum.HIGH
                confidence = 0.95
            elif excess_pct >= 2.0:
                severity = SeverityEnum.MEDIUM
                confidence = 0.90
            else:
                severity = SeverityEnum.LOW
                confidence = 0.85

            evidence = {
                "sanctioned_amount_lakh": round(sanctioned_amount, 2),
                "expenditure_lakh": round(expenditure, 2),
                "excess_amount_lakh": excess_amount,
                "excess_pct": excess_pct,
                "tolerance_lakh": self.config.expenditure_excess_tolerance_lakh,
            }

            explanation = (
                f"Total expenditure of ₹{expenditure:.2f} Lakh exceeds the sanctioned limit of "
                f"₹{sanctioned_amount:.2f} Lakh by ₹{excess_amount:.2f} Lakh ({excess_pct:.2f}% excess)."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.EXPENDITURE_EXCEEDS_SANCTION,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(self, projects_df: pd.DataFrame) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        for row in projects_df.to_dict(orient="records"):
            anomaly = self.evaluate_project(row)
            if anomaly:
                results.append(anomaly)
        return results


class AbnormallyHighUtilizationRule:
    """
    Rule 3 (Financial): Detects projects where fund utilization is disproportionately high (>90%)
    while physical progress remains low (<50%), or where funds are overdrawn (>100%).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        financial_row: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        sanctioned_amount = float(project_row.get("sanctioned_amount_lakh", 0.0) or 0.0)
        expenditure = float(project_row.get("expenditure_lakh", 0.0) or 0.0)
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)

        if sanctioned_amount <= 0:
            return None

        utilization_pct = round((expenditure / sanctioned_amount) * 100, 2)
        if financial_row and "utilization_pct" in financial_row and financial_row["utilization_pct"] is not None:
            try:
                utilization_pct = float(financial_row["utilization_pct"])
            except (ValueError, TypeError):
                pass

        is_over_utilized = utilization_pct > self.config.over_utilization_ceiling_pct
        is_high_lagging = (
            utilization_pct >= self.config.high_utilization_threshold_pct
            and physical_progress < self.config.high_utilization_physical_lag_pct
        )

        if is_over_utilized or is_high_lagging:
            if is_over_utilized or (utilization_pct >= 95.0 and physical_progress <= 30.0):
                severity = SeverityEnum.CRITICAL
                confidence = 0.95
            elif utilization_pct >= 90.0 and physical_progress <= 40.0:
                severity = SeverityEnum.HIGH
                confidence = 0.90
            else:
                severity = SeverityEnum.MEDIUM
                confidence = 0.85

            evidence = {
                "utilization_pct": round(utilization_pct, 2),
                "physical_progress_pct": round(physical_progress, 2),
                "expenditure_lakh": round(expenditure, 2),
                "sanctioned_amount_lakh": round(sanctioned_amount, 2),
                "is_over_utilized": is_over_utilized,
                "high_utilization_threshold_pct": self.config.high_utilization_threshold_pct,
                "physical_lag_threshold_pct": self.config.high_utilization_physical_lag_pct,
            }

            explanation = (
                f"Abnormally high fund utilization ({utilization_pct:.2f}%) detected while physical progress "
                f"stands at only {physical_progress:.2f}% (₹{expenditure:.2f}L of ₹{sanctioned_amount:.2f}L utilized)."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.ABNORMALLY_HIGH_UTILIZATION,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        fin_map: Dict[str, Dict[str, Any]] = {}
        if financials_df is not None and not financials_df.empty:
            for r in financials_df.to_dict(orient="records"):
                fin_map[str(r["project_id"])] = r

        for proj_dict in projects_df.to_dict(orient="records"):
            pid = str(proj_dict.get("project_id", ""))
            anomaly = self.evaluate_project(proj_dict, fin_map.get(pid))
            if anomaly:
                results.append(anomaly)

        return results


class AbnormallyLowUtilizationRule:
    """
    Rule 4 (Financial): Detects stalled projects where planned timeline or progress has advanced (>=50%),
    but fund utilization remains abnormally low (<=15%).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        financial_row: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        sanctioned_amount = float(project_row.get("sanctioned_amount_lakh", 0.0) or 0.0)
        expenditure = float(project_row.get("expenditure_lakh", 0.0) or 0.0)
        planned_progress = float(project_row.get("planned_progress_pct", 0.0) or 0.0)
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)
        status = str(project_row.get("status", ""))

        if sanctioned_amount <= 0:
            return None

        utilization_pct = round((expenditure / sanctioned_amount) * 100, 2)
        if financial_row and "utilization_pct" in financial_row and financial_row["utilization_pct"] is not None:
            try:
                utilization_pct = float(financial_row["utilization_pct"])
            except (ValueError, TypeError):
                pass

        is_low_utilization = (
            planned_progress >= self.config.low_utilization_planned_progress_min_pct
            and utilization_pct <= self.config.low_utilization_threshold_pct
        )

        if is_low_utilization:
            if planned_progress >= 75.0 and utilization_pct <= 10.0:
                severity = SeverityEnum.HIGH
                confidence = 0.90
            elif planned_progress >= 50.0 and utilization_pct <= 15.0:
                severity = SeverityEnum.MEDIUM
                confidence = 0.85
            else:
                severity = SeverityEnum.LOW
                confidence = 0.80

            evidence = {
                "utilization_pct": round(utilization_pct, 2),
                "planned_progress_pct": round(planned_progress, 2),
                "physical_progress_pct": round(physical_progress, 2),
                "expenditure_lakh": round(expenditure, 2),
                "sanctioned_amount_lakh": round(sanctioned_amount, 2),
                "status": status,
                "low_utilization_threshold_pct": self.config.low_utilization_threshold_pct,
                "min_planned_progress_pct": self.config.low_utilization_planned_progress_min_pct,
            }

            explanation = (
                f"Fund utilization is severely lagging at {utilization_pct:.2f}% (₹{expenditure:.2f}L of ₹{sanctioned_amount:.2f}L) "
                f"despite planned progress reaching {planned_progress:.2f}% (physical progress: {physical_progress:.2f}%)."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.ABNORMALLY_LOW_UTILIZATION,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        fin_map: Dict[str, Dict[str, Any]] = {}
        if financials_df is not None and not financials_df.empty:
            for r in financials_df.to_dict(orient="records"):
                fin_map[str(r["project_id"])] = r

        for proj_dict in projects_df.to_dict(orient="records"):
            pid = str(proj_dict.get("project_id", ""))
            anomaly = self.evaluate_project(proj_dict, fin_map.get(pid))
            if anomaly:
                results.append(anomaly)

        return results


class ProgressFinancialMismatchRule:
    """
    Rule 5 (Financial): Detects substantial divergence where financial expenditure percentage
    substantially outpaces verified physical completion progress (gap >= 35%).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(self, project_row: Dict[str, Any]) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        sanctioned_amount = float(project_row.get("sanctioned_amount_lakh", 0.0) or 0.0)
        expenditure = float(project_row.get("expenditure_lakh", 0.0) or 0.0)
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)
        planned_progress = float(project_row.get("planned_progress_pct", 0.0) or 0.0)

        if sanctioned_amount <= 0:
            return None

        financial_progress_pct = round((expenditure / sanctioned_amount) * 100, 2)
        progress_gap_pct = round(financial_progress_pct - physical_progress, 2)

        if progress_gap_pct >= self.config.progress_mismatch_gap_pct:
            if progress_gap_pct >= self.config.progress_mismatch_critical_gap_pct:
                severity = SeverityEnum.CRITICAL
                confidence = 0.95
            elif progress_gap_pct >= self.config.progress_mismatch_high_gap_pct:
                severity = SeverityEnum.HIGH
                confidence = 0.90
            elif progress_gap_pct >= self.config.progress_mismatch_gap_pct:
                severity = SeverityEnum.MEDIUM
                confidence = 0.85
            else:
                severity = SeverityEnum.LOW
                confidence = 0.80

            evidence = {
                "financial_progress_pct": financial_progress_pct,
                "physical_progress_pct": round(physical_progress, 2),
                "progress_gap_pct": progress_gap_pct,
                "planned_progress_pct": round(planned_progress, 2),
                "expenditure_lakh": round(expenditure, 2),
                "sanctioned_amount_lakh": round(sanctioned_amount, 2),
                "mismatch_threshold_pct": self.config.progress_mismatch_gap_pct,
            }

            explanation = (
                f"Significant progress mismatch: financial progress ({financial_progress_pct:.2f}%) "
                f"outpaces physical progress ({physical_progress:.2f}%) by a gap of {progress_gap_pct:.2f}%."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.PROGRESS_FINANCIAL_MISMATCH,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(self, projects_df: pd.DataFrame) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        for row in projects_df.to_dict(orient="records"):
            anomaly = self.evaluate_project(row)
            if anomaly:
                results.append(anomaly)
        return results


class UnusualExpenditurePatternRule:
    """
    Rule 6 (Financial): Detects extreme single-payment concentration (>=60% of total payments)
    or disproportionate early-stage disbursements.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_id: str,
        project_row: Optional[Dict[str, Any]],
        payments_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        if not payments_rows:
            return None

        total_pmt = sum(float(p.get("amount_lakh", 0.0) or 0.0) for p in payments_rows)
        if total_pmt <= 0:
            return None

        max_pmt_record = max(payments_rows, key=lambda p: float(p.get("amount_lakh", 0.0) or 0.0))
        max_pmt_amount = float(max_pmt_record.get("amount_lakh", 0.0) or 0.0)
        max_pmt_share_pct = round((max_pmt_amount / total_pmt) * 100, 2)
        payment_stage = str(max_pmt_record.get("payment_stage", "Unknown"))
        payment_id = str(max_pmt_record.get("payment_id", "Unknown"))
        payment_date = str(max_pmt_record.get("payment_date", "Unknown"))

        is_early_stage = payment_stage in ["Mobilization", "Foundation"]
        meets_threshold = (
            max_pmt_share_pct >= self.config.single_payment_concentration_pct
            or (max_pmt_share_pct >= self.config.early_stage_concentration_pct and is_early_stage)
        )

        if meets_threshold:
            if max_pmt_share_pct >= 75.0 or (max_pmt_share_pct >= 65.0 and is_early_stage):
                severity = SeverityEnum.CRITICAL
                confidence = 0.94
            elif max_pmt_share_pct >= 60.0:
                severity = SeverityEnum.HIGH
                confidence = 0.90
            else:
                severity = SeverityEnum.MEDIUM
                confidence = 0.85

            evidence = {
                "max_single_payment_id": payment_id,
                "max_single_payment_lakh": round(max_pmt_amount, 2),
                "total_project_payments_lakh": round(total_pmt, 2),
                "single_payment_share_pct": max_pmt_share_pct,
                "payment_stage": payment_stage,
                "payment_date": payment_date,
                "total_payment_installments": len(payments_rows),
                "concentration_threshold_pct": self.config.single_payment_concentration_pct,
            }

            explanation = (
                f"Unusual payment concentration: single transaction ({payment_id}) of ₹{max_pmt_amount:.2f} Lakh "
                f"represents {max_pmt_share_pct:.2f}% of all payments released to the project at stage '{payment_stage}'."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.UNUSUAL_EXPENDITURE_PATTERN,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        payments_df: pd.DataFrame,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if payments_df.empty:
            return results

        grouped_payments: Dict[str, List[Dict[str, Any]]] = {}
        for r in payments_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped_payments:
                grouped_payments[pid] = []
            grouped_payments[pid].append(r)

        proj_map = {str(row["project_id"]): row for row in projects_df.to_dict(orient="records")}

        for pid, pmt_list in grouped_payments.items():
            proj_dict = proj_map.get(pid)
            anomaly = self.evaluate_project(pid, proj_dict, pmt_list)
            if anomaly:
                results.append(anomaly)

        return results
