import sys
import os
import time
import json
import unittest
import pandas as pd
import numpy as np
from datetime import datetime

# Paths
_curr = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.abspath(os.path.join(_curr, ".."))
_root = os.path.abspath(os.path.join(_backend, ".."))

for p in [_root, _backend]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.cache import get_cache, IntelligenceCache
from app.data_loader import load_all_datasets
from app.anomaly_engine import AnomalyEngine, AnomalyTypeEnum, SeverityEnum, ThresholdConfig
from app.risk_engine import RiskEngine, RiskConfig, RiskLevelEnum, RiskCategoryEnum, ANOMALY_CATEGORY_MAPPING, RULE_PRIORITY_WEIGHTS, CATEGORY_MAX_RULE_WEIGHT
from app.risk_engine.scorer import ProjectScorer
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
from ml.features import extract_project_features
from fastapi.testclient import TestClient
from app.main import app


class MasterBackendAuditSuite(unittest.TestCase):
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

    # -------------------------------------------------------------
    # PHASE 1: DATA INTEGRITY
    # -------------------------------------------------------------
    def test_phase1_dataset_integrity(self):
        # 1. Row & column counts
        self.assertEqual(len(self.projects_df), 500)
        self.assertEqual(len(self.financials_df), 500)
        self.assertEqual(len(self.progress_df), 2475)
        self.assertEqual(len(self.payments_df), 4227)
        self.assertEqual(len(self.vendors_df), 80)
        self.assertEqual(len(self.agencies_df), 30)
        self.assertEqual(len(self.evidence_df), 1259)
        self.assertEqual(len(self.compliance_df), 2500)

        # 2. PK uniqueness
        self.assertEqual(self.projects_df["project_id"].nunique(), 500)
        self.assertEqual(self.financials_df["project_id"].nunique(), 500)
        self.assertEqual(self.progress_df["progress_id"].nunique(), 2475)
        self.assertEqual(self.payments_df["payment_id"].nunique(), 4227)

        # 3. Foreign key integrity -> 0 orphans
        pids = set(self.projects_df["project_id"])
        self.assertEqual(set(self.financials_df["project_id"]) - pids, set())
        self.assertEqual(set(self.progress_df["project_id"]) - pids, set())
        self.assertEqual(set(self.payments_df["project_id"]) - pids, set())
        self.assertEqual(set(self.evidence_df["project_id"]) - pids, set())
        self.assertEqual(set(self.compliance_df["project_id"]) - pids, set())

        # 4. Values validity
        self.assertTrue((self.projects_df["sanctioned_amount_lakh"] >= 0).all())
        self.assertTrue((self.projects_df["expenditure_lakh"] >= 0).all())
        self.assertTrue((self.projects_df["physical_progress_pct"] >= 0).all())
        self.assertTrue((self.projects_df["physical_progress_pct"] <= 100.0).all())

    # -------------------------------------------------------------
    # PHASE 2 & 3: 31 ANOMALY RULES & REGRESSION
    # -------------------------------------------------------------
    def test_phase2_3_anomaly_rules_regression(self):
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
        
        anom_projects = set(a.project_id for a in anomalies)
        self.assertEqual(len(anom_projects), 313)

        summary = engine.get_summary(anomalies, len(self.projects_df))
        self.assertEqual(len(summary.anomalies_by_type), 31)

        expected_rule_counts = {
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
        for r_name, exp_cnt in expected_rule_counts.items():
            act_cnt = summary.anomalies_by_type.get(r_name, 0)
            self.assertEqual(act_cnt, exp_cnt, f"Rule {r_name} failed: expected {exp_cnt}, got {act_cnt}")

    # -------------------------------------------------------------
    # PHASE 4: DUPLICATE GEOSPATIAL ENGINE
    # -------------------------------------------------------------
    def test_phase4_duplicate_engine(self):
        dup_anoms = [a for a in self.cache.all_anomalies if a.anomaly_type == AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK]
        self.assertEqual(len(dup_anoms), 24)
        pairs = set()
        for a in dup_anoms:
            p1 = a.project_id
            p2 = a.evidence["matched_project_id"]
            pairs.add(tuple(sorted([p1, p2])))
            self.assertGreaterEqual(a.evidence["similarity_score"], 0.65)
            self.assertLessEqual(a.evidence["distance_km"], 3.0)
            self.assertTrue(a.evidence["category_match"])
        self.assertEqual(len(pairs), 12)

    # -------------------------------------------------------------
    # PHASE 5: COMPLIANCE ENGINE
    # -------------------------------------------------------------
    def test_phase5_compliance_engine(self):
        comp_types = {
            AnomalyTypeEnum.MISSING_SANCTION_DOCUMENT,
            AnomalyTypeEnum.MISSING_PROGRESS_DOCUMENT,
            AnomalyTypeEnum.MISSING_INSPECTION_REPORT,
            AnomalyTypeEnum.MISSING_PAYMENT_SUPPORT,
            AnomalyTypeEnum.MISSING_COMPLETION_CERTIFICATE,
            AnomalyTypeEnum.COMPLIANCE_DOCUMENT_GAP,
        }
        comp_anoms = [a for a in self.cache.all_anomalies if a.anomaly_type in comp_types]
        self.assertEqual(len(comp_anoms), 76)

    # -------------------------------------------------------------
    # PHASE 6 & 7: RISK ENGINE & RULE PRIORITY WEIGHTING
    # -------------------------------------------------------------
    def test_phase6_7_risk_engine(self):
        cfg = RiskConfig()
        cat_sum = cfg.weight_financial + cfg.weight_progress + cfg.weight_payment + cfg.weight_vendor + cfg.weight_agency + cfg.weight_duplicate_geo + cfg.weight_compliance
        self.assertEqual(cat_sum, 100.0)
        self.assertEqual(cfg.weight_ml, 5.0)

        # Verify all 31 rule weights are mapped
        self.assertEqual(len(RULE_PRIORITY_WEIGHTS), 31)
        for r_type, w in RULE_PRIORITY_WEIGHTS.items():
            self.assertTrue(3 <= w <= 8)

        profiles = self.cache.risk_profiles
        self.assertEqual(len(profiles), 500)
        scores = [p.risk_score for p in profiles]
        self.assertTrue(all(0 <= s <= 100 for s in scores))
        self.assertEqual(min(scores), 0)
        self.assertEqual(max(scores), 72)
        self.assertAlmostEqual(float(np.mean(scores)), 13.68, delta=0.05)

        # Isolated edge cases
        scorer = ProjectScorer(cfg)
        clean_prof = scorer.score("TEST-001", [])
        self.assertEqual(clean_prof.risk_score, 0)
        self.assertEqual(clean_prof.risk_level, RiskLevelEnum.LOW)

    # -------------------------------------------------------------
    # PHASE 8 & 9: ML PIPELINE & ISOLATION FOREST
    # -------------------------------------------------------------
    def test_phase8_9_ml_engine(self):
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

    # -------------------------------------------------------------
    # PHASE 11: FORECASTING ENGINE
    # -------------------------------------------------------------
    def test_phase11_forecasting(self):
        forecasts = self.cache.forecast_results
        self.assertEqual(len(forecasts), 500)
        summary = self.cache.forecast_summary
        self.assertEqual(summary.total_projects, 500)
        self.assertEqual(summary.completed_projects, 138)
        self.assertEqual(summary.active_projects, 362)
        self.assertEqual(summary.status_counts["COMPLETED"], 138)
        self.assertEqual(summary.status_counts["ON_TRACK"], 110)
        self.assertEqual(summary.status_counts["SEVERE_DELAY_RISK"], 203)

    # -------------------------------------------------------------
    # PHASE 12: DISTRICT ANALYTICS
    # -------------------------------------------------------------
    def test_phase12_district_analytics(self):
        districts = self.cache.district_profiles
        self.assertEqual(len(districts), 30)
        self.assertEqual(sum(d.total_projects for d in districts), 500)
        for i in range(len(districts) - 1):
            self.assertGreaterEqual(districts[i].average_risk_score, districts[i+1].average_risk_score)

    # -------------------------------------------------------------
    # PHASE 13: AUDIT QUEUE
    # -------------------------------------------------------------
    def test_phase13_audit_queue(self):
        queue = self.cache.audit_queue_items
        self.assertEqual(len(queue), 500)
        self.assertEqual(queue[0].project_id, "MPL-0358")
        self.assertEqual(queue[0].risk_score, 72)
        self.assertEqual(queue[0].urgency, AuditUrgencyEnum.HIGH_URGENCY)

    # -------------------------------------------------------------
    # PHASE 14: RELATED-PROJECT BENCHMARKING
    # -------------------------------------------------------------
    def test_phase14_benchmarking(self):
        benchmarks = self.cache.benchmark_results
        self.assertEqual(len(benchmarks), 500)
        summary = self.cache.benchmark_summary
        self.assertEqual(summary.total_projects_evaluated, 500)
        self.assertEqual(summary.insufficient_peers_count, 0)
        self.assertEqual(summary.tier_counts["DISTRICT_CATEGORY"], 119)
        self.assertEqual(summary.tier_counts["STATE_CATEGORY"], 342)
        self.assertEqual(summary.tier_counts["NATIONAL_CATEGORY"], 39)

    # -------------------------------------------------------------
    # PHASE 15 & 16: CACHE & API TESTING
    # -------------------------------------------------------------
    def test_phase15_16_cache_and_apis(self):
        endpoints = [
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
        for ep in endpoints:
            resp = self.client.get(ep)
            self.assertEqual(resp.status_code, 200, f"Endpoint {ep} returned {resp.status_code}")

        # Detail endpoints
        self.assertEqual(self.client.get("/api/anomalies/MPL-0008").status_code, 200)
        self.assertEqual(self.client.get("/api/risk/MPL-0008").status_code, 200)
        self.assertEqual(self.client.get("/api/ml/anomalies/MPL-0008").status_code, 200)
        self.assertEqual(self.client.get("/api/analytics/benchmark/MPL-0008").status_code, 200)
        self.assertEqual(self.client.get("/api/analytics/forecast/MPL-0008").status_code, 200)

        # 404 & 422 error handling
        self.assertEqual(self.client.get("/api/risk/NONEXISTENT").status_code, 404)
        self.assertEqual(self.client.get("/api/projects?limit=-5").status_code, 422)


if __name__ == "__main__":
    unittest.main()
