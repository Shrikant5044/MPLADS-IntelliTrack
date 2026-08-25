from typing import Any, Dict, List, Optional, Tuple
from app.anomaly_engine.models import AnomalyResult, AnomalyTypeEnum, SeverityEnum
from app.risk_engine.models import (
    ANOMALY_CATEGORY_MAPPING,
    CATEGORY_MAX_RULE_WEIGHT,
    MLRiskSignal,
    ProjectRiskProfile,
    RiskCategoryEnum,
    RiskConfig,
    RiskFactor,
    RiskLevelEnum,
)
from ml.predict import ProjectMLPrediction


def get_severity_multiplier(severity: SeverityEnum, config: RiskConfig) -> float:
    if severity == SeverityEnum.CRITICAL:
        return config.severity_critical
    elif severity == SeverityEnum.HIGH:
        return config.severity_high
    elif severity == SeverityEnum.MEDIUM:
        return config.severity_medium
    else:
        return config.severity_low


def get_category_weight(category: RiskCategoryEnum, config: RiskConfig) -> float:
    if category == RiskCategoryEnum.FINANCIAL:
        return config.weight_financial
    elif category == RiskCategoryEnum.PROGRESS:
        return config.weight_progress
    elif category == RiskCategoryEnum.PAYMENT:
        return config.weight_payment
    elif category == RiskCategoryEnum.VENDOR:
        return config.weight_vendor
    elif category == RiskCategoryEnum.AGENCY:
        return config.weight_agency
    elif category == RiskCategoryEnum.DUPLICATE_GEO:
        return config.weight_duplicate_geo
    elif category == RiskCategoryEnum.COMPLIANCE:
        return config.weight_compliance
    elif category == RiskCategoryEnum.ML_STATISTICAL:
        return config.weight_ml
    return 0.0


