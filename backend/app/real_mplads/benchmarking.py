import math
from typing import Any, Dict, List, Optional
import numpy as np
from app.real_mplads.loader import RealMPLADSLoader, get_real_data_loader
from app.real_mplads.models import (
    RealComparableWorkPeer,
    RealWorkBenchmarkResult,
    RealWorkRecord,
)
from app.real_mplads.search_index import (
    RealMPLADSSearchIndex,
    clean_work_description,
    get_real_search_index,
)


ASSET_DOMAINS: Dict[str, List[str]] = {
    "community_hall": [
        "community hall", "community centre", "community center", "samudayik bhavan",
        "samuday bhavan", "community building", "chopal", "dharmshala", "meeting hall"
    ],
    "road_cc": [
        "cc road", "pcc road", "cement concrete road", "bt road", "road construction",
        "laying of cc", "providing of cc road", "brick soling road", "road from", "paving"
    ],
    "school_education": [
        "school", "classroom", "hostel", "sainik school", "anganwadi", "college",
        "shiksha", "vidyalaya", "class room", "boys hostel", "girls hostel"
    ],
    "lighting_solar": [
        "high mast", "solar light", "street light", "solar high mast", "led light",
        "solar street", "highmast", "solar plant"
    ],
    "ambulance_health": [
        "ambulance", "icu", "als ambulance", "bls ambulance", "hospital vehicle",
        "dialysis", "medical equipment", "healthcare vehicle", "cancer screening vehicle"
    ],
    "water_borewell": [
        "hand pump", "borewell", "tubewell", "drinking water", "water supply",
        "water tank", "solar pump", "tube well", "bore well", "ro plant"
    ],
    "library": [
        "library", "reading room", "pustakalaya", "study centre", "digital library"
    ],
    "gym_sports": [
        "gym", "gymnasium", "sports arena", "playground", "badminton", "cricket",
        "fitness", "sports campus", "open gym", "sports complex"
    ],
    "boundary_wall": [
        "boundary wall", "cremation ground", "kabristan", "graveyard boundary",
        "compound wall", "fencing", "cremation"
    ],
    "surveillance_cctv": [
        "cc camera", "cctv", "surveillance camera", "security camera", "cc cameras"
    ],
    "drainage_sanitation": [
        "drainage", "cc drain", "nala", "sanitation", "toilet", "sewerage",
        "sulabh", "drain"
    ],
    "repair_renovation": [
        "repair", "renovation", "restoration", "maintenance", "reconstruction"
    ],
}

CATEGORY_CANONICAL_QUERIES: Dict[str, List[str]] = {
    "Community Hall": ["community hall", "community centre", "multipurpose hall"],
    "Public Library": ["public library", "library", "reading room"],
    "Road": ["road", "cc road", "pcc road", "bt road"],
    "Street Lighting": ["street light", "street lighting", "high mast", "solar light"],
    "School Infrastructure": ["school", "classroom", "government school", "school building"],
    "Drainage": ["drain", "drainage", "nala", "storm water drainage"],
    "Water Supply": ["drinking water", "water supply", "borewell", "pipeline"],
    "Sanitation": ["sanitation", "toilet", "public toilet"],
    "Sports Facility": ["sports", "gym", "playground", "sports equipment"],
    "Health Facility": ["health centre", "healthcare", "hospital", "ambulance"],
}


def detect_asset_domain(text: str) -> str:
    """
    Identifies the core asset/work domain from the work description or category string.
    Returns the domain key if confidently detected, else 'other'.
    """
    t = (text or "").lower()
    for domain, keywords in ASSET_DOMAINS.items():
        for kw in keywords:
            if kw in t:
                return domain
    return "other"


def are_asset_domains_compatible(target_domain: str, candidate_domain: str) -> bool:
    """
    Asset-Type Compatibility Gate: Rejects candidates from clearly incompatible asset domains.
    If either domain is unclassified ('other'), allows text similarity thresholding to govern.
    """
    if target_domain == "other" or candidate_domain == "other":
        return True
    return target_domain == candidate_domain


