import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.analytics_engine.models import (
    BenchmarkConfig,
    BenchmarkStatusEnum,
    BenchmarkSummary,
    PeerHierarchyTierEnum,
    PeerSummaryStats,
    ProjectBenchmarkResult,
)


class ProjectBenchmarkingEngine:
    """
    Independent Comparable Project Benchmarking Engine for MPLADS-IntelliTrack.
    Compares project financial scale and cost against statistical peer cohorts
    using a multi-tier geographic hierarchy (District -> State -> National).
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()

    def _resolve_peers(
        self,
        target_row: pd.Series,
        projects_df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, PeerHierarchyTierEnum]:
        """
        Resolves comparable peer cohort using strict hierarchical search:
        1. Same District + Same Work Category (excluding target project)
        2. Same State + Same Work Category (if fallback enabled)
        3. National Category Baseline (if fallback enabled)
        """
        target_pid = str(target_row["project_id"])
        target_cat = str(target_row.get("work_category", "")).strip()
        target_dist = str(target_row.get("district", "")).strip()
        target_state = str(target_row.get("state", "")).strip()

        # Filter out target project and any records missing cost or category
        valid_pool = projects_df[
            (projects_df["project_id"].astype(str) != target_pid)
            & (projects_df["work_category"].astype(str).str.strip() == target_cat)
            & (projects_df["estimated_cost_lakh"].notnull())
            & (projects_df["estimated_cost_lakh"] > 0)
        ]

        # Tier 1: Same District + Same Category
        tier1_df = valid_pool[valid_pool["district"].astype(str).str.strip() == target_dist]
        if len(tier1_df) >= self.config.min_peers:
            return tier1_df, PeerHierarchyTierEnum.DISTRICT_CATEGORY

        # Tier 2: Same State + Same Category (Fallback)
        if self.config.allow_state_fallback:
            tier2_df = valid_pool[valid_pool["state"].astype(str).str.strip() == target_state]
            if len(tier2_df) >= self.config.min_peers:
                return tier2_df, PeerHierarchyTierEnum.STATE_CATEGORY

        # Tier 3: National Category Baseline (Fallback)
        if self.config.allow_national_fallback:
            if len(valid_pool) >= self.config.min_peers:
                return valid_pool, PeerHierarchyTierEnum.NATIONAL_CATEGORY

        return pd.DataFrame(), PeerHierarchyTierEnum.INSUFFICIENT

    def evaluate_project(
        self,
        project_id: str,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> Optional[ProjectBenchmarkResult]:
        """
        Evaluates comparable benchmarking for a single project.
        """
        matched = projects_df[projects_df["project_id"].astype(str) == str(project_id)]
        if matched.empty:
            return None

        target_row = matched.iloc[0]
        work_name = str(target_row.get("work_name", ""))
        work_cat = str(target_row.get("work_category", "General"))
        district = str(target_row.get("district", "Unknown"))
        state = str(target_row.get("state", "Unknown"))

        est_cost = float(target_row.get("estimated_cost_lakh", 0.0) or 0.0)
        sanc_amount = float(target_row.get("sanctioned_amount_lakh", 0.0) or 0.0)
        expenditure = float(target_row.get("expenditure_lakh", 0.0) or 0.0)

        peers_df, tier = self._resolve_peers(target_row, projects_df)
        peer_count = len(peers_df)

        if peer_count < self.config.min_peers or tier == PeerHierarchyTierEnum.INSUFFICIENT:
            explanation = (
                f"Insufficient comparable peer projects ({peer_count} found, minimum required: {self.config.min_peers}) "
                f"for work category '{work_cat}' in {district}, {state}. Benchmarking withheld to avoid statistical bias."
            )
            limitations = (
                "Statistical benchmark requires a minimum peer cohort to establish representative cost quartiles."
            )
            return ProjectBenchmarkResult(
                project_id=project_id,
                work_name=work_name,
                work_category=work_cat,
                district=district,
                state=state,
                project_estimated_cost_lakh=round(est_cost, 2),
                project_sanctioned_amount_lakh=round(sanc_amount, 2),
                project_expenditure_lakh=round(expenditure, 2),
                benchmark_status=BenchmarkStatusEnum.INSUFFICIENT_PEERS,
                peer_hierarchy_tier=PeerHierarchyTierEnum.INSUFFICIENT,
                peer_count=peer_count,
                cost_ratio_vs_peer_median=None,
                deviation_percentage=None,
                percentile_position=None,
                confidence=0.0,
                peer_stats=None,
                sample_peer_project_ids=[],
                explanation=explanation,
                limitations=limitations,
            )

        peer_costs = peers_df["estimated_cost_lakh"].astype(float).values
        peer_mean = float(np.mean(peer_costs))
        peer_median = float(np.median(peer_costs))
        peer_std = float(np.std(peer_costs))
        peer_min = float(np.min(peer_costs))
        peer_max = float(np.max(peer_costs))

        q75, q25 = np.percentile(peer_costs, [75, 25])
        peer_iqr = float(q75 - q25)

        # Ratio and percentage deviation
        cost_ratio = round(est_cost / peer_median, 2) if peer_median > 0 else 1.0
        deviation_pct = round(((est_cost - peer_median) / peer_median) * 100.0, 1) if peer_median > 0 else 0.0

        # Empirical percentile position (0.0 to 100.0)
        less_equal_count = np.sum(peer_costs <= est_cost)
        percentile = round((float(less_equal_count) / float(peer_count)) * 100.0, 1)

        # Status determination
        if cost_ratio >= self.config.extreme_ratio_threshold:
            status = BenchmarkStatusEnum.EXTREME_DEVIATION
        elif cost_ratio >= self.config.high_ratio_threshold:
            status = BenchmarkStatusEnum.HIGH_DEVIATION
        elif cost_ratio >= self.config.moderate_ratio_threshold:
            status = BenchmarkStatusEnum.MODERATE_DEVIATION
        elif cost_ratio <= self.config.low_outlier_ratio_threshold:
            status = BenchmarkStatusEnum.LOW_OUTLIER
        else:
            status = BenchmarkStatusEnum.NORMAL

        # Confidence calculation
        tier_weight = {
            PeerHierarchyTierEnum.DISTRICT_CATEGORY: 1.0,
            PeerHierarchyTierEnum.STATE_CATEGORY: 0.85,
            PeerHierarchyTierEnum.NATIONAL_CATEGORY: 0.70,
            PeerHierarchyTierEnum.INSUFFICIENT: 0.0,
        }.get(tier, 0.70)
        sample_confidence = min(1.0, peer_count / 10.0)
        confidence = round(0.5 * tier_weight + 0.5 * sample_confidence, 2)

        # Tier descriptive text
        tier_desc = {
            PeerHierarchyTierEnum.DISTRICT_CATEGORY: f"{district} district",
            PeerHierarchyTierEnum.STATE_CATEGORY: f"{state} state",
            PeerHierarchyTierEnum.NATIONAL_CATEGORY: "national baseline",
            PeerHierarchyTierEnum.INSUFFICIENT: "unknown scope",
        }.get(tier, "cohort")

        sample_pids = [str(x) for x in peers_df["project_id"].head(10).tolist()]

        explanation = (
            f"Compared against {peer_count} comparable '{work_cat}' projects in {tier_desc}. "
            f"Current estimated cost (₹{est_cost:.2f}L) is {cost_ratio:.2f}× the peer median (₹{peer_median:.2f}L), "
            f"placing it at the {percentile:.0f}th percentile."
        )

        limitations = (
            "Benchmark reflects historical cost distributions in the dataset. "
            "Local site specifications, terrain difficulty, and material transport variations may justify variance."
        )

        peer_stats = PeerSummaryStats(
            peer_count=peer_count,
            peer_tier=tier,
            peer_mean_cost_lakh=round(peer_mean, 2),
            peer_median_cost_lakh=round(peer_median, 2),
            peer_std_cost_lakh=round(peer_std, 2),
            peer_min_cost_lakh=round(peer_min, 2),
            peer_max_cost_lakh=round(peer_max, 2),
            peer_iqr_lakh=round(peer_iqr, 2),
        )

        return ProjectBenchmarkResult(
            project_id=project_id,
            work_name=work_name,
            work_category=work_cat,
            district=district,
            state=state,
            project_estimated_cost_lakh=round(est_cost, 2),
            project_sanctioned_amount_lakh=round(sanc_amount, 2),
            project_expenditure_lakh=round(expenditure, 2),
            benchmark_status=status,
            peer_hierarchy_tier=tier,
            peer_count=peer_count,
            cost_ratio_vs_peer_median=cost_ratio,
            deviation_percentage=deviation_pct,
            percentile_position=percentile,
            confidence=confidence,
            peer_stats=peer_stats,
            sample_peer_project_ids=sample_pids,
            explanation=explanation,
            limitations=limitations,
        )

    def evaluate_all(
        self,
        projects_df: pd.DataFrame,
        financials_df: Optional[pd.DataFrame] = None,
    ) -> List[ProjectBenchmarkResult]:
        """
        Evaluates comparable benchmarking across all projects in the dataset.
        """
        results: List[ProjectBenchmarkResult] = []
        if projects_df.empty:
            return results

        for pid in projects_df["project_id"].astype(str):
            res = self.evaluate_project(pid, projects_df, financials_df)
            if res:
                results.append(res)

        return results

    def get_summary(
        self,
        results: List[ProjectBenchmarkResult],
    ) -> BenchmarkSummary:
        """
        Generates aggregated summary statistics across benchmark results.
        """
        status_counts: Dict[str, int] = {}
        tier_counts: Dict[str, int] = {}
        ratios: List[float] = []
        insufficient_count = 0

        for r in results:
            s_key = r.benchmark_status.value
            status_counts[s_key] = status_counts.get(s_key, 0) + 1

            t_key = r.peer_hierarchy_tier.value
            tier_counts[t_key] = tier_counts.get(t_key, 0) + 1

            if r.benchmark_status == BenchmarkStatusEnum.INSUFFICIENT_PEERS:
                insufficient_count += 1
            elif r.cost_ratio_vs_peer_median is not None:
                ratios.append(r.cost_ratio_vs_peer_median)

        avg_ratio = round(float(np.mean(ratios)), 2) if ratios else 1.0
        benchmarkable = len(results) - insufficient_count

        return BenchmarkSummary(
            total_projects_evaluated=len(results),
            benchmarkable_projects_count=benchmarkable,
            insufficient_peers_count=insufficient_count,
            status_counts=status_counts,
            tier_counts=tier_counts,
            average_cost_ratio=avg_ratio,
        )
