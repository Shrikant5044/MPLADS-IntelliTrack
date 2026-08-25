from typing import Any, Dict, List, Optional
import pandas as pd
from app.anomaly_engine.models import (
    AnomalyResult,
    AnomalyTypeEnum,
    SeverityEnum,
    ThresholdConfig,
)


class CostOverrunRule:
    """
    Rule 2 (Cost): Detects projects where actual expenditure or final cost exceeds
    the original estimated cost beyond acceptable thresholds (> 5.0% cost escalation).
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdConfig()

    def evaluate_project(
        self,
        project_row: Dict[str, Any],
        financial_row: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnomalyResult]:
        project_id = str(project_row.get("project_id", ""))
        estimated_cost = float(project_row.get("estimated_cost_lakh", 0.0) or 0.0)
        sanctioned_amount = float(project_row.get("sanctioned_amount_lakh", 0.0) or 0.0)
        expenditure = float(project_row.get("expenditure_lakh", 0.0) or 0.0)

        if estimated_cost <= 0:
            return None

        # Retrieve or compute cost overrun percentage against original estimate
        cost_overrun_pct = 0.0
        if financial_row and "cost_overrun_pct" in financial_row and financial_row["cost_overrun_pct"] is not None:
            try:
                cost_overrun_pct = float(financial_row["cost_overrun_pct"])
            except (ValueError, TypeError):
                cost_overrun_pct = round(((expenditure - estimated_cost) / estimated_cost) * 100, 2)
        else:
            cost_overrun_pct = round(((expenditure - estimated_cost) / estimated_cost) * 100, 2)

        overrun_amount_lakh = round(expenditure - estimated_cost, 2)

        # Trigger only when cost overrun exceeds calibrated threshold (5.0%)
        if cost_overrun_pct >= self.config.cost_overrun_pct_threshold:
            if cost_overrun_pct >= self.config.cost_overrun_critical_pct:
                severity = SeverityEnum.CRITICAL
                confidence = 0.96
            elif cost_overrun_pct >= self.config.cost_overrun_high_pct:
                severity = SeverityEnum.HIGH
                confidence = 0.92
            elif cost_overrun_pct >= self.config.cost_overrun_medium_pct:
                severity = SeverityEnum.MEDIUM
                confidence = 0.88
            else:
                severity = SeverityEnum.LOW
                confidence = 0.82

            evidence = {
                "estimated_cost_lakh": round(estimated_cost, 2),
                "sanctioned_amount_lakh": round(sanctioned_amount, 2),
                "expenditure_lakh": round(expenditure, 2),
                "cost_overrun_lakh": overrun_amount_lakh,
                "cost_overrun_pct": cost_overrun_pct,
                "threshold_pct": self.config.cost_overrun_pct_threshold,
            }

            explanation = (
                f"Project expenditure of ₹{expenditure:.2f} Lakh exceeds original estimated cost "
                f"of ₹{estimated_cost:.2f} Lakh by ₹{overrun_amount_lakh:.2f} Lakh "
                f"({cost_overrun_pct:.2f}% cost overrun)."
            )

            return AnomalyResult(
                project_id=project_id,
                anomaly_type=AnomalyTypeEnum.COST_OVERRUN,
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
            fin_dict = fin_map.get(pid)
            anomaly = self.evaluate_project(proj_dict, fin_dict)
            if anomaly:
                results.append(anomaly)

        return results