def generate_summary(
    risk_level: RiskLevelEnum,
    category_scores: Dict[RiskCategoryEnum, float],
    anomalies: List[AnomalyResult],
    ml_signal: Optional[MLRiskSignal] = None,
) -> str:
    """
    Generates a clear, explainable summary of the project's risk profile fusing rule and ML signals.
    """
    if not anomalies and (not ml_signal or not ml_signal.flag):
        return "Project operations, milestone progress, and financial disbursements are proceeding normally with no anomalies detected."

    active_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    top_cats = [cat for cat, score in active_cats if score >= 4.0]

    signals_by_type = {a.anomaly_type: a for a in anomalies}
    descriptions = []

    # 1. Duplicate & Geo driver
    if RiskCategoryEnum.DUPLICATE_GEO in top_cats or AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK in signals_by_type:
        dup_anom = signals_by_type.get(AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK)
        if dup_anom:
            matched_id = dup_anom.evidence.get("matched_project_id", "adjacent project")
            dist_km = dup_anom.evidence.get("distance_km", 0.0)
            descriptions.append(f"potential duplicate work identified with {matched_id} ({dist_km:.2f} km away)")

    # 2. Financial drivers
    if RiskCategoryEnum.FINANCIAL in top_cats:
        if AnomalyTypeEnum.EXPENDITURE_EXCEEDS_SANCTION in signals_by_type:
            descriptions.append("expenditure exceeding approved sanction limit")
        elif AnomalyTypeEnum.COST_OVERRUN in signals_by_type:
            descriptions.append("significant cost overrun against original estimates")
        elif AnomalyTypeEnum.PROGRESS_FINANCIAL_MISMATCH in signals_by_type:
            descriptions.append("high financial drawdown outpacing physical completion")
        elif AnomalyTypeEnum.ABNORMALLY_HIGH_UTILIZATION in signals_by_type:
            descriptions.append("abnormally high fund utilization with lagging progress")
        elif AnomalyTypeEnum.ABNORMALLY_LOW_UTILIZATION in signals_by_type:
            descriptions.append("severe fund underutilization despite advancing schedule")

    # 3. Progress drivers
    if RiskCategoryEnum.PROGRESS in top_cats:
        if AnomalyTypeEnum.PROJECT_DELAY in signals_by_type:
            descriptions.append("timeline delay past expected completion deadline")
        elif AnomalyTypeEnum.SLOW_PROGRESS in signals_by_type or AnomalyTypeEnum.MILESTONE_LAG in signals_by_type:
            descriptions.append("substantial physical execution lag behind schedule targets")
        elif AnomalyTypeEnum.COMPLETION_RISK in signals_by_type:
            descriptions.append("critical completion deadline risk with low physical progress")
        elif AnomalyTypeEnum.NO_RECENT_PROGRESS_UPDATE in signals_by_type:
            descriptions.append("progress reporting stagnation")

    # 4. Payment drivers
    if RiskCategoryEnum.PAYMENT in top_cats:
        if AnomalyTypeEnum.PAYMENT_LOW_PROGRESS in signals_by_type:
            descriptions.append("heavy fund disbursement with low ground physical progress")
        elif AnomalyTypeEnum.LARGE_PAYMENT in signals_by_type or AnomalyTypeEnum.DEADLINE_PAYMENT_CONCENTRATION in signals_by_type:
            descriptions.append("unusual payment tranche concentration")
        elif AnomalyTypeEnum.RAPID_MULTIPLE_PAYMENTS in signals_by_type:
            descriptions.append("rapid consecutive payment disbursements")
        elif AnomalyTypeEnum.PAYMENT_BEFORE_MILESTONE in signals_by_type:
            descriptions.append("premature milestone payments")

    # 5. Vendor & Agency drivers
    if RiskCategoryEnum.VENDOR in top_cats:
        descriptions.append("vendor historical delay/overrun risk factor")
    if RiskCategoryEnum.AGENCY in top_cats:
        descriptions.append("implementing agency recurring systemic performance issues")

    # 6. Compliance drivers
    if RiskCategoryEnum.COMPLIANCE in top_cats:
        if AnomalyTypeEnum.COMPLIANCE_DOCUMENT_GAP in signals_by_type:
            gap_anom = signals_by_type[AnomalyTypeEnum.COMPLIANCE_DOCUMENT_GAP]
            count = gap_anom.evidence.get("missing_document_count", 2)
            descriptions.append(f"{count} mandatory compliance documents missing")
        elif AnomalyTypeEnum.MISSING_COMPLETION_CERTIFICATE in signals_by_type:
            descriptions.append("missing completion certificate on completed project")
        elif AnomalyTypeEnum.MISSING_PAYMENT_SUPPORT in signals_by_type:
            descriptions.append("unsupported financial payment documentation")
        elif AnomalyTypeEnum.MISSING_SANCTION_DOCUMENT in signals_by_type:
            descriptions.append("missing formal sanction order")

    # 7. ML Statistical driver mention
    if ml_signal and ml_signal.flag and ml_signal.contribution >= 3:
        descriptions.append("statistically unusual multi-dimensional patterns detected by unsupervised ML")

    if descriptions:
        joined_desc = ", ".join(descriptions[:3])
        return f"{joined_desc.capitalize()}."
    elif anomalies:
        top_sig = anomalies[0].anomaly_type.value.replace("_", " ").lower()
        return f"Identified moderate operational risk driven by {top_sig}."
    else:
        return "Project exhibits statistically unusual operational metrics according to unsupervised ML analysis."


