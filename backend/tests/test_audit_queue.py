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
    AuditUrgencyEnum,
    InvestigationTypeEnum,
    PrioritizedAuditQueueEngine,
)
from app.cache import get_cache
from fastapi.testclient import TestClient
from app.main import app


class TestPrioritizedAuditQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = get_cache()
        cls.client = TestClient(app)
        cls.engine = PrioritizedAuditQueueEngine()
        login_resp = cls.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"})
        token = login_resp.json()["access_token"]
        cls.auth_headers = {"Authorization": f"Bearer {token}"}

    def test_01_priority_one_is_highest_risk_project(self):
        """Verify priority #1 item is the highest risk project (MPL-0358)."""
        queue = self.cache.audit_queue_items
        self.assertGreater(len(queue), 0)
        top = queue[0]
        self.assertEqual(top.priority_rank, 1)
        self.assertEqual(top.project_id, "MPL-0358")
        self.assertEqual(top.risk_score, 72)
        self.assertEqual(top.urgency, AuditUrgencyEnum.HIGH_URGENCY)
        self.assertIn("CRITICAL", top.decision_support_rationale)

    def test_02_deterministic_ranking_order(self):
        """Verify priority queue is strictly sorted by risk score descending."""
        queue = self.cache.audit_queue_items
        for i in range(len(queue) - 1):
            self.assertGreaterEqual(queue[i].risk_score, queue[i + 1].risk_score)

    def test_03_no_duplicate_projects_in_queue(self):
        """Verify each project appears exactly once in the queue."""
        queue = self.cache.audit_queue_items
        pids = [item.project_id for item in queue]
        self.assertEqual(len(pids), len(set(pids)))
        self.assertEqual(len(pids), 500)

    def test_04_investigation_types_assigned(self):
        """Verify multi-domain anomalous projects receive targeted investigation types."""
        queue = self.cache.audit_queue_items
        top = queue[0] # MPL-0358
        self.assertGreaterEqual(len(top.recommended_investigation_types), 3)
        self.assertIn(InvestigationTypeEnum.PHYSICAL_INSPECTION, top.recommended_investigation_types)
        self.assertIn(InvestigationTypeEnum.PAYMENT_VERIFICATION, top.recommended_investigation_types)
        self.assertIn(InvestigationTypeEnum.COMPLIANCE_REVIEW, top.recommended_investigation_types)

    def test_05_api_filters_and_pagination(self):
        """Verify GET /api/analytics/audit-queue filters by risk_level, urgency, and investigation_type."""
        # Risk level filter
        resp_high = self.client.get("/api/analytics/audit-queue?risk_level=HIGH", headers=self.auth_headers)
        self.assertEqual(resp_high.status_code, 200)
        data_high = resp_high.json()
        self.assertEqual(data_high["total"], 26)
        self.assertEqual(data_high["data"][0]["project_id"], "MPL-0358")

        # Investigation type filter
        resp_dup = self.client.get("/api/analytics/audit-queue?investigation_type=DUPLICATE_GEO_VERIFICATION", headers=self.auth_headers)
        self.assertEqual(resp_dup.status_code, 200)
        data_dup = resp_dup.json()
        self.assertEqual(data_dup["total"], 24)

        # Pagination
        resp_page = self.client.get("/api/analytics/audit-queue?limit=15&offset=0", headers=self.auth_headers)
        self.assertEqual(resp_page.status_code, 200)
        self.assertEqual(len(resp_page.json()["data"]), 15)

    def test_06_district_analytics_endpoint(self):
        """Verify GET /api/analytics/districts returns all 30 districts ranked by risk."""
        resp = self.client.get("/api/analytics/districts", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 30)
        self.assertEqual(len(data["data"]), 30)
        self.assertIn("national_average_district_risk", data["summary"])


if __name__ == "__main__":
    unittest.main()
