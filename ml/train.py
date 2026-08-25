import os
import sys
import time

# Ensure project root and backend are in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.join(project_root, "backend")

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.data_loader import load_all_datasets
from ml.features import extract_project_features
from ml.isolation_forest import IsolationForestAnomalyDetector
from ml.preprocessing import FeaturePreprocessor


def train_model(
    artifact_dir: Optional[str] = None,
    contamination: float = 0.10,
    n_estimators: int = 150,
    random_state: int = 42,
) -> dict:
    """
    End-to-end training pipeline for the unsupervised ML anomaly detection layer.
    """
    t0 = time.time()
    save_dir = artifact_dir or os.path.join(current_dir, "model_artifacts")
    os.makedirs(save_dir, exist_ok=True)

    print("==================================================")
    print("  MPLADS-IntelliTrack: Unsupervised ML Training   ")
    print("==================================================")
    print(f"Artifact Directory: {save_dir}")

    # 1. Load Raw Datasets
    print("\n[Step 1/4] Loading project datasets...")
    data = load_all_datasets()
    projects_df = data["projects"]
    total_projects = len(projects_df)
    print(f"Loaded {total_projects} projects from data/raw/.")

    # 2. Extract Multi-Domain Features
    print("\n[Step 2/4] Engineering project-level feature matrix...")
    project_ids, feature_df = extract_project_features(
        projects_df=projects_df,
        financials_df=data["financials"],
        payments_df=data["payments"],
        progress_df=data["progress_updates"],
        compliance_df=data["compliance"],
        evidence_df=data["evidence"],
    )
    feature_count = len(feature_df.columns)
    print(f"Extracted {feature_count} numerical features across Financial, Progress, Payment, Vendor, Compliance, and Geo domains.")

    # 3. Preprocess and Scale
    print("\n[Step 3/4] Preprocessing and standardizing features...")
    preprocessor = FeaturePreprocessor()
    X_scaled = preprocessor.fit_transform(feature_df)
    preprocessor.save(save_dir)
    print(f"Saved preprocessing scaler and features.json to {save_dir}.")

    # 4. Train Isolation Forest
    print("\n[Step 4/4] Training Isolation Forest model...")
    detector = IsolationForestAnomalyDetector(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        model_version="v1.0.0-isolation-forest",
    )
    detector.fit(X_scaled)
    detector.save(save_dir)

    flags, scores = detector.predict_scores(X_scaled)
    anomaly_count = int(sum(flags))
    elapsed = time.time() - t0

    print(f"\nModel training completed in {elapsed:.3f} seconds!")
    print(f"Training Samples    : {total_projects}")
    print(f"Feature Count       : {feature_count}")
    print(f"Anomalies Flagged   : {anomaly_count} ({(anomaly_count/total_projects)*100:.1f}%)")
    print(f"Score Distribution  : Min={scores.min():.1f}, Mean={scores.mean():.1f}, Max={scores.max():.1f}")

    results = {
        "status": "success",
        "training_samples": total_projects,
        "feature_count": feature_count,
        "feature_names": list(feature_df.columns),
        "anomalies_detected": anomaly_count,
        "contamination": contamination,
        "elapsed_seconds": round(elapsed, 3),
        "model_version": detector.model_version,
    }
    return results


if __name__ == "__main__":
    train_model()