class RealPeerBenchmarkEngine:
    """
    Peer Benchmarking and Cost Comparability Engine for Real MPLADS Works.
    Implements Multi-Query Max-Pooling under Config A quality thresholds and domain compatibility gating.
    """

    def __init__(
        self,
        loader: Optional[RealMPLADSLoader] = None,
        search_index: Optional[RealMPLADSSearchIndex] = None,
    ):
        self.loader = loader or get_real_data_loader()
        self.search_index = search_index or get_real_search_index()

    def benchmark_by_id(
        self,
        work_id: int,
        dataset: str = "recommended",
        top_k: int = 5,
        min_text_similarity: float = 0.45,
        min_composite_similarity: float = 0.55,
        min_peers_required: int = 2,
    ) -> RealWorkBenchmarkResult:
        """
        Executes peer benchmarking for a work identified by its unique Work ID in the real dataset.
        """
        self.loader.load_all()
        by_id_map = self.loader.recommended_by_id if dataset == "recommended" else self.loader.completed_by_id

        if work_id not in by_id_map:
            return RealWorkBenchmarkResult(
                status="ERROR_NOT_FOUND",
                analysis_type="Comparable Project Analysis / Peer Benchmarking",
                source_dataset="recommended_works" if dataset == "recommended" else "completed_works",
                amount_type="Recommended Amount" if dataset == "recommended" else "Final Amount",
                target_work=None,
                target_amount=0.0,
                target_amount_lakh=0.0,
                comparable_project_count=0,
                peer_median_amount=0.0,
                peer_median_lakh=0.0,
                peer_average_amount=0.0,
                peer_average_lakh=0.0,
                peer_min_amount=0.0,
                peer_min_lakh=0.0,
                peer_max_amount=0.0,
                peer_max_lakh=0.0,
                peer_std_amount=0.0,
                ratio_to_peer_median=1.0,
                percentage_difference_from_peer_median=0.0,
                average_peer_similarity=0.0,
                matching_confidence=0.0,
                benchmark_insight=f"Work ID {work_id} was not found in the real {dataset} dataset.",
                comparable_works=[],
            )

        target_record = by_id_map[work_id]
        return self._evaluate_benchmarking(
            target_record=target_record,
            query_description=target_record.work_description,
            query_amount=target_record.amount,
            query_state=target_record.state,
            query_category=target_record.category,
            query_ida=target_record.ida,
            dataset=dataset,
            exclude_work_id=work_id,
            top_k=top_k,
            min_text_similarity=min_text_similarity,
            min_composite_similarity=min_composite_similarity,
            min_peers_required=min_peers_required,
        )

    def benchmark_custom(
        self,
        description: str,
        amount: float,
        state: Optional[str] = None,
        category: Optional[str] = None,
        ida: Optional[str] = None,
        dataset: str = "recommended",
        top_k: int = 5,
        min_text_similarity: float = 0.45,
        min_composite_similarity: float = 0.55,
        min_peers_required: int = 2,
    ) -> RealWorkBenchmarkResult:
        """
        Executes peer benchmarking for custom parameters or prototype project queries using Multi-Query Max-Pooling.
        """
        self.loader.load_all()
        target_record = RealWorkRecord(
            work_id=0,
            work_description=description,
            category=category or "Normal/Others",
            mp_name="Custom Query",
            constituency="Ad-hoc",
            state=state or "National",
            house="Custom",
            amount=amount,
            amount_lakh=round(amount / 100000.0, 2),
            date="2026-08-25",
            has_images=False,
            ida=ida or "",
            dataset_source="recommended_works" if dataset == "recommended" else "completed_works",
        )

        return self._evaluate_benchmarking(
            target_record=target_record,
            query_description=description,
            query_amount=amount,
            query_state=state or "",
            query_category=category or "",
            query_ida=ida or "",
            dataset=dataset,
            exclude_work_id=0,
            top_k=top_k,
            min_text_similarity=min_text_similarity,
            min_composite_similarity=min_composite_similarity,
            min_peers_required=min_peers_required,
        )

    def _evaluate_benchmarking(
        self,
        target_record: RealWorkRecord,
        query_description: str,
        query_amount: float,
        query_state: str,
        query_category: str,
        query_ida: str,
        dataset: str,
        exclude_work_id: int,
        top_k: int,
        min_text_similarity: float,
        min_composite_similarity: float,
        min_peers_required: int,
    ) -> RealWorkBenchmarkResult:
        all_records = self.loader.recommended_records if dataset == "recommended" else self.loader.completed_records
        amount_type_label = "Recommended Amount" if dataset == "recommended" else "Final Amount"
        source_dataset_label = "recommended_works" if dataset == "recommended" else "completed_works"

        if not query_description.strip() or len(all_records) == 0:
            return RealWorkBenchmarkResult(
                status="INSUFFICIENT_PEERS",
                analysis_type="Comparable Project Analysis / Peer Benchmarking",
                source_dataset=source_dataset_label,
                amount_type=amount_type_label,
                target_work=target_record,
                target_amount=query_amount,
                target_amount_lakh=round(query_amount / 100000.0, 2),
                comparable_project_count=0,
                peer_median_amount=0.0,
                peer_median_lakh=0.0,
                peer_average_amount=0.0,
                peer_average_lakh=0.0,
                peer_min_amount=0.0,
                peer_min_lakh=0.0,
                peer_max_amount=0.0,
                peer_max_lakh=0.0,
                peer_std_amount=0.0,
                ratio_to_peer_median=1.0,
                percentage_difference_from_peer_median=0.0,
                average_peer_similarity=0.0,
                matching_confidence=0.0,
                benchmark_insight="No query description provided for peer matching.",
                comparable_works=[],
            )

        # 1. Detect target asset domain
        target_domain = detect_asset_domain(query_description)
        if target_domain == "other" and query_category:
            target_domain = detect_asset_domain(query_category)

        # 2. Multi-Query Formulation (Independent Queries evaluated separately)
        queries = [query_description]
        if query_category in CATEGORY_CANONICAL_QUERIES:
            for cq in CATEGORY_CANONICAL_QUERIES[query_category]:
                if cq not in queries:
                    queries.append(cq)

        # Compute TF-IDF cosine similarities independently for each sub-query
        all_sims = []
        for q in queries:
            all_sims.append(self.search_index.compute_similarity(q, dataset=dataset))

        all_sims_matrix = np.vstack(all_sims)  # shape: (num_queries, num_candidates)
        max_sims = np.max(all_sims_matrix, axis=0)  # shape: (num_candidates,)
        winning_query_idx = np.argmax(all_sims_matrix, axis=0)  # shape: (num_candidates,)

        # 3. Score and filter candidates
        candidates: List[RealComparableWorkPeer] = []
        target_state_clean = query_state.strip().lower()
        target_cat_clean = query_category.strip().lower()
        target_ida_clean = query_ida.strip().lower()

        for idx, rec in enumerate(all_records):
            # Gate 1: Exclude target work itself
            if exclude_work_id != 0 and rec.work_id == exclude_work_id:
                continue

            # Gate 2: Asset-Type Compatibility Gate
            cand_domain = detect_asset_domain(rec.work_description)
            if not are_asset_domains_compatible(target_domain, cand_domain):
                continue

            # Gate 3: Minimum text similarity threshold (0.45)
            text_sim = float(max_sims[idx])
            if text_sim < min_text_similarity:
                continue

            state_match = bool(target_state_clean and rec.state.strip().lower() == target_state_clean)
            cat_match = bool(target_cat_clean and rec.category.strip().lower() == target_cat_clean)
            ida_match = bool(target_ida_clean and rec.ida.strip().lower() == target_ida_clean and target_ida_clean != "")

            # Multiplicative Context Scoring Formula (Config A):
            # composite_score = text_sim * (1.0 + 0.20*state + 0.15*cat + 0.10*ida)
            context_mult = 1.0
            if state_match:
                context_mult += 0.20
            if cat_match:
                context_mult += 0.15
            if ida_match:
                context_mult += 0.10

            comp_score = round(min(1.50, text_sim * context_mult), 4)

            # Gate 4: Minimum composite similarity threshold (0.55)
            if comp_score < min_composite_similarity:
                continue

            if state_match and ida_match:
                tier = "Same State & District"
            elif state_match:
                tier = "Same State"
            else:
                tier = "National Peer"

            winning_q = queries[winning_query_idx[idx]]

            peer = RealComparableWorkPeer(
                work_id=rec.work_id,
                work_description=rec.work_description,
                category=rec.category,
                state=rec.state,
                constituency=rec.constituency,
                mp_name=rec.mp_name,
                ida=rec.ida,
                amount=rec.amount,
                amount_lakh=rec.amount_lakh,
                similarity_score=comp_score,
                text_similarity=round(text_sim, 4),
                state_match=state_match,
                category_match=cat_match,
                ida_match=ida_match,
                match_tier=tier,
                winning_query=winning_q,
            )
            candidates.append(peer)

        # 4. Sort by composite similarity descending
        candidates.sort(key=lambda p: p.similarity_score, reverse=True)
        top_peers = candidates[:top_k]

        # 5. Check if sufficient reliable peers found
        if len(top_peers) < min_peers_required:
            return RealWorkBenchmarkResult(
                status="INSUFFICIENT_PEERS",
                analysis_type="Comparable Project Analysis / Peer Benchmarking",
                source_dataset=source_dataset_label,
                amount_type=amount_type_label,
                target_work=target_record,
                target_amount=query_amount,
                target_amount_lakh=round(query_amount / 100000.0, 2),
                comparable_project_count=len(top_peers),
                peer_median_amount=0.0,
                peer_median_lakh=0.0,
                peer_average_amount=0.0,
                peer_average_lakh=0.0,
                peer_min_amount=0.0,
                peer_min_lakh=0.0,
                peer_max_amount=0.0,
                peer_max_lakh=0.0,
                peer_std_amount=0.0,
                ratio_to_peer_median=1.0,
                percentage_difference_from_peer_median=0.0,
                average_peer_similarity=0.0,
                matching_confidence=0.0,
                benchmark_insight="No reliable comparable projects found above quality threshold in the real MPLADS dataset.",
                comparable_works=top_peers,
            )

        # 6. Compute peer distribution statistics
        peer_amts = [p.amount for p in top_peers]
        peer_median = float(np.median(peer_amts))
        peer_avg = float(np.mean(peer_amts))
        peer_min = float(np.min(peer_amts))
        peer_max = float(np.max(peer_amts))
        peer_std = float(np.std(peer_amts)) if len(peer_amts) > 1 else 0.0

        avg_similarity = float(np.mean([p.similarity_score for p in top_peers]))

        if peer_median > 0:
            ratio = round(query_amount / peer_median, 2)
            pct_diff = round(((query_amount - peer_median) / peer_median) * 100.0, 1)
        else:
            ratio = 1.0
            pct_diff = 0.0

        confidence = round(min(1.0, (avg_similarity / 1.20) * (len(top_peers) / min(top_k, 5))), 3)

        # 7. Generate neutral, explainable insight
        target_lakh = round(query_amount / 100000.0, 2)
        median_lakh = round(peer_median / 100000.0, 2)
        state_ctx = f" in {query_state}" if query_state else ""
        
        if pct_diff > 35.0:
            insight = f"Proposed {amount_type_label.lower()} (₹{target_lakh:.2f}L) is substantially higher (+{pct_diff:.1f}%) than the peer median (₹{median_lakh:.2f}L) across {len(top_peers)} comparable works{state_ctx}."
        elif pct_diff < -35.0:
            insight = f"Proposed {amount_type_label.lower()} (₹{target_lakh:.2f}L) is substantially lower ({pct_diff:.1f}%) than the peer median (₹{median_lakh:.2f}L) across {len(top_peers)} comparable works{state_ctx}."
        elif abs(pct_diff) <= 10.0:
            insight = f"Proposed {amount_type_label.lower()} (₹{target_lakh:.2f}L) aligns closely ({pct_diff:+.1f}%) with the peer median (₹{median_lakh:.2f}L) across {len(top_peers)} comparable works{state_ctx}."
        else:
            insight = f"Proposed {amount_type_label.lower()} (₹{target_lakh:.2f}L) is moderately {('higher' if pct_diff > 0 else 'lower')} ({pct_diff:+.1f}%) compared to peer median (₹{median_lakh:.2f}L) across {len(top_peers)} comparable works{state_ctx}."

        return RealWorkBenchmarkResult(
            status="SUCCESS",
            analysis_type="Comparable Project Analysis / Peer Benchmarking",
            source_dataset=source_dataset_label,
            amount_type=amount_type_label,
            target_work=target_record,
            target_amount=query_amount,
            target_amount_lakh=target_lakh,
            comparable_project_count=len(top_peers),
            peer_median_amount=peer_median,
            peer_median_lakh=median_lakh,
            peer_average_amount=round(peer_avg, 2),
            peer_average_lakh=round(peer_avg / 100000.0, 2),
            peer_min_amount=peer_min,
            peer_min_lakh=round(peer_min / 100000.0, 2),
            peer_max_amount=peer_max,
            peer_max_lakh=round(peer_max / 100000.0, 2),
            peer_std_amount=round(peer_std, 2),
            ratio_to_peer_median=ratio,
            percentage_difference_from_peer_median=pct_diff,
            average_peer_similarity=round(avg_similarity, 4),
            matching_confidence=confidence,
            benchmark_insight=insight,
            comparable_works=top_peers,
        )


_engine_instance = RealPeerBenchmarkEngine()


def get_real_benchmark_engine() -> RealPeerBenchmarkEngine:
    return _engine_instance
