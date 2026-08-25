import os
import sys
import unittest

_curr = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.abspath(os.path.join(_curr, ".."))
_root = os.path.abspath(os.path.join(_backend, ".."))
for p in [_root, _backend]:
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.real_mplads import (
    RealMPLADSLoader,
    RealPeerBenchmarkEngine,
    are_asset_domains_compatible,
    clean_work_description,
    detect_asset_domain,
    get_real_benchmark_engine,
    get_real_data_loader,
)


class TestRealMPLADSBenchmarkingConfigA(unittest.TestCase):
    """
    Comprehensive Test Suite for Approved Multi-Query Max-Pooling in Real MPLADS Benchmark Engine.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.loader = get_real_data_loader()
        cls.engine = get_real_benchmark_engine()

    def test_01_text_preprocessing_boilerplate_removal(self):
        """Verify geographic/administrative boilerplate is cleaned while preserving asset terms."""
        raw_text = "Construction of community hall in sahilong village in dumargadi panchayat under karra block Khunti district"
        cleaned = clean_work_description(raw_text)
        self.assertNotIn("village", cleaned)
        self.assertNotIn("panchayat", cleaned)
        self.assertNotIn("block", cleaned)
        self.assertNotIn("district", cleaned)
        self.assertIn("community", cleaned)
        self.assertIn("hall", cleaned)
        self.assertIn("construction", cleaned)

    def test_02_asset_type_gate_classification(self):
        """Verify asset domains are detected accurately."""
        self.assertEqual(detect_asset_domain("Construction of Community Hall"), "community_hall")
        self.assertEqual(detect_asset_domain("Construction of Community Centre"), "community_hall")
        self.assertEqual(detect_asset_domain("Laying of CC Road from house to field"), "road_cc")
        self.assertEqual(detect_asset_domain("Boundary wall around cremation ground"), "boundary_wall")
        self.assertEqual(detect_asset_domain("Purchase of ALS Ambulance ICU"), "ambulance_health")
        self.assertEqual(detect_asset_domain("Construction of school classroom"), "school_education")
        self.assertEqual(detect_asset_domain("Installation of High Mast Solar Light"), "lighting_solar")

    def test_03_asset_type_compatibility_matrix(self):
        """Verify asset compatibility gate rules."""
        # Compatible
        self.assertTrue(are_asset_domains_compatible("community_hall", "community_hall"))
        self.assertTrue(are_asset_domains_compatible("road_cc", "road_cc"))
        self.assertTrue(are_asset_domains_compatible("other", "community_hall"))

        # Incompatible (Must Reject)
        self.assertFalse(are_asset_domains_compatible("community_hall", "boundary_wall"))
        self.assertFalse(are_asset_domains_compatible("community_hall", "road_cc"))
        self.assertFalse(are_asset_domains_compatible("community_hall", "lighting_solar"))
        self.assertFalse(are_asset_domains_compatible("ambulance_health", "community_hall"))

    def test_04_work_1809_eliminates_cremation_boundary_wall(self):
        """Verify Work 1809 (Community Hall) does NOT match cremation boundary wall ID 304415."""
        res = self.engine.benchmark_by_id(1809, dataset="recommended", top_k=5)
        self.assertEqual(res.status, "SUCCESS")
        peer_ids = [p.work_id for p in res.comparable_works]
        self.assertNotIn(304415, peer_ids)
        for p in res.comparable_works:
            self.assertIn("hall", p.work_description.lower())
            self.assertNotIn("cremation", p.work_description.lower())

    def test_05_work_1888_returns_insufficient_peers_instead_of_dharmshala(self):
        """Verify Work 1888 returns INSUFFICIENT_PEERS rather than returning unrelated dharmshalas/chopals."""
        res = self.engine.benchmark_by_id(1888, dataset="recommended", top_k=5)
        self.assertEqual(res.status, "INSUFFICIENT_PEERS")
        self.assertEqual(res.comparable_project_count, 0)
        self.assertIn("No reliable comparable projects found", res.benchmark_insight)

    def test_06_work_849_and_pcc_roads(self):
        """Verify Work 849 matches genuine PCC road construction works."""
        res = self.engine.benchmark_by_id(849, dataset="recommended", top_k=5)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(len(res.comparable_works), 2)
        peer_ids = [p.work_id for p in res.comparable_works]
        self.assertIn(850, peer_ids)
        self.assertIn(852, peer_ids)
        self.assertNotIn(849, peer_ids)

    def test_07_work_2139_cc_cameras(self):
        """Verify Work 2139 matches genuine CC camera installations."""
        res = self.engine.benchmark_by_id(2139, dataset="recommended", top_k=5)
        self.assertEqual(res.status, "SUCCESS")
        for p in res.comparable_works:
            self.assertTrue("camera" in p.work_description.lower() or "cc camera" in p.work_description.lower())

    def test_08_work_2065_and_2066_cc_road_cluster(self):
        """Verify reciprocal CC road cluster matching in Yelgalagudem."""
        res2065 = self.engine.benchmark_by_id(2065, dataset="recommended", top_k=5)
        self.assertEqual(res2065.status, "SUCCESS")
        peer_ids_2065 = [p.work_id for p in res2065.comparable_works]
        self.assertIn(2066, peer_ids_2065)
        self.assertNotIn(2065, peer_ids_2065)

        res2066 = self.engine.benchmark_by_id(2066, dataset="recommended", top_k=5)
        self.assertEqual(res2066.status, "SUCCESS")
        peer_ids_2066 = [p.work_id for p in res2066.comparable_works]
        self.assertIn(2065, peer_ids_2066)
        self.assertNotIn(2066, peer_ids_2066)

    def test_09_work_1331_and_2147_community_halls(self):
        """Verify Work 1331 and 2147 return 100% genuine community halls."""
        res1331 = self.engine.benchmark_by_id(1331, dataset="recommended", top_k=5)
        self.assertEqual(res1331.status, "SUCCESS")
        for p in res1331.comparable_works:
            self.assertIn("hall", p.work_description.lower())
            self.assertGreaterEqual(p.text_similarity, 0.45)
            self.assertGreaterEqual(p.similarity_score, 0.55)

        res2147 = self.engine.benchmark_by_id(2147, dataset="recommended", top_k=5)
        self.assertEqual(res2147.status, "SUCCESS")
        peer_ids_2147 = [p.work_id for p in res2147.comparable_works]
        self.assertIn(1331, peer_ids_2147)

    def test_10_target_work_exclusion(self):
        """Verify target work is strictly excluded from candidate peers."""
        for tid in [1331, 2065, 2066, 2147, 849, 2110]:
            res = self.engine.benchmark_by_id(tid, dataset="recommended")
            if res.status == "SUCCESS":
                peer_ids = [p.work_id for p in res.comparable_works]
                self.assertNotIn(tid, peer_ids)

    def test_11_amount_type_separation(self):
        """Verify Recommended Amount used for recommended dataset and Final Amount for completed dataset."""
        res_rec = self.engine.benchmark_by_id(1331, dataset="recommended")
        self.assertEqual(res_rec.amount_type, "Recommended Amount")
        self.assertEqual(res_rec.source_dataset, "recommended_works")

        res_comp = self.engine.benchmark_by_id(68103, dataset="completed")
        self.assertEqual(res_comp.amount_type, "Final Amount")
        self.assertEqual(res_comp.source_dataset, "completed_works")

    def test_12_no_fabricated_expenditures_linkage(self):
        """Verify expenditure transactions remain unlinked without fake Work IDs."""
        exp_cols = self.loader.expenditures_df.columns.tolist()
        self.assertNotIn("Work ID", exp_cols)
        self.assertNotIn("work_id", exp_cols)

    def test_13_prototype_max_pooling_matches_genuine_peers(self):
        """Verify prototype project Road Project 0001 matches genuine CC Road peers via max-pooling."""
        res = self.engine.benchmark_custom(
            description="Road Project 0001",
            amount=1681000.0,
            state="Karnataka",
            category="Road",
            dataset="recommended",
            top_k=5,
        )
        self.assertEqual(res.status, "SUCCESS")
        self.assertGreaterEqual(len(res.comparable_works), 2)
        for p in res.comparable_works:
            self.assertIsNotNone(p.winning_query)
            self.assertTrue("road" in p.work_description.lower())

    def test_14_prototype_drainage_and_school_max_pooling(self):
        """Verify prototype projects in Drainage and School Infrastructure find authentic peers."""
        res_drain = self.engine.benchmark_custom(
            description="Drainage Project 0358",
            amount=4876000.0,
            state="Rajasthan",
            category="Drainage",
            dataset="recommended",
            top_k=5,
        )
        self.assertEqual(res_drain.status, "SUCCESS")
        for p in res_drain.comparable_works:
            self.assertTrue("drain" in p.work_description.lower() or "nala" in p.work_description.lower())

        res_school = self.engine.benchmark_custom(
            description="School Infrastructure Project 0291",
            amount=1260000.0,
            state="Telangana",
            category="School Infrastructure",
            dataset="recommended",
            top_k=5,
        )
        self.assertEqual(res_school.status, "SUCCESS")
        for p in res_school.comparable_works:
            self.assertTrue("school" in p.work_description.lower() or "classroom" in p.work_description.lower())

    def test_15_api_endpoints_contract_compatibility_and_winning_query(self):
        """Verify API endpoints return valid response models with winning_query under Max-Pooling."""
        # 1. Works endpoint
        r1 = self.client.get("/api/real-mplads/works?dataset=recommended&limit=5")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["count"], 5)

        # 2. Benchmark endpoint for custom prototype
        r2 = self.client.get(
            "/api/real-mplads/benchmark?description=Road+Project+0001&amount=1681000&state=Karnataka&category=Road&dataset=recommended"
        )
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertEqual(d2["status"], "SUCCESS")
        self.assertGreaterEqual(len(d2["comparable_works"]), 2)
        for p in d2["comparable_works"]:
            self.assertGreaterEqual(p["text_similarity"], 0.45)
            self.assertGreaterEqual(p["similarity_score"], 0.55)
            self.assertIn("winning_query", p)

        # 3. Stats endpoint
        r3 = self.client.get("/api/real-mplads/stats")
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["total_recommended_works"], 14745)


if __name__ == "__main__":
    unittest.main()
