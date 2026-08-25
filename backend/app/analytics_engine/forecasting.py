from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class TrajectoryStatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    ON_TRACK = "ON_TRACK"
    WATCH = "WATCH"
    LIKELY_DELAY = "LIKELY_DELAY"
    SEVERE_DELAY_RISK = "SEVERE_DELAY_RISK"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


class ForecastConfig(BaseModel):
    """
    Configurable parameters for empirical progress trajectory and cost forecasting.
    These are empirical extrapolations, NOT machine-learning predictions.
    """
    min_progress_updates: int = Field(
        default=2,
        ge=1,
        description="Minimum number of chronological progress logs required for trajectory estimation.",
    )
    watch_delay_days: int = Field(
        default=30,
        description="Forecasted delay days threshold for WATCH status.",
    )
    likely_delay_days: int = Field(
        default=90,
        description="Forecasted delay days threshold for LIKELY_DELAY status.",
    )
    cost_watch_variance_pct: float = Field(
        default=10.0,
        description="Projected cost variance threshold for WATCH status.",
    )
    cost_high_variance_pct: float = Field(
        default=25.0,
        description="Projected cost variance threshold for SEVERE_DELAY_RISK status.",
    )
    velocity_stall_threshold: float = Field(
        default=0.0001,
        description="Physical progress percentage per day below which progress is considered stalled.",
    )


class ProjectForecastResult(BaseModel):
    """
    Standardized early-warning trajectory forecast result for a single project.
    """
    project_id: str = Field(..., description="Target project identifier")
    work_name: str = Field(..., description="Name of the work")
    status: str = Field(..., description="Lifecycle status in registry (Ongoing, Completed, etc.)")
    
    current_progress_pct: float = Field(..., ge=0.0, le=100.0, description="Current recorded physical progress percentage")
    planned_progress_pct: float = Field(..., ge=0.0, le=100.0, description="Target planned progress percentage")
    
    velocity_pct_per_day: Optional[float] = Field(
        default=None,
        description="Empirical historical physical progress rate in percentage points per day",
    )
    elapsed_days: int = Field(..., description="Execution days elapsed from start date to latest progress update")
    estimated_days_remaining: Optional[int] = Field(
        default=None,
        description="Estimated days required to reach 100% physical completion at historical velocity",
    )
    
    forecast_completion_date: Optional[str] = Field(
        default=None,
        description="Forecasted completion date (YYYY-MM-DD) based on empirical velocity",
    )
    expected_completion_date: Optional[str] = Field(
        default=None,
        description="Statutory scheduled completion date (YYYY-MM-DD)",
    )
    actual_completion_date: Optional[str] = Field(
        default=None,
        description="Actual completion date (YYYY-MM-DD) if project is completed",
    )
    forecast_delay_days: Optional[int] = Field(
        default=None,
        description="Forecasted delay in days relative to statutory expected completion date (negative = ahead of schedule)",
    )
    
    burn_rate_lakh_per_day: Optional[float] = Field(
        default=None,
        description="Empirical financial disbursement rate in Lakhs per day",
    )
    current_expenditure_lakh: float = Field(..., description="Current cumulative expenditure recorded in Lakhs")
    sanctioned_amount_lakh: float = Field(..., description="Total sanctioned budget in Lakhs")
    
    projected_final_expenditure_lakh: Optional[float] = Field(
        default=None,
        description="Projected final expenditure in Lakhs if current burn/progress ratio continues",
    )
    projected_cost_variance_pct: Optional[float] = Field(
        default=None,
        description="Projected cost variance relative to sanctioned budget ((projected - sanctioned) / sanctioned * 100)",
    )
    
    trajectory_status: TrajectoryStatusEnum = Field(
        ...,
        description="Operational early warning status: COMPLETED, ON_TRACK, WATCH, LIKELY_DELAY, SEVERE_DELAY_RISK, INSUFFICIENT_HISTORY",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score based on progress update density and execution history span",
    )
    explanation: str = Field(
        ...,
        description="Human-readable synthesis of completion timeline, velocity, and burn-rate",
    )
    assumptions_and_limitations: str = Field(
        ...,
        description="Clear documentation of empirical extrapolation assumptions and operational limitations",
    )


