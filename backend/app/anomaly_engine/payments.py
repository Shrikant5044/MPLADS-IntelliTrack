from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from app.anomaly_engine.models import (
    AnomalyResult,
    AnomalyTypeEnum,
    SeverityEnum,
    ThresholdConfig,
)


def parse_date(date_val: Any) -> Optional[datetime]:
    """Fast date parsing for YYYY-MM-DD and DD-MM-YYYY strings."""
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


class LargePaymentRule:
    """
    Rule 1 (Payment): Detects exceptionally large single disbursements (>=60% of total payments
    or absolute tranche >= ₹25.0 Lakh).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_id: str,
        payments_rows: List[Dict[str, Any]],
        project_row: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnomalyResult]:
        if not payments_rows:
            return None

        total_paid = sum(float(p.get("amount_lakh", 0.0) or 0.0) for p in payments_rows)
        if total_paid <= 0:
            return None

        max_pmt = max(payments_rows, key=lambda p: float(p.get("amount_lakh", 0.0) or 0.0))
        max_amt = float(max_pmt.get("amount_lakh", 0.0) or 0.0)
        share_pct = round((max_amt / total_paid) * 100, 2)
        pmt_id = str(max_pmt.get("payment_id", "Unknown"))
        pmt_stage = str(max_pmt.get("payment_stage", "Unknown"))
        pmt_date = str(max_pmt.get("payment_date", "Unknown"))

        is_large_share = share_pct >= self.config.large_payment_share_threshold_pct
        is_large_amt = max_amt >= self.config.large_payment_amount_lakh

        if is_large_share or is_large_amt:
            if share_pct >= 75.0 or max_amt >= 35.0:
                severity = SeverityEnum.CRITICAL
                confidence = 0.95
            elif share_pct >= 65.0 or max_amt >= 28.0:
                severity = SeverityEnum.HIGH
                confidence = 0.90
            else:
                severity = SeverityEnum.MEDIUM
                confidence = 0.85

            evidence = {
                "largest_payment_id": str(pmt_id),
                "largest_payment_amount_lakh": round(max_amt, 2),
                "total_payments_lakh": round(total_paid, 2),
                "payment_share_pct": float(share_pct),
                "payment_stage": str(pmt_stage),
                "payment_date": str(pmt_date),
                "share_threshold_pct": float(self.config.large_payment_share_threshold_pct),
            }

            explanation = (
                f"Disproportionately large single disbursement: payment {pmt_id} of ₹{max_amt:.2f} Lakh "
                f"constitutes {share_pct:.2f}% of all payments released to project ({pmt_stage} stage on {pmt_date})."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.LARGE_PAYMENT,
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

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in payments_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for pid, p_list in grouped.items():
            anomaly = self.evaluate_project(pid, p_list)
            if anomaly:
                results.append(anomaly)

        return results


class RapidMultiplePaymentsRule:
    """
    Rule 2 (Payment): Detects abnormal bursts of payments in rapid succession (>=3 payments within <=5 days
    or same-day multiple high-value disbursements).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_id: str,
        payments_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        if len(payments_rows) < 2:
            return None

        sorted_pmts = sorted(
            payments_rows,
            key=lambda x: parse_date(x.get("payment_date")) or datetime.min,
        )

        # Check rolling 3 payments within window
        rapid_burst: Optional[List[Dict[str, Any]]] = None
        min_burst_days: int = 999

        if len(sorted_pmts) >= self.config.rapid_payment_min_count:
            for i in range(len(sorted_pmts) - self.config.rapid_payment_min_count + 1):
                window_slice = sorted_pmts[i : i + self.config.rapid_payment_min_count]
                d_start = parse_date(window_slice[0].get("payment_date"))
                d_end = parse_date(window_slice[-1].get("payment_date"))
                if d_start and d_end:
                    gap = (d_end - d_start).days
                    if 0 <= gap <= self.config.rapid_payment_window_days and gap < min_burst_days:
                        min_burst_days = gap
                        rapid_burst = window_slice

        # Also check same-day duplicate disbursement of significant value (>= ₹5.0L)
        same_day_pair: Optional[tuple[Dict[str, Any], Dict[str, Any]]] = None
        for i in range(1, len(sorted_pmts)):
            p1, p2 = sorted_pmts[i - 1], sorted_pmts[i]
            d1, d2 = parse_date(p1.get("payment_date")), parse_date(p2.get("payment_date"))
            amt1, amt2 = float(p1.get("amount_lakh", 0.0) or 0.0), float(p2.get("amount_lakh", 0.0) or 0.0)
            if d1 and d2 and (d2 - d1).days == 0 and (amt1 + amt2) >= 5.0:
                same_day_pair = (p1, p2)
                break

        if rapid_burst:
            total_burst_amt = sum(float(p.get("amount_lakh", 0.0) or 0.0) for p in rapid_burst)
            pmt_ids = [str(p.get("payment_id")) for p in rapid_burst]
            dates_str = f"{rapid_burst[0].get('payment_date')} to {rapid_burst[-1].get('payment_date')}"

            severity = SeverityEnum.HIGH if min_burst_days <= 2 else SeverityEnum.MEDIUM
            confidence = 0.90

            evidence = {
                "burst_payment_count": len(rapid_burst),
                "days_span": int(min_burst_days),
                "total_burst_amount_lakh": round(total_burst_amt, 2),
                "payment_ids": pmt_ids,
                "date_range": dates_str,
                "window_threshold_days": int(self.config.rapid_payment_window_days),
            }

            explanation = (
                f"Rapid multiple payments: {len(rapid_burst)} separate transactions totaling ₹{total_burst_amt:.2f} Lakh "
                f"were processed within {min_burst_days} days ({dates_str})."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.RAPID_MULTIPLE_PAYMENTS,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        elif same_day_pair:
            p1, p2 = same_day_pair
            amt1, amt2 = float(p1.get("amount_lakh", 0.0) or 0.0), float(p2.get("amount_lakh", 0.0) or 0.0)
            evidence = {
                "first_payment_id": str(p1.get("payment_id")),
                "second_payment_id": str(p2.get("payment_id")),
                "payment_date": str(p1.get("payment_date")),
                "combined_amount_lakh": round(amt1 + amt2, 2),
            }
            explanation = (
                f"Same-day payment splitting: multiple transactions ({p1.get('payment_id')}, {p2.get('payment_id')}) "
                f"totaling ₹{amt1+amt2:.2f} Lakh were executed on the same date ({p1.get('payment_date')})."
            )
            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.RAPID_MULTIPLE_PAYMENTS,
                severity=SeverityEnum.MEDIUM,
                confidence=0.86,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(self, payments_df: pd.DataFrame) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if payments_df.empty:
            return results

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in payments_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for pid, p_list in grouped.items():
            anomaly = self.evaluate_project(pid, p_list)
            if anomaly:
                results.append(anomaly)

        return results


class RepeatedPaymentAmountRule:
    """
    Rule 3 (Payment): Detects repeated identical payment amounts of significant value (>= ₹5.0 Lakh)
    for the same project.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_id: str,
        payments_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        if len(payments_rows) < 2:
            return None

        # Filter payments meeting minimum value threshold (>= 5.0L) to avoid minor retainers
        significant_pmts = [
            p for p in payments_rows
            if float(p.get("amount_lakh", 0.0) or 0.0) >= self.config.repeated_amount_min_value_lakh
        ]

        amount_counts: Dict[float, List[Dict[str, Any]]] = {}
        for p in significant_pmts:
            amt = round(float(p.get("amount_lakh", 0.0) or 0.0), 2)
            if amt not in amount_counts:
                amount_counts[amt] = []
            amount_counts[amt].append(p)

        dup_sets = {amt: pmts for amt, pmts in amount_counts.items() if len(pmts) >= self.config.repeated_amount_min_count}
        if dup_sets:
            repeated_amt = max(dup_sets.keys())
            matched_pmts = dup_sets[repeated_amt]
            count = len(matched_pmts)
            pmt_ids = [str(p.get("payment_id")) for p in matched_pmts]

            if count >= 3 or repeated_amt >= 10.0:
                severity = SeverityEnum.HIGH
                confidence = 0.94
            else:
                severity = SeverityEnum.MEDIUM
                confidence = 0.88

            evidence = {
                "repeated_amount_lakh": float(repeated_amt),
                "repetition_count": int(count),
                "payment_ids": pmt_ids,
                "payment_dates": [str(p.get("payment_date")) for p in matched_pmts],
                "min_value_threshold_lakh": float(self.config.repeated_amount_min_value_lakh),
            }

            explanation = (
                f"Repeated identical high-value payment amounts: exactly ₹{repeated_amt:.2f} Lakh disbursed {count} times "
                f"across transactions ({', '.join(pmt_ids[:3])})."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.REPEATED_PAYMENT_AMOUNT,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(self, payments_df: pd.DataFrame) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if payments_df.empty:
            return results

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in payments_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for pid, p_list in grouped.items():
            anomaly = self.evaluate_project(pid, p_list)
            if anomaly:
                results.append(anomaly)

        return results


class PaymentBeforeMilestoneRule:
    """
    Rule 4 (Payment): Detects advanced stage payments (Final, Finishing) released prematurely
    while ground physical progress remains lagging (<=25%).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        payments_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)

        if not payments_rows:
            return None

        # Check for Final or Finishing payments when physical progress is lagging
        advanced_pmts = [
            p for p in payments_rows
            if str(p.get("payment_stage", "")).strip() in ["Final", "Finishing"]
        ]

        if advanced_pmts:
            latest_adv = advanced_pmts[-1]
            stage = str(latest_adv.get("payment_stage"))
            amt = float(latest_adv.get("amount_lakh", 0.0) or 0.0)
            pmt_id = str(latest_adv.get("payment_id"))
            pmt_date = str(latest_adv.get("payment_date"))

            # Stricter condition for Final vs Finishing
            is_anomaly = (
                (stage == "Final" and physical_progress < self.config.payment_before_milestone_physical_threshold_pct)
                or (stage == "Finishing" and physical_progress < 15.0)
            )

            if is_anomaly:
                severity = SeverityEnum.CRITICAL if stage == "Final" else SeverityEnum.HIGH
                confidence = 0.94

                evidence = {
                    "premature_payment_id": str(pmt_id),
                    "payment_stage": str(stage),
                    "payment_amount_lakh": round(amt, 2),
                    "payment_date": str(pmt_date),
                    "physical_progress_pct": round(physical_progress, 2),
                    "required_physical_threshold_pct": float(self.config.payment_before_milestone_physical_threshold_pct),
                }

                explanation = (
                    f"Premature milestone disbursement: '{stage}' stage payment {pmt_id} of ₹{amt:.2f} Lakh released on "
                    f"{pmt_date} while ground physical progress has only reached {physical_progress:.2f}%."
                )

                return AnomalyResult(
                    project_id=project_id,
                    anomaly_type=AnomalyTypeEnum.PAYMENT_BEFORE_MILESTONE,
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
        if payments_df.empty or projects_df.empty:
            return results

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in payments_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for proj_row in projects_df.to_dict(orient="records"):
            pid = str(proj_row.get("project_id", ""))
            anomaly = self.evaluate_project(proj_row, grouped.get(pid, []))
            if anomaly:
                results.append(anomaly)

        return results


class PaymentLowProgressRule:
    """
    Rule 5 (Payment): Detects projects where a substantial portion of funds (>=40%)
    has been disbursed while physical progress remains severely low (<15%).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        payments_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        sanctioned = float(project_row.get("sanctioned_amount_lakh", 0.0) or 0.0)
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)

        if sanctioned <= 0 or not payments_rows:
            return None

        total_paid = sum(float(p.get("amount_lakh", 0.0) or 0.0) for p in payments_rows)
        paid_pct = round((total_paid / sanctioned) * 100, 2)

        if paid_pct >= self.config.payment_low_progress_paid_pct and physical_progress < self.config.payment_low_progress_physical_pct:
            severity = SeverityEnum.CRITICAL if paid_pct >= 50.0 else SeverityEnum.HIGH
            confidence = 0.95

            evidence = {
                "total_paid_lakh": round(total_paid, 2),
                "sanctioned_amount_lakh": round(sanctioned, 2),
                "paid_pct": float(paid_pct),
                "physical_progress_pct": round(physical_progress, 2),
                "payment_threshold_pct": float(self.config.payment_low_progress_paid_pct),
                "physical_progress_max_pct": float(self.config.payment_low_progress_physical_pct),
            }

            explanation = (
                f"Severe fund drawdown with lagging progress: ₹{total_paid:.2f} Lakh ({paid_pct:.2f}% of sanctioned funds) "
                f"has been disbursed while physical progress is only {physical_progress:.2f}%."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.PAYMENT_LOW_PROGRESS,
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
        if payments_df.empty or projects_df.empty:
            return results

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in payments_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for proj_row in projects_df.to_dict(orient="records"):
            pid = str(proj_row.get("project_id", ""))
            anomaly = self.evaluate_project(proj_row, grouped.get(pid, []))
            if anomaly:
                results.append(anomaly)

        return results


class DeadlinePaymentConcentrationRule:
    """
    Rule 6 (Payment): Detects unusually high payment concentration (>=50%) close to or past
    the expected completion date on ONGOING / INCOMPLETE projects only.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        payments_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        status = str(project_row.get("status", "")).strip()
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)
        expected_comp_str = project_row.get("expected_completion_date")

        # Exclude completed projects with 100% progress (normal final settlements)
        if status.lower() == "completed" or physical_progress >= 100.0:
            return None

        if not payments_rows or not expected_comp_str:
            return None

        exp_date = parse_date(expected_comp_str)
        if not exp_date:
            return None

        total_paid = sum(float(p.get("amount_lakh", 0.0) or 0.0) for p in payments_rows)
        if total_paid <= 0:
            return None

        near_deadline_pmts = []
        for p in payments_rows:
            p_date = parse_date(p.get("payment_date"))
            if p_date:
                days_diff = (exp_date - p_date).days
                # Payment within 20 days prior to deadline or after deadline
                if -10 <= days_diff <= self.config.deadline_payment_window_days or p_date >= exp_date:
                    near_deadline_pmts.append(p)

        near_amt = sum(float(p.get("amount_lakh", 0.0) or 0.0) for p in near_deadline_pmts)
        near_share_pct = round((near_amt / total_paid) * 100, 2)

        if near_share_pct >= self.config.deadline_payment_share_threshold_pct and len(near_deadline_pmts) > 0:
            if near_share_pct >= 65.0:
                severity = SeverityEnum.CRITICAL
                confidence = 0.94
            elif near_share_pct >= 50.0:
                severity = SeverityEnum.HIGH
                confidence = 0.88
            else:
                severity = SeverityEnum.MEDIUM
                confidence = 0.82

            evidence = {
                "expected_completion_date": str(expected_comp_str),
                "near_deadline_payments_count": int(len(near_deadline_pmts)),
                "near_deadline_amount_lakh": round(near_amt, 2),
                "total_project_payments_lakh": round(total_paid, 2),
                "near_deadline_share_pct": float(near_share_pct),
                "status": str(status),
                "window_days": int(self.config.deadline_payment_window_days),
            }

            explanation = (
                f"Deadline payment concentration on ongoing project: ₹{near_amt:.2f} Lakh ({near_share_pct:.2f}% of all payments) "
                f"disbursed in proximity to completion deadline ({expected_comp_str}) while project remains incomplete."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.DEADLINE_PAYMENT_CONCENTRATION,
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
        if payments_df.empty or projects_df.empty:
            return results

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in payments_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for proj_row in projects_df.to_dict(orient="records"):
            pid = str(proj_row.get("project_id", ""))
            anomaly = self.evaluate_project(proj_row, grouped.get(pid, []))
            if anomaly:
                results.append(anomaly)

        return results
