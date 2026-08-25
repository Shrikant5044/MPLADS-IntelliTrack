from typing import Any, Dict, List, Optional
import pandas as pd
from app.anomaly_engine.models import AnomalyResult
from app.risk_engine.models import (
    ProjectRiskProfile,
    RiskConfig,
    RiskEngineSummary,
    RiskLevelEnum,
)
from app.risk_engine.scorer import ProjectScorer
from ml.predict import ProjectMLPrediction


class RiskEngine:
    """
    Central Risk Engine for MPLADS-IntelliTrack.
    Aggregates multi-domain anomaly signals and supporting unsupervised ML predictions
    into unified, deterministic, explainable 0-100 project risk profiles.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.scorer = ProjectScorer(self.config)

    def evaluate_projects(
        self,
        projects_df: pd.DataFrame,
        anomalies: List[AnomalyResult],
        ml_predictions: Optional[List[ProjectMLPrediction]] = None,
    ) -> List[ProjectRiskProfile]:
        """
        Evaluates risk profiles across all projects, fusing rule-based and ML signals.
        Returns profiles sorted by risk_score descending (highest risk first).
        """
        if projects_df.empty:
            return []

        # 1. Group anomalies by project_id
        anomalies_by_project: Dict[str, List[AnomalyResult]] = {}
        for a in anomalies:
            pid = str(a.project_id)
            if pid not in anomalies_by_project:
                anomalies_by_project[pid] = []
            anomalies_by_project[pid].append(a)

        # 2. Map ML predictions by project_id
        ml_by_project: Dict[str, ProjectMLPrediction] = {}
        if ml_predictions:
            for p in ml_predictions:
                ml_by_project[str(p.project_id)] = p

        # 3. Score every project
        profiles: List[ProjectRiskProfile] = []
        for pid in projects_df["project_id"]:
            pid_str = str(pid)
            proj_anomalies = anomalies_by_project.get(pid_str, [])
            proj_ml = ml_by_project.get(pid_str, None)

            profile = self.scorer.score(
                project_id=pid_str,
                anomalies=proj_anomalies,
                ml_prediction=proj_ml,
            )
            profiles.append(profile)

        # 4. Sort highest risk first
        profiles.sort(key=lambda p: p.risk_score, reverse=True)
        return profiles

    def get_summary(self, profiles: List[ProjectRiskProfile]) -> RiskEngineSummary:
        """
        Computes distribution summary statistics across risk profiles.
        """
        total = len(profiles)
        if total == 0:
            return RiskEngineSummary(
                total_projects=0,
                average_risk_score=0.0,
                risk_level_counts={"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
                highest_risk_projects=[],
            )

        avg_score = round(sum(p.risk_score for p in profiles) / total, 2)
        level_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for p in profiles:
            level_counts[p.risk_level.value] = level_counts.get(p.risk_level.value, 0) + 1

        top_projects = [
            {
                "project_id": p.project_id,
                "risk_score": p.risk_score,
                "risk_level": p.risk_level.value,
                "summary": p.summary,
            }
            for p in profiles[:10]
        ]

        return RiskEngineSummary(
            total_projects=total,
            average_risk_score=avg_score,
            risk_level_counts=level_counts,
            highest_risk_projects=top_projects,
        )
