import os
import sys
from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

# Ensure path resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.join(project_root, "backend")

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.features import extract_project_features
from ml.isolation_forest import IsolationForestAnomalyDetector
from ml.preprocessing import FeaturePreprocessor


class ProjectMLPrediction(BaseModel):
    """
    Standardized prediction output for a project from the unsupervised ML anomaly layer.
    """
    project_id: str = Field(..., description="Unique project identifier")
    ml_anomaly_score: float = Field(..., ge=0.0, le=100.0, description="Normalized 0-100 ML anomaly score (higher = more anomalous/outlier)")
    ml_anomaly_flag: bool = Field(..., description="Binary anomaly flag based on statistical contamination threshold")
    model_version: str = Field(..., description="Model version identifier")


class MLAnomalySummary(BaseModel):
    total_projects_evaluated: int
    anomalous_projects_count: int
    contamination_rate: float
    average_ml_score: float
    model_version: str
    feature_count: int


class MLInferenceService:
    """
    Inference service for the unsupervised Isolation Forest anomaly detection engine.
    """

    def __init__(self, artifact_dir: Optional[str] = None):
        self.artifact_dir = artifact_dir or os.path.join(current_dir, "model_artifacts")
        self.preprocessor = FeaturePreprocessor()
        self.detector = IsolationForestAnomalyDetector()
        self.is_ready: bool = False

    def ensure_model_loaded(self) -> None:
        """
        Loads saved model artifacts or trains them on-the-fly if missing.
        """
        if self.is_ready:
            return

        model_file = os.path.join(self.artifact_dir, "model.joblib")
        scaler_file = os.path.join(self.artifact_dir, "scaler.joblib")

        if not os.path.exists(model_file) or not os.path.exists(scaler_file):
            from ml.train import train_model
            train_model(artifact_dir=self.artifact_dir)

        self.preprocessor.load(self.artifact_dir)
        self.detector.load(self.artifact_dir)
        self.is_ready = True

    def predict_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
        payments_df: Optional[pd.DataFrame] = None,
        progress_df: Optional[pd.DataFrame] = None,
        compliance_df: Optional[pd.DataFrame] = None,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> List[ProjectMLPrediction]:
        """
        Runs unsupervised ML inference across all projects and returns predictions sorted highest score first.
        """
        self.ensure_model_loaded()

        project_ids, feature_df = extract_project_features(
            projects_df=projects_df,
            financials_df=financials_df,
            payments_df=payments_df,
            progress_df=progress_df,
            compliance_df=compliance_df,
            evidence_df=evidence_df,
        )

        if not project_ids:
            return []

        X_scaled = self.preprocessor.transform(feature_df)
        flags, scores = self.detector.predict_scores(X_scaled)

        predictions: List[ProjectMLPrediction] = []
        for i, pid in enumerate(project_ids):
            predictions.append(ProjectMLPrediction(
                project_id=pid,
                ml_anomaly_score=float(scores[i]),
                ml_anomaly_flag=bool(flags[i]),
                model_version=self.detector.model_version,
            ))

        # Sort highest ML anomaly score first
        predictions.sort(key=lambda p: p.ml_anomaly_score, reverse=True)
        return predictions

    def predict_project(
        self,
        project_id: str,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
        payments_df: Optional[pd.DataFrame] = None,
        progress_df: Optional[pd.DataFrame] = None,
        compliance_df: Optional[pd.DataFrame] = None,
        evidence_df: Optional[pd.DataFrame] = None,
    ) -> Optional[ProjectMLPrediction]:
        """
        Runs ML prediction for a single project by project_id.
        """
        all_preds = self.predict_all(
            projects_df=projects_df,
            financials_df=financials_df,
            payments_df=payments_df,
            progress_df=progress_df,
            compliance_df=compliance_df,
            evidence_df=evidence_df,
        )
        for p in all_preds:
            if p.project_id == project_id:
                return p
        return None

    def get_summary(self, predictions: List[ProjectMLPrediction]) -> MLAnomalySummary:
        """
        Computes summary statistics for ML predictions.
        """
        total = len(predictions)
        if total == 0:
            return MLAnomalySummary(
                total_projects_evaluated=0,
                anomalous_projects_count=0,
                contamination_rate=0.0,
                average_ml_score=0.0,
                model_version=self.detector.model_version,
                feature_count=len(self.preprocessor.feature_names),
            )

        anom_count = sum(1 for p in predictions if p.ml_anomaly_flag)
        avg_score = round(sum(p.ml_anomaly_score for p in predictions) / total, 2)
        contam = round((anom_count / total) * 100, 2)

        return MLAnomalySummary(
            total_projects_evaluated=total,
            anomalous_projects_count=anom_count,
            contamination_rate=contam,
            average_ml_score=avg_score,
            model_version=self.detector.model_version,
            feature_count=len(self.preprocessor.feature_names),
        )