class ForecastSummary(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    status_counts: Dict[str, int]
    average_forecast_delay_days: Optional[float]
    total_projected_cost_overrun_lakh: float


class ForecastListResponse(BaseModel):
    total: int = Field(..., description="Total records matching filters")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")
    count: int = Field(..., description="Items in current payload")
    summary: ForecastSummary = Field(..., description="Statistical summary across all project forecasts")
    data: List[ProjectForecastResult] = Field(..., description="List of project early warning trajectory forecasts")


class EarlyWarningForecastEngine:
    """
    Early Warning Progress Trajectory and Cost Forecasting Engine.
    Performs empirical extrapolation of execution velocity and financial burn rate
    without using black-box ML claims.
    """

    def __init__(self, config: Optional[ForecastConfig] = None):
        self.config = config or ForecastConfig()

    def evaluate_project(
        self,
        project_id: str,
        projects_df: pd.DataFrame,
        progress_df: Optional[pd.DataFrame] = None,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> Optional[ProjectForecastResult]:
        """
        Evaluates early warning progress trajectory and cost forecast for a single project.
        """
        matched = projects_df[projects_df["project_id"].astype(str) == str(project_id)]
        if matched.empty:
            return None

        p_row = matched.iloc[0]
        work_name = str(p_row.get("work_name", ""))
        status = str(p_row.get("status", "Ongoing"))
        curr_progress = float(p_row.get("physical_progress_pct", 0.0) or 0.0)
        planned_progress = float(p_row.get("planned_progress_pct", 0.0) or 0.0)
        expenditure = float(p_row.get("expenditure_lakh", 0.0) or 0.0)
        sanctioned = float(p_row.get("sanctioned_amount_lakh", 0.0) or 0.0)

        exp_comp_str = str(p_row.get("expected_completion_date", "")) if pd.notnull(p_row.get("expected_completion_date")) else None
        act_comp_str = str(p_row.get("actual_completion_date", "")) if pd.notnull(p_row.get("actual_completion_date")) else None
        start_date_str = str(p_row.get("start_date", "")) if pd.notnull(p_row.get("start_date")) else None

        # Handle COMPLETED projects
        if status == "Completed" or curr_progress >= 100.0:
            delay_days = None
            if act_comp_str and exp_comp_str:
                try:
                    d_act = datetime.strptime(act_comp_str, "%Y-%m-%d")
                    d_exp = datetime.strptime(exp_comp_str, "%Y-%m-%d")
                    delay_days = (d_act - d_exp).days
                except (ValueError, TypeError):
                    pass

            cost_var = round(((expenditure - sanctioned) / sanctioned) * 100.0, 1) if sanctioned > 0 else 0.0
            explanation = (
                f"Project is officially marked COMPLETED with {curr_progress:.1f}% physical progress. "
                f"Total expenditure closed at ₹{expenditure:.2f}L vs sanctioned ₹{sanctioned:.2f}L."
            )
            if delay_days is not None:
                if delay_days > 0:
                    explanation += f" Completed with a statutory delay of {delay_days} days."
                else:
                    explanation += f" Completed on or ahead of scheduled deadline ({abs(delay_days)} days ahead)."

            return ProjectForecastResult(
                project_id=project_id,
                work_name=work_name,
                status=status,
                current_progress_pct=curr_progress,
                planned_progress_pct=planned_progress,
                velocity_pct_per_day=None,
                elapsed_days=0,
                estimated_days_remaining=0,
                forecast_completion_date=act_comp_str or exp_comp_str,
                expected_completion_date=exp_comp_str,
                actual_completion_date=act_comp_str,
                forecast_delay_days=delay_days,
                burn_rate_lakh_per_day=None,
                current_expenditure_lakh=round(expenditure, 2),
                sanctioned_amount_lakh=round(sanctioned, 2),
                projected_final_expenditure_lakh=round(expenditure, 2),
                projected_cost_variance_pct=cost_var,
                trajectory_status=TrajectoryStatusEnum.COMPLETED,
                confidence=1.0,
                explanation=explanation,
                assumptions_and_limitations="Completed project record; reflects historical execution outturn.",
            )

        # Active project: inspect progress updates history
        p_updates = pd.DataFrame()
        if progress_df is not None and not progress_df.empty:
            p_updates = progress_df[progress_df["project_id"].astype(str) == str(project_id)].sort_values("update_date")

        if len(p_updates) < self.config.min_progress_updates or not start_date_str:
            return ProjectForecastResult(
                project_id=project_id,
                work_name=work_name,
                status=status,
                current_progress_pct=curr_progress,
                planned_progress_pct=planned_progress,
                velocity_pct_per_day=None,
                elapsed_days=0,
                estimated_days_remaining=None,
                forecast_completion_date=None,
                expected_completion_date=exp_comp_str,
                actual_completion_date=None,
                forecast_delay_days=None,
                burn_rate_lakh_per_day=None,
                current_expenditure_lakh=round(expenditure, 2),
                sanctioned_amount_lakh=round(sanctioned, 2),
                projected_final_expenditure_lakh=None,
                projected_cost_variance_pct=None,
                trajectory_status=TrajectoryStatusEnum.INSUFFICIENT_HISTORY,
                confidence=0.0,
                explanation=(
                    f"Insufficient progress update logs ({len(p_updates)} updates found, minimum {self.config.min_progress_updates} required) "
                    "or missing commencement date. Empirical trajectory cannot be computed without bias."
                ),
                assumptions_and_limitations="Requires minimum chronological milestone history to establish progress rate.",
            )

        # Parse timeline dates
        try:
            d_start = datetime.strptime(start_date_str, "%Y-%m-%d")
            latest_update_str = str(p_updates["update_date"].iloc[-1])
            d_latest = datetime.strptime(latest_update_str, "%Y-%m-%d")
            d_exp = datetime.strptime(exp_comp_str, "%Y-%m-%d") if exp_comp_str else None
        except (ValueError, TypeError):
            d_start = datetime(2026, 1, 1)
            d_latest = datetime(2026, 8, 23)
            d_exp = None

        elapsed_days = max(1, (d_latest - d_start).days)

        # Empirical Physical Velocity (% per day)
        velocity = curr_progress / float(elapsed_days)

        # Financial Burn Rate (Lakhs per day)
        burn_rate = expenditure / float(elapsed_days)

        # Projected Final Cost based on expenditure-to-progress ratio
        if curr_progress > 5.0:
            projected_cost = round((expenditure / (curr_progress / 100.0)), 2)
        else:
            projected_cost = round(sanctioned, 2)
        
        projected_cost_variance = round(((projected_cost - sanctioned) / sanctioned) * 100.0, 1) if sanctioned > 0 else 0.0

        # Handle Stalled Progress (zero velocity)
        if velocity <= self.config.velocity_stall_threshold:
            explanation = (
                f"CRITICAL STAGNATION: Project has recorded negligible progress ({curr_progress:.1f}%) "
                f"over {elapsed_days} elapsed execution days (velocity: {velocity*100:.3f}%/day). "
                f"Current expenditure stands at ₹{expenditure:.2f}L."
            )
            return ProjectForecastResult(
                project_id=project_id,
                work_name=work_name,
                status=status,
                current_progress_pct=curr_progress,
                planned_progress_pct=planned_progress,
                velocity_pct_per_day=round(velocity, 4),
                elapsed_days=elapsed_days,
                estimated_days_remaining=None,
                forecast_completion_date=None,
                expected_completion_date=exp_comp_str,
                actual_completion_date=None,
                forecast_delay_days=999,
                burn_rate_lakh_per_day=round(burn_rate, 4),
                current_expenditure_lakh=round(expenditure, 2),
                sanctioned_amount_lakh=round(sanctioned, 2),
                projected_final_expenditure_lakh=projected_cost,
                projected_cost_variance_pct=projected_cost_variance,
                trajectory_status=TrajectoryStatusEnum.SEVERE_DELAY_RISK,
                confidence=0.85,
                explanation=explanation,
                assumptions_and_limitations=(
                    "Extrapolated from zero historical velocity. Physical site mobilization intervention required."
                ),
            )

        # Extrapolate Remaining Days
        remaining_progress = max(0.0, 100.0 - curr_progress)
        estimated_days_rem = int(round(remaining_progress / velocity))
        
        # Forecasted Completion Date
        d_forecast = d_latest + pd.Timedelta(days=estimated_days_rem)
        forecast_date_str = d_forecast.strftime("%Y-%m-%d")

        # Forecast Delay Days
        forecast_delay_days = None
        if d_exp:
            forecast_delay_days = (d_forecast - d_exp).days

        # Status Classification
        if forecast_delay_days is not None:
            if forecast_delay_days > self.config.likely_delay_days or projected_cost_variance > self.config.cost_high_variance_pct:
                traj_status = TrajectoryStatusEnum.SEVERE_DELAY_RISK
            elif forecast_delay_days > self.config.watch_delay_days or projected_cost_variance > self.config.cost_watch_variance_pct:
                traj_status = TrajectoryStatusEnum.LIKELY_DELAY
            elif forecast_delay_days > 0:
                traj_status = TrajectoryStatusEnum.WATCH
            else:
                traj_status = TrajectoryStatusEnum.ON_TRACK
        else:
            traj_status = TrajectoryStatusEnum.ON_TRACK if velocity >= 0.20 else TrajectoryStatusEnum.WATCH

        # Confidence based on log density and timeline span
        update_density = min(1.0, len(p_updates) / 5.0)
        span_confidence = min(1.0, elapsed_days / 180.0)
        confidence = round(0.5 * update_density + 0.5 * span_confidence, 2)

        # Explainability synthesis
        if forecast_delay_days is not None:
            if forecast_delay_days > 0:
                timeline_summary = f"forecasted to complete on {forecast_date_str} ({forecast_delay_days} days behind scheduled deadline of {exp_comp_str})"
            else:
                timeline_summary = f"on schedule for completion on {forecast_date_str} ({abs(forecast_delay_days)} days ahead of deadline {exp_comp_str})"
        else:
            timeline_summary = f"forecasted to complete on {forecast_date_str}"

        explanation = (
            f"Based on historical execution velocity of {velocity:.2f}%/day across {elapsed_days} elapsed days ({len(p_updates)} milestone logs), "
            f"the remaining {remaining_progress:.1f}% physical work is estimated to require {estimated_days_rem} days. "
            f"Project is {timeline_summary}. "
            f"Financial burn-rate is ₹{burn_rate*30:.2f}L/month with projected final expenditure of ₹{projected_cost:.2f}L "
            f"({'+' if projected_cost_variance > 0 else ''}{projected_cost_variance:.1f}% vs sanction)."
        )

        limitations = (
            "Empirical linear trajectory assumes sustained historical physical velocity and steady material procurement. "
            "Weather seasonality, monsoon shutdowns, or mid-project budget revisions may alter actual completion."
        )

        return ProjectForecastResult(
            project_id=project_id,
            work_name=work_name,
            status=status,
            current_progress_pct=curr_progress,
            planned_progress_pct=planned_progress,
            velocity_pct_per_day=round(velocity, 4),
            elapsed_days=elapsed_days,
            estimated_days_remaining=estimated_days_rem,
            forecast_completion_date=forecast_date_str,
            expected_completion_date=exp_comp_str,
            actual_completion_date=act_comp_str,
            forecast_delay_days=forecast_delay_days,
            burn_rate_lakh_per_day=round(burn_rate, 4),
            current_expenditure_lakh=round(expenditure, 2),
            sanctioned_amount_lakh=round(sanctioned, 2),
            projected_final_expenditure_lakh=projected_cost,
            projected_cost_variance_pct=projected_cost_variance,
            trajectory_status=traj_status,
            confidence=confidence,
            explanation=explanation,
            assumptions_and_limitations=limitations,
        )

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        progress_df: Optional[pd.DataFrame] = None,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> List[ProjectForecastResult]:
        """
        Evaluates early warning forecasts across all projects in dataset.
        """
        results: List[ProjectForecastResult] = []
        if projects_df.empty:
            return results

        for pid in projects_df["project_id"].astype(str):
            res = self.evaluate_project(pid, projects_df, progress_df, financials_df)
            if res:
                results.append(res)

        return results

    def get_summary(
        self,
        results: List[ProjectForecastResult],
    ) -> ForecastSummary:
        """
        Computes summary statistics across all project trajectory forecasts.
        """
        status_counts: Dict[str, int] = {}
        active_count = 0
        completed_count = 0
        delays: List[int] = []
        total_overrun = 0.0

        for r in results:
            s_key = r.trajectory_status.value
            status_counts[s_key] = status_counts.get(s_key, 0) + 1

            if r.trajectory_status == TrajectoryStatusEnum.COMPLETED:
                completed_count += 1
            else:
                active_count += 1
                if r.forecast_delay_days is not None and r.forecast_delay_days < 900:
                    delays.append(r.forecast_delay_days)

            if r.projected_final_expenditure_lakh and r.sanctioned_amount_lakh:
                diff = r.projected_final_expenditure_lakh - r.sanctioned_amount_lakh
                if diff > 0:
                    total_overrun += diff

        avg_delay = round(float(np.mean(delays)), 1) if delays else None

        return ForecastSummary(
            total_projects=len(results),
            active_projects=active_count,
            completed_projects=completed_count,
            status_counts=status_counts,
            average_forecast_delay_days=avg_delay,
            total_projected_cost_overrun_lakh=round(total_overrun, 2),
        )