def generate_recommended_action(
    risk_level: RiskLevelEnum,
    category_scores: Dict[RiskCategoryEnum, float],
    anomalies: Optional[List[AnomalyResult]] = None,
    ml_signal: Optional[MLRiskSignal] = None,
) -> str:
    """
    Generates actionable, deterministic administrative recommendations based on risk severity and dominant driver.
    """
    signals_set = {a.anomaly_type for a in (anomalies or [])}
    has_dup = AnomalyTypeEnum.POTENTIAL_DUPLICATE_WORK in signals_set
    has_comp_gap = AnomalyTypeEnum.COMPLIANCE_DOCUMENT_GAP in signals_set

    fin_score = category_scores.get(RiskCategoryEnum.FINANCIAL, 0.0)
    prog_score = category_scores.get(RiskCategoryEnum.PROGRESS, 0.0)
    pmt_score = category_scores.get(RiskCategoryEnum.PAYMENT, 0.0)
    vdr_score = category_scores.get(RiskCategoryEnum.VENDOR, 0.0)

    if has_dup:
        return "Conduct on-site GPS verification and inspect Measurement Book (MB) records to cross-verify physical site execution against potential duplicate project entry."

    if risk_level == RiskLevelEnum.CRITICAL:
        if fin_score >= 15.0 or pmt_score >= 15.0:
            return "Prioritize district-level audit: Freeze further payment disbursements and dispatch on-site inspection team to verify work completed against billed contractor invoices."
        elif prog_score >= 12.0:
            return "Escalate to District Collector & State Nodal Department: Issue show-cause notice to implementing agency for timeline recovery and milestone restructuring."
        else:
            return "Conduct comprehensive multi-disciplinary audit: Review agency procurement, financial ledgers, and physical milestone verification records."

    elif risk_level == RiskLevelEnum.HIGH:
        if fin_score >= 12.0:
            return "Dispatch district technical verification officer to inspect physical progress before releasing the next financial installment."
        elif prog_score >= 10.0:
            return "Request expedited milestone status update and review agency execution bottlenecks to mitigate delay."
        elif vdr_score >= 5.0:
            return "Flag contractor for enhanced monitoring and review contract allocation prior to sanctioning subsequent works."
        elif has_comp_gap:
            return "Issue administrative notice to implementing agency to upload all pending mandatory compliance and inspection records within 14 days."
        else:
            return "Schedule prioritized field inspection and review evidence uploads."

    elif risk_level == RiskLevelEnum.MEDIUM:
        if has_comp_gap:
            return "Issue compliance notice to implementing agency to submit missing statutory documentation and progress evidence."
        if ml_signal and ml_signal.flag:
            return "Conduct supervisory review of project milestones and payment tranches to verify alignment with physical execution."
        return "Maintain active supervisory monitoring and verify upcoming milestone progress and evidence submissions."

    else:
        return "Project health is within normal operational parameters. Continue routine quarterly monitoring."


