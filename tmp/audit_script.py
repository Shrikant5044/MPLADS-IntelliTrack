import os
import sys
import json

_root = os.path.abspath('.')
_backend = os.path.join(_root, 'backend')
for p in [_root, _backend]:
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ['JWT_SECRET_KEY'] = 'sih-test-jwt-secret-key-32-chars-minimum-demo-2026'

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

r_mospi = client.post('/api/auth/login', json={'username': 'mospi_officer', 'password': 'MoSPI@2026'}).json()
h_mospi = {'Authorization': f"Bearer {r_mospi['access_token']}"}

r_dist = client.post('/api/auth/login', json={'username': 'district_officer_04', 'password': 'District@2026'}).json()
h_dist = {'Authorization': f"Bearer {r_dist['access_token']}"}

r_admin = client.post('/api/auth/login', json={'username': 'admin_user', 'password': 'Admin@2026'}).json()
h_admin = {'Authorization': f"Bearer {r_admin['access_token']}"}

endpoints = [
    ('GET', '/health', None),
    ('POST', '/api/auth/login', {'username': 'mospi_officer', 'password': 'MoSPI@2026'}),
    ('GET', '/api/auth/me', None),
    ('POST', '/api/auth/logout', None),
    ('GET', '/api/admin/users', None),
    ('POST', '/api/admin/users', {'username': 'test_u', 'email': 't@t.com', 'full_name': 'T U', 'role': 'DISTRICT_AUTHORITY', 'assigned_district': 'District-01', 'assigned_state': 'State', 'password': 'Password@123', 'is_active': True}),
    ('PUT', '/api/admin/users/usr_002', {'is_active': True}),
    ('DELETE', '/api/admin/users/usr_002', None),
    ('GET', '/api/projects', None),
    ('GET', '/api/projects?district=District-04', None),
    ('GET', '/api/projects?district=District-12', None),
    ('GET', '/api/anomalies', None),
    ('GET', '/api/anomalies/MPL-0358', None),
    ('GET', '/api/anomalies/MPL-0001', None),
    ('GET', '/api/risk', None),
    ('GET', '/api/risk/MPL-0358', None),
    ('GET', '/api/risk/MPL-0001', None),
    ('GET', '/api/ml/anomalies', None),
    ('GET', '/api/ml/anomalies/MPL-0358', None),
    ('GET', '/api/ml/anomalies/MPL-0001', None),
    ('GET', '/api/analytics/benchmark', None),
    ('GET', '/api/analytics/benchmark/MPL-0358', None),
    ('GET', '/api/analytics/benchmark/MPL-0001', None),
    ('GET', '/api/analytics/forecast', None),
    ('GET', '/api/analytics/forecast/MPL-0358', None),
    ('GET', '/api/analytics/forecast/MPL-0001', None),
    ('GET', '/api/analytics/audit-queue', None),
    ('GET', '/api/analytics/audit-queue?district=District-04', None),
    ('GET', '/api/analytics/audit-queue?district=District-12', None),
    ('GET', '/api/investigations', None),
    ('GET', '/api/investigations?district=District-04', None),
    ('GET', '/api/investigations?district=District-12', None),
    ('GET', '/api/investigations/INV-2026-0358', None),
    ('GET', '/api/investigations/INV-2026-0001', None),
    ('GET', '/api/investigations/project/MPL-0358', None),
    ('GET', '/api/investigations/project/MPL-0001', None),
    ('POST', '/api/investigations', {'project_id': 'MPL-0358', 'reason': 'Audit in-scope'}),
    ('POST', '/api/investigations', {'project_id': 'MPL-0001', 'reason': 'Audit out-of-scope'}),
    ('PUT', '/api/investigations/INV-2026-0358/assign', {'assigned_to': 'Inspector', 'assigned_role': 'District Authority'}),
    ('PUT', '/api/investigations/INV-2026-0001/assign', {'assigned_to': 'Inspector', 'assigned_role': 'District Authority'}),
    ('PUT', '/api/investigations/INV-2026-0358/status', {'status': 'IN_PROGRESS', 'comment': 'Audit'}),
    ('PUT', '/api/investigations/INV-2026-0001/status', {'status': 'IN_PROGRESS', 'comment': 'Audit'}),
    ('PUT', '/api/investigations/INV-2026-0358/progress', {'progress_percentage': 50}),
    ('PUT', '/api/investigations/INV-2026-0001/progress', {'progress_percentage': 50}),
    ('POST', '/api/investigations/INV-2026-0358/findings', {'finding_text': 'Audit'}),
    ('POST', '/api/investigations/INV-2026-0001/findings', {'finding_text': 'Audit'}),
    ('POST', '/api/investigations/INV-2026-0358/escalate', {'reason': 'Audit'}),
    ('POST', '/api/investigations/INV-2026-0001/escalate', {'reason': 'Audit'}),
    ('POST', '/api/investigations/INV-2026-0358/resolve', {'final_recommendation': 'Audit'}),
    ('POST', '/api/investigations/INV-2026-0001/resolve', {'final_recommendation': 'Audit'}),
    ('GET', '/api/analytics/districts', None),
    ('GET', '/api/analytics/geospatial/quality', None),
    ('GET', '/api/real-mplads/works', None),
    ('GET', '/api/real-mplads/benchmark?work_id=1', None),
    ('GET', '/api/real-mplads/stats', None),
]

print(f"{'Endpoint':<55} | {'Unauth':<6} | {'MOSPI':<6} | {'Dist(D04)':<10} | {'ADMIN':<6}")
print('-'*90)

for method, ep, body in endpoints:
    if method == 'GET':
        r_un = client.get(ep)
        r_mo = client.get(ep, headers=h_mospi)
        r_di = client.get(ep, headers=h_dist)
        r_ad = client.get(ep, headers=h_admin)
    elif method == 'POST':
        r_un = client.post(ep, json=body)
        r_mo = client.post(ep, json=body, headers=h_mospi)
        r_di = client.post(ep, json=body, headers=h_dist)
        r_ad = client.post(ep, json=body, headers=h_admin)
    elif method == 'PUT':
        r_un = client.put(ep, json=body)
        r_mo = client.put(ep, json=body, headers=h_mospi)
        r_di = client.put(ep, json=body, headers=h_dist)
        r_ad = client.put(ep, json=body, headers=h_admin)
    elif method == 'DELETE':
        r_un = client.delete(ep)
        r_mo = client.delete(ep, headers=h_mospi)
        r_di = client.delete(ep, headers=h_dist)
        r_ad = client.delete(ep, headers=h_admin)
    
    print(f"{method + ' ' + ep:<55} | {r_un.status_code:<6} | {r_mo.status_code:<6} | {r_di.status_code:<10} | {r_ad.status_code:<6}")
