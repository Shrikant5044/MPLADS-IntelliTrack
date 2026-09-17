import sys
import os
import unittest
import pandas as pd

# Add paths
_curr = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.abspath(os.path.join(_curr, ".."))
_root = os.path.abspath(os.path.join(_backend, ".."))

for p in [_root, _backend]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("JWT_SECRET_KEY", "sih-test-jwt-secret-key-32-chars-minimum-demo-2026")

from app.analytics_engine import (
    EarlyWarningForecastEngine,
    ForecastConfig,
    ProjectForecastResult,
    TrajectoryStatusEnum,
)
from app.data_loader import load_all_datasets
from fastapi.testclient import TestClient
from app.main import app


class TestEarlyWarningForecasting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_all_datasets()
        cls.projects_df = cls.data["projects"]
        cls.progress_df = cls.data["progress_updates"]
        cls.financials_df = cls.data["financials"]
        cls.engine = EarlyWarningForecastEngine()
        cls.client = TestClient(app)
        login_resp = cls.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"})
        token = login_resp.json()["access_token"]
        cls.auth_headers = {"Authorization": f"Bearer {token}"}

    def test_01_active_project_sufficient_history(self):
        """Verify active project with history returns valid velocity and dates."""
        # MPL-0001 (Ongoing)
        res = self.engine.evaluate_project("MPL-0001", self.projects_df, self.progress_df, self.financials_df)
        self.assertIsNotNone(res)
        self.assertEqual(res.project_id, "MPL-0001")
        self.assertGreater(res.velocity_pct_per_day, 0.0)
        self.assertIsNotNone(res.forecast_completion_date)
        self.assertIsNotNone(res.estimated_days_remaining)
        self.assertGreater(res.confidence, 0.0)
        self.assertIn("historical execution velocity", res.explanation)

    def test_02_completed_project(self):
        """Verify completed project returns actual outturn rather than pretending to forecast."""
        completed_pids = self.projects_df[self.projects_df["status"] == "Completed"]["project_id"].tolist()
        self.assertGreater(len(completed_pids), 0)
        pid = completed_pids[0]
        
        res = self.engine.evaluate_project(pid, self.projects_df, self.progress_df, self.financials_df)
        self.assertIsNotNone(res)
        self.assertEqual(res.trajectory_status, TrajectoryStatusEnum.COMPLETED)
        self.assertEqual(res.estimated_days_remaining, 0)
        self.assertEqual(res.confidence, 1.0)
        self.assertIn("COMPLETED", res.explanation)

    def test_03_insufficient_history(self):
        """Verify project with empty progress logs returns INSUFFICIENT_HISTORY without bias."""
        empty_progress = pd.DataFrame(columns=self.progress_df.columns)
        res = self.engine.evaluate_project("MPL-0001", self.projects_df, empty_progress, self.financials_df)
        self.assertIsNotNone(res)
        self.assertEqual(res.trajectory_status, TrajectoryStatusEnum.INSUFFICIENT_HISTORY)
        self.assertIsNone(res.forecast_completion_date)
        self.assertEqual(res.confidence, 0.0)

    def test_04_zero_velocity_stalled(self):
        """Verify stalled project (zero progress over elapsed days) is flagged as SEVERE_DELAY_RISK."""
        mock_projects = self.projects_df.copy()
        mock_projects.loc[mock_projects["project_id"] == "MPL-0001", "physical_progress_pct"] = 0.0
        
        res = self.engine.evaluate_project("MPL-0001", mock_projects, self.progress_df, self.financials_df)
        self.assertIsNotNone(res)
        self.assertEqual(res.trajectory_status, TrajectoryStatusEnum.SEVERE_DELAY_RISK)
        self.assertIn("CRITICAL STAGNATION", res.explanation)

    def test_05_ahead_of_schedule(self):
        """Verify fast projects ahead of schedule have negative delay days and ON_TRACK status."""
        results = self.engine.evaluate_all(self.projects_df, self.progress_df, self.financials_df)
        on_track = [r for r in results if r.trajectory_status == TrajectoryStatusEnum.ON_TRACK and r.forecast_delay_days is not None and r.forecast_delay_days < 0]
        self.assertGreater(len(on_track), 0)
        for r in on_track:
            self.assertLess(r.forecast_delay_days, 0)

    def test_06_delayed_project(self):
        """Verify lagging projects receive delay projections and LIKELY_DELAY / SEVERE_DELAY_RISK status."""
        results = self.engine.evaluate_all(self.projects_df, self.progress_df, self.financials_df)
        delayed = [r for r in results if r.trajectory_status in (TrajectoryStatusEnum.LIKELY_DELAY, TrajectoryStatusEnum.SEVERE_DELAY_RISK)]
        self.assertGreater(len(delayed), 0)

    def test_07_unknown_project_returns_404(self):
        """Verify API returns 404 for unknown project ID when authenticated."""
        resp = self.client.get("/api/analytics/forecast/UNKNOWN_PID_9999", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)

    def test_08_api_endpoints(self):
        """Verify GET /api/analytics/forecast and pagination."""
        resp = self.client.get("/api/analytics/forecast?limit=10", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 500)
        self.assertEqual(len(data["data"]), 10)
        self.assertIn("summary", data)

        # Single project endpoint
        resp_single = self.client.get("/api/analytics/forecast/MPL-0008", headers=self.auth_headers)
        self.assertEqual(resp_single.status_code, 200)
        self.assertEqual(resp_single.json()["project_id"], "MPL-0008")

    def test_09_regression_anomaly_rules(self):
        """Regression Test: Verify 31 rules still produce exactly 896 anomalies."""
        from app.cache import get_cache
        cache = get_cache()
        self.assertEqual(len(cache.all_anomalies), 896)
        self.assertEqual(cache.anomaly_summary.total_anomalies_detected, 896)

    def test_10_regression_risk_scores(self):
        """Regression Test: Verify risk scores with rule-priority weighting (average 13.68)."""
        from app.cache import get_cache
        cache = get_cache()
        self.assertAlmostEqual(cache.risk_summary.average_risk_score, 13.68, delta=0.05)
        self.assertEqual(cache.risk_summary.risk_level_counts["HIGH"], 26)
        self.assertEqual(cache.risk_summary.risk_level_counts["LOW"], 381)

    def test_11_regression_ml_outliers(self):
        """Regression Test: Verify ML Isolation Forest produces exactly 50 outliers."""
        from app.cache import get_cache
        cache = get_cache()
        self.assertEqual(cache.ml_summary.anomalous_projects_count, 50)


if __name__ == "__main__":
    unittest.main()
