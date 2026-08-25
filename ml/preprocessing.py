import json
import os
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


class FeaturePreprocessor:
    """
    Handles robust scaling, imputation, and feature alignment for unsupervised ML modeling.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    def fit(self, feature_df: pd.DataFrame) -> "FeaturePreprocessor":
        """
        Fits StandardScaler across the feature columns.
        """
        self.feature_names = list(feature_df.columns)
        clean_matrix = self._clean_dataframe(feature_df)
        self.scaler.fit(clean_matrix)
        self.is_fitted = True
        return self

    def transform(self, feature_df: pd.DataFrame) -> np.ndarray:
        """
        Transforms input dataframe into scaled numerical numpy array.
        """
        if not self.is_fitted:
            raise ValueError("FeaturePreprocessor must be fitted before calling transform.")

        # Ensure exact column alignment
        aligned_df = pd.DataFrame()
        for col in self.feature_names:
            if col in feature_df.columns:
                aligned_df[col] = feature_df[col]
            else:
                aligned_df[col] = 0.0

        clean_matrix = self._clean_dataframe(aligned_df)
        return self.scaler.transform(clean_matrix)

    def fit_transform(self, feature_df: pd.DataFrame) -> np.ndarray:
        return self.fit(feature_df).transform(feature_df)

    def _clean_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """
        Cleans NaNs, nulls, and infinite values.
        """
        mat = df.values.astype(np.float64)
        mat = np.nan_to_num(mat, nan=0.0, posinf=0.0, neginf=0.0)
        return mat

    def save(self, artifact_dir: str) -> None:
        """
        Saves scaler and feature list to disk.
        """
        os.makedirs(artifact_dir, exist_ok=True)
        scaler_path = os.path.join(artifact_dir, "scaler.joblib")
        features_path = os.path.join(artifact_dir, "features.json")

        joblib.dump(self.scaler, scaler_path)
        with open(features_path, "w", encoding="utf-8") as f:
            json.dump({"feature_names": self.feature_names, "feature_count": len(self.feature_names)}, f, indent=2)

    def load(self, artifact_dir: str) -> "FeaturePreprocessor":
        """
        Loads scaler and feature list from disk.
        """
        scaler_path = os.path.join(artifact_dir, "scaler.joblib")
        features_path = os.path.join(artifact_dir, "features.json")

        if not os.path.exists(scaler_path) or not os.path.exists(features_path):
            raise FileNotFoundError(f"Preprocessing artifacts not found in {artifact_dir}")

        self.scaler = joblib.load(scaler_path)
        with open(features_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            self.feature_names = meta.get("feature_names", [])

        self.is_fitted = True
        return self
