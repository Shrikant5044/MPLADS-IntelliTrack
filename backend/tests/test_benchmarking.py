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
    BenchmarkConfig,
    BenchmarkStatusEnum,
    PeerHierarchyTierEnum,
    ProjectBenchmarkingEngine,
)
from app.data_loader import load_all_datasets
from fastapi.testclient import TestClient
from app.main import app


class TestComparableBenchmarking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_all_datasets()
        cls.projects_df = cls.data["projects"]
        cls.engine = ProjectBenchmarkingEngine()
        cls.client = TestClient(app)

    def test_01_sufficient_peers(self):
        """Verify project with sufficient peers returns valid statistics."""
        res = self.engine.evaluate_project("MPL-0001", self.projects_df)
        self.assertIsNotNone(res)
        self.assertEqual(res.project_id, "MPL-0001")
        self.assertGreaterEqual(res.peer_count, 3)
        self.assertIsNotNone(res.cost_ratio_vs_peer_median)
        self.assertIsNotNone(res.percentile_position)
        self.assertGreater(res.confidence, 0.0)
        self.assertIsNotNone(res.peer_stats)

    def test_02_insufficient_peers_handling(self):
        """Verify fallback disabled returns INSUFFICIENT_PEERS without fabricating values."""
        strict_config = BenchmarkConfig(
            min_peers=100, # Unattainable threshold in small cohort
            allow_state_fallback=False,
            allow_national_fallback=False,
        )
        strict_engine = ProjectBenchmarkingEngine(strict_config)
        res = strict_engine.evaluate_project("MPL-0001", self.projects_df)
        self.assertIsNotNone(res)
        self.assertEqual(res.benchmark_status, BenchmarkStatusEnum.INSUFFICIENT_PEERS)
        self.assertEqual(res.peer_hierarchy_tier, PeerHierarchyTierEnum.INSUFFICIENT)
        self.assertIsNone(res.cost_ratio_vs_peer_median)
        self.assertIsNone(res.percentile_position)
        self.assertEqual(res.confidence, 0.0)
        self.assertIn("Insufficient", res.explanation)

    def test_03_target_excluded_from_peers(self):
        """Verify the evaluated project is strictly excluded from its own peer group."""
        res = self.engine.evaluate_project("MPL-0001", self.projects_df)
        self.assertIsNotNone(res)
        self.assertNotIn("MPL-0001", res.sample_peer_project_ids)

    def test_04_same_category_filtering(self):
        """Verify all peers belong strictly to the same work category."""
        res = self.engine.evaluate_project("MPL-0001", self.projects_df)
        target_cat = self.projects_df[self.projects_df["project_id"] == "MPL-0001"]["work_category"].iloc[0]
        self.assertEqual(res.work_category, target_cat)
        
        # Inspect sample peers
        peers_df = self.projects_df[self.projects_df["project_id"].isin(res.sample_peer_project_ids)]
        for _, p in peers_df.iterrows():
            self.assertEqual(p["work_category"], target_cat)

    def test_05_district_preference(self):
        """Verify district peers are preferred if count >= min_peers."""
        grouped = self.projects_df.groupby(["district", "work_category"]).size()
        large_groups = grouped[grouped >= 4]
        self.assertGreater(len(large_groups), 0)
        dist, cat = large_groups.index[0]
        sample_pid = self.projects_df[(self.projects_df["district"] == dist) & (self.projects_df["work_category"] == cat)]["project_id"].iloc[0]
        
        res = self.engine.evaluate_project(sample_pid, self.projects_df)
        self.assertEqual(res.peer_hierarchy_tier, PeerHierarchyTierEnum.DISTRICT_CATEGORY)

    def test_06_high_deviation_project(self):
        """Verify cost outliers receive elevated status."""
        results = self.engine.evaluate_all(self.projects_df)
        high_deviations = [r for r in results if r.benchmark_status in (BenchmarkStatusEnum.HIGH_DEVIATION, BenchmarkStatusEnum.EXTREME_DEVIATION)]
        self.assertGreater(len(high_deviations), 0)
        for h in high_deviations:
            self.assertGreaterEqual(h.cost_ratio_vs_peer_median, 1.60)
            self.assertGreaterEqual(h.percentile_position, 50.0)

    def test_07_normal_project(self):
        """Verify nominal projects are classified as NORMAL."""
        results = self.engine.evaluate_all(self.projects_df)
        normal_projects = [r for r in results if r.benchmark_status == BenchmarkStatusEnum.NORMAL]
        self.assertGreater(len(normal_projects), 200)

    def test_08_unknown_project_returns_404(self):
        """Verify API returns 404 for unknown project ID."""
        resp = self.client.get("/api/analytics/benchmark/INVALID_PID_9999")
        self.assertEqual(resp.status_code, 404)

    def test_09_api_endpoints(self):
        """Verify GET /api/analytics/benchmark and pagination."""
        resp = self.client.get("/api/analytics/benchmark?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 500)
        self.assertEqual(len(data["data"]), 10)
        self.assertIn("summary", data)

        # Single project endpoint
        resp_single = self.client.get("/api/analytics/benchmark/MPL-0008")
        self.assertEqual(resp_single.status_code, 200)
        self.assertEqual(resp_single.json()["project_id"], "MPL-0008")

    def test_10_regression_anomaly_rules(self):
        """Regression Test: Verify 31 rules still produce exactly 896 anomalies."""
        from app.cache import get_cache
        cache = get_cache()
        self.assertEqual(len(cache.all_anomalies), 896)
        self.assertEqual(cache.anomaly_summary.total_anomalies_detected, 896)

    def test_11_regression_risk_scores(self):
        """Regression Test: Verify risk scores with rule-priority weighting (average 13.68)."""
        from app.cache import get_cache
        cache = get_cache()
        self.assertAlmostEqual(cache.risk_summary.average_risk_score, 13.68, delta=0.05)
        self.assertEqual(cache.risk_summary.risk_level_counts["HIGH"], 26)
        self.assertEqual(cache.risk_summary.risk_level_counts["LOW"], 381)

    def test_12_regression_ml_outliers(self):
        """Regression Test: Verify ML Isolation Forest produces exactly 50 outliers."""
        from app.cache import get_cache
        cache = get_cache()
        self.assertEqual(cache.ml_summary.anomalous_projects_count, 50)


if __name__ == "__main__":
    unittest.main()