class ProjectScorer:
    """
    Deterministic risk scorer that aggregates multi-domain anomaly signals and supporting
    unsupervised ML anomaly signals into a normalized 0-100 project risk score
    using centralized rule-priority weights and intra-category diminishing returns.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

    def score(
        self,
        project_id: str,
        anomalies: List[AnomalyResult],
        ml_prediction: Optional[ProjectMLPrediction] = None,
    ) -> ProjectRiskProfile:
        """
        Computes the complete risk profile for a single project integrating rule-priority weights and ML evidence.
        """
        # 1. Group rule anomalies by category with normalized rule weights
        # Tuple: (anomaly, rule_weight, normalized_rule_weight, weighted_impact)
        category_anomalies: Dict[RiskCategoryEnum, List[Tuple[AnomalyResult, int, float, float]]] = {
            cat: [] for cat in RiskCategoryEnum if cat != RiskCategoryEnum.ML_STATISTICAL
        }

        for a in anomalies:
            cat = ANOMALY_CATEGORY_MAPPING.get(a.anomaly_type, RiskCategoryEnum.FINANCIAL)
            r_weight = self.config.rule_priority_weights.get(a.anomaly_type, 5)
            cat_max_w = CATEGORY_MAX_RULE_WEIGHT.get(cat, 8.0)
            norm_weight = r_weight / float(cat_max_w)
            sev_mult = get_severity_multiplier(a.severity, self.config)
            weighted_impact = norm_weight * sev_mult * float(a.confidence)

            if cat in category_anomalies:
                category_anomalies[cat].append((a, r_weight, norm_weight, weighted_impact))

        category_scores: Dict[RiskCategoryEnum, float] = {}
        # Tuple: (anomaly, category, rule_weight, weighted_impact, raw_points_contribution)
        factor_raw_contributions: List[Tuple[Any, RiskCategoryEnum, int, float, float]] = []

        # 2. Compute de-duplicated, discounted scores for rule categories
        for cat, anom_list in category_anomalies.items():
            cat_weight = get_category_weight(cat, self.config)
            if not anom_list or cat_weight <= 0:
                category_scores[cat] = 0.0
                continue

            # Sort signals within the category by weighted_impact (descending)
            sorted_anoms = sorted(anom_list, key=lambda x: x[3], reverse=True)
            discounted_sum = 0.0
            for rank, (anom, r_w, norm_w, w_impact) in enumerate(sorted_anoms):
                if rank == 0:
                    discount = 1.0
                elif rank == 1:
                    discount = self.config.secondary_signal_discount
                else:
                    discount = self.config.tertiary_signal_discount

                contribution_to_cat = w_impact * discount
                discounted_sum += contribution_to_cat
                factor_raw_contributions.append((anom, cat, r_w, w_impact, contribution_to_cat * cat_weight))

            cat_saturation = min(1.0, discounted_sum)
            category_scores[cat] = cat_saturation * cat_weight

        # 3. Compute ML Statistical Anomaly Signal Contribution (Capped at weight_ml = 5 pts)
        ml_signal: Optional[MLRiskSignal] = None
        ml_score_pts = 0.0

        if ml_prediction is not None:
            raw_ml_score = float(ml_prediction.ml_anomaly_score)
            is_outlier = bool(ml_prediction.ml_anomaly_flag)

            if is_outlier or raw_ml_score >= 50.0:
                # Scaled points [1, 5] based on outlier score
                ml_score_pts = min(self.config.weight_ml, max(1.0, (raw_ml_score / 100.0) * self.config.weight_ml))
            elif raw_ml_score >= 35.0:
                ml_score_pts = 1.0
            else:
                ml_score_pts = 0.0

            ml_signal = MLRiskSignal(
                score=round(raw_ml_score, 1),
                flag=is_outlier,
                contribution=int(round(ml_score_pts)),
                model_version=ml_prediction.model_version,
            )

            category_scores[RiskCategoryEnum.ML_STATISTICAL] = ml_score_pts

        # 4. Compute Total Fused Risk Score
        total_raw_score = sum(category_scores.values())
        final_risk_score = int(min(100, max(0, round(total_raw_score))))

        # 5. Determine Risk Level
        if final_risk_score >= 75:
            risk_level = RiskLevelEnum.CRITICAL
        elif final_risk_score >= 50:
            risk_level = RiskLevelEnum.HIGH
        elif final_risk_score >= 25:
            risk_level = RiskLevelEnum.MEDIUM
        else:
            risk_level = RiskLevelEnum.LOW

        # 6. Build Explainable Risk Factors
        rule_contrib_sum = sum(c for _, _, _, _, c in factor_raw_contributions)
        risk_factors: List[RiskFactor] = []

        if rule_contrib_sum > 0:
            # Scale rule factor contributions to match total rule points
            rule_points_total = max(0, final_risk_score - int(round(ml_score_pts)))
            for anom, cat, r_w, w_imp, raw_c in factor_raw_contributions:
                scaled_points = int(round((raw_c / rule_contrib_sum) * rule_points_total))
                if scaled_points > 0 or final_risk_score > 0:
                    risk_factors.append(RiskFactor(
                        category=cat,
                        signal=anom.anomaly_type.value,
                        contribution=max(1, scaled_points) if rule_points_total > 0 else 0,
                        severity=anom.severity,
                        confidence=round(float(anom.confidence), 2),
                        rule_weight=r_w,
                        weighted_impact=round(float(w_imp), 3),
                    ))

        # Add ML risk factor if it contributed points
        if ml_signal and ml_signal.contribution > 0:
            risk_factors.append(RiskFactor(
                category=RiskCategoryEnum.ML_STATISTICAL,
                signal="ML_STATISTICAL_OUTLIER" if ml_signal.flag else "ML_ELEVATED_ANOMALY_SCORE",
                contribution=ml_signal.contribution,
                severity=SeverityEnum.HIGH if ml_signal.flag else SeverityEnum.MEDIUM,
                confidence=round(ml_signal.score / 100.0, 2),
                rule_weight=None,
                weighted_impact=round(float(ml_score_pts) / float(self.config.weight_ml), 3),
            ))

        risk_factors.sort(key=lambda x: x.contribution, reverse=True)

        # 7. Generate Summary and Governance Recommendation
        summary = generate_summary(risk_level, category_scores, anomalies, ml_signal)
        recommended_action = generate_recommended_action(risk_level, category_scores, anomalies, ml_signal)

        return ProjectRiskProfile(
            project_id=project_id,
            risk_score=final_risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            ml_signal=ml_signal,
            summary=summary,
            recommended_action=recommended_action,
        )
