import sys
import os
import time
import json
import unittest
import pandas as pd
import numpy as np

# Ensure paths
_curr = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.abspath(os.path.join(_curr, ".."))
_root = os.path.abspath(os.path.join(_backend, ".."))

for p in [_root, _backend]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("JWT_SECRET_KEY", "sih-test-jwt-secret-key-32-chars-minimum-demo-2026")

from app.cache import get_cache
from app.data_loader import load_all_datasets
from app.anomaly_engine import AnomalyEngine, AnomalyTypeEnum, SeverityEnum
from app.risk_engine import RiskEngine, RiskConfig, RiskLevelEnum
from app.analytics_engine import (
    ProjectBenchmarkingEngine,
    BenchmarkConfig,
    BenchmarkStatusEnum,
    EarlyWarningForecastEngine,
    ForecastConfig,
    TrajectoryStatusEnum,
    DistrictAnalyticsEngine,
    PrioritizedAuditQueueEngine,
    AuditUrgencyEnum,
    InvestigationTypeEnum,
)
from ml.predict import MLInferenceService
from fastapi.testclient import TestClient
from app.main import app


class ComprehensiveSeniorAuditSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_all_datasets()
        cls.projects_df = cls.data["projects"]
        cls.financials_df = cls.data["financials"]
        cls.progress_df = cls.data["progress_updates"]
        cls.payments_df = cls.data["payments"]
        cls.vendors_df = cls.data["vendors"]
        cls.agencies_df = cls.data["implementing_agencies"]
        cls.evidence_df = cls.data["evidence"]
        cls.compliance_df = cls.data["compliance"]
        
        cls.cache = get_cache()
        cls.client = TestClient(app)

    # =========================================================================
    # 1. DATA INTEGRITY AUDIT
    # =========================================================================
    def test_01_data_layer_integrity(self):
        """Verify 100% primary-key uniqueness, foreign-key integrity, and value bounds."""
        # 1. Primary keys
        self.assertEqual(self.projects_df["project_id"].nunique(), len(self.projects_df))
        self.assertEqual(self.financials_df["project_id"].nunique(), len(self.financials_df))
        self.assertEqual(self.progress_df["progress_id"].nunique(), len(self.progress_df))
        self.assertEqual(self.payments_df["payment_id"].nunique(), len(self.payments_df))
        self.assertEqual(self.vendors_df["vendor_id"].nunique(), len(self.vendors_df))
        self.assertEqual(self.agencies_df["agency_id"].nunique(), len(self.agencies_df))
        self.assertEqual(self.evidence_df["evidence_id"].nunique(), len(self.evidence_df))
        self.assertEqual(self.compliance_df["compliance_id"].nunique(), len(self.compliance_df))

        # 2. Foreign keys -> projects.csv
        pids = set(self.projects_df["project_id"])
        self.assertEqual(set(self.financials_df["project_id"]) - pids, set())
        self.assertEqual(set(self.progress_df["project_id"]) - pids, set())
        self.assertEqual(set(self.payments_df["project_id"]) - pids, set())
        self.assertEqual(set(self.evidence_df["project_id"]) - pids, set())
        self.assertEqual(set(self.compliance_df["project_id"]) - pids, set())

        # 3. Foreign keys -> vendors & agencies
        vids = set(self.vendors_df["vendor_id"])
        aids = set(self.agencies_df["agency_id"])
        self.assertEqual(set(self.projects_df["vendor_id"].dropna()) - vids, set())
        self.assertEqual(set(self.projects_df["agency_id"].dropna()) - aids, set())

        # 4. Numerical value bounds
        self.assertTrue((self.projects_df["sanctioned_amount_lakh"] >= 0).all())
        self.assertTrue((self.projects_df["expenditure_lakh"] >= 0).all())
        self.assertTrue((self.projects_df["physical_progress_pct"] >= 0).all())
        self.assertTrue((self.projects_df["physical_progress_pct"] <= 100.0).all())
        self.assertTrue((self.payments_df["amount_lakh"] >= 0).all())

    # =========================================================================
    # 2. ANOMALY ENGINE — 31 RULES VERIFICATION
    # =========================================================================
    def test_02_all_31_rules_active_and_counted(self):
        """Verify all 31 rules execute and match calibrated reference outputs."""
        engine = AnomalyEngine()
        anomalies = engine.run_all(
            self.projects_df,
            self.financials_df,
            self.payments_df,
            self.progress_df,
            self.compliance_df,
            self.evidence_df,
        )
        self.assertEqual(len(anomalies), 896)
        summary = engine.get_summary(anomalies, len(self.projects_df))
        self.assertEqual(len(summary.anomalies_by_type), 31)
        self.assertEqual(len(AnomalyTypeEnum), 31)
        
        # Verify specific key rule counts
        expected_counts = {
            "EXPENDITURE_EXCEEDS_SANCTION": 39,
            "COST_OVERRUN": 33,
            "ABNORMALLY_HIGH_UTILIZATION": 58,
            "ABNORMALLY_LOW_UTILIZATION": 14,
            "PROGRESS_FINANCIAL_MISMATCH": 98,
            "UNUSUAL_EXPENDITURE_PATTERN": 23,
            "PROJECT_DELAY": 33,
            "SLOW_PROGRESS": 63,
            "NO_RECENT_PROGRESS_UPDATE": 29,
            "SUDDEN_PROGRESS_JUMP": 5,
            "MILESTONE_LAG": 62,
            "COMPLETION_RISK": 23,
            "LARGE_PAYMENT": 25,
            "RAPID_MULTIPLE_PAYMENTS": 47,
            "REPEATED_PAYMENT_AMOUNT": 17,
            "PAYMENT_BEFORE_MILESTONE": 36,
            "PAYMENT_LOW_PROGRESS": 8,
            "DEADLINE_PAYMENT_CONCENTRATION": 90,
            "VENDOR_HIGH_DELAY_RATE": 13,
            "VENDOR_HIGH_COST_ANOMALY_RATE": 9,
            "VENDOR_HIGH_PAYMENT_ANOMALY_RATE": 2,
            "VENDOR_PROJECT_CONCENTRATION": 14,
            "AGENCY_HIGH_ANOMALY_RATE": 30,
            "AGENCY_REPEATED_ISSUES": 25,
            "POTENTIAL_DUPLICATE_WORK": 24,
            "MISSING_SANCTION_DOCUMENT": 13,
            "MISSING_PROGRESS_DOCUMENT": 18,
            "MISSING_INSPECTION_REPORT": 15,
            "MISSING_PAYMENT_SUPPORT": 21,
            "MISSING_COMPLETION_CERTIFICATE": 4,
            "COMPLIANCE_DOCUMENT_GAP": 5,
        }
        for r_name, exp_cnt in expected_counts.items():
            act_cnt = summary.anomalies_by_type.get(r_name, 0)
            self.assertEqual(act_cnt, exp_cnt, f"Mismatch in rule {r_name}: expected {exp_cnt}, got {act_cnt}")

    # =========================================================================
    # 3. DUPLICATE WORK INTELLIGENCE
    # =========================================================================
    def test_03_duplicate_work_intelligence(self):
        """Verify duplicate work detection requires composite multi-factor similarity."""
        dup_anoms = [a for a in self.cache.all_anomalies if a.anomaly_type == AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK]
        self.assertEqual(len(dup_anoms), 24)
        
        # Verify pairs are reciprocal
        pairs = set()
        for a in dup_anoms:
            p1 = a.project_id
            p2 = a.evidence["matched_project_id"]
            pairs.add(tuple(sorted([p1, p2])))
            self.assertGreaterEqual(a.evidence["similarity_score"], 0.65)
            self.assertLessEqual(a.evidence["distance_km"], 3.0)
            self.assertTrue(a.evidence["category_match"])
        self.assertEqual(len(pairs), 12)

    # =========================================================================
    # 4. COMPARABLE BENCHMARKING
    # =========================================================================
    def test_04_comparable_benchmarking(self):
        """Verify peer resolution and empirical percentile ranking."""
        benchmarks = self.cache.benchmark_results
        self.assertEqual(len(benchmarks), 500)
        
        summary = self.cache.benchmark_summary
        self.assertEqual(summary.total_projects_evaluated, 500)
        self.assertEqual(summary.insufficient_peers_count, 0)
        self.assertEqual(summary.status_counts["EXTREME_DEVIATION"], 30)
        self.assertEqual(summary.status_counts["HIGH_DEVIATION"], 62)
        self.assertEqual(summary.status_counts["NORMAL"], 232)

    # =========================================================================
    # 5. RISK ENGINE & ML FUSION
    # =========================================================================
    def test_05_risk_engine_bounds_and_fusion(self):
        """Verify risk weights sum, score bounds [0, 100], and ML capping <= 5 points."""
        cfg = RiskConfig()
        rule_sum = cfg.weight_financial + cfg.weight_progress + cfg.weight_payment + cfg.weight_vendor + cfg.weight_agency + cfg.weight_duplicate_geo + cfg.weight_compliance
        self.assertEqual(rule_sum, 100.0)
        self.assertEqual(cfg.weight_ml, 5.0)

        profiles = self.cache.risk_profiles
        scores = [p.risk_score for p in profiles]
        self.assertEqual(min(scores), 0)
        self.assertEqual(max(scores), 72)
        
        for p in profiles:
            self.assertTrue(0 <= p.risk_score <= 100)
            if p.ml_signal:
                self.assertTrue(0 <= p.ml_signal.contribution <= 5)

    # =========================================================================
    # 6. ML ISOLATION FOREST ENGINE
    # =========================================================================
    def test_06_ml_engine_decontamination(self):
        """Verify exactly 29 decontaminated features and zero leaked rule aggregates."""
        with open("ml/model_artifacts/features.json") as f:
            f_json = json.load(f)
        feat_names = f_json["feature_names"]
        self.assertEqual(len(feat_names), 29)
        
        banned = ["latitude", "longitude", "reported_cost_overrun_pct", "vendor_delay_rate", "vendor_cost_overrun_rate", "agency_problem_rate", "risk_score", "anomaly_count"]
        for b in banned:
            self.assertNotIn(b, feat_names)

        preds = self.cache.ml_predictions
        self.assertEqual(len(preds), 500)
        outliers = [p for p in preds if p.ml_anomaly_flag]
        self.assertEqual(len(outliers), 50)

    # =========================================================================
    # 7. FORECASTING & TRAJECTORY ENGINE
    # =========================================================================
    def test_07_forecasting_trajectory(self):
        """Verify empirical velocity, completion dates, and graceful status handling."""
        forecasts = self.cache.forecast_results
        self.assertEqual(len(forecasts), 500)
        
        summary = self.cache.forecast_summary
        self.assertEqual(summary.completed_projects, 138)
        self.assertEqual(summary.active_projects, 362)
        self.assertEqual(summary.status_counts["COMPLETED"], 138)
        self.assertEqual(summary.status_counts["ON_TRACK"], 110)
        self.assertEqual(summary.status_counts["SEVERE_DELAY_RISK"], 203)
        self.assertEqual(summary.status_counts["LIKELY_DELAY"], 33)
        self.assertEqual(summary.status_counts["WATCH"], 16)

    # =========================================================================
    # 8. DISTRICT ANALYTICS
    # =========================================================================
    def test_08_district_analytics(self):
        """Verify all 30 districts are accurately aggregated and sorted by risk."""
        districts = self.cache.district_profiles
        self.assertEqual(len(districts), 30)
        for i in range(len(districts) - 1):
            self.assertGreaterEqual(districts[i].average_risk_score, districts[i+1].average_risk_score)
        
        total_p = sum(d.total_projects for d in districts)
        self.assertEqual(total_p, 500)

    # =========================================================================
    # 9. PRIORITIZED AUDIT QUEUE
    # =========================================================================
    def test_09_audit_queue(self):
        """Verify decision-support priority queue ranks high-risk targets first."""
        queue = self.cache.audit_queue_items
        self.assertEqual(len(queue), 500)
        self.assertEqual(queue[0].project_id, "MPL-0358")
        self.assertEqual(queue[0].risk_score, 72)
        self.assertEqual(queue[0].urgency, AuditUrgencyEnum.HIGH_URGENCY)

    # =========================================================================
    # 10. API ROBUSTNESS & SECURITY
    # =========================================================================
    def test_10_api_security_and_error_handling(self):
        """Verify 200, 404, 422, and path traversal protection across all endpoints."""
        valid_eps = [
            "/health",
            "/api/projects?limit=5",
            "/api/anomalies?limit=5",
            "/api/risk?limit=5",
            "/api/ml/anomalies?limit=5",
            "/api/analytics/benchmark?limit=5",
            "/api/analytics/forecast?limit=5",
            "/api/analytics/audit-queue?limit=5",
            "/api/analytics/districts",
        ]
        for ep in valid_eps:
            resp = self.client.get(ep)
            self.assertEqual(resp.status_code, 200, f"Failed on valid endpoint: {ep}")

        # 404 on unknown project
        self.assertEqual(self.client.get("/api/anomalies/NONEXISTENT").status_code, 404)
        self.assertEqual(self.client.get("/api/risk/NONEXISTENT").status_code, 404)
        self.assertEqual(self.client.get("/api/ml/anomalies/NONEXISTENT").status_code, 404)
        self.assertEqual(self.client.get("/api/analytics/benchmark/NONEXISTENT").status_code, 404)
        self.assertEqual(self.client.get("/api/analytics/forecast/NONEXISTENT").status_code, 404)

        # 422 on invalid parameters
        self.assertEqual(self.client.get("/api/projects?limit=-10").status_code, 422)
        self.assertEqual(self.client.get("/api/anomalies?limit=0").status_code, 422)
        self.assertEqual(self.client.get("/api/anomalies?severity=INVALID_SEV").status_code, 422)

        # Path traversal resistance
        resp_pt = self.client.get("/api/risk/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(resp_pt.status_code, (404, 422))

    # =========================================================================
    # 11. CROSS-ENGINE CONSISTENCY
    # =========================================================================
    def test_11_cross_engine_consistency(self):
        """Verify anomaly engine, risk engine, ML, forecasting, and audit queue have 100% ID parity."""
        c = self.cache
        p_ids = set(r["project_id"] for r in c.projects_records)
        self.assertEqual(len(p_ids), 500)
        
        self.assertEqual(set(c.risk_by_project.keys()), p_ids)
        self.assertEqual(set(c.ml_by_project.keys()), p_ids)
        self.assertEqual(set(c.benchmark_by_project.keys()), p_ids)
        self.assertEqual(set(c.forecast_by_project.keys()), p_ids)
        self.assertEqual(set(i.project_id for i in c.audit_queue_items), p_ids)


if __name__ == "__main__":
    unittest.main()
