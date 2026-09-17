import os
import sys
import json

_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, ".."))
_backend = os.path.join(_root, "backend")
for p in [_root, _backend]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ["JWT_SECRET_KEY"] = "sih-test-jwt-secret-key-32-chars-minimum-demo-2026"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Logins
r_mospi = client.post("/api/auth/login", json={"username": "mospi_officer", "password": "MoSPI@2026"}).json()
h_mospi = {"Authorization": f"Bearer {r_mospi['access_token']}"}

r_dist = client.post("/api/auth/login", json={"username": "district_officer_04", "password": "District@2026"}).json()
h_dist = {"Authorization": f"Bearer {r_dist['access_token']}"}

r_admin = client.post("/api/auth/login", json={"username": "admin_user", "password": "Admin@2026"}).json()
h_admin = {"Authorization": f"Bearer {r_admin['access_token']}"}

print("=== 1. MOSPI_OFFICER TESTS ===")
r = client.get("/api/investigations", headers=h_mospi)
print("MOSPI List all investigations:", r.status_code, f"{len(r.json())} items")
r = client.get("/api/investigations/INV-2026-0358", headers=h_mospi)
print("MOSPI Get INV-2026-0358 (District-04):", r.status_code)
r = client.get("/api/investigations/INV-2026-0001", headers=h_mospi)
print("MOSPI Get INV-2026-0001 (District-12):", r.status_code)

print("\n=== 2. DISTRICT_AUTHORITY (District-04) IN-SCOPE TESTS ===")
r = client.get("/api/investigations/INV-2026-0358", headers=h_dist)
print("Get INV-2026-0358 (District-04):", r.status_code)
r = client.get("/api/investigations/project/MPL-0358", headers=h_dist)
print("Get Project Investigation MPL-0358 (District-04):", r.status_code)
r = client.get("/api/investigations", headers=h_dist)
print("List investigations (unfiltered):", r.status_code, f"{len(r.json())} item(s) returned")
r = client.get("/api/investigations?district=District-04", headers=h_dist)
print("List investigations (district=District-04):", r.status_code, f"{len(r.json())} item(s) returned")

print("\n=== 3. OUT-OF-SCOPE ATTACK TESTS (District-04 officer attacking District-12) ===")
# Create investigation for MPL-0001 (District-12)
r = client.post("/api/investigations", json={"project_id": "MPL-0001", "reason": "Attack test"}, headers=h_dist)
print("Create investigation for out-of-scope project MPL-0001:", r.status_code, r.json())

# View out-of-scope investigation INV-2026-0001
r = client.get("/api/investigations/INV-2026-0001", headers=h_dist)
print("Get out-of-scope investigation INV-2026-0001:", r.status_code, r.json())

# View out-of-scope project investigation MPL-0001
r = client.get("/api/investigations/project/MPL-0001", headers=h_dist)
print("Get out-of-scope project investigation MPL-0001:", r.status_code, r.json())

# List investigations for District-12 via query param
r = client.get("/api/investigations?district=District-12", headers=h_dist)
print("List investigations with district=District-12:", r.status_code, r.json())

# Assign out-of-scope investigation INV-2026-0001
r = client.put("/api/investigations/INV-2026-0001/assign", json={"assigned_to": "Test", "assigned_role": "District Authority"}, headers=h_dist)
print("Assign out-of-scope investigation INV-2026-0001:", r.status_code, r.json())

# Status update out-of-scope
r = client.put("/api/investigations/INV-2026-0001/status", json={"status": "IN_PROGRESS", "comment": "Attack"}, headers=h_dist)
print("Status update out-of-scope INV-2026-0001:", r.status_code, r.json())

# Progress update out-of-scope
r = client.put("/api/investigations/INV-2026-0001/progress", json={"progress_percentage": 50, "comment": "Attack"}, headers=h_dist)
print("Progress update out-of-scope INV-2026-0001:", r.status_code, r.json())

# Add finding out-of-scope
r = client.post("/api/investigations/INV-2026-0001/findings", json={"finding_text": "Attack finding"}, headers=h_dist)
print("Add finding out-of-scope INV-2026-0001:", r.status_code, r.json())

# Escalate out-of-scope
r = client.post("/api/investigations/INV-2026-0001/escalate", json={"reason": "Attack escalation"}, headers=h_dist)
print("Escalate out-of-scope INV-2026-0001:", r.status_code, r.json())

# Resolve out-of-scope
r = client.post("/api/investigations/INV-2026-0001/resolve", json={"final_recommendation": "Attack resolve", "close_case": False}, headers=h_dist)
print("Resolve out-of-scope INV-2026-0001:", r.status_code, r.json())

print("\n=== 4. PARAMETER MANIPULATION & IDOR TESTS ===")
# Try manipulating project_id in body to another district while pretending to be District-04
r = client.post("/api/investigations", json={"project_id": "MPL-0005", "reason": "Manipulate project ID"}, headers=h_dist)
print("Manipulate project_id to MPL-0005 (District-12):", r.status_code, r.json())

# Try manipulating URL parameter investigation_id
r = client.get("/api/investigations/INV-2026-0001", headers=h_dist)
print("URL parameter manipulation (INV-2026-0001):", r.status_code, r.json())

# Try query parameter district manipulation
r = client.get("/api/investigations?district=District-05", headers=h_dist)
print("Query parameter district=District-05 manipulation:", r.status_code, r.json())

print("\n=== 5. ADMIN ROLE INVESTIGATION ACCESS TESTS ===")
r = client.get("/api/investigations", headers=h_admin)
print("Admin list investigations:", r.status_code, f"{len(r.json())} item(s)")
r = client.get("/api/investigations/INV-2026-0001", headers=h_admin)
print("Admin get INV-2026-0001 (District-12):", r.status_code)
r = client.get("/api/investigations/INV-2026-0358", headers=h_admin)
print("Admin get INV-2026-0358 (District-04):", r.status_code)
r = client.post("/api/investigations", json={"project_id": "MPL-0002", "reason": "Admin test investigation"}, headers=h_admin)
print("Admin create investigation for MPL-0002 (District-12):", r.status_code, r.json() if r.status_code == 200 else "")

print("\n=== 6. UNAUTHENTICATED TESTS ===")
print("Unauthenticated GET /api/investigations:", client.get("/api/investigations").status_code)
print("Unauthenticated GET /api/investigations/INV-2026-0358:", client.get("/api/investigations/INV-2026-0358").status_code)
print("Unauthenticated POST /api/investigations:", client.post("/api/investigations", json={"project_id": "MPL-0003", "reason": "Anon"}).status_code)
