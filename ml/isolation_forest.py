import json
import os
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest


class IsolationForestAnomalyDetector:
    """
    Unsupervised statistical anomaly detector based on Isolation Forests.
    Measures how isolated/unusual a project's multi-domain metrics are compared to the population.
    """

    def __init__(
        self,
        n_estimators: int = 150,
        contamination: float = 0.10,
        random_state: int = 42,
        model_version: str = "v1.0.0-isolation-forest",
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.model_version = model_version

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            max_samples=1.0,
            bootstrap=False,
            n_jobs=-1,
        )
        self.is_fitted: bool = False
        self.min_decision_val: float = -0.25
        self.max_decision_val: float = 0.25

    def fit(self, X: np.ndarray) -> "IsolationForestAnomalyDetector":
        """
        Fits the Isolation Forest on scaled numerical features.
        """
        self.model.fit(X)
        self.is_fitted = True

        # Store baseline calibration boundaries
        decisions = self.model.decision_function(X)
        neg_decs = decisions[decisions < 0]
        pos_decs = decisions[decisions >= 0]

        self.min_decision_val = float(np.min(decisions)) if len(decisions) > 0 else -0.25
        self.max_decision_val = float(np.max(decisions)) if len(decisions) > 0 else 0.25
        return self

    def predict_scores(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates binary anomaly flags (-1 -> True, 1 -> False) and normalized 0-100 ML anomaly scores.
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before generating predictions.")

        preds = self.model.predict(X)
        decisions = self.model.decision_function(X)

        ml_anomaly_flags = (preds == -1)
        ml_scores = []

        for d in decisions:
            # Normalized piece-wise scaling:
            # Outliers (d < 0) map to [50.0, 100.0]
            # Inliers (d >= 0) map to [0.0, 49.0]
            if d < 0:
                denom = abs(self.min_decision_val) if abs(self.min_decision_val) > 0 else 0.2
                score = 50.0 + 50.0 * min(1.0, abs(d) / denom)
            else:
                denom = self.max_decision_val if self.max_decision_val > 0 else 0.2
                score = 49.0 * max(0.0, 1.0 - (d / denom))

            ml_scores.append(round(float(np.clip(score, 0.0, 100.0)), 1))

        return ml_anomaly_flags, np.array(ml_scores)

    def save(self, artifact_dir: str) -> None:
        """
        Persists model and hyperparameters to disk.
        """
        os.makedirs(artifact_dir, exist_ok=True)
        model_path = os.path.join(artifact_dir, "model.joblib")
        config_path = os.path.join(artifact_dir, "config.json")

        joblib.dump(self.model, model_path)
        config_data = {
            "model_version": self.model_version,
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "min_decision_val": self.min_decision_val,
            "max_decision_val": self.max_decision_val,
            "is_fitted": self.is_fitted,
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

    def load(self, artifact_dir: str) -> "IsolationForestAnomalyDetector":
        """
        Loads persisted model and hyperparameters.
        """
        model_path = os.path.join(artifact_dir, "model.joblib")
        config_path = os.path.join(artifact_dir, "config.json")

        if not os.path.exists(model_path) or not os.path.exists(config_path):
            raise FileNotFoundError(f"Model artifacts not found in {artifact_dir}")

        self.model = joblib.load(model_path)
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            self.model_version = cfg.get("model_version", self.model_version)
            self.n_estimators = cfg.get("n_estimators", self.n_estimators)
            self.contamination = cfg.get("contamination", self.contamination)
            self.random_state = cfg.get("random_state", self.random_state)
            self.min_decision_val = cfg.get("min_decision_val", self.min_decision_val)
            self.max_decision_val = cfg.get("max_decision_val", self.max_decision_val)
            self.is_fitted = cfg.get("is_fitted", True)

        return self
