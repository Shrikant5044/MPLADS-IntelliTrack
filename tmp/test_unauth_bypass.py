import os
import sys

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

# Login District Officer 04
r_dist = client.post("/api/auth/login", json={"username": "district_officer_04", "password": "District@2026"}).json()
h_dist = {"Authorization": f"Bearer {r_dist['access_token']}"}

print("=== UNAUTHENTICATED READ BYPASS AUDIT ===")

# 1. District officer trying to view District-12 investigation with token:
r1 = client.get("/api/investigations/INV-2026-0001", headers=h_dist)
print("1. District Officer with Token -> GET INV-2026-0001:", r1.status_code)

# 2. Same request WITHOUT token (Unauthenticated):
r2 = client.get("/api/investigations/INV-2026-0001")
print("2. Unauthenticated (NO Token) -> GET INV-2026-0001:", r2.status_code, "ID:", r2.json().get("investigation_id"), "District:", r2.json().get("district"))

# 3. District officer trying to list all investigations with token:
r3 = client.get("/api/investigations", headers=h_dist)
print("3. District Officer with Token -> GET /api/investigations:", r3.status_code, f"Returned {len(r3.json())} item(s)")

# 4. Unauthenticated list all investigations:
r4 = client.get("/api/investigations")
print("4. Unauthenticated (NO Token) -> GET /api/investigations:", r4.status_code, f"Returned {len(r4.json())} item(s)")

# 5. Unauthenticated project investigation:
r5 = client.get("/api/investigations/project/MPL-0001")
print("5. Unauthenticated (NO Token) -> GET /api/investigations/project/MPL-0001:", r5.status_code, "Project:", r5.json().get("project_id"))
