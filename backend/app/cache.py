import threading
import time
from typing import Any, Dict, List, Optional
import pandas as pd

from app.analytics_engine import (
    AuditQueueItem,
    AuditQueueSummary,
    BenchmarkConfig,
    BenchmarkSummary,
    DistrictAnalyticsEngine,
    DistrictAnalyticsSummary,
    DistrictRiskProfile,
    EarlyWarningForecastEngine,
    ForecastConfig,
    ForecastSummary,
    GeospatialQualityMetrics,
    PrioritizedAuditQueueEngine,
    ProjectBenchmarkResult,
    ProjectBenchmarkingEngine,
    ProjectForecastResult,
    get_geospatial_quality_metrics,
)
from app.anomaly_engine import (
    AnomalyEngine,
    AnomalyResult,
    AnomalySummary,
    ThresholdConfig,
)
from app.data_loader import (
    dataframe_to_records,
    load_all_datasets,
)
from app.risk_engine import (
    ProjectRiskProfile,
    RiskConfig,
    RiskEngine,
    RiskEngineSummary,
)
from ml.predict import (
    MLAnomalySummary,
    MLInferenceService,
    ProjectMLPrediction,
)


class IntelligenceCache:
    """
    Thread-safe in-memory cache for MPLADS-IntelliTrack datasets, anomaly detections,
    ML outlier predictions, fused risk profiles, comparable benchmarking, trajectory forecasts,
    district risk aggregations, and prioritized audit decision-support queue.
    Precomputes intelligence on startup to provide sub-5ms API response latencies.
    """

    def __init__(
        self,
        threshold_config: Optional[ThresholdConfig] = None,
        risk_config: Optional[RiskConfig] = None,
        benchmark_config: Optional[BenchmarkConfig] = None,
        forecast_config: Optional[ForecastConfig] = None,
    ):
        self._lock = threading.Lock()
        self._is_initialized = False

        self.threshold_config = threshold_config or ThresholdConfig()
        self.risk_config = risk_config or RiskConfig()
        self.benchmark_config = benchmark_config or BenchmarkConfig()
        self.forecast_config = forecast_config or ForecastConfig()

        self.anomaly_engine = AnomalyEngine(self.threshold_config)
        self.risk_engine = RiskEngine(self.risk_config)
        self.ml_service = MLInferenceService()
        self.benchmark_engine = ProjectBenchmarkingEngine(self.benchmark_config)
        self.forecast_engine = EarlyWarningForecastEngine(self.forecast_config)
        self.district_engine = DistrictAnalyticsEngine()
        self.audit_queue_engine = PrioritizedAuditQueueEngine()

        # Cached Datasets
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.projects_records: List[Dict[str, Any]] = []
        self.project_ids_set: set = set()

        # Cached Anomalies
        self.all_anomalies: List[AnomalyResult] = []
        self.anomalies_by_project: Dict[str, List[AnomalyResult]] = {}
        self.anomaly_summary: Optional[AnomalySummary] = None

        # Cached ML Predictions
        self.ml_predictions: List[ProjectMLPrediction] = []
        self.ml_by_project: Dict[str, ProjectMLPrediction] = {}
        self.ml_summary: Optional[MLAnomalySummary] = None

        # Cached Risk Profiles
        self.risk_profiles: List[ProjectRiskProfile] = []
        self.risk_by_project: Dict[str, ProjectRiskProfile] = {}
        self.risk_summary: Optional[RiskEngineSummary] = None

        # Cached Benchmarking
        self.benchmark_results: List[ProjectBenchmarkResult] = []
        self.benchmark_by_project: Dict[str, ProjectBenchmarkResult] = {}
        self.benchmark_summary: Optional[BenchmarkSummary] = None

        # Cached Early Warning Forecasts
        self.forecast_results: List[ProjectForecastResult] = []
        self.forecast_by_project: Dict[str, ProjectForecastResult] = {}
        self.forecast_summary: Optional[ForecastSummary] = None

        # Cached District Analytics
        self.district_profiles: List[DistrictRiskProfile] = []
        self.district_summary: Optional[DistrictAnalyticsSummary] = None

        # Cached Prioritized Audit Queue
        self.audit_queue_items: List[AuditQueueItem] = []
        self.audit_queue_summary: Optional[AuditQueueSummary] = None

        # Cached Geospatial Quality Metrics
        self.geospatial_quality: Optional[GeospatialQualityMetrics] = None

        # Telemetry
        self.last_computed_at: Optional[float] = None
        self.initialization_duration_ms: float = 0.0

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    def initialize(self, force_reload: bool = False) -> None:
        """
        Precomputes all intelligence layers in-memory. Thread-safe and idempotent.
        """
        if self._is_initialized and not force_reload:
            return

        with self._lock:
            if self._is_initialized and not force_reload:
                return

            t0 = time.time()

            # 1. Load Datasets
            data = load_all_datasets()
            self.datasets = data
            projects_df = data["projects"]
            self.projects_records = dataframe_to_records(projects_df)
            self.project_ids_set = set(str(pid) for pid in projects_df["project_id"])

            # 2. Run Deterministic Anomaly Engine (31 rules)
            self.all_anomalies = self.anomaly_engine.run_all(
                projects_df=projects_df,
                financials_df=data.get("financials"),
                payments_df=data.get("payments"),
                progress_df=data.get("progress_updates"),
                compliance_df=data.get("compliance"),
                evidence_df=data.get("evidence"),
            )
            self.anomaly_summary = self.anomaly_engine.get_summary(
                self.all_anomalies, total_projects=len(projects_df)
            )

            anom_map: Dict[str, List[AnomalyResult]] = {pid: [] for pid in self.project_ids_set}
            for a in self.all_anomalies:
                pid_str = str(a.project_id)
                if pid_str not in anom_map:
                    anom_map[pid_str] = []
                anom_map[pid_str].append(a)
            self.anomalies_by_project = anom_map

            # 3. Run Unsupervised ML Anomaly Engine (29 features)
            self.ml_service.ensure_model_loaded()
            self.ml_predictions = self.ml_service.predict_all(
                projects_df=projects_df,
                financials_df=data.get("financials"),
                payments_df=data.get("payments"),
                progress_df=data.get("progress_updates"),
                compliance_df=data.get("compliance"),
                evidence_df=data.get("evidence"),
            )
            self.ml_summary = self.ml_service.get_summary(self.ml_predictions)
            self.ml_by_project = {str(p.project_id): p for p in self.ml_predictions}

            # 4. Run Fused Risk Engine (7 categories + ML_STATISTICAL)
            self.risk_profiles = self.risk_engine.evaluate_projects(
                projects_df=projects_df,
                anomalies=self.all_anomalies,
                ml_predictions=self.ml_predictions,
            )
            self.risk_summary = self.risk_engine.get_summary(self.risk_profiles)
            self.risk_by_project = {str(p.project_id): p for p in self.risk_profiles}

            # 5. Run Comparable Project Benchmarking Engine
            self.benchmark_results = self.benchmark_engine.evaluate_all(
                projects_df=projects_df,
                financials_df=data.get("financials"),
            )
            self.benchmark_summary = self.benchmark_engine.get_summary(self.benchmark_results)
            self.benchmark_by_project = {str(b.project_id): b for b in self.benchmark_results}

            # 6. Run Early Warning Trajectory & Cost Forecasting Engine
            self.forecast_results = self.forecast_engine.evaluate_all(
                projects_df=projects_df,
                progress_df=data.get("progress_updates"),
                financials_df=data.get("financials"),
            )
            self.forecast_summary = self.forecast_engine.get_summary(self.forecast_results)
            self.forecast_by_project = {str(f.project_id): f for f in self.forecast_results}

            # 7. Run District Risk Aggregation Engine
            self.district_profiles = self.district_engine.evaluate_all(
                projects_df=projects_df,
                risk_profiles=self.risk_profiles,
                anomalies=self.all_anomalies,
            )
            self.district_summary = self.district_engine.get_summary(self.district_profiles)

            # 8. Run Prioritized Audit Queue Engine
            self.audit_queue_items = self.audit_queue_engine.generate_queue(
                projects_df=projects_df,
                risk_profiles=self.risk_profiles,
                anomalies=self.all_anomalies,
            )
            self.audit_queue_summary = self.audit_queue_engine.get_summary(self.audit_queue_items)

            # 9. Compute Geospatial Data Quality Metrics
            self.geospatial_quality = get_geospatial_quality_metrics(projects_df)

            self.initialization_duration_ms = (time.time() - t0) * 1000.0
            self.last_computed_at = time.time()
            self._is_initialized = True


# Global singleton instance
cache = IntelligenceCache()


def get_cache() -> IntelligenceCache:
    """
    Accessor function that ensures the cache is initialized before returning.
    """
    if not cache.is_initialized:
        cache.initialize()
    return cache
