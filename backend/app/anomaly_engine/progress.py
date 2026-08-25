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


class ProjectDelayRule:
    """
    Rule 1 (Progress): Detects ongoing or incomplete projects whose expected completion date
    has passed by >=15 days relative to the reference snapshot date, or projects marked as Delayed.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        ref_date: Optional[datetime] = None,
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        status = str(project_row.get("status", "")).strip()
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)
        expected_comp_str = project_row.get("expected_completion_date")

        if status.lower() == "completed" or physical_progress >= 100.0:
            return None

        exp_date = parse_date(expected_comp_str)
        if not exp_date:
            return None

        current_ref = ref_date or parse_date(self.config.reference_date_str) or datetime(2026, 8, 23)
        days_delayed = (current_ref - exp_date).days

        is_delayed = days_delayed >= self.config.project_delay_medium_days or status.lower() == "delayed"

        if is_delayed:
            effective_delay_days = max(days_delayed, 1)

            if effective_delay_days >= self.config.project_delay_critical_days or (status.lower() == "delayed" and effective_delay_days >= 45):
                severity = SeverityEnum.CRITICAL
                confidence = 0.96
            elif effective_delay_days >= self.config.project_delay_high_days:
                severity = SeverityEnum.HIGH
                confidence = 0.92
            else:
                severity = SeverityEnum.MEDIUM
                confidence = 0.88

            evidence = {
                "status": status,
                "expected_completion_date": str(expected_comp_str),
                "reference_date": current_ref.strftime("%Y-%m-%d"),
                "days_delayed": int(days_delayed),
                "physical_progress_pct": round(physical_progress, 2),
            }

            delay_desc = f"{days_delayed} days overdue" if days_delayed > 0 else f"marked as '{status}'"
            explanation = (
                f"Project timeline delay: project is {delay_desc} past expected deadline "
                f"({expected_comp_str}) while physical progress is only {physical_progress:.2f}%."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.PROJECT_DELAY,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        ref_date: Optional[datetime] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        for row in projects_df.to_dict(orient="records"):
            anomaly = self.evaluate_project(row, ref_date)
            if anomaly:
                results.append(anomaly)
        return results


class SlowProgressRule:
    """
    Rule 2 (Progress): Detects projects whose physical progress substantially lags (>=30%)
    behind the planned cumulative schedule target.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(self, project_row: Dict[str, Any]) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        planned_progress = float(project_row.get("planned_progress_pct", 0.0) or 0.0)
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)
        status = str(project_row.get("status", ""))

        if status.lower() == "completed" and physical_progress >= 100.0:
            return None

        progress_lag = round(planned_progress - physical_progress, 2)

        if progress_lag >= self.config.slow_progress_threshold_pct:
            if progress_lag >= self.config.slow_progress_critical_pct:
                severity = SeverityEnum.CRITICAL
                confidence = 0.95
            elif progress_lag >= self.config.slow_progress_high_pct:
                severity = SeverityEnum.HIGH
                confidence = 0.90
            else:
                severity = SeverityEnum.MEDIUM
                confidence = 0.85

            evidence = {
                "planned_progress_pct": round(planned_progress, 2),
                "physical_progress_pct": round(physical_progress, 2),
                "progress_lag_pct": float(progress_lag),
                "status": str(status),
                "lag_threshold_pct": float(self.config.slow_progress_threshold_pct),
            }

            explanation = (
                f"Substantial schedule lag: reported physical progress ({physical_progress:.2f}%) "
                f"is {progress_lag:.2f}% below the planned milestone target ({planned_progress:.2f}%)."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.SLOW_PROGRESS,
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


class NoRecentProgressUpdateRule:
    """
    Rule 3 (Progress): Detects active/ongoing projects that have had no progress updates
    recorded for >=90 days (quarterly monitoring dormancy).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        progress_rows: List[Dict[str, Any]],
        ref_date: Optional[datetime] = None,
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        status = str(project_row.get("status", "")).strip()

        if status.lower() == "completed":
            return None

        current_ref = ref_date or parse_date(self.config.reference_date_str) or datetime(2026, 8, 23)

        if not progress_rows:
            evidence = {
                "status": status,
                "total_updates_count": 0,
                "reference_date": current_ref.strftime("%Y-%m-%d"),
                "threshold_days": int(self.config.no_update_threshold_days),
            }
            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.NO_RECENT_PROGRESS_UPDATE,
                severity=SeverityEnum.HIGH,
                confidence=0.90,
                evidence=evidence,
                explanation=f"No progress updates have ever been recorded for active project '{project_id}'.",
            )

        valid_dates = [parse_date(p.get("update_date")) for p in progress_rows if parse_date(p.get("update_date"))]
        if not valid_dates:
            return None

        latest_date = max(valid_dates)
        days_since_update = (current_ref - latest_date).days

        if days_since_update >= self.config.no_update_threshold_days:
            severity = SeverityEnum.HIGH if days_since_update >= self.config.no_update_critical_days else SeverityEnum.MEDIUM
            confidence = 0.90 if days_since_update >= self.config.no_update_critical_days else 0.85

            evidence = {
                "last_update_date": latest_date.strftime("%Y-%m-%d"),
                "reference_date": current_ref.strftime("%Y-%m-%d"),
                "days_since_last_update": int(days_since_update),
                "status": str(status),
                "threshold_days": int(self.config.no_update_threshold_days),
            }

            explanation = (
                f"Progress monitoring dormancy: no progress update has been filed for {days_since_update} days "
                f"(last update on {latest_date.strftime('%Y-%m-%d')}), exceeding the {self.config.no_update_threshold_days}-day limit."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.NO_RECENT_PROGRESS_UPDATE,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        progress_df: pd.DataFrame,
        ref_date: Optional[datetime] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []

        grouped_progress: Dict[str, List[Dict[str, Any]]] = {}
        if not progress_df.empty:
            for r in progress_df.to_dict(orient="records"):
                pid = str(r["project_id"])
                if pid not in grouped_progress:
                    grouped_progress[pid] = []
                grouped_progress[pid].append(r)

        for proj_row in projects_df.to_dict(orient="records"):
            pid = str(proj_row.get("project_id", ""))
            anomaly = self.evaluate_project(proj_row, grouped_progress.get(pid, []), ref_date)
            if anomaly:
                results.append(anomaly)

        return results


class SuddenProgressJumpRule:
    """
    Rule 4 (Progress): Detects abrupt surges in reported physical progress (>=35% jump)
    between consecutive periodic updates.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_id: str,
        progress_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        if len(progress_rows) < 2:
            return None

        sorted_updates = sorted(
            progress_rows,
            key=lambda x: parse_date(x.get("update_date")) or datetime.min,
        )

        max_jump = 0.0
        jump_record_prev: Optional[Dict[str, Any]] = None
        jump_record_curr: Optional[Dict[str, Any]] = None

        for i in range(1, len(sorted_updates)):
            prev_update = sorted_updates[i - 1]
            curr_update = sorted_updates[i]

            prev_prog = float(prev_update.get("physical_progress_pct", 0.0) or 0.0)
            curr_prog = float(curr_update.get("physical_progress_pct", 0.0) or 0.0)

            diff = round(curr_prog - prev_prog, 2)
            if diff > max_jump:
                max_jump = diff
                jump_record_prev = prev_update
                jump_record_curr = curr_update

        if max_jump >= self.config.sudden_progress_jump_threshold_pct and jump_record_prev and jump_record_curr:
            prev_d = str(jump_record_prev.get("update_date", ""))
            curr_d = str(jump_record_curr.get("update_date", ""))
            prev_val = float(jump_record_prev.get("physical_progress_pct", 0.0) or 0.0)
            curr_val = float(jump_record_curr.get("physical_progress_pct", 0.0) or 0.0)
            milestone = str(jump_record_curr.get("milestone", "Unknown"))

            severity = SeverityEnum.CRITICAL if max_jump >= self.config.sudden_progress_jump_critical_pct else SeverityEnum.HIGH
            confidence = 0.94

            evidence = {
                "from_update_date": prev_d,
                "to_update_date": curr_d,
                "previous_physical_progress_pct": prev_val,
                "current_physical_progress_pct": curr_val,
                "progress_jump_pct": float(max_jump),
                "milestone": milestone,
                "threshold_pct": float(self.config.sudden_progress_jump_threshold_pct),
            }

            explanation = (
                f"Abrupt physical progress surge: reported physical progress jumped by {max_jump:.2f}% "
                f"(from {prev_val:.2f}% on {prev_d} to {curr_val:.2f}% on {curr_d}) during milestone '{milestone}'."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.SUDDEN_PROGRESS_JUMP,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        progress_df: pd.DataFrame,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if progress_df.empty:
            return results

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in progress_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for pid, p_list in grouped.items():
            anomaly = self.evaluate_project(pid, p_list)
            if anomaly:
                results.append(anomaly)

        return results


class MilestoneLagRule:
    """
    Rule 5 (Progress): Detects milestone-specific execution bottlenecks where physical progress
    in late-stage milestones (Finishing, Execution, Completion) lags planned milestone targets (>=30%).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_id: str,
        progress_rows: List[Dict[str, Any]],
    ) -> Optional[AnomalyResult]:
        if not progress_rows:
            return None

        sorted_updates = sorted(
            progress_rows,
            key=lambda x: parse_date(x.get("update_date")) or datetime.min,
        )
        latest_update = sorted_updates[-1]

        planned_prog = float(latest_update.get("planned_progress_pct", 0.0) or 0.0)
        physical_prog = float(latest_update.get("physical_progress_pct", 0.0) or 0.0)
        milestone = str(latest_update.get("milestone", "Unknown"))
        update_date = str(latest_update.get("update_date", ""))
        remarks = str(latest_update.get("remarks", ""))

        lag = round(planned_prog - physical_prog, 2)

        if lag >= self.config.milestone_lag_threshold_pct:
            severity = SeverityEnum.CRITICAL if lag >= self.config.milestone_lag_critical_pct else SeverityEnum.HIGH
            confidence = 0.92

            evidence = {
                "milestone": milestone,
                "update_date": update_date,
                "planned_progress_pct": planned_prog,
                "physical_progress_pct": physical_prog,
                "milestone_lag_pct": float(lag),
                "remarks": remarks,
                "threshold_pct": float(self.config.milestone_lag_threshold_pct),
            }

            explanation = (
                f"Milestone execution bottleneck: latest milestone '{milestone}' on {update_date} reports physical "
                f"progress of {physical_prog:.2f}%, lagging {lag:.2f}% behind planned milestone target ({planned_prog:.2f}%)."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.MILESTONE_LAG,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        progress_df: pd.DataFrame,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        if progress_df.empty:
            return results

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in progress_df.to_dict(orient="records"):
            pid = str(r["project_id"])
            if pid not in grouped:
                grouped[pid] = []
            grouped[pid].append(r)

        for pid, p_list in grouped.items():
            anomaly = self.evaluate_project(pid, p_list)
            if anomaly:
                results.append(anomaly)

        return results


class CompletionRiskRule:
    """
    Rule 6 (Progress): Detects ongoing projects approaching deadline (<=45 days remaining)
    while physical completion remains severely incomplete (<=40%).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        ref_date: Optional[datetime] = None,
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        status = str(project_row.get("status", "")).strip()
        physical_progress = float(project_row.get("physical_progress_pct", 0.0) or 0.0)
        planned_progress = float(project_row.get("planned_progress_pct", 0.0) or 0.0)
        expected_comp_str = project_row.get("expected_completion_date")

        if status.lower() == "completed" or physical_progress >= 100.0:
            return None

        exp_date = parse_date(expected_comp_str)
        if not exp_date:
            return None

        current_ref = ref_date or parse_date(self.config.reference_date_str) or datetime(2026, 8, 23)
        days_remaining = (exp_date - current_ref).days

        if days_remaining <= self.config.completion_risk_window_days and physical_progress <= self.config.completion_risk_progress_threshold_pct:
            severity = SeverityEnum.CRITICAL if (days_remaining <= 20 or physical_progress <= 25.0) else SeverityEnum.HIGH
            confidence = 0.94

            evidence = {
                "expected_completion_date": str(expected_comp_str),
                "reference_date": current_ref.strftime("%Y-%m-%d"),
                "days_remaining": int(days_remaining),
                "physical_progress_pct": round(physical_progress, 2),
                "planned_progress_pct": round(planned_progress, 2),
                "status": str(status),
                "risk_window_days": int(self.config.completion_risk_window_days),
                "max_progress_threshold_pct": float(self.config.completion_risk_progress_threshold_pct),
            }

            deadline_desc = f"{days_remaining} days remaining" if days_remaining >= 0 else f"{abs(days_remaining)} days past deadline"
            explanation = (
                f"Severe project completion risk: only {deadline_desc} to deadline ({expected_comp_str}) "
                f"while physical progress stands at only {physical_progress:.2f}%."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.COMPLETION_RISK,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                explanation=explanation,
            )

        return None

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        ref_date: Optional[datetime] = None,
    ) -> List[AnomalyResult]:
        results: List[AnomalyResult] = []
        for row in projects_df.to_dict(orient="records"):
            anomaly = self.evaluate_project(row, ref_date)
            if anomaly:
                results.append(anomaly)
        return results
