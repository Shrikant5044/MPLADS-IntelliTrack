import unittest
from fastapi.testclient import TestClient
import sys, os

_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, "..", ".."))
_backend = os.path.join(_root, "backend")
for p in [_root, _backend]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("JWT_SECRET_KEY", "sih-test-jwt-secret-key-32-chars-minimum-demo-2026")

from app.main import app
from app.cache import get_cache
from app.auth.store import get_user_store
from app.investigation.store import get_investigation_store


class TestAuthInvestigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.cache = get_cache()
        cls.user_store = get_user_store()
        cls.inv_store = get_investigation_store()

    # 1. AUTHENTICATION TESTS
    def test_01_valid_login_mospi(self):
        resp = self.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "MOSPI_OFFICER")
        self.assertIsNone(data["user"]["assigned_district"])

    def test_02_valid_login_district_authority(self):
        resp = self.client.post("/api/auth/login", json={"username": "district_officer_04", "password": "District@2026"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "DISTRICT_AUTHORITY")
        self.assertEqual(data["user"]["assigned_district"], "District-04")

    def test_03_invalid_login(self):
        resp = self.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "WrongPassword"})
        self.assertEqual(resp.status_code, 401)

    def test_04_auth_me_endpoint(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"})
        token = login_resp.json()["access_token"]
        
        me_resp = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["username"], "mospi_officer")

    # 2. AUTHORIZATION & RBAC SCOPING
    def test_05_mospi_access_all_projects(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"})
        token = login_resp.json()["access_token"]
        
        resp = self.client.get("/api/projects?limit=500", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], 500)

    def test_06_district_authority_scoped_access(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "district_officer_04", "password": "District@2026"})
        token = login_resp.json()["access_token"]
        
        # When district authority requests projects, backend returns only District-04
        resp = self.client.get("/api/projects?limit=500", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        for p in data:
            self.assertEqual(p["district"], "District-04")

    def test_07_district_authority_cross_district_rejected(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "district_officer_04", "password": "District@2026"})
        token = login_resp.json()["access_token"]
        
        # Attempting to query another district returns 403 Forbidden
        resp = self.client.get("/api/projects?district=District-07", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 403)

        resp_aq = self.client.get("/api/analytics/audit-queue?district=District-12", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp_aq.status_code, 403)

    # 3. ADMIN USER MANAGEMENT
    def test_08_admin_user_management(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "admin_user", "password": "Admin@2026"})
        token = login_resp.json()["access_token"]
        
        # List users
        resp_list = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp_list.status_code, 200)
        
        # Create a new district authority user
        new_user = {
            "username": "district_officer_09",
            "email": "officer09@district.gov.in",
            "full_name": "Shri Vikram Rathore",
            "role": "DISTRICT_AUTHORITY",
            "assigned_district": "District-09",
            "assigned_state": "Rajasthan",
            "password": "Password@123",
            "is_active": True
        }
        resp_create = self.client.post("/api/admin/users", json=new_user, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp_create.status_code, 200)
        self.assertEqual(resp_create.json()["assigned_district"], "District-09")

    # 4. INVESTIGATION LIFECYCLE & AUDIT TRAIL
    def test_09_investigation_workflow(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"})
        token = login_resp.json()["access_token"]
        
        # Check pre-seeded investigation for MPL-0358
        resp_inv = self.client.get("/api/investigations/project/MPL-0358", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp_inv.status_code, 200)
        inv_data = resp_inv.json()
        self.assertEqual(inv_data["project_id"], "MPL-0358")
        self.assertEqual(inv_data["status"], "IN_PROGRESS")
        self.assertGreaterEqual(len(inv_data["audit_trail"]), 3)

        # Update progress
        inv_id = inv_data["investigation_id"]
        resp_prog = self.client.put(
            f"/api/investigations/{inv_id}/progress",
            json={"progress_percentage": 75, "comment": "Plinth verification completed."},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(resp_prog.status_code, 200)
        self.assertEqual(resp_prog.json()["progress_percentage"], 75)

        # Add finding
        resp_fnd = self.client.post(
            f"/api/investigations/{inv_id}/findings",
            json={"finding_text": "Material supply invoices match state schedule rates.", "evidence_notes": "Bill voucher BV-88"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(resp_fnd.status_code, 200)
        self.assertEqual(len(resp_fnd.json()["findings"]), 2)

    # 5. REGRESSION INVARIANTS
    def test_10_regression_intelligence_invariants(self):
        # 31 anomaly rules & 896 detections
        self.assertEqual(len(self.cache.all_anomalies), 896)
        distinct_rules = set(a.anomaly_type.value for a in self.cache.all_anomalies)
        self.assertEqual(len(distinct_rules), 31)

        # 50 ML outliers
        ml_outliers = sum(1 for m in self.cache.ml_predictions if m.ml_anomaly_flag)
        self.assertEqual(ml_outliers, 50)

        # Risk distribution & top project
        levels = [p.risk_level.value for p in self.cache.risk_profiles]
        self.assertEqual(levels.count("LOW"), 381)
        self.assertEqual(levels.count("MEDIUM"), 93)
        self.assertEqual(levels.count("HIGH"), 26)
        self.assertEqual(levels.count("CRITICAL"), 0)
        self.assertEqual(self.cache.risk_profiles[0].project_id, "MPL-0358")
        self.assertEqual(self.cache.risk_profiles[0].risk_score, 72)

    # 6. SECURITY CONFIGURATION & CORS TESTS
    def test_11_cors_origins_parsing(self):
        from app.config import Settings
        
        # Comma-separated string parsing
        s1 = Settings(CORS_ORIGINS="https://mplads.onrender.com,https://frontend.vercel.app")
        self.assertEqual(s1.CORS_ORIGINS, ["https://mplads.onrender.com", "https://frontend.vercel.app"])

        # JSON array string parsing
        s2 = Settings(CORS_ORIGINS='["https://mplads.onrender.com"]')
        self.assertEqual(s2.CORS_ORIGINS, ["https://mplads.onrender.com"])

        # Default fallback
        s3 = Settings(CORS_ORIGINS="")
        self.assertIn("*", s3.CORS_ORIGINS)
        self.assertIn("http://localhost:5173", s3.CORS_ORIGINS)

    def test_12_jwt_secret_key_environment_enforcement(self):
        # Verify that loading security without JWT_SECRET_KEY raises RuntimeError
        import subprocess
        code = (
            "import os, sys; "
            "sys.path.insert(0, 'backend'); "
            "os.environ.pop('JWT_SECRET_KEY', None); "
            "from app.auth.security import JWT_SECRET_KEY"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CRITICAL SECURITY CONFIGURATION ERROR", proc.stderr)
        self.assertIn("JWT_SECRET_KEY", proc.stderr)

    # 7. ENFORCED RBAC SECURITY TESTS (GAPS 1, 2, 3)
    def test_13_unauthenticated_investigation_endpoints_return_401(self):
        self.assertEqual(self.client.get("/api/investigations").status_code, 401)
        self.assertEqual(self.client.get("/api/investigations/INV-2026-0358").status_code, 401)
        self.assertEqual(self.client.get("/api/investigations/project/MPL-0358").status_code, 401)

    def test_14_admin_investigation_endpoints_return_403(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "admin_user", "password": "Admin@2026"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        self.assertEqual(self.client.get("/api/investigations", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/investigations/INV-2026-0358", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/investigations/project/MPL-0358", headers=headers).status_code, 403)

        self.assertEqual(self.client.post("/api/investigations", json={"project_id": "MPL-0358", "reason": "Test"}, headers=headers).status_code, 403)
        self.assertEqual(self.client.put("/api/investigations/INV-2026-0358/assign", json={"assigned_to": "Officer A", "assigned_role": "District Authority"}, headers=headers).status_code, 403)
        self.assertEqual(self.client.put("/api/investigations/INV-2026-0358/status", json={"status": "IN_PROGRESS", "comment": "Test"}, headers=headers).status_code, 403)
        self.assertEqual(self.client.put("/api/investigations/INV-2026-0358/progress", json={"progress_percentage": 50}, headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/investigations/INV-2026-0358/findings", json={"finding_text": "Test"}, headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/investigations/INV-2026-0358/escalate", json={"reason": "Test"}, headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/investigations/INV-2026-0358/resolve", json={"final_recommendation": "Test"}, headers=headers).status_code, 403)

    def test_15_district_authority_assignment_scoping(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "district_officer_04", "password": "District@2026"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # In-scope assignment on District-04 investigation INV-2026-0358 succeeds
        resp_in = self.client.put(
            "/api/investigations/INV-2026-0358/assign",
            json={"assigned_to": "Field Inspector B", "assigned_role": "District Authority", "comment": "Local assignment"},
            headers=headers
        )
        self.assertEqual(resp_in.status_code, 200)

        # Out-of-scope assignment on District-12 investigation INV-2026-0001 fails with 403 Forbidden
        resp_out = self.client.put(
            "/api/investigations/INV-2026-0001/assign",
            json={"assigned_to": "Field Inspector B", "assigned_role": "District Authority"},
            headers=headers
        )
        self.assertEqual(resp_out.status_code, 403)

    def test_16_unauthenticated_operational_endpoints_return_401(self):
        endpoints = [
            "/api/projects",
            "/api/anomalies",
            "/api/anomalies/MPL-0358",
            "/api/risk",
            "/api/risk/MPL-0358",
            "/api/ml/anomalies",
            "/api/ml/anomalies/MPL-0358",
            "/api/analytics/benchmark",
            "/api/analytics/benchmark/MPL-0358",
            "/api/analytics/forecast",
            "/api/analytics/forecast/MPL-0358",
            "/api/analytics/audit-queue",
            "/api/analytics/districts",
            "/api/analytics/geospatial/quality",
            "/api/real-mplads/works",
            "/api/real-mplads/benchmark?work_id=358",
            "/api/real-mplads/stats",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 401, msg=f"Endpoint {ep} failed to return 401 for unauthenticated request")

    def test_17_admin_operational_endpoints_return_403(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "admin_user", "password": "Admin@2026"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        endpoints = [
            "/api/projects",
            "/api/anomalies",
            "/api/anomalies/MPL-0358",
            "/api/risk",
            "/api/risk/MPL-0358",
            "/api/ml/anomalies",
            "/api/ml/anomalies/MPL-0358",
            "/api/analytics/benchmark",
            "/api/analytics/benchmark/MPL-0358",
            "/api/analytics/forecast",
            "/api/analytics/forecast/MPL-0358",
            "/api/analytics/audit-queue",
            "/api/analytics/districts",
            "/api/analytics/geospatial/quality",
            "/api/real-mplads/works",
            "/api/real-mplads/benchmark?work_id=358",
            "/api/real-mplads/stats",
        ]
        for ep in endpoints:
            res = self.client.get(ep, headers=headers)
            self.assertEqual(res.status_code, 403, msg=f"Endpoint {ep} failed to return 403 for ADMIN role")

    def test_18_district_authority_scoped_analytics_and_benchmarking(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "district_officer_04", "password": "District@2026"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # In-scope single project lookups (District-04 project MPL-0007)
        self.assertEqual(self.client.get("/api/anomalies/MPL-0007", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/risk/MPL-0007", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/ml/anomalies/MPL-0007", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/analytics/benchmark/MPL-0007", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/analytics/forecast/MPL-0007", headers=headers).status_code, 200)

        # Out-of-scope single project lookups (District-21 project MPL-0001) -> 403 Forbidden
        self.assertEqual(self.client.get("/api/anomalies/MPL-0001", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/risk/MPL-0001", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/ml/anomalies/MPL-0001", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/analytics/benchmark/MPL-0001", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/analytics/forecast/MPL-0001", headers=headers).status_code, 403)

    def test_19_mospi_full_national_operational_access(self):
        login_resp = self.client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        endpoints = [
            "/api/projects",
            "/api/anomalies",
            "/api/anomalies/MPL-0001",
            "/api/risk",
            "/api/risk/MPL-0001",
            "/api/ml/anomalies",
            "/api/ml/anomalies/MPL-0001",
            "/api/analytics/benchmark",
            "/api/analytics/benchmark/MPL-0001",
            "/api/analytics/forecast",
            "/api/analytics/forecast/MPL-0001",
            "/api/analytics/audit-queue",
            "/api/analytics/districts",
            "/api/analytics/geospatial/quality",
            "/api/real-mplads/works",
            "/api/real-mplads/stats",
        ]
        for ep in endpoints:
            res = self.client.get(ep, headers=headers)
            self.assertEqual(res.status_code, 200, msg=f"Endpoint {ep} failed to return 200 for MOSPI_OFFICER role")


if __name__ == "__main__":
    unittest.main()


